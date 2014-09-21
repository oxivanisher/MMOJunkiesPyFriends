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
import urllib

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
        self.avatarUrl = 'http://%s.battle.net/' % (self.config['region'])
        self.locale = 'en_US'

        # things to fetch from blizzard
        self.loadAllData()
        if len(self.dataResources) == 0:
            self.dataResources['battletags'] = {}

        self.wowDataResourcesList = {
            'battlegroups': "/wow/data/battlegroups/",
            'character_races': "/wow/data/character/races",
            'character_classes': "/wow/data/character/classes",
            'character_achievements': "/wow/data/character/achievements",
            'guild_rewards': "/wow/data/guild/rewards",
            'guild_perks': "/wow/data/guild/perks",
            'guild_achievements': "/wow/data/guild/achievements",
            'item_classes': "/wow/data/item/classes",
            'talents': "/wow/data/talents",
            'pet_types': "/wow/data/pet/types"
        }
        # self.wowDataResources = {}
        if len(self.wowDataResources) == 0:
            self.wowDataResources['user_characters'] = {}
        
        # self.d3DataResources = {}
        if len(self.d3DataResources) == 0:
            self.d3DataResources['profiles'] = {}

        # self.sc2DataResources = {}
        self.sc2DataResourcesList = {
            'achievements': "/sc2/data/achievements",
            'rewards': "/sc2/data/rewards"
        }
        if len(self.sc2DataResources) == 0:
            self.sc2DataResources['profiles'] = {}

    # save data to file!!
    def saveAllData(self):
        self.log.debug("Saving Battle.net data to files")
        saveJSON(self.handle, 'general', self.dataResources)
        saveJSON(self.handle, 'wow', self.wowDataResources)
        saveJSON(self.handle, 'd3', self.d3DataResources)
        saveJSON(self.handle, 'sc2', self.sc2DataResources)

    def loadAllData(self):
        self.log.debug("Loading Battle.net data from files")
        self.dataResources = loadJSON(self.handle, 'general', {})
        self.wowDataResources = loadJSON(self.handle, 'wow', {})
        self.d3DataResources = loadJSON(self.handle, 'd3', {})
        self.sc2DataResources = loadJSON(self.handle, 'sc2', {})

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
        params = {'redirect_uri': '%s/Network/Oauth2/Login/Blizz' % self.app.config['WEBURL'],
                  'response_type': 'code'}
        return self.battleNet.get_authorize_url(**params)

    def requestAccessToken(self, code):
        if not self.battleNet:
            self.requestAuthorizationUrl()
        self.log.debug("Requesting Access Token")

        data = {'redirect_uri': '%s/Network/Oauth2/Login/Blizz' % self.app.config['WEBURL'],
                'scope': 'wow.profile sc2.profile',
                'grant_type': 'authorization_code',
                'code': code}

        access_token = self.battleNet.get_access_token(decoder = json.loads, data=data)
        self.log.debug("Oauth2 Login successful, recieved new access_token")
        self.saveLink(access_token)
        self.setSessionValue(self.linkIdName, access_token)

        # fetching battle tag
        if 'battletags' not in self.dataResources:
            self.dataResources['battletags'] = {}
        self.updateResource(self.dataResources['battletags'], self.session['userid'], '/account/user/battletag')
        
        # fetching wow chars
        if 'profiles' not in self.wowDataResources:
            self.wowDataResources['profiles'] = {}
        self.updateResource(self.wowDataResources['profiles'], self.session['userid'], '/wow/user/characters')

        # fetching d3 profile
        if 'profiles' not in self.d3DataResources:
            self.d3DataResources['profiles'] = {}
        self.updateResource(self.d3DataResources['profiles'],
                            self.session['userid'],
                            '/d3/profile/%s/' % self.dataResources['battletags'][self.session['userid']]['battletag'].replace('#', '-'))

        # fetching sc2 
        if 'profiles' not in self.sc2DataResources:
            self.sc2DataResources['profiles'] = {}
        self.updateResource(self.sc2DataResources['profiles'], self.session['userid'], '/sc2/profile/user')

        self.saveAllData()
        return self.dataResources['battletags'][self.session['userid']]['battletag']

    # Query Blizzard
    def queryBlizzardApi(self, what):
        if not self.battleNet:
            self.requestAuthorizationUrl()
        payload = {'access_token': self.getSessionValue(self.linkIdName),
                   'apikey': self.config['apikey'],
                   'locale': self.locale}

        for entry in self.wowDataResourcesList.keys():
            self.updateResource(self.wowDataResources, entry, self.wowDataResourcesList[entry])

        for entry in self.sc2DataResourcesList.keys():
            self.updateResource(self.sc2DataResources, entry, self.sc2DataResourcesList[entry])

        self.log.debug("Query Blizzard API for %s" % what)
        r = requests.get(self.baseUrl + what, params=payload).json()
        
        try:
            if r['code'] == 403:
                link = db.session.query(MMONetLink).filter_by(network_handle=self.handle, network_data=self.getSessionValue(self.linkIdName)).first()
                self.unlink(self.session['userid'], link.id)
                return (False, r['detail'])
        except KeyError:
            pass

        self.saveAllData()
        return (True, r)

    def updateResource(self, resource, entry, location):
        payload = {'access_token': self.getSessionValue(self.linkIdName),
                   'apikey': self.config['apikey'],
                   'locale': self.locale}
        if entry not in resource or resource[entry]['mmolastupdate'] < (time.time() - self.config['updateLock'] - random.randint(1, 300)):
            self.log.debug("Fetching %s from %s" % (entry, location))
            resource[entry] = requests.get(self.baseUrl + location, params=payload).json()
            resource[entry]['mmolastupdate'] = int(time.time())

    def cacheAvatarFile(self, origUrl, race, gender):
        avatarUrl = None

        # missing (oxivanisher)
        # api: internal-record-3679/184/109895608-avatar.jpg
        # http://eu.battle.net/static-render/eu/internal-record-3679/184/109895608-avatar.jpg?alt=wow/static/images/2d/avatar/4-0.jpg
        # to
        # http://eu.battle.net/wow/static/images/2d/avatar/4-0.jpg

        # existing (cernunnos)
        # api: thrall/156/74806172-avatar.jpg
        # http://eu.battle.net/static-render/eu/thrall/156/74806172-avatar.jpg
        # http://eu.battle.net/static-render/eu/thrall/156/74806172-avatar.jpg?alt=wow/static/images/2d/avatar/6-0.jpg
          # http://eu.battle.net/static-render/eu/azshara/56/94830136-avatar.jpg?alt=wow/static/images/2d/avatar/2-0.jpg

        # FIXME against bug http://us.battle.net/en/forum/topic/14525622754 !
        if 'internal-record' in origUrl or 'azshara' in origUrl or 'arthas' in origUrl or 'dethecus' in origUrl:
            # http://eu.battle.net/wow/static/images/2d/avatar/4-0.jpg
            tmpUrl = 'wow/static/images/2d/avatar/%s-%s.jpg' % (race, gender)
            savePath = tmpUrl.replace('/', '-')
            avatarUrl = self.avatarUrl + tmpUrl
            self.log.debug("Found non existing avatar url")

        else:
            savePath = origUrl.replace('/', '-')
            avatarUrl = self.avatarUrl + 'static-render/%s/' % self.config['region'] + origUrl
            self.log.debug("Downloading existing avatar url")

        outputFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../static/cache', savePath)
        if os.path.isfile(outputFilePath):
            self.log.debug("Not downloading %s, it already exists" % savePath)
        else:
            self.log.info("Downloading %s to %s" % (avatarUrl, savePath))
            avatarFile = urllib.URLopener()
            try:
                avatarFile.retrieve(avatarUrl, outputFilePath)
            except Exception:
                self.log.warning("Not existing avatar (BUG: http://us.battle.net/en/forum/topic/14525622754)! Force fetching general avatar.")
                savePath = self.cacheAvatarFile('internal-record', race, gender)

        return savePath

    def devTest(self):
        ret = []

        for userid in self.sc2DataResources['profiles'].keys():
            for character in self.sc2DataResources['profiles'][userid]['characters']:
                print "userid", userid
                # ret.append(str(self.sc2DataResources['profiles'][userid][character]['avatar']['url']))
                print "url", character['avatar']['url']
                # ret.append(str(self.sc2DataResources['profiles'][userid][character]['displayName']))
                print "displayName", character['displayName']
        ret.append(str(self.sc2DataResources['profiles']))

        # for userid in self.wowDataResources['profiles'].keys():
        #     ret.append("userid: %s" % userid)
        #     for char in self.wowDataResources['profiles'][userid]['characters']:
        #         # avUrl = self.avatarUrl + 'static-render/%s/' % self.config['region'] + char['thumbnail']
        #         ret.append(" - char: %s <img src='%s' />" % (char['name'], self.cacheAvatarFile(char['thumbnail'], char['race'], char['gender'])))
        #         # ret.append(" - thumbnail: %s" % (self.avatarUrl + char['thumbnail']))

        # respv, respt = self.queryBlizzardApi('/account/user/battletag')
        # if respv:
        #     response = respt['battletag']
        # else:
        #     response = "Error: %s" % respt
        # ret.append("Battletag: %s" + response)

        # respv, respt = self.queryBlizzardApi('/wow/user/characters')
        # if respv:
        #     response = str(respt)
        # else:
        #     response = "Error: %s" % respt
        # ret.append("Profile Data:\n%s" % response)

        # for entry in self.wowDataResources.keys():
        #     ret.append("\n%s %s:\n%s" % (entry, len(self.wowDataResources[entry]), self.wowDataResources[entry]))

        # ret.append("access_token: %s" % self.getSessionValue(self.linkIdName))
        return '\n'.join(ret)

    def getPartners(self):
        self.log.debug("List all partners for given user")
        if not self.getSessionValue(self.linkIdName):
            return (False, False)
        result = []

        try:
            # FIXME exclude myself ...
            for userid in self.wowDataResources['profiles'].keys():
                friendImgs = []
                product = 'World of Warcraft'
                for char in self.wowDataResources['profiles'][userid]['characters']:
                    # avUrl = self.avatarUrl + 'static-render/%s/' % self.config['region'] + char['thumbnail']
                    friendImgs.append({
                                        'type': 'cache',
                                        'name': self.cacheAvatarFile(char['thumbnail'], char['race'], char['gender']),
                                        'title': char['name'] + '@' + char['realm']
                                    })

                result.append({ 'id': userid,
                                'nick': self.dataResources['battletags'][userid]['battletag'],
                                'state': 'bla bla',
                                # 'state': OnlineState(friend.state),
                                'netHandle': self.handle,
                                'networkText': product,
                                'networkImgs': [{
                                    'type': 'network',
                                    'name': self.handle,
                                    'title': self.name
                                },{
                                    'type': 'product',
                                    'name': 'worldofwarcraft',
                                    'title': product
                                }],
                                'friendImgs': friendImgs
                            })

                friendImgs = []
                product = 'Starcraft 2'
                for userid in self.sc2DataResources['profiles']:
                    for character in self.sc2DataResources['profiles'][userid]['characters']:
                        # avUrl = self.avatarUrl + 'static-render/%s/' % self.config['region'] + char['thumbnail']
                        friendImgs.append({
                                            'type': 'cache',
                                            'name': self.cacheFile(character['avatar']['url']),
                                            'title': "[%s] %s" % (character['clanTag'], character['displayName'])
                                        })

                result.append({ 'id': userid,
                                'nick': self.dataResources['battletags'][userid]['battletag'],
                                'state': 'bla bla',
                                # 'state': OnlineState(friend.state),
                                'netHandle': self.handle,
                                'networkText': product,
                                'networkImgs': [{
                                    'type': 'network',
                                    'name': self.handle,
                                    'title': self.name
                                },{
                                    'type': 'product',
                                    'name': 'starcraft2',
                                    'title': product
                                }],
                                'friendImgs': friendImgs
                            })


            return (True, result)
        except Exception as e:
            self.log.warning("Unable to connect to Network: %s" % e)
            return (False, "Unable to connect to Network: %s" % e)

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
