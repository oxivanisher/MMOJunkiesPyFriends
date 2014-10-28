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
        self.baseUrl = 'https://%s.api.battle.net' % self.config['region']
        self.avatarUrl = 'http://%s.battle.net/' % (self.config['region'])
        self.locale = 'en_US'

        # activate debug while development
        # self.setLogLevel(logging.DEBUG)

        self.wowDataResourcesList = {
            'wowBattlegroups': "/wow/data/battlegroups/",
            'wowCharRaces': "/wow/data/character/races",
            'wowCharClasses': "/wow/data/character/classes",
            'wowCharAchievements': "/wow/data/character/achievements",
            'wowGuildRewards': "/wow/data/guild/rewards",
            'wowGuildPerks': "/wow/data/guild/perks",
            'wowGuildAchievements': "/wow/data/guild/achievements",
            'wowItemClasses': "/wow/data/item/classes",
            'wowTalents': "/wow/data/talents",
            'wowPettypes': "/wow/data/pet/types"
        }

        self.sc2DataResourcesList = {
            'sc2Achievements': "/sc2/data/achievements",
            'sc2Rewards': "/sc2/data/rewards"
        }

        # admin methods
        self.adminMethods.append((self.updateBaseResources, 'Recache base resources'))
        self.adminMethods.append((self.updateAllUserResources, 'Recache all user resources'))
        self.adminMethods.append((self.updateUserResources, 'Recache (your) user resources'))

        # background updater methods
        self.registerWorker(self.updateBaseResources, 10800)
        self.registerWorker(self.updateAllUserResources, 3600)

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
        # self.updateBaseResources(False)
        self.updateUserResources()
        return self.cache['battletags'][self.session['userid']]

    # update resource helpers
    def updateBaseResources(self, force = True):
        accessToken = False
        for link in self.getNetworkLinks():
            accessToken = link['network_data']

        for entry in self.wowDataResourcesList.keys():
            self.forceCacheUpdate(entry)

        for entry in self.sc2DataResourcesList.keys():
            self.forceCacheUpdate(entry)

        if accessToken:
            for entry in self.wowDataResourcesList.keys():
                self.updateResource(entry, self.wowDataResourcesList[entry], accessToken)

            for entry in self.sc2DataResourcesList.keys():
                self.updateResource(entry, self.sc2DataResourcesList[entry], accessToken)

        # self.saveAllData()
        return "All resources updated"

    def updateAllUserResources(self, logger = None):
        if not logger:
            logger = self.log
        self.getCache('battletags')

        for link in self.getNetworkLinks():
            logger.debug("Updating user resources for userid %s" % link['user_id'])
            self.updateUserResources(link['user_id'], link['network_data'])
        return (True, "All user resources updated")

    def updateUserResources(self, userid = None, accessToken = None, logger = None):
        if not logger:
            logger = self.log

        if not userid:
            userid = self.session['userid']
            userNick = userid
        logger.debug("Updating resources for userid %s" % userid)

        if not accessToken:
            if userid != self.session['userid']:
                link = self.getNetworkLinks(userid)
                accessToken = link[0]['network_data']
            else:
                accessToken = self.getSessionValue(self.linkIdName)

        # fetching battle tag
        (retValue, retMessage) = self.queryBlizzardApi('/account/user/battletag', accessToken)
        if retValue != False:
            self.getCache('battletags')
            if 'battletag' in retMessage:
                self.cache['battletags'][userid] = retMessage['battletag']
                self.setCache('battletags')
                userNick = retMessage['battletag']
            else:
                return (False, "Unable to update Battletag for user %s (%s)" % (userid, retMessage))

        # fetching wow chars
        (retValue, retMessage) = self.queryBlizzardApi('/wow/user/characters', accessToken)
        if retValue != False:
            self.getCache('wowProfiles')
            self.cache['wowProfiles'][userid] = retMessage
            self.setCache('wowProfiles')

        # fetching d3 profile
        (retValue, retMessage) = self.queryBlizzardApi('/d3/profile/%s/' % self.cache['battletags'][userid].replace('#', '-'), accessToken)
        if retValue != False:
            self.getCache('d3Profiles')
            self.cache['d3Profiles'][userid] = retMessage
            self.setCache('d3Profiles')

        # fetching sc2
        (retValue, retMessage) = self.queryBlizzardApi('/sc2/profile/user', accessToken)
        if retValue != False:
            self.getCache('sc2Profiles')
            self.cache['sc2Profiles'][userid] = retMessage
            self.setCache('sc2Profiles')

        return (True, "All resources updated for %s" % userNick)

    def updateResource(self, entry, location, accessToken = None):
        self.log.debug("Updating resource from %s" % (location))
        self.getCache(entry)
        # if self.getCacheAge(entry) < self.config['updateLock'] - random.randint(1, 300) or len(self.cache[entry]) == 0:
        (resValue, resData)  = self.queryBlizzardApi(location, accessToken)
        if resValue:
            self.cache[entry] = resData
            self.setCache(entry)
            self.log.debug("Fetched %s from %s with %s result length" % (entry, location, len(resData)))
            return (True, "Resource updated from %s" % location)
        else:
            self.log.warning("Unable to update resource from %s because: %s" % (location, resData))
            return (False, resData)

    # Query Blizzard
    def queryBlizzardApi(self, what, accessToken = None):
        self.log.debug("Query Blizzard API for %s" % what)
        if not accessToken:
            self.getSessionValue(self.linkIdName)

        payload = {'access_token': accessToken,
                   'apikey': self.config['apikey'],
                   'locale': self.locale}
        r = requests.get(self.baseUrl + what, params=payload).json()
     
        try:
            if r['code']:
                link = db.session.query(MMONetLink).filter_by(network_handle=self.handle, network_data=accessToken).first()
                # self.unlink(self.session['userid'], link.id)
                self.log.debug("queryBlizzardApi found code: %s" % r['code'])
                with self.app.test_request_context():
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

    def cacheWowAvatarFile(self, origUrl, race, gender):
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
                savePath = self.cacheWowAvatarFile('internal-record', race, gender)

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

        # self.updateBaseResources(False)
        # self.getCache('battletags')
        # if len(self.cache['battletags']) < len(self.getNetworkLinks()):
        #     self.log.info("Battletags missing in cache. Forced update initiated")
            # self.updateAllUserResources()

        if not self.getSessionValue(self.linkIdName):
            return (False, False)
        result = []

        self.getCache('battletags')
        self.getCache('wowProfiles')
        self.getCache('sc2Profiles')
        self.getCache('d3Profiles')

        try:
            allLinks = self.getNetworkLinks()
            for userid in self.cache['battletags'].keys():
                if str(userid) == str(self.session['userid']):
                    continue

                myProducts = [{ 'type': 'network',
                                'name': self.handle,
                                'title': self.name }]
                friendImgs = []
                linkId = self.cache['battletags'][userid]

                # World of warcraft
                if userid in self.cache['wowProfiles'].keys():
                    if self.cache['wowProfiles'][userid]['characters']:
                        try:
                            for char in self.getBestWowChar(self.cache['wowProfiles'][userid]['characters']):
                                friendImgs.append({ 'type': 'cache',
                                                    'name': self.cacheWowAvatarFile(char['thumbnail'], char['race'], char['gender']),
                                                    'title': char['name'] + '@' + char['realm'] })
                            myProducts.append({ 'type': 'product',
                                                'name': 'worldofwarcraft',
                                                'title': 'World of Warcraft' })
                        except KeyError:
                            pass


                # Starcraft 2
                if userid in self.cache['sc2Profiles'].keys():
                    try:
                        for character in self.cache['sc2Profiles'][userid]['characters']:
                            friendImgs.append({ 'type': 'cache',
                                                'name': self.cacheFile(character['avatar']['url']),
                                                'title': "[%s] %s" % (character['clanTag'], character['displayName']) })
                        myProducts.append({ 'type': 'product',
                                            'name': 'starcraft2',
                                            'title': 'Starcraft 2' })
                    except KeyError:
                        pass

                # Diablo 3 heroes
                if userid in self.cache['d3Profiles'].keys():
                    try:
                        if len(self.cache['d3Profiles'][userid]['heroes']) > 0:
                            myProducts.append({ 'type': 'product',
                                                'name': 'diablo3',
                                                'title': 'Diablo 3' })
                            # friendImgs.append({ 'type': 'product',
                            #                     'name': 'diablo3',
                            #                     'title': 'Diablo 3' })
                    except KeyError:
                        pass

                result.append({ 'id': linkId,
                                'mmoid': userid,
                                'nick': self.cache['battletags'][userid],
                                'state': 'No info available',
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
                    try:
                        for char in self.cache['sc2Profiles'][userid]['characters']:
                            self.setPartnerDetail(moreInfo, "SC 2", "[%s] %s" % (char['clanTag'], char['displayName']))
                            self.setPartnerAvatar(moreInfo, self.cacheFile(char['avatar']['url']))
                    except KeyError:
                        pass


                # Diablo 3
                if userid in self.cache['d3Profiles'].keys():
                    try:
                        for hero in self.cache['d3Profiles'][userid]['heroes']:
                            self.setPartnerDetail(moreInfo, "D3", "%s lvl %s (%s)" % (hero['name'], hero['level'], hero['class']))
                    except KeyError:
                        pass

                # World of Warcraft
                if userid in self.cache['wowProfiles'].keys():
                    try:
                        for char in self.cache['wowProfiles'][userid]['characters']:
                            self.setPartnerDetail(moreInfo, "WoW", "%s@%s: %s %s lvl: %s" % (char['name'],
                                                                                             char['realm'],
                                                                                             char['gender'],
                                                                                             char['race'],
                                                                                             char['level']))
                        chars = self.getBestWowChar(self.cache['wowProfiles'][userid]['characters'])
                        for char in chars:
                            self.setPartnerAvatar(moreInfo, self.cacheWowAvatarFile(char['thumbnail'], char['race'], char['gender']))
                    except KeyError:
                        pass
        
        return moreInfo

    def findPartners(self):
        self.log.debug("Searching for new partners to play with")
        return self.getPartners()
