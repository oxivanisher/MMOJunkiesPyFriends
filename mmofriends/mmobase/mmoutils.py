#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os
import io
import json
import yaml

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
    myPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../')
    logPath = os.path.join(myPath, 'log/mmofriends.log')
    logging.basicConfig(filename=logPath, format='%(asctime)s %(levelname)s:%(message)s', datefmt='%Y-%d-%m %H:%M:%S', level=level)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    # formatter = logging.Formatter('%(levelname)-7s %(name)-25s| %(message)s')
    # formatter = logging.Formatter("[%(levelname)8s] --- %(message)s (%(filename)s:%(lineno)s)")
    formatter = logging.Formatter("%(levelname)-7s %(message)s (%(filename)s:%(lineno)s)")
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    return logging.getLogger(__name__)

class YamlConfig (object):
    def __init__(self, filename = None):
        self.filename = filename
        self.values = {}
        if filename:
            self.load()

    def load(self):
        f = open(self.filename)
        self.values = yaml.safe_load(f)
        f.close()

    # def save(self):
    #     f = open(filename, "w")
    #     yaml.dump(self.values, f)
    #     f.close()

    def get_values(self):
        return self.values

    def set_values(self, values):
        self.values = values

class JsonConfig (object):
    def __init__(self, filename):
        self.filename = filename
        self.values = {}
        self.load()

    def load(self):
        self.values = json.loads(open(self.filename).read())

    # def save(self):
    #     pass
    #     with io.open(self.filename, 'w', encoding='utf-8') as outfile:
    #         json.dumps(self.values, outfile)
    #     pass

    def get_values(self):
        return self.values

    def set_values(self, values):
        self.values = values

