#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os
import io
import json
import yaml
import sys
import cgi
import textwrap
import time
import smtplib
import gzip
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

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

def get_short_age(timestamp):
    return get_short_duration(time.time() - int(timestamp))

def get_short_duration(age):
    age = int(age)
    if age < 0:
        age = age * -1

    if age == 0:
        return ''
    elif age < 60:
        return '%ss' % (age)
    elif age > 59 and age < 3600:
        return '%sm' % (int(age / 60))
    elif age >= 3600 and age < 86400:
        return '%sh' % (int(age / 3600))
    elif age >= 86400 and age < 604800:
        return '%sd' % (int(age / 86400))
    elif age >= 604800 and age < 31449600:
        return '%sw' % (int(age / 604800))
    else:
        return '%sy' % (int(age / 31449600))

def get_long_age(timestamp):
    return get_long_duration(time.time() - int(timestamp))

def get_long_duration(age):
    intervals = (
        ('y', 31536000),  # 60 * 60 * 24 * 365
        ('w', 604800),  # 60 * 60 * 24 * 7
        ('d', 86400),    # 60 * 60 * 24
        ('h', 3600),    # 60 * 60
        ('m', 60),
        ('s', 1),
        )

    result = []

    for name, count in intervals:
        value = age // count
        if value:
            age -= value * count
            result.append("%s%s" % (int(value), name))
    return ' '.join(result)

def convertToInt(s):
    try:
        return int(s)
    except ValueError:
        return s

def getHighestRated(myList, sortKey, amount = 75):
    return sorted(myList, key=lambda k: k[sortKey])[::-1][:amount]

# emailer functions
def load_image_file_to_email(app, msgRoot, filename):
    fp = open(os.path.join(app.root_path, 'static/img/', filename), 'rb')
    msgImage = MIMEImage(fp.read())
    newImageName = os.path.splitext(filename)[0]
    fp.close()
    msgImage.add_header('Content-Disposition', 'inline', filename=filename)
    msgImage.add_header('Content-ID', '<' + newImageName + '@mmofriends.local>')
    msgRoot.attach(msgImage)
    return newImageName

def send_email(app, msgto, msgsubject, msgtext, image):
    try:
        msgRoot = MIMEMultipart('related', type="text/html")
        msgRoot['Subject'] = msgsubject
        msgRoot['From'] = app.config['EMAILFROM']
        msgRoot['To'] = msgto
        msgRoot.preamble = 'This is a multi-part message in MIME format.'
        if len(app.config['EMAILREPLYTO']):
            msgRoot.add_header('reply-to', app.config['EMAILREPLYTO'])
        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)

        htmltext = u"""<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <title>%s</title>
        <style type="text/css" media="screen">
            body {
                margin: 0px;
                padding: 0px;
            }
            #background { 
                left: 0px; 
                top: 0px; 
                position: relative; 
                margin-left: auto; 
                margin-right: auto; 
                width: 601px;
                height: 500px;
                overflow: hidden;
                z-index:0;
            }
            #logo { 
                left: 0px; 
                top: 0px; 
                position: absolute; 
                width: 601px;
                height: 181px;
                z-index:2;
            } 
            #content {
                top: 185px;
                width: 601px;
                position: absolute;
                font-size: x-large;
            }
            #footer {
                top: 480px;
                width: 601px;
                font-size: small;
                position: absolute;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div id="background">
            <div id="logo"><img src="cid:%s@mmofriends.local" alt="Header Image"></div>
            <div id="content">%s</div>
            <div id="footer">MMOJunkies Friends <a href="https://github.com/oxivanisher/MMOJunkiesPyFriends">github.com/oxivanisher/MMOJunkiesPyFriends</a></div>
        </div>
    </body>
    </html>""" % (msgsubject,
                  load_image_file_to_email(app, msgRoot, image),
                  msgtext.replace('\n', '<br />').encode('ascii', 'xmlcharrefreplace'))

        newplaintext = ""
        for line in msgtext.split("\n"):
            newplaintext += "\n".join(textwrap.wrap(line)) + "\n"

        part1 = MIMEText(newplaintext.replace('\n', '\r\n').encode("UTF-8"), 'plain', 'UTF-8')
        part2 = MIMEText(htmltext.replace('\n', '\r\n').encode('UTF-8'), 'html', 'UTF-8')
        msgAlternative.attach(part1)
        msgAlternative.attach(part2)

        s = smtplib.SMTP(app.config['EMAILSERVER'])
        if len(app.config['EMAILLOGIN']) and len(app.config['EMAILPASSWORD']):
            s.login(app.config['EMAILLOGIN'], app.config['EMAILPASSWORD'])
        s.sendmail(app.config['EMAILFROM'], msgto, msgRoot.as_string())
        s.quit()
        return True
    except Exception as e:
        print 'Email ERROR: ' + str(e) + ' on line ' + str(sys.exc_traceback.tb_lineno)
        return False

# Dashboard methods
def createDashboardBox(method, netHandle, handle, settings = {}, data = {}):
    logging.debug("[%s] Registered dashboard box %s (%s)" % (netHandle, handle, method.func_name))

    options = []
    options.append(('admin', False))
    options.append(('loggedin', None))
    options.append(('development', False))
    options.append(('sticky', False))
    options.append(('title', "Title %s" % handle))
    options.append(('template', "box_%s_%s.html" % (netHandle, handle)))

    newSettings = {}
    for (option, defaultValue) in options:
        if option in settings:
            newSettings[option] = settings[option]
        else:
            newSettings[option] = defaultValue

    box = {}
    box['method'] = method
    box['handle'] = handle
    box['settings'] = newSettings
    box['netHandle'] = netHandle

    return box

def checkShowBox(session, box):
    if not box:
        return False
    show = True

    # set them empty for not logged in users -> aka no session vars available
    loggedIn = True
    if not session.get('logged_in'):
        loggedIn = False
    admin = True
    if not session.get('admin'):
        admin = False

    # checking if loggedin is set
    if box['settings']['loggedin'] is not None:
        if box['settings']['loggedin'] != loggedIn:
            show = False

    # if we need to be admin, only show it then
    if box['settings']['admin'] and not admin:
        show = False

    return show