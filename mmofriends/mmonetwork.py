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
        self.clients = {}

        self.connect()
        self.lastOnlineRefreshDate = 0
        self.fetchOnlineClients()

    def refresh(self):
        if self.lastRefreshDate > (time.time() - self.config['updateLock']):
            self.log.debug("Not refreshing clients")
        else:
            self.log.debug("Refreshing all clients")
            self.lastRefreshDate = time.time()
            response = self.server.send_command('clientdblist')
            self.clients = {}
            for client in response.data:
                self.clients[client['client_unique_identifier']] = {
                    'client_unique_identifier': client['client_unique_identifier'],
                    'cldbid': int(client['cldbid']),
                    'client_lastip': client['client_lastip'],
                    'client_lastconnected': client['client_lastconnected'],
                    'client_totalconnections': int(client['client_totalconnections']),
                    'client_created': client['client_created'],
                    'client_nickname': client['client_nickname'],
                    'client_description': client['client_description']
                }

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

    def getUserdetatilsByCldbid(self, cldbid):
        for client in self.clients.keys():
            if self.clients[client]['cldbid'] == cldbid:
                return self.clients[client]
        return False

    def fetchOnlineClients(self):
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

    def getUserDetails(self, clid):
        self.log.debuf("Getting user details for clid: %s" % clid)
        self.refresh()
        for user in self.clients.keys():
            if self.clients[user]['cldbid'] == clid:
                return self.clients[user]
        return {}

    def returnOnlineUserDetails(self):
        self.fetchOnlineClients()
        ret = []
        for cldbid in self.onlineclients.keys():
            myRet = self.getUserdetatilsByCldbid(cldbid)
            if myRet:
                ret.append(myRet)
        return ret

    # tmp methods, delete please
    def listOnlineClients(self):
        for client in self.onlineclients.keys():
            self.log.debug("Client %s: (dbid: %s, type: %s, cid: %s, clid: %s)" %
                (self.onlineclients[client]['client_nickname'],
                    client,
                    self.onlineclients[client]['client_type'],
                    self.onlineclients[client]['cid'],
                    self.onlineclients[client]['clid'] ))