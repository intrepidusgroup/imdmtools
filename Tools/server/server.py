import web, os, pprint, json, uuid, sys
from plistlib import *
from APNSWrapper import *
from creds import *

#
# Simple, basic, bare-bones example test server
# Implements Apple's Mobile Device Management (MDM) protocol
# Compatible with iOS 4.x devices
# Not yet tested with iOS 5.0
#
# David Schuetz, Senior Consultant, Intrepidus Group
#
# Copyright 2011, Intrepidus Group
# http://intrepidusgroup.com
#

###########################################################################
# Update this to match the UUID in the test provisioning profiles, in order 
#   to demonstrate removal of the profile

my_test_provisioning_uuid = 'REPLACE-ME-WITH-REAL-UUIDSTRING'

                             
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
)


def setup_commands():
    global my_test_provisioning_uuid

    ret_list = dict()

    for cmd in ['DeviceLock', 'ProfileList', 'Restrictions',
        'CertificateList', 'InstalledApplicationList', 
        'ProvisioningProfileList']:
        
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
                'SIMMCC', 'SIMMNC', 'SerialNumber', 'UDID', 'WiFiMAC', 'UDID'
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
#    ret_list['DONT_EraseDevice'] = dict(
#        Command = dict(
#            RequestType = 'DONT_EraseDevice',
#        )
#    )
#
    if 'test.mobileconfig' in os.listdir('.'):
        my_test_cfg_profile = open('test.mobileconfig', 'rb').read()
        pl = readPlistFromString(my_test_cfg_profile)
        ret_list['RemoveProfile'] = dict(
            Command = dict(
                RequestType = 'RemoveProfile',
                Identifier = pl['PayloadIdentifier']
            )
        )
    else:
        print "Can't find test.mobileconfig in current directory."
        sys.exit()

    ret_list['InstallProfile'] = dict(
        Command = dict(
            RequestType = 'InstallProfile', 
            Payload = Data(my_test_cfg_profile)
        )
    )



    if 'test.mobileprovision' in os.listdir('.'):
        my_test_prov_profile = open('test.mobileprovision', 'rb').read()
    else:
        print "Can't find test.mobileprovision in current directory."
        sys.exit()

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

        wrapper = APNSNotificationWrapper('PlainCert.pem', False)
        message = APNSNotification()
        message.token(my_DeviceToken)
        message.appendProperty(APNSProperty('mdm', my_PushMagic))
        wrapper.append(message)
        print "[1;31mSending push notification[1;37m"
        wrapper.notify()

        return home_page()



class do_mdm:        
    global last_result
    def PUT(self):
        global current_command, last_result
        RED='[1;31m'
        GREY='[0;37m'

        i = web.data()
        pl = readPlistFromString(i)
#        print i

        print "%sReceived %4d bytes: %s" % (RED, len(web.data()), GREY),

        if pl.get('Status') == 'Idle':
            print RED + "Idle Status" + GREY
            rd = current_command
            print "%sSent: %s%s" % (RED, rd['Command']['RequestType'], GREY)

        elif pl.get('MessageType') == 'TokenUpdate':
            print RED+"Token Update"+GREY
            rd = do_TokenUpdate(pl)
            print RED+"Device Enrolled!"+GREY

        elif pl.get('Status') == 'Acknowledged':
            print RED+"Acknowledged"+GREY
            rd = dict()

        else:
            rd = dict()
            if pl.get('MessageType') == 'Authenticate':
                print RED+"Authenticate"+GREY
            else:
                print RED+"(other)"+GREY

        out = writePlistToString(rd)

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
    for key in mdm_commands:
        if current_command['Command']['RequestType'] == key:
            selected = 'selected'
        else:
            selected = ''
        drop_list += '<option value="%s" %s>%s</option>\n'%(key,selected,key)

    out = """
<html><head><title>MDM Test Console</title></head><body>
<form method="GET" action="/queue">
  <select name="command">
  <option value=''>Select command</option>
%s
  </select>
  <input type=submit value="Send"/>
</form>
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

        if 'enroll.mobileconfig' in os.listdir('.'):
            web.header('Content-Type', 'application/x-apple-aspen-config;charset=utf-8')
            web.header('Content-Disposition', 'attachment;filename="enroll.mobileconfig"')
            return open('enroll.mobileconfig', "rb").read()
        else:
            raise web.notfound()



mdm_commands = setup_commands()
current_command = mdm_commands['DeviceLock']


if __name__ == "__main__":
    print "[1;31mStarting Server[0;37m"
    app = web.application(urls, globals())
    app.run()
