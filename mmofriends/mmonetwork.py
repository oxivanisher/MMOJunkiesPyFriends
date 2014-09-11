#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
import socket
import os

from mmoutils import *
from mmofriends import db

try:
    import ts3
except ImportError:
    print "Please install PyTS3"
    import sys
    sys.exit(2)

# base classes
class MMONetworkConfig(object):

    def __init__(self, config = {}, shortName = None, longName = None):
        self.log = logging.getLogger(__name__ + ".cfg")
        self.longName = longName
        self.shortName = shortName
        self.log.debug("Initializing MMONetwork config: %s" % self.longName)
        self.config = config[shortName]

    def get(self):
        self.log.debug("Returning MMONetwork config: %s" % self.longName)
        return self.config

class MMONetworkProduct(object):

    def __init__(self, name):
        self.log = logging.getLogger(__name__)
        self.log.debug("Initializing MMONetwork product %s" % name)
        self.name = name
        self.fields = []

    def addField(self, name, comment = "", fieldType = str):
        self.log.debug("Add a field with name, comment and fieldType")
        self.fields.append((name, fieldType))

class MMONetwork(object):

    def __init__(self, config, myId):
        # loading config
        self.config = config.get()

        # setting variables
        self.longName = config.longName
        self.shortName = config.shortName
        self.icon = self.config['icon']

        self.log = logging.getLogger(__name__ + "." + self.shortName.lower())
        self.log.debug("Initializing MMONetwork: %s" % self.longName)

        self.comment = "Unset"
        self.description = "Unset"
        self.moreInfo = 'NoMoreInfo'
        self.lastRefreshDate = 0
        self.hidden = False
        self.myId = myId

        self.products = self.getProducts() #Fields: Name, Type (realm, char, comment)

        self.log.info("Initialized network: %s (%s)" % (self.longName, self.shortName))

    def refresh(self):
        self.log.debug("Refresh data from source")
        pass

    def link(self):
        self.log.debug("Link user to network %s" % self.longName)
        pass

    def unlink(self):
        self.log.debug("Unlink network %s" % self.longName)
        pass

    def listPartners(self, user):
        self.log.debug("List all partners for given user")
        return {'id': 1234,
                'nick': self.onlineClients[cldbid]['client_nickname'].decode('utf-8'),
                'moreInfo': ', '.join(moreInfo),
                'networkText': channelName,
                'networkImgs': [{
                    'type': 'network',
                    'name': self.myId,
                    'title': self.longName
                },{
                    'type': 'cache',
                    'name': 'icon_' + str(int(self.serverInfo['virtualserver_icon_id']) + 4294967296),
                    'title': ', '.join(moreInfo)
                },{
                    'type': 'cache',
                    'name': 'icon_' + channelIcon,
                    'title': channelName
                }],
                'friendImgs': [{
                    'type': 'cache',
                    'name': userGroupIcon,
                    'title': userGroupName
                },{
                    'type': 'cache',
                    'name': userGroupIcon,
                    'title': userGroupName
                }]
            }

    def getProducts(self):
        self.log.debug("MMONetwork %s: Fetching products" % self.shortName)
        pass

    def setNetworkMoreInfo(self, moreInfo):
        self.moreInfo = moreInfo

    def setNetworkComment(self, comment):
        self.comment = comment

# ts3 classes
class TS3Network(MMONetwork):

    # class overwrites
    def __init__(self, config, myId):
        super(TS3Network, self).__init__(config, myId)

        self.description = "Team Speak 3 is like skype for gamers."

        self.onlineClients = {}
        self.clientDatabase = {}
        self.clientInfoDatabase = {}
        self.serverInfo = {}
        self.channelList = []
        self.groupList = []
        self.server = None

        self.connected = False

        self.lastOnlineRefreshDate = 0
        self.clientftfid = 0

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
            for client in response.data:
                clients[client['clid']] = client

            for client in clients.keys():
                # ignoring console users
                if int(clients[client]['client_type']) != 1:
                    self.onlineClients[clients[client]['client_database_id']] = clients[client]

            self.log.info("Found %s online clients" % len(self.onlineClients))
        return True

    def listPartners(self):
        if self.refresh():
            ret = []
            for cldbid in self.onlineClients.keys():
                # Get user details
                self.fetchUserDetatilsByCldbid(cldbid)
                self.fetchUserInfo(self.onlineClients[cldbid]['clid'], cldbid)

                # self.clientDatabase[cldbid]

                moreInfo = []
                try:
                    moreInfo.append("Last Conn: %s" % timestampToString(self.clientDatabase[cldbid]['client_lastconnected']))
                    moreInfo.append("Total Conn: %s" % self.clientDatabase[cldbid]['client_totalconnections'])
                    moreInfo.append("Created: %s" % timestampToString(self.clientDatabase[cldbid]['client_created']))
                    moreInfo.append("Description: %s" % self.clientDatabase[cldbid]['client_created'])

                    userGroups = []
                    userGroupIcon = 0
                    userGroupName = ""
                    for group in self.clientDatabase[cldbid]['groups']:
                        for g in self.groupList:
                            if g['sgid'] == group['sgid']:
                                userGroupIcon = 'icon_' + g['iconid']
                                self.cacheIcon(g['iconid'])
                        userGroups.append(group['name'])
                        userGroupName = group['name']
                    moreInfo.append("Groups: %s" % ', '.join(userGroups))

                    # if admin
                    moreInfo.append("Last IP: %s" % self.clientDatabase[cldbid]['client_lastip'])
                    # {'client_total_bytes_downloaded': '366040', 'client_month_bytes_downloaded': '39211', 'client_database_id': '644', 'client_icon_id': '0', 'client_base64HashClientUID': 'niljclpbalpldpbecbdiemcdncjlglfbilemoloi', 'client_month_bytes_uploaded': '0', 'client_flag_avatar': None, 'client_nickname': 'EvilM0nkey', 'client_description': None, 'client_total_bytes_uploaded': '0'}
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
                                'name': self.myId,
                                'title': self.longName
                            },{
                                'type': 'cache',
                                'name': 'icon_' + str(int(self.serverInfo['virtualserver_icon_id']) + 4294967296),
                                'title': ', '.join(moreInfo)
                            }]
                if int(channelIcon) != 0:
                    networkImgs.append({'type': 'cache', 'name': 'icon_' + channelIcon, 'title': channelName })

                friendImgs = []
                if userGroupIcon != 'icon_0':
                    friendImgs.append({ 'type': 'cache', 'name': userGroupIcon, 'title': userGroupName })

# {
#                                 'type': 'cache',
#                                 'name': userGroupIcon,
#                                 'title': userGroupName
#                             }

                ret.append({'id': 1234,
                            'nick': self.onlineClients[cldbid]['client_nickname'].decode('utf-8'),
                            'moreInfo': ', '.join(moreInfo),
                            'networkText': channelName,
                            'networkImgs': networkImgs,
                            'friendImgs': friendImgs
                    })
            # info:
            # client_servergroups
            # self.channelList = []
            # self.groupList = []
            # print self.channelList[client_servergroups]

            return (True, ret)
        else:
            return (False, "Unable to connect to TS3 server.")

    # helper methods
    def connect(self):
        if not self.connected:
            self.log.info("Connecting to TS3 server")

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
            self.groupList = []
            result = self.sendCommand('servergrouplist')
            self.groupList = result.data

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
            if self.clientDatabase[cldbid]['lastUpdateUserDetails'] < (time.time() - self.config['updateLock']):
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
            if self.clientDatabase[cldbid]['lastUpdateUserGroupDetails'] < (time.time() - self.config['updateLock']):
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
        self.log.setLevel(logging.INFO)
        updateUserInfo = False
        try:
            if self.clientInfoDatabase[cldbid]['lastUpdateUserInfo'] < (time.time() - self.config['updateLock']):
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

    def test(self):
        # result = "blah"
        result = self.sendCommand('clientinfo clid=2')
        return result.data

    # file transfer methods
    def cacheFile(self, name, cid, cpw = "", seekpos = 0):
        self.log.setLevel(logging.INFO)
        filename = name
        if name[0] == "/":
            filename = name[1:]
        outputFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/cache', filename)

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
        self.log.setLevel(logging.INFO)
        if int(iconId) == 0:
            self.log.debug("No icon available because IconID is 0")
            return True
        else:
            return self.cacheFile("/icon_%s" % int(iconId), cid)

    def cacheFiles(self):
        self.log.setLevel(logging.INFO)
        if self.connect():
            self.log.info("Caching server icon")
            self.cacheServerIcon(self.serverInfo['virtualserver_icon_id'])

            self.log.info("Caching channel icons")
            for channel in self.channelList:
                self.log.debug("Caching file for channel: %s" % channel['channel_name'])
                self.cacheIcon(channel['channel_icon_id'])
                    # break

            self.log.info("Caching client icons")
            for client in self.onlineClients.keys():
                self.log.debug("Caching file for client: %s" % self.onlineClients[client]['client_nickname'])
                self.cacheIcon(self.onlineClients[client]['client_icon_id'])
                    # break

            self.log.info("Caching group icons")
            for group in self.groupList:
                self.log.debug("Caching file for group: %s" % group['name'])
                if int(group['iconid']):
                    self.cacheIcon(group['iconid'])
                        # break

    def cacheServerIcon(self, iconId):
        self.cacheIcon((int(iconId) + 4294967296))
