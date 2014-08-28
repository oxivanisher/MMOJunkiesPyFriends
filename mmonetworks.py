#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import ts3

# base classes
class TS3NetworkConfig(object):

    def __init__(self, name = None, config = {}):
        self.name = name
        self.config = config

    def get(self):
        return self.config


class MMONetwork(object):

    def __init__(self, config):
        self.config = config.get()
        self.name = config.name
        self.log = logging.getLogger(__name__)
        self.log.info("Initialized network: %s" % self.name)


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