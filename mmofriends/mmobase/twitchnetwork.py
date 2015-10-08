#!/usr/bin/env python
# -*- coding: utf-8 -*-

# http://support.mashery.com/docs/read/mashery_api/20/Samples
# https://github.com/litl/rauth

import logging
import time
import os
import random
import json
import requests
import urllib

from flask import current_app, url_for
from flask.ext.babel import Babel, gettext

from mmofriends.mmoutils import *
from mmofriends.models import *

try:
    from rauth.service import OAuth2Service
except ImportError:
    logging.error("[System] Please install the rauth library (https://github.com/litl/rauth)")
    import sys
    sys.exit(2)

class TwitchNetwork(MMONetwork):

    def __init__(self, app, session, handle):
        super(TwitchNetwork, self).__init__(app, session, handle)

        # self.setLogLevel(logging.DEBUG)

        # admin methods
        # self.adminMethods.append((self.updateBaseResources, 'Recache base resources'))

        # background updater methods$
        self.registerWorker(self.updateAllUserResources, 121)

        # dashboard boxes
        self.registerDashboardBox(self.dashboard_channels, 'channels', {'title': 'Streams'})

        # setup twitch service
        self.baseUrl = 'https://api.twitch.tv/kraken'
        self.twitchApi = OAuth2Service(
            client_id=self.config['apikey'],
            client_secret=self.config['apisecret'],
            authorize_url='%s/oauth2/authorize' % self.baseUrl,
            access_token_url='%s/oauth2/token' % self.baseUrl)

    # Class overwrites
    def getPartnerDetails(self, partnerId):
        moreInfo = {}
        self.getCache('channels')
        self.getCache("streams")

        try:
            self.setPartnerDetail(moreInfo, gettext("Nickname"), self.cache['channels'][partnerId]['display_name'])
            online = False
            if 'stream' in self.cache['streams'][partnerId].keys():
                if self.cache['streams'][partnerId]['stream'] != None:
                    self.setPartnerDetail(moreInfo, gettext("Streaming"), gettext("Yes"))
                    self.setPartnerDetail(moreInfo, gettext("Viewers"), self.cache['streams'][partnerId]['stream']['viewers'])
                    self.setPartnerDetail(moreInfo, gettext("Status"), self.cache['channels'][partnerId]['status'])
                    self.setPartnerDetail(moreInfo, gettext("Game"), self.cache['channels'][partnerId]['game'])
                    online = True
            if not online:
                self.setPartnerDetail(moreInfo, gettext("Streaming"), gettext("No"))

            if 'logo' in self.cache['channels'][partnerId].keys():
                if self.cache['channels'][partnerId]['logo']:
                    self.setPartnerAvatar(moreInfo, self.cacheFile(self.cache['channels'][partnerId]['logo']))
            elif 'banner' in self.cache['channels'][partnerId].keys():
                if self.cache['channels'][partnerId]['banner']:
                    self.setPartnerAvatar(moreInfo, self.cacheFile(self.cache['channels'][partnerId]['banner']))
            elif 'video_banner' in self.cache['channels'][partnerId].keys():
                if self.cache['channels'][partnerId]['video_banner']:
                    self.setPartnerAvatar(moreInfo, self.cacheFile(self.cache['channels'][partnerId]['video_banner']))
                
        except (KeyError, IndexError):
            pass

        return moreInfo

    def getPartners(self, **kwargs):
        self.log.debug("[%s] List all partners for given user" % (self.handle))

        self.getCache('channels')
        result = []
        try:
            allLinks = self.getNetworkLinks()
            for userid in self.cache['channels'].keys():
                if str(userid) == str(self.session['userid']):
                    continue

                myProducts = [{ 'type': 'network',
                                'name': self.handle,
                                'title': self.name }]

                result.append({ 'id': userid,
                                'mmoid': userid,
                                'nick': self.cache['channels'][userid]['display_name'],
                                'state': 'No info available',
                                'netHandle': self.handle,
                                'networkText': self.name,
                                'networkImgs': myProducts,
                                'friendImgs': []
                            })

            return (True, result)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            message = "Unable to connect to Network: %s %s %s:%s" % (exc_type, e, fname, exc_tb.tb_lineno )
            self.log.warning(message)
            return (False, message)

    def checkForUserOnline(self, partnerId):
        self.getCache("channels")
        self.getCache("streams")

        try:
            if partnerId in self.cache['channels'].keys():
                userid = partnerId
            return False
        except (KeyError, IndexError):
            return False

        if userid in self.cache['streams'].keys():
            if 'stream' in self.cache['streams'][userid].keys():
                if self.cache['streams'][userid]['stream'] != None:
                    return True
        return False

    def getStats(self):
        self.log.debug("[%s] Requesting stats" % (self.handle))
        self.getCache("channels")
        self.getCache("streams")

        return {
            gettext('User Channels'): len(self.cache['channels']),
            gettext('Streams Total'): len(self.cache['streams'])
        }

    def getLinkHtml(self):
        self.log.debug("Show linkHtml %s" % self.name)
        htmlFields = {}
        # if not self.getSessionValue(self.linkIdName):
        htmlFields['link'] = {'comment': "%s %s" % (gettext("Login with"), self.name),
                              'linkUrl': self.requestAuthorizationUrl()}
        return htmlFields

    # Oauth2 helper
    def requestAuthorizationUrl(self):
        self.log.debug("[%s] %s is requesting the Authorization URL (Step 1/3)" % (self.handle, self.session['nick']))
        params = {'redirect_uri': url_for('oauth2_login', netHandle=self.handle, _external=True),
                  'scope': 'user_read channel_read',
                  'response_type': 'code'}
        self.log.debug("[%s] Generating Authorization Url" % (self.handle))
        return self.twitchApi.get_authorize_url(**params)

    def requestAccessToken(self, code):
        self.log.debug("[%s] Recieved code: %s" % (self.handle, code))
        self.log.debug("[%s] %s is requesting a Access Token (Step 2/3)" % (self.handle, self.session['nick']))

        data = {'redirect_uri': url_for('oauth2_login', netHandle=self.handle, _external=True),
                'grant_type': 'authorization_code',
                'code': code}

        access_token = self.twitchApi.get_access_token(decoder = json.loads, data=data)
        self.log.debug("[%s] Oauth2 Login successful, recieved new access_token (Step 3/3)" % (self.handle))
        self.saveLink(access_token)
        self.setSessionValue(self.linkIdName, access_token)
        self.updateUserResources()
        self.getCache("channels")
        return self.cache['channels'][self.session['userid']]['display_name']

    # twitch api methods
    def queryTwitchApi(self, what, accessToken = None):
        self.log.debug("[%s] Query Twitch API for %s" % (self.handle, what))
        if not accessToken:
            accessToken = self.getSessionValue(self.linkIdName)

        headers = {'Accept': 'application/vnd.twitchtv.v2+json',
                   'Authorization': 'OAuth %s' % accessToken}

        tryCount = 0
        while tryCount < 3:
            try:
                tryCount += 1
                r = requests.get(self.baseUrl + what, headers=headers, timeout=6.1).json()
                break
            except requests.exceptions.Timeout:
                self.log.warning("[%s] queryTwitchApi ran into timeout for: %s" % (self.handle, what))
            except requests.exceptions.RequestException as e:
                self.log.warning("[%s] queryTwitchApi ran into requests.exception %s for: %s" % (self.handle, e, what))
            except (ValueError, requests.ConnectionError) as e:
                self.log.warning("[%s] queryTwitchApi got ValueError %s for: %s" % (self.handle, e, what))
            except Exception as e:
                self.log.warning("[%s] queryTwitchApi ran into exception %s for: %s" % (self.handle, e, what))
                return (False, e)
        else:
            message = "queryTwitchApi %s tries reached for: %s" % (tryCount, what)
            self.log.warning("[%s] %s" % (self.handle, message))
            return (False, message)
        return (True, r)

    def updateUserResources(self, userid = None, accessToken = None, logger = None):
        if not logger:
            logger = self.log

        background = True

        if isinstance( userid, int ):
            userNick = self.getUserById(userid).nick
            userFetchMode = True
        else:
            userNick = "System"
            userFetchMode = False

        if userid == None:
            userid = self.session['userid']
            background = False
            logger.debug("[%s] Foreground updating the resources for userid %s" % (self.handle, userNick))
        else:
            logger.debug("[%s] Background updating the resources for userid %s" % (self.handle, userNick))
        

        if not accessToken:
            if userid != self.session['userid']:
                link = self.getNetworkLinks(userid)
                accessToken = link[0]['network_data']
                if not accessToken:
                    return (False, "Unable to update resources for %s (no access Token)" % userNick)
            else:
                accessToken = self.getSessionValue(self.linkIdName)

        if userFetchMode:
            logger.debug("[%s] Fetching channel for %s" % (self.handle, userNick))
            self.getCache("channels")
            (ret, channel) = self.queryTwitchApi("/channel", accessToken)
            if ret and len(channel):
                if 'error' in channel.keys():
                    logger.warning("[%s] Unable to fetch channel for %s: %s (%s)" % (self.handle, userNick, channel['error'], channel['message']))
                    if channel['message'] == "Token invalid or missing required scope":
                        self.updateLink(userid, None)
                    return (False, "Unable to update resources for %s: %s (%s)" % (userNick, channel['error'], channel['message']))
                elif 'name' not in channel.keys():
                    logger.warning("[%s] Unable to fetch channel for %s: no name found in channel (%s)" % (self.handle, userNick, channel))
                    return (False, "Unable to update resources for %s: no name found in channel (%s)" % (self.handle, userNick, channel))

                self.cache['channels'][userid] = channel

                self.setCache("channels")
                logger.debug("[%s] Fetched channel for %s" % (self.handle, userNick))
                if 'logo' in channel:
                    if channel['logo']:
                        self.cacheFile(channel['logo'])
                if 'banner' in channel:
                    if channel['banner']:
                        self.cacheFile(channel['banner'])
                if 'video_banner' in channel:
                    if channel['video_banner']:
                        self.cacheFile(channel['video_banner'])
        else:
            channel = { 'name': userid }

        if isinstance(channel, dict):
            if isinstance(channel['name'], basestring):
                logger.debug("[%s] Fetching stream for %s (%s)" % (self.handle, userNick, channel['name']))
                self.getCache("streams")
                
                lastOnline = False
                if userid in self.cache['streams'].keys():
                    if 'stream' in self.cache['streams'][userid].keys():
                        if self.cache['streams'][userid]['stream'] != None:
                            lastOnline = True
                
                (ret, stream) = self.queryTwitchApi("/streams/%s" % channel['name'], accessToken)
                nowOnline = False
                if ret and len(stream):
                    if 'stream' in stream:
                        if stream['stream']:
                            if 'preview' in stream['stream']:
                                nowOnline = True
                                stream['stream']['preview'] = stream['stream']['preview'].replace('http://', '//')
            
                    if 'error' in stream.keys():
                        logger.warning("[%s] Unable to fetch stream for %s: %s (%s)" % (self.handle, userNick, stream['error'], stream['message']))
                        return (False, "Unable to update resources for %s: %s (%s)" % (userNick, stream['error'], stream['message']))
                    self.cache['streams'][userid] = stream
                    self.setCache("streams")
                    logger.debug("[%s] Fetched stream for %s" % (self.handle, userNick))

                if nowOnline != lastOnline:
                    if userFetchMode:
                        self.getCache("lastly")
                                
                        if nowOnline == True:
                            self.cache["lastly"][time.time()] = '%s started streaming %s.' % (channel['name'], channel['game'])
                        else:
                            self.cache["lastly"][time.time()] = '%s stopped streaming.' % (channel['name'])
                        self.setCache("lastly")

        return (True, "All resources updated for %s" % userNick)

    # background worker only
    def updateAllUserResources(self, logger = None):
        if not logger:
            logger = self.log

        okCount = 0
        nokCount = 0
        lastToken = ""
        for link in self.getNetworkLinks():
            logger.debug("[%s] Updating user resources for userid %s" % (self.handle, link['user_id']))
            if link['network_data'] and int(link['user_id']):
                (ret, message) = self.updateUserResources(int(link['user_id']), link['network_data'], logger)
                #dirty hack!
                lastToken = link['network_data']
                if ret:
                    okCount += 1
                    # newlastlyCheck.append(message)
                else:
                    nokCount += 1
            else:
                nokCount += 1

        if lastToken:
            for sysChan in self.config['siteChannel']:
                logger.debug("[%s] Updating system channel %s" % (self.handle, sysChan))
                (ret, message) = self.updateUserResources(sysChan, lastToken, logger)
                if ret:
                    okCount += 1
                else:
                    nokCount += 1
        else:
            logger.warning("[%s] Unable to update streams becuase no token was found." % (self.handle))

        return "%s user resources updated, %s ignored" % (okCount, nokCount)

    def devTest(self):
        ret = []
        ret.append("netLinks: %s" % self.getSessionValue(self.linkIdName))
        ret.append("updateUserResources: %s" % self.updateUserResources())
        return '\n'.join(ret)

    # Dashbord boxes
    def dashboard_channels(self, request):
        self.log.debug("[%s] Dashboard channels" % (self.handle))
        self.getCache("channels")
        self.getCache("streams")

        channelsWithLink = {}
        for chan in self.cache['channels'].keys():
            channelsWithLink[chan] = self.cache['channels'][chan]
            channelsWithLink[chan]['detailLink'] = url_for('partner_details', netHandle=self.handle, partnerId=chan)
            channelsWithLink[chan]['mmoUserName'] = self.getUserById(chan).nick
            channelsWithLink[chan].pop('stream_key', None)
        return { 'channels': channelsWithLink, 'streams': self.cache['streams'] }
