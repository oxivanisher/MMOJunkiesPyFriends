#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import ts3

import mmobase
import mmouser

# base classes
class MMONetworkConfig(object):

    def __init__(self, name = None, config = {}):
        """ initialize a mmonetwork config """
        self.name = name
        self.config = config
        self.log = logging.getLogger(__name__)

    def get(self):
        """ get config """
        return self.config

class MMONetworkProduct(object):

    def __init__(self, name):
        """ initialize a network product """
        self.name = name
        self.fields = []
        self.log = logging.getLogger(__name__)

    def addField(self, name, comment = "", fieldType = str):
        """ add a field with name, comment and fieldType """
        self.fields.append((name, fieldType))

class MMONetwork(object):

    def __init__(self, config):
        """ initialize mmonetwork """

        # loading config
        self.config = config.get()

        # setting variables
        self.name = self.config.name
        self.icon = self.config.icon
        self.comment = self.config.comment
        self.description = self.config.description
        self.lastRefreshDate = 0
        self.hidden = False

        self.log = logging.getLogger(__name__)
        self.products = self.getProducts() #Fields: Name, Type (realm, char, comment)

        self.log.info("Initialized network: %s" % self.name)

    def refresh(self):
        """ refresh data from source """
        pass

    def link(self):
        """ link user to network """
        pass

    def unlink(self):
        """ unlink network """
        pass

    def listPartner(self, user):
        """ list all partners for given user """
        pass

    def getProducts(self):
        """ fetches the products """
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