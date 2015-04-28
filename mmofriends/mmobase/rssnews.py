#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
# import os
# import random
# import json
# import requests
# import urllib
import re

from flask import current_app
from flask.ext.babel import Babel, gettext
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
        self.registerWorker(self.updateNews, 559)

        # dashboard boxes
        self.registerDashboardBox(self.dashboard_getNews, 'getNews', {'title': 'News feeds' })

        self.TAG_RE = re.compile(r'<[^>]+>')

    # helper
    def remove_tags(self, text):
        return self.TAG_RE.sub('', text)

    # overwritten class methods
    def getStats(self):
        self.log.debug("[%s] Requesting stats" % (self.handle))
        self.getCache('feeds')

        entries = 0
        for feed in self.cache['feeds']:
            entries += len(self.cache['feeds'][feed]['entries'])
        return { gettext('News feeds'): len(self.config['rssSources']),
                 gettext('News entries'): entries }

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
                if fixMe in fixDict.keys():
                    fixDict[fixMe] = int(time.mktime(fixDict[fixMe]))
            return fixDict

        feedRet = []
        for feed in self.config['rssSources']:
            logger.debug("[%s] Fetching feed from %s" % (self.handle, feed))
            try:
                feedData = fixDate(feedparser.parse(feed))
            except Exception as e:
                logger.warning("[%s] Error %s with feedparser for feed: %s" % (self.handle, e, feed))
                continue
            if 'feed' in feedData:
                feedData['feed'] = fixDate(feedData['feed'])

            newEntries = []
            if 'entries' in feedData:
                for entry in feedData['entries']:
                    newEntries.append(fixDate(entry))

            feedData['entries'] = newEntries
            self.cache['feeds'][feed] = feedData

        for feed in [x for x in self.cache['feeds'].keys() if x not in self.config['rssSources']]:
            logger.debug("[%s] Removing old feed: %s" % (self.handle, feed))
            self.cache['feeds'].pop(feed, None)

        try:
            self.setCache('feeds')
        except TypeError as e:
            logger.warning("[%s] Unable to save feed (TypeError): %s" % (self.handle, feed))

        return "Updated %s feeds" % len(self.cache['feeds'])

    # Dashboard
    def dashboard_getNews(self, request):
        self.log.debug("Dashboard getNews")
        self.getCache('feeds')

        feedRet = []
        for feed in self.cache['feeds']:
            if self.cache['feeds'][feed]['status'] == 200:
                feedTitle = self.cache['feeds'][feed]['feed']['title']
                if 'author' in self.cache['feeds'][feed]['feed']:
                    feedAuthor = self.cache['feeds'][feed]['feed']['author']
                else:
                    feedAuthor = "Unknown"
                for entry in self.cache['feeds'][feed]['entries']:
                    feedEntry = {}
                    feedEntry['feedTitle'] = feedTitle
                    feedEntry['author'] = feedAuthor
                    feedEntry['title'] = entry['title']
                    feedEntry['link'] = entry['link']
                    if 'updated_parsed' in entry:
                        feedEntry['date'] = entry['updated_parsed']
                    elif 'published_parsed' in entry:
                        feedEntry['date'] = entry['published_parsed']
                    elif 'created_parsed' in entry:
                        feedEntry['date'] = entry['created_parsed']
                    else:
                        # ignore entries without a date
                        continue
                    feedEntry['summary'] = "None"
                    if 'summary_detail' in entry:
                        if 'value' in entry['summary_detail']:
                            feedEntry['summary'] = self.remove_tags(entry['summary_detail']['value'])

                    feedRet.append(feedEntry)

        # sort by date
        feedRet = sorted(feedRet, key=lambda k: k['date'], reverse=True) 

        # shorten to needed list
        if self.session['crawlerRun']:
            feedRet = feedRet
        else:
            feedRet = feedRet[:self.config['numOfNews']]

        # create short date version
        ret = []
        for entry in feedRet:
            entry['age'] = get_short_age(entry['date'])
            entry['date'] = timestampToString(entry['date'])
            ret.append(entry)

        return { 'news': ret }
