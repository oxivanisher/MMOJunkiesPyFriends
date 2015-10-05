#!/usr/bin/env python
# -*- coding: utf-8 -*-

# https://developer.riotgames.com/docs/getting-started
# https://developer.riotgames.com/discussion/riot-games-api/show/iXR9Vl2A

import logging
import time
import os
import random
import json
import requests
import urllib

from flask import current_app
from flask.ext.babel import Babel, gettext

from mmofriends.mmoutils import *
from mmofriends.models import *

# try:
#     from rauth.service import OAuth2Service
# except ImportError:
#     print "Please install rauth (https://github.com/litl/rauth)"
#     import sys
#     sys.exit(2)

class RiotNetwork(MMONetwork):

    def __init__(self, app, session, handle):
        super(RiotNetwork, self).__init__(app, session, handle)
        pass
