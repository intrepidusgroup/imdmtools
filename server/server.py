import web, os, pprint, json, uuid, sys, re
from plistlib import *
from APNSWrapper import *
from creds import *
from problems import *
from datetime import datetime
from subprocess import call
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

LOGFILE = 'xactn.log'

# Dummy socket to get the hostname
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(('google.com', 0))

# NOTE: Will need to overwrite this if behind a firewall
MY_ADDR = s.getsockname()[0] + ":8080"

# 
# set up some smime objects to verify signed messages coming from devices
#
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
from web.wsgiserver.ssl_builtin import BuiltinSSLAdapter

CherryPyWSGIServer.ssl_adapter = BuiltinSSLAdapter('Server.crt', 'Server.key', None)

###########################################################################

last_result = ''
last_sent = ''

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
)



def setup_commands():
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
                'UnlockToken',

    		'MEID', 'CellularTechnology', 'BatteryLevel', 
		    'SubscriberCarrierNetwork', 'VoiceRoamingEnabled', 
		    'SubscriberMCC', 'SubscriberMNC', 'DataRoaming', 'VoiceRomaing',
            'JailbreakDetected'
            ]
        )
    )

    ret_list['ClearPasscode'] = dict(
        Command = dict(
            RequestType = 'ClearPasscode',
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
# new for iOS 5:
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
        
class queue_cmd_post:
    def POST(self):
        global current_command, last_sent
        global devList

	
        devListPrime = []
	i = json.loads(web.data())
	cmd = i.pop("cmd", [])
	dev = i.pop("dev[]", [])

        for device in dev:
            for devP in devList:
                if devP[1] == devP[1]:
                    devListPrime.append(devP)
                    break
	

        for dev_creds in devListPrime:
            mylocal_PushMagic = dev_creds[1]
            mylocal_DeviceToken = dev_creds[2]
            print mylocal_PushMagic
            print mylocal_DeviceToken
            #cmd = i.cmd
            cmd_data = mdm_commands[cmd]
            cmd_data['CommandUUID'] = str(uuid.uuid4())
            current_command = cmd_data
            last_sent = pprint.pformat(current_command)

	    """
	    # Send command to Apple
            wrapper = APNSNotificationWrapper('PushCert.pem', False)
            message = APNSNotification()
            message.token(mylocal_DeviceToken)
            message.appendProperty(APNSProperty('mdm', mylocal_PushMagic))
            wrapper.append(message)
            wrapper.notify()
            """
        
	#Update page
        return update()
	
class do_mdm:        
    global last_result, sm_obj
    def PUT(self):
        global current_command, last_result
        HIGH='[1;31m'
        LOW='[0;32m'
        NORMAL='[0;39m'

        i = web.data()
        pl = readPlistFromString(i)

        if 'HTTP_MDM_SIGNATURE' in web.ctx.environ:
            raw_sig = web.ctx.environ['HTTP_MDM_SIGNATURE']
            cooked_sig = '\n'.join(raw_sig[pos:pos+76] for pos in xrange(0, len(raw_sig), 76))
    
            signature = '''
-----BEGIN PKCS7-----
%s
-----END PKCS7-----
''' % cooked_sig

            '''Comment to fix color highlighting.'''

            #print i
            #print signature

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
            rd = current_command
            print "%sSent: %s%s" % (HIGH, rd['Command']['RequestType'], NORMAL)
#            print HIGH, rd, NORMAL

        elif pl.get('MessageType') == 'TokenUpdate':
            print HIGH+"Token Update"+NORMAL
            rd = do_TokenUpdate(pl)
            print HIGH+"Device Enrolled!"+NORMAL

        elif pl.get('Status') == 'Acknowledged':
            print HIGH+"Acknowledged"+NORMAL
            rd = dict()

        else:
            rd = dict()
            if pl.get('MessageType') == 'Authenticate':
                print HIGH+"Authenticate"+NORMAL
            elif pl.get('MessageType') == 'CheckOut':
                print HIGH+"Device leaving MDM"+ NORMAL
            else:
                print HIGH+"(other)"+NORMAL
                print HIGH, pl, NORMAL
        log_data(pl)
        log_data(rd)

        out = writePlistToString(rd)
#        print LOW, out, NORMAL

        q = pl.get('QueryResponses')
        last_result = pprint.pformat(pl)
        return out
'''
        if q:
            redact_list = ('UDID', 'BluetoothMAC', 'SerialNumber', 'WiFiMAC',
                'IMEI', 'ICCID', 'SerialNumber')
            for resp in redact_list:
                if q.get(resp):
                    pl['QueryResponses'][resp] = '--redacted--'
        for top in ('UDID', 'Token', 'PushMagic', 'UnlockToken'):
            if pl.get(top):
                pl[top] = '--redacted--'
'''


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
    # Function to update displays on the frontend
    # Sends back dictionary of devices, last command, last result, problems
    # Is called on page load and polling

    global last_result, last_sent, problems, devList
    
    # Create list of devices
    dev_list_out = []
    for dev_creds in devList:
	dev_list_out.append([dev_creds[0], dev_creds[1]])
    
    # Format output as a dict and then return as JSON
    out = dict()
    out['dev_list'] = dev_list_out
    out['last_cmd'] = last_sent
    out['last_result'] = last_result
    out['problems'] = '<br>'.join(problems)

    return json.dumps(out)	


class poll:
    def POST(self):
        # Polling function to update page with new data
        return update()


def do_TokenUpdate(pl):
    global mdm_commands, devList

    my_PushMagic = pl['PushMagic']
    my_DeviceToken = pl['Token'].data
    my_UnlockToken = pl['UnlockToken'].data

    mdm_commands['ClearPasscode'] = dict(
        Command = dict(
            RequestType = 'ClearPasscode',
            UnlockToken = Data(my_UnlockToken)
        )
    )

    newTuple = (web.ctx.ip, my_PushMagic, my_DeviceToken, my_UnlockToken)
    devList.append(newTuple)

    # Check for duplicates in devList
    for dev1 in devList:
      found = False
      for dev2 in devList:
        if dev1[1] == dev2[1]:
          if not found:
             found = True
          else:
             devList.remove(dev2)
    
    devListP = devList
    devList = list(set(devListP))
    out = "devList = ["
    for dev in devList:
        ipAddr = dev[0]
        pushMagic = dev[1]
        deviceToken = dev[2]
        unlockToken = dev[3]
       
        out += """
            ( '%s'
            , '%s'
            , %s
            , %s
            ),
        """ % (ipAddr, pushMagic, repr(deviceToken), repr(unlockToken))
    out += "]"
    """Comment to fix syntax highlighting"""
    # tokenStr = (repr(my_DeviceToken)).replace("'", "").replace("\\\\", "\\")
    #out = "devList = " + r"%s" % devList

    fd = open('creds.py', 'w')
    fd.write(out)
    fd.close()
    
    # Why return empty dictionary?
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
        out = """
problems = %s""" % problems
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
        else:
            raise web.notfound()


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
	    #raise web.notfound()



mdm_commands = setup_commands()
current_command = mdm_commands['DeviceLock']

def log_data(out):
    fd = open(LOGFILE, "a")
    fd.write(datetime.now().ctime())
    fd.write(" %s\n" % repr(out))
    fd.close()

if __name__ == "__main__":
    print "Starting Server" 
    app = web.application(urls, globals())
    app.internalerror = web.debugerror
    app.run()
    try:
        app.run()
    except:
        os._exit(0)
