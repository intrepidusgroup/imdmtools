from collections import deque

class device:
    IP = '0.0.0.0'
    pushMagic = ''
    deviceToken = ''
    unlockToken = ''
    UDID = ''
    name = ''
    model = ''
    OS = ''

    queue = deque() # Queue to hold commands that HAVE NOT been sent    
    cmdList = {} # Dictionary to hold commands and responses that HAVE been sent
                 # Keys are Command UUID, value is an array [command, response]

    # Possible additional parameters
    # Note that adding parameters will void pickle list and may require device reregistration
    #availableCapacity = 0
    #totalCapacity = 0
    #installedApps = []

    def __init__(self, newUDID, tuple):
        self.UDID = newUDID
        self.IP = tuple[0]
        self.pushMagic = tuple[1]
        self.deviceToken = tuple[2]
        self.unlockToken = tuple[3]

    def getUDID(self):
        return self.UDID

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
        print "ADDED COMMAND TO QUEUE:", cmd['CommandUUID']
        self.queue.append(cmd)

    def sendCommand(self):
        # Pop command off queue to be sent to the device
        if len(self.queue) == 0:
            print "**ERROR: Attempting to fetch command, but no command in queue"
            return ''

        cmd = self.queue.popleft()
        self.cmdList[cmd['CommandUUID']] = ["", '']
        self.cmdList[cmd['CommandUUID']][0] = cmd
        print "**Sending command", cmd['CommandUUID'], "and moving it from queue**"
        return cmd


    def addResponse(self, cmdUUID, response):
        # Add a response to correspond with a previous command
        print "**ADDING RESPONSE TO CMD:", cmdUUID
        print self.cmdList.keys()
        #self.cmdList[cmdUUID][1] = response


    def output(self):
        # DEPRICATED - pickle module takes care of this
        # Convert data into a dictionary for persistence storage
        d = dict()
        d['IP'] = self.IP
        d['pushMagic'] = self.pushMagic
        d['deviceToken'] = self.deviceToken
        d['unlockToken'] = self.unlockToken
        d['UDID'] = self.UDID
        d['name'] = self.name
        d['model'] = self.model
        d['OS'] = self.OS

        # May need to rework queue since its a type deque
        d['queue'] = self.queue
        d['cmdList'] = self.cmdList

        return d

    def print_device(self):
        # Debug fuction to print the contents of the device
        # Should not be used with a live server due to sensitive token data
        print "****************"
        print "Device name:", self.name
        print "Device ID:", self.UDID
        print "IP:", self.IP
        print "Model:", self.model
        print "OS: iOS", self.OS
        print "Push magic token:", self.pushMagic
        print "Device token:", self.deviceToken
        # Contains lots of escape sequences and messes with printing
        #print "Unlock token:", self.unlockToken
        print self.queue
        print self.cmdList
        print "****************"
