#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ts3

import mmonetworks

# server = ts3.TS3Server('127.0.0.1', 10011)
# server.login('serveradmin', 'secretpassword')

# choose virtual server
# server.use(1)

# create a channel
# response = server.send_command('channelcreate', keys={'channel_name': 'Just some channel'})

# id of the newly created channel
# channel_id = response.data[0]['cid']

# create a sub-channel
# server.send_command('channelcreate', keys={'channel_name': 'Just some sub-channel', 'cpid': channel_id})

class TS3Network(MMONetwork):

	def __init__(self, name):
		super(MMONetwork, self).__init__(name)

		self.server = None
		self.serverip = '127.0.0.1'
		self.username = 'serveradmin'
		self.password = 'secret'
		self.serverport = 10011
		self.serverid = 1

		self.connect()
		self.getclients()

	def connect(self):
		self.server = ts3.TS3Server(self.serverip, self.serverport)
		self.server.login(self.username, self.password)
		self.server.use(self.serverid)

	def getclients(self):
		response = self.server.send_command('clientlist')
		print response