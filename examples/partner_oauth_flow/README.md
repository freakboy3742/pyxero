Simple example for the oAuth partner workflow
=============================================

Once you've registered with Xero as a Partner and been approved, you'll start building a Public App.  Once you are ready to share what you've developed, contact Xero to upgrade your public app to partner.

    [Xero Partner Program](http://developer.xero.com/partner/)

Once done simply run:

    XERO_CONSUMER_KEY=yourkey \
     XERO_CONSUMER_SECRET=yoursecret \
      XERO_RSA_CERT_KEY_PATH=privatekey.pem \
       python runserver.py

Then open your browser and go to http://localhost:8000/


