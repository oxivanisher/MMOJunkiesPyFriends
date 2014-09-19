#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
import os
import random
import urllib2
import urllib
import re

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
        options = {
            'key': self.config['apikey'],
            'steamids': steam_id
        }
        url = 'http://api.steampowered.com/ISteamUser/' \
              'GetPlayerSummaries/v0001/?%s' % urllib.urlencode(options)
        rv = json.load(urllib2.urlopen(url))
        return rv['response']['players']['player'][0] or {}

    def cacheFile(self, url):
        outputFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../static/cache', url.split('/')[-1])

        if os.path.isfile(outputFilePath):
            self.log.debug("Not downloading %s" % url)
        else:
            self.log.info("Downloading %s" % url)

            avatarFile = urllib.URLopener()
            avatarFile.retrieve(url, outputFilePath)
        return True

    # oid methods
    def oid_login(self, oid):
        self.log.debug("OID Login")
        if self.getSessionValue('steamId') is not None:
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
        self.setSessionValue('steamId', match.group(1))
        steamdata = self.get_steam_userinfo(self.getSessionValue('steamId'))
        # self.steamData[self.getSessionValue('steamId')] = steamdata
        self.saveLink(self.getSessionValue('steamId'))
        return ('You are logged in to Steam as %s (%s)' % (steamdata['personaname'], steamdata['realname']), oid.get_next_url())
        # return ('You are logged in to Steam as %s (%s)' % (steamdata['personaname'], steamdata['realname']), oid.get_next_url())

    # overwritten class methods
    def getLinkHtml(self):
        self.log.debug("Show linkHtml %s" % self.name)
        htmlFields = {}
        if not self.getSessionValue('steamId'):
            htmlFields['oid'] = {'comment': "Click to login with Steam.", 'image': "//steamcommunity-a.akamaihd.net/public/images/signinthroughsteam/sits_small.png"}
        return htmlFields

    def loadLinks(self, userId):
        self.log.debug("Loading user links for userId %s" % userId)
        self.setSessionValue('steamId', None)
        for link in self.getNetworkLinks(userId):
            self.setSessionValue('steamId', link['network_data'])

    def devTest(self):
        # have fun: https://github.com/smiley/steamapi/blob/master/steamapi/user.py
        return "steamId: %s" % self.getSessionValue('steamId')

    def getPartners(self):
        self.log.debug("List all partners for given user")
        if not self.getSessionValue('steamId'):
            return (False, False)
        if self.getSessionValue('steamId'):
            result = []
            # try:
            for friend in self.getSteamUser(self.getSessionValue('steamId')).friends:
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
        self.log.debug("List partner details")
        steam_user = self.getSteamUser(partnerId)
        moreInfo = {}

        avatar = steam_user.avatar_full.split('/')[-1]

        self.setPartnerAvatar(moreInfo, avatar)

        self.setPartnerDetail(moreInfo, "Country Code", steam_user.country_code)
        # self.setPartnerDetail(moreInfo, "Created", steam_user.time_created)
        self.setPartnerDetail(moreInfo, "Last Logoff", steam_user.last_logoff)
        self.setPartnerDetail(moreInfo, "Profile URL", steam_user.profile_url)
        self.setPartnerDetail(moreInfo, "Online/Offline", steam_user.state)
        self.setPartnerDetail(moreInfo, "Level", steam_user.level)
        self.setPartnerDetail(moreInfo, "XP", steam_user.xp)
        # self.setPartnerDetail(moreInfo, "Badges", steam_user.badges)

        try:
            recent = []
            for game in steam_user.recently_played:
                recent.append(game.name)
            self.setPartnerDetail(moreInfo, "Recently Played", ', '.join(recent))
        except TypeError:
            pass
        
        try:
            games = []
            for game in steam_user.games:
                games.append(game.name)
            self.setPartnerDetail(moreInfo, "Games", ', '.join(games))
        except TypeError:
            pass
        
        # self.setPartnerDetail(moreInfo, "Owned Games", steam_user.owned_games)

        if steam_user.group:
            self.setPartnerDetail(moreInfo, "Primary Group", steam_user.group.guid)

        # groups = []
        # for group in steam_user.groups:
        #     group.append(group.guid)
        # self.setPartnerDetail(moreInfo, "Groups", ', '.join(groups))

        if steam_user.currently_playing:
            self.setPartnerDetail(moreInfo, "Currently Playing", steam_user.currently_playing.name)

        if self.session.get('admin'):
            self.setPartnerDetail(moreInfo, "Steam ID", steam_user.steamid)
            self.setPartnerDetail(moreInfo, "Real Name", steam_user.real_name)

        return moreInfo

    # def setNetworkMoreInfo(self, moreInfo):
    #     self.moreInfo = moreInfo

    def admin(self):
        self.log.debug("Loading admin stuff")

    # steam methods
    def getSteamUser(self, name):
        try:
            steam_user = user.SteamUser(userid=int(name))
        except ValueError: # Not an ID, but a vanity URL.
            steam_user = user.SteamUser(userurl=name)
        return steam_user        
