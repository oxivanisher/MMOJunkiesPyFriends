#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import ts3

import mmobase
import mmouser

# base classes
class MMONetworkConfig(object):

    def __init__(self, name = None, config = {}):
        self.log = logging.getLogger(__name__)
        self.log.debug("Initializing a mmonetwork config")
        self.name = name
        self.config = config

    def get(self):
        self.log.debug("Getting config %s" % self.name)
        return self.config

class MMONetworkProduct(object):

    def __init__(self, name):
        self.log = logging.getLogger(__name__)
        self.log.debug("Initializing network product %s" % name)
        self.name = name
        self.fields = []

    def addField(self, name, comment = "", fieldType = str):
        self.log.debug("Add a field with name, comment and fieldType")
        self.fields.append((name, fieldType))

class MMONetwork(object):

    def __init__(self, config):
        self.log = logging.getLogger(__name__)

        # loading config
        self.config = config.get()

        # setting variables
        self.name = self.config.name
        self.log.debug("Initializing mmonetwork %s" % self.name)

        self.icon = self.config.icon
        self.comment = self.config.comment
        self.description = self.config.description
        self.lastRefreshDate = 0
        self.hidden = False

        self.products = self.getProducts() #Fields: Name, Type (realm, char, comment)

        self.log.info("Initialized network: %s" % self.name)

    def refresh(self):
        self.log.debug("Refresh data from source")
        pass

    def link(self):
        self.log.debug("Link user to network %s" % self.name)
        pass

    def unlink(self):
        self.log.debug("Unlink network %s" % self.name)
        pass

    def listPartner(self, user):
        self.log.debug("List all partners for given user")
        pass

    def getProducts(self):
        self.log.debug("Fetches the products")
        pass


# ts3 classes
class TS3Network(MMONetwork):

    def __init__(self, config):
        super(TS3Network, self).__init__(config)

        self.onlineclients = {}

        self.connect()
        self.getOnlineClients()
        self.listOnlineClients()

    # helper functions
    def connect(self):
        self.log.info("Connecting to TS3 server")
        self.server = ts3.TS3Server(self.config['ip'], self.config['port'])
        self.server.login(self.config['username'], self.config['password'])
        self.server.use(self.config['serverid'])

    def getOnlineClients(self):
        self.log.debug("Fetching online clients")
        response = self.server.send_command('clientlist')
        self.onlineclients = {}
        for client in response.data:
            self.onlineclients[client['client_database_id']] = {
                'client_nickname': client['client_nickname'],
                'cid': client['cid'],
                'clid': client['clid'],
                'client_type': client['client_type']
            }
        self.log.info("Found %s online clients" % len(self.onlineclients))

    def listOnlineClients(self):
        for client in self.onlineclients.keys():
            self.log.debug("Client %s: (dbid: %s, type: %s, cid: %s, clid: %s)" %
                (self.onlineclients[client]['client_nickname'],
                    client,
                    self.onlineclients[client]['client_type'],
                    self.onlineclients[client]['cid'],
                    self.onlineclients[client]['clid'] ))