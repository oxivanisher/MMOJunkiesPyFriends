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
    from sqlalchemy.exc import IntegrityError

except ImportError:
    log.error("Please install the sqlalchemy extension for flask")
    sys.exit(2)

# setup flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
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

@app.route('/')
def show_index():
    for network in MMONetworks:
        network.refresh()

    friends = MMONetworks[0].returnOnlineUserDetails()
    MMONetworks[0].listOnlineClients()

    users = MMOUser.query.all()
    for user in users:
        print user
    return render_template('index.html', friends = friends)

@app.route('/register', methods=['GET'])
def register():
    nick = request.args.get("nick")
    test = MMOUser(nick)
    db.session.add(test)
    try:
        db.session.commit()
        flash("added %s" % nick)
    except IntegrityError, e:
        flash("error because: %s" % e)
    return redirect(url_for('show_index'))


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


@app.route('/Images/<int:friendId>', methods = ['GET'])
def get_avatar(movieId):
    # moviesList = get_moviesData()
    # cover = moviesList[movieId]['Cover']
    # if cover:
    #     return send_from_directory(os.path.join(app.config['scriptPath'], app.config['OUTPUTDIR']), cover)
    # else:
    abort(404)

@app.route('/ShowFriend')
def show_friend(freiendID):
    return redirect(url_for('show_index'))