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
    age = int(time.time() - timestamp)

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

# emailer functions
def load_file(app, msgRoot, filename):
    fp = open(os.path.join(app.root_path, 'static/img/', filename), 'rb')
    msgImage = MIMEImage(fp.read())
    fp.close()
    msgImage.add_header('Content-Disposition', 'inline', filename=filename)
    msgImage.add_header('Content-ID', '<' + os.path.splitext(filename)[0] + '@mmofriends.local>')
    msgRoot.attach(msgImage)

def send_email(app, msgto, msgsubject, msgtext):
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
                margin: 0;
                padding: 0;
            }
            #background { 
                left: 0px; 
                top: 0px; 
                position: relative; 
                margin-left: auto; 
                margin-right: auto; 
                width: 600px;
                height: 500px; 
                overflow: hidden;
                z-index:0;
            }
            #logo { 
                left: 0px; 
                top: 0px; 
                position: absolute; 
                width: 600px;
                height: 150px;
                z-index:2;
            } 
            #content {
                top: 160px;
                position: absolute;
            }
        </style>
    </head>
    <body>
        <div id="background">
            <div id="logo"><img src="cid:email_header@mmofriends.local"></div>
            <div id="content">%s</div>
        </div>
    </body>
    </html>""" % (msgsubject, msgtext.replace('\n', '<br />').encode('ascii', 'xmlcharrefreplace'))

        newplaintext = ""
        for line in msgtext.split("\n"):
            newplaintext += "\n".join(textwrap.wrap(line)) + "\n"

        part1 = MIMEText(newplaintext.replace('\n', '\r\n').encode("UTF-8"), 'plain', 'UTF-8')
        part2 = MIMEText(htmltext.replace('\n', '\r\n').encode('UTF-8'), 'html', 'UTF-8')
        msgAlternative.attach(part1)
        msgAlternative.attach(part2)

        load_file(app, msgRoot, 'email_header.png')

        s = smtplib.SMTP(app.config['EMAILSERVER'])
        if len(app.config['EMAILLOGIN']) and len(app.config['EMAILPASSWORD']):
            s.login(app.config['EMAILLOGIN'], app.config['EMAILPASSWORD'])
        s.sendmail(app.config['EMAILFROM'], msgto, msgRoot.as_string())
        s.quit()
        return True
    except Exception as e:
        print 'Email ERROR: ' + str(e) + ' on line ' + str(sys.exc_traceback.tb_lineno)
        return False