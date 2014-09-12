#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime

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