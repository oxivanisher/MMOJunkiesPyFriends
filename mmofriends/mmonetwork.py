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

    def listPartner(self, user):
        self.log.debug("List all partners for given user")
        pass

    def getProducts(self):
        self.log.debug("MMONetwork %s: Fetching products" % self.shortName)
        pass

    def getNetworkDetails(self):
        return {'networkId': self.myId,
                'networkName': self.longName,
                'networkMoreInfo': self.moreInfo,
                'networkDetailInfo': "networkDetailInfo",
                'id': 1234,
                'nick': "nick",
                'moreInfo': ', '.join(["moreInfo"]),
                'cacheFile1': '',
                'cacheFile2': ''
                }

    def setNetworkMoreInfo(self, moreInfo):
        self.moreInfo = moreInfo

    def setNetworkComment(self, comment):
        self.comment = comment

# ts3 classes
class TS3Network(MMONetwork):

    def __init__(self, config, myId):
        super(TS3Network, self).__init__(config, myId)

        self.description = "Team Speak 3 is like skype for gamers."

        self.onlineClients = {}
        self.clientDatabase = {}
        self.serverInfo = {}
        self.channelList = []
        self.groupList = []
        self.server = None

        self.connected = False

        self.lastOnlineRefreshDate = 0
        self.clientftfid = 0

        self.connect()
        self.refresh()
        self.cacheFiles()

    # helper functions
    def connect(self):
        if not self.connected:
            self.log.info("Connecting to TS3 server")
            try:
                self.server = ts3.TS3Server(self.config['ip'], self.config['port'])
                self.server.login(self.config['username'], self.config['password'])
                self.server.use(self.config['serverid'])

                result = self.server.send_command('serverinfo')

                for serverData in result.data:
                    if int(serverData['virtualserver_id']) == self.config['serverid']:
                        self.serverInfo = serverData
                        self.setNetworkMoreInfo(serverData['virtualserver_name'])
                        self.log.info("Connected to: %s" % self.moreInfo)

                self.connected = True
            except ts3.ConnectionError as e:
                self.connected = False
                self.log.warning("TS3 Server connection error: %s" % e)
                return False
            except EOFError as e:
                self.connected = False
                self.log.warning("TS3 Server connection error - EOFError: %s" % e)
                return False
            except KeyError as e:
                self.connected = False
                self.log.warning("TS3 Server connection error - KeyError: %s" % e)
                return False

            # fetching channels
            self.log.debug("Fetching channels")
            self.channelList = []
            result = self.server.send_command('channellist -icon')
            for channel in result.data:
                if int(channel['channel_icon_id']) < 0:
                    channel['channel_icon_id'] = str(int(channel['channel_icon_id']) + 4294967296)
                self.channelList.append(channel)

            # fetching groups
            self.log.debug("Fetching groups")
            self.groupList = []
            result = self.server.send_command('servergrouplist')
            self.groupList = result.data

        return True

    def cacheFiles(self):
        if self.connect():
            self.log.info("Caching server icon")
            self.cacheServerIcon(self.serverInfo['virtualserver_icon_id'])

            self.log.info("Caching channel icons")
            for channel in self.channelList:
                self.log.debug("Caching file for channel: %s" % channel['channel_name'])
                if not self.cacheIcon(channel['channel_icon_id']):
                    break

            self.log.info("Caching client icons")
            for client in self.onlineClients.keys():
                self.log.debug("Caching file for client: %s" % self.onlineClients[client]['client_nickname'])
                if not self.cacheIcon(self.onlineClients[client]['client_icon_id']):
                    break

            self.log.info("Caching group icons")
            for group in self.groupList:
                self.log.debug("Caching file for group: %s" % group['name'])
                if int(group['iconid']):
                    if not self.cacheIcon(group['iconid']):
                        break


    def refresh(self):
        if not self.connect():
            self.log.warning("Not refreshing online clients because we are disconnected")
            return False

        if self.lastOnlineRefreshDate > (time.time() - self.config['updateOnlineLock']):
            self.log.debug("Not refreshing online clients")
        else:
            self.lastOnlineRefreshDate = time.time()
            self.log.debug("Fetching online clients")
            response = self.server.send_command("clientlist -icon")
            self.onlineClients = {}
            clients = {}
            for client in response.data:
                clients[client['clid']] = client

            # fetching clients
            for client in clients.keys():
                # ignoring console users
                # clientDetails = self.server.send_command('clientinfo clid=%s' % clients[client]['clid'])
                # print clientDetails
                if int(clients[client]['client_type']) != 1:
                    self.onlineClients[clients[client]['client_database_id']] = {
                        'client_database_id': int(clients[client]['client_database_id']),
                        'client_nickname': clients[client]['client_nickname'],
                        'cid': int(clients[client]['cid']),
                        'clid': int(clients[client]['clid']),
                        'client_icon_id': int(clients[client]['client_icon_id']),
                        'client_type': int(clients[client]['client_type'])
                    }

            self.log.info("Found %s online clients" % len(self.onlineClients))
        return True

    # request from frontend
    def returnOnlineUserDetails(self):
        if self.refresh():
            ret = []
            for cldbid in self.onlineClients.keys():
                # Get user details
                myUserDetails = self.fetchUserdetatilsByCldbid(cldbid)

                moreInfo = []
                moreInfo.append("Last Conn: %s" % timestampToString(myUserDetails['client_lastconnected']))
                moreInfo.append("Total Conn: %s" % myUserDetails['client_totalconnections'])
                moreInfo.append("Created: %s" % timestampToString(myUserDetails['client_created']))
                if myUserDetails['client_description']:
                    moreInfo.append("Description: %s" % myUserDetails['client_created'])

                userGroups = []
                userGroupIcon = 0
                userGroupName = ""
                for group in myUserDetails['groups']:
                    for g in self.groupList:
                        if g['sgid'] == group['sgid']:
                            userGroupIcon = 'icon_' + g['iconid']
                            self.cacheIcon(g['iconid'])
                    userGroups.append(group['name'])
                    userGroupName = group['name']
                moreInfo.append("Groups: %s" % ', '.join(userGroups))

                # if admin
                moreInfo.append("Last IP: %s" % myUserDetails['client_lastip'])
                # {'client_total_bytes_downloaded': '366040', 'client_month_bytes_downloaded': '39211', 'client_database_id': '644', 'client_icon_id': '0', 'client_base64HashClientUID': 'niljclpbalpldpbecbdiemcdncjlglfbilemoloi', 'client_month_bytes_uploaded': '0', 'client_flag_avatar': None, 'client_nickname': 'EvilM0nkey', 'client_description': None, 'client_total_bytes_uploaded': '0'}

                # Get channel details
                channelName = "Unknown"
                channelIcon = None
                try:
                    for channel in self.channelList:
                        if int(channel['cid']) == self.onlineClients[cldbid]['cid']:
                            channelName = channel['channel_name'].decode('utf-8')
                            channelIcon = channel['channel_icon_id']
                            self.cacheIcon(channelIcon)
                except IndexError:
                    pass

                # FIXME residign for dynamic pairs <a>(img/title) and text</a>
                ret.append({'networkId': self.myId,
                            'networkName': self.longName,
                            'networkMoreInfo': self.moreInfo,
                            'networkDetailInfo': channelName,
                            'id': 1234,
                            'nickDeco': userGroupIcon,
                            'nickDecoInfo': userGroupName,
                            'nick': self.onlineClients[cldbid]['client_nickname'].decode('utf-8'),
                            'moreInfo': ', '.join(moreInfo),
                            'cacheFile1': 'icon_' + str(int(self.serverInfo['virtualserver_icon_id']) + 4294967296),
                            'cacheFile2': 'icon_' + channelIcon })
            return (True, ret)
        else:
            return (False, "Unable to connect to TS3 server.")

    def cacheServerIcon(self, iconId):
        self.cacheIcon((int(iconId) + 4294967296))

    def cacheIcon(self, iconId, cid = 0):
        if int(iconId) == 0:
            self.log.debug("No icon available because IconID is 0")
            return True
        else:
            return self.cacheFile("/icon_%s" % int(iconId), cid)

    # file transfer methods
    def cacheFile(self, name, cid, cpw = "", seekpos = 0):
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
            try:
                response = self.server.send_command("ftinitdownload clientftfid=%s name=%s cid=%s cpw=%s seekpos=%s" % (self.clientftfid, name, cid, cpw, seekpos))
                fileinfo = response.data[0]
            except EOFError as e:
                self.connected = False
                self.log.warning("Unable to initialize filetransfer: %s" % e)
                return False
            except KeyError as e:
                self.connected = False
                self.log.warning("Unable to initialize filetransfer: %s" % e)
                return False

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
            output_file = open(outputFilePath,'ab')
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

    def fetchUserdetatilsByCldbid(self, cldbid):
        updateUserDetails = False
        try:
            if self.clientDatabase[cldbid]['lastUpdateUserDetails'] < (time.time() - self.config['updateLock']):
                updateUserDetails = True
        except KeyError:
            updateUserDetails = True

        if updateUserDetails:
            self.log.debug("Fetching user details for cldbid: %s" % cldbid)
            response = self.server.send_command('clientdbinfo cldbid=%s' % cldbid)
            response.data[0]
            self.clientDatabase[cldbid] = response.data[0]

            self.clientDatabase[cldbid]['lastUpdateUserDetails'] = time.time()
        else:
            self.log.debug("Not fetching user details for cldbid: %s" % cldbid)


        updateUserGroupDetails = False
        try:
            if self.clientDatabase[cldbid]['lastUpdateUserGroupDetails'] < (time.time() - self.config['updateOnlineLock']):
                updateUserGroupDetails = True
        except KeyError:
            updateUserGroupDetails = True

        if updateUserGroupDetails:
            self.log.debug("Fetching user group details for cldbid: %s" % cldbid)
            response = self.server.send_command('servergroupsbyclientid cldbid=%s' % cldbid)
            self.clientDatabase[cldbid]['groups'] = response.data

            self.clientDatabase[cldbid]['lastUpdateUserGroupDetails'] = time.time()
        else:
            self.log.debug("Not fetching user group details for cldbid: %s" % cldbid)

        return self.clientDatabase[cldbid]

    def test(self):
        result = "blah"
        # result = self.server.send_command('ftgetfilelist cid=0 cpw= path=/')
        return result