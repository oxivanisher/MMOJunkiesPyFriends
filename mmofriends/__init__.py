#!/usr/bin/env python
# -*- coding: utf-8 -*-

# imports
import sys
import os
import logging


from mmobase.mmouser import *
from mmobase.mmonetwork import *
from mmobase.mmoutils import *
from mmobase.ts3mmonetwork import *
from mmobase.valvenetwork import *
log = getLogger(level=logging.INFO)

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

try:
    from flask.ext.openid import OpenID
except ImportError:
    log.error("Please install the openid extension for flask")
    sys.exit(2)

# try:
#     import twitter
# except ImportError:
#     log.error("Please install python-twitter")
#     sys.exit(2)

# setup flask app
app = Flask(__name__)
app.config['scriptPath'] = os.path.dirname(os.path.realpath(__file__))

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
    mail_handler = SMTPHandler(app.config['EMAILSERVER'], app.config['EMAILFROM'], app.config['ADMINS'], current_app.name + ' failed!')
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

# initialize stuff
app.config['networkConfig'] = YamlConfig(os.path.join(app.config['scriptPath'], "../config/mmonetworks.yml")).get_values()
app.secret_key = app.config['APPSECRET']
MMONetworks = {}

# jinja2 methods
app.jinja_env.globals.update(timestampToString=timestampToString)

# initialize database
db = SQLAlchemy(app)
with app.test_request_context():
    from mmobase.mmouser import *
    from mmobase.mmonetwork import *
    db.create_all()

# initialize twitter api for news
# api = twitter.Api(consumer_key='bAngUFXT9c5FCRFkfQZjqAqJT',
#                   consumer_secret='0Lfi8jMiNb5fQeeLRh9exAwM3UarVdS6o3bg16GlrK6xXRFcOp',
#                   access_token_key='',
#                   access_token_secret='')

# helper methods
def fetchFriendsList():
    retFriendsList = []
    for handle in MMONetworks.keys():
        (res, friendsList) = MMONetworks[handle].getPartners()
        if res:
            retFriendsList += friendsList
        else:
            flash(("%s: " % MMONetworks[handle].name) + friendsList)
    return retFriendsList

def loadNetworks():
    for handle in app.config['networkConfig'].keys():
        network = app.config['networkConfig'][handle]
        log.info("Trying to initialize MMONetwork %s (%s)" % (network['name'], handle))
        try:
            MMONetworks[handle] = eval(network['class'])(app, session, handle)
            log.info("Initialization of MMONetwork %s (%s) completed" % (network['name'], handle))
            MMONetworks[handle].setLogLevel(logging.INFO)
        except Exception as e:
            log.error("Unable to initialize MMONetwork %s because: %s" % (network['name'], e))

def getUserByNick(nick = None):
    with app.test_request_context():
        if not nick:
            nick = session.get('nick')
        ret = MMOUser.query.filter(MMOUser.nick.ilike(nick)).first()
        if ret:
            return ret
        else:
            return False

def getUserById(userId = None):
    with app.test_request_context():
        if not userId:
            userId = session.get('userid')
        ret = MMOUser.query.filter_by(id=userId).first()
        if ret:
            return ret
        else:
            return False

def fetchNetworkLinks(userId):
    with app.test_request_context():
        session['netLinks'] = {}
        for net in MMONetworks.keys():
            session['netLinks'][net] = MMONetworks[net].getNetworkLinks(userId)
        return session['netLinks']

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
    loadNetworks()

@app.before_request
def before_request():
    try:
        session['requests'] += 1
    except KeyError:
        pass

# main routes
@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('partner_list'))
    return redirect(url_for('about'))

@app.route('/About')
def about():
    twitterData = {'widgetUrl': app.config['TWITTERURL'], 'widgetId': app.config['TWITTERWIDGETID']}
    return render_template('about.html', twitter = twitterData)

@app.route('/Administration/')
def admin():
    if not session.get('logged_in'):
        abort(401)
    if not session.get('admin'):
        log.warning("<%s> tried to access admin without permission!")
        abort(401)

    loadedNets = []
    for handle in MMONetworks.keys():
        network = MMONetworks[handle]
        loadedNets.append({ 'handle': handle,
                            'name': network.name,
                            'className': network.__class__.__name__,
                            'moreInfo': network.moreInfo,
                            'description': network.description })

    loadedNets = []
    for handle in MMONetworks.keys():
        network = MMONetworks[handle]
        loadedNets.append({ 'handle': handle,
                            'name': network.name,
                            'className': network.__class__.__name__,
                            'moreInfo': network.moreInfo,
                            'description': network.description })
    registredUsers = []

    with app.test_request_context():
        users = MMOUser.query.all()
        for user in users:
            registredUsers.append({ 'nick': user.nick,
                                    'name': user.name,
                                    'email': user.email,
                                    'website': user.website,
                                    'admin': user.admin,
                                    'locked': user.locked,
                                    'veryfied': user.veryfied })

    infos = {}
    infos['loadedNets'] = loadedNets
    infos['registredUsers'] = registredUsers
    return render_template('admin.html', infos = infos)

@app.route('/Development')
def dev():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if not session.get('admin'):
        log.warning("<%s> tried to access admin without permission!")
        abort(401)

    # result = "nope nix"
    # result = MMONetworks[0].getIcon(-247099292)
    try:
        result = MMONetworks['Valve'].test()
    except Exception as e:
        result = e

    return render_template('dev.html', result = result)

# support routes
@app.route('/Images/<imgType>/<imgId>', methods = ['GET', 'POST'])
def get_image(imgType, imgId):
    filePath = os.path.join(app.config['scriptPath'], 'static', imgType)
    log.debug("Requesting img type <%s> id <%s>" % (imgType, imgId))

    try:
        if imgType == 'avatar':
            fileName = MMOFriends[int(imgId)].avatar
        elif imgType == 'network':
            fileName = MMONetworks[imgId].icon
        elif imgType == 'cache':
            fileName = imgId
        elif imgType == 'flag':
            fileName = imgId + '.png'

        if os.path.isfile(os.path.join(filePath, fileName)):
            return send_from_directory(filePath, fileName)
        else:
            log.warning("Image not found: %s/%s" % (filePath, fileName))

    except IndexError:
        log.warning("Unknown ID for img type %s: %s" % (imgType, imgId))
    abort(404)

# network routes
@app.route('/Network/Show/<networkId>', methods = ['GET'])
def network_show(networkId):
    if not session.get('logged_in'):
        abort(401)
    pass

@app.route('/Network/Administration/<networkHandle>', methods = ['GET'])
def network_admin(networkHandle):
    if not session.get('logged_in'):
        abort(401)
    if session.get('admin'):
        return MMONetworks[networkHandle].admin()

@app.route('/Network/Link', methods=['GET', 'POST'])
def network_link():
    if not session.get('logged_in'):
        abort(401)

    if request.method == 'POST':
        net = MMONetworks[request.form['handle']]
        if request.form['do'] == 'link':
            doLinkReturn = MMONetworks[request.form['handle']].doLink(request.form['id'])
            return render_template('network_link.html', doLinkReturn = {'doLinkReturn': doLinkReturn,
                                                                        'handle': net.handle,
                                                                        'name': net.name,
                                                                        'moreInfo': net.moreInfo})
        elif request.form['do'] == 'finalize':
            if MMONetworks[request.form['handle']].finalizeLink(request.form['userKey']):
                flash('Successfully linked to network %s' % net.moreInfo)
                return redirect(url_for('network_link'))
            else:
                flash('Unable to link network %s. Please try again.' % net.moreInfo)
                return redirect(url_for('network_link'))
        else:
            abort(404)
    else:
        linkedNetworks = []
        fetchNetworkLinksData = fetchNetworkLinks(session.get('userid'))
        for net in fetchNetworkLinksData:
            netInfo = MMONetworks[net]
            for link in fetchNetworkLinksData[net]:
                linkedNetworks.append({'name': netInfo.name,
                                       'moreInfo': netInfo.moreInfo,
                                       'handle': netInfo.handle,
                                       'icon': netInfo.icon,
                                       'network_data': link['network_data'],
                                       'linkId': link['id'],
                                       'linked_date': timestampToString(link['linked_date']) })

        linkNetwork = []
        for netKey in MMONetworks.keys():
            net = MMONetworks[netKey]
            linkNetwork.append({ 'id': netKey,
                              'name': net.name,
                              'handle': net.handle,
                              'description': net.description,
                              'moreInfo': net.moreInfo,
                              'linkNetwork': net.getLinkHtml() })
        return render_template('network_link.html', linkNetwork = linkNetwork, linkedNetworks = linkedNetworks)

@app.route('/Network/Unlink/<netHandle>/<netLinkId>', methods=['GET'])
def network_unlink(netHandle, netLinkId):
    if not session.get('logged_in'):
        abort(401)
    if request.method == 'GET':
        if MMONetworks[netHandle].unlink(session.get('userid'), netLinkId):
            flash('Removed link')
        else:
            flash('Unable to remove link')
    return redirect(url_for('network_link'))

# profile routes
@app.route('/Profile/Register', methods=['GET', 'POST'])
def profile_register():
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
                actUrl = app.config['WEBURL'] + url_for('profile_verify', userId=newUser.id, verifyKey=newUser.verifyKey)
                if send_email(app, newUser.email, "MMOFriends Activation email", "<a href='%s'>Verify your account with this link.</a>" % (actUrl)):
                    flash("Please check your mails at %s" % newUser.email)
                else:
                    flash("Error sending the email to you.")
                return redirect(url_for('profile_login'))

            except IntegrityError, e:
                flash("SQL Alchemy IntegrityError: %s" % e)
            except InterfaceError, e:
                flash("SQL Alchemy InterfaceError %s" % e)
    
    return render_template('profile_register.html', values = request.form)

@app.route('/Profile/Show', methods=['GET', 'POST'])
def profile_show():
    flash("show profile, change template in the future")
    return render_template('profile_register.html', values = getUserById())

@app.route('/Profile/Verify/<userId>/<verifyKey>', methods=['GET'])
def profile_verify(userId, verifyKey):
    log.info("Verify userid %s" % userId)
    verifyUser = getUserById(userId)
    if verifyUser.verify(verifyKey):
        db.session.add(verifyUser)
        db.session.commit()
        flash("Verification ok. Please log in.")
        return redirect(url_for('profile_login'))
    else:
        flash("Verification NOT ok. Please try again.")
    return redirect(url_for('index'))

@app.route('/Profile/Login', methods=['GET', 'POST'])
def profile_login():
    if request.method == 'POST':
        log.info("Trying to login user: %s" % request.form['nick'])
        myUser = False
        myUser = getUserByNick(request.form['nick'])

        if myUser:
            myUser.load()
            if not myUser.veryfied:
                flash("User not yet veryfied. Please check your email for the unlock key.")
                return redirect(url_for('index'))
            elif myUser.locked:
                flash("User locked. Please contact an administrator.")
                return redirect(url_for('index'))
            elif myUser.checkPassword(request.form['password']):
                log.info("<%s> logged in" % myUser.nick)
                session['logged_in'] = True
                session['userid'] = myUser.id
                session['nick'] = myUser.nick
                session['admin'] = myUser.admin
                session['logindate'] = time.time()
                session['requests'] = 0
                return redirect(url_for('index'))                
            else:
                log.info("Invalid password for %s" % myUser.nick)
                flash('Invalid login')               
        else:
            flash('Invalid login')

    return render_template('profile_login.html')

@app.route('/Profile/Logout')
def profile_logout():
    session.pop('logged_in', None)
    session.pop('nick', None)
    session.pop('admin', None)
    session.pop('logindate', None)
    return redirect(url_for('profile_login'))

# partner routes
@app.route('/Partner/List')
def partner_list():
    # users = MMOUser.query.all()
    # for user in users:
    #     print user
    if session.get('logged_in'):
        return render_template('partner_list.html', friends = fetchFriendsList())
    else:
        abort(401)

@app.route('/Partner/Show')
def partner_show(freiendID):
    if not session.get('logged_in'):
        abort(401)
    return redirect(url_for('index'))

@app.route('/Partner/Details/<networkId>/<partnerId>', methods = ['GET', 'POST'])
def partner_show_details(networkId, partnerId):
    log.info("Trying to show partner details for networkId %s and partnerId %s" % (networkId, partnerId))
    if not session.get('logged_in'):
        abort(401)
    return render_template('partner_details.html', details = MMONetworks[networkId].getPartnerDetails(partnerId))