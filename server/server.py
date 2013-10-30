import web, os, pprint, json, uuid, sys, re
from plistlib import *
from APNSWrapper import *
from creds import *
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
#

LOGFILE = 'xactn.log'

MY_ADDR = '<IP ADDRESS>:8080' # The address for the server that you used 
                             # when setting up the MDM enrollment profile

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
    '/queue', 'queue_cmd',
    '/checkin', 'do_mdm',
    '/server', 'do_mdm',
    '/ServerURL', 'do_mdm',
    '/CheckInURL', 'do_mdm',
    '/enroll', 'enroll_profile',
    '/ca', 'mdm_ca',
    '/favicon.ico', 'favicon',
    '/manifest', 'app_manifest',
    '/app', 'app_ipa',
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
            UnlockToken = Data(my_UnlockToken)
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
    else:
        print "Need both MyApp.ipa and Manifest.plist to enable InstallCustomApp."


    ret_list['RemoveApplication'] = dict(
    Command = dict(
        RequestType = 'RemoveApplication',
        Identifier = 'com.apple.movietrailers',
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
        return home_page()
        
class queue_cmd:
    def GET(self):
        global current_command, last_sent
        global my_DeviceToken, my_PushMagic
        i = web.input()
        cmd = i.command

        cmd_data = mdm_commands[cmd]
        cmd_data['CommandUUID'] = str(uuid.uuid4())
        current_command = cmd_data
        last_sent = pprint.pformat(current_command)

        wrapper = APNSNotificationWrapper('PushCert.pem', False)
        message = APNSNotification()
        message.token(my_DeviceToken)
        message.appendProperty(APNSProperty('mdm', my_PushMagic))
        wrapper.append(message)
        wrapper.notify()

        return home_page()



class do_mdm:        
    global last_result, sm_obj
    def PUT(self):
        global current_command, last_result
        HIGH='[1;31m'
        LOW='[0;32m'
        NORMAL='[0;30m'

        i = web.data()
        pl = readPlistFromString(i)

        if 'HTTP_MDM_SIGNATURE' in web.ctx.environ:
            raw_sig = web.ctx.environ['HTTP_MDM_SIGNATURE']
            cooked_sig = '\n'.join(raw_sig[pos:pos+76] for pos in xrange(0, len(raw_sig), 76))
    
            signature = """
-----BEGIN PKCS7-----
%s
-----END PKCS7-----
""" % cooked_sig


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
        if q:
            redact_list = ('UDID', 'BluetoothMAC', 'SerialNumber', 'WiFiMAC',
                'IMEI', 'ICCID', 'SerialNumber')
            for resp in redact_list:
                if q.get(resp):
                    pl['QueryResponses'][resp] = '--redacted--'
        for top in ('UDID', 'Token', 'PushMagic', 'UnlockToken'):
            if pl.get(top):
                pl[top] = '--redacted--'

        last_result = pprint.pformat(pl)
        return out


def home_page():
    global mdm_commands, last_result, last_sent, current_command

    drop_list = ''
    for key in sorted(mdm_commands.iterkeys()):
        if current_command['Command']['RequestType'] == key:
            selected = 'selected'
        else:
            selected = ''
        drop_list += '<option value="%s" %s>%s</option>\n'%(key,selected,key)

    out = """
<html><head><title>MDM Test Console</title></head><body>
<table border='0' width='100%%'><tr><td>
<form method="GET" action="/queue">
  <select name="command">
  <option value=''>Select command</option>
%s
  </select>
  <input type=submit value="Send"/>
</form></td>
<td align="center">Tap <a href='/enroll'>here</a> to <br/>enroll in MDM</td>
<td align="right">Tap <a href='/ca'>here</a> to install the <br/> CA Cert (for Server/Identity)</td>
</tr></table>
<hr/>
<b>Last command sent</b>
<pre>%s</pre>
<hr/>
<b>Last result</b> (<a href="/">Refresh</a>)
<pre>%s</pre>
</body></html>
""" % (drop_list, last_sent, last_result)

    return out


def do_TokenUpdate(pl):
    global my_PushMagic, my_DeviceToken, my_UnlockToken, mdm_commands

    my_PushMagic = pl['PushMagic']
    my_DeviceToken = pl['Token'].data
    my_UnlockToken = pl['UnlockToken'].data

    mdm_commands['ClearPasscode'] = dict(
        Command = dict(
            RequestType = 'ClearPasscode',
            UnlockToken = Data(my_UnlockToken)
        )
    )

    out = """
# these will be filled in by the server when a device enrolls

my_PushMagic = '%s'
my_DeviceToken = %s
my_UnlockToken = %s
""" % (my_PushMagic, repr(my_DeviceToken), repr(my_UnlockToken))

#    print out

    fd = open('creds.py', 'w')
    fd.write(out)
    fd.close()
    

    return dict()


class enroll_profile:
    def GET(self):

        if 'Enroll.mobileconfig' in os.listdir('.'):
            web.header('Content-Type', 'application/x-apple-aspen-config;charset=utf-8')
            web.header('Content-Disposition', 'attachment;filename="Enroll.mobileconfig"')
            return open('Enroll.mobileconfig', "rb").read()
        else:
            raise web.notfound()


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
#            web.header('Content-Disposition', 'attachment;filename="favicon.ico"')
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
            raise web.notfound()



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
    app.run()
