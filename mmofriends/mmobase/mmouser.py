#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
import hashlib

from mmoutils import *
from mmofriends import db

class MMOUserLevel(object):

    pass

class MMOUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nick = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(20), unique=False)
    email = db.Column(db.String(120), unique=True)
    website = db.Column(db.String(120), unique=False)
    password = db.Column(db.String(20), unique=False)
    joinedDate = db.Column(db.Integer, unique=False)
    lastLoginDate = db.Column(db.Integer, unique=False)
    lastRefreshDate = db.Column(db.Integer, unique=False)
    admin = db.Column(db.Boolean)
    locked = db.Column(db.Boolean)
    veryfied = db.Column(db.Boolean)

    def __init__(self, nick):
        self.log = logging.getLogger(__name__)
        self.log.debug("Initializing MMOUser: %s" % nick)
        self.nick = nick
        self.name = None
        self.email = None
        self.website = None
        self.password = None
        self.linkedNetworks = []
        self.joinedDate = int(time.time())
        self.lastLoginDate = 0
        self.lastRefreshDate = 0
        self.admin = False
        self.locked = True
        self.veryfied = False
        self.load()

    # def __repr__(self):
    #     return '<MMOUser %r>' % self.nick

    def load(self):
        self.log = logging.getLogger(__name__)
        self.log.debug("Loaded MMOUser: %s" % self.nick)

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

    def setPassword(self, password):
        self.log.info("Setting new Password")
        hash_object = hashlib.sha512(password)
        self.password = hash_object.hexdigest()

    def checkPassword(self, password):
        self.log.info("Checking password")
        hash_object = hashlib.sha512(password)
        if self.password == hash_object.hexdigest():
            return True
        else:
            return False
