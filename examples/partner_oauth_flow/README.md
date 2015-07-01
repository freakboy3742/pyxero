Simple example for the oAuth partner workflow
=============================================

Once you've gone through Xero's process of registering a partner application, having the application
be approved, and obtaining the certificates from Entrust you will need to split the p12 file to use
it with pyxero.

Instructions for doing this are under "Using OpenSSL to split the Xero Entrust certificate":

    http://developer.xero.com/documentation/getting-started/partner-applications/

Once done simply run:

    XERO_CONSUMER_KEY=yourkey \
     XERO_CONSUMER_SECRET=yoursecret \
      XERO_RSA_CERT_KEY_PATH=privatekey.pem \
        XERO_ENTRUST_CERT_PATH=entrust-cert.pem \
          XERO_ENTRUST_PRIVATE_KEY_PATH=entrust-private-nopass.pem \
           python runserver.py

Then open your browser and go to http://localhost:8000/


