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

try:
    from steamapi import *
except ImportError:
    print "Please install steamapi (https://github.com/smiley/steamapi)"
    import sys
    sys.exit(2)

class ValveNetwork(MMONetwork):

    def __init__(self, app, session, handle):
        super(ValveNetwork, self).__init__(app, session, handle)

        self.steam_id_re = re.compile('steamcommunity.com/openid/id/(.*?)$')
        self.description = "Steam network from Valve"
        # self.linkIdName = 'steamId'

        try:
            # core.APIConnection(api_key=self.config['apikey'], precache=True)
            core.APIConnection(api_key=self.config['apikey'])
        except Exception as e:
            self.log.warning("Unable to set apikey")

        # self.steamData = {}

        # activate debug while development
        self.setLogLevel(logging.DEBUG)

    # helper methods
    def get_steam_userinfo(self, steam_id):
        self.getCache('users')
        if steam_id not in self.cache['users'].keys():
            options = {
                'key': self.config['apikey'],
                'steamids': steam_id
            }
            url = 'http://api.steampowered.com/ISteamUser/' \
                  'GetPlayerSummaries/v0001/?%s' % urllib.urlencode(options)
            rv = json.load(urllib2.urlopen(url))
            self.cache['users'][steam_id] = rv['response']['players']['player'][0]
            self.setCache('users')
        return self.cache['users'][steam_id] or {}

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
        steamdata = self.get_steam_userinfo(self.getSessionValue(self.linkIdName))
        # self.steamData[self.getSessionValue(self.linkIdName)] = steamdata
        self.saveLink(self.getSessionValue(self.linkIdName))
        try:
            shownName = steamdata['personaname']
        except KeyError:
            shownName = steamdata['name']

        try:
            additionalName = steamdata['realname']
        except KeyError:
            additionalName = ""

        return ('You are logged in to Steam as %s (%s)' % (shownName, additionalName), oid.get_next_url())
        # return ('You are logged in to Steam as %s (%s)' % (steamdata['personaname'], steamdata['realname']), oid.get_next_url())

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
            # try:
            for friend in self.getSteamUser(self.getSessionValue(self.linkIdName)).friends:
                self.getPartnerDetails(friend.steamid)
                self.cacheFile(friend.avatar)
                self.cacheFile(friend.avatar_full)
                friendImgs = []
                try:
                    friendImgs.append({
                                    'type': 'flag',
                                    'name': friend.country_code.lower(),
                                    'title': friend.country_code
                                    })
                except Exception:
                    pass

                friendImgs.append({
                                    'type': 'cache',
                                    'name': friend.avatar.split('/')[-1],
                                    'title': friend.real_name
                                })

                result.append({ 'id': friend.steamid,
                                'nick': friend.name,
                                'state': friend.state,
                                # 'state': OnlineState(friend.state),
                                # state() == OnlineState.OFFLINE
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
            # except Exception as e:
            #     self.log.warning("Unable to connect to Steam Network: %s" % e)
            #     return (False, "Unable to connect to Steam Network: %s" % e)
        else:
            return (True, {})

    def getPartnerDetails(self, partnerId):
        self.getCache('users')
        self.getCache('games')
        self.getCache('groups')

        self.log.debug("List partner details for: %s" % partnerId)
        if partnerId not in self.cache['users'].keys():
            self.log.debug("Fetch user data for: %s" % partnerId)
            steam_user = self.getSteamUser(partnerId)
            self.cache['users'][partnerId] = {}
            self.cache['users'][partnerId]['steamid'] = steam_user.steamid
            self.cache['users'][partnerId]['real_name'] = steam_user.real_name
            self.cache['users'][partnerId]['country_code'] = steam_user.country_code
            try:
                self.cache['users'][partnerId]['last_logoff'] = time.mktime(steam_user.last_logoff.timetuple())
            except KeyError:
                pass
            self.cache['users'][partnerId]['profile_url'] = steam_user.profile_url
            self.cache['users'][partnerId]['state'] = steam_user.state
            self.cache['users'][partnerId]['level'] = steam_user.level
            self.cache['users'][partnerId]['xp'] = steam_user.xp
            # self.cache['users'][partnerId]['time_created'] = time.mktime(steam_user.time_created.timetuple())
            self.cache['users'][partnerId]['avatar'] = self.cacheFile(steam_user.avatar_full)
            self.cache['users'][partnerId]['primary_group'] = steam_user.group.guid

            try:
                games = []
                for game in steam_user.games:
                    if game.id not in self.cache['games'].keys():
                        self.cache['games'][game.id] = {}
                        self.cache['games'][game.id]['id'] = game.id
                        self.cache['games'][game.id]['name'] = game.name
                        self.setCache('games')
                    games.append(game.id)
            except TypeError:
                pass
            self.cache['users'][partnerId]['games'] = games

            try:
                recent = []
                for game in steam_user.recently_played:
                    recent.append(game.id)
            except TypeError:
                pass
            self.cache['users'][partnerId]['recently_played'] = recent

            try:
                badges = []
                for badge in steam_user.badges:
                    badges.append(badge.id)
            except TypeError:
                pass
            self.cache['users'][partnerId]['badges'] = badges

            # print "steam_user.groups", steam_user.groups
            # try:
            #     groups = []
            #     for group in steam_user.groups:
            #         if group.guid not in self.cache['groups'].keys():
            #             self.cache['groups'][group.id] = {}
            #             self.cache['groups'][group.id]['id'] = group.gid
            #             self.cache['groups'][group.id]['name'] = group.name
            #             self.setCache('groups')
            #         groups.append(group.id)
            # except TypeError:
            #     pass
            # self.cache['users'][partnerId]['groups'] = groups

            self.setCache('users')

        moreInfo = {}

        # avatar = steam_user.avatar_full.split('/')[-1]

        self.setPartnerAvatar(moreInfo, self.cache['users'][partnerId]['avatar'])

        if self.session.get('admin'):
            self.setPartnerDetail(moreInfo, "Steam ID", self.cache['users'][partnerId]['steamid'])
            self.setPartnerDetail(moreInfo, "Real Name", self.cache['users'][partnerId]['real_name'])

        self.setPartnerDetail(moreInfo, "Country Code", self.cache['users'][partnerId]['country_code'])
        try:
            self.setPartnerDetail(moreInfo, "Created", timestampToString(self.cache['users'][partnerId]['time_created']))
        except KeyError:
            pass
        try:
            self.setPartnerDetail(moreInfo, "Last Logoff", timestampToString(self.cache['users'][partnerId]['last_logoff']))
        except KeyError:
            pass
        self.setPartnerDetail(moreInfo, "Profile URL", self.cache['users'][partnerId]['profile_url'])
        self.setPartnerDetail(moreInfo, "Online/Offline", self.cache['users'][partnerId]['state'])
        self.setPartnerDetail(moreInfo, "Level", self.cache['users'][partnerId]['level'])
        self.setPartnerDetail(moreInfo, "XP", self.cache['users'][partnerId]['xp'])

        games = []
        for gameid in self.cache['users'][partnerId]['games']:
            try:
                games.append(self.cache['games'][str(gameid)]['name'])
            except KeyError:
                self.log.debug("Ignoring game ID %s" % gameid)
        self.setPartnerDetail(moreInfo, "Games", ', '.join(games))

        games = []
        for gameid in self.cache['users'][partnerId]['recently_played']:
            try:
                games.append(self.cache['games'][str(gameid)]['name'])
            except KeyError:
                self.log.debug("Ignoring game ID %s" % gameid)
        self.setPartnerDetail(moreInfo, "Recently Played", ', '.join(games))
        
        # self.setPartnerDetail(moreInfo, "Badges", steam_user.badges)
        # self.setPartnerDetail(moreInfo, "Owned Games", steam_user.owned_games)

        if self.cache['users'][partnerId]['primary_group']:
            self.setPartnerDetail(moreInfo, "Primary Group", self.cache['users'][partnerId]['primary_group'])

        # groups = []
        # for group in self.cache['users'][partnerId]['groups']:
        #     groups.append(self.cache['users'][group]['name'])
        # self.setPartnerDetail(moreInfo, "Groups", ', '.join(groups))

        # if steam_user.currently_playing:
        #     self.setPartnerDetail(moreInfo, "Currently Playing", steam_user.currently_playing.name)

        return moreInfo

    # def setNetworkMoreInfo(self, moreInfo):
    #     self.moreInfo = moreInfo

    def admin(self):
        self.log.debug("Loading admin stuff")

    # steam methods
    def getSteamUser(self, name):
        self.log.debug("getSteamUser %s" % name)
        try:
            steam_user = user.SteamUser(userid=int(name))
        except ValueError: # Not an ID, but a vanity URL.
            steam_user = user.SteamUser(userurl=name)
        except APIUnauthorized:
            return False
        return steam_user        
