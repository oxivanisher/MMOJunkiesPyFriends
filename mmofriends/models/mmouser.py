#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
import hashlib
import time
import string
import random

from sqlalchemy import Boolean, Column, Integer, String, UnicodeText, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, backref

from mmofriends.mmoutils import *
from mmofriends.database import db_session, Base
from paypal import MMOPayPalPayment

class MMOUserLevel(object):
    pass

class MMONetLink(Base):
    __tablename__ = 'mmonetlink'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('mmouser.id'))
    user = relationship('MMOUser', backref=backref('links', lazy='dynamic'))
    network_handle = Column(String(20))
    network_data = Column(String(200))
    linked_date = Column(Integer)

    __table_args__ = (UniqueConstraint(user_id, network_handle, name="userid_network_handle_uc"), )

    def __init__(self, user_id, network_handle, network_data = "", linked_date = 0):
        self.user_id = user_id
        self.network_handle = network_handle
        self.network_data = network_data
        if not linked_date:
            linked_date = int(time.time())
        self.linked_date = linked_date

    def __repr__(self):
        return '<MMONetLink %r>' % self.id


class MMOUserNick(Base):
    __tablename__ = 'mmousernick'

    id = Column(Integer, primary_key=True)
    user = relationship('MMOUser', backref=backref('nicks', lazy='dynamic'))
    user_id = Column(Integer, ForeignKey('mmouser.id'))
    nick = Column(String(25))    

    __table_args__ = (UniqueConstraint(user_id, nick, name="userid_nick_uc"), )

    def __init__(self, user_id, nick):
        self.user_id = user_id
        self.nick = nick

    def __repr__(self):
        return '<MMOUserNick %r' % self.id


class MMOUser(Base):
    __tablename__ = 'mmouser'

    id = Column(Integer, primary_key=True)
    nick = Column(String(20), unique=True)
    name = Column(String(20), unique=False)
    email = Column(String(120), unique=True)
    website = Column(String(120), unique=False)
    password = Column(String(512), unique=False)
    joinedDate = Column(Integer, unique=False)
    lastLoginDate = Column(Integer, unique=False)
    lastRefreshDate = Column(Integer, unique=False)
    verifyKey = Column(String(32), unique=False)
    admin = Column(Boolean)
    locked = Column(Boolean)
    veryfied = Column(Boolean)

    def __init__(self, nick):
        self.log = logging.getLogger(__name__)
        self.log.debug("[User] Initializing MMOUser %s" % self.getDisplayName())
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
        self.donated = float(0)
        self.load()

    def __repr__(self):
        return '<MMOUser %r>' % self.nick

    def load(self):
        self.log = logging.getLogger(__name__)
        self.loadDonations()
        self.log.debug("[User] Loaded MMOUser %s" % (self.getDisplayName()))

    def lock(self):
        self.log.debug("[User] Lock MMOUser %s" % (self.getDisplayName()))
        self.locked = True

    def unlock(self):
        self.log.debug("[User] Unlock MMOUser %s" % (self.getDisplayName()))
        self.locked = False

    def verify(self, key):
        if key == self.verifyKey:
            self.veryfied = True
            self.locked = False
            return True
        else:
            return False

    def refreshNetworks(self):
        self.log.debug("[User] Refresh MMONetwork for MMOUser %s" % (self.getDisplayName()))
        pass

    def getDisplayName(self):
        if self.name:
            return self.nick + " (" + self.name + ")"
        else:
            return self.nick

    def setPassword(self, password):
        self.log.info("[User] Setting new Password for MMOUser %s" % (self.getDisplayName()))
        hash_object = hashlib.sha512(password)
        self.password = hash_object.hexdigest()

    def checkPassword(self, password):
        self.log.info("[User] Checking password for MMOUser %s" % (self.getDisplayName()))
        hash_object = hashlib.sha512(password)
        if self.password == hash_object.hexdigest():
            return True
        else:
            return False

    def addNick(self, nick = None):
        self.log.info("[User] Adding Nick: %s for MMOUser %s" % (nick, self.getDisplayName()))
        if nick:
            newNick = MMOUserNick(self.id, nick)
            try:
                db_session.add(newNick)
                runQuery(db_session.commit)
            except Exception as e:
                self.log.warning("[User] SQL Alchemy Error: %s" % e)
                return False
            return True
        return False

    def removeNick(self, nickId = None):
        self.log.info("[User] Removing NickID: %s for MMOUser %s" % (nickId, self.getDisplayName()))
        if nickId:
            try:
                oldNick = runQuery(MMOUserNick.query.filter_by(id=nickId, user_id=self.id).first)
            except Exception as e:
                self.log.warning("[User] SQL Alchemy Error on removeNick: %s" % (e))
                return False

            try:
                db_session.delete(oldNick)
                runQuery(db_session.commit)
            except Exception as e:
                self.log.warning("[User] SQL Alchemy Error: %s" % e)
                return False
            return True
        return False

    def loadDonations(self):
        self.log.debug("[User] Calculating donations for MMOUser %s" % (self.getDisplayName()))
        amount = float(0)
        try:
            donations = MMOPayPalPayment.query.filter_by(custom=self.id, payment_status="Completed", response_string="Verified", item_name="MMOJunkies")
            for donation in donations:
                amount += float(donation.payment_amount)
        except Exception as e:
            self.log.warning("[User] SQL Alchemy Error: %s" % e)
        self.donated = amount

