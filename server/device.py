from collections import deque
from plistlib import *
from operator import itemgetter
import time, datetime, copy

class device:
    TIMEOUT = 20    # Number of seconds before command times out
    WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 "
    def __init__(self, newUDID, tuple):
        self.UDID = newUDID
        self.IP = tuple[0]
        self.pushMagic = tuple[1]
        self.deviceToken = tuple[2]
        self.unlockToken = tuple[3]

        # Hard coded information to show possible features
        self.GEO = "42*21'29''N 71*03'49''W"

        # Owner and location default to unassigned
        self.owner = 'Unassigned'
        self.location = 'Unassigned'

        self.status = 0 # 0=ready for command (green? gray?)
                        # 1=command in queue (yellow)
                        # 2=error/timeout (red)
                        # maybe have green (last command successful?)

        # Possible additional parameters based on query commands
        #self.availableCapacity
        #self.totalCapacity
        #self.installedApps

        self.name = ''
        self.customName = ''
        self.model = ''
        self.OS = ''

        # Dictionary to hold commands and responses that HAVE been sent
        # Keys are Command UUID, value is a dictionary
        # {'command', 'response', 'order', 'status'}
        self.cmdList = {}

        # Queue to hold commands that HAVE NOT been sent
        self.queue = deque()


    def getUDID(self):
        return self.UDID

    def getQueueInfo(self):
        # Returns information needed by queue function
        return self.pushMagic, self.deviceToken

    def getResponse(self, cmdUUID):
        return self.cmdList[cmdUUID]['response']

    def sortCommands(self):
        temp = []
        for key in self.cmdList:
            temp.append((self.cmdList[key]['order'], key))
        return sorted(temp, reverse=True)


    def populate(self):
        # Returns info as a dictionary for use with mustache
        d = {}
        d['UDID'] = self.UDID
        if self.customName:
            d['name'] = self.customName
        else:
            d['name'] = self.name
        d['ip'] = self.IP
        d['owner'] = self.owner
        d['location'] = self.location
        d['geo'] = self.GEO
        d['status'] = ['success', 'warning', 'danger'][self.status]
        #d['icon'] = ['ok', 'refresh', 'remove'][self.status] # possible glyphicon functionality

        # Send back 5 most recent commands
        temp = self.sortCommands()
        d['commands'] = []
        for tuple in temp[:5]:
            # Check for commands with variables that are not JSON serializable
            if 'UnlockToken' in self.cmdList[tuple[1]]['cmd']['Command']:
                # Remove unlocktoken from output
                temp_cmd = copy.deepcopy(self.cmdList[tuple[1]])
                temp_cmd['cmd']['Command']['UnlockToken'] = 'Redacted by server'
                d['commands'].append(temp_cmd)
            elif 'CertificateList' in self.cmdList[tuple[1]]['response']:
                # Remove CertificateList data from output
                # TODO: Possibly implement some other method of delivering certificate data
                temp_cmd = copy.deepcopy(self.cmdList[tuple[1]])
                for i in range(len(temp_cmd['response']['CertificateList'])):
                   temp_cmd['response']['CertificateList'][i]['Data'] = 'Redacted by server'
                d['commands'].append(temp_cmd)
            elif 'ProfileList' in self.cmdList[tuple[1]]['response']:
                # Remove SignerCertificates data from output
                # Note that some profiles may not have SignerCertificates, in which case this
                # will add it to the ProfileList, though only for response output on server
                temp_cmd = copy.deepcopy(self.cmdList[tuple[1]])
                for i in range(len(temp_cmd['response']['ProfileList'])):
                    temp_cmd['response']['ProfileList'][i]['SignerCertificates'] = 'Redacted by server'
                d['commands'].append(temp_cmd)
            elif 'ProvisioningProfileList' in self.cmdList[tuple[1]]['response']:
                # Change ExpiryDate datetime objects to UTC strings for output
                temp_cmd = copy.deepcopy(self.cmdList[tuple[1]])
                for i in range(len(temp_cmd['response']['ProvisioningProfileList'])):
                    temp_cmd['response']['ProvisioningProfileList'][i]['ExpiryDate'] = temp_cmd['response']['ProvisioningProfileList'][i]['ExpiryDate'].strftime("%Y-%m-%d %H:%M:%S") + " UTC"
                d['commands'].append(temp_cmd)
            elif 'InstallProfile' == self.cmdList[tuple[1]]['cmd']['Command']['RequestType']:
                #Remove payload data from output
                temp_cmd = copy.deepcopy(self.cmdList[tuple[1]])
                temp_cmd['cmd']['Command']['Payload'] = 'Redacted by server'
                d['commands'].append(temp_cmd)

            else:
                d['commands'].append(self.cmdList[tuple[1]])

        return d

    def sanitize(self, string):
        # Function to remove any non-alphanumeric characters from input
        wl = set(self.WHITELIST)

        for char in set(string)-wl:
            string = string.replace(char, '');

        return string[:32]

    def updateMetadata(self, newName, newOwner, newLocation):
        # Fuction for customizable metadata
        if newName:
            self.customName = self.sanitize(newName.strip())
        if newOwner:
            self.owner = self.sanitize(newOwner.strip())
        if newLocation:
            self.location = self.sanitize(newLocation.strip())


    def updateInfo(self, newName, newModel, newOS):
        # Update class variables with data from DeviceInformation
        self.name = newName
        self.model = newModel
        self.OS = newOS

    def reenroll(self, newIP, newPush, newUnlock):
        self.IP = newIP
        self.pushMagic = newPush
        self.unlockToken = newUnlock

    def addCommand(self, cmd):
        # Add a new command to the queue
        # Update status to show command pending
        self.status = 1
        cmd['TimeStamp'] = time.time()

        # Update command with unlockToken if necessary
        if cmd['Command']['RequestType'] == 'ClearPasscode':
            cmd['Command']['UnlockToken'] = Data(self.unlockToken)

        print "ADDED COMMAND TO QUEUE:", cmd['CommandUUID']
        self.queue.append(cmd)

    def sendCommand(self):
        # Pop command off queue to be sent to the device
        if len(self.queue) == 0:
            print "**No commands left in queue"
            return ''

        cmd = self.queue.popleft()
        self.cmdList[cmd['CommandUUID']] = {}
        self.cmdList[cmd['CommandUUID']]['cmd'] = cmd
        self.cmdList[cmd['CommandUUID']]['response'] = ''
        self.cmdList[cmd['CommandUUID']]['status'] = 'warning'
        self.cmdList[cmd['CommandUUID']]['order'] = len(self.cmdList.keys())
        print "**Sending command", cmd['CommandUUID'], "and moving it from queue**"
        return cmd


    def addResponse(self, cmdUUID, response):
        # Add a response to correspond with a previous command
        print "**ADDING RESPONSE TO CMD:", cmdUUID
        self.cmdList[cmdUUID]['response'] = response
        # Check response for success/failure
        if response['Status'] == 'Acknowledged':
            self.cmdList[cmdUUID]['status'] = 'success'
            self.status = 0
        elif response['Status'] == 'Error':
            self.cmdList[cmdUUID]['status'] = 'danger'
            self.status = 2

    def checkTimeout(self):
        # Checks for command timeout
        now = time.time()

        # If we have no commands waiting, we're good
        if self.status != 1:
            return
        
        # Check queue for timed out commands
        if len(self.queue) > 0:
            for cmd in self.queue:
                if now - cmd['TimeStamp'] > self.TIMEOUT:
                    # Command has time out, add it to cmd list with an error
                    self.status = 2
                    self.queue.remove(cmd)
                    self.cmdList[cmd['CommandUUID']] = {}
                    self.cmdList[cmd['CommandUUID']]['cmd'] = cmd
                    self.cmdList[cmd['CommandUUID']]['response'] = {'Status':'TimeoutError'}
                    self.cmdList[cmd['CommandUUID']]['status'] = 'danger'
                    self.cmdList[cmd['CommandUUID']]['order'] = len(self.cmdList.keys())
                    return

        # Check command list for timed out commands
        for commandUUID in self.cmdList:
            if self.cmdList[commandUUID]['response'] == "" and now-self.cmdList[commandUUID]['cmd']['TimeStamp'] > self.TIMEOUT:
                self.status = 2
                self.cmdList[command['cmd']['CommandUUID']]['status'] = 'danger'
                self.cmdList[command['cmd']['CommandUUID']]['response'] = {'Status':'TimeoutError'}
