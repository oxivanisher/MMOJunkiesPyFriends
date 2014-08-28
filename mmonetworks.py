#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import ts3


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


class TS3Network(MMONetwork):

    def __init__(self, config):
        super(TS3Network, self).__init__(config)

        self.connect()
        self.getclients()

    def connect(self):
        self.log.info("Connecting")
        self.server = ts3.TS3Server(self.config['ip'], self.config['port'])
        self.server.login(self.config['username'], self.config['password'])
        self.server.use(self.config['serverid'])

    def getclients(self):
        self.log.info("Get clients")
        response = self.server.send_command('clientlist')
        print response.data