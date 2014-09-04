#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time

import mmonetwork
import mmouser

class MMOBase(object):

    def __init__(self):
        """ initialize mmobase """
        self.log = logging.getLogger(__name__)
        self.startupDate = time.time()
        self.lastRefreshDate = 0
        self.user = None #my user
        self.users = []

    def login(self):
        """ login user """
        pass

    def logout(self):
        """ logout user """
        pass

    def searchPartners(self):
        """ search partners on all networks and products """
        pass

    def notify(self, user):
        """ notify a single user """
        pass

    def notifyAll(self):
        """ notify all users """
        pass

    def lockUser(self, user):
        """ lock user """
        pass

    def unlockUser(self, user):
        """ unlock user """
        pass

    def refreshAllUsers(self, force = False):
        """ refresh all users where needed if not forced """
        pass

