#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

def getUserByEmail(email = None):
    with app.test_request_context():
        ret = MMOUser.query.filter(MMOUser.email.ilike(email)).first()
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

def checkPassword(password1, password2):
    valid = True
    if password1 != password2:
        flash(gettext("Passwords do not match!"), 'error')
        valid = False

    if len(password1) < 8:
        flash(gettext("Password is too short"), 'error')
        valid = False

    #and further checks for registration plz
    # - user needs to be uniq!
    # - minimal field length
    # - is the website a website?
    # - max length (cut oversize)
    return valid