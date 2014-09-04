#!/usr/bin/env python
# -*- coding: utf-8 -*-

# imports
import sys
import os
import logging
from sqlite3 import dbapi2 as sqlite3

import config
from mmobase import *
from mmonetwork import *
from mmouser import *

# configure logging
logging.basicConfig(filename='log/mmofriends.log', format='%(asctime)s %(levelname)s:%(message)s', datefmt='%Y-%d-%m %H:%M:%S', level=logging.DEBUG)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)-16s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
log = logging.getLogger(__name__)

# more imports
try:
    from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, make_response, send_from_directory, current_app
except ImportError:
    log.error("Please install flask")
    sys.exit(2)

# loading mmofriends base
mmobase = mmobase.MMOBase()

# setup flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['dbFile'] = "mmofriends.db"

try:
    app.config.from_envvar('MMOFRIENDS_CFG', silent=False)
except RuntimeError as e:
    log.error(e)
    sys.exit(2)

if not app.debug:
    from logging.handlers import SMTPHandler
    mail_handler = SMTPHandler(app.config['EMAILSERVER'], app.config['EMAILFROM'], ADMINS, current_app.name + ' failed!')
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)


if __name__ == '__main__':
    app.run()