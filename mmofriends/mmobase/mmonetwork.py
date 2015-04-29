#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
import socket
import os
import random
import atexit
import urllib
import json
import zlib
import traceback
import signal

from flask import current_app
from flask.ext.babel import Babel, gettext
from mmoutils import *
from mmouser import *
from mmofriends import db

class Timeout():
    """Timeout class using ALARM signal."""
    class Timeout(Exception):
        pass
 
    def __init__(self, sec):
        self.sec = sec
 
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.raise_timeout)
        signal.alarm(self.sec)
 
    def __exit__(self, *args):
        signal.alarm(0)    # disable alarm
 
    def raise_timeout(self, *args):
        raise Timeout.Timeout()

class MMONetworkCache(db.Model):
    __tablename__ = 'mmonetcache'
    
    id = db.Column(db.Integer, primary_key=True)
    network_handle = db.Column(db.String(20))
    entry_name = db.Column(db.String(20))
    last_update = db.Column(db.Integer)
    cache_data = db.Column(db.UnicodeText) #MEDIUMTEXT
    
    __table_args__ = (db.UniqueConstraint(network_handle, entry_name, name="handle_name_uc"), )

    def __init__(self, network_handle, entry_name, cache_data = ""):
        self.network_handle = network_handle
        self.entry_name = entry_name
        self.last_update = 0
        self.cache_data = cache_data

    def __repr__(self):
        return '<MMONetworkCache %r>' % self.id

    def get(self):
        return json.loads(self.cache_data)

    def set(self, cache_data):
        self.cache_data = json.dumps(cache_data)

    def age(self):
        return int(time.time()) - self.last_update

class MMONetwork(object):

    def __init__(self, app, session, handle):
        # loading config
        self.app = app
        self.session = session
        self.handle = handle
        self.config = self.app.config['networkConfig'][handle]

        # setting variables
        self.name = self.config['name']
        self.icon = self.config['icon']
        self.linkIdName = 'userToken'

        self.log = logging.getLogger(__name__ + "." + self.handle.lower())
        self.log.info("[%s] Initializing MMONetwork %s" % (self.handle, self.name))

        self.description = self.config['description']
        self.varsToSave = []
        self.lastRefreshDate = 0
        self.backgroundWorkerTime = 0
        self.adminMethods = []
        self.userMethods = []
        self.backgroundTasks = []
        self.dashboardBoxes = {}
        self.cache = {}

    # Helpers
    def getUserById(self, userId):
        ret = MMOUser.query.filter_by(id=userId).first()
        if ret:
            return ret
        else:
            return None

    def setLogLevel(self, level):
        self.log.info("[%s] Setting loglevel to %s" % (self.handle, level))
        self.log.setLevel(level)

    def checkForUserOnline(self, userId):
        return True

    def getSessionValue(self, name):
        try:
            return self.session[self.handle][name]
        except KeyError:
            self.session[self.handle] = {}
            return None

    def setSessionValue(self, name, value):
        try:
            self.session[self.handle][name] = value
        except Exception, e:
            self.session[self.handle] = {}
            self.session[self.handle][name] = value

    def delSessionValue(self, name):
        try:
            self.session[self.handle][name] = None
            del self.session[self.handle][name]
        except Exception:
            pass

    def loadNetworkToSession(self):
        if not self.getSessionValue('loaded'):
            self.log.info("[%s] Loading MMONetwork to session" % (self.handle))
            self.loadLinks(self.session.get('userid'))
            self.setSessionValue('loaded', True)
            return (True, "[%s] loaded to session" % (self.handle))
        return (True, "[%s] already loaded to session" % (self.handle))

    def cacheFile(self, url):
        if not url:
            return url
        newUrl = url.replace('https://', '').replace('http://', '').replace('/', '-')
        outputFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../static/cache', newUrl)
        # outputFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../static/cache', url.split('/')[-1])

        if os.path.isfile(outputFilePath):
            self.log.debug("[%s] Not downloading %s" % (self.handle, url))
        else:
            self.log.info("[%s] Downloading %s" % (self.handle, url))

            avatarFile = urllib.URLopener()
            try:
                avatarFile.retrieve(url, outputFilePath)
            except IOError as e:
                self.log.warning("[%s] Unable to cache file from URL: %s (%s)" % (self.handle, url, e))
                return ""
        return newUrl

    # Basic class methods
    def refresh(self):
        self.log.debug("[%s] Refresh data from source" % (self.handle))

    def admin(self):
        self.log.debug("[%s] Loading admin stuff" % (self.handle))

    def prepareForFirstRequest(self):
        self.log.info("[%s] Running prepareForFirstRequest." % (self.handle))

    def getLastly(self):
        self.log.info("[%s] Running getLastly." % (self.handle))
        self.getCache("lastly")
        return self.cache["lastly"]

    # Network linking methods
    def getLinkHtml(self):
        self.log.debug("[%s] Show linkHtml %s" % (self.handle, self.name))

    def doLink(self, userId):
        self.log.debug("[%s] Link user %s to network %s" % (self.handle, userId, self.name))

    def clearLinkRequest(self):
        self.log.debug("[%s] Clearing link requst" % (self.handle))

    def finalizeLink(self, userKey):
        self.log.debug("[%s] Finalize user link to network %s" % (self.handle, self.name))

    def saveLink(self, network_data):
        updateLink = False

        ret = MMONetLink.query.filter_by(network_handle=self.handle, user_id=self.session['userid']).first()
        if ret:
            if not ret.network_data:
                updateLink = True
                
        if updateLink:
            self.log.debug("[%s] Updating network link for user %s" % (self.handle, self.session['nick']))
            ret.network_data = network_data
            db.session.merge(ret)
        else:
            self.log.debug("[%s] Saving network link for user %s" % (self.handle, self.session['nick']))
            netLink = MMONetLink(self.session['userid'], self.handle, network_data)
            db.session.add(netLink)

        db.session.flush()
        db.session.commit()

    def updateLink(self, userid, network_data, logger = None):
        if not logger:
            logger = self.log
        logger.debug("[%s] Updating network link for user %s" % (self.handle, userid))
        netLink = MMONetLink(userid, self.handle, network_data)
        ret = MMONetLink.query.filter_by(network_handle=self.handle, user_id=userid).first()
        if not ret:
            logger.warning("[%s] Unable to update network link for user %s, no existing link found." % (self.handle, userid))
            return False

        ret.network_data = network_data
        db.session.merge(ret)
        db.session.flush()
        db.session.commit()
        return True

    def loadLinks(self, userId):
        self.log.debug("[%s] Loading user links for userId %s" % (self.handle, userId))
        self.setSessionValue(self.linkIdName, None)
        for link in self.getNetworkLinks(userId):
            self.setSessionValue(self.linkIdName, link['network_data'])

    def getNetworkLinks(self, userId = None):
        netLinks = []
        if userId:
            self.log.debug("[%s] Getting network links for userId %s" % (self.handle, userId))
            for link in db.session.query(MMONetLink).filter_by(user_id=userId, network_handle=self.handle):
                netLinks.append({'network_data': link.network_data, 'linked_date': link.linked_date, 'user_id': link.user_id, 'id': link.id})
        else:
            self.log.debug("[%s] Getting all network links" % (self.handle))
            for link in db.session.query(MMONetLink).filter_by(network_handle=self.handle):
                netLinks.append({'network_data': link.network_data, 'linked_date': link.linked_date, 'user_id': link.user_id, 'id': link.id})
        return netLinks

    def unlink(self, user_id, netLinkId):
        try:
            link = db.session.query(MMONetLink).filter_by(user_id=user_id, id=netLinkId).first()
            self.delSessionValue(self.linkIdName)
            db.session.delete(link)
            db.session.flush()
            db.session.commit()
            self.log.info("[%s] Unlinked network with userid %s and netLinkId %s" % (self.handle, user_id, netLinkId))
            return True
        except Exception as e:
            self.log.info("[%s] Unlinking network with userid %s and netLinkId %s failed" % (self.handle, user_id, netLinkId))
            return False

    # Partner methods
    def getPartners(self, **kwargs):
        self.log.debug("[%s] List all partners for given user" % (self.handle))
        return ( False, "Network not yet programmed")
        return ( True, {'id': 'someId',
                        'mmoid': internalId,
                        'nick': 'nickName',
                        'state': 'State',
                        'netHandle': self.handle,
                        'networkText': 'Product',
                        'networkImgs': [{
                            'type': 'network',
                            'name': self.handle,
                            'title': self.name
                        },{
                            'type': 'cache',
                            'name': 'gameIconPath',
                            'title': 'gameName'
                        },{
                            'type': 'cache',
                            'name': 'mapIconPath',
                            'title': 'mapName'
                        }],
                        'friendImgs': [{
                            'type': 'cache',
                            'name': 'rankIconPath',
                            'title': 'rankIcon'
                        },{
                            'type': 'cache',
                            'name': 'someImagePath',
                            'title': 'someImage'
                        }]
                    })

    def findPartners(self):
        self.log.debug("[%s] Searching for new partners to play with" % (self.handle))
        return ( False, "Network not yet programmed")
        return ( True, {'id': 'someId',
                        'mmoid': internalId,
                        'nick': 'nickName',
                        'state': 'State',
                        'netHandle': self.handle,
                        'networkText': 'Product',
                        'networkImgs': [{
                            'type': 'network',
                            'name': self.handle,
                            'title': self.name
                        },{
                            'type': 'cache',
                            'name': 'gameIconPath',
                            'title': 'gameName'
                        },{
                            'type': 'cache',
                            'name': 'mapIconPath',
                            'title': 'mapName'
                        }],
                        'friendImgs': [{
                            'type': 'cache',
                            'name': 'rankIconPath',
                            'title': 'rankIcon'
                        },{
                            'type': 'cache',
                            'name': 'someImagePath',
                            'title': 'someImage'
                        }]
                    })

    def getPartnerDetails(self, partnerId):
        self.log.debug("[%s] List partner details" % (self.handle))

    def setPartnerFlag(self, myDict, key, value):
        try:
            myDict['flags']
        except KeyError:
            myDict['flags'] = []
        if value != '0' and value:
            myDict['flags'].append(key)

    def setPartnerDetail(self, myDict, key, value):
        try:
            myDict['details']
        except KeyError:
            myDict['details'] = []
        if value != '0' and value:
            myDict['details'].append({'key': key, 'value': value})

    def setPartnerAvatar(self, myDict, avatarName):
        if avatarName[0] == '/':
            avatarName = avatarName[1:]
        myDict['avatar'] = avatarName

    def getStats(self):
        self.log.debug("[%s] Requesting stats" % (self.handle))
        return { 'Loaded': True }

    # MMONetworkCache methods
    def getCache(self, name):
        ret = MMONetworkCache.query.filter_by(network_handle=self.handle, entry_name=name).first()
        if ret:
            # self.log.debug("Loading cache: %s" % name)
            try:
                # output_dict = {}
                # for key, value in json.loads(ret.cache_data).iteritems():
                #     output_dict[convertToInt(key)] = value
                # self.cache[name] = output_dict

                self.cache[name] = json.loads(ret.cache_data)
            except ValueError as e:
                # print "e", e
                self.cache[name] = {}
        else:
            # self.log.debug("Setting up new cache: %s" % name)
            self.cache[name] = {}

        # db.session.commit()

    def setCache(self, name):
        # self.log.debug("Saving cache: %s" % name)
        ret = MMONetworkCache.query.filter_by(network_handle=self.handle, entry_name=name).first()
        if ret:
            # self.log.debug("Found existing cache")
            ret.set(self.cache[name])
        else:
            # self.log.debug("New cache created")
            ret = MMONetworkCache(self.handle, name)
            ret.set(self.cache[name])
        ret.last_update = int(time.time())
        db.session.merge(ret)
        db.session.flush()
        db.session.commit()
        # db.session.expire(ret)

    def getCacheAge(self, name):
        # self.log.debug("Getting age of cache: %s" % name)
        ret = MMONetworkCache.query.filter_by(network_handle=self.handle, entry_name=name).first()
        if not ret:
            return int(time.time())
        return ret.last_update

    def forceCacheUpdate(self, name):
        self.log.debug("[%s] Forcing cache update: %s" % (self.handle, name))
        ret = MMONetworkCache.query.filter_by(network_handle=self.handle, entry_name=name).first()
        if ret:
            try:
                self.cache[name] = json.loads(ret.cache_data)
            except ValueError:
                self.cache[name] = {}
        else:
            self.cache[name] = {}
            ret = MMONetworkCache(self.handle, name)
            
        ret.last_update = 0
        db.session.merge(ret)
        db.session.flush()
        db.session.commit()
        # db.session.expire(ret)

    # Background worker methods
    def background_worker(self, logger):
        if logging.DEBUG == self.log.getEffectiveLevel():
            logger.setLevel(self.log.getEffectiveLevel())
        else:
            logger.setLevel(logging.INFO)

        logger.debug("[%s] Background worker is looping" % (self.handle))
        for (method, timeout, lastCheck) in self.backgroundTasks:
            self.getCache('backgroundTasks')
            if method.func_name not in self.cache['backgroundTasks']:
                self.cache['backgroundTasks'][method.func_name] = {}
                self.cache['backgroundTasks'][method.func_name]['handle'] = self.handle
                self.cache['backgroundTasks'][method.func_name]['method'] = method.func_name
                self.cache['backgroundTasks'][method.func_name]['timeout'] = timeout
                self.cache['backgroundTasks'][method.func_name]['start'] = 0
                self.cache['backgroundTasks'][method.func_name]['end'] = 0
                self.setCache('backgroundTasks')

            run = False
            remove = False
            index = self.backgroundTasks.index((method, timeout, lastCheck))
            if not timeout:
                run = True
                remove = True
            else:
                if time.time() - lastCheck > timeout:
                    run = True
                    self.backgroundTasks[index] = (method, timeout, time.time())

            if run:
                self.cache['backgroundTasks'][method.func_name]['start'] = time.time()
                self.setCache('backgroundTasks')

                ret = None
                logger.info("[%s] %s (%s)" % (self.handle, method.func_name, timeout))
                try:
                    with Timeout(300):
                        ret = method(logger)
                except Timeout.Timeout:
                    self.getCache('backgroundTasks')
                    logger.error("[%s] Timeout of 300 seconds reached. Background job '%s' killed!\n%s\n%s" % (self.handle, method.func_name, traceback.format_exc(), self.cache['backgroundTasks'][method.func_name]['result']))
                    ret = False
                except Exception as e:
                    logger.error("[%s] Exception catched in '%s':\n%s" % (self.handle, method.func_name, traceback.format_exc()))
                    ret = False
                if ret:
                    logger.info("[%s] -> %s" % (self.handle, ret))

                self.getCache('backgroundTasks')
                self.cache['backgroundTasks'][method.func_name]['end'] = time.time()
                self.cache['backgroundTasks'][method.func_name]['result'] = ret
                self.setCache('backgroundTasks')

            if remove:
                logger.info("[%s] -> Removing task %s" % (self.handle, method.func_name))
                self.backgroundTasks.pop(index)

    def setBackgroundWorkerResult(self, message):
        self.getCache('liveBGTask')
        self.cache['liveBGTask']['message'] = message
        self.setCache('liveBGTask')

    def registerWorker(self, method, timeout):
        self.log.info("[%s] Registered background worker %s (%s)" % (self.handle, method.func_name, timeout))
        self.backgroundTasks.append((method, timeout, 0))

    def registerDashboardBox(self, method, handle, settings = {}):
        self.dashboardBoxes[handle] = createDashboardBox(method, self.handle, handle, settings)

    # Game methods
    def getGames(self):
        pass

    def getGamesOfUser(self, userId):
        pass

    def getUsersOfGame(self, gameName):
        pass

    # Dashboard methods
    def getDashboardBoxes(self):
        self.log.info("[%s] Get dashboard boxes" % self.handle)
        return self.dashboardBoxes.keys()

    def getDashboardBox(self, handle):
        self.log.info("[%s] Get dashboard box %s" % (self.handle, handle))
        if handle in self.dashboardBoxes.keys():
            return self.dashboardBoxes[handle]
        else:
            return None
