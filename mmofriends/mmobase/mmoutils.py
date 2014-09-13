#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os

def timestampToString(ts):
    return datetime.datetime.fromtimestamp(int(ts)).strftime('%d.%m.%Y %H:%M:%S')

def bytes2human(n):
    # http://code.activestate.com/recipes/578019
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if int(n) >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return "%sB" % n

def getLogger(level=logging.INFO):
    myPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../')
    logPath = os.path.join(myPath, 'log/mmofriends.log')
    logging.basicConfig(filename=logPath, format='%(asctime)s %(levelname)s:%(message)s', datefmt='%Y-%d-%m %H:%M:%S', level=level)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)-7s %(name)-25s| %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    return logging.getLogger(__name__)
