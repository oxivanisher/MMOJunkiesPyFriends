#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime

def timestampToString(ts):
	return datetime.datetime.fromtimestamp(int(ts)).strftime('%s.%m.%Y %H:%M:%S')