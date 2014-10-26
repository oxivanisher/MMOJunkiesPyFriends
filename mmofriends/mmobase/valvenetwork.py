#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
import os
import random
import urllib2
import urllib
import re
import time

from flask import current_app
from mmoutils import *
from mmouser import *
from mmonetwork import *
from mmofriends import db

from requests.exceptions import ConnectionError

class ValveNetwork(MMONetwork):

    def __init__(self, app, session, handle):
        super(ValveNetwork, self).__init__(app, session, handle)

        self.steam_id_re = re.compile('steamcommunity.com/openid/id/(.*?)$')
        self.description = "Steam network from Valve"
        self.maxUpdateUsers = 99

        # activate debug while development
        # self.setLogLevel(logging.DEBUG)

        self.onlineStates = {}
        self.onlineStates[0] = "Offline"
        self.onlineStates[1] = "Online"
        self.onlineStates[2] = "Busy"
        self.onlineStates[3] = "Away"
        self.onlineStates[4] = "Snooze"
        self.onlineStates[5] = "Looking for trade"
        self.onlineStates[6] = "Looking to play"

        # background updater methods
        self.registerWorker(self.updateUsers, 300)
        self.registerWorker(self.updateUsersOnlineState, 60)

    # steam helper
    def fetchFromSteam(self, what, options = {}, logger = None):
        if not logger:
            logger = self.log

        logger.debug("Fetching %s" % (what))
        options['key'] = self.config['apikey']
        url = 'http://api.steampowered.com/%s/?%s' % (what, urllib.urlencode(options))
        logger.debug("URL: %s" % url)
        steamData = {}
        try:
            steamData = json.load(urllib2.urlopen(url))
            logger.debug("Recieved %s Bytes" % (len(str(steamData))))
        except urllib2.URLError as e:
            if e.code == 401:
                logger.info("Unauthorized")
                return {}
        except Exception as e:
            logger.warning("[%s] Unable to fetch %s because: %s" % (self.handle, url, e))

        if 'response' in steamData.keys():
            return steamData['response']
        elif 'friendslist' in steamData.keys():
            return steamData['friendslist']
        else:
            logger.warning("No response found")
            return False

    # background worker
    def updateUsers(self, logger = None):
        if not logger:
            logger = self.log

        allLinks = self.getNetworkLinks()
        steamIds = []
        for link in allLinks:
            steamIds.append(link['network_data'])

        logger.info("[%s] Will fetch %s users" % (self.handle, len(steamIds)))
        steamData = self.fetchFromSteam('ISteamUser/GetPlayerSummaries/v0002', {'steamids': ','.join(steamIds)})
        friendIds = []
        if steamData:
            self.getCache('users')
            self.getCache('games')
            for player in steamData['players']:
                self.cache['users'][player['steamid']] = player

                # fetching friends
                steamFriends = self.fetchFromSteam('ISteamUser/GetFriendList/v0001', {'steamid': player['steamid'],
                                                                                      'relationship': 'friend'})
                if steamFriends:
                    self.cache['users'][player['steamid']]['friends'] = steamFriends['friends']
                    for friend in steamFriends['friends']:
                        if friend['steamid'] not in friendIds:
                            friendIds.append(friend['steamid'])

                # fetching owned games
                ownedGames = self.fetchFromSteam('IPlayerService/GetOwnedGames/v0001', {'steamid': player['steamid'],
                                                                                        'include_played_free_games': '1',
                                                                                        'include_appinfo': '1' })
                self.cache['users'][player['steamid']]['ownedGames'] = {}
                if ownedGames:
                    for game in ownedGames['games']:
                        # updating games in general
                        self.cache['games'][game['appid']] = {}
                        self.cache['games'][game['appid']]['appid'] = game['appid']
                        self.cache['games'][game['appid']]['name'] = game['name']
                        self.cache['games'][game['appid']]['img_icon_url'] = game['img_icon_url']
                        self.cache['games'][game['appid']]['img_logo_url'] = game['img_logo_url']

                        # updating games of the user
                        self.cache['users'][player['steamid']]['ownedGames'][game['appid']] = {}
                        if 'playtime_2weeks' in game:
                            self.cache['users'][player['steamid']]['ownedGames'][game['appid']]['playtime_2weeks'] = game['playtime_2weeks']
                        else:
                            self.cache['users'][player['steamid']]['ownedGames'][game['appid']]['playtime_2weeks'] = 0
                            
                        if 'playtime_forever' in game:
                            self.cache['users'][player['steamid']]['ownedGames'][game['appid']]['playtime_forever'] = game['playtime_forever']
                        else:
                            self.cache['users'][player['steamid']]['ownedGames'][game['appid']]['playtime_forever'] = 0

            # fetch friends info
            run = True
            logger.debug("All friends: %s" % len(friendIds))
            while run:
                fetchFriends = friendIds[:self.maxUpdateUsers]
                friendIds = friendIds[self.maxUpdateUsers:]
                if len(fetchFriends) == 0:
                    run = False
                else:
                    logger.info("[%s] Fetching %s friends info" % (self.handle, len(fetchFriends)))
                    steamFriends = self.fetchFromSteam('ISteamUser/GetPlayerSummaries/v0002', {'steamids': ','.join(fetchFriends)})
                    for friend in steamFriends['players']:
                        if friend['steamid'] not in self.cache['users']:
                            self.cache['users'][friend['steamid']] = friend

            # fetch friends and games played for friends
            for player in self.cache['users'].keys():
                steamId = self.cache['users'][player]['steamid']
                if 'friends' not in self.cache['users'][player]:
                    logger.info("[%s] Fetching friendslist for %s" % (self.handle, steamId))
                    steamFriends = self.fetchFromSteam('ISteamUser/GetFriendList/v0001', {'steamid': steamId,
                                                                                          'relationship': 'friend'})
                    if steamFriends != False:
                        if 'friends' not in steamFriends:
                                steamFriends['friends'] = []
                        self.cache['users'][steamId]['friends'] = steamFriends['friends']

                if 'ownedGames' not in self.cache['users'][player]:
                    logger.info("[%s] Fetching games for %s" % (self.handle, steamId))
                    ownedGames = self.fetchFromSteam('IPlayerService/GetOwnedGames/v0001', {'steamid': steamId,
                                                                                            'include_played_free_games': '1',
                                                                                            'include_appinfo': '1' })
                    self.cache['users'][steamId]['ownedGames'] = {}
                    if ownedGames:
                        for game in ownedGames['games']:
                            # updating games in general
                            self.cache['games'][game['appid']] = {}
                            self.cache['games'][game['appid']]['appid'] = game['appid']
                            self.cache['games'][game['appid']]['name'] = game['name']
                            self.cache['games'][game['appid']]['img_icon_url'] = game['img_icon_url']
                            self.cache['games'][game['appid']]['img_logo_url'] = game['img_logo_url']

                            # updating games of the user
                            self.cache['users'][steamId]['ownedGames'][game['appid']] = {}
                            if 'playtime_2weeks' in game:
                                self.cache['users'][steamId]['ownedGames'][game['appid']]['playtime_2weeks'] = game['playtime_2weeks']
                            else:
                                self.cache['users'][steamId]['ownedGames'][game['appid']]['playtime_2weeks'] = 0
                                
                            if 'playtime_forever' in game:
                                self.cache['users'][steamId]['ownedGames'][game['appid']]['playtime_forever'] = game['playtime_forever']
                            else:
                                self.cache['users'][steamId]['ownedGames'][game['appid']]['playtime_forever'] = 0

            self.setCache('users')
            self.setCache('games')
            logger.info("[%s] Updated %s users" % (self.handle, len(steamData['players'])))

    def updateUsersOnlineState(self, logger = None):
        if not logger:
            logger = self.log

        self.getCache('users')
        allUsers = []
        for user in self.cache['users'].keys():
            allUsers.append(user)

        run = True
        logger.debug("All friends: %s" % len(allUsers))
        while run:
            fetchFriends = allUsers[:self.maxUpdateUsers]
            allUsers = allUsers[self.maxUpdateUsers:]
            if len(fetchFriends) == 0:
                run = False
            else:
                logger.info("Fetching %s friends info" % len(fetchFriends))
                steamFriends = self.fetchFromSteam('ISteamUser/GetPlayerSummaries/v0002', {'steamids': ','.join(fetchFriends)})
                for friend in steamFriends['players']:
                    self.cache['users'][friend['steamid']]['personastate'] = friend['personastate']

    # oid methods
    def oid_login(self, oid):
        self.log.debug("OID Login")
        if self.getSessionValue(self.linkIdName) is not None:
            self.log.debug("SteamId found")
            return (True, oid.get_next_url())

        self.log.debug("No steamId found")
        return (False, oid.try_login('http://steamcommunity.com/openid'))

    def oid_logout(self, oid):
        self.log.debug("OID Logout")
        return oid.get_next_url()

    def oid_create_or_login(self, oid, resp):
        self.log.debug("OID create_or_login")
        match = self.steam_id_re.search(resp.identity_url)
        self.setSessionValue(self.linkIdName, match.group(1))
        self.saveLink(self.getSessionValue(self.linkIdName))
        return ('You are now connected to steam', oid.get_next_url())

    # overwritten class methods
    def getLinkHtml(self):
        self.log.debug("Show linkHtml %s" % self.name)
        htmlFields = {}
        if not self.getSessionValue(self.linkIdName):
            htmlFields['oid'] = {'comment': "Click to login with Steam.", 'image': "//steamcommunity-a.akamaihd.net/public/images/signinthroughsteam/sits_small.png"}
        return htmlFields

    def devTest(self):
        # have fun: https://github.com/smiley/steamapi/blob/master/steamapi/user.py
        return "steamId: %s" % self.getSessionValue(self.linkIdName)

    def getPartners(self, **kwargs):
        self.getCache('users')

        self.log.debug("List all partners for given user")
        if not self.getSessionValue(self.linkIdName):
            return (False, False)
        if self.getSessionValue(self.linkIdName):

            onlineOnly = False
            try:
                kwargs['onlineOnly']
                onlineOnly = True
            except KeyError:
                pass

            result = []
            allLinks = self.getNetworkLinks()
            friends = []
            onlineFriends = {}
            steamId = self.getSessionValue(self.linkIdName)
            if steamId not in self.cache['users']:
                self.log.info("User probably not yet cached")
                return (False, False)

            for friend in self.cache['users'][steamId]['friends']:
                onlineFriends[friend['steamid']] = self.cache['users'][friend['steamid']]['personastate']

            for friend in self.cache['users'][steamId]['friends']:
                self.log.error("blah %s" % friend['steamid'])
                friendSteamId = friend['steamid']
                if onlineOnly:
                    self.log.warning("%s|%s" % (friendSteamId, onlineFriends[friendSteamId]))
                    if onlineFriends[friendSteamId] == 0:
                        continue

                linkId = None
                for link in allLinks:
                    if friend == link['network_data']:
                        linkId = friend

                self.getPartnerDetails(friendSteamId)
                self.getCache('users')

                if friendSteamId not in self.cache['users'].keys():
                    self.log.error("Unable to find or load user %s" % friendSteamId)
                    continue
                friend = str(friend)
                self.cacheFile(self.cacheFile(self.cache['users'][friendSteamId]['avatar']))
                self.cacheFile(self.cacheFile(self.cache['users'][friendSteamId]['avatarfull']))

                friendImgs = []
                try:
                    friendImgs.append({
                                    'type': 'flag',
                                    'name': self.cache['users'][friendSteamId]['loccountrycode'].lower(),
                                    'title': self.cache['users'][friendSteamId]['loccountrycode']
                                    })
                except KeyError:
                    pass

                friendImgs.append({
                                    'type': 'cache',
                                    'name': self.cacheFile(self.cache['users'][friendSteamId]['avatar']),
                                    'title': self.cache['users'][friendSteamId]['personaname']
                                })

                onlineState = 0
                try:
                    onlineState = onlineFriends[friendSteamId]
                except KeyError:
                    self.log.warning("Online state not found: %s" % onlineFriends[friend])

                result.append({ 'mmoid': linkId,
                                'id': friendSteamId,
                                'nick': self.cache['users'][friendSteamId]['personaname'],
                                'state': self.onlineStates[onlineState],
                                'netHandle': self.handle,
                                'networkText': self.name,
                                'networkImgs': [{
                                    'type': 'network',
                                    'name': self.handle,
                                    'title': self.name
                                }],
                                'friendImgs': friendImgs
                            })
            return (True, result)
        else:
            return (True, {})

    def getPartnerDetails(self, partnerId):
        self.getCache('users')
        self.getCache('games')

        self.log.debug("List partner details for: %s" % partnerId)
        moreInfo = {}

        try:
            self.setPartnerDetail(moreInfo, "Nick", self.cache['users'][partnerId]['personaname'])
        except KeyError:
            #Probably empty database!
            return moreInfo
        self.setPartnerAvatar(moreInfo, self.cacheFile(self.cache['users'][partnerId]['avatarfull']))


        if self.session.get('admin'):
            self.setPartnerDetail(moreInfo, "Steam ID", self.cache['users'][partnerId]['steamid'])
            try:
                self.setPartnerDetail(moreInfo, "Real Name", self.cache['users'][partnerId]['realname'])
            except KeyError:
                pass

        try:
            self.setPartnerDetail(moreInfo, "Country Code", self.cache['users'][partnerId]['loccountrycode'])
        except KeyError:
            pass
        try:
            self.setPartnerDetail(moreInfo, "Created", timestampToString(self.cache['users'][partnerId]['timecreated']))
        except KeyError:
            pass
        try:
            self.setPartnerDetail(moreInfo, "Last Logoff", timestampToString(self.cache['users'][partnerId]['lastlogoff']))
        except KeyError:
            pass
        self.setPartnerDetail(moreInfo, "Profile URL", self.cache['users'][partnerId]['profileurl'])
        self.setPartnerDetail(moreInfo, "Online/Offline", self.onlineStates[self.cache['users'][partnerId]['personastate']])

        games = []
        if 'games' in self.cache['users'][partnerId]:
            for gameid in self.cache['users'][partnerId]['games']:
                try:
                    games.append(self.cache['games'][str(gameid)]['name'])
                except KeyError:
                    self.log.debug("Ignoring game ID %s" % gameid)
            self.setPartnerDetail(moreInfo, "Games", ', '.join(games))

            games = []
            for gameid in self.cache['users'][partnerId]['recentlyplayed']:
                try:
                    games.append(self.cache['games'][str(gameid)]['name'])
                except KeyError:
                    self.log.debug("Ignoring game ID %s" % gameid)
            self.setPartnerDetail(moreInfo, "Recently Played", ', '.join(games))
        
        # self.setPartnerDetail(moreInfo, "Owned Games", steam_user.owned_games)

        # if steam_user.currently_playing:
        #     self.setPartnerDetail(moreInfo, "Currently Playing", steam_user.currently_playing.name)

        return moreInfo

    def admin(self):
        self.log.debug("Loading admin stuff")

    def findPartners(self):
        self.log.debug("Searching for new partners to play with")
        return ( True, [])
        return ( False, "Network not yet programmed")
        return ( True, {'id': 'someId',
                        'mmoid': internalId,
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
