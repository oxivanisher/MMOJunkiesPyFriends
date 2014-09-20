#!/usr/bin/env python
# -*- coding: utf-8 -*-

# http://support.mashery.com/docs/read/mashery_api/20/Samples
# https://github.com/litl/rauth

import logging
# import socket
import time
import os
import random
import json
import requests

# import urllib2
# import urllib
# import re

from flask import current_app
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

class BlizzNetwork(MMONetwork):

    def __init__(self, app, session, handle):
        super(BlizzNetwork, self).__init__(app, session, handle)

        self.description = "Battle.Net from Blizzard Entertainment"
        self.setLogLevel(logging.DEBUG)
        self.battleNet = None
        self.baseUrl = 'https://%s.api.battle.net' % self.config['region']

        self.blizzWowDataResourcesList = {
            'battlegroups': "/wow/data/battlegroups/",
            'character_races': "/wow/data/character/races",
            'character_classes': "/wow/data/character/classes",
            'character_achievements': "/wow/data/character/achievements",
            'guild_rewards': "/wow/data/guild/rewards",
            'guild_perks': "/wow/data/guild/perks",
            'guild_achievments': "/wow/data/guild/achievments",
            'item_classes': "/wow/data/item/classes",
            'talents': "/wow/data/talents",
            'pet_types': "/wow/data/pet/types"
        }
        self.blizzWowDataResources = {}

    # overwritten class methods
    def getLinkHtml(self):
        self.log.debug("Show linkHtml %s" % self.name)

        htmlFields = {}
        if not self.getSessionValue(self.linkIdName):
            htmlFields['link'] = {'comment': "Click to login with Battle.Net.",
                                  'image': "//%s.battle.net/mashery-assets/static/images/bnet-logo.png" % self.config['region'],
                                  'url': self.requestAuthorizationUrl()}
        return htmlFields

    # Oauth2 helper
    def requestAuthorizationUrl(self):
        self.log.debug("Generating Authorization Url")
        self.battleNet = OAuth2Service(
            base_url=self.baseUrl,
            client_id=self.config['apikey'],
            client_secret=self.config['apisecret'],
            authorize_url='https://%s.battle.net/oauth/authorize' % self.config['region'],
            access_token_url='https://%s.battle.net/oauth/token' % self.config['region'])
        # params = {'redirect_uri': 'https://dev.battle.net/',
        params = {'redirect_uri': 'https://localhost:5000/Network/Oauth2/Login/Blizz',
                  'response_type': 'code'}
        return self.battleNet.get_authorize_url(**params)

    def requestAccessToken(self, code):
        self.log.debug("Requesting Access Token")

        data = {'redirect_uri': 'https://localhost:5000/Network/Oauth2/Login/Blizz',
                'scope': 'wow.profile sc2.profile',
                'grant_type': 'authorization_code',
                'code': code}

        access_token = self.battleNet.get_access_token(decoder = json.loads, data=data)
        self.log.debug("Oauth2 Login successful, recieved new access_token")
        self.saveLink(access_token)
        self.setSessionValue(self.linkIdName, access_token)

        result, data = self.queryBlizzardApi('/account/user/battletag')
        return data['battletag']

    # Query Blizzard
    def queryBlizzardApi(self, what):
        payload = {'access_token': self.getSessionValue(self.linkIdName),
                   'apikey': self.config['apikey'],
                   'locale': 'en_US'}

        self.log.debug("Checking for missing Blizzard Wow Data Resources.")
        for entry in self.blizzWowDataResourcesList.keys():
            if len(self.blizzWowDataResourcesList[entry]) == 0:
                location = self.baseUrl + self.blizzWowDataResourcesList[entry]
                self.log.debug("Fetching %s from %s" % (entry, location))
                self.blizzWowDataResources[entry] = requests.get(location, params=payload).json()
           
        self.log.debug("Query Blizzard API for %s" % what)
        r = requests.get(self.baseUrl + what, params=payload).json()
        
        try:
            if r['code'] == 403:
                link = db.session.query(MMONetLink).filter_by(network_handle=self.handle, network_data=self.getSessionValue(self.linkIdName)).first()
                self.unlink(self.session['userid'], link.id)
                return (False, r['detail'])
        except KeyError:
            pass

        return (True, r)

    # def cacheFile(self, url):
    #     outputFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../static/cache', url.split('/')[-1])

    #     if os.path.isfile(outputFilePath):
    #         self.log.debug("Not downloading %s" % url)
    #     else:
    #         self.log.info("Downloading %s" % url)

    #         avatarFile = urllib.URLopener()
    #         avatarFile.retrieve(url, outputFilePath)
    #     return True


    #     self.log.debug("No code found")
    #     return (False, oid.try_login('https://%s.battle.net/oauth/authorize' % self.config['region']))

    def devTest(self):
        ret = []
        respv, respt = self.queryBlizzardApi('/account/user/battletag')
        if respv:
            response = respt['battletag']
        else:
            response = "Error: %s" % respt
        ret.append("Battletag: %s" + response)

        respv, respt = self.queryBlizzardApi('/wow/user/characters')
        if respv:
            response = str(respt)
        else:
            response = "Error: %s" % respt
        ret.append("Profile Data:\n%s" % response)

        for entry in self.blizzWowDataResources.keys():
            ret.append("\n%s %s:\n%s" % (entry, len(self.blizzWowDataResources[entry]), self.blizzWowDataResources[entry]))

        ret.append("access_token: %s" % self.getSessionValue(self.linkIdName))
        return '\n'.join(ret)

    # def getPartners(self):
    #     self.log.debug("List all partners for given user")
    #     if not self.getSessionValue(self.linkIdName):
    #         return (False, False)
    #     result = []
    #     try:
    #         for friend in self.getSteamUser(self.getSessionValue(self.linkIdName)).friends:
    #             self.cacheFile(friend.avatar)
    #             self.cacheFile(friend.avatar_full)
    #             friendImgs = []
    #             try:
    #                 friendImgs.append({
    #                                 'type': 'flag',
    #                                 'name': friend.country_code.lower(),
    #                                 'title': friend.country_code
    #                                 })
    #             except Exception:
    #                 pass

    #             friendImgs.append({
    #                                 'type': 'cache',
    #                                 'name': friend.avatar.split('/')[-1],
    #                                 'title': friend.real_name
    #                             })


    #             result.append({ 'id': friend.code,
    #                             'nick': friend.name,
    #                             'state': friend.state,
    #                             # 'state': OnlineState(friend.state),
    #                             'netHandle': self.handle,
    #                             'networkText': self.name,
    #                             'networkImgs': [{
    #                                 'type': 'network',
    #                                 'name': self.handle,
    #                                 'title': self.name
    #                             }],
    #                             'friendImgs': friendImgs
    #                         })
    #         return (True, result)
    #     except Exception as e:
    #         self.log.warning("Unable to connect to Steam Network: %s" % e)
    #         return (False, "Unable to connect to Steam Network: %s" % e)

    # def getPartnerDetails(self, partnerId):
    #     self.log.debug("List partner details")
    #     steam_user = self.getSteamUser(partnerId)
    #     moreInfo = {}

    #     avatar = steam_user.avatar_full.split('/')[-1]

    #     self.setPartnerAvatar(moreInfo, avatar)

    #     self.setPartnerDetail(moreInfo, "Country Code", steam_user.country_code)
    #     # self.setPartnerDetail(moreInfo, "Created", steam_user.time_created)
    #     self.setPartnerDetail(moreInfo, "Last Logoff", steam_user.last_logoff)
    #     self.setPartnerDetail(moreInfo, "Profile URL", steam_user.profile_url)
    #     self.setPartnerDetail(moreInfo, "Online/Offline", steam_user.state)
    #     self.setPartnerDetail(moreInfo, "Level", steam_user.level)
    #     self.setPartnerDetail(moreInfo, "XP", steam_user.xp)
    #     # self.setPartnerDetail(moreInfo, "Badges", steam_user.badges)

    #     recent = []
    #     for game in steam_user.recently_played:
    #         recent.append(game.name)
    #     self.setPartnerDetail(moreInfo, "Recently Played", ', '.join(recent))
        
    #     games = []
    #     for game in steam_user.games:
    #         games.append(game.name)
    #     self.setPartnerDetail(moreInfo, "Games", ', '.join(games))
        
    #     # self.setPartnerDetail(moreInfo, "Owned Games", steam_user.owned_games)


    #     if steam_user.group:
    #         self.setPartnerDetail(moreInfo, "Primary Group", steam_user.group.guid)

    #     # groups = []
    #     # for group in steam_user.groups:
    #     #     group.append(group.guid)
    #     # self.setPartnerDetail(moreInfo, "Groups", ', '.join(groups))

    #     if steam_user.currently_playing:
    #         self.setPartnerDetail(moreInfo, "Currently Playing", steam_user.currently_playing.name)

    #     if self.session.get('admin'):
    #         self.setPartnerDetail(moreInfo, "Steam ID", steam_user.code)
    #         self.setPartnerDetail(moreInfo, "Real Name", steam_user.real_name)

    #     return moreInfo

    # # def setNetworkMoreInfo(self, moreInfo):
    # #     self.moreInfo = moreInfo

    # def admin(self):
    #     self.log.debug("Loading admin stuff")
