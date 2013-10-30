# Overview

Instructions and code for setting up a simple iOS Mobile Device Management (MDM) server.  MDM allows for OS level control of a device from a centralized location.  A remote administrator can install/remove apps, install/revoke certificates, lock the device, change password requirements, etc.  

# Prerequisites

 * Publicly accessible Linux/Unix server
 * Apple Enterprise Account
 * Apple Developer Account
 * OS X KeyChain Access Tool
 * openssl command-line
 * Java SDK (java/javac)

# Apple MDM Push Certificate
Download the [MDM vendor CSR signing tool](http://www.softhinker.com/in-the-news/iosmdmvendorcsrsigning/Softhinker.zip) from [Softhinker](http://www.softhinker.com/).  You will notice several certificates are included:
 * customer.der
   * Must be replaced
   * Generated from server setup
   * Accept defaults for all other values (Including **Challenge password**)
 * intermediate.pem 
   * Does not need replaced
   * Apple's WWDR intermediate certificate
 * mdm.pem
   * Must be replaced
   * Obtain from [iOS Provisioning Portal](Apple Member Center)
   * Use **customer.csr** created by **genCustomerDer.sh**
   * Download the file, should be in .cer format
   * Convert to pem: **openssl x509 -inform der -in YOUR_MDM.cer -out mdm.pem**
 * root.pem
   * Does not need replaced
   * Apple's root certificate
 * vendor.p12
   * Import the customerPrivateKey.pem into Keychain access
   * Export the private key as p12 file

Now that all certificates are in place, compile and run the java program
    cd Softhinker/src/com/softhinker
    javac -cp "../../../lib/dom4j-1.6.1.jar:./" Test.java 
    cd ../../
    java -cp ".././lib/dom4j-1.6.1.jar:./" com.softhinker.Test

You should now have **plist_encoded.plist**.  Upload this to [Apple's Push Certificates Portal](https://identity.apple.com/pushcert/).  If all was successfull you will see a screen similar to below:

Notice the (i) icon besides renew.  If you click it there will be a long string of text ending in **UID=com.apple.mgmt...**, make sure to copy that string starting at **com** since you will need it later.  Finally download the certificate, save as **PushCert.pem** and upload to your server.

# Server Setup

The server is a direct copy from [Intrepidus Group's blackhat presentation](https://intrepidusgroup.com/).
