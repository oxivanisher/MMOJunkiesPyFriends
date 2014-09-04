#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time

import mmobase
from mmonetwork import *

class MMOUserLevel(object):

	pass

class MMOUser(object):

	def __init__(self):
		self.log = logging.getLogger(__name__)
		self.log.debug("Initializing MMOUser")
		self.name = None
		self.nick = None
		self.email = None
		self.website = None
		self.password = None
		self.linkedNetworks = []
		self.joinedDate = time.time()
		self.lastLoginDate = 0
		self.lastRefreshDate = 0
		self.level = 0
		self.locked = False

	def lock(self):
		self.log.debug("Lock MMOUser %s" % self.getDisplayName())
		self.locked = True

	def unlock(self):
		self.log.debug("Unlock MMOUser %s" % self.getDisplayName())
		self.locked = False

	def refreshNetworks(self):
		self.log.debug("Refresh MMONetwork for MMOUser %s" % self.getDisplayName())
		pass

	def getDisplayName(self):
		return self.nick + " (" + self.name + ")"