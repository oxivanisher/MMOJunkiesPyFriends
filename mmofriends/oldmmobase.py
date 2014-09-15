#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time

from mmofriends import db

from config import *
from mmonetwork import *
from mmouser import *

class MMOBase(object):

    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.log.debug("Initializing MMOBase")
        # self.db = db
        self.startupDate = time.time()
        self.lastRefreshDate = 0
        self.user = None #my user
        self.users = []
        self.networks = []
        self.startup()
        self.networkConfig = None

    def startup(self):
        self.log.info("Starting up")

        # load network configs
        self.networkConfig = YamlConfig("config/mmonetworks.yml").get_values()

        # test = MMOUser('testuser')
        # db.session.add(test)
        # db.session.commit()

        # self.loadNetworks()
        # self.loadUsers()

    def login(self):
        self.log.debug("Login user %s" % self.user.getDisplayName())
        pass

    def logout(self):
        self.log.debug("Logout user %s" % self.user.getDisplayName())
        pass

    def searchPartners(self):
        self.log.debug("Search partners on all networks and products")
        pass

    def notify(self, user):
        self.log.debug("Notify a single user")
        pass

    def notifyAll(self):
        self.log.debug("Notify all users")
        pass

    def lockUser(self, user):
        self.log.debug("Lock user %s" % user.getDisplayName())
        pass

    def unlockUser(self, user):
        self.log.debug("Unlock user %s" % user.getDisplayName())
        pass

    def refreshAllUsers(self, force = False):
        self.log.debug("Refresh all users where needed if not forced")
        pass

    def loadNetwork(self, handle, name):
        self.log.debug("Loading MMONetwork: %s" % name)
        self.networks.append(TS3Network(MMONetworkConfig(self.networkConfig, handle, name)))

    def loadNetworks(self):
        self.log.debug("Loading all MMONetworks")

        self.loadNetwork("TS3", "Team Speak 3")
    
    def loadUsers(self):
        self.log.debug("Load all users")
        pass
