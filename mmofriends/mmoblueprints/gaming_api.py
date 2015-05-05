#!/usr/bin/env python
# -*- coding: utf-8 -*-

# system imports
from ..mmobase.mmouser import *
from ..mmobase.mmonetwork import *
from ..mmobase.mmoutils import *
from ..mmobase.ts3mmonetwork import *
from ..mmobase.valvenetwork import *
from ..mmobase.blizznetwork import *
from ..mmobase.twitchnetwork import *
from ..mmobase.rssnews import *

log = getLogger(level=logging.INFO)

# flask imports
try:
    from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, make_response, send_from_directory, current_app, jsonify, Markup, Blueprint
except ImportError:
    log.error("[System] Please install flask")
    sys.exit(2)

try:
    from flask.ext.sqlalchemy import SQLAlchemy
    from sqlalchemy.exc import IntegrityError, InterfaceError, InvalidRequestError
except ImportError:
    log.error("[System] Please install the sqlalchemy extension for flask")
    sys.exit(2)

gaming_api = Blueprint('gaming_api', __name__)

def getGames():
    games = {}
    for net in MMONetworks.keys():
        games[net] = MMONetworks[net].getGames()
    return games

def getGamesOfUser(userId):
    games = {}
    for net in MMONetworks.keys():
        games[net] = MMONetworks[net].getGamesOfUser(userId)
    return games

def getUsersOfGame(gameName):
    nets = {}
    for net in MMONetworks.keys():
        nets[net] = MMONetworks[net].getUsersOfGame(gameName)
    return nets

def getGameLinks(request):
    # https://github.com/IMBApplications/rmk.gabi/blob/master/gabicustom.py 132
    return { 'games': getGames() }

# Gaming URLs
@gaming_api.route('/Icon/<netId>/<gameId>', methods = ['POST', 'GET'])
def get_game_icon(netId, gameId):
    return redirect(MMONetworks[netId].getGameIcon(gameId))

# Gaming JSON API
@gaming_api.route('/Api/Get/', methods = ['POST', 'GET'])
def json_get_games():
    log.info("[System] Trying to show JSON games")
    return jsonify(getGames())

@gaming_api.route('/Api/GetGamesOfUser/<userId>', methods = ['POST', 'GET'])
def json_get_games_of_user(userId):
    log.info("[System] Trying to show JSON games of user")
    if not session.get('logged_in'):
        abort(401)
    return jsonify(getGamesOfUser(userId))

@gaming_api.route('/Api/GetUsersOfGame/<gameName>', methods = ['POST', 'GET'])
def json_get_users_of_game(gameName):
    log.info("[System] Trying to show JSON users of game")
    if not session.get('logged_in'):
        abort(401)
    return jsonify(getUsersOfGame(gameName))