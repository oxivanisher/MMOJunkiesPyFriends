#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
import os
import random
import json
import requests
import urllib

from flask import current_app
from mmoutils import *
from mmouser import *
from mmonetwork import *
from mmofriends import db

try:
    import feedparser
except ImportError:
    log.error("[System] Please install python-feedparser")
    sys.exit(2)

class RSSNews(MMONetwork):

    def __init__(self, app, session, handle):
        super(RSSNews, self).__init__(app, session, handle)
        # activate debug while development
        self.setLogLevel(logging.DEBUG)

        # background updater methods
        self.registerWorker(self.updateNews, 600)

        # dashboard boxes
        self.registerDashboardBox(self.dashboard_getNews, 'getNews', {'title': 'News feeds', 'admin': True })

    def getStats(self):
        self.log.debug("[%s] Requesting stats" % (self.handle))
        return { 'News feeds': len(self.config['rssSources']) }

    def updateNews(self, logger = None):
        if not logger:
            logger = self.log
        self.getCache('news')

        feedRet = []
        for feed in self.config['rssSources']:
            logger.debug("[%s] Fetching feed from %s" % (self.handle, feed))
            # self.cache['news'][feed] = feedparser.parse(feed)
            # convert times to json compatible data
            # TypeError: time.struct_time(tm_year=2014, tm_mon=12, tm_mday=10, tm_hour=17, tm_min=2, tm_sec=6, tm_wday=2, tm_yday=344, tm_isdst=0) is not JSON serializable
        self.setCache('news')

        return "Updated %s feeds" % len(self.cache['news'])

    # Dashboard
    def dashboard_getNews(self, request):
        self.log.debug("Dashboard getNews")
        self.getCache('news')
        return self.cache['news']
