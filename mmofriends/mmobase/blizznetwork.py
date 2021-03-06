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
import numpy

from flask import current_app, url_for, request, get_flashed_messages
from flask.ext.babel import Babel, gettext

from mmofriends.mmoutils import *
from mmofriends.models import *
from mmofriends.database import db_session

try:
    from rauth.service import OAuth2Service
except ImportError:
    logging.error("[Systen] Please install the rauth library (https://github.com/litl/rauth)")
    import sys
    sys.exit(2)

class BlizzNetwork(MMONetwork):

    def __init__(self, app, session, handle):
        super(BlizzNetwork, self).__init__(app, session, handle)

        self.baseUrl = 'https://%s.api.battle.net' % self.config['region']
        self.avatarUrl = 'http://%s.battle.net/' % (self.config['region'])
        self.locale = 'en_US'
        self.products = { 'worldofwarcraft': 'World of Warcraft',
                          'starcraft2': 'Starcraft 2',
                          'diablo3': 'Diablo 3',
                          'hearthstone': 'Hearthstone',
                          'hots': 'Heroes of the Storm' }

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

        # admin methods
        self.adminMethods.append((self.updateBaseResources, 'Recache base resources'))
        self.adminMethods.append((self.updateAllUserResources, 'Recache all user resources'))
        self.adminMethods.append((self.updateUserResources, 'Recache (your) user resources'))

        # background updater methods
        self.registerWorker(self.updateBaseResources, 39600)
        self.registerWorker(self.updateAllUserResources, 3500)
        self.registerWorker(self.updateUserFeeds, 909)
        self.registerWorker(self.cleanProfiles, 3400)

        # dashboard boxes
        self.registerDashboardBox(self.dashboard_wowChars, 'wowChars', {'title': 'WoW: Chars by level','template': 'box_jQCloud.html'})

        # setup batttleNet service
        self.battleNet = OAuth2Service(
            client_id=self.config['apikey'],
            client_secret=self.config['apisecret'],
            authorize_url='https://%s.battle.net/oauth/authorize' % self.config['region'],
            access_token_url='https://%s.battle.net/oauth/token' % self.config['region'])

    # overwritten class methods
    def getStats(self):
        self.log.debug("[%s] Requesting stats" % (self.handle))
        self.getCache('wowProfiles')
        self.getCache('sc2Profiles')
        self.getCache('d3Profiles')

        wowChars = 0
        for char in self.cache['wowProfiles']:
            try:
                wowChars += len(self.cache['wowProfiles'][char]['characters'])
            except KeyError:
                pass

        sc2Chars = 0
        for char in self.cache['sc2Profiles']:
            try:
                sc2Chars += len(self.cache['sc2Profiles'][char]['characters'])
            except KeyError:
                pass

        d3Heroes = 0
        for char in self.cache['d3Profiles']:
            try:
                d3Heroes += len(self.cache['d3Profiles'][char]['heroes'])
            except KeyError:
                pass

        return {
            gettext('World of Warcraft Characters'): wowChars,
            gettext('Starcraft 2 Profiles'): sc2Chars,
            gettext('Diablo 3 Heores'): d3Heroes,
        }

    def getLinkHtml(self):
        self.log.debug("Show linkHtml %s" % self.name)
        htmlFields = {}
        # if not self.getSessionValue(self.linkIdName):
        htmlFields['link'] = {'comment': "%s %s" % (gettext("Login with"), self.name),
                              'linkUrl': self.requestAuthorizationUrl()}
        return htmlFields

    def loadNetworkToSession(self):
        if request.path != url_for('oauth2_login', netHandle=self.handle):
            for link in self.getNetworkLinks(self.session['userid']):
                if not link['network_data']:
                    return (False, "%s %s" % (gettext("Blizzard automatically removes permission to fetch your data after 30 days."),
                                              gettext("Please klick <a href='%(link)s' target='_blank'>this link</a> to reauthorize.", link=self.requestAuthorizationUrl())))
        else:
            for message in get_flashed_messages(category_filter=["error"]):
                pass
        return super(BlizzNetwork, self).loadNetworkToSession()

    def getPartners(self, **kwargs):
        self.log.debug("[%s] List all partners for given user" % (self.handle))

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
                # linkId = self.cache['battletags'][userid]

                # World of warcraft
                if userid in self.cache['wowProfiles'].keys():
                    if 'characters' in self.cache['wowProfiles'][userid]:
                        if self.cache['wowProfiles'][userid]['characters']:
                            try:
                                bestChar = self.getBestWowChar(self.cache['wowProfiles'][userid]['characters'])
                                friendImgs.append({ 'type': 'cache',
                                                    'name': self.cacheWowAvatarFile(bestChar['thumbnail'],
                                                                                    bestChar['race'],
                                                                                    bestChar['gender']),
                                                    'title': bestChar['name'] + '@' + bestChar['realm'] })
                                myProducts.append({ 'type': 'product',
                                                    'name': 'worldofwarcraft',
                                                    'title': self.products['worldofwarcraft'] })
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
                                            'title': self.products['starcraft2'] })
                    except KeyError:
                        pass

                # Diablo 3 heroes
                if userid in self.cache['d3Profiles'].keys():
                    try:
                        if len(self.cache['d3Profiles'][userid]['heroes']) > 0:
                            myProducts.append({ 'type': 'product',
                                                'name': 'diablo3',
                                                'title': self.products['diablo3'] })
                            # friendImgs.append({ 'type': 'product',
                            #                     'name': 'diablo3',
                            #                     'title': 'Diablo 3' })
                    except KeyError:
                        pass

                result.append({ 'id': userid,
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

    def getPartnerDetails(self, partnerId):
        self.log.debug("List partner details")
        moreInfo = {}

        self.getCache('battletags')
        self.getCache('wowProfiles')
        self.getCache('sc2Profiles')
        self.getCache('d3Profiles')

        try:
            self.setPartnerDetail(moreInfo, "Battletag", self.cache['battletags'][partnerId])
        except (KeyError, IndexError):
            return moreInfo

        # Starcraft 2
        if partnerId in self.cache['sc2Profiles'].keys():
            try:
                for char in self.cache['sc2Profiles'][partnerId]['characters']:
                    clantag = ""
                    if char['clanTag']:
                        clantag = "[%s] " % char['clanTag']
                    self.setPartnerDetail(moreInfo, "SC 2", "%s%s" % (clantag, char['displayName']))
                    self.setPartnerAvatar(moreInfo, self.cacheFile(char['avatar']['url']))
            except (KeyError, TypeError):
                pass

        # Diablo 3
        if partnerId in self.cache['d3Profiles'].keys():
            try:
                for hero in self.cache['d3Profiles'][partnerId]['heroes']:
                    self.setPartnerDetail(moreInfo, "D3", "%s lvl %s (%s)" % (hero['name'], hero['level'], hero['class']))
            except (KeyError, TypeError):
                pass

        # World of Warcraft
        if partnerId in self.cache['wowProfiles'].keys():
            try:
                for char in self.cache['wowProfiles'][partnerId]['characters']:
                    self.setPartnerDetail(moreInfo, "WoW", char['name'] + " (" + self.getWowCharDescription(char) + ")")
                bestChar = self.getBestWowChar(self.cache['wowProfiles'][partnerId]['characters'])
                self.setPartnerAvatar(moreInfo, self.cacheWowAvatarFile(bestChar['thumbnail'], bestChar['race'], bestChar['gender']))
            except (KeyError, TypeError):
                pass
        
        return moreInfo

    def findPartners(self):
        self.log.debug("[%s] Searching for new partners to play with" % (self.handle))
        return self.getPartners()

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

    # Oauth2 helper
    def requestAuthorizationUrl(self):
        self.log.debug("%s is requesting the Authorization URL (Step 1/3)" % self.session['nick'])
        params = {'redirect_uri': url_for('oauth2_login', netHandle=self.handle, _external=True),
                  'scope': 'wow.profile sc2.profile',
                  'response_type': 'code'}
        self.log.debug("Generating Authorization Url")
        return self.battleNet.get_authorize_url(**params)

    def requestAccessToken(self, code):
        # if not self.battleNet:
        #     self.requestAuthorizationUrl()
        self.log.debug("%s is requesting a Access Token (Step 2/3)" % self.session['nick'])

        data = {'redirect_uri': url_for('oauth2_login', netHandle=self.handle, _external=True),
                'scope': 'wow.profile sc2.profile',
                'grant_type': 'authorization_code',
                'code': code}

        access_token = self.battleNet.get_access_token(decoder = json.loads, data=data)
        self.log.debug("Oauth2 Login successful, recieved new access_token (Step 3/3)")
        self.saveLink(access_token)
        self.setSessionValue(self.linkIdName, access_token)
        # self.updateBaseResources(False)
        self.updateUserResources()
        return self.cache['battletags'][self.session['userid']]

    # update resource helpers
    def updateBaseResources(self, force = True):
        count = 0
        accessToken = False
        for link in self.getNetworkLinks():
            if link['network_data']:
                accessToken = link['network_data']

        for entry in self.wowDataResourcesList.keys():
            self.forceCacheUpdate(entry)

        for entry in self.sc2DataResourcesList.keys():
            self.forceCacheUpdate(entry)

        if accessToken:
            for entry in self.wowDataResourcesList.keys():
                count += 1
                self.setBackgroundWorkerResult('Updating wow resource %s' % (entry))
                self.updateResource(entry, self.wowDataResourcesList[entry], accessToken)

            for entry in self.sc2DataResourcesList.keys():
                count += 1
                self.setBackgroundWorkerResult('Updating sc2 resource %s' % (entry))
                self.updateResource(entry, self.sc2DataResourcesList[entry], accessToken)

        # self.saveAllData()
        return "%s base resources updated" % count

    def updateAllUserResources(self, logger = None):
        if not logger:
            logger = self.log

        okCount = 0
        nokCount = 0
        for link in self.getNetworkLinks():
            logger.debug("[%s] Updating user resources for %s" % (self.handle, self.getUserById(link['user_id']).nick))
            if link['network_data']:
                self.updateUserResources(link['user_id'], link['network_data'])
                okCount += 1
            else:
                nokCount += 1
        return "%s user resources updated, %s ignored" % (okCount, nokCount)

    def updateUserFeeds(self, logger = None):
        if not logger:
            logger = self.log

        self.getCache('wowFeeds')
        self.getCache('wowAchievments')
        self.getCache('wowProfiles')

        okCount = 0
        nokCount = 0
        feedCount = 0
        lowieCount = 0
        for link in self.getNetworkLinks():
            logger.debug("[%s] Updating user feed for %s" % (self.handle, self.getUserById(link['user_id']).nick))
            if link['network_data']:

                self.setBackgroundWorkerResult("[%s] Background updating the feeds for %s" % (self.handle, self.getUserById(link['user_id']).nick))

                (retValue, retMessage) = self.queryBlizzardApi('/wow/user/characters', link['network_data'])
                if retValue != False:
                    if 'characters' in retMessage.keys():
                        for char in retMessage['characters']:
                            charIndex = retMessage['characters'].index(char)

                            if char['level'] < 10:
                                lowieCount += 1
                                logger.debug("[%s] Not updating feed for %s@%s, level too low." % (self.handle, retMessage['characters'][charIndex]['name'], retMessage['characters'][charIndex]['realm']))
                            else:
                                logger.debug("[%s] Updating feed for %s@%s" % (self.handle, retMessage['characters'][charIndex]['name'], retMessage['characters'][charIndex]['realm']))
                                (detailRetValue, detailRetMessage) = self.queryBlizzardApi('/wow/character/%s/%s?fields=feed&locale=en_GB' % (retMessage['characters'][charIndex]['realm'], retMessage['characters'][charIndex]['name']), link['network_data'])
                                if detailRetValue != False:
                                    try:
                                        self.cache['wowFeeds'][link['user_id']]
                                    except KeyError:
                                        self.cache['wowFeeds'][link['user_id']] = {}
                                    if detailRetMessage != '{"status": "nok", "reason": "Character not found."}':
                                        self.cache['wowFeeds'][link['user_id']][retMessage['characters'][charIndex]['name']] = detailRetMessage
                                        feedCount += 1

                    if link['user_id'] in self.cache['wowFeeds']:
                        logger.debug("[%s] Updated %s feed(s) for %s" % (self.handle, len(self.cache['wowFeeds'][link['user_id']]), self.getUserById(link['user_id']).nick))
                    else:
                        logger.debug("[%s] Updated no feeds for %s" % (self.handle, self.getUserById(link['user_id']).nick))

                okCount += 1
            else:
                nokCount += 1

        self.setCache('wowFeeds')

        self.getCache('lastly')
        self.cache['lastly'] = {}
        for userid in self.cache['wowFeeds'].keys():
            try:
                if 'characters' not in self.cache['wowProfiles'][userid].keys():
                    continue
            except KeyError:
                continue
            bestChar = self.getBestWowChar(self.cache['wowProfiles'][userid]['characters'])

            # create list of type and achievments to remove doubles
            checkFeed = []
            for char in self.cache['wowFeeds'][userid].keys():
                if 'feed' in self.cache['wowFeeds'][userid][char].keys():
                    for entry in self.cache['wowFeeds'][userid][char]['feed']:
                        checkFeed.append((entry['type'], entry['timestamp']))

            for char in self.cache['wowFeeds'][userid].keys():
                if 'feed' in self.cache['wowFeeds'][userid][char].keys():
                    charName = self.cache['wowFeeds'][userid][char]['name']
                    charRealm = self.cache['wowFeeds'][userid][char]['realm']
                    for entry in self.cache['wowFeeds'][userid][char]['feed']:
                        showMe = False

                        foundCount = 0
                        for (checkType, checkTimestamp) in checkFeed:
                            if checkType == entry['type'] and checkTimestamp == entry['timestamp']:
                                foundCount += 1
                        if foundCount == 1:
                            showMe = True
                        elif foundCount == 0:
                            logger.warning("[%s] Something is strange here... Please investigate updateUserFeeds on updating lastly!" % (self.handle))
                        else:
                            logger.debug("[%s] found multiple occurences of %s %s" % (self.handle, entry['type'], entry['timestamp']))
                            if bestChar['name'] == charName:
                                showMe = True

                        if showMe:
                            myTimestamp = float(entry['timestamp']/1000.0)
                            tsOk = False
                            while not tsOk:
                                if myTimestamp in self.cache['lastly'].keys():
                                    myTimestamp = numpy.nextafter(myTimestamp, myTimestamp + 1)
                                else:
                                    tsOk = True
                            if entry['type'] == 'ACHIEVEMENT':
                                self.cache['lastly'][myTimestamp] = "WOW achievment of %s@%s: %s" % (charName, charRealm, entry['achievement']['title'])
                            elif entry['type'] == 'CRITERIA':
                                self.cache['lastly'][myTimestamp] = "WOW achievment criteria of %s@%s: %s for %s" % (charName, charRealm, entry['criteria']['description'], entry['achievement']['title'])
                            elif entry['type'] == 'BOSSKILL':
                                self.cache['lastly'][myTimestamp] = "WOW boss kill of %s@%s: %s" % (charName, charRealm, entry['achievement']['title'])
                        # elif entry['type'] == 'LOOT':
                        #     self.cache['lastly'][int(entry['timestamp']/1000)] = "WOW item loot of %s@%s: %s" % (charName, charRealm, entry['itemId'])

        self.setCache('lastly')

        return "%s feeds from %s users updated. Ignored because unlinked: %s, lowie: %s." % (feedCount, okCount, nokCount, lowieCount)

    def cleanProfiles(self, logger = None):
        # FIXME: clean up other profiles too... (d3, sc2)

        keepProfilesSeconds = 86400

        if not logger:
            logger = self.log

        wowCleanCount = 0
        self.getCache('wowProfiles')
        for profile in self.cache['wowProfiles'].keys():
            deleteMe = False
            if 'lastUpdate' in self.cache['wowProfiles'][profile].keys():
                if self.cache['wowProfiles'][profile]['lastUpdate'] + keepProfilesSeconds < time.time():
                    deleteMe = True
            else:
                deleteMe = True

            if deleteMe:
                self.cache['wowProfiles'].pop(profile, None)
                wowCleanCount += 1

        self.setCache('wowProfiles')
        
        return "%s WoW profiles cleaned up." % (wowCleanCount)

    def updateUserResources(self, userid = None, accessToken = None, logger = None):
        if not logger:
            logger = self.log

        background = True
        if not userid:
            userid = self.session['userid']
            background = False
            logger.info("[%s] Foreground updating the resources for %s" % (self.handle, self.getUserById(userid).nick))
        else:
            message = "[%s] Background updating the resources for %s" % (self.handle, self.getUserById(userid).nick)
            self.setBackgroundWorkerResult(message)
            logger.info(message)
        userNick = self.getUserById(userid).nick

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
                userNick = "%s (%s)" % (userNick, retMessage['battletag'])
                logger.info("[%s] Updated battletag %s" % (self.handle, retMessage['battletag']))
            else:
                message = "Unable to update Battletag for %s (%s)" % (self.getUserById(userid).nick, retMessage)
                logger.debug(message)
                try:
                    if retMessage['code'] == 403:
                        self.updateLink(userid, None)
                        logger.warning("[%s] Removed access token for %s because %s" % (self.handle, self.getUserById(userid).nick, retMessage['detail']))
                except KeyError:
                    pass
                
                return (False, message)

        # fetching wow chars
        (retValue, retMessage) = self.queryBlizzardApi('/wow/user/characters', accessToken)
        if retValue != False:
            lowieCount = 0
            self.getCache('wowProfiles')
            self.cache['wowProfiles'][userid] = retMessage
            self.cache['wowProfiles'][userid]['lastUpdate'] = time.time()
            self.setCache('wowProfiles')
            if background and 'characters' in retMessage.keys():
                self.getCache('wowAchievments')
                for char in retMessage['characters']:
                    charIndex = retMessage['characters'].index(char)
                    self.cacheWowAvatarFile(char['thumbnail'], char['race'], char['gender'])

                    if char['level'] < 10:
                        lowieCount += 1
                        logger.debug("[%s] Not updating feed for %s@%s, level too low." % (self.handle, retMessage['characters'][charIndex]['name'], retMessage['characters'][charIndex]['realm']))
                    else:
                        logger.debug("[%s] Updating achievments for %s@%s" % (self.handle, retMessage['characters'][charIndex]['name'], retMessage['characters'][charIndex]['realm']))
                        (detailRetValue, detailRetMessage) = self.queryBlizzardApi('/wow/character/%s/%s?fields=achievements&locale=en_GB' % (retMessage['characters'][charIndex]['realm'], retMessage['characters'][charIndex]['name']), accessToken)
                        if detailRetValue != False:
                            try:
                                self.cache['wowAchievments'][userid]
                            except KeyError:
                                self.cache['wowAchievments'][userid] = {}
                            self.cache['wowAchievments'][userid][retMessage['characters'][charIndex]['name']] = detailRetMessage
                    self.setCache('wowAchievments')

                logger.info("[%s] Updated %s WoW characters (ignored %s lowies)" % (self.handle, len(self.cache['wowProfiles'][userid]['characters']), lowieCount))

        # fetching d3 profile
        if self.cache['battletags'][userid]:
            (retValue, retMessage) = self.queryBlizzardApi('/d3/profile/%s/' % self.cache['battletags'][userid].replace('#', '-'), accessToken)
            if retValue != False:
                self.getCache('d3Profiles')
                self.cache['d3Profiles'][userid] = retMessage
                self.setCache('d3Profiles')
                logger.info("[%s] Updated D3 Profile" % (self.handle))

        # fetching sc2
        (retValue, retMessage) = self.queryBlizzardApi('/sc2/profile/user', accessToken)
        if retValue != False:
            self.getCache('sc2Profiles')
            self.cache['sc2Profiles'][userid] = retMessage
            self.setCache('sc2Profiles')
            logger.info("[%s] Updated SC2 Profile" % (self.handle))

        return (True, "All resources updated for %s" % userNick)

    def updateResource(self, entry, location, accessToken = None):
        message = "[%s] Updating resource from %s" % (self.handle, location)
        self.log.debug(message)
        self.getCache(entry)
        # if self.getCacheAge(entry) < self.config['updateLock'] - random.randint(1, 300) or len(self.cache[entry]) == 0:
        (resValue, resData)  = self.queryBlizzardApi(location, accessToken)
        if resValue:
            self.cache[entry] = resData
            self.setCache(entry)
            self.log.debug("[%s] Fetched %s from %s with %s result length" % (self.handle, entry, location, len(resData)))
            return (True, "Resource updated from %s" % location)
        else:
            self.log.warning("[%s] Unable to update resource from %s because: %s" % (self.handle, location, resData))
            return (False, resData)

    # Query Blizzard
    def queryBlizzardApi(self, what, accessToken = None):
        self.log.debug("[%s] Query Blizzard API for %s" % (self.handle, what))
        if not accessToken:
            accessToken = self.getSessionValue(self.linkIdName)
            if not accessToken:
                return (False, "No access token available")

        payload = {'access_token': accessToken,
                   'apikey': self.config['apikey'],
                   'locale': self.locale}

        tryCount = 0
        while tryCount < 3:
            try:
                tryCount += 1
                r = requests.get(self.baseUrl + what, params=payload, timeout=6.1).json()
                break
            except requests.exceptions.Timeout:
                self.log.debug("[%s] queryBlizzardApi ran into timeout for: %s" % (self.handle, what))
            except requests.exceptions.RequestException as e:
                self.log.debug("[%s] queryBlizzardApi ran into requests.exception %s for: %s" % (self.handle, e, what))
            except ValueError as e:
                self.log.debug("[%s] queryBlizzardApi got ValueError %s for: %s" % (self.handle, e, what))
            except Exception as e:
                self.log.warning("[%s] queryBlizzardApi ran into exception %s for: %s" % (self.handle, e, what))
                return (False, e)
        else:
            message = "queryBlizzardApi %s tries reached. giving up on: %s" % (tryCount, what)
            self.log.warning("[%s] %s" % (self.handle, message))
            return (False, message)
     
        try:
            if r['code']:
                try:
                    link = runQuery(db_session.query(MMONetLink).filter_by(network_handle=self.handle, network_data=accessToken).first)
                except Exception as e:
                    self.log.warning("[%s] SQL Alchemy Error on queryBlizzardApi: %s" % (self.handle, e))

                # self.unlink(self.session['userid'], link.id)
                self.log.debug("[%s] queryBlizzardApi found code: %s" % (self.handle, r['code']))
                with self.app.test_request_context():
                    self.requestAuthorizationUrl()
                    return (False, "<a href='%s'>Please reauthorize this page.</a>" % self.requestAuthorizationUrl())
                return (False, r['detail'])
            elif 'error' in r.keys():
                self.log.debug("[%s] queryBlizzardApi found error: %s" % (self.handle, r['error_description']))
                return (False, r['error_description'])
        except KeyError:
            pass
        except Exception as e:
            self.log.warning("[%s] Please handle exception %s on in queryBlizzardApi!" % (self.handle, e))

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
        tmpUrl = 'wow/static/images/2d/avatar/%s-%s.jpg' % (race, gender)
        savePath = tmpUrl.replace('/', '-')
        
        if 'internal-record' in origUrl:
            self.log.debug("[%s] Found non existing avatar url" % (self.handle))
            avatarUrl = self.avatarUrl + tmpUrl
        else:
            savePath = origUrl.replace('/', '-')
            avatarUrl = self.avatarUrl + 'static-render/%s/' % self.config['region'] + origUrl
            self.log.debug("[%s] Downloading existing avatar url" % (self.handle))

        outputFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../static/cache', savePath)
        if os.path.isfile(outputFilePath):
            self.log.debug("[%s] Not downloading %s, it already exists" % (self.handle, savePath))
        else:
            self.log.info("[%s] Downloading %s to %s" % (self.handle, avatarUrl, savePath))
            avatarFile = urllib.URLopener()
            try:
                avatarFile.retrieve(avatarUrl, outputFilePath)
            except Exception:
                # BUG: http://us.battle.net/en/forum/topic/14525622754
                avatarUrl = self.avatarUrl + tmpUrl
                self.log.warning("[%s] Not existing avatar! Saving general avatar %s to %s" % (self.handle, avatarUrl, outputFilePath))
                try:
                    avatarFile.retrieve(avatarUrl, outputFilePath)
                except Exception as e:
                    self.log.error("[%s] Unable to fetch file from %s to %s: %s" % (self.handle, avatarUrl, outputFilePath, e))
                
                # savePath = self.cacheWowAvatarFile('internal-record', race, gender)

        return savePath

    # Helpers
    def getWowRace(self, race):
        self.getCache('wowCharRaces')
        for wowRace in self.cache['wowCharRaces']['races']:
            if wowRace['id'] == race:
                return wowRace['name']
        return gettext("Unknown")

    def getWowGender(self, gender = False):
        if gender:
            return gettext("Female")
        else:
            return gettext("Male")

    def getWowClass(self, charClass):
        self.getCache('wowCharClasses')
        for wowClass in self.cache['wowCharClasses']['classes']:
            if wowClass['id'] == charClass:
                return wowClass['name']
        return gettext("Unknown")

    def getWowCharDescription(self, wowChar):
        return gettext("Level %(level)s %(gender)s %(race)s %(wowclass)s on %(realm)s",
                level=wowChar['level'], gender=self.getWowGender(wowChar['gender']),
                race=self.getWowRace(wowChar['race']), wowclass=self.getWowClass(wowChar['class']),
                realm=wowChar['realm'])

    def getBestWowChar(self, chars):
        level = -1
        achievmentPoints = -1
        finalChars = []
        # get max level
        for char in chars:
            if int(char['level']) > level:
                level = int(char['level'])
        # get chars with max level
        for char in chars:
            if int(char['level']) == level:
                finalChars.append(char)
        # get max achievment points
        for char in finalChars:
            if int(char['achievementPoints']) > int(achievmentPoints):
                achievmentPoints = int(char['achievementPoints'])
        # get char with highest achievment points
        for char in finalChars:
            if int(char['achievementPoints']) == int(achievmentPoints):
                return char

        # unable to locate some prefered char. just return the first one.
        try:
            return chars[0]
        except IndexError:
            return []

    # Game methods
    def getGames(self):
        return self.products

    def getGameIcon(self, gameId):
        return url_for('get_image', imgType='product', imgId=gameId)

    def getGamesOfUser(self, userId):
        self.getCache('wowProfiles')
        self.getCache('d3Profiles')
        self.getCache('sc2Profiles')

        games = self.products

        if userId not in self.cache['wowProfiles'].keys():
            games.pop("worldofwarcraft", None)
        if userId not in self.cache['d3Profiles'].keys():
            games.pop("diablo3", None)
        if userId not in self.cache['sc2Profiles'].keys():
            games.pop("starcraft2", None)

        return games

    def getUsersOfGame(self, gameHandle):
        if gameHandle == 'worldofwarcraft':
            self.getCache('wowProfiles')
            return self.cache['wowProfiles'].keys()

        if gameHandle == 'starcraft2':
            self.getCache('sc2Profiles')
            return self.cache['sc2Profiles'].keys()

        if gameHandle == 'diablo3':
            self.getCache('d3Profiles')
            return self.cache['d3Profiles'].keys()

        if gameHandle == 'hearthstone':
            self.getCache('battletags')
            return self.cache['battletags'].keys()

        if gameHandle == 'hots':
            self.getCache('battletags')
            return self.cache['battletags'].keys()

        return []
            
    # Dashboard
    def dashboard_wowChars(self, request):
        self.log.debug("[%s] Dashboard wowChars" % (self.handle))

        self.getCache('wowProfiles')

        chars = []
        for profile in self.cache['wowProfiles'].keys():
            try:
                for myChar in self.cache['wowProfiles'][profile]['characters']:
                    if 'logged_in' in self.session:
                        user = self.getUserById(profile)
                        link = { 'href': url_for('partner_show', partnerId=profile, netHandle=self.handle),
                                 'title': self.getWowCharDescription(myChar) + " (" + user.nick + ")"}
                    else:
                        link = { 'href': "%swow/en/character/%s/%s/" % (self.avatarUrl, myChar['realm'], myChar['name']),
                                 'target': '_blank',
                                 'title': self.getWowCharDescription(myChar) }

                    chars.append({ 'text': myChar['name'],
                                   'weight': myChar['level'],
                                   'link': link})
            except KeyError:
                pass
        return { 'wowChars': getHighestRated(chars, 'weight') }
