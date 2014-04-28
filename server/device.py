from collections import deque

class device:
    IP = '0.0.0.0'
    pushMagic = ''
    deviceToken = ''
    unlockToken = ''
    name = ''
    model = ''
    OS = ''

    queue = deque() # Array to hold commands that HAVE NOT been sent    
    cmdList = {} # Dictionary to hold commands and responses that HAVE been sent

    # Possible additional parameters
    #availableCapacity = 0
    #totalCapacity = 0
    #installedApps = []

    def __init__(self):
        pass

    def __init__(self, newIP, newPushMagic, newDeviceToken, newUnlockToken):
        self.IP = newIP
        self.pushMagic = newPushMagic
        self.deviceToken = newDeviceToken
        self.unlockToken = newUnlockToken

    def updateInfo(self, newName, newModel, newOS):
        # Update class variables with data from DeviceInformation
        self.name = newName
        self.model = newModel
        self.OS = newOS

    def addCommand(self, cmd):
        # Add a new command to the queue
        #queue.append(cmd)

    def sendCommand(self):
        # Pop command off queue to be sent to the device
        #cmd = queue.popleft()
        #cmdList['cmd'] = ''
        #return cmd


    def addResponse(self, cmd, response):
        # Add a response to correspond with a previous command
        #cmdList[cmd] = response
        #search queue, queue[x][1] = response

        # If command is DeviceInformation, call updateInfo
        #if cmd=='DeviceInformation':
            #self.updateInfo(response.get(DeviceName), ...)

    def output(self):
        # Format data for outputting to creds.py


