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
        # self.battleNet = None
        self.baseUrl = 'https://%s.api.battle.net' % self.config['region']
        self.avatarUrl = 'http://%s.battle.net/' % (self.config['region'])
        self.locale = 'en_US'

        # things to fetch from blizzard

        # load caches
        # self.getCache('battletags')
        # self.getCache('wowProfiles')
        # self.getCache('d3Profiles')
        # self.getCache('sc2Profiles')

        # if 'user_characters' not in self.cache['wowDataResources'].keys():
        #     self.cache['wowDataResources']['user_characters'] = {}

        # if 'profiles' not in self.cache['d3DataResources'].keys():
        #     self.cache['d3DataResources']['profiles'] = {}

        # if 'profiles' not in self.cache['sc2DataResources'].keys():
        #     self.cache['sc2DataResources']['profiles'] = {}

        # self.loadAllData()
        # if len(self.dataResources) == 0:
        #     self.dataResources['battletags'] = {}

        self.wowDataResourcesList = {
            'wowBattlegroups': "/wow/data/battlegroups/",
            'wowCharacter_races': "/wow/data/character/races",
            'wowCharacter_classes': "/wow/data/character/classes",
            'wowCharacter_achievements': "/wow/data/character/achievements",
            'wowGuild_rewards': "/wow/data/guild/rewards",
            'wowGuild_perks': "/wow/data/guild/perks",
            'wowGuild_achievements': "/wow/data/guild/achievements",
            'wowItem_classes': "/wow/data/item/classes",
            'wowTalents': "/wow/data/talents",
            'wowPettypes': "/wow/data/pet/types"
        }
        # self.wowDataResources = {}
        # if len(self.wowDataResources) == 0:
        #     self.wowDataResources['user_characters'] = {}
        
        # self.d3DataResources = {}
        # if len(self.d3DataResources) == 0:
        #     self.d3DataResources['profiles'] = {}

        # self.sc2DataResources = {}
        self.sc2DataResourcesList = {
            'sc2achievements': "/sc2/data/achievements",
            'sc2rewards': "/sc2/data/rewards"
        }
        # if len(self.sc2DataResources) == 0:
        #     self.sc2DataResources['profiles'] = {}

        # admin methods
        self.adminMethods.append((self.updateBaseResources, 'Recache base resources'))
        self.adminMethods.append((self.updateUserResources, 'Recache (your) user resources'))

        # setup batttleNet service
        self.battleNet = OAuth2Service(
            client_id=self.config['apikey'],
            client_secret=self.config['apisecret'],
            authorize_url='https://%s.battle.net/oauth/authorize' % self.config['region'],
            access_token_url='https://%s.battle.net/oauth/token' % self.config['region'])

    # save data to file!!
    # def saveAllData(self):
    #     self.log.debug("Saving Battle.net data to files")
    #     saveJSON(self.handle, 'general', self.dataResources)
    #     saveJSON(self.handle, 'wow', self.wowDataResources)
    #     saveJSON(self.handle, 'd3', self.d3DataResources)
    #     saveJSON(self.handle, 'sc2', self.sc2DataResources)

    # def loadAllData(self):
    #     self.log.debug("Loading Battle.net data from files")
    #     self.dataResources = loadJSON(self.handle, 'general', {})
    #     self.wowDataResources = loadJSON(self.handle, 'wow', {})
    #     self.d3DataResources = loadJSON(self.handle, 'd3', {})
    #     self.sc2DataResources = loadJSON(self.handle, 'sc2', {})

    # overwritten class methods
    def getLinkHtml(self):
        self.log.debug("Show linkHtml %s" % self.name)
        htmlFields = {}
        if not self.getSessionValue(self.linkIdName):
            htmlFields['link'] = {'comment': "Click to login with Battle.Net.",
                                  'image': "//%s.battle.net/mashery-assets/static/images/bnet-logo.png" % self.config['region'],
                                  'url': self.requestAuthorizationUrl()}
        # print "url", self.requestAuthorizationUrl()
        return htmlFields

    # Oauth2 helper
    def requestAuthorizationUrl(self):
        self.log.debug("%s is requesting the Authorization URL (Step 1/3)" % self.session['nick'])
        params = {'redirect_uri': '%s/Network/Oauth2/Login/Blizz' % self.app.config['WEBURL'],
                  'scope': 'wow.profile sc2.profile',
                  'response_type': 'code'}
        self.log.debug("Generating Authorization Url")
        return self.battleNet.get_authorize_url(**params)

    def requestAccessToken(self, code):
        # if not self.battleNet:
        #     self.requestAuthorizationUrl()
        self.log.debug("%s is requesting a Access Token (Step 2/3)" % self.session['nick'])

        data = {'redirect_uri': '%s/Network/Oauth2/Login/Blizz' % self.app.config['WEBURL'],
                'scope': 'wow.profile sc2.profile',
                'grant_type': 'authorization_code',
                'code': code}

        access_token = self.battleNet.get_access_token(decoder = json.loads, data=data)
        # print "access_token", access_token
        self.log.debug("Oauth2 Login successful, recieved new access_token (Step 3/3)")
        self.saveLink(access_token)
        self.setSessionValue(self.linkIdName, access_token)
        self.updateBaseResources(False)
        self.updateUserResources()
        return self.cache['battletags'][self.session['userid']]

    # update resource helpers
    def updateBaseResources(self, force = True):
        if force:
            for entry in self.wowDataResourcesList.keys():
                # self.wowDataResources[entry]['mmolastupdate'] = 0
                self.cache[entry]['mmolastupdate'] = 0

            for entry in self.sc2DataResourcesList.keys():
                # self.sc2DataResources[entry]['mmolastupdate'] = 0
                self.cache[entry]['mmolastupdate'] = 0

        for entry in self.wowDataResourcesList.keys():
            # self.updateResource(self.wowDataResources, entry, self.wowDataResourcesList[entry])
            self.updateResource(entry, self.wowDataResourcesList[entry])

        for entry in self.sc2DataResourcesList.keys():
            # self.updateResource(self.sc2DataResources, entry, self.sc2DataResourcesList[entry])
            self.updateResource(entry, self.sc2DataResourcesList[entry])

        # self.saveAllData()
        return (True, "All resources updated")

    def updateUserResources(self):
        # fetching battle tag
        self.getCache('battletags')
        # print "battletags", self.cache['battletags']
        # if 'battletags' not in self.dataResources.keys():
            # self.dataResources['battletags'][self.session['userid']] = {}
        # (retValue, retMessage) = self.updateResource('battletags', self.session['userid'], '/account/user/battletag')
        (retValue, retMessage) = self.queryBlizzardApi('/account/user/battletag')
        # print "battletags", self.cache['battletags']
        if not retValue:
            return (False, retMessage)
        self.cache['battletags'][self.session['userid']] = retMessage['battletag']
        self.setCache('battletags')


        # fetching wow chars
        # if 'user_characters' not in self.wowDataResources.keys():
        #     self.wowDataResources['user_characters'] = {}
        #     self.wowDataResources['user_characters'][self.session['userid']]['mmolastupdate'] = 0
        # (retValue, retMessage) = self.updateResource(self.wowDataResources['user_characters'], self.session['userid'], '/wow/user/characters')
        self.getCache('wowProfiles')
        (retValue, retMessage) = self.queryBlizzardApi('/wow/user/characters')
        if not retValue:
            return (False, retMessage)
        # if 'user_characters' not in self.cache['wowDataResources'].keys():
        #     self.cache['wowDataResources']['user_characters'] = {}
        # self.cache['wowDataResources']['user_characters'][self.session['userid']] = retMessage
        self.cache['wowProfiles'][self.session['userid']] = retMessage
        self.setCache('wowProfiles')

        # fetching d3 profile
        # if 'profiles' not in self.d3DataResources.keys():
        #     self.d3DataResources['profiles'] = {}
        #     self.d3DataResources['profiles'][self.session['userid']]['mmolastupdate'] = 0
        #     (retValue, retMessage) = self.updateResource(self.d3DataResources['profiles'],
        #                     self.session['userid'],
        #                     '/d3/profile/%s/' % self.dataResources['battletags'][self.session['userid']]['battletag'].replace('#', '-'))
        self.getCache('d3Profiles')
        (retValue, retMessage) = self.queryBlizzardApi('/d3/profile/%s/' % self.cache['battletags'][self.session['userid']].replace('#', '-'))
        if not retValue:
            return (False, retMessage)
        # if 'profiles' not in self.cache['d3DataResources'].keys():
        #     self.cache['d3DataResources']['profiles'] = {}
        # self.cache['d3Profiles']['profiles'][self.session['userid']] = retMessage
        self.cache['d3Profiles'][self.session['userid']] = retMessage
        self.setCache('d3Profiles')

        # fetching sc2
        # if 'profiles' not in self.sc2DataResources.keys():
        #     self.sc2DataResources['profiles'] = {}
        #     self.sc2DataResources['profiles'][self.session['userid']]['mmolastupdate'] = 0
        # (retValue, retMessage) = self.updateResource(self.sc2DataResources['profiles'], self.session['userid'], '/sc2/profile/user')
        self.getCache('sc2Profiles')
        (retValue, retMessage) = self.queryBlizzardApi('/sc2/profile/user')
        if not retValue:
            return (False, retMessage)
        # if 'profiles' not in self.cache['sc2DataResources'].keys():
        #     self.cache['sc2DataResources']['profiles'] = {}
        # self.cache['sc2DataResources']['profiles'][self.session['userid']] = retMessage
        self.cache['sc2Profiles'][self.session['userid']] = retMessage
        self.setCache('sc2Profiles')

        # self.saveAllData()
        return (True, "All resources updated")

    def updateResource(self, entry, location):
        self.log.debug("Updating resource from %s" % (location))
        self.getCache(entry)
        if 'mmolastupdate' not in self.cache[entry] or self.cache[entry]['mmolastupdate'] < (time.time() - self.config['updateLock'] - random.randint(1, 300)):
            (resValue, resData)  = self.queryBlizzardApi(location)
            if resValue:
                self.cache[entry] = resData
                self.cache[entry]['mmolastupdate'] = int(time.time())
                self.setCache(entry)
                self.log.debug("Fetched %s from %s with %s result length" % (entry, location, len(resData)))
            else:
                self.log.warning("Unable to update resource from %s because: %s" % (location, resData))
                return (False, resData)
        return (True, "Resource updated from %s" % location)

    # def updateResource(self, resource, entry, location):
    #     self.log.debug("Updating resource from %s" % (location))
    #     if entry not in resource or resource[entry]['mmolastupdate'] < (time.time() - self.config['updateLock'] - random.randint(1, 300)):
    #         (resValue, resData)  = self.queryBlizzardApi(location)
    #         if resValue:
    #             resource[entry] = resData
    #             resource[entry]['mmolastupdate'] = int(time.time())
    #             self.log.debug("Fetched %s from %s with %s result length" % (entry, location, len(resource[entry])))
    #         else:
    #             self.log.warning("Unable to update resource from %s because: %s" % (location, resData))
    #             return (False, resData)
    #     return (True, "Resource updated from %s" % location)

    # Query Blizzard
    def queryBlizzardApi(self, what):
        self.log.debug("Query Blizzard API for %s" % what)
        payload = {'access_token': self.getSessionValue(self.linkIdName),
                   'apikey': self.config['apikey'],
                   'locale': self.locale}
        r = requests.get(self.baseUrl + what, params=payload).json()
     
        try:
            if r['code']:
                link = db.session.query(MMONetLink).filter_by(network_handle=self.handle, network_data=self.getSessionValue(self.linkIdName)).first()
                # self.unlink(self.session['userid'], link.id)
                self.log.debug("queryBlizzardApi found code: %s" % r['code'])
                self.requestAuthorizationUrl()
                return (False, "<a href='%s'>Please reauthorize this page.</a>" % self.requestAuthorizationUrl())
                return (False, r['detail'])
            elif 'error' in r.keys():
                self.log.debug("queryBlizzardApi found error: %s" % r['error_description'])
                return (False, r['error_description'])
        except KeyError:
            pass
        except Exception as e:
            self.log.warning("Please handle exception %s on in queryBlizzardApi!" % e)

        # self.saveAllData()
        return (True, r)

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
        # FIXME bug 2 http://us.battle.net/en/forum/topic/14525912884 !
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

        self.getCache('battletags')

        try:
            # FIXME exclude myself ...
            self.getCache('wowProfiles')
            for userid in self.cache['wowProfiles'].keys():
                friendImgs = []
                product = 'World of Warcraft'
                for char in self.cache['wowProfiles'][userid]['characters']:
                    # avUrl = self.avatarUrl + 'static-render/%s/' % self.config['region'] + char['thumbnail']
                    friendImgs.append({
                                        'type': 'cache',
                                        'name': self.cacheAvatarFile(char['thumbnail'], char['race'], char['gender']),
                                        'title': char['name'] + '@' + char['realm']
                                    })

                result.append({ 'id': userid,
                                'nick': self.cache['battletags'][userid],
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

                product = 'Starcraft 2'
                self.getCache('sc2Profiles')
                for userid in self.cache['sc2Profiles'].keys():
                    friendImgs = []
                    for character in self.cache['sc2Profiles'][userid]['characters']:
                        # avUrl = self.avatarUrl + 'static-render/%s/' % self.config['region'] + char['thumbnail']
                        print "character['avatar']['url']", character['avatar']['url']
                        friendImgs.append({
                                            'type': 'cache',
                                            'name': self.cacheFile(character['avatar']['url']),
                                            'title': "[%s] %s" % (character['clanTag'], character['displayName'])
                                        })

                    result.append({ 'id': userid,
                                    'nick': self.cache['battletags'][userid],
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
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            message = "Unable to connect to Network: %s %s %s:%s" % (exc_type, e, fname, exc_tb.tb_lineno )
            self.log.warning(message)
            return (False, message)

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
