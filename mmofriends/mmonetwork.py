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

    def __init__(self, config):
        # loading config
        self.config = config.get()

        # setting variables
        self.longName = config.longName
        self.shortName = config.shortName

        self.log = logging.getLogger(__name__ + "." + self.shortName.lower())
        self.log.debug("Initializing MMONetwork: %s" % self.longName)

        self.icon = "Unset"
        self.comment = "Unset"
        self.description = "Unset"
        self.lastRefreshDate = 0
        self.hidden = False

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


# ts3 classes
class TS3Network(MMONetwork):

    def __init__(self, config):
        super(TS3Network, self).__init__(config)

        self.icon = "None"
        self.comment = "TS3 comment"
        self.description = "TS3 description"

        self.onlineclients = {}
        self.clients = {}

        self.connect()
        self.lastOnlineRefreshDate = 0
        self.fetchOnlineClients()

    def refresh(self):
        if self.lastRefreshDate > (time.time() - 10):
            self.log.debug("Not refreshing clients")
        else:
            self.log.debug("Refreshing all clients")
            self.lastRefreshDate = time.time()
            response = self.server.send_command('clientdblist')
            self.clients = {}
            for client in response.data:
                self.clients[client['client_unique_identifier']] = {
                    'client_unique_identifier': client['client_unique_identifier'],
                    'cldbid': client['cldbid'],
                    'client_lastip': client['client_lastip'],
                    'client_lastconnected': client['client_lastconnected'],
                    'client_totalconnections': client['client_totalconnections'],
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

    def getUserdetatilsByCldbid(self, cldbid):
        for client in self.clients.keys():
            if self.clients[client]['cldbid'] == cldbid:
                return self.clients[client]
        return None

    def fetchOnlineClients(self):
        if self.lastOnlineRefreshDate > (time.time() - 10):
            self.log.debug("Not refreshing online clients")
        else:
            self.lastOnlineRefreshDate = time.time()
            self.log.debug("Fetching online clients")
            response = self.server.send_command('clientlist')
            self.onlineclients = {}
            for client in response.data:
                self.onlineclients[client['client_database_id']] = {
                    'client_database_id': client['client_database_id'],
                    'client_nickname': client['client_nickname'],
                    'cid': client['cid'],
                    'clid': client['clid'],
                    'client_type': client['client_type']
                }
            self.log.info("Found %s online clients" % len(self.onlineclients))

    def getUserDetails(self, clid):
        self.log.debuf("Getting user details for clid: %s" % clid)
        self.refresh()
        for user in self.clients.keys():
            if self.clients[user]['cldbid'] == clid:
                return self.clients[user]
        return None

    def returnOnlineUserDetails(self):
        self.fetchOnlineClients()
        ret = []
        for cldbid in self.onlineclients.keys():
            print self.getUserdetatilsByCldbid(cldbid)
        return ret

    def listOnlineClients(self):
        for client in self.onlineclients.keys():
            if int(self.onlineclients[client]['client_type']) == 0:
                self.log.debug("Client %s: (dbid: %s, type: %s, cid: %s, clid: %s)" %
                    (self.onlineclients[client]['client_nickname'],
                        client,
                        self.onlineclients[client]['client_type'],
                        self.onlineclients[client]['cid'],
                        self.onlineclients[client]['clid'] ))