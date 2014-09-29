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
        self.baseUrl = 'https://%s.api.battle.net' % self.config['region']
        self.avatarUrl = 'http://%s.battle.net/' % (self.config['region'])
        self.locale = 'en_US'

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

        self.sc2DataResourcesList = {
            'sc2achievements': "/sc2/data/achievements",
            'sc2rewards': "/sc2/data/rewards"
        }

        # admin methods
        self.adminMethods.append((self.updateBaseResources, 'Recache base resources'))
        self.adminMethods.append((self.updateUserResources, 'Recache (your) user resources'))

        # setup batttleNet service
        self.battleNet = OAuth2Service(
            client_id=self.config['apikey'],
            client_secret=self.config['apisecret'],
            authorize_url='https://%s.battle.net/oauth/authorize' % self.config['region'],
            access_token_url='https://%s.battle.net/oauth/token' % self.config['region'])

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
                self.forceCacheUpdate(entry)

            for entry in self.sc2DataResourcesList.keys():
                self.forceCacheUpdate(entry)

        for entry in self.wowDataResourcesList.keys():
            self.updateResource(entry, self.wowDataResourcesList[entry])

        for entry in self.sc2DataResourcesList.keys():
            self.updateResource(entry, self.sc2DataResourcesList[entry])

        # self.saveAllData()
        return (True, "All resources updated")

    def updateUserResources(self):
        # fetching battle tag
        self.getCache('battletags')
        (retValue, retMessage) = self.queryBlizzardApi('/account/user/battletag')
        if not retValue:
            return (False, retMessage)
        self.cache['battletags'][self.session['userid']] = retMessage['battletag']
        self.setCache('battletags')

        # fetching wow chars
        self.getCache('wowProfiles')
        (retValue, retMessage) = self.queryBlizzardApi('/wow/user/characters')
        if not retValue:
            return (False, retMessage)
        self.cache['wowProfiles'][self.session['userid']] = retMessage
        self.setCache('wowProfiles')

        # fetching d3 profile
        self.getCache('d3Profiles')
        (retValue, retMessage) = self.queryBlizzardApi('/d3/profile/%s/' % self.cache['battletags'][self.session['userid']].replace('#', '-'))
        if not retValue:
            return (False, retMessage)
        self.cache['d3Profiles'][self.session['userid']] = retMessage
        self.setCache('d3Profiles')

        # fetching sc2
        self.getCache('sc2Profiles')
        (retValue, retMessage) = self.queryBlizzardApi('/sc2/profile/user')
        if not retValue:
            return (False, retMessage)
        self.cache['sc2Profiles'][self.session['userid']] = retMessage
        self.setCache('sc2Profiles')

        return (True, "All resources updated")

    def updateResource(self, entry, location):
        self.log.debug("Updating resource from %s" % (location))
        self.getCache(entry)
        if self.getCacheAge(entry) < self.config['updateLock'] - random.randint(1, 300):
            (resValue, resData)  = self.queryBlizzardApi(location)
            if resValue:
                self.cache[entry] = resData
                self.setCache(entry)
                self.log.debug("Fetched %s from %s with %s result length" % (entry, location, len(resData)))
            else:
                self.log.warning("Unable to update resource from %s because: %s" % (location, resData))
                return (False, resData)
        return (True, "Resource updated from %s" % location)

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

        self.getCache('battletags')
        self.getCache('wowProfiles')
        self.getCache('sc2Profiles')
        for userid in self.cache['wowProfiles'].keys():

            ret.append("WOW Account: %s" % self.cache['battletags'][userid])
            for char in self.cache['wowProfiles'][userid]['characters']:
                ret.append("    WOW Toon: %s@%s" % (char['name'], char['realm']))

            # ret.append("WOW Account: %s" % self.cache['battletags'][userid])
            # for char in self.cache['sc2Profiles'][userid]['characters']:
            #     ret.append("    SC2: %s" % (char['name']))

        print json.dumps(self.cache['sc2Profiles'])
        return '\n'.join(ret)

    def getBestWowChar(self, chars):
        achievmentPoints = -1
        preferedChars = []
        for char in chars:
            if char['achievementPoints'] > achievmentPoints:
                preferedChars = [char]
                achievmentPoints = char['achievementPoints']
            elif char['achievementPoints'] == achievmentPoints:
                preferedChars.append(char)

        level = -1
        finalChars = []
        for char in preferedChars:
            if char['level'] > level:
                finalChars = [char]
            elif char['level'] == level:
                finalChars.append(char)
        if len(finalChars) == 0:
            finalChars = preferedChars

        return finalChars

    def getPartners(self, **kwargs):
        self.log.debug("List all partners for given user")

        self.updateBaseResources(False)

        if not self.getSessionValue(self.linkIdName):
            return (False, False)
        result = []

        self.getCache('battletags')
        self.getCache('wowProfiles')
        self.getCache('sc2Profiles')
        self.getCache('d3Profiles')

        try:
            allLinks = self.getNetworkLinks()
            myNets = []
            friendImgs = []
            # FIXME exclude myself ...

            # Battle.net in general
            myProducts = [{ 'type': 'network',
                            'name': self.handle,
                            'title': self.name }]

            for userid in self.cache['battletags'].keys():
                linkId = self.cache['battletags'][userid]

                # World of warcraft
                if userid in self.cache['wowProfiles'].keys():
                    if self.cache['wowProfiles'][userid]['characters']:
                        myProducts.append({ 'type': 'product',
                                            'name': 'worldofwarcraft',
                                            'title': 'World of Warcraft' })

                        for char in self.getBestWowChar(self.cache['wowProfiles'][userid]['characters']):
                            friendImgs.append({ 'type': 'cache',
                                                'name': self.cacheAvatarFile(char['thumbnail'], char['race'], char['gender']),
                                                'title': char['name'] + '@' + char['realm'] })

                # Starcraft 2
                if userid in self.cache['sc2Profiles'].keys():
                    myProducts.append({ 'type': 'product',
                                        'name': 'starcraft2',
                                        'title': 'Starcraft 2' })
                    for character in self.cache['sc2Profiles'][userid]['characters']:
                        friendImgs.append({ 'type': 'cache',
                                            'name': self.cacheFile(character['avatar']['url']),
                                            'title': "[%s] %s" % (character['clanTag'], character['displayName']) })

                # Diablo 3
                if userid in self.cache['d3Profiles'].keys():
                    myProducts.append({ 'type': 'product',
                                        'name': 'diablo3',
                                        'title': 'Diablo 3' })
                    friendImgs.append({ 'type': 'product',
                                        'name': 'diablo3',
                                        'title': 'Diablo 3' })

                result.append({ 'id': linkId,
                                'mmoid': userid,
                                'nick': self.cache['battletags'][userid],
                                'state': 'bla bla',
                                'netHandle': self.handle,
                                'networkText': self.name,
                                'networkImgs': myProducts,
                                'friendImgs': friendImgs
                            })

            return (True, result)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            message = "Unable to connect to Network: %s %s %s:%s" % (exc_type, e, fname, exc_tb.tb_lineno )
            self.log.warning(message)
            return (False, message)

    def getPartnerDetails(self, battletag):
        self.log.debug("List partner details")
        moreInfo = {}

        self.getCache('battletags')
        self.getCache('wowProfiles')
        self.getCache('sc2Profiles')
        self.getCache('d3Profiles')

        for link in self.getNetworkLinks():
            if link['network_data'] == battletag:
                battletag = self.cache['battletags'][str(link['user_id'])]

        for userid in self.cache['battletags'].keys():
            if battletag == self.cache['battletags'][userid]:
                # Starcraft 2
                if userid in self.cache['sc2Profiles'].keys():
                    for char in self.cache['sc2Profiles'][userid]['characters']:
                        self.setPartnerDetail(moreInfo, "SC 2", "[%s] %s" % (char['clanTag'], char['displayName']))
                        self.setPartnerAvatar(moreInfo, self.cacheFile(char['avatar']['url']))

                # Diablo 3
                for hero in self.cache['d3Profiles'][userid]['heroes']:
                    self.setPartnerDetail(moreInfo, "D3", "%s lvl %s (%s)" % (hero['name'], hero['level'], hero['class']))

                # World of Warcraft
                if userid in self.cache['wowProfiles'].keys():
                    for char in self.cache['wowProfiles'][userid]['characters']:
                        self.setPartnerDetail(moreInfo, "WoW", "%s@%s: %s %s lvl: %s" % (char['name'],
                                                                                         char['realm'],
                                                                                         char['gender'],
                                                                                         char['race'],
                                                                                         char['level']))

                chars = self.getBestWowChar(self.cache['wowProfiles'][userid]['characters'])
                for char in chars:
                    self.setPartnerAvatar(moreInfo, self.cacheAvatarFile(char['thumbnail'], char['race'], char['gender']))
        
        return moreInfo

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
