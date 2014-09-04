#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time

import mmobase
import mmonetwork

class MMOUserLevel(object):

	pass

class MMOUser(object):

	def __init__(self):
		""" initialized mmouser """
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
		""" lock user """
		self.locked = True

	def unlock(self):
		""" unlock user """
		self.locked = False

	def refreshNetworks(self):
		""" refresh networks """
		pass