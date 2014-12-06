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
from mmoutils import *
from mmouser import *
from mmonetwork import *
from mmofriends import db

try:
    from rauth.service import OAuth2Service
except ImportError:
    print "Please install rauth (https://github.com/litl/rauth)"
    import sys
    sys.exit(2)

class TwitchNetwork(MMONetwork):

    def __init__(self, app, session, handle):
        super(TwitchNetwork, self).__init__(app, session, handle)
        # activate debug while development
        self.setLogLevel(logging.DEBUG)

        # admin methods
        # self.adminMethods.append((self.updateBaseResources, 'Recache base resources'))

        # background updater methods
        self.registerWorker(self.updateAllUserResources, 60)

        # dashboard boxes
        self.registerDashboardBox(self.dashboard_channels, 'channels', {'title': 'Channels'})

        # setup twitch service
        self.baseUrl = 'https://api.twitch.tv/kraken'
        self.twitchApi = OAuth2Service(
            client_id=self.config['apikey'],
            client_secret=self.config['apisecret'],
            authorize_url='%s/oauth2/authorize' % self.baseUrl,
            access_token_url='%s/oauth2/token' % self.baseUrl)

    # overwritten class methods
    def getLinkHtml(self):
        self.log.debug("Show linkHtml %s" % self.name)
        htmlFields = {}
        if not self.getSessionValue(self.linkIdName):
            htmlFields['link'] = {'comment': "Click to login with Twitch.tv.",
                                  'image': "",
                                  'url': self.requestAuthorizationUrl()}
        return htmlFields

    # Oauth2 helper
    def requestAuthorizationUrl(self):
        self.log.debug("%s is requesting the Authorization URL (Step 1/3)" % self.session['nick'])
        params = {'redirect_uri': '%s/Network/Oauth2/Login/%s' % (self.app.config['WEBURL'], self.handle),
                  'scope': 'user_read channel_read',
                  'response_type': 'code'}
        self.log.debug("Generating Authorization Url")
        return self.twitchApi.get_authorize_url(**params)

    def requestAccessToken(self, code):
        self.log.debug("recieved code: %s" % code)
        self.log.debug("%s is requesting a Access Token (Step 2/3)" % self.session['nick'])

        data = {'redirect_uri': '%s/Network/Oauth2/Login/%s' % (self.app.config['WEBURL'], self.handle),
                'grant_type': 'authorization_code',
                'code': code}

        access_token = self.twitchApi.get_access_token(decoder = json.loads, data=data)
        self.log.debug("Oauth2 Login successful, recieved new access_token (Step 3/3)")
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
        r = requests.get(self.baseUrl + what, headers=headers).json()
        return (True, r)

    def updateUserResources(self, userid = None, accessToken = None, logger = None):
        if not logger:
            logger = self.log

        background = True
        if not userid:
            userid = self.session['userid']
            background = False
            logger.debug("[%s] Foreground updating the resources for userid %s" % (self.handle, self.getUserById(userid).nick))
        else:
            logger.debug("[%s] Background updating the resources for userid %s" % (self.handle, self.getUserById(userid).nick))
        userNick = self.getUserById(userid).nick

        if not accessToken:
            if userid != self.session['userid']:
                link = self.getNetworkLinks(userid)
                accessToken = link[0]['network_data']
            else:
                accessToken = self.getSessionValue(self.linkIdName)

        logger.debug("[%s] Fetching channel for %s" % (self.handle, userNick))
        self.getCache("channels")
        (ret, channel) = self.queryTwitchApi("/channel", accessToken)
        if ret and len(channel):
            if 'error' in channel.keys():
                logger.warning("[%s] Unable to fetch channel for %s: %s (%s)" % (self.handle, userNick, channel['error'], channel['message']))
                return (False, "Unable to update resources for %s: %s (%s)" % (userNick, channel['error'], channel['message']))
            self.cache['channels'][userid] = channel
            self.setCache("channels")
            logger.info("[%s] Fetched channel for %s" % (self.handle, userNick))
            if 'logo' in channel:
                if channel['logo']:
                    self.cacheFile(channel['logo'])
            if 'banner' in channel:
                if channel['banner']:
                    self.cacheFile(channel['banner'])
            if 'video_banner' in channel:
                if channel['video_banner']:
                    self.cacheFile(channel['video_banner'])

            logger.debug("[%s] Fetching stream for %s" % (self.handle, userNick))
            self.getCache("streams")
            (ret, stream) = self.queryTwitchApi("/streams/%s" % channel['name'], accessToken)
            if ret and len(stream):
                print stream
                if 'stream' in stream:
                    if 'preview' in stream['stream']:
                        stream['stream']['preview'] = stream['stream']['preview'].replace('http://', '//')
                if 'error' in channel.keys():
                    logger.warning("[%s] Unable to fetch stream for %s: %s (%s)" % (self.handle, userNick, stream['error'], stream['message']))
                    return (False, "Unable to update resources for %s: %s (%s)" % (userNick, stream['error'], stream['message']))
                self.cache['streams'][userid] = stream
                self.setCache("streams")
                logger.info("[%s] Fetched channel for %s" % (self.handle, userNick))

        return (True, "All resources updated for %s" % userNick)

    # background worker only
    def updateAllUserResources(self, logger = None):
        if not logger:
            logger = self.log

        okCount = 0
        nokCount = 0
        for link in self.getNetworkLinks():
            logger.debug("[%s] Updating user resources for userid %s" % (self.handle, link['user_id']))
            if link['network_data']:
                (ret, message) = self.updateUserResources(link['user_id'], link['network_data'], logger)
                if ret:
                    okCount += 1
                else:
                    nokCount += 1
            else:
                nokCount += 1
        return "%s user resources updated, %s ignored" % (okCount, nokCount)

    def devTest(self):
        ret = []
        ret.append("netLinks: %s" % self.getSessionValue(self.linkIdName))
        ret.append("updateUserResources: %s" % self.updateUserResources())
        return '\n'.join(ret)

    # Dashbord boxes
    def dashboard_channels(self, request):
        self.log.debug("Dashboard channels")
        self.getCache("channels")
        self.getCache("streams")
        return { 'channels': self.cache['channels'], 'streams': self.cache['streams'] }
