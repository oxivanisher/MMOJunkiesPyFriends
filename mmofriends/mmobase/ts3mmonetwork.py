#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import socket
import os
import random

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

        self.description = "Team Speak 3 is like skype for gamers."

        self.onlineClients = {}
        self.clientDatabase = {}
        self.clientInfoDatabase = {}
        self.serverInfo = {}
        self.channelList = []
        self.channelGroupList = {}
        self.groupList = {}
        self.server = None

        self.connected = False

        self.lastOnlineRefreshDate = 0
        self.clientftfid = 0

        self.onlineClients = {}
        self.clientDatabase = {}
        self.clientInfoDatabase = {}

    def refresh(self):
        if not self.connect():
            self.log.warning("Not refreshing online clients because we are disconnected")
            return False

        if self.lastOnlineRefreshDate > (time.time() - self.config['updateOnlineLock']):
            self.log.debug("Not refreshing online clients")
        else:
            self.lastOnlineRefreshDate = time.time()
            self.log.debug("Fetching online clients")
            response = self.sendCommand("clientlist -icon")
            self.onlineClients = {}
            clients = {}
            try:
                for client in response.data:
                    clients[client['clid']] = client
            except AttributeError:
                return True

            for client in clients.keys():
                # ignoring console users
                if int(clients[client]['client_type']) != 1:
                    self.onlineClients[clients[client]['client_database_id']] = clients[client]

            self.log.info("Found %s online client(s)" % len(self.onlineClients))
        return True

    def getPartners(self):
        if self.refresh():
            ret = []
            for cldbid in self.onlineClients.keys():
                # Refresh user details
                self.fetchUserDetatilsByCldbid(cldbid)
                self.fetchUserInfo(self.onlineClients[cldbid]['clid'], cldbid)

                try:
                    userGroups = []
                    userGroupIcon = 0
                    userGroupName = ""
                    for group in self.clientDatabase[cldbid]['groups']:
                        for g in self.groupList.keys():
                            if self.groupList[g]['sgid'] == group['sgid']:
                                userGroupIcon = 'icon_' + self.groupList[g]['iconid']
                                self.cacheIcon(self.groupList[g]['iconid'])
                        userGroups.append(group['name'])
                        userGroupName = group['name']
                except KeyError:
                    pass

                # Get channel details
                channelName = "Unknown"
                channelIcon = None
                try:
                    for channel in self.channelList:
                        if channel['cid'] == self.onlineClients[cldbid]['cid']:
                            channelName = channel['channel_name'].decode('utf-8')
                            channelIcon = channel['channel_icon_id']
                            self.cacheIcon(channelIcon)
                except IndexError:
                    pass

                networkImgs = [{
                                'type': 'network',
                                'name': self.handle,
                                'title': self.name
                            },{
                                'type': 'cache',
                                'name': 'icon_' + str(int(self.serverInfo['virtualserver_icon_id']) + 4294967296),
                                'title': channelName
                            }]
                if int(channelIcon) != 0:
                    networkImgs.append({'type': 'cache', 'name': 'icon_' + channelIcon, 'title': channelName })

                friendImgs = []
                if self.clientInfoDatabase[cldbid]['client_country']:
                    friendImgs.append({ 'type': 'flag',
                                        'name': self.clientInfoDatabase[cldbid]['client_country'].lower(),
                                        'title': self.clientInfoDatabase[cldbid]['client_country'] })

                if userGroupIcon != 'icon_0':
                    friendImgs.append({ 'type': 'cache', 'name': userGroupIcon, 'title': userGroupName })

                cgid = self.clientInfoDatabase[cldbid]['client_channel_group_id']
                if int(self.channelGroupList[cgid]['iconid']) != 0:
                    friendImgs.append({ 'type': 'cache', 'name': 'icon_' + self.channelGroupList[cgid]['iconid'], 'title': self.channelGroupList[cgid]['name'] })

                ret.append({'id': cldbid,
                            'nick': self.onlineClients[cldbid]['client_nickname'].decode('utf-8'),
                            'networkText': channelName,
                            'networkId': self.handle,
                            'networkImgs': networkImgs,
                            'friendImgs': friendImgs
                    })

            return (True, ret)
        else:
            return (False, "Unable to connect to TS3 server.")

    def getPartnerDetails(self, cldbid):
        moreInfo = {}
        if self.refresh():
            # Refresh user details
            self.fetchUserDetatilsByCldbid(cldbid)
            self.fetchUserInfo(self.onlineClients[cldbid]['clid'], cldbid)

            try:
                #fetch avatar
                if self.clientDatabase[cldbid]['client_flag_avatar']:
                    avatar = "/avatar_%s" % self.clientDatabase[cldbid]['client_base64HashClientUID']
                    self.cacheFile(avatar)
                    self.setPartnerAvatar(moreInfo, avatar)

                self.setPartnerDetail(moreInfo, "Description", self.clientDatabase[cldbid]['client_description'])
                self.setPartnerFlag(moreInfo, "Away", self.clientInfoDatabase[cldbid]['client_away'])
                self.setPartnerDetail(moreInfo, "Away message", self.clientInfoDatabase[cldbid]['client_away_message'])
                self.setPartnerDetail(moreInfo, "Created", timestampToString(self.clientDatabase[cldbid]['client_created']))
                self.setPartnerDetail(moreInfo, "Last Connection", timestampToString(self.clientDatabase[cldbid]['client_lastconnected']))
                self.setPartnerDetail(moreInfo, "Total Connections", self.clientDatabase[cldbid]['client_totalconnections'])

                userGroups = []
                userGroupIcon = 0
                userGroupName = ""
                for group in self.clientDatabase[cldbid]['groups']:
                    for g in self.groupList.keys():
                        if self.groupList[g]['sgid'] == group['sgid']:
                            userGroupIcon = 'icon_' + self.groupList[g]['iconid']
                            self.cacheIcon(self.groupList[g]['iconid'])
                    userGroups.append(group['name'])
                    userGroupName = group['name']
                self.setPartnerDetail(moreInfo, "Server Groups", ', '.join(userGroups))
                self.setPartnerDetail(moreInfo, "Channel Group", self.channelGroupList[self.clientInfoDatabase[cldbid]['client_channel_group_id']]['name'])

                if self.session.get('admin'):
                    self.setPartnerDetail(moreInfo, "Last IP", self.clientDatabase[cldbid]['client_lastip'])
                    self.setPartnerDetail(moreInfo, "Bytes uploaded month", bytes2human(self.clientDatabase[cldbid]['client_month_bytes_uploaded']))
                    self.setPartnerDetail(moreInfo, "Bytes downloaded month", bytes2human(self.clientDatabase[cldbid]['client_month_bytes_downloaded']))
                    self.setPartnerDetail(moreInfo, "Bytes uploaded total", bytes2human(self.clientDatabase[cldbid]['client_total_bytes_uploaded']))
                    self.setPartnerDetail(moreInfo, "Bytes downloaded total", bytes2human(self.clientDatabase[cldbid]['client_total_bytes_downloaded']))

                self.setPartnerFlag(moreInfo, "Output muted", self.clientInfoDatabase[cldbid]['client_output_muted'])
                self.setPartnerFlag(moreInfo, "Output only muted", self.clientInfoDatabase[cldbid]['client_outputonly_muted'])
                self.setPartnerFlag(moreInfo, "Input muted", self.clientInfoDatabase[cldbid]['client_input_muted'])
                self.setPartnerFlag(moreInfo, "Is channelcommander", self.clientInfoDatabase[cldbid]['client_is_channel_commander'])
                self.setPartnerFlag(moreInfo, "Is recording", self.clientInfoDatabase[cldbid]['client_is_recording'])
                self.setPartnerFlag(moreInfo, "Is talker", self.clientInfoDatabase[cldbid]['client_is_talker'])

            except KeyError:
                pass
        return moreInfo

    def getLinkHtml(self):
        self.log.debug("Show linkHtml %s" % self.name)
        self.refresh()
        
        htmlFields = {}
        htmlFields['dropdown'] = []
        currentLinks = []
        for link in self.getNetworkLinks():
            currentLinks.append(link['network_data'])
        for cldbid in self.onlineClients.keys():
            if cldbid not in currentLinks:
                htmlFields['dropdown'].append({ 'name': self.onlineClients[cldbid]['client_nickname'].decode('utf-8'), 'value': cldbid })
        return htmlFields

    def doLink(self, userId):
        self.log.debug("Link user %s to network %s" % (userId, self.name))
        self.refresh()
        self.setSessionValue('doLinkKey', "%06d" % (random.randint(1, 999999)))
        self.setSessionValue('cldbid', userId)
        message = "Your MMOfriends key is: %s" % self.getSessionValue('doLinkKey')
        self.server.clientpoke(self.onlineClients[userId]['clid'], message)
        return "Please enter the number you recieved via teamspeak"

    def finalizeLink(self, userKey):
        self.log.debug("Finalize user link to network %s" % self.name)
        self.refresh()
        if self.getSessionValue('doLinkKey') == userKey:
            self.saveLink(self.getSessionValue('cldbid'))
            return True
        else:
            return False

    def loadLinks(self, userId):
        self.log.debug("Loading user links for userId %s" % userId)
        self.setSessionValue('userId', None)
        for link in self.getNetworkLinks(userId):
            self.setSessionValue('cldbid', link['network_data'])

    # helper methods
    def connect(self):
        if not self.connected:
            self.log.debug("Connecting to TS3 server")

            try:
                self.server = ts3.TS3Server(self.config['ip'], self.config['port'], self.config['serverid'])
                if not self.server.is_connected():
                    self.log.warning("TS3 Server connection error: Unable to open connection, probably banned!")
                    return False
                    
                if not self.server.login(self.config['username'], self.config['password']):
                    self.log.warning("TS3 Server connection error: Unable to login")
                    return False

            except ts3.ConnectionError as e:
                self.log.warning("TS3 Server connection error: %s" % e)
                return False
            except EOFError as e:
                self.log.warning("TS3 Server connection error: %s" % e)
                return False

            result = self.sendCommand('serverinfo')
            for serverData in result.data:
                if int(serverData['virtualserver_id']) == self.config['serverid']:
                    self.serverInfo = serverData
                    self.setNetworkMoreInfo(serverData['virtualserver_name'])
                    self.log.info("Connected to: %s" % self.moreInfo)

            self.connected = True

            # fetching channels
            self.log.debug("Fetching channels")
            self.channelList = []
            result = self.sendCommand('channellist -icon')
            for channel in result.data:
                try:
                    if int(channel['channel_icon_id']) < 0:
                        channel['channel_icon_id'] = str(int(channel['channel_icon_id']) + 4294967296)
                except KeyError:
                    channel['channel_icon_id'] = 0
                self.channelList.append(channel)

            # fetching groups
            self.log.debug("Fetching groups")
            self.groupList = {}
            result = self.sendCommand('servergrouplist')
            for group in result.data:
                self.groupList[group['sgid']] = group

            # fetching channel groups
            self.log.debug("Fetching channel groups")
            self.channelGroupList = {}
            result = self.sendCommand('channelgrouplist')
            for group in result.data:
                self.channelGroupList[group['cgid']] = group

        return True

    def sendCommand(self, command):
        self.log.debug("Sending command: %s" % command)
        try:
            return self.server.send_command(command)
        except EOFError as e:
            self.connected = False
            self.log.warning("TS3 Server connection error - EOFError: %s" % e)
            return False
        except KeyError as e:
            self.connected = False
            self.log.warning("TS3 Server connection error - KeyError: %s" % e)
            return False

    def fetchUserDetatilsByCldbid(self, cldbid):
        updateUserDetails = False
        try:
            if self.clientDatabase[cldbid]['lastUpdateUserDetails'] < (time.time() - self.config['updateLock'] - random.randint(1, 10)):
                updateUserDetails = True
        except KeyError:
            updateUserDetails = True

        if updateUserDetails:
            self.clientDatabase[cldbid] = {}
            self.log.debug("Fetching client db info for cldbid: %s" % cldbid)
            response = self.sendCommand('clientdbinfo cldbid=%s' % cldbid)
            if response:
                self.clientDatabase[cldbid] = response.data[0]
                self.clientDatabase[cldbid]['lastUpdateUserDetails'] = time.time()

        else:
            self.log.debug("Not fetching user details for cldbid: %s" % cldbid)


        updateUserGroupDetails = False
        try:
            if self.clientDatabase[cldbid]['lastUpdateUserGroupDetails'] < (time.time() - self.config['updateLock'] - random.randint(1, 10)):
                updateUserGroupDetails = True
        except KeyError:
            updateUserGroupDetails = True

        if updateUserGroupDetails:
            self.clientDatabase[cldbid]['groups'] = {}
            self.log.debug("Fetching user group details for cldbid: %s" % cldbid)
            response = self.sendCommand('servergroupsbyclientid cldbid=%s' % cldbid)
            if response:
                self.clientDatabase[cldbid]['groups'] = response.data
                self.clientDatabase[cldbid]['lastUpdateUserGroupDetails'] = time.time()

        else:
            self.log.debug("Not fetching user group details for cldbid: %s" % cldbid)

    def fetchUserInfo(self, clid, cldbid):
        updateUserInfo = False
        try:
            if self.clientInfoDatabase[cldbid]['lastUpdateUserInfo'] < (time.time() - self.config['updateLock'] - random.randint(1, 10)):
                updateUserInfo = True
        except KeyError:
            updateUserInfo = True

        if updateUserInfo:
            self.clientInfoDatabase[cldbid] = {}
            self.log.debug("Fetching client info for clid: %s" % clid)
            response = self.sendCommand('clientinfo clid=%s' % clid)
            if response:
                self.clientInfoDatabase[cldbid] = response.data[0]
                self.clientInfoDatabase[cldbid]['lastUpdateUserInfo'] = time.time()

        else:
            self.log.debug("Not fetching user details for cldbid: %s" % cldbid)

    def devTest(self):
        try:
            return "cldbid: %s" % self.getSessionValue('cldbid')
        except Exception as e:
            return "%s" % e

    def cacheAvailableClients(self):
        clientNum = 0
        clientTot = int(self.sendCommand('clientdblist -count').data[0]['count'])
        allClients = []
        while clientNum < clientTot:
            self.log.debug("Fetching all clients, starting at: %s" % clientNum)
            newClients = self.sendCommand('clientdblist start=%s' % clientNum).data
            clientNum += len(newClients)
            allClients += newClients
        for client in allClients:
            self.clientDatabase[client['cldbid']] = client
        self.log.info("Fetched all client database. %s clients in total." % clientNum)
        # return "all clients fetched: %s" % len(allClients)

    # file transfer methods
    def cacheFile(self, name, cid = 0, cpw = "", seekpos = 0):
        filename = name
        if name[0] == "/":
            filename = name[1:]
        outputFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../static/cache', filename)

        if os.path.isfile(outputFilePath):
            self.log.debug("Not fetching %s. Already cached." % (name))
            return False
        else:
            self.log.debug("File save path: %s" % outputFilePath)

        if seekpos == 0:
            self.log.debug("Requesting file name: %s" % name)
            self.clientftfid += 1

        if self.connect():
            response = self.sendCommand("ftinitdownload clientftfid=%s name=%s cid=%s cpw=%s seekpos=%s" % (self.clientftfid, name, cid, cpw, seekpos))
            fileinfo = response.data[0]

            try:
                self.log.warning("File request error: %s" % fileinfo['msg'])
                return False
            except KeyError:
                pass

            try:
                fileinfo['port'], fileinfo['size'], fileinfo['ftkey']
            except KeyError:
                self.log.warning("No response recieved")
                return False

            self.log.debug("Recieved informations to fetch file %s, Port: %s, Size: %s" % (name, fileinfo['port'], fileinfo['size']))
            self.log.info("Saving file to static/cache/%s" % filename)
            read_size = seekpos
            block_size = 4096
            try:
                output_file = open(outputFilePath,'ab')
            except IOError as e:
                self.log.warning("Unable to open outputfile %s: %s" % (outputFilePath, e))
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
                self.log.error("Filetransfer error: %s" % err)
  
            output_file.close()
            sock.close()

            if read_size < int(fileinfo['size']):
                self.log.warning("Filetransfer incomplete (%s/%s bytes) for ftkey: %s" % (read_size, fileinfo['size'], fileinfo['ftkey']))
                return False
            else:
                return True
        self.log.warning("No connection to TS3 Server")
        return False

    def cacheIcon(self, iconId, cid = 0):
        if int(iconId) == 0:
            self.log.debug("No icon available because IconID is 0")
            return True
        else:
            return self.cacheFile("/icon_%s" % int(iconId), cid)

    def cacheFlagAvatar(self, flagAvatarId, cid = 0):
        # https://docs.planetteamspeak.com/ts3/php/framework/_client_8php_source.html
        # https://docs.planetteamspeak.com/ts3/php/framework/class_team_speak3___node___client.html#a1c1b0fa71731df7ac3d4098b046938c7
        return self.cacheFile("avatar_%s" % flagAvatarId, cid)

    def cacheFiles(self):
        if self.connect():
            self.log.debug("Caching server icon")
            self.cacheServerIcon(self.serverInfo['virtualserver_icon_id'])

            self.log.debug("Caching channel icons")
            for channel in self.channelList:
                self.log.debug("Caching file for channel: %s" % channel['channel_name'])
                self.cacheIcon(channel['channel_icon_id'])

            self.log.debug("Caching client icons")
            for client in self.onlineClients.keys():
                self.log.debug("Caching file for client: %s" % self.onlineClients[client]['client_nickname'])
                self.cacheIcon(self.onlineClients[client]['client_icon_id'])

            self.log.debug("Caching group icons")
            for group in self.groupList.keys():
                self.log.debug("Caching file for group: %s" % self.groupList[group]['name'])
                if int(self.groupList[group]['iconid']):
                    self.cacheIcon(self.groupList[group]['iconid'])

    def cacheServerIcon(self, iconId):
        self.cacheIcon((int(iconId) + 4294967296))

    def admin(self):
        self.log.debug("Admin: Returning client database")
        # add method to refetch all clients from server!
        self.cacheAvailableClients()
        self.cacheFiles()
        self.refresh()
        return self.clientDatabase

    # def saveAtExit(self):
    #     self.loadFromSave()
        # self.onlineClients = {}
        # self.clientDatabase = {}
        # self.clientInfoDatabase = {}
