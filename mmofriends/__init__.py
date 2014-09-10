#!/usr/bin/env python
# -*- coding: utf-8 -*-

# imports
import sys
import os
import logging

from config import *
from mmoutils import *

# configure logging
logging.basicConfig(filename='log/mmofriends.log', format='%(asctime)s %(levelname)s:%(message)s', datefmt='%Y-%d-%m %H:%M:%S', level=logging.DEBUG)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)-8s [%(name)s] %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
log = logging.getLogger(__name__)

# flask imports
try:
    from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, make_response, send_from_directory, current_app
except ImportError:
    log.error("Please install flask")
    sys.exit(2)

try:
    from flask.ext.sqlalchemy import SQLAlchemy
    from sqlalchemy.exc import IntegrityError, InterfaceError

except ImportError:
    log.error("Please install the sqlalchemy extension for flask")
    sys.exit(2)

# setup flask app
app = Flask(__name__)
app.config['scriptPath'] = os.path.dirname(os.path.realpath(__file__))
db = SQLAlchemy(app)

try:
    os.environ['MMOFRIENDS_CFG']
except KeyError:
    log.warning("Loading config from dist/mmofriends.cfg.example becuase MMOFRIENDS_CFG environment variable is not set.")
    os.environ['MMOFRIENDS_CFG'] = "../dist/mmofriends.cfg.example"

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

with app.test_request_context():
    # finally loading mmofriends
    # from mmobase import *
    from mmonetwork import *
    from mmouser import *
    db.create_all()

# initialize stuff
app.config['networkConfig'] = YamlConfig("config/mmonetworks.yml").get_values()
app.secret_key = app.config['APPSECRET']
MMONetworks = []
MyUser = None

# helper methods
def loadNetwork(network, shortName, longName):
    MMONetworks.append(network(MMONetworkConfig(app.config['networkConfig'], shortName, longName), len(MMONetworks)))

def fetchFriendsList():
    retFriendsList = []
    for network in MMONetworks:
        (res, friendsList) = network.returnOnlineUserDetails()
        if res:
            retFriendsList += friendsList
        else:
            flash(friendsList)
    return retFriendsList

def getUser(nick = None):
    with app.test_request_context():
        if not nick:
            nick = session.get('nick')
        return MMOUser.query.filter_by(nick=nick).first()

# flask error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', number = 404, message = "Page not found!"), 404

@app.errorhandler(401)
def not_found(error):
    return render_template('error.html', number = 401, message = "Unauthorized!"), 401

# app routes
@app.before_first_request
def before_first_request():
    log.debug("Before first request")

    # load networks
    loadNetwork(TS3Network, "TS3", "Team Speak 3")

    log.debug("Serving first request")

@app.route('/About')
def about():
    return render_template('about.html')

@app.route('/')
def index():
    # users = MMOUser.query.all()
    # for user in users:
    #     print user
    if session.get('logged_in'):
        return render_template('index.html', friends = fetchFriendsList())
    else:
        return redirect(url_for('about'))

@app.route('/Admin')
def admin():
    if not session.get('logged_in'):
        abort(401)
    if not session.get('admin'):
        log.warning("<%s> tried to access admin without permission!")
        abort(401)
    flash("admin page would be loading ^^")
    return redirect(url_for('index'))

@app.route('/Dev')
def dev():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if not session.get('admin'):
        log.warning("<%s> tried to access admin without permission!")
        abort(401)

    # result = "nope nix"
    # result = MMONetworks[0].getIcon(-247099292)
    result = MMONetworks[0].test()

    return render_template('dev.html', result = result)

@app.route('/Network/Show', methods = ['GET'])
def show_network():
    if not session.get('logged_in'):
        abort(401)
    pass

@app.route('/Register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        valid = True
        if request.form['nick'] and \
            request.form['password'] and \
            request.form['password2'] and \
            request.form['email']:

            if request.form['password'] != request.form['password2']:
                flash("Passwords do not match!")
                valid = False

            if len(request.form['nick']) < 3:
                flash("Nickname is too short")
                valid = False

            if len(request.form['password']) < 8:
                flash("Password is too short")
                valid = False


            #and further checks for registration plz
            # - user needs to be uniq!
            # - minimal field length
            # - is the website a website?
            # - max length (cut oversize)

        else:
            valid = False
            flash("Please fill out all the fields!")

        if valid:
            newUser = MMOUser(request.form['nick'])
            newUser.email = request.form['email']
            newUser.name = request.form['name']
            newUser.website = request.form['website']
            newUser.setPassword(request.form['password'])
            if request.form['nick'] == app.config['ROOTUSER']:
                log.info("Registred root user: %s" % request.form['nick'])
                newUser.admin = True
                newUser.locked = False
                newUser.veryfied = True

            db.session.add(newUser)
            try:
                db.session.commit()
                flash("Please check your emails on %s" % newUser.email)
                return redirect(url_for('login'))

            except IntegrityError, e:
                flash("SQL Alchemy IntegrityError: %s" % e)
            except InterfaceError, e:
                flash("SQL Alchemy InterfaceError %s" % e)
    
    return render_template('register.html', values = request.form)

@app.route('/Profile', methods=['GET', 'POST'])
def profile():
    flash("show profile, change template in the future")
    return render_template('register.html', values = getUser())

@app.route('/Login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        log.info("Trying to login user: %s" % request.form['nick'])
        myUser = False
        myUser = getUser(request.form['nick'])

        if myUser:
            myUser.load()
            if myUser.checkPassword(request.form['password']):
                log.info("<%s> logged in" % myUser.nick)
                session['logged_in'] = True
                session['nick'] = myUser.nick
                session['admin'] = myUser.admin
                flash('Welcome %s' % myUser.nick)
                return redirect(url_for('index'))                
            else:
                log.info("Invalid password for %s" % myUser.nick)
        else:
            flash('Invalid login')                

    return render_template('login.html')

@app.route('/Logout')
def logout():
    session.pop('logged_in', None)
    session.pop('nick', None)
    session.pop('admin', None)
    flash('Logged out')
    return redirect(url_for('login'))

@app.route('/Img/Avatar/<int:friendId>', methods = ['GET'])
def get_avatar(friendId):
    filePath = os.path.join(app.config['scriptPath'], 'static', 'avatar')
    try:
        if os.path.isfile(os.path.join(filePath, MMOFriends[friendId].avatar)):
            return send_from_directory(filePath, MMOFriends[friendId].avatar)
        else:
            log.warning("Avatar not found: %s" % filePath)
    except IndexError:
        log.warning("Unknown ID for Avatar")
    abort(404)

@app.route('/Img/NetworkIcon/<int:networkId>', methods = ['GET'])
def get_network_icon(networkId):
    filePath = os.path.join(app.config['scriptPath'], 'static', 'icon')
    try:
        if os.path.isfile(os.path.join(filePath, MMONetworks[networkId].icon)):
            return send_from_directory(filePath, MMONetworks[networkId].icon)
        else:
            log.warning("NetworkIcon not found: %s" % filePath)
    except IndexError:
        log.warning("Unknown ID for NetworkIcon")
    abort(404)

@app.route('/Img/Cache/<cacheFile>', methods = ['GET'])
def get_cached_file(cacheFile):
    filePath = os.path.join(app.config['scriptPath'], 'static', 'cache')
    try:
        if os.path.isfile(os.path.join(filePath, cacheFile)):
            return send_from_directory(filePath, cacheFile)
        else:
            log.warning("CacheFile not found: %s" % filePath)
    except IndexError:
        log.warning("Unknown cacheFile in Cache")
    abort(404)

@app.route('/ShowFriend')
def show_friend(freiendID):
    if not session.get('logged_in'):
        abort(401)
    return redirect(url_for('index'))