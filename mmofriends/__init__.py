#!/usr/bin/env python
# -*- coding: utf-8 -*-

# imports
import sys
import os
import logging
import urllib
import hashlib

from mmobase.mmouser import *
from mmobase.mmonetwork import *
from mmobase.mmoutils import *
from mmobase.ts3mmonetwork import *
from mmobase.valvenetwork import *
from mmobase.blizznetwork import *
from mmobase.twitchnetwork import *
from mmobase.rssnews import *
log = getLogger(level=logging.INFO)

# flask imports
try:
    from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, make_response, send_from_directory, current_app, jsonify, Markup
except ImportError:
    log.error("[System] Please install flask")
    sys.exit(2)

try:
    from flask.ext.sqlalchemy import SQLAlchemy
    from sqlalchemy.exc import IntegrityError, InterfaceError, InvalidRequestError
except ImportError:
    log.error("[System] Please install the sqlalchemy extension for flask")
    sys.exit(2)

try:
    from flask.ext.openid import OpenID
except ImportError:
    log.error("[System] Please install the openid extension for flask")
    sys.exit(2)

try:
    from flask.ext.compress import Compress
except ImportError:
    log.error("[System] Please install the compress extension for flask")

try:
    from celery import Celery
except ImportError:
    log.error("[System] Please install Celery")
    sys.exit(2)

# try:
#     import twitter
# except ImportError:
#     log.error("Please install python-twitter")
#     sys.exit(2)

# setup flask app
app = Flask(__name__)
Compress(app)
app.config['scriptPath'] = os.path.dirname(os.path.realpath(__file__))
app.config['startupDate'] = time.time()

try:
    sys.path.append(os.path.join(app.config['scriptPath'], '../libs/sep'))
    import process
    from urlparse import urlsplit, urlunsplit, parse_qs
except ImportError:
    log.warning("[System] Unable to import the google crawler stuff")

try:
    os.environ['MMOFRIENDS_CFG']
    log.info("[System] Loading config from: %s" % os.environ['MMOFRIENDS_CFG'])
except KeyError:
    log.warning("[System] Loading config from dist/mmofriends.cfg.example becuase MMOFRIENDS_CFG environment variable is not set.")
    os.environ['MMOFRIENDS_CFG'] = "../dist/mmofriends.cfg.example"

try:
    app.config.from_envvar('MMOFRIENDS_CFG', silent=False)
except RuntimeError as e:
    log.error(e)
    sys.exit(2)

with app.test_request_context():
    if not app.debug:
        from logging.handlers import SMTPHandler
        mail_handler = SMTPHandler(app.config['EMAILSERVER'], app.config['EMAILFROM'], app.config['ADMINS'], current_app.name + ' failed!')
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

# initialize stuff
app.config['networkConfig'] = YamlConfig(os.path.join(app.config['scriptPath'], "../config/mmonetworks.yml")).get_values()
if not len(app.config['APPSECRET']):
    log.warning("[System] Generating random secret_key. All older cookies will be invalid, but i will NOT work with multiple processes (WSGI).")
    app.secret_key = os.urandom(24)
else:
    app.secret_key = app.config['APPSECRET']
MMONetworks = {}
SystemBoxes = {}

# jinja2 methods
app.jinja_env.globals.update(timestampToString=timestampToString)
app.jinja_env.globals.update(get_short_duration=get_short_duration)
app.jinja_env.globals.update(get_short_age=get_short_age)

# initialize database
db = SQLAlchemy(app)
with app.test_request_context():
    from mmobase.mmouser import *
    from mmobase.mmonetwork import *
    db.create_all()
    # db.session.autocommit = True
    # db.session.autoflush = True
    oid = OpenID(app)

# initialize twitter api for news
# api = twitter.Api(consumer_key='bAngUFXT9c5FCRFkfQZjqAqJT',
#                   consumer_secret='0Lfi8jMiNb5fQeeLRh9exAwM3UarVdS6o3bg16GlrK6xXRFcOp',
#                   access_token_key='',
#                   access_token_secret='')

# helper methods
def fetchFriendsList(netHandle = None):
    retFriendsList = []
    if not netHandle:
        netHandles = MMONetworks.keys()
    else:
        netHandles = [netHandle]

    for handle in netHandles:
        if not netHandle:
            (res, friendsList) = MMONetworks[handle].getPartners(onlineOnly=True)
        else:
            (res, friendsList) = MMONetworks[handle].getPartners()

        if res:
            # yes, we are getting friends
            retFriendsList += friendsList
        else:
            if friendsList:
                # yes, we are getting a error message
                flash(("%s: " % MMONetworks[handle].name) + friendsList, 'error')

        if not len(retFriendsList):
            flash("Nothing to show here, sorry.", 'info')
            return False
            
    return retFriendsList

def loadNetworks():
    for handle in app.config['networkConfig'].keys():
        network = app.config['networkConfig'][handle]
        log.info("[System] Initializing MMONetwork %s (%s)" % (network['name'], handle))
        if network['active']:
            try:
                MMONetworks[handle] = eval(network['class'])(app, session, handle)
                log.info("[System] -> Initialization of MMONetwork %s (%s) completed" % (network['name'], handle))
                # MMONetworks[handle].setLogLevel(logging.INFO)
                # log.info("Preparing MMONetwork %s (%s) for first request." % (network['name'], handle))
                MMONetworks[handle].prepareForFirstRequest()
            except Exception as e:
                message = "[System] -> Unable to initialize MMONetwork %s (%s) because: %s" % (network['name'], handle, e)
                with app.test_request_context():
                    if session.get('admin'):
                        flash(message, 'error')
                log.error(message)
        else:
            log.info("[System] -> MMONetwork %s (%s) is deactivated" % (network['name'], handle))
    return MMONetworks

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

def getAdminMethods():
    nets = []
    for net in MMONetworks.keys():
        adminMethods = []
        for (method, methodName) in MMONetworks[net].adminMethods:
            adminMethods.append({'name': methodName,
                                 'index': MMONetworks[net].adminMethods.index((method, methodName))})
        nets.append({'handle': MMONetworks[net].handle,
                     'name': MMONetworks[net].name,
                     'methods': adminMethods})
    return nets

def getBox(netHandle, methodHandle):
    if netHandle == "System":
        return SystemBoxes[methodHandle]
    else:
        return MMONetworks[netHandle].getDashboardBox(methodHandle)

# background worker methods (celery)
def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery
celery = make_celery(app)

@celery.task()
def background_worker():
    log.setLevel(logging.INFO)
    log.warning("[System] Background worker is loading the MMONetworks")
    MMONetworks = loadNetworks()
    log.warning("[System] Background worker starts looping")
    firstLoop = time.time()
    loopCount = 0
    lastNotify = time.time()
    startupTime = time.time()
    work = True
    while work:
        log.setLevel(logging.INFO)
        loopCount += 1
        for net in MMONetworks.keys():
            ret = None
            ret = MMONetworks[net].background_worker(log)
            if ret:
                log.info("[%s] -> Result: %s" % (net, ret))

        if firstLoop:
            log.warning("[System] First loop finished. Run took %s seconds." % (time.time() - firstLoop))
            firstLoop = False

        if (time.time() - lastNotify) > 60:
            lastNotify = time.time()
            log.warning("[System] Background worker status: Loop no.: %s; Uptime: %s" % (loopCount, get_long_duration(lastNotify - startupTime)))

        time.sleep(1)

try:
    background_worker.delay()
except Exception as e:
    log.error("[System] Background workers could not be started: %s" % (e))
    sys.exit(2)

# flask error handlers
@app.errorhandler(404)
def not_found(error):
    flash("Page not found!", 'error')
    # return render_template('profile_login.html'), 404
    return redirect(url_for('index'))

@app.errorhandler(401)
def not_found(error):
    flash("Unauthorized request", 'error')
    # return render_template('profile_login.html'), 401
    return redirect(url_for('index'))

@app.errorhandler(403)
def not_found(error):
    flash("Forbidden request", 'error')
    # return render_template('profile_login.html'), 403
    return redirect(url_for('index'))

# app routes
@app.before_first_request
def before_first_request():
    db.session.remove()
    loadNetworks()

@app.before_request
def before_request():
    if '_escaped_fragment_' in request.args and '_escaped_fragment_once_' not in request.args:
        return process.send_process([ "/opt/phantomjs/bin/phantomjs", "--load-images=false", os.path.join(app.config['scriptPath'], "../libs/sep/driver.js"), request.url + "&_escaped_fragment_once_=true" ])
    elif '_escaped_fragment_once_' in request.args:
        session['crawlerRun'] = True
    else:
        session['crawlerRun'] = False

    db.session.remove()
    try:
        session['requests'] += 1
    except KeyError:
        session['requests'] = 0

    if session.get('logged_in'):
        for handle in MMONetworks.keys():
            (ret, message) = MMONetworks[handle].loadNetworkToSession()
            if not ret:
                flash(Markup(message), 'error')

# main routes
@app.route('/About')
def about():
    twitterData = {'widgetUrl': app.config['TWITTERURL'], 'widgetId': app.config['TWITTERWIDGETID']}
    return render_template('about.html', twitter = twitterData)

@app.route('/Development')
def dev():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    if not session.get('admin'):
        log.warning("[System] <%s> tried to access admin without permission!")
        abort(403)
    ret = []
    for handle in MMONetworks.keys():
        try:
            result = MMONetworks[handle].devTest()
        except Exception as e:
            result = e
        ret.append({'handle': handle, 'result': result})
    return render_template('dev.html', result = ret)

# support routes
@app.route('/Images/<imgType>/<imgId>', methods = ['GET', 'POST'])
def get_image(imgType, imgId):
    filePath = os.path.join(app.config['scriptPath'], 'static', imgType)
    fileName = ""
    log.debug("[System] Requesting img type <%s> id <%s>" % (imgType, imgId))

    try:
        if imgType == 'avatar':
            fileName = MMOFriends[int(imgId)].avatar
        elif imgType == 'network':
            if imgId == 'System':
                fileName = 'logo_trans_dark.png'
                filePath = os.path.join(app.config['scriptPath'], 'static')
            else:
                fileName = MMONetworks[imgId].icon
        elif imgType == 'cache':
            fileName = imgId
        elif imgType == 'flag':
            fileName = imgId + '.png'
        elif imgType == 'product':
            fileName = imgId + '.png'

        if os.path.isfile(os.path.join(filePath, fileName)):
            return send_from_directory(filePath, fileName)
        else:
            log.warning("[System] Image not found: %s/%s" % (filePath, fileName))

    except IndexError:
        log.warning("[System] Unknown ID for img type %s: %s" % (imgType, imgId))
    abort(404)

@app.route('/robots.txt')
def get_robots_txt():
    ret = []
    ret.append('User-agent: *')
    ret.append('Allow: /')
    ret.append('Sitemap: %s/sitemap.xml' % app.config['WEBURL'])
    return '\n'.join(ret)

@app.route('/sitemap.xml')
def get_sitemap_xml():
    ret = []
    ret.append('<?xml version="1.0" encoding="UTF-8"?>')
    ret.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    ret.append('    <url>')
    ret.append('      <loc>%s/</loc>' % app.config['WEBURL'])
    ret.append('    </url>')
    ret.append('    <url>')
    ret.append('      <loc>%s/About</loc>' % app.config['WEBURL'])
    ret.append('    </url>')
    ret.append('    <url>')
    ret.append('      <loc>%s/Profile/Register</loc>' % app.config['WEBURL'])
    ret.append('    </url>')
    ret.append('</urlset>')
    return '\n'.join(ret)

# admin routes
@app.route('/Administration/System_Status')
def admin_system_status():
    if not session.get('logged_in'):
        abort(401)
    if not session.get('admin'):
        log.warning("[System] <%s> tried to access admin without permission!")
        abort(403)

    loadedNets = []
    for handle in MMONetworks.keys():
        network = MMONetworks[handle]
        loadedNets.append({ 'handle': handle,
                            'name': network.name,
                            'className': network.__class__.__name__,
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
    return render_template('admin_system_status.html', infos = infos)

@app.route('/Administration/Celery_Status')
def admin_celery_status():
    if not session.get('logged_in'):
        abort(401)
    if not session.get('admin'):
        log.warning("[System] <%s> tried to access admin without permission!")
        abort(403)

    registeredWorkers = []
    i = celery.control.inspect()
    if i.registered():
        for worker in i.registered().keys():
            for task in i.registered()[worker]:
                registeredWorkers.append({ 'worker': worker,
                                           'task': task })

    avtiveTasks = []
    if i.active():
        for worker in i.active().keys():
            for task in i.active()[worker]:
                avtiveTasks.append({ 'worker': worker,
                                     'name': task['name'],
                                     'id': task['id'],
                                     'args': task['args'],
                                     'kwargs': task['kwargs'] })

    scheduledTasks = []
    if i.scheduled():
        for worker in i.scheduled().keys():
            for task in i.scheduled()[worker]:
                scheduledTasks.append({ 'worker': worker,
                                        'eta': task['eta'],
                                        'priority': task['priority'],
                                        'name': task['request']['name'],
                                        'id': task['request']['id'],
                                        'args': task['request']['args'],
                                        'kwargs': task['request']['kwargs'] })

    infos = {}
    infos['registeredWorkers'] = registeredWorkers
    infos['avtiveTasks'] = avtiveTasks
    infos['scheduledTasks'] = scheduledTasks
    return render_template('admin_celery_status.html', infos = infos)

@app.route('/Administration/Background_Jobs_Status')
def admin_bgjob_status():
    if not session.get('logged_in'):
        abort(401)
    if not session.get('admin'):
        log.warning("[System] <%s> tried to access admin without permission!")
        abort(403)

    methodStats = []
    for handle in MMONetworks.keys():
        network = MMONetworks[handle]
        network.getCache('backgroundTasks')
        for task in network.cache['backgroundTasks'].keys():
            methodStats.append(network.cache['backgroundTasks'][task])

    infos = {}
    infos['methodStats'] = methodStats
    return render_template('admin_bgjob_status.html', infos = infos)

# network routes
@app.route('/Network/Show/<netHandle>', methods = ['GET'])
def network_show(netHandle):
    if session.get('logged_in'):
        ret = fetchFriendsList(netHandle)
        if ret:
            return render_template('partner_list.html', friends = ret)
        else:
            return redirect(url_for('index'))
    else:
        abort(401)

@app.route('/Network/Administration', methods = ['GET'])
def network_admin():
    if session.get('logged_in') and session.get('admin'):
        return render_template('network_admin.html', networks = getAdminMethods())
    abort(403)

@app.route('/Network/Administration/<networkHandle>/<int:index>', methods = ['GET'])
def network_admin_do(networkHandle, index):
    if session.get('logged_in') and session.get('admin'):
        ret = {}
        ret['networkName'] = MMONetworks[networkHandle].name
        (method, ret['methodName']) = MMONetworks[networkHandle].adminMethods[index]
        (retValue, ret['methodResult']) = method()
        if not retValue:
            flash(ret['methodResult'], 'error')
        return render_template('network_admin.html', networks = getAdminMethods(), result = ret)
    abort(403)

@app.route('/Network/Link', methods=['GET', 'POST'])
def network_link():
    if not session.get('logged_in'):
        log.warning("[System] Not logged in")
        return redirect(url_for('index'))

    if request:
        if request.method == 'POST':
            if 'handle' in request.form and 'do' in request.form:
                log.info("[System] Linking request via post (handle: %s, do: %s)" % (request.form['handle'], request.form['do']))
                net = MMONetworks[request.form['handle']]
                if request.form['do'] == 'link':
                    return jsonify({ 'message': MMONetworks[request.form['handle']].doLink(request.form['id']) })
                elif request.form['do'] == 'finalize':
                    if MMONetworks[request.form['handle']].finalizeLink(request.form['userKey']):
                        flash('Successfully linked to network %s' % net.description, 'success')
                    else:
                        MMONetworks[request.form['handle']].clearLinkRequest()
                        flash('Unable to link network %s. Please try again.' % net.description, 'error')
                elif request.form['do'] == 'cancel':
                    MMONetworks[request.form['handle']].clearLinkRequest()
            else:
                log.warning("[System] Linking request is missing form fields!")
        else:
            log.warning("[System] Linking request is not POST!")
    return redirect(url_for('index'))

def getNetworksLinkData(request = None):
    log.debug("[System] Returning linked networks (get)")
    linkedNetworks = []
    reLinkNetworks = []
    fetchNetworkLinksData = fetchNetworkLinks(session.get('userid'))
    for net in fetchNetworkLinksData:
        netInfo = MMONetworks[net]
        for link in fetchNetworkLinksData[net]:
            if link['network_data']:
                linkedNetworks.append({'name': netInfo.name,
                                       'description': netInfo.description,
                                       'handle': netInfo.handle,
                                       'icon': url_for('get_image', imgType='network', imgId=netInfo.handle),
                                       'unlinkLink': url_for('network_unlink', netHandle=netInfo.handle, netLinkId=link['id']),
                                       'linked_date': timestampToString(link['linked_date']) })
            else:
                reLinkNetworks.append({ 'id': net,
                                        'icon': url_for('get_image', imgType='network', imgId=netInfo.handle),
                                        'name': netInfo.name,
                                        'handle': netInfo.handle,
                                        'description': netInfo.description,
                                        'linkData': netInfo.getLinkHtml() })

    linkNetwork = []
    for netKey in MMONetworks.keys():
        net = MMONetworks[netKey]
        if net.getLinkHtml():
            linkNetwork.append({ 'id': netKey,
                                 'icon': url_for('get_image', imgType='network', imgId=net.handle),
                                 'name': net.name,
                                 'handle': net.handle,
                                 'description': net.description,
                                 'linkData': net.getLinkHtml() })

    return { 'linkNetwork': linkNetwork, 'linkedNetworks': linkedNetworks, 'reLinkNetworks': reLinkNetworks }
    # log.warning("No ")
    # return redirect(url_for('index'))

@app.route('/Network/Unlink/<netHandle>/<netLinkId>', methods=['GET'])
def network_unlink(netHandle, netLinkId):
    if not session.get('logged_in'):
        abort(401)
    if request.method == 'GET':
        if MMONetworks[netHandle].unlink(session.get('userid'), netLinkId):
            flash('Removed link to %s' % MMONetworks[netHandle].name, 'info')
        else:
            flash('Unable to remove link to %s' % MMONetworks[netHandle].name, 'error')
    return redirect(url_for('index'))

# oid methods
@app.route('/Network/OID/Login/<netHandle>')
@oid.loginhandler
def oid_login(netHandle):
    log.debug("[System] OpenID login for MMONetwork %s from user %s" % (netHandle, session['nick']))
    session['OIDAuthInProgress'] = netHandle
    (doRedirect, retValue) = MMONetworks[netHandle].oid_login(oid)
    if doRedirect:
        log.info("[System] OID redirecting to: %s" % retValue)
        return redirect(retValue)
    else:
        log.info("[System] OID not redirecting...")
        return retValue

@app.route('/Network/OID/Logout')
def oid_logout():
    log.debug("[System] OpenID logout from user %s" % (session['nick']))
    netHandle = session.get('OIDAuthInProgress')
    return redirect(MMONetworks[netHandle].oid_logout(oid))

@oid.after_login
def oid_create_or_login(resp):
    log.debug("[System] OpenID create_or_login from user %s" % (session['nick']))
    netHandle = session.get('OIDAuthInProgress')
    flashMessage, returnUrl = MMONetworks[netHandle].oid_create_or_login(oid, resp)
    session.pop('OIDAuthInProgress')
    flash(flashMessage, 'success')
    return redirect(returnUrl)

# oauth2 methods
@app.route('/Network/Oauth2/Login/<netHandle>', methods=['GET', 'POST'])
def oauth2_login(netHandle):
    log.debug("[System] OpenID2 login for MMONetwork %s from user %s" % (netHandle, session['nick']))
    # print "request.args", request.args
    # print "code", request.args.get("code")
    try:
        name = MMONetworks[netHandle].requestAccessToken(request.args.get("code"))
    except KeyError:
        log.warning("[System] OpenID2 login failed because MMONetwork %s was not found" % (netHandle))
        return redirect(url_for('index'))
    except Exception as e:
        log.error("[System] OpenID2 login for user %s and MMONetwork %s failed because: %s (%s)\nrequest args: %s\ne: %s" % (session['nick'], netHandle, request.args.get("error_description"), request.args.get("error"), request.args, e))
        flash("Unable to link network %s. The administrator was informed of this bug. Please try again." % netHandle, 'error')
        return redirect(url_for('index'))
    # for arg in request.args:
    #     print arg, request.args[arg]
    # print "requestAccessToken returned:", name
    if name:
        message = "Authentication with %s successfull as %s." % (MMONetworks[netHandle].name, name)
        log.info("[System] " + message)
        flash(message, 'success')
    else:
        message = "Authentication with %s  NOT successfull" % MMONetworks[netHandle].name
        log.warning("[System] " + message)
        flash(message, 'error')
    return redirect(url_for('index'))

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
                flash("Passwords do not match!", 'error')
                valid = False

            if len(request.form['nick']) < 3:
                flash("Nickname is too short", 'error')
                valid = False

            if len(request.form['password']) < 8:
                flash("Password is too short", 'error')
                valid = False

            #and further checks for registration plz
            # - user needs to be uniq!
            # - minimal field length
            # - is the website a website?
            # - max length (cut oversize)

        else:
            valid = False
            flash("Please fill out all the fields!", 'error')

        if valid:
            newUser = MMOUser(request.form['nick'])
            newUser.email = request.form['email']
            newUser.name = request.form['name']
            if request.form['website'].startswith("http"):
                newUser.website = request.form['website']
            elif len(request.form['website']):
                newUser.website = "http://" + request.form['website']
            else:
                newUser.website = ""
            newUser.setPassword(request.form['password'])
            if request.form['nick'] == app.config['ROOTUSER']:
                log.info("[System] Registred root user: %s" % request.form['nick'])
                newUser.admin = True
                newUser.locked = False
                newUser.veryfied = True

            db.session.add(newUser)
            try:
                db.session.flush()
                db.session.commit()
                actUrl = app.config['WEBURL'] + url_for('profile_verify', userId=newUser.id, verifyKey=newUser.verifyKey)
                if send_email(app, newUser.email,
                              "MMOJunkies Activation Email",
                              "<h3>Hello %s</h3>We are happy to welcome you to MMOJunkies!<br>Please verify your account with <a href='%s'>this link</a>.<br><br><b>To remove the recurring message in Teamspeak, you have to connect yout TS3 user in the 'Network Connections' box.</b><br>Have fun and see you soon ;)" % (request.form['nick'], actUrl),
                              'logo_banner1_mmo_color_qr.png'):
                    flash("Please check your mails at %s" % newUser.email, 'info')
                else:
                    flash("Error sending the email to you.", 'error')
                # return redirect(url_for('profile_login'))
                return redirect(url_for('index'))

            except (IntegrityError, InterfaceError, InvalidRequestError) as e:
                db.session.rollback()
                flash("SQL Alchemy Error: %s" % e, 'error')
                log.warning("[System] SQL Alchemy Error: %s" % e)
            # db.session.expire(newUser)
    
    return render_template('profile_register.html', values = request.form)

@app.route('/Profile/Show', methods=['GET', 'POST'])
def profile_show(do = None):
    # gravatar: https://de.gravatar.com/site/implement/images/python/
    if not session.get('logged_in'):
        abort(401)
    myUser = getUserById(session.get('userid'))
    myUser.load()
    userChanged = False
    if request.method == 'POST':
        if request.form['do'] == "pwchange":
            if myUser.checkPassword(request.form['oldpassword']):
                if request.form['newpassword1'] == request.form['newpassword2']:
                    if len(request.form['newpassword1']) < 8:
                        flash("Password is too short", 'error')
                    else:
                        myUser.setPassword(request.form['newpassword1'])
                        userChanged = True
                else:
                    flash("New passwords do not match!", 'error')
            else:
                flash("Old password not correct!", 'error')
        elif request.form['do'] == "editprofile":
            if request.form['website'].startswith("http"):
                myUser.website = request.form['website']
            else:
                myUser.website = "http://" + request.form['website']
            myUser.name = request.form['name']
            userChanged = True
    if userChanged:
        db.session.merge(myUser)
        db.session.flush()
        db.session.commit()
        flash("Profile changed", 'success')

    size = 80
    gravatar_url = "//www.gravatar.com/avatar/" + hashlib.md5(myUser.email.lower()).hexdigest() + "?"
    gravatar_url += urllib.urlencode({'d':app.config['WEBURL'] + url_for('static', filename='logo.png'), 's':str(size)})

    return render_template('profile_show.html', values = myUser, nicknames = myUser.nicks.all(), userAvatar = gravatar_url)

@app.route('/Profile/Nick/<do>', methods=['GET', 'POST'])
@app.route('/Profile/Nick/<do>/<nick>', methods=['GET', 'POST'])
def profile_nick(do, nick = None):
    if not session.get('logged_in'):
        abort(401)
    if not nick:
        nick = request.form['nick']
    myUser = getUserById(session.get('userid'))
    myUser.load()

    if do == "add":
        myUser.addNick(nick)
    elif do == "remove":
        myUser.removeNick(nick)

    return redirect(url_for('profile_show'))

@app.route('/Profile/Verify/<userId>/<verifyKey>', methods=['GET'])
def profile_verify(userId, verifyKey):
    log.info("[System] Verify userid %s" % userId)
    verifyUser = getUserById(userId)
    if not verifyUser:
        flash("User not found to verify.")
    elif verifyUser.verify(verifyKey):
        db.session.merge(verifyUser)
        db.session.flush()
        db.session.commit()
        if verifyUser.veryfied:
            # db.session.expire(verifyUser)
            flash("Verification ok. Please log in.", 'success')
            # return redirect(url_for('profile_login'))
            return redirect(url_for('index'))
        else:
            flash("Verification NOT ok. Please try again.", 'error')
    # db.session.expire(verifyUser)
    return redirect(url_for('index'))

@app.route('/Profile/Login', methods=['GET', 'POST'])
@app.route('/Login', methods=['GET', 'POST'])
def profile_login():
    if request.method == 'POST':
        log.info("[System] Trying to login user: %s" % request.form['nick'])
        myUser = False
        try:
            myUser = getUserByNick(request.form['nick'])
        except Exception as e:
            log.warning('[System] Error finding user: "%s" -> %s' % (request.form['nick'], e))
            flash('Error locating your user', 'error')
            
            return redirect(url_for('profile_logout'))

        if myUser:
            myUser.load()
            if not myUser.veryfied:
                flash("User not yet veryfied. Please check your email for the unlock key.", 'info')
                return redirect(url_for('index'))
            elif myUser.locked:
                flash("User locked. Please contact an administrator.", 'info')
                return redirect(url_for('index'))
            elif myUser.checkPassword(request.form['password']):
                log.info("[System] <%s> logged in" % myUser.nick)
                session['logged_in'] = True
                session['userid'] = myUser.id
                session['nick'] = myUser.nick
                session['admin'] = myUser.admin
                session['logindate'] = time.time()
                session['networks'] = []
                for net in MMONetworks.keys():
                    session['networks'].append({'name': MMONetworks[net].name, 'handle': MMONetworks[net].handle})
                session['requests'] = 0
                
                #loading network links:
                # for net in MMONetworks.keys():
                #     log.debug("[System] Loading links for %s@%s" % (myUser.nick, MMONetworks[net].name))
                #     MMONetworks[net].loadNetworkToSession()

            else:
                log.info("[System] Invalid password for %s" % myUser.nick)
                flash('Invalid login', 'error')
        else:
            flash('Invalid login', 'error')

    return redirect(url_for('index'))
    # return render_template('profile_login.html')

@app.route('/Profile/Logout')
@app.route('/Logout')
def profile_logout():
    session.pop('logged_in', None)
    session.pop('nick', None)
    session.pop('admin', None)
    session.pop('logindate', None)
    session.clear()
    return redirect(url_for('index'))

# partner routes
@app.route('/Partner/List')
def partner_list():
    if session.get('logged_in'):
        ret = fetchFriendsList()
        if ret:
            return render_template('partner_list.html', friends = ret)
        else:
            return redirect(url_for('index'))
    else:
        abort(401)

@app.route('/Partner/Find')
def partner_find():
    if session.get('logged_in'):
        retFriendsFindList = []
        for handle in MMONetworks.keys():
            (res, findList) = MMONetworks[handle].findPartners()
            if res:
                retFriendsFindList += findList
            else:
                flash(findList, 'error')
        return render_template('partner_find.html', friends = retFriendsFindList)
    else:
        abort(401)

@app.route('/Partner/Show/<partnerId>/', methods = ['GET', 'POST'])
@app.route('/Partner/Show/<partnerId>/<netHandle>/', methods = ['GET', 'POST'])
def partner_show(partnerId, netHandle = None):
    if not session.get('logged_in'):
        abort(401)

    active, count, networks = 0, 0, []
    for net in MMONetworks.keys():
        linkInfo = MMONetworks[net].getNetworkLinks(partnerId)
        if linkInfo:
            netData = {}
            netData['linkData'] = []
            if MMONetworks[net].handle == netHandle:
                active = count
            netData['name'] = MMONetworks[net].name
            netData['handle'] = MMONetworks[net].handle

            for link in linkInfo:
                netData['linkData'].append(MMONetworks[net].getPartnerDetails(link['network_data']))
                networks.append(netData)
                count += 1

    # print "zzzz", networks
    myUser = getUserById(partnerId)
    if not myUser:
        flash("User not found", 'error')
        return redirect(url_for('index'))
    
    myUser.load()

    size = 120
    gravatar_url = "//www.gravatar.com/avatar/" + hashlib.md5(myUser.email.lower()).hexdigest() + "?"
    gravatar_url += urllib.urlencode({'d':app.config['WEBURL'] + url_for('static', filename='logo.png'), 's':str(size)})

    return render_template('partner_show.html',
                            myUser = myUser,
                            nicknames = myUser.nicks.all(),
                            userAvatar = gravatar_url,
                            networks = networks,
                            active = active)

@app.route('/Partner/Details/<netHandle>/<partnerId>', methods = ['GET', 'POST'])
def partner_details(netHandle, partnerId):
    log.info("Trying to show partner details for netHandle %s and partnerId %s" % (netHandle, partnerId))
    if not session.get('logged_in'):
        abort(401)
    return render_template('partner_details.html', details = MMONetworks[netHandle].getPartnerDetails(partnerId))

# Dashboard methods (general)
def tmpFunc(nothing = None):
    return True

def getSystemStats(request):
    bgTasks = 0
    for handle in MMONetworks.keys():
        MMONetworks[handle].getCache('backgroundTasks')
        for task in MMONetworks[handle].cache['backgroundTasks'].keys():
            bgTasks += 1

    users = 0
    for user in MMOUser.query.all():
        users += 1

    loadedNets = 0
    for handle in MMONetworks.keys():
        loadedNets += 1

    stats = {}
    for net in MMONetworks.keys():
        stats.update({ MMONetworks[net].name: {
            'description': MMONetworks[net].description,
            'data': MMONetworks[net].getStats(),
            'handle': net,
            'icon': url_for('get_image', imgType='network', imgId=net)
            }})
    if session.get('admin'):
        stats.update({ 'System': {
                'data': {
                    'Users Registred': users,
                    'Background Tasks': bgTasks,
                    'Networks Loaded': loadedNets,
                    'Session Requests': session['requests'],
                    'Session Login': timestampToString(session['logindate']),
                    'Application Start': timestampToString(app.config['startupDate']) },
                'icon': url_for('get_image', imgType='network', imgId='System'),
                'description': "MMOJunkies Friends by Cernunnos",
                'handle': "system" }})
    return stats

def getSystemUsers(request):
    if session.get('logged_in'):
        usersReturn, friendNets,  netsReturn = {}, {}, {}
        for net in MMONetworks.keys():
            (res, findList) = MMONetworks[net].getPartners()
            if res:
                friendNets[net] = findList
                netsReturn[net] = {}
                netsReturn[net]['iconUrl'] = url_for('get_image', imgType='network', imgId=net)
                netsReturn[net]['name'] = MMONetworks[net].name
                netsReturn[net]['description'] = MMONetworks[net].description
                netsReturn[net]['usersConnected'] = 0
            else:
                log.info("[System] Unable to fetch network users from %s" % findList)

        users = MMOUser.query.all()
        for user in users:
            if user.id == session['userid']:
                continue
            if user.veryfied and not user.locked:
                userNets, userNicks = [], []
                for net in friendNets:
                    for friend in friendNets[net]:
                        if str(friend['mmoid']) == str(user.id):
                            netsReturn[net]['usersConnected'] += 1
                            userNets.append(net)

                for nick in user.nicks.all():
                    userNicks.append(nick.nick)

                gravatar_url = "//www.gravatar.com/avatar/" + hashlib.md5(user.email.lower()).hexdigest() + "?"
                gravatar_url += urllib.urlencode({'d':app.config['WEBURL'] + url_for('static', filename='logo.png'), 's':str(16)})

                usersReturn[user.id] = { 'nick': user.nick,
                                         'avatar': gravatar_url,
                                         'url': url_for('partner_show', partnerId = user.id),
                                         'aliases': userNicks,
                                         'name': user.name,
                                         'website': user.website,
                                         'admin': user.admin,
                                         'nets': userNets }

        return { 'users': usersReturn, 'nets': netsReturn }
    else:
        abort(401)

def getLastly(request):
    lastlyReturn = []
    nets = {}
    for net in MMONetworks.keys():
        nets[net] = {   'name': MMONetworks[net].name,
                        'description': MMONetworks[net].description,
                        'handle': net,
                        'icon': url_for('get_image', imgType='network', imgId=net) }

        ret = MMONetworks[net].getLastly()
        if ret:
            for date in ret.keys():
                lastlyReturn.append({'date': date, 'age': get_short_age(float(date)), 'text': ret[date], 'net': net})

    return { 'lastly': sorted(lastlyReturn, key=lambda k: k['date'], reverse=True)[:30], 'net': nets }

# Dashboard functions
SystemBoxes["stats"] = createDashboardBox(getSystemStats, "System", "stats", {'title': 'Statistics'})
SystemBoxes["login"] = createDashboardBox(tmpFunc, "System", "login", {'loggedin': False, 'title': 'Login'})
SystemBoxes["navigation"] = createDashboardBox(tmpFunc, "System", "navigation", {'loggedin': True, 'title': 'Navigation', 'sticky': True})
SystemBoxes["networkLink"] = createDashboardBox(getNetworksLinkData, "System", "networkLink", {'loggedin': True, 'title': 'Network Connections'})
SystemBoxes["users"] = createDashboardBox(getSystemUsers, "System", "users", {'loggedin': True, 'title': 'Users'})
SystemBoxes["lastly"] = createDashboardBox(getLastly, "System", "lastly", {'title': 'Lastly on MMOJunkies'})

# Dashboard routes
@app.route('/')
def index():
    if session.get('logged_in'):
        linked = False
        links = fetchNetworkLinks(session['userid'])
        for link in links:
            if links[link]:
                linked = True
        if not linked:
            flash("You have no network connected. Please do so in the 'Network Connections' box.", 'info')
    boxes = []
    for box in SystemBoxes.keys():
        if checkShowBox(session, SystemBoxes[box]):
            boxes.append(SystemBoxes[box])
    for net in MMONetworks.keys():
        for boxKey in MMONetworks[net].getDashboardBoxes():
            box = MMONetworks[net].getDashboardBox(boxKey)
            if checkShowBox(session, box):
                boxes.append(box)
    return render_template('dashboard.html', boxes = boxes)

@app.route('/Dashboard')
def dashboard():
    return redirect(url_for('index'))

# Dashboard HTML API
@app.route('/Dashboard/<netHandle>/<methodHandle>', methods = ['GET', 'POST'])
def dashboard_method_html(netHandle, methodHandle):
    box = getBox(netHandle, methodHandle)
    if checkShowBox(session, box):
        return render_template(box['settings']['template'], box = box, boxData = box['method'](request))
    else:
        abort(401)

# Dashboard JSON API
@app.route('/Api/Dashboard/<netHandle>/<methodHandle>', methods = ['POST', 'GET'])
def dashboard_method_json(netHandle, methodHandle):
    box = getBox(netHandle, methodHandle)
    if checkShowBox(session, box):
        return jsonify(box['method'](request))
    else:
        return jsonify({'error': True, 'message': 'You are not allowed to request this box'})

@app.route('/Api/Partner/Details/<netHandle>/<partnerId>', methods = ['POST'])
def json_partner_details(netHandle, partnerId):
    log.info("[System] Trying to show JSON partner details for netHandle %s and partnerId %s" % (netHandle, partnerId))
    if not session.get('logged_in'):
        abort(401)
    return jsonify(MMONetworks[netHandle].getPartnerDetails(partnerId))
