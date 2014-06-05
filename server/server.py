import web, os, json, uuid, sys
import cPickle as pickle
from device import device # Custom device class
from plistlib import *
from APNSWrapper import *
from problems import *
from datetime import datetime
# needed to handle verification of signed messages from devices
from M2Crypto import SMIME, X509, BIO

#
# Simple, basic, bare-bones example test server
# Implements Apple's Mobile Device Management (MDM) protocol
# Compatible with iOS 4.x devices
# 
#
# David Schuetz, Senior Consultant, Intrepidus Group
#
# Copyright 2011, Intrepidus Group
# http://intrepidusgroup.com

# Reuse permitted under terms of BSD License (see LICENSE file).
# No warranties, expressed or implied.
# This is experimental software, for research only. Use at your own risk.

#
# Revision History:
#  
# * August 2011    - initial release, Black Hat USA
# * January 2012   - minor tweaks, including favicon, useful README, and 
#                    scripts to create certs, log file, etc.
# * January 2012   - Added support for some iOS 5 functions. ShmooCon 8.
# * February 2012  - Can now verify signed messages from devices
#                  - Tweaks to CherryPy startup to avoid errors on console  
# * January 2014   - Support for multiple enrollments
#                  - Supports reporting problems
# * April 2014     - Support for new front end
#                  - Tweaks and bug fixes
# * May 2014       - New device class
#                  - Rework server to use device class
#                  - Fixes a number of problems with using multiple devices
#                  - Support for new device-based front end


# Global variable setup
LOGFILE = 'xactn.log'

# Dummy socket to get the hostname
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(('8.8.8.8', 0))

# NOTE: Will need to overwrite this if behind a firewall
MY_ADDR = s.getsockname()[0] + ":8080"

# Set up some smime objects to verify signed messages coming from devices
sm_obj = SMIME.SMIME()
x509 = X509.load_cert('identity.crt')
sk = X509.X509_Stack()
sk.push(x509)
sm_obj.set_x509_stack(sk)

st = X509.X509_Store()
st.load_info('CA.crt')
sm_obj.set_x509_store(st)
    

###########################################################################
# Update this to match the UUID in the test provisioning profiles, in order 
#   to demonstrate removal of the profile

my_test_provisioning_uuid = 'REPLACE-ME-WITH-REAL-UUIDSTRING'

from web.wsgiserver import CherryPyWSGIServer

# Python 2.7 requires the PyOpenSSL library
# Python 3.x should use be able to use the default python SSL
try:
    from OpenSSL import SSL 
    from OpenSSL import crypto 
except ImportError: 
    SSL = None 


CherryPyWSGIServer.ssl_certificate = "Server.crt"
CherryPyWSGIServer.ssl_private_key = "Server.key"

###########################################################################

device_list = dict()

global mdm_commands

urls = (
    '/', 'root',
    '/queue', 'queue_cmd_post',
    '/checkin', 'do_mdm',
    '/server', 'do_mdm',
    '/ServerURL', 'do_mdm',
    '/CheckInURL', 'do_mdm',
    '/enroll', 'enroll_profile',
    '/ca', 'mdm_ca',
    '/favicon.ico', 'favicon',
    '/manifest', 'app_manifest',
    '/app', 'app_ipa',
    '/problem', 'do_problem',
    '/problemjb', 'do_problem',
    '/poll', 'poll',
    '/getcommands', 'get_commands',
    '/devices', 'dev_tab',
    '/response', 'get_response',
)



def setup_commands():
    # Function to generate dictionary of valid commands
    global my_test_provisioning_uuid

    ret_list = dict()

    for cmd in ['DeviceLock', 'ProfileList', 'Restrictions',
        'CertificateList', 'InstalledApplicationList', 
        'ProvisioningProfileList', 
# new for iOS 5:
        'ManagedApplicationList',
	]:
        ret_list[cmd] = dict( Command = dict( RequestType = cmd ))

    ret_list['SecurityInfo'] = dict(
        Command = dict(
            RequestType = 'SecurityInfo',
            Queries = [
                'HardwareEncryptionCaps', 'PasscodePresent', 
                'PasscodeCompliant', 'PasscodeCompliantWithProfiles',
            ]
        )
    )

    ret_list['DeviceInformation'] = dict(
        Command = dict(
            RequestType = 'DeviceInformation',
            Queries = [
                'AvailableDeviceCapacity', 'BluetoothMAC', 'BuildVersion', 
                'CarrierSettingsVersion', 'CurrentCarrierNetwork', 
                'CurrentMCC', 'CurrentMNC', 'DataRoamingEnabled', 
                'DeviceCapacity', 'DeviceName', 'ICCID', 'IMEI', 'IsRoaming', 
                'Model', 'ModelName', 'ModemFirmwareVersion', 'OSVersion', 
                'PhoneNumber', 'Product', 'ProductName', 'SIMCarrierNetwork', 
                'SIMMCC', 'SIMMNC', 'SerialNumber', 'UDID', 'WiFiMAC', 'UDID',
                'UnlockToken', 'MEID', 'CellularTechnology', 'BatteryLevel', 
		        'SubscriberCarrierNetwork', 'VoiceRoamingEnabled', 
		        'SubscriberMCC', 'SubscriberMNC', 'DataRoaming', 'VoiceRoaming',
                'JailbreakDetected'
            ]
        )
    )

    ret_list['ClearPasscode'] = dict(
        Command = dict(
            RequestType = 'ClearPasscode',
            # When ClearPasscode is used, the device specific unlock token needs to be added
            # UnlockToken = Data(my_UnlockToken)
        )
    )

# commented out, and command string changed, to avoid accidentally
# erasing test devices.
#
#    ret_list['EraseDevice'] = dict(
#        Command = dict(
#            RequestType = 'DONT_EraseDevice',
#        )
#    )
#
    if 'Example.mobileconfig' in os.listdir('.'):
        my_test_cfg_profile = open('Example.mobileconfig', 'rb').read()
        pl = readPlistFromString(my_test_cfg_profile)

        ret_list['InstallProfile'] = dict(
            Command = dict(
                RequestType = 'InstallProfile', 
                Payload = Data(my_test_cfg_profile)
            )
        )

        ret_list['RemoveProfile'] = dict(
            Command = dict(
                RequestType = 'RemoveProfile',
                Identifier = pl['PayloadIdentifier']
            )
        )

    else:
        print "Can't find Example.mobileconfig in current directory."


    if 'MyApp.mobileprovision' in os.listdir('.'):
        my_test_prov_profile = open('MyApp.mobileprovision', 'rb').read()

        ret_list['InstallProvisioningProfile'] = dict(
            Command = dict(
                RequestType = 'InstallProvisioningProfile', 
                ProvisioningProfile = Data(my_test_prov_profile)
            )
        )

        ret_list['RemoveProvisioningProfile'] = dict(
            Command = dict(
                RequestType = 'RemoveProvisioningProfile',
                # need an ASN.1 parser to snarf the UUID out of the signed profile
                UUID = my_test_provisioning_uuid
            )
        )

    else:
        print "Can't find MyApp.mobileprovision in current directory."

#
# iOS 5:
#
    ret_list['InstallApplication'] = dict(
    Command = dict(
        RequestType = 'InstallApplication',
        ManagementFlags = 4,  # do not delete app when unenrolling from MDM
        iTunesStoreID=471966214,  # iTunes Movie Trailers
    ))

    if ('MyApp.ipa' in os.listdir('.')) and ('Manifest.plist' in os.listdir('.')):
        ret_list['InstallCustomApp'] = dict(
        Command = dict(
            RequestType = 'InstallApplication',
            ManifestURL = 'https://%s/manifest' % MY_ADDR,
            ManagementFlags = 1,  # delete app when unenrolling from MDM
        ))
        print ret_list['InstallCustomApp']
    else:
        print "Need both MyApp.ipa and Manifest.plist to enable InstallCustomApp."


    ret_list['RemoveApplication'] = dict(
    Command = dict(
        RequestType = 'RemoveApplication',
        Identifier = 'com.apple.movietrailers',
    ))

    ret_list['RemoveCustomApplication'] = dict(
    Command = dict(
        RequestType = 'RemoveApplication',
        Identifier = 'mitre.managedTest',
    ))

#
# on an ipad, you'll likely get errors for the "VoiceRoaming" part.
# Since, you know...it's not a phone.
#
    ret_list['Settings'] = dict(
    Command = dict(
        RequestType = 'Settings',
        Settings = [
            dict(
                Item = 'DataRoaming',
                Enabled = False,
            ),
            dict(
                Item = 'VoiceRoaming',
                Enabled = True,
            ),
        ]
        ))

#
# haven't figured out how to make this one work yet. :(
#
#    ret_list['ApplyRedemptionCode'] = dict(
#    Command = dict(
#        RequestType = 'ApplyRedemptionCode',
## do I maybe need to add an iTunesStoreID in here?
#        RedemptionCode = '3WABCDEFGXXX',
#        iTunesStoreID=471966214,  # iTunes Movie Trailers
#        ManagementFlags = 1,
#    ))



    return ret_list

class root:
    def GET(self):
        return web.redirect("/static/index.html")

def queue(cmd, dev_UDID):
    # Function to add a command to a device queue
    global device_list, mdm_commands

    mylocal_PushMagic, mylocal_DeviceToken = device_list[dev_UDID].getQueueInfo()

    cmd_data = mdm_commands[cmd]
    cmd_data['CommandUUID'] = str(uuid.uuid4())

    # Have to search through device_list using pushmagic or devtoken to get UDID
    for key in device_list:
        if device_list[key].UDID == dev_UDID:
            device_list[key].addCommand(cmd_data)
            print "*Adding CMD:", cmd_data['CommandUUID'], "to device:", key
            break

    store_devices()


    # Send request to Apple
    wrapper = APNSNotificationWrapper('PushCert.pem', False)
    message = APNSNotification()
    message.token(mylocal_DeviceToken)
    message.appendProperty(APNSProperty('mdm', mylocal_PushMagic))
    wrapper.append(message)
    wrapper.notify()

    

class queue_cmd_post:
    def POST(self):
        global device_list
        
        i = json.loads(web.data())
        cmd = i.pop("cmd", [])
        dev = i.pop("dev[]", [])

        for UDID in dev:
            queue(cmd, UDID)

        # Update page - currently not using update()
        #return update()
        return

class do_mdm:        
    def PUT(self):
        global sm_obj, device_list
        HIGH='[1;31m'
        LOW='[0;32m'
        NORMAL='[0;39m'

        i = web.data()
        pl = readPlistFromString(i)

        if 'HTTP_MDM_SIGNATURE' in web.ctx.environ:
            raw_sig = web.ctx.environ['HTTP_MDM_SIGNATURE']
            cooked_sig = '\n'.join(raw_sig[pos:pos+76] for pos in xrange(0, len(raw_sig), 76))

            signature = '\n-----BEGIN PKCS7-----\n%s\n-----END PKCS7-----\n' % cooked_sig

            # Verify client signature - necessary?
            buf = BIO.MemoryBuffer(signature)
            p7 = SMIME.load_pkcs7_bio(buf)
            data_bio = BIO.MemoryBuffer(i)
            try:
                v = sm_obj.verify(p7, data_bio)
                if v:
                    print "Client signature verified."
            except:
                print "*** INVALID CLIENT MESSAGE SIGNATURE ***"

        print "%sReceived %4d bytes: %s" % (HIGH, len(web.data()), NORMAL),

        if pl.get('Status') == 'Idle':
            print HIGH + "Idle Status" + NORMAL
            
            print "*FETCHING CMD TO BE SENT FROM DEVICE:", pl['UDID']
            rd = device_list[pl['UDID']].sendCommand()

            # If no commands in queue, return empty string to avoid infinite idle loop
            if(not rd):
                return ''

            print "%sSent: %s%s" % (HIGH, rd['Command']['RequestType'], NORMAL)

        elif pl.get('MessageType') == 'TokenUpdate':
            print HIGH+"Token Update"+NORMAL
            rd = do_TokenUpdate(pl)
            print HIGH+"Device Enrolled!"+NORMAL

        elif pl.get('Status') == 'Acknowledged':
            print HIGH+"Acknowledged"+NORMAL
            rd = dict()
            # A command has returned a response
            # Add the response to the given device
            print "*CALLING ADD RESPONSE TO CMD:", pl['CommandUUID']
            device_list[pl['UDID']].addResponse(pl['CommandUUID'], pl)

            # If we grab device information, we should also update the device info
            if pl.get('QueryResponses'):
                print "DeviceInformation should update here..."
                p = pl['QueryResponses']
                device_list[pl['UDID']].updateInfo(p['DeviceName'], p['ModelName'], p['OSVersion'])

            # Update pickle file with new response
            store_devices()
        else:
            rd = dict()
            if pl.get('MessageType') == 'Authenticate':
                print HIGH+"Authenticate"+NORMAL
            elif pl.get('MessageType') == 'CheckOut':
                print HIGH+"Device leaving MDM"+ NORMAL
            elif pl.get('Status') == 'Error':
                print "*CALLING ADD RESPONSE WITH ERROR TO CMD:", pl['CommandUUID']
                device_list[pl['UDID']].addResponse(pl['CommandUUID'], pl)
            else:
                print HIGH+"(other)"+NORMAL
                print HIGH, pl, NORMAL
        log_data(pl)
        log_data(rd)

        out = writePlistToString(rd)
        #print LOW, out, NORMAL

        return out

class get_commands:
    def POST(self):
        # Function to return static list of commands to the front page
        # Should be called once by document.ready
        global mdm_commands

        drop_list = []
        for key in sorted(mdm_commands.iterkeys()):
            drop_list.append([key, key])    
        return json.dumps(drop_list)

def update():

    # DEPRICATED
    # Current polling endpoint is /devices
    # May be updated later on for intelligent updating of devices

    # Function to update devices on the frontend
    # Is called on page load and polling

    global problems, device_list
    
    # Create list of devices
    dev_list_out = []
    for UDID in device_list:
        dev_list_out.append([device_list[UDID].IP, device_list[UDID].pushMagic])
    
    # Format output as a dict and then return as JSON
    out = dict()
    out['dev_list'] = dev_list_out
    out['problems'] = '<br>'.join(problems)

    return json.dumps(out)


class poll:
    def POST(self):

    # DEPRICATED
    # Current polling endpoint is /devices
    # May be updated later on for intelligent updating of devices


        # Polling function to update page with new data
        return update()

class get_response:
    def POST(self):
        # Endpoint to return a reponse given a UDID and command UUID
        global device_list
        
        i = json.loads(web.data())

        return device_list[i['UDID']].getResponse(i['UUID'])

class dev_tab:
    def POST(self):
        # Endpoint to return list of devices with a list of device info
        global device_list
        devices = []

        for key in device_list:
            device_list[key].checkTimeout()
            devices.append(device_list[key].populate())

        # A device-sorting functionality could happen here

        out = {}
        out['devices'] = devices

        # return JSON
        return json.dumps(out)

def store_devices():
    # Function to convert the device list and write to a file
    global device_list

    print "STORING DEVICES..."
    
    # Use pickle to store list of devices
    pickle.dump(device_list, file('devicelist.pickle', 'w'))

def read_devices():
    # Function to open and read the device list
    # Is called when the server loads
    global device_list

    try:
        device_list = pickle.load(file('devicelist.pickle'))
        print "LOADED PICKLE"
    except:
        print "NO DATA IN PICKLE FILE or PICKLE FILE DOES NOT EXIST"
        # Creating new pickle file if need be
        open('devicelist.pickle', 'a').close()


def do_TokenUpdate(pl):
    global mdm_commands

    my_PushMagic = pl['PushMagic']
    my_DeviceToken = pl['Token'].data
    my_UnlockToken = pl['UnlockToken'].data

    newTuple = (web.ctx.ip, my_PushMagic, my_DeviceToken, my_UnlockToken)

    print "NEW DEVICE UDID:", pl.get('UDID')
    # A new device has enrolled, add a new device
    if pl.get('UDID') not in device_list:
        # Device does not already exist, create new instance of device
        device_list[pl.get('UDID')] = device(pl['UDID'], newTuple)
        print "ADDING DEVICE TO DEVICE_LIST"
    else:
        # Device exists, update information - token stays the same
        device_list[pl['UDID']].reenroll(web.ctx.ip, my_PushMagic, my_UnlockToken)
        print "DEVICE ALREADY EXISTS, UPDATE INFORMATION"


    # Queue a DeviceInformation command to populate fields in device_list
    # Is this command causing an off-by-one error with commands?
    queue('DeviceInformation', pl['UDID'])

    # Store devices in a file for persistence
    store_devices()

    # Return empty dictionary for use in do_mdm 
    return dict()


class enroll_profile:
    def GET(self):
	# Enroll an iPad/iPhone/iPod when requested
        if 'Enroll.mobileconfig' in os.listdir('.'):
            web.header('Content-Type', 'application/x-apple-aspen-config;charset=utf-8')
            web.header('Content-Disposition', 'attachment;filename="Enroll.mobileconfig"')
            return open('Enroll.mobileconfig', "rb").read()
        else:
            raise web.notfound()

class do_problem:
    # DEBUG
    # DEPRICATED?
    # TODO: Problems may need to be reworked a bit
    #       Stop storing in a .py file
    #       What is the purpose of problems? Whats the end goal?
    def GET(self):
        global problems
        problem_detect = ' ('
        problem_detect += datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if web.ctx.path == "/problem":
            problem_detect += ') Debugger attached to '
        elif web.ctx.path == "/problemjb":
            problem_detect += ') Jailbreak detected for ' 
        problem_detect += web.ctx.ip

        problems.insert(0, problem_detect)
        out = "\nproblems = %s" % problems
        fd = open('problems.py', 'w')
        fd.write(out)
        fd.close()

class mdm_ca:
    def GET(self):

        if 'CA.crt' in os.listdir('.'):
            web.header('Content-Type', 'application/octet-stream;charset=utf-8')
            web.header('Content-Disposition', 'attachment;filename="CA.crt"')
            return open('CA.crt', "rb").read()
        else:
            raise web.notfound()


class favicon:
    def GET(self):
        if 'favicon.ico' in os.listdir('.'):
            web.header('Content-Type', 'image/x-icon;charset=utf-8')
            return open('favicon.ico', "rb").read()
        elif 'favicon.ico' in os.listdir('./static/'):
            web.header('Content-Type', 'image/x-icon;charset=utf-8')
            return open('/static/favicon.ico', "rb").read()
        else:
            raise web.ok


class app_manifest:
    def GET(self):

        if 'Manifest.plist' in os.listdir('.'):
            web.header('Content-Type', 'text/xml;charset=utf-8')
            return open('Manifest.plist', "rb").read()
        else:
            raise web.notfound()


class app_ipa:
    def GET(self):

        if 'MyApp.ipa' in os.listdir('.'):
            web.header('Content-Type', 'application/octet-stream;charset=utf-8')
            web.header('Content-Disposition', 'attachment;filename="MyApp.ipa"')
            return open('MyApp.ipa', "rb").read()
        else:
            return web.ok


def log_data(out):
    fd = open(LOGFILE, "a")
    fd.write(datetime.now().ctime())
    fd.write(" %s\n" % repr(out))
    fd.close()


if __name__ == "__main__":
    print "Starting Server" 
    app = web.application(urls, globals())
    app.internalerror = web.debugerror

    try:
        app.run()
    except:
        sys.exit(0)
else:
    # app.run() seems to use server.py as a module
    # Placing these in main causes them not to run
    # Placing these above main causes them to run twice
    mdm_commands = setup_commands()
    read_devices()

