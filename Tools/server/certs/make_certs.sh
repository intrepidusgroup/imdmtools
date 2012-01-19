#!/bin/sh

echo ""
echo "Setting up certificates for MDM server testing!"
echo ""
echo "1. Creating Certificate Authority (CA)"
echo " ** For 'Common Name' enter something like 'MDM Test CA'"
echo ""
openssl req -new -x509 -extensions v3_ca -keyout cakey.key -out cacert.crt -days 365

echo ""
echo "2. Creating the Web Server private key and certificate request"
echo " ** For 'Common Name' enter your server's IP address **"
echo ""
openssl genrsa 2048 > server.key
openssl req -new -key server.key -out server.csr

echo ""
echo "3. Signing the server key with the CA. You'll the CA passphrase from step 1."
echo ""
openssl x509 -req -days 365 -in server.csr -CA cacert.crt -CAkey cakey.key -CAcreateserial -out server.crt



echo ""
echo "4. Creating the device Identity key and certificate request"
echo " ** For 'Common Name' enter something like 'my device'"
echo ""
openssl genrsa 2048 > identity.key
openssl req -new -key identity.key -out identity.csr

echo ""
echo "5. Signing the identity key with the CA. You'll the CA passphrase from step 1."
echo " ** Give it a passphrase. You'll need to include that in the IPCU profile."
echo ""
openssl x509 -req -days 365 -in identity.csr -CA cacert.crt -CAkey cakey.key -CAcreateserial -out identity.crt
openssl pkcs12 -export -out identity.p12 -inkey identity.key -in identity.crt -certfile cacert.crt

echo ""
echo "6. Copying keys and certs to parent folder"
cp server.key ../Server.key
cp server.crt ../Server.crt
cp cacert.crt ../CA.crt
cp identity.p12 ../Identity.p12

