#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import ts3
import time

from mmofriends import db

# base classes
class MMONetworkConfig(object):

    def __init__(self, config = {}, shortName = None, longName = None):
        self.log = logging.getLogger(__name__ + ".cfg")
        self.longName = longName
        self.shortName = shortName
        self.log.debug("Initializing MMONetwork config: %s" % self.longName)
        self.config = config[shortName]

    def get(self):
        self.log.debug("Returning MMONetwork config: %s" % self.longName)
        return self.config

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

    def __init__(self, config, myId):
        # loading config
        self.config = config.get()

        # setting variables
        self.longName = config.longName
        self.shortName = config.shortName
        self.icon = self.config['icon']

        self.log = logging.getLogger(__name__ + "." + self.shortName.lower())
        self.log.debug("Initializing MMONetwork: %s" % self.longName)

        self.comment = "Unset"
        self.description = "Unset"
        self.moreInfo = 'NoMoreInfo'
        self.lastRefreshDate = 0
        self.hidden = False
        self.myId = myId

        self.products = self.getProducts() #Fields: Name, Type (realm, char, comment)

        self.log.info("Initialized network: %s (%s)" % (self.longName, self.shortName))

    def refresh(self):
        self.log.debug("Refresh data from source")
        pass

    def link(self):
        self.log.debug("Link user to network %s" % self.longName)
        pass

    def unlink(self):
        self.log.debug("Unlink network %s" % self.longName)
        pass

    def listPartner(self, user):
        self.log.debug("List all partners for given user")
        pass

    def getProducts(self):
        self.log.debug("MMONetwork %s: Fetching products" % self.shortName)
        pass

    def getNetworkDetails(self):
        return { 'networkId': self.myId,
                 'networkShortName': config.shortName,
                 'networkLongName': config.longName,
                 'networkMoreInfo': self.moreInfo
                }

    def setNetworkMoreInfo(self, moreInfo):
        self.moreInfo = moreInfo

    def setNetworkComment(self, comment):
        self.comment = comment

# ts3 classes
class TS3Network(MMONetwork):

    def __init__(self, config, myId):
        super(TS3Network, self).__init__(config, myId)

        self.description = "Team Speak 3 is like skype for gamers."

        self.onlineclients = {}
        self.clientDatabase = {}

        self.connect()
        self.lastOnlineRefreshDate = 0
        self.refresh()

    # helper functions
    def connect(self):
        self.log.info("Connecting to TS3 server")
        self.server = ts3.TS3Server(self.config['ip'], self.config['port'])
        self.server.login(self.config['username'], self.config['password'])
        self.server.use(self.config['serverid'])
        result = self.server.send_command('serverinfo')
        for server in result.data:
            if int(server['virtualserver_id']) == self.config['serverid']:
                self.setNetworkMoreInfo(server['virtualserver_name'])
                self.log.info("Connected to: %s" % self.moreInfo)

    def refresh(self):
        if self.lastOnlineRefreshDate > (time.time() - self.config['updateOnlineLock']):
            self.log.debug("Not refreshing online clients")
        else:
            self.lastOnlineRefreshDate = time.time()
            self.log.debug("Fetching online clients")
            clients = self.server.clientlist()
            self.onlineclients = {}
            for client in clients.keys():
                # ignoring console users
                if int(clients[client]['client_type']) != 1:
                    self.onlineclients[clients[client]['client_database_id']] = {
                        'client_database_id': int(clients[client]['client_database_id']),
                        'client_nickname': clients[client]['client_nickname'],
                        'cid': int(clients[client]['cid']),
                        'clid': int(clients[client]['clid']),
                        'client_type': int(clients[client]['client_type'])
                    }
            self.log.info("Found %s online clients" % len(self.onlineclients))

    # request from frontend
    def returnOnlineUserDetails(self):
        self.refresh()
        ret = []
        for cldbid in self.onlineclients.keys():
            # apperently currently not needed
            # myRet = self.fetchUserdetatilsByCldbid(cldbid)
            # if myRet:
            ret.append({'networkId': self.myId,
                        'networkName': self.longName,
                        'networkMoreInfo': self.moreInfo,
                        'id': 1234,
                        'nick': self.onlineclients[cldbid]['client_nickname'],
                        'moreInfo': "blah user comment"})
        return ret

    def fetchUserdetatilsByCldbid(self, cldbid):
        update = False
        try:
            if self.clientDatabase[cldbid]['lastUpdateDate'] < (time.time() - self.config['updateLock']):
                update = True
        except KeyError:
            update = True

        if update:
            self.log.debug("Fetching user details for cldbid: %s" % cldbid)
            response = self.server.send_command('clientdbinfo cldbid=%s' % cldbid)
            response.data[0]
            self.clientDatabase[cldbid] = response.data[0]
        else:
            self.log.debug("Not fetching user details for cldbid: %s" % cldbid)
        return self.clientDatabase[cldbid]
