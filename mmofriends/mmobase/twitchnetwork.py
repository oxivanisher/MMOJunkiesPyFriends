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
        # self.registerWorker(self.updateBaseResources, 10800)

        # dashboard boxes
        # self.registerDashboardBox(self.dashboard_liveStreams, 'liveStreams', {'title': 'Currently live','template': 'box_jQCloud.html'})

        # setup twitch service
        self.twitchApi = OAuth2Service(
            client_id=self.config['apikey'],
            client_secret=self.config['apisecret'],
            authorize_url='https://api.twitch.tv/kraken/oauth2/authorize')

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
        # if not self.twitchApi:
        #     self.requestAuthorizationUrl()
        self.log.debug("recieved code: %s" % code)
        self.log.debug("%s is requesting a Access Token (Step 2/3)" % self.session['nick'])

        data = {'redirect_uri': '%s/Network/Oauth2/Login/%s' % (self.app.config['WEBURL'], self.handle),
                'grant_type': 'authorization_code',
                'code': code}

        access_token = self.twitchApi.get_access_token(decoder = json.loads, data=data)
        self.log.debug("Oauth2 Login successful, recieved new access_token (Step 3/3)")
        self.saveLink(access_token)
        self.setSessionValue(self.linkIdName, access_token)
        # self.updateBaseResources(False)
        # self.updateUserResources()
        # return self.cache['battletags'][unicode(self.session['userid'])]
