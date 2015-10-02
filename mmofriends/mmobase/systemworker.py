#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import json

from mmonetwork import MMONetworkCache

# from mmofriends import db
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, InterfaceError, InvalidRequestError, OperationalError

db = SQLAlchemy()

# base class
class MMOSystemWorker(object):
    def __init__(self):
        self.lastRun = 0
        self.log = logging.getLogger(__name__ + "." + self.handle.lower())
        self.cache = {}

        # activate debug while development
        self.setLogLevel(logging.DEBUG)

        self.getCache('backgroundTasks')
        if self.handle not in self.cache['backgroundTasks']:
            self.cache['backgroundTasks'][self.handle] = {}
            self.cache['backgroundTasks'][self.handle]['handle'] = "System"
            self.cache['backgroundTasks'][self.handle]['method'] = self.handle
            self.cache['backgroundTasks'][self.handle]['timeout'] = self.timeout
            self.cache['backgroundTasks'][self.handle]['start'] = 0
            self.cache['backgroundTasks'][self.handle]['end'] = 0
            self.setCache('backgroundTasks')

    def run(self):
        startTime = time.time()
        if (startTime - self.lastRun) > self.timeout:
            self.cache['backgroundTasks'][self.handle]['start'] = time.time()
            self.setCache('backgroundTasks')

            self.log.debug("[SW:%s] Running work method...")
            ret = self.work()
            endTime = time.time()
            self.lastRun = endTime
            self.log.debug("[SW:%s] Work method finished with return '%s'. Run took %s seconds." % (self.handle, ret, endTime - startTime))

            self.getCache('backgroundTasks')
            self.cache['backgroundTasks'][self.handle]['end'] = time.time()
            self.cache['backgroundTasks'][self.handle]['result'] = ret
            self.setCache('backgroundTasks')

            return ret

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
            self.log.debug("set")
            ret.set(self.cache[name])
        except TypeError as e:
            self.log.warning("[SW:%s] setCache - Unable to set cache (TypeError): %s (%s)" % (self.handle, name, e))
            raise TypeError

        ret.last_update = int(time.time())
        self.log.debug("merge")
        db.session.merge(ret)
        try:
            self.log.debug("flush")
            db.session.flush()
            self.log.debug("commit")
            db.session.commit()
        except (IntegrityError, InterfaceError, InvalidRequestError) as e:
            db.session.rollback()
            self.log.warning("[SW:%s] SQL Alchemy Error on setCache: %s" % (self.handle, e))

    def setLogLevel(self, level):
        self.log.info("[SW:%s] Setting loglevel to %s" % (self.handle, level))
        self.log.setLevel(level)

# user checker
class MMOUserChecker(MMOSystemWorker):

    def __init__(self):
        self.handle = "userChecker"
        self.timeout = 20
        super(MMOUserChecker, self).__init__()

    def work(self):
        return "I would check for users and stuff"