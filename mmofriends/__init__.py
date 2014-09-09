#!/usr/bin/env python
# -*- coding: utf-8 -*-

# imports
import sys
import os
import logging

from config import *

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
app.secret_key = os.urandom(24)
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
MMONetworks = []

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

# flask error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html'), 404

# app routes
@app.before_first_request
def before_first_request():
    log.debug("Before first request")

    # load networks
    loadNetwork(TS3Network, "TS3", "Team Speak 3")

    log.debug("Serving first request")

@app.route('/About')
def show_about():
    return render_template('about.html')

@app.route('/')
def show_index():
    # users = MMOUser.query.all()
    # for user in users:
    #     print user
    if session.get('logged_in'):
        return render_template('index.html', friends = fetchFriendsList())
    else:
        return redirect(url_for('show_about'))

@app.route('/Network/Show', methods = ['GET'])
def show_network():
    if not session.get('logged_in'):
        abort(401)
    pass

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        valid = True
        if request.form['username'] and \
            request.form['password'] and \
            request.form['password2'] and \
            request.form['email']:

            if request.form['password'] != request.form['password2']:
                flash("Passwords do not match!")
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
            newUser = MMOUser(request.form['username'])
            newUser.email = request.form['email']
            newUser.name = request.form['name']
            newUser.website = request.form['website']
            newUser.setPassword(request.form['password'])

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

@app.route('/Login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            log.info("Invalid username for %s" % request.form['username'])
            flash('Invalid login')
        elif request.form['password'] != app.config['PASSWORD']:
            log.info("Invalid password for %s" % request.form['username'])
            flash('Invalid login')
        else:
            log.info("%s Logged in" % request.form['username'])
            session['logged_in'] = True
            flash('Logged in')
            return redirect(url_for('admin'))
    return render_template('login.html')

@app.route('/Logout')
def logout():
    session.pop('logged_in', None)
    flash('Logged out')
    return redirect(url_for('show_index'))

@app.route('/Avatar/<int:friendId>', methods = ['GET'])
def get_avatar(friendId):
    filePath = os.path.join(app.config['scriptPath'], 'static', 'avatar')
    try:
        if os.path.isfile(os.path.join(filePath, MMOFriends[friendId].avatar)):
            return send_from_directory(filePath, MMOFriends[friendId].avatar)
        else:
            log.warning("Icon not found: %s" % filePath)
    except IndexError:
        log.warning("Unknown friend ID for avatar")
    abort(404)

@app.route('/Icon/<int:networkId>', methods = ['GET'])
def get_icon(networkId):
    filePath = os.path.join(app.config['scriptPath'], 'static', 'icon')
    try:
        if os.path.isfile(os.path.join(filePath, MMONetworks[networkId].icon)):
            return send_from_directory(filePath, MMONetworks[networkId].icon)
        else:
            log.warning("Icon not found: %s" % filePath)
    except IndexError:
        log.warning("Unknown network ID for icon")
    abort(404)

@app.route('/ShowFriend')
def show_friend(freiendID):
    if not session.get('logged_in'):
        abort(401)
    return redirect(url_for('show_index'))