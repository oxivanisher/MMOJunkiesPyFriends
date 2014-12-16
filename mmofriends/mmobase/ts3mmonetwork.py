#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import socket
import os
import random

from flask import current_app, url_for
from mmofriends import db
from mmonetwork import *
from mmoutils import *

try:
    import ts3
except ImportError:
    print "Please install PyTS3"
    import sys
    sys.exit(2)

class TS3Network(MMONetwork):

    # class overwrites
    def __init__(self, app, session, handle):
        super(TS3Network, self).__init__(app, session, handle)
        # activate debug while development
        # self.setLogLevel(logging.DEBUG)

        self.server = None
        self.connected = False
        self.clientftfid = 0

        # admin methods
        self.adminMethods.append((self.cacheAvailableClients, 'Recache available clients'))
        self.adminMethods.append((self.cacheFiles, 'Cache files'))

        # background updater methods
        self.registerWorker(self.updateServerInfo, 900)
        self.registerWorker(self.cacheAvailableClients, 10800)
        self.registerWorker(self.loadMissingClientInformations, 10800)
        self.registerWorker(self.refreshOnlineClients, 10)
        self.registerWorker(self.updateOnlineClientInfos, 60)
        self.registerWorker(self.cacheFiles, 900)
        self.registerWorker(self.userWatchdog, 120)

    # background worker methods
    def refreshOnlineClients(self, logger = None):
        if not logger:
            logger = self.log
        if self.connect():
            self.getCache('onlineClients')
            if not self.connect():
                logger.warning("[%s] Not refreshing online clients because we are disconnected" % (self.handle))
                return False

            logger.debug("[%s] Fetching online clients from server" % (self.handle))
            response = self.sendCommand("clientlist -icon")
            self.cache['onlineClients'] = {}
            clients = {}

            try:
                for client in response.data:
                    try:
                        clients[client['clid']] = client
                    except KeyError:
                        logger.warning("refreshOnlineClients: Removing missing client %s" % client['clid'])
                        clients.pop(client['clid'], None)
                        pass
            except AttributeError:
                return True

            for client in clients.keys():
                # ignoring console users
                if int(clients[client]['client_type']) != 1:
                    self.cache['onlineClients'][clients[client]['client_database_id']] = clients[client]

            self.setCache('onlineClients')
            return "%s online client(s) updated" % len(self.cache['onlineClients'])
        else:
            return "Not connected to TS3 Server"

    def updateOnlineClientInfos(self, logger = None):
        if self.connect():
            self.getCache('onlineClients')
            if not logger:
                logger = self.log

            for client in self.cache['onlineClients']:
                logger.debug("[%s] Updating online client info for: %s" % (self.handle, self.cache['onlineClients'][client]['client_database_id']))
                self.fetchUserDetatilsByCldbid(self.cache['onlineClients'][client]['client_database_id'])
            return "%s online client(s) updated" % len(self.cache['onlineClients'])
        else:
            return "Not connected to TS3 Server"

    def cacheAvailableClients(self, logger = None):
        if self.connect():
            if not logger:
                logger = self.log
            self.getCache('clientDatabase')
            logger.debug("[%s] Fetching all clients from server" % (self.handle))

            clientNum = 0
            serverData = self.sendCommand('clientdblist -count').data[0]
            if 'count' in serverData:
                clientTot = int(serverData['count'])
            else:
                clientTot = 0
            allClients = []
            while clientNum < clientTot:
                logger.debug("[%s] Fetching all clients, starting at: %s" % (self.handle, clientNum))
                newClients = self.sendCommand('clientdblist start=%s' % clientNum).data
                clientNum += len(newClients)
                allClients += newClients
            for client in allClients:
                try:
                    self.cache['clientDatabase'][client['cldbid']] = client
                except KeyError:
                    logger.warning("cacheAvailableClients: Removing missing client %s" % client)

            allNewClients = self.cache['clientDatabase'].keys()
            allOldClients = allClients.keys()
            for client in [x for x in allOldClients if x not in allNewClients]:
                    logger.warning("cacheAvailableClients: Removing client from db which is mission in ts3 (probably cleaned): %s" % client)
                    # self.cache['clientDatabase'].pop(client['cldbid'], None)
                    # self.cache['clientDatabase'].pop(client, None)
                    pass

            self.setCache('clientDatabase')

            logger.debug("[%s] Fetched %s clients" % (self.handle, clientNum))
            return "%s client(s) updated" % len(allClients)
        else:
            return "Not connected to TS3 Server"

    def loadMissingClientInformations(self, logger = None):
        if self.connect():
            if not logger:
                logger = self.log
            count = 0

            self.getCache('clientDatabase')
            self.getCache('clientInfoDatabase')
            for client in self.cache['clientDatabase'].keys():
                if client not in self.cache['clientInfoDatabase'].keys():
                    self.fetchUserDetatilsByCldbid(client, True)
                    count += 1

            return "%s client(s) updated" % count
        else:
            return "Not connected to TS3 Server"

    def updateServerInfo(self, logger = None):
        if not logger:
            logger = self.log
        self.getCache('serverInfo')
        if self.connect():
            # fetching channels
            ccount = 0
            logger.debug("[%s] Fetching channels" % (self.handle))
            self.cache['serverInfo']['channelList'] = []
            result = self.sendCommand('channellist -icon')
            for channel in result.data:
                try:
                    if int(channel['channel_icon_id']) < 0:
                        channel['channel_icon_id'] = str(int(channel['channel_icon_id']) + 4294967296)
                except KeyError:
                    channel['channel_icon_id'] = 0
                self.cache['serverInfo']['channelList'].append(channel)
                ccount += 1

            # fetching groups
            gcount = 0
            logger.debug("[%s] Fetching groups" % (self.handle))
            self.cache['serverInfo']['groupList'] = {}
            result = self.sendCommand('servergrouplist')
            for group in result.data:
                # logger.error("group id %s" % group)
                self.cache['serverInfo']['groupList'][group['sgid']] = group
                gcount += 1

            # fetching channel groups
            cgcount = 0
            logger.debug("[%s] Fetching channel groups" % (self.handle))
            self.cache['serverInfo']['channelGroupList'] = {}
            result = self.sendCommand('channelgrouplist')
            for group in result.data:
                self.cache['serverInfo']['channelGroupList'][group['cgid']] = group
                cgcount += 1
            self.setCache('serverInfo')
            return "%s channel(s), %s group(s) and %s channel group(s) updated" % (ccount, gcount, cgcount)
        else:
            return "Not connected to TS3 Server"

    def cacheFiles(self, logger = None):
        count = 0
        if not logger:
            logger = self.log
        self.getCache('onlineClients')
        self.getCache('serverInfo')
        self.getCache('clientDatabase')
        if self.connect():
            logger.debug("[%s] Caching server icon" % (self.handle))
            self.cacheServerIcon(self.cache['serverInfo']['serverInfo']['virtualserver_icon_id'])

            logger.debug("[%s] Caching channel icons" % (self.handle))
            for channel in self.cache['serverInfo']['channelList']:
                logger.debug("[%s] Caching file for channel: %s" % (self.handle, channel['channel_name']))
                self.cacheIcon(channel['channel_icon_id'])
                count += 1

            logger.debug("[%s] Caching client icons" % (self.handle))
            for client in self.cache['onlineClients'].keys():
                logger.debug("[%s] Caching file for client: %s" % (self.handle, self.cache['onlineClients'][client]['client_nickname']))
                self.cacheIcon(self.cache['onlineClients'][client]['client_icon_id'])
                count += 1

            logger.debug("[%s] Caching group icons" % (self.handle))
            for group in self.cache['serverInfo']['groupList'].keys():
                logger.debug("[%s] Caching file for group: %s" % (self.handle, self.cache['serverInfo']['groupList'][group]['name']))
                if int(self.cache['serverInfo']['groupList'][group]['iconid']):
                    self.cacheIcon(self.cache['serverInfo']['groupList'][group]['iconid'])
                    count += 1

            logger.debug("[%s] Caching user avatars" % (self.handle))
            for client in self.cache['clientDatabase'].keys():
                if 'client_flag_avatar' in self.cache['clientDatabase'][client]:
                    if self.cache['clientDatabase'][client]['client_flag_avatar']:
                        logger.debug("[%s] Caching avatar for client: %s" % (self.handle, self.cache['clientDatabase'][client]['client_nickname']))
                        avatar = "/avatar_%s" % self.cache['clientDatabase'][client]['client_base64HashClientUID']
                        self.cacheFile(avatar)
                        count += 1

            return "%s files cached" % count
        else:
            return "Not connected to TS3 Server"

    def userWatchdog(self, logger = None):
        spamedCount = 0
        if not logger:
            logger = self.log
        links = []

        if self.connect():
            self.getCache('onlineClients')
            self.getCache('userWatchdog')
            self.getCache('clientDatabase')
            for link in self.getNetworkLinks():
                links.append(link['network_data'])
            for client in self.cache['onlineClients'].keys():
                if client not in links:
                    if client not in self.cache['userWatchdog']:
                        self.cache['userWatchdog'][client] = 0
                    if self.cache['userWatchdog'][client] < (time.time() - self.config['userWatchdogSpamTimeout']):
                        logger.info("[%s] Spamming user: %s" % (self.handle, self.cache['onlineClients'][client]['client_nickname']))
                        for group in self.cache['clientDatabase'][client]['groups']:
                            if int(group['sgid']) == self.config['memberGroupId']:
                                # self.sendCommand('servergroupaddclient sgid=%s cldbid=%s' % (self.config['defaultGuestGroupId'], client))
                                self.sendCommand('servergroupdelclient sgid=%s cldbid=%s' % (group['sgid'], client))
                            # if int(group['sgid']) == self.config['adminGroupIds']:

                        self.cache['userWatchdog'][client] = time.time()
                        self.server.clientpoke(self.cache['onlineClients'][client]['clid'], self.config['userWatchdogSpamMessage'])
                        spamedCount += 1
                    else:
                        spamAgainIn = get_short_duration(self.config['userWatchdogSpamTimeout'] - (time.time() - self.cache['userWatchdog'][client]))
                        logger.debug("[%s] Not spaming (again in %ss): %s (%s)" % (self.handle, spamAgainIn, self.cache['onlineClients'][client]['client_nickname'], client))
                else:
                    logger.debug("[%s] Not spaming (already linked): %s (%s)" % (self.handle, self.cache['onlineClients'][client]['client_nickname'], client))
                    for group in self.cache['clientDatabase'][client]['groups']:
                        if int(group['sgid']) in self.config['guestGroups']:
                            logger.warning("[%s] Setting missing member group" % (self.handle))
                            self.sendCommand('servergroupaddclient sgid=%s cldbid=%s' % (self.config['memberGroupId'], client))

            self.setCache('userWatchdog')
            return "%s users spamed" % (spamedCount)
        else:
            return "Unable to connect to server"

    # Class overwrites
    def getStats(self):
        self.log.debug("[%s] Requesting stats" % (self.handle))
        self.getCache('onlineClients')
        self.getCache('clientDatabase')

        return {
            'Clients Online': len(self.cache['onlineClients']),
            'Clients in Database': len(self.cache['clientDatabase']),
        }

    def getPartners(self, **kwargs):
        self.getCache('onlineClients')
        allLinks = self.getNetworkLinks()
        self.getCache('clientDatabase')
        self.getCache('clientInfoDatabase')
        self.getCache('serverInfo')

        ret = []
        try:
            kwargs['onlineOnly']
            clientList = self.cache['onlineClients'].keys()
        except KeyError:
            clientList = self.cache['clientDatabase'].keys()

        for cldbid in clientList:
            myself = False
            MMOUser = False
            for link in allLinks:
                MMOUser = True
                if link['network_data'] == cldbid and link['user_id'] == self.session['userid']:
                    myself = True
            if myself:
                continue
            if not MMOUser:
                continue

            # player state
            if 'client_nickname' not in self.cache['clientDatabase'][cldbid]:
                self.log.debug("Nickname of cldbid %s not found. Ignoring this user." % cldbid)
                continue
            nick = self.cache['clientDatabase'][cldbid]['client_nickname']

            if cldbid in self.cache['onlineClients']:
                state = "Online"
            else:
                state = "Offline"

            # user server group
            try:
                userGroups = []
                userGroupIcon = 0
                userGroupName = ""
                for group in self.cache['clientDatabase'][cldbid]['groups']:
                    for g in self.cache['serverInfo']['groupList'].keys():
                        if g == group['sgid']:
                            userGroupIcon = 'icon_' + self.cache['serverInfo']['groupList'][g]['iconid']
                            self.cacheIcon(self.cache['serverInfo']['groupList'][g]['iconid'])
                            continue
                    userGroups.append(group['name'])
                    userGroupName = group['name']
            except KeyError:
                pass

            # Get channel details
            channelName = self.description
            channelIcon = None
            try:
                for channel in self.cache['serverInfo']['channelList']:
                    if channel['cid'] == self.cache['clientInfoDatabase'][cldbid]['cid']:
                        try:
                            channelName = channel['channel_name'].decode('utf-8')
                        except UnicodeEncodeError:
                            channelName = channel['channel_name']
                        channelIcon = channel['channel_icon_id']
                        self.cacheIcon(channelIcon)
                        continue
            except (IndexError, KeyError):
                pass

            # network icons
            networkImgs = [{
                            'type': 'network',
                            'name': self.handle,
                            'title': self.name
                        },{
                            'type': 'cache',
                            'name': 'icon_' + str(int(self.cache['serverInfo']['serverInfo']['virtualserver_icon_id']) + 4294967296),
                            'title': channelName
                        }]
            try:
                if int(channelIcon) != 0 and channelIcon:
                    networkImgs.append({'type': 'cache', 'name': 'icon_' + channelIcon, 'title': channelName })
            except TypeError:
                pass

            # country flags
            friendImgs = []
            try:
                if self.cache['clientInfoDatabase'][cldbid]['client_country']:
                    friendImgs.append({ 'type': 'flag',
                                        'name': self.cache['clientInfoDatabase'][cldbid]['client_country'].lower(),
                                        'title': self.cache['clientInfoDatabase'][cldbid]['client_country'] })
            except KeyError:
                pass

            # user froup
            if userGroupIcon != 'icon_0' and userGroupIcon != 0:
                friendImgs.append({ 'type': 'cache', 'name': userGroupIcon, 'title': userGroupName })

            # client channel group
            try:
                cgid = self.cache['clientInfoDatabase'][cldbid]['client_channel_group_id']
                if int(self.cache['serverInfo']['channelGroupList'][cgid]['iconid']) != 0:
                    friendImgs.append({ 'type': 'cache', 'name': 'icon_' + self.cache['serverInfo']['channelGroupList'][cgid]['iconid'], 'title': self.cache['serverInfo']['channelGroupList'][cgid]['name'] })
            except KeyError:
                pass

            linkId = None
            for link in allLinks:
                if cldbid == link['network_data']:
                    linkId = link['user_id']

            ret.append({'id': cldbid,
                        'mmoid': linkId,
                        'nick': nick,
                        'state': state,
                        'networkText': channelName,
                        'netHandle': self.handle,
                        'networkImgs': networkImgs,
                        'friendImgs': friendImgs
                })

        return (True, ret)

    def getPartnerDetails(self, cldbid):
        moreInfo = {}
        self.getCache('onlineClients')
        self.getCache('clientDatabase')
        self.getCache('clientInfoDatabase')
        self.getCache('serverInfo')

        try:
        #fetch avatar
            if 'client_flag_avatar' in self.cache['clientDatabase'][cldbid].keys():
                if self.cache['clientDatabase'][cldbid]['client_flag_avatar']:
                    avatar = "/avatar_%s" % self.cache['clientDatabase'][cldbid]['client_base64HashClientUID']
                    self.cacheFile(avatar)
                    self.setPartnerAvatar(moreInfo, avatar)

            self.setPartnerDetail(moreInfo, "Description", self.cache['clientDatabase'][cldbid]['client_description'])
            self.setPartnerDetail(moreInfo, "Created", timestampToString(self.cache['clientDatabase'][cldbid]['client_created']))
            self.setPartnerDetail(moreInfo, "Last Connection", timestampToString(self.cache['clientDatabase'][cldbid]['client_lastconnected']))
            self.setPartnerDetail(moreInfo, "Total Connections", self.cache['clientDatabase'][cldbid]['client_totalconnections'])

            userGroups = []
            userGroupIcon = 0
            userGroupName = "Unknown"
            for group in self.cache['clientDatabase'][cldbid]['groups']:
                for g in self.cache['serverInfo']['groupList'].keys():
                    if self.cache['serverInfo']['groupList'][g]['sgid'] == group['sgid']:
                        userGroupIcon = 'icon_' + self.cache['serverInfo']['groupList'][g]['iconid']
                        self.cacheIcon(self.cache['serverInfo']['groupList'][g]['iconid'])
                userGroups.append(group['name'])
                userGroupName = group['name']
            self.setPartnerDetail(moreInfo, "Server Groups", ', '.join(userGroups))

            if self.session.get('admin'):
                self.setPartnerDetail(moreInfo, "Last IP", self.cache['clientDatabase'][cldbid]['client_lastip'])
                self.setPartnerDetail(moreInfo, "Bytes uploaded month", bytes2human(self.cache['clientDatabase'][cldbid]['client_month_bytes_uploaded']))
                self.setPartnerDetail(moreInfo, "Bytes downloaded month", bytes2human(self.cache['clientDatabase'][cldbid]['client_month_bytes_downloaded']))
                self.setPartnerDetail(moreInfo, "Bytes uploaded total", bytes2human(self.cache['clientDatabase'][cldbid]['client_total_bytes_uploaded']))
                self.setPartnerDetail(moreInfo, "Bytes downloaded total", bytes2human(self.cache['clientDatabase'][cldbid]['client_total_bytes_downloaded']))

            for entry in self.cache['clientInfoDatabase'].keys():
                if self.cache['clientInfoDatabase'][entry]['client_unique_identifier'] == self.cache['clientDatabase'][cldbid]['client_unique_identifier']:
                    clientInfoDatabaseId = entry
            if entry in self.cache['clientInfoDatabase'].keys():
                self.setPartnerFlag(moreInfo, "Away", self.cache['clientInfoDatabase'][entry]['client_away'])
                self.setPartnerDetail(moreInfo, "Away message", self.cache['clientInfoDatabase'][entry]['client_away_message'])
                self.setPartnerDetail(moreInfo, "Channel Group", self.cache['serverInfo']['channelGroupList'][self.cache['clientInfoDatabase'][entry]['client_channel_group_id']]['name'])
                self.setPartnerFlag(moreInfo, "Output muted", self.cache['clientInfoDatabase'][entry]['client_output_muted'])
                self.setPartnerFlag(moreInfo, "Output only muted", self.cache['clientInfoDatabase'][entry]['client_outputonly_muted'])
                self.setPartnerFlag(moreInfo, "Input muted", self.cache['clientInfoDatabase'][entry]['client_input_muted'])
                self.setPartnerFlag(moreInfo, "Is channelcommander", self.cache['clientInfoDatabase'][entry]['client_is_channel_commander'])
                self.setPartnerFlag(moreInfo, "Is recording", self.cache['clientInfoDatabase'][entry]['client_is_recording'])
                self.setPartnerFlag(moreInfo, "Is talker", self.cache['clientInfoDatabase'][entry]['client_is_talker'])

            tmpCldbid = cldbid
            if cldbid not in self.cache['clientInfoDatabase'].keys():
                for entry in self.cache['clientInfoDatabase'].keys():
                    if self.cache['clientInfoDatabase'][entry]['client_unique_identifier'] == self.cache['clientDatabase'][cldbid]['client_unique_identifier']:
                        tmpCldbid = entry
    
            if tmpCldbid in self.cache['clientInfoDatabase'].keys():
                self.setPartnerFlag(moreInfo, "Away", self.cache['clientInfoDatabase'][tmpCldbid]['client_away'])
                self.setPartnerDetail(moreInfo, "Away message", self.cache['clientInfoDatabase'][tmpCldbid]['client_away_message'])
                self.setPartnerDetail(moreInfo, "Channel Group", self.cache['serverInfo']['channelGroupList'][self.cache['clientInfoDatabase'][tmpCldbid]['client_channel_group_id']]['name'])
                self.setPartnerFlag(moreInfo, "Output muted", self.cache['clientInfoDatabase'][tmpCldbid]['client_output_muted'])
                self.setPartnerFlag(moreInfo, "Output only muted", self.cache['clientInfoDatabase'][tmpCldbid]['client_outputonly_muted'])
                self.setPartnerFlag(moreInfo, "Input muted", self.cache['clientInfoDatabase'][tmpCldbid]['client_input_muted'])
                self.setPartnerFlag(moreInfo, "Is channelcommander", self.cache['clientInfoDatabase'][tmpCldbid]['client_is_channel_commander'])
                self.setPartnerFlag(moreInfo, "Is recording", self.cache['clientInfoDatabase'][tmpCldbid]['client_is_recording'])
                self.setPartnerFlag(moreInfo, "Is talker", self.cache['clientInfoDatabase'][tmpCldbid]['client_is_talker'])

        except KeyError as e:
            self.log.info("Missing client information to show in details: %s" % e)
            pass
        return moreInfo

    def getLinkHtml(self):
        self.log.debug("Show linkHtml %s" % self.name)
        self.getCache('onlineClients')
        
        htmlFields = {}
        if not self.getSessionValue(self.linkIdName) and not self.getSessionValue('doLinkKey'):
            htmlFields['action'] = url_for('network_link')
            htmlFields['dropdown'] = [{ 'name': '', 'value': "" }]
            currentLinks = []
            for link in self.getNetworkLinks():
                currentLinks.append(link['network_data'])
            for cldbid in self.cache['onlineClients'].keys():
                if cldbid not in currentLinks:
                    try:
                        htmlFields['dropdown'].append({ 'name': self.cache['onlineClients'][cldbid]['client_nickname'].decode('utf-8'), 'value': cldbid })
                    except UnicodeEncodeError:
                        htmlFields['dropdown'].append({ 'name': self.cache['onlineClients'][cldbid]['client_nickname'], 'value': cldbid })
            if not len(htmlFields['dropdown']):
                htmlFields = {}
                htmlFields['text'] = "Please connect to the Teamspeak Server"
        return htmlFields

    def doLink(self, userId):
        if not userId:
            return "Please choose a user."
        self.getCache('onlineClients')
        self.connect()
        self.log.debug("[%s] Link user %s to network %s" % (self.handle, userId, self.name))
        self.setSessionValue('doLinkKey', "%06d" % (random.randint(1, 999999)))
        self.setSessionValue(self.linkIdName, userId)
        message = "Your MMOfriends key is: %s" % self.getSessionValue('doLinkKey')
        try:
            ret = self.server.clientpoke(self.cache['onlineClients'][userId]['clid'], message)
        except EOFError as e:
            self.log.warning("[%s] Unable to link network because: %s" % (self.handle, e))
            return "An error occured. Please try again. Sorry"
        self.log.info("[%s] Linking with code: %s" % (self.handle, self.getSessionValue('doLinkKey')))
        return "Please enter the number you recieved via teamspeak chat."

    def clearLinkRequest(self):
        self.log.debug("[%s] Clearing link requst" % (self.handle))
        self.delSessionValue('doLinkKey')
        self.delSessionValue(self.linkIdName)

    def finalizeLink(self, userKey):
        self.log.info("[%s] Finalize user link to network %s" % (self.handle, self.name))
        if self.getSessionValue('doLinkKey') == userKey:
            cldbid = self.getSessionValue(self.linkIdName)
            self.delSessionValue('doLinkKey')
            self.saveLink(cldbid)
            self.connect()
            self.fetchUserDetatilsByCldbid(cldbid, True)
            self.getCache('clientDatabase')
            for group in self.cache['clientDatabase'][cldbid]['groups']:
                if int(group['sgid']) in self.config['guestGroups']:
                    self.sendCommand('servergroupaddclient sgid=%s cldbid=%s' % (self.config['memberGroupId'], cldbid))
                    # self.sendCommand('servergroupdelclient sgid=%s cldbid=%s' % (group['sgid'], cldbid))
            self.fetchUserDetatilsByCldbid(cldbid, True)

            return True
        else:
            self.log.warning("[%s] Unable to finalize user link to network %s because no userKey is submitted." % (self.handle, self.name))
            return False

    def admin(self):
        self.log.debug("Admin: Returning client database")
        return "noting"

    def findPartners(self):
        self.log.debug("Searching for new partners to play with")
        return self.getPartners(onlineOnly=True)

    def devTest(self):
        # self.log.error("Registring worker!")
        # self.registerWorker(self.cacheAvailableClients, 0)
        try:
            return "cldbid: %s" % self.getSessionValue(self.linkIdName)
        except Exception as e:
            return "%s" % e

    def prepareForFirstRequest(self):
        self.log.info("[%s] Running prepareForFirstRequest." % self.handle)
        # This is done to set "More Info"
        self.connect()

    # helper methods
    def connect(self, logger = None):
        if not logger:
            logger = self.log
        self.getCache('serverInfo')
        if not self.connected:
            logger.info("[%s] Connecting to TS3 server %s:%s/%s" % (self.handle, self.config['ip'], self.config['port'], self.config['serverid']))

            try:
                self.server = ts3.TS3Server(self.config['ip'], self.config['port'], self.config['serverid'])
                if not self.server.is_connected():
                    logger.warning("[%s] TS3 Server connection error: Unable to open connection, probably banned!" % (self.handle))
                    return False
                    
                if not self.server.login(self.config['username'], self.config['password']):
                    logger.warning("[%s] TS3 Server connection error: Unable to login" % (self.handle))
                    return False

            except ts3.ConnectionError as e:
                logger.warning("[%s] TS3 Server connection error: %s" % (self.handle, e))
                return False
            except EOFError as e:
                logger.warning("[%s] TS3 Server connection error: %s" % (self.handle, e))
                return False

            result = self.sendCommand('serverinfo')
            for serverData in result.data:
                if int(serverData['virtualserver_id']) == self.config['serverid']:
                    self.cache['serverInfo']['serverInfo'] = serverData
                    self.description = serverData['virtualserver_name']
                    logger.info("[%s] Connected to: %s" % (self.handle, self.description))
                    self.setCache('serverInfo')

            self.connected = True
        return True

    def sendCommand(self, command):
        self.log.debug("[%s] Sending command: %s" % (self.handle, command))
        try:
            return self.server.send_command(command)
        except EOFError as e:
            self.connected = False
            self.log.warning("[%s] TS3 Server connection error - EOFError: %s" % (self.handle, e))
            return False
        except KeyError as e:
            self.connected = False
            self.log.warning("[%s] TS3 Server connection error - KeyError: %s" % (self.handle, e))
            return False
        except Exception as e:
            self.connected = False
            self.log.warning("[%s] TS3 Server connection error - Exception: %s" % (self.handle, e))
            return False

    def fetchUserDetatilsByCldbid(self, cldbid, force = False, logger = None):
        if not logger:
            logger = self.log

        updateUserDetails = False
        self.getCache('clientDatabase')
        self.getCache('onlineClients')

        try:
            if self.cache['clientDatabase'][cldbid]['lastUpdateUserDetails'] < (time.time() - self.config['updateLock'] - random.randint(1, 30)):
                updateUserDetails = True
        except KeyError:
            updateUserDetails = True

        if force:
            updateUserDetails = True

        if updateUserDetails:
            self.cache['clientDatabase'][cldbid] = {}
            self.cache['clientDatabase'][cldbid]['cldbid'] = cldbid

            logger.debug("[%s] Fetching client db info for cldbid: %s" % (self.handle, cldbid))
            response = self.sendCommand('clientdbinfo cldbid=%s' % cldbid)
            if response:
                self.cache['clientDatabase'][cldbid] = response.data[0]
                self.cache['clientDatabase'][cldbid]['lastUpdateUserDetails'] = time.time()

            self.cache['clientDatabase'][cldbid]['groups'] = {}
            logger.debug("[%s] Fetching user group details for cldbid: %s" % (self.handle, cldbid))
            response = self.sendCommand('servergroupsbyclientid cldbid=%s' % cldbid)
            if response:
                self.cache['clientDatabase'][cldbid]['groups'] = response.data
                self.cache['clientDatabase'][cldbid]['lastUpdateUserGroupDetails'] = time.time()

            if cldbid in self.cache['onlineClients']:
                clid = self.cache['onlineClients'][cldbid]['clid']
                self.getCache('clientInfoDatabase')
                self.cache['clientInfoDatabase'][cldbid] = {}
                logger.debug("[%s] Fetching client info for clid: %s" % (self.handle, clid))
                response = self.sendCommand('clientinfo clid=%s' % clid)
                if response:
                    self.cache['clientInfoDatabase'][cldbid] = response.data[0]
                    logger.debug("[%s] Updated infor for cldbid: %s" % (self.handle, clid))
                    self.setCache('clientInfoDatabase')

        else:
            logger.debug("[%s] Not fetching user details for cldbid: %s" % (self.handle, cldbid))

        self.setCache('clientDatabase')

    # file transfer methods
    def cacheFile(self, name, cid = 0, cpw = "", seekpos = 0):
        filename = name
        if name[0] == "/":
            filename = name[1:]
        outputFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../static/cache', filename)

        if os.path.isfile(outputFilePath):
            self.log.debug("[%s] Not fetching %s. Already cached." % (self.handle, name))
            return False
        else:
            self.log.debug("[%s] File save path: %s" % (self.handle, outputFilePath))

        if seekpos == 0:
            self.log.debug("[%s] Requesting file name: %s" % (self.handle, name))
            self.clientftfid += 1

        if self.connect():
            response = self.sendCommand("ftinitdownload clientftfid=%s name=%s cid=%s cpw=%s seekpos=%s" % (self.clientftfid, name, cid, cpw, seekpos))
            if not response:
                self.log.warning("[%s] Recieved no response to download file %s from TS3 Server" % (self.handle, name))
                return False
            fileinfo = response.data[0]

            try:
                self.log.warning("[%s] File request error: %s (%s)" % (self.handle, fileinfo['msg'], name))
                return False
            except KeyError:
                pass

            try:
                fileinfo['port'], fileinfo['size'], fileinfo['ftkey']
            except KeyError as e:
                self.log.warning("[%s] Unable to fetch %s (%s | %s)" % (self.handle, name, e, response.data))
                return False

            # possible bug
            # self.log.debug("[%s] Recieved informations to fetch file %s, Port: %s, Size: %s" % (self.handle, name, fileinfo['port'], fileinfo['size']))
            # self.log.info("[%s] Saving file to static/cache/%s" % (self.handle, filename))
            read_size = seekpos
            block_size = 4096
            try:
                output_file = open(outputFilePath,'ab')
            except IOError as e:
                self.log.warning("[%s] Unable to open outputfile %s: %s" % (self.handle, outputFilePath, e))
                return False
            try:
                sock = socket.create_connection((self.config['ip'], fileinfo['port']))
                sock.sendall(fileinfo['ftkey'])
                while True:
                    data = sock.recv(block_size)
                    output_file.write(data)
                    read_size += len(data)
                    if not data:
                        sock.close()
                        break
            except OSError as err:
                self.log.error("[%s] Filetransfer error: %s" % (self.handle, err))
  
            output_file.close()
            sock.close()

            if read_size < int(fileinfo['size']):
                self.log.warning("[%s] Filetransfer incomplete (%s/%s bytes) for ftkey: %s" % (self.handle, read_size, fileinfo['size'], fileinfo['ftkey']))
                return False
            else:
                return True
        self.log.warning("[%s] No connection to TS3 Server" % (self.handle))
        return False

    def cacheIcon(self, iconId, cid = 0):
        if int(iconId) == 0:
            self.log.debug("[%s] No icon available because IconID is 0" % (self.handle))
            return True
        else:
            return self.cacheFile("/icon_%s" % int(iconId), cid)

    def cacheFlagAvatar(self, flagAvatarId, cid = 0):
        # https://docs.planetteamspeak.com/ts3/php/framework/_client_8php_source.html
        # https://docs.planetteamspeak.com/ts3/php/framework/class_team_speak3___node___client.html#a1c1b0fa71731df7ac3d4098b046938c7
        return self.cacheFile("avatar_%s" % flagAvatarId, cid)

    def cacheServerIcon(self, iconId):
        self.cacheIcon((int(iconId) + 4294967296))
