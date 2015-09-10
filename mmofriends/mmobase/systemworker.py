#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

from mmonetwork import MMONetworkCache

# from mmofriends import db
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, InterfaceError, InvalidRequestError, OperationalError

db = SQLAlchemy()

# base class
class MMOSystemWorker(object):
    def __init__(self):
        self.handle = "unnamedSW"
        self.lastRun = 0
        self.timeout = 3600
        self.log = logging.getLogger(__name__ + "." + self.handle.lower())

        # activate debug while development
        self.setLogLevel(logging.DEBUG)

    def run(self, log):
        startTime = time.time()
        if (startTime - self.lastRun) > self.timeout:
            self.log.debug("[SW:%s] Running work method...")
            ret = self.work()
            endTime = time.time()
            self.lastRun = endTime
            self.log.debug("[SW:%s] Work method finished with return '%s'. Run took %s seconds." % (self.handle, ret, endTime - startTime))
            if ret:
                return (True, ret)
            else:
                return (False, "Worker gave no return value")

    def work(self):
        return "I should do something ..."

    # helper
    def getCache(self, name):
        try:
            ret = MMONetworkCache.query.filter_by(network_handle=self.handle, entry_name=name).first()
        except (IntegrityError, InterfaceError, InvalidRequestError) as e:
            db.session.rollback()
            self.log.warning("[SW:%s] SQL Alchemy Error on getCache: %s" % (self.handle, e))
            ret = False

        if ret:
            try:
                self.log.debug("[SW:%s] getCache - Loading %s Bytes of data to cache: %s" % (self.handle, len(ret.cache_data), name))
                self.cache[name] = json.loads(ret.cache_data)
            except ValueError as e:
                self.log.debug("[SW:%s] getCache - Setting up new cache: %s" % (self.handle, name))
                self.cache[name] = {}
        else:
            self.log.debug("[SW:%s] getCache - Setting up new cache: %s" % (self.handle, name))
            self.cache[name] = {}

    def setCache(self, name):
        ret = MMONetworkCache.query.filter_by(network_handle=self.handle, entry_name=name).first()
        if ret:
            self.log.debug("[SW:%s] setCache - Found existing cache: %s" % (self.handle, name))
        else:
            self.log.debug("[SW:%s] setCache - Created new cache: %s" % (self.handle, name))
            ret = MMONetworkCache(self.handle, name)

        try:
            ret.set(self.cache[name])
        except TypeError as e:
            self.log.warning("[SW:%s] setCache - Unable to set cache (TypeError): %s (%s)" % (self.handle, name, e))
            raise TypeError

        ret.last_update = int(time.time())
        db.session.merge(ret)
        try:
            db.session.flush()
            db.session.commit()
        except (IntegrityError, InterfaceError, InvalidRequestError) as e:
            db.session.rollback()
            self.log.warning("[SW:%s] SQL Alchemy Error on setCache: %s" % (self.handle, e))

# user checker
class MMOUserChecker(MMOSystemWorker):

    def __init__(self):
        super(MMOUserChecker, self).__init__(handle, timeout)
        self.handle = "userChecker"
        self.timetout = 20

    def work(self):
        return "I would check for users and stuff"