#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
import socket
import os
import random

from flask import current_app
from mmoutils import *
from mmouser import *
from mmonetwork import *
from mmofriends import db

# try:
#     from steamapi import *
# except ImportError:
#     print "Please install steamapi (https://github.com/smiley/steamapi)"
#     import sys
#     sys.exit(2)

class ValveNetwork(MMONetwork):

    def __init__(self, app, session, handle):
        super(ValveNetwork, self).__init__(app, session, handle)

    def test(self):
        # name = "oxivanisher"
        # try:
        #     core.APIConnection(api_key=self.config['apikey'])
        #     try:
        #         steam_user = user.SteamUser(userid=int(name))
        #     except ValueError: # Not an ID, but a vanity URL.
        #         steam_user = user.SteamUser(userurl=name)
        #     name = steam_user.name
        #     content = "Your real name is {0}. You have {1} friends and {2} games.".format(steam_user.real_name,
        #                                                                               len(steam_user.friends),
        #                                                                               len(steam_user.games))
        #     img = steam_user.avatar
        # except Exception as ex:
        #     # We might not have permission to the user's friends list or games, so just carry on with a blank message.
        #     content = None
        #     img = None

        # return content
        return "okies"

    # def setLogLevel(self, level):
    #     self.log.info("Setting loglevel to %s" % level)
    #     self.log.setLevel(level)

    # def refresh(self):
    #     self.log.debug("Refresh data from source")

    # def getLinkHtml(self):
    #     self.log.debug("Show linkHtml %s" % self.name)

    # def doLink(self, userId):
    #     self.log.debug("Link user %s to network %s" % (userId, self.name))

    # def finalizeLink(self, userKey):
    #     self.log.debug("Finalize user link to network %s" % self.name)

    # def saveLink(self, network_data):
    #     self.log.debug("Saving network link for user %s" % (self.session['nick']))
    #     netLink = MMONetLink(self.session['userid'], self.handle, network_data)
    #     db.session.add(netLink)
    #     db.session.commit()

    # def getNetworkLinks(self, userId = None):
    #     netLinks = []
    #     if userId:
    #         self.log.debug("Loading network links for userId %s" % (userId))
    #         for link in db.session.query(MMONetLink).filter_by(user_id=userId, network_handle=self.handle):
    #             netLinks.append({'network_data': link.network_data, 'linked_date': link.linked_date, 'user_id': link.user_id, 'id': link.id})
    #     else:
    #         self.log.debug("Loading all network links")
    #         for link in db.session.query(MMONetLink).filter_by(network_handle=self.handle):
    #             netLinks.append({'network_data': link.network_data, 'linked_date': link.linked_date, 'user_id': link.user_id, 'id': link.id})
    #     return netLinks

    # def unlink(self, user_id, netLinkId):
    #     try:
    #         link = db.session.query(MMONetLink).filter_by(user_id=user_id, id=netLinkId).first()
    #         db.session.delete(link)
    #         db.session.flush()
    #         self.log.info("Unlinked network with userid %s and netLinkId %s" % (user_id, netLinkId))
    #         return True
    #     except Exception as e:
    #         self.log.info("Unlinking network with userid %s and netLinkId %s failed" % (user_id, netLinkId))
    #         return False

    # def listPartners(self, user):
    #     self.log.debug("List all partners for given user")
    #     return {'id': 'someId',
    #             'nick': self.onlineClients[cldbid]['client_nickname'].decode('utf-8'),
    #             'networkText': channelName,
    #             'networkImgs': [{
    #                 'type': 'network',
    #                 'name': self.handle,
    #                 'title': self.name
    #             },{
    #                 'type': 'cache',
    #                 'name': 'icon_' + str(int(self.serverInfo['virtualserver_icon_id']) + 4294967296),
    #                 'title': ', '.join(moreInfo)
    #             },{
    #                 'type': 'cache',
    #                 'name': 'icon_' + channelIcon,
    #                 'title': channelName
    #             }],
    #             'friendImgs': [{
    #                 'type': 'cache',
    #                 'name': userGroupIcon,
    #                 'title': userGroupName
    #             },{
    #                 'type': 'cache',
    #                 'name': userGroupIcon,
    #                 'title': userGroupName
    #             }]
    #         }

    # def getPartnerDetails(self, partnerId):
    #     self.log.debug("List partner details")

    # def setPartnerFlag(self, myDict, key, value):
    #     try:
    #         myDict['flags']
    #     except KeyError:
    #         myDict['flags'] = []
    #     if value != '0' and value:
    #         myDict['flags'].append(key)

    # def setPartnerDetail(self, myDict, key, value):
    #     try:
    #         myDict['details']
    #     except KeyError:
    #         myDict['details'] = []
    #     if value != '0' and value:
    #         myDict['details'].append({'key': key, 'value': value})

    # def setPartnerAvatar(self, myDict, avatarName):
    #     if avatarName[0] == '/':
    #         avatarName = avatarName[1:]
    #     myDict['avatar'] = avatarName

    # def getProducts(self):
    #     self.log.debug("MMONetwork %s: Fetching products" % self.handle)

    # def setNetworkMoreInfo(self, moreInfo):
    #     self.moreInfo = moreInfo

    # def admin(self):
    #     self.log.debug("Loading admin stuff")