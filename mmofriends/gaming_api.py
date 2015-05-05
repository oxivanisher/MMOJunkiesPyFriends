#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Blueprint

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