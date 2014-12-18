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
        # self.setLogLevel(logging.DEBUG)

        # background updater methods
        self.registerWorker(self.updateNews, 600)

        # dashboard boxes
        self.registerDashboardBox(self.dashboard_getNews, 'getNews', {'title': 'News feeds' })

    # overwritten class methods
    def getStats(self):
        self.log.debug("[%s] Requesting stats" % (self.handle))
        self.getCache('feeds')

        entries = 0
        for feed in self.cache['feeds']:
            entries += len(self.cache['feeds'][feed]['entries'])
        return { 'News feeds': len(self.config['rssSources']),
                 'News entries': entries }

    def getPartners(self, **kwargs):
        self.log.debug("[%s] List all partners for given user" % (self.handle))
        return ( False, None )

    # background worker
    def updateNews(self, logger = None):
        if not logger:
            logger = self.log
        logger.debug("[%s] Updating feeds" % (self.handle))
        self.getCache('feeds')

        def fixDate(fixDict):
            itemList = ['updated_parsed', 'published_parsed', 'created_parsed', 'expired_parsed']
            for fixMe in itemList:
                if fixMe in fixDict:
                    fixDict[fixMe] = int(time.mktime(fixDict[fixMe]))

        feedRet = []
        for feed in self.config['rssSources']:
            logger.debug("[%s] Fetching feed from %s" % (self.handle, feed))
            feedData = feedparser.parse(feed)
            if 'feed' in feedData:
                fixDate(feedData['feed'])

            newEntries = []
            if 'entries' in feedData:
                for entry in feedData['entries']:
                    newEntry = entry
                    fixDate(newEntry)
                    newEntries.append(newEntry)

            feedData['entries'] = newEntries
            self.cache['feeds'][feed] = feedData

        for feed in [x for x in self.cache['feeds'].keys() if x not in self.config['rssSources']]:
            logger.debug("[%s] Removing old feed: %s" % (self.handle, feed))
            self.cache['feeds'].pop(feed, None)
        self.setCache('feeds')

        return "Updated %s feeds" % len(self.cache['feeds'])

    # Dashboard
    def dashboard_getNews(self, request):
        self.log.debug("Dashboard getNews")
        self.getCache('feeds')

        feedRet = []
        for feed in self.cache['feeds']:
            count = 0
            if self.cache['feeds'][feed]['status'] == 200:
                feedData = {}
                feedData['title'] = self.cache['feeds'][feed]['feed']['title']
                if 'author' in self.cache['feeds'][feed]['feed']:
                    feedData['author'] = self.cache['feeds'][feed]['feed']['author']
                else:
                    feedData['author'] = "Unknown"
                feedData['entries'] = []
                for entry in self.cache['feeds'][feed]['entries']:
                    count += 1
                    if count > self.config['numOfNews']:
                        break
                    feedEntry = {}
                    feedEntry['title'] = entry['title']
                    # feedEntry['summary'] = entry['summary']
                    feedEntry['link'] = entry['link']
                    if 'updated_parsed' in entry:
                        feedEntry['date'] = timestampToString(entry['updated_parsed'])
                    elif 'published_parsed' in entry:
                        feedEntry['date'] = timestampToString(entry['published_parsed'])
                    elif 'created_parsed' in entry:
                        feedEntry['date'] = timestampToString(entry['created_parsed'])
                    else:
                        feedEntry['date'] = "Unknown"
                    feedEntry['summary'] = "None"
                    if 'summary_detail' in entry:
                        if 'value' in entry['summary_detail']:
                            feedEntry['summary'] = entry['summary_detail']['value']

                    feedData['entries'].append(feedEntry)
                feedRet.append(feedData)

        return { 'feeds': feedRet }
