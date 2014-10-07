#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
import hashlib
import time
import string
import random

from mmoutils import *
from flask.ext.sqlalchemy import SQLAlchemy
# from mmofriends import db, app
db = SQLAlchemy()

class MMOUserLevel(object):

    pass

class MMONetLink(db.Model):
    __tablename__ = 'mmonetlink'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey('mmouser.id'))
    user = db.relationship('MMOUser', backref=db.backref('links', lazy='dynamic'))
    network_handle = db.Column(db.String(20))
    network_data = db.Column(db.String(200))
    linked_date = db.Column(db.Integer)

    def __init__(self, user_id, network_handle, network_data = "", linked_date = 0):
        self.user_id = user_id
        self.network_handle = network_handle
        self.network_data = network_data
        if not linked_date:
            linked_date = int(time.time())
        self.linked_date = linked_date

    def __repr__(self):
        return '<MMONetLink %r>' % self.id


class MMOUserNick(db.Model):
    __tablename__ = 'mmousernick'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey('mmouser.id'))
    nick = db.Column(db.String(25))    

    def __init__(self, user_id, nick):
        self.user_id = user_id
        self.nick = nick

    def __repr__(self):
        return '<MMOUserNick %r' % self.id


class MMOUser(db.Model):
    __tablename__ = 'mmouser'

    id = db.Column(db.Integer, primary_key=True)
    nick = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(20), unique=False)
    email = db.Column(db.String(120), unique=True)
    website = db.Column(db.String(120), unique=False)
    password = db.Column(db.String(512), unique=False)
    joinedDate = db.Column(db.Integer, unique=False)
    lastLoginDate = db.Column(db.Integer, unique=False)
    lastRefreshDate = db.Column(db.Integer, unique=False)
    verifyKey = db.Column(db.String(32), unique=False)
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
        self.verifyKey = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
        self.load()

    def __repr__(self):
        return '<MMOUser %r>' % self.nick

    def load(self):
        self.log = logging.getLogger(__name__)
        self.log.debug("Loaded MMOUser: %s" % self.nick)

    def lock(self):
        self.log.debug("Lock MMOUser %s" % self.getDisplayName())
        self.locked = True

    def unlock(self):
        self.log.debug("Unlock MMOUser %s" % self.getDisplayName())
        self.locked = False

    def verify(self, key):
        if key == self.verifyKey:
            self.veryfied = True
            self.locked = False
            return True
        else:
            return False

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
