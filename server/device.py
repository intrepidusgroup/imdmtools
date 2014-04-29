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

    queue = deque() # Array to hold commands that HAVE NOT been sent    
    cmdList = {} # Dictionary to hold commands and responses that HAVE been sent

    # Possible additional parameters
    #availableCapacity = 0
    #totalCapacity = 0
    #installedApps = []

    def __init__(self, *args, **kwargs):
        if kwargs.get('dictionary'):
            self.__setup_dict(kwargs['dictionary'])
        else:
            self.__setup(kwargs['UDID'], kwargs['tuple'])

    def __setup(self, newUDID, tuple):
        self.UDID = newUDID
        self.IP = tuple[0]
        self.pushMagic = tuple[1]
        self.deviceToken = tuple[2]
        self.unlockToken = tuple[3]
    def __setup_dict(self, storage):
        # Sets up device from read in data
        self.IP = storage['IP']
        self.pushMagic = storage['pushmagic']
        self.deviceToken = storage['deviceToken']
        self.unlockToken = storage['unlockToken']
        self.UDID = storage['UDID']
        self.name = storage['name']
        self.model = storage['model']
        self.OS = storage['OS']

        # May need to rework queue since its type deque
        self.queue = storage['queue']    
        self.cmdList = storage['cmdList']

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
        self.queue.append(cmd)

    def sendCommand(self):
        # Pop command off queue to be sent to the device
        cmd = self.queue.popleft()
        cmdList[cmd] = ''
        return cmd


    def addResponse(self, cmd, response):
        # Add a response to correspond with a previous command
        cmdList[cmd] = response # If only it was this easy...
        #search queue, queue[x][1] = response

    def output(self):
        # DEPRICATED
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
