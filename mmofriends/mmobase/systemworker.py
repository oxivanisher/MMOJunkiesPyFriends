#!/usr/bin/env python
# -*- coding: utf-8 -*-

# http://stackoverflow.com/questions/12044776/how-to-use-flask-sqlalchemy-in-a-celery-task

import time
import logging
import json

from mmofriends.mmoutils import *
from mmofriends.database import *
from mmofriends.models import *

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

            self.log.debug("[SW:%s] Running work method" % (self.handle))
            ret = self.work()
            endTime = time.time()
            self.lastRun = endTime
            self.log.debug("[SW:%s] Work method finished with return '%s'. Run took %s seconds." % (self.handle, ret, endTime - startTime))

            self.getCache('backgroundTasks')
            self.cache['backgroundTasks'][self.handle]['end'] = time.time()
            self.cache['backgroundTasks'][self.handle]['result'] = ret
            self.setCache('backgroundTasks')

            db_session.remove()

            return ret

    def work(self):
        return "I should do something ..."

    # helper
    def getCache(self, name):
        try:
            ret = runQuery(MMONetworkCache.query.filter_by(network_handle=self.handle, entry_name=name).first)
        except Exception as e:
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
        try:
            ret = runQuery(MMONetworkCache.query.filter_by(network_handle=self.handle, entry_name=name).first)
        except Exception as e:
            self.log.warning("[%s] SQL Alchemy Error on setCache: %s" % (self.handle, e))
            ret = False

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
        db_session.merge(ret)
        try:
            runQuery(db_session.commit)
        except Exception as e:
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

class MMODatabaseMaintenance(MMOSystemWorker):

    def __init__(self):
        self.handle = "databaseMaintenance"
        self.timeout = 86400
        super(MMODatabaseMaintenance, self).__init__()

    def work(self):
        tableList = []
        if engine.url.get_dialect().name == "mysql":

            try:
                # tables = Base.metadata.reflect(engine)
                # FIXME: use mysql_query("SHOW TABLES");
                # for row in result:
                # infos['cachesizes'].append({ 'handle': row['network_handle'], 'name': row['entry_name'], 'size': bytes2human(row['size'])})

                tableList = ['mmogamelink', 'mmonetcache', 'mmonetlink', 'mmopaypalpayment', 'mmouser', 'mmousernick']

<<<<<<< HEAD
                # tableList = get_db_tables()
=======
                tableList = get_table_list()
>>>>>>> dev
                self.log.debug("[SW:%s] Found the following tables: %s" % (self.handle, ', '.join(tableList)))

                result = engine.execute('OPTIMIZE TABLE %s;' % (', '.join(tableList)))
            except Exception as e:
                self.log.error("[SW:%s] SQL Alchemy Error on table optimization: %s" % (self.handle, e))

        else:
            self.log.info("[SW:%s] Database optimization not supported for dialect: %s" % (self.handle, engine.url.get_dialect().name))

        return "%s tables optimized." % (len(tableList))
