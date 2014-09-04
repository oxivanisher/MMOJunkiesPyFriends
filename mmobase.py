#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time

import mmonetwork
import mmouser

class MMOBase(object):

    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.log.info("Initializing mmobase")
        self.startupDate = time.time()
        self.lastRefreshDate = 0
        self.user = None #my user
        self.users = []
        self.networks = []
        self.startup()

    def startup(self):
        self.log.debug("Starting up")
        self.loadNetworks()
        self.loadUsers()
        pass

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

    def loadNetworks(self):
        self.log.debug("Load all networks")
        pass

    def loadUsers(self):
        self.log.debug("Load all users")
        pass