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
        # activate debug while development
        self.setLogLevel(logging.DEBUG)

        self.steam_id_re = re.compile('steamcommunity.com/openid/id/(.*?)$')
        self.maxUpdateUsers = 99

        self.onlineStates = {}
        self.onlineStates[0] = "Offline"
        self.onlineStates[1] = "Online"
        self.onlineStates[2] = "Busy"
        self.onlineStates[3] = "Away"
        self.onlineStates[4] = "Snooze"
        self.onlineStates[5] = "Looking for trade"
        self.onlineStates[6] = "Looking to play"

        # background updater methods
        self.registerWorker(self.updateUsers, 10800)
        self.registerWorker(self.checkForNewUsers, 10)
        self.registerWorker(self.updateUsersOnlineState, 60)

        # dashboard boxes
        # self.registerDashboardBox(self.dashboard_online_users, 'online1', {'loggedin': True})
        # self.registerDashboardBox(self.dashboard_online_users, 'online2', {'loggedin': True, 'template': 'box_Valve_online1.html'})
        self.registerDashboardBox(self.dashboard_games2weeks, 'games2weeks', {'title': 'Minutes played last two weeks','template': 'box_jQCloud.html'})
        self.registerDashboardBox(self.dashboard_games2weeks, 'gamesForever', {'title': 'Minutes played forever', 'template': 'box_jQCloud.html'})
        self.registerDashboardBox(self.dashboard_games2weeks, 'gamesUsers', {'title': 'Users own', 'template': 'box_jQCloud.html'})

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
            if hasattr(e, 'code'): 
                if e.code == 401:
                    logger.info("[%s] Unauthorized" % (self.handle))
                else:
                    logger.warning("[%s] Unhandled code: %s" % (self.handle, e))
            else:
                logger.warning("[%s] Unhandled error: %s" % (self.handle, e))
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
    def checkForNewUsers(self, logger = None):
        if not logger:
            logger = self.log
        self.getCache('users')
        allLinks = self.getNetworkLinks()
        check = False
        for link in allLinks:
            if link['network_data'] not in self.cache['users']:
                check = True
        if check:
            logger.info("[%s] New use(r)s found. Forcing update" % (self.handle))
            self.updateUsers()
            return "New users found"
        else:
            return "No new users found"

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
                    logger.debug("[%s] Owned games: %s" % (self.handle, len(ownedGames['games'])))
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
                    self.setCache("games")
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
                #if 'friends' not in self.cache['users'][steamId]:
                if True:
                    logger.info("[%s] Fetching friendslist for %s" % (self.handle, steamId))
                    steamFriends = self.fetchFromSteam('ISteamUser/GetFriendList/v0001', {'steamid': steamId,
                                                                                          'relationship': 'friend'})
                    if steamFriends != False:
                        if 'friends' not in steamFriends:
                            steamFriends['friends'] = []
                        self.cache['users'][steamId]['friends'] = steamFriends['friends']
                        logger.info("[%s] %s friends found for: %s" % (self.handle, len(steamFriends['friends']), steamId))
                    else:
                        logger.info("[%s] No friendslist revieved for: %s" % (self.handle, steamId))
                #if 'ownedGames' not in self.cache['users'][steamId]:
                if True:
                    logger.info("[%s] Fetching games for %s" % (self.handle, steamId))
                    ownedGames = self.fetchFromSteam('IPlayerService/GetOwnedGames/v0001', {'steamid': steamId,
                                                                                            'include_played_free_games': '1',
                                                                                            'include_appinfo': '1' })
                    self.cache['users'][steamId]['ownedGames'] = {}
                    if ownedGames:
                        if 'games' in ownedGames:
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
            return "%s users updated" % len(steamData['players'])
        else:
            return "Unable to recieve data from Steam"

    def updateUsersOnlineState(self, logger = None):
        count = 0
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
            count += len(fetchFriends)
            if len(fetchFriends) == 0:
                run = False
            else:
                logger.info("[%s] Fetching %s friends info" % (self.handle, len(fetchFriends)))
                steamFriends = self.fetchFromSteam('ISteamUser/GetPlayerSummaries/v0002', {'steamids': ','.join(fetchFriends)})
                if 'players' in steamFriends:
                    for friend in steamFriends['players']:
                        self.cache['users'][friend['steamid']]['personastate'] = friend['personastate']
                        if 'gameextrainfo' in friend:
                            self.cache['users'][friend['steamid']]['gameextrainfo'] = friend['gameextrainfo']
                        if 'gameid' in friend:
                            self.cache['users'][friend['steamid']]['gameid'] = friend['gameid']
                        else:
                            self.cache['users'][friend['steamid']]['gameid'] = None
                        if 'lastlogoff' in friend:
                            self.cache['users'][friend['steamid']]['lastlogoff'] = friend['lastlogoff']
                        if 'profilestate' in friend:
                            self.cache['users'][friend['steamid']]['profilestate'] = friend['profilestate']
        self.setCache("users")
        return "%s user states updated" % count

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
            result = []
            allLinks = self.getNetworkLinks()
            friends = []
            onlineFriends = {}
            steamId = self.getSessionValue(self.linkIdName)

            onlineOnly = False
            try:
                kwargs['onlineOnly']
                onlineOnly = True
            except KeyError:
                pass

            unknownOnly = False
            try:
                kwargs['unknownOnly']
                unknownOnly = True
            except KeyError:
                pass

            if unknownOnly:
                myFriends = [steamId]
                try:
                    for friend in self.cache['users'][steamId]['friends']:
                        myFriends.append(friend['steamid'])
                except KeyError:
                    pass
                friendsList = []
                for friend in self.cache['users'].keys():
                    if friend not in myFriends:
                        friendsList.append({ 'steamid': friend })
            else:
                friendsList = self.cache['users'][steamId]['friends']

            if steamId not in self.cache['users']:
                self.log.info("User probably not yet cached")
                return (False, False)

            for friend in friendsList:
                onlineFriends[friend['steamid']] = self.cache['users'][friend['steamid']]['personastate']

            for friend in friendsList:
                friendSteamId = friend['steamid']
                if onlineOnly:
                    if onlineFriends[friendSteamId] == 0:
                        continue

                linkId = None
                for link in allLinks:
                    if friendSteamId == link['network_data']:
                        linkId = link['user_id']

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
        if 'ownedGames' in self.cache['users'][partnerId]:
            for gameid in self.cache['users'][partnerId]['ownedGames']:
                try:
                    games.append(self.cache['games'][str(gameid)]['name'])
                except KeyError:
                    self.log.debug("Ignoring game ID %s" % gameid)
            self.setPartnerDetail(moreInfo, "Games", ', '.join(games))

            # games = []
            # for gameid in self.cache['users'][partnerId]['recentlyplayed']:
            #     try:
            #         games.append(self.cache['games'][str(gameid)]['name'])
            #     except KeyError:
            #         self.log.debug("Ignoring game ID %s" % gameid)
            # self.setPartnerDetail(moreInfo, "Recently Played", ', '.join(games))
        
        # self.setPartnerDetail(moreInfo, "Owned Games", steam_user.owned_games)

        # if steam_user.currently_playing:
        #     self.setPartnerDetail(moreInfo, "Currently Playing", steam_user.currently_playing.name)

        return moreInfo

    def admin(self):
        self.log.debug("Loading admin stuff")

    def findPartners(self):
        self.log.debug("Searching for new partners to play with")
        return self.getPartners(unknownOnly=True)

    # Helper
    def getGameStats(self):
        self.getCache('users')
        self.getCache('games')

        games2weeks = {}
        return2weeks = []

        gamesForever = {}
        returnForever = []

        gamesUsers = {}
        returnUsers = []
        for user in self.cache['users']:
            for game in self.cache['users'][user]['ownedGames']:
                if game not in games2weeks:
                    games2weeks[game] = 0
                try:
                    games2weeks[game] += int(self.cache['users'][user]['ownedGames'][game]['playtime_2weeks'])
                except KeyError as e:
                    pass

                if game not in gamesForever:
                    gamesForever[game] = 0
                try:
                    gamesForever[game] += int(self.cache['users'][user]['ownedGames'][game]['playtime_forever'])
                except KeyError as e:
                    pass

                if game not in gamesUsers:
                    gamesUsers[game] = 0
                try:
                    gamesUsers[game] += 1
                except KeyError as e:
                    pass

        for game in self.cache['games']:
            try:
                if games2weeks[game] > 0:
                    return2weeks.append({ 'text': self.cache['games'][game]['name'],
                                          'weight': games2weeks[game],
                                          'link': { 'href': 'http://store.steampowered.com/app/' + game + '/',
                                                    'target': '_blank'}})
            except KeyError as e:
                pass

            try:
                if gamesForever[game] > 0:
                    returnForever.append({ 'text': self.cache['games'][game]['name'],
                                           'weight': gamesForever[game],
                                           'link': { 'href': 'http://store.steampowered.com/app/' + game + '/',
                                                     'target': '_blank'}})
            except KeyError as e:
                pass

            try:
                if gamesUsers[game] > 0:
                    returnUsers.append({ 'text': self.cache['games'][game]['name'],
                                         'weight': gamesUsers[game],
                                         'link': { 'href': 'http://store.steampowered.com/app/' + game + '/',
                                                   'target': '_blank'}})
            except KeyError as e:
                pass

        return { 'games2weeks': getHighestRated(return2weeks, 'weight'),
                 'gamesForever': getHighestRated(returnForever, 'weight'),
                 'gamesUsers': getHighestRated(returnUsers, 'weight') }

    # Dashboard
    def dashboard_online_users(self, request):
        self.log.debug("Dashboard online users")
        return {'message': 'This is a test box'}

    def dashboard_games2weeks(self, request):
        self.log.debug("Dashboard games2weeks")
        return self.getGameStats()

    def dashboard_gamesForever(self, request):
        self.log.debug("Dashboard gamesForever")
        return self.getGameStats()

    def dashboard_gamesUsers(self, request):
        self.log.debug("Dashboard gamesUsers")
        return self.getGameStats()
