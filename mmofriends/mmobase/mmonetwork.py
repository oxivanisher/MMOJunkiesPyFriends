#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
import socket
import os
import random

from flask import current_app
from mmoutils import *
from flask.ext.sqlalchemy import SQLAlchemy
# from mmofriends import db, app
db = SQLAlchemy()

class MMONetworkProduct(object):

    def __init__(self, name):
        self.log = logging.getLogger(__name__)
        self.log.debug("Initializing MMONetwork product %s" % name)
        self.name = name
        self.fields = []

    def addField(self, name, comment = "", fieldType = str):
        self.log.debug("Add a field with name, comment and fieldType")
        self.fields.append((name, fieldType))

class MMONetwork(object):

    def __init__(self, app, session, shortName):
        # loading config
        self.app = app
        self.session = session
        self.shortName = shortName
        self.config = self.app.config['networkConfig'][shortName]

        # setting variables
        self.longName = self.config['longName']
        self.icon = self.config['icon']

        self.log = logging.getLogger(__name__ + "." + self.shortName.lower())
        self.log.debug("Initializing MMONetwork: %s" % self.longName)

        self.comment = "Unset"
        self.description = "Unset"
        self.moreInfo = 'NoMoreInfo'
        self.lastRefreshDate = 0
        self.hidden = False

        self.products = self.getProducts() #Fields: Name, Type (realm, char, comment)

        self.log.info("Initialized network: %s (%s)" % (self.longName, self.shortName))

    def refresh(self):
        self.log.debug("Refresh data from source")

    def showLinkHtml(self):
        self.log.debug("Show linkHtml %s" % self.longName)

    def doLink(self):
        self.log.debug("Link user to network %s" % self.longName)

    def unlink(self):
        self.log.debug("Unlink network %s" % self.longName)

    def listPartners(self, user):
        self.log.debug("List all partners for given user")
        return {'id': 'someId',
                'nick': self.onlineClients[cldbid]['client_nickname'].decode('utf-8'),
                'networkText': channelName,
                'networkImgs': [{
                    'type': 'network',
                    'name': self.shortName,
                    'title': self.longName
                },{
                    'type': 'cache',
                    'name': 'icon_' + str(int(self.serverInfo['virtualserver_icon_id']) + 4294967296),
                    'title': ', '.join(moreInfo)
                },{
                    'type': 'cache',
                    'name': 'icon_' + channelIcon,
                    'title': channelName
                }],
                'friendImgs': [{
                    'type': 'cache',
                    'name': userGroupIcon,
                    'title': userGroupName
                },{
                    'type': 'cache',
                    'name': userGroupIcon,
                    'title': userGroupName
                }]
            }

    def getPartnerDetails(self, partnerId):
        self.log.debug("List partner details")

    def setPartnerFlag(self, myDict, key, value):
        try:
            myDict['flags']
        except KeyError:
            myDict['flags'] = []
        if value != '0' and value:
            myDict['flags'].append(key)

    def setPartnerDetail(self, myDict, key, value):
        try:
            myDict['details']
        except KeyError:
            myDict['details'] = []
        if value != '0' and value:
            myDict['details'].append({'key': key, 'value': value})

    def setPartnerAvatar(self, myDict, avatarName):
        if avatarName[0] == '/':
            avatarName = avatarName[1:]
        myDict['avatar'] = avatarName

    def getProducts(self):
        self.log.debug("MMONetwork %s: Fetching products" % self.shortName)

    def setNetworkMoreInfo(self, moreInfo):
        self.moreInfo = moreInfo

    def setNetworkComment(self, comment):
        self.comment = comment
