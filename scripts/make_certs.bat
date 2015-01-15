@echo off
choice /m "Do you have CA?"
IF ERRORLEVEL 2 GOTO BUILDCA
IF ERRORLEVEL 1 GOTO INBUILTCA
:BUILDCA

echo 1. Creating Certificate Authority (CA)
echo For 'Common Name' enter something like 'MDM Test CA
openssl req -new -x509 -extensions v3_ca -keyout cakey.key -out cacert.crt -days 365

:CONT
echo 2. Creating the Web Server private key and certificate request
echo  For 'Common Name' enter your server's IP address
openssl genrsa 2048 > server.key
openssl req -new -key server.key -out server.csr 

echo 3. Signing the server key with the CA. You'll the CA passphrase from step 1.
openssl x509 -req -days 365 -in server.csr -CA cacert.crt -CAkey cakey.key -CAcreateserial -out server.crt -extfile .\server.cnf -extensions ssl_server

echo 4. Creating the device Identity key and certificate request.
openssl genrsa 2048 > identity.key
openssl req -new -key identity.key -out identity.csr

echo 5. Signing the identity key with the CA. You'll the CA passphrase from step 1.
echo ** Give it a passphrase. You'll need to include that in the IPCU profile.
openssl x509 -req -days 365 -in identity.csr -CA cacert.crt -CAkey cakey.key -CAcreateserial -out identity.crt
openssl pkcs12 -export -out identity.p12 -inkey identity.key -in identity.crt -certfile cacert.crt


echo 6. Copying keys and certs to server folder
copy server.key ..\server\Server.key
copy server.crt ..\server\Server.crt
copy cacert.crt ..\server\CA.crt
copy identity.crt ..\server\identity.crt
copy identity.p12 ..\server\Identity.p12


#echo  7. Generating keys and certs for plist generation
#openssl req -inform pem -outform der -in identity.csr -out customer.der
## Rename identity.csr to be used with the iOS Provisioning Portal
#rename identity.csr customer.csr

#copy Identity.p12 ..\vendor-signing\com\softhinker\vendor.p12
#copy customer.der ..\vendor-signing\com\softhinker\customer.der

#echo 8. Making the Apple Certificate useble by python
#openssl x509 -inform der -in AppleWWDRCA.cer -out intermediate.pem
#openssl x509 -inform der -in AppleIncRootCertificate.cer -out root.pem

#cp intermediate.pem ..\..\vendor-signing\com\softhinker\intermediate.pem
#cp root.pem ..\..\vendor-signing\com\softhinker\root.pem

echo DONE!!
goto end

:INBUILTCA
echo place CA Certificate and CA Key and then press enter. NOTE: you should have the password of the certificate.

@pause
goto CONT

:end
@pause
