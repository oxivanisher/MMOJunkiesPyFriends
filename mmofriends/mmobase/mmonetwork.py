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

from flask import current_app
from mmoutils import *
from mmouser import *
from mmofriends import db

class MMONetworkProduct(object):

    def __init__(self, name):
        self.log = logging.getLogger(__name__)
        self.log.debug("Initializing MMONetwork product %s" % name)
        self.name = name
        self.fields = []

    def addField(self, name, comment = "", fieldType = str):
        self.log.debug("Add a field with name, comment and fieldType")
        self.fields.append((name, fieldType))

class MMONetworkCache(db.Model):
    __tablename__ = 'mmonetcache'

    id = db.Column(db.Integer, primary_key=True)
    network_handle = db.Column(db.String(20))
    entry_name = db.Column(db.String(20))
    last_update = db.Column(db.Integer)
    cache_data = db.Column(db.Text)

    def __init__(self, network_handle, entry_name, cache_data = ""):
        self.network_handle = network_handle
        self.entry_name = entry_name
        self.last_update = 0
        self.cache_data = cache_data

    def __repr__(self):
        return '<MMONetCache %r>' % self.id

    def get(self):
        return json.loads(self.cache_data)

    def set(self, cache_data):
        self.cache_data = json.dumps(cache_data)

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
        self.log.info("Initializing MMONetwork %s (%s)" % (self.name, self.handle))

        self.description = "Unset"
        self.moreInfo = 'NoMoreInfo'
        self.varsToSave = []
        self.lastRefreshDate = 0
        self.adminMethods = []
        self.cache = {}

        # self.hidden = False

        # atexit.register(self.saveAtExit)

        self.products = self.getProducts() #Fields: Name, Type (realm, char, comment)

    def setLogLevel(self, level):
        self.log.info("Setting loglevel to %s" % level)
        self.log.setLevel(level)

    def refresh(self):
        self.log.debug("Refresh data from source")

    def getLinkHtml(self):
        self.log.debug("Show linkHtml %s" % self.name)

    def doLink(self, userId):
        self.log.debug("Link user %s to network %s" % (userId, self.name))

    def finalizeLink(self, userKey):
        self.log.debug("Finalize user link to network %s" % self.name)

    def saveLink(self, network_data):
        self.log.debug("Saving network link for user %s" % (self.session['nick']))
        netLink = MMONetLink(self.session['userid'], self.handle, network_data)
        db.session.add(netLink)
        db.session.commit()
        db.session.flush()

    def loadLinks(self, userId):
        self.log.debug("Loading user links for userId %s" % userId)
        self.setSessionValue(self.linkIdName, None)
        for link in self.getNetworkLinks(userId):
            self.setSessionValue(self.linkIdName, link['network_data'])

    def getNetworkLinks(self, userId = None):
        netLinks = []
        if userId:
            self.log.debug("Loading network links for userId %s" % (userId))
            for link in db.session.query(MMONetLink).filter_by(user_id=userId, network_handle=self.handle):
                netLinks.append({'network_data': link.network_data, 'linked_date': link.linked_date, 'user_id': link.user_id, 'id': link.id})
        else:
            self.log.debug("Loading all network links")
            for link in db.session.query(MMONetLink).filter_by(network_handle=self.handle):
                netLinks.append({'network_data': link.network_data, 'linked_date': link.linked_date, 'user_id': link.user_id, 'id': link.id})
        return netLinks

    def unlink(self, user_id, netLinkId):
        try:
            link = db.session.query(MMONetLink).filter_by(user_id=user_id, id=netLinkId).first()
            self.setSessionValue(self.linkIdName, None)
            db.session.delete(link)
            db.session.commit()
            db.session.flush()
            self.log.info("Unlinked network with userid %s and netLinkId %s" % (user_id, netLinkId))
            return True
        except Exception as e:
            self.log.info("Unlinking network with userid %s and netLinkId %s failed" % (user_id, netLinkId))
            return False

    def getPartners(self):
        self.log.debug("List all partners for given user")
        return ( False, "Network not yet programmed")
        return ( True, {'id': 'someId',
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
        self.log.debug("List partner details")

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

    def getProducts(self):
        self.log.debug("MMONetwork %s: Fetching products" % self.handle)

    def setNetworkMoreInfo(self, moreInfo):
        self.moreInfo = moreInfo

    def admin(self):
        self.log.debug("Loading admin stuff")

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

    def loadNetworkToSession(self):
        if not self.getSessionValue('loaded'):
            self.log.info("Loading MMONetwork to session")
            self.loadLinks(self.session.get('userid'))
            self.setSessionValue('loaded', True)

    def prepareForFirstRequest(self):
        self.log.debug("Prepare for first request.")

    def cacheFile(self, url):
        newUrl = url.replace('https://', '').replace('http://', '').replace('/', '-')
        outputFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../static/cache', newUrl)
        # outputFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../static/cache', url.split('/')[-1])

        if os.path.isfile(outputFilePath):
            self.log.debug("Not downloading %s" % url)
        else:
            self.log.info("Downloading %s" % url)

            avatarFile = urllib.URLopener()
            avatarFile.retrieve(url, outputFilePath)
        return newUrl

    def getCache(self, name):
        ret = MMONetworkCache.query.filter_by(network_handle=self.handle, entry_name=name).first()
        if ret:
            self.log.debug("Loading cache %s from database" % name)
            self.cache[name] = json.loads(ret.cache_data)
        else:
            self.log.debug("Setting up new cache named %s" % name)
            self.cache[name] = {}

    def setCache(self, name):
        self.log.debug("Saving cache named %s" % name)
        ret = MMONetworkCache.query.filter_by(network_handle=self.handle, entry_name=name).first()
        if ret:
            ret.set(self.cache[name])
        else:
            ret = MMONetworkCache(self.handle, name)
            ret.set(self.cache[name])

        db.session.add(ret)
        db.session.commit()
        

    # saver and loader methods
    # def registerToAutosaveAndLoad(self, var, fileName, default):
    #     self.log.debug("Registring %s to save on exit." % fileName)
    #     self.varsToSave.append((var, fileName, default))

    # def loadFromSave(self):
    #     self.log.debug("MMONetwork loading data from file")
    #     for var, fileName, default in self.varsToSave:
    #         var = loadJSON(self.handle, fileName, default)

    # def saveAtExit(self):
    #     self.log.debug("MMONetwork saving data on exit")
    #     for var, fileName, default in self.varsToSave:
    #         saveJSON(self.handle, fileName, var)