ChangeLog
=========

.. _master:

master (unreleased)
-------------------

.. _v0.9.3:

0.9.3 (2021-06-29)
------------------

    #291 - Correct representation of boolean fields
    #294 - Correct saving of updated Invoices
    #300 - Add filtering by ID
    #302 - Correct handling of XML body format.
    #303 - Removed support for Private Apps
    #304 - Add support for the Payment Services API
    #309 - Allow an (optional) authorization event ID when retrieving tenants
    #310 - Add Python 3.9 support
    #314 - Added support for HTTP429 rate limit handling

.. _v0.9.2:

0.9.2 (2020-03-01)
------------------

    #208 - Support the journal date field
    #211 - Improve error handling when an API response is unparseable
    #219 - Corrected declaration of boolean fields on Items
    #222 - Correct the handling of the AmountPaid field
    #232 - Made the API URL configurable
    #245 - Ensure ``put_attachment`` returns a response.
    #249 - Add support for the Batch Payments API
    #250 - Correct the handling of user agents.
    #254 - Add support for the History API
    #259 - Corrected boolean handling of DiscountEnteredAsPercent
    #265 - Add support for Super Funds to the Payroll API
    #266 - Add support for Payroll object names.
    #269 - Added new endpoints to support the Invoice API
    #271 - Improved example of OAuth flow
    #273 - Add support for the Projects API
    #278 - Added an OAuth2 authentication implementation
    #282 - Add support for the Quotes API

.. _v0.9.1:

0.9.1 (2018-08-27)
------------------

    #241 - Added support for Python 3.5-3.7
    #234 - Correct PyJWT pinned version
    #207 - Correct PyJWT pinned version
    #165 - Correct declaration of some Boolean fields

.. _v0.9.0:

0.9.0 (2017-07-05)
------------------

    - #179 - Change cryptography setup version (thanks João Miguel Neves).
    - #170 - Add User-Agent customisation on OAuth related requests.
    - #168 - Deprecate Entrust Certificates for Partners API (thanks Sidney Allen).
    - #157 - Add PurchaseOrders handling (thanks vadim-pavlov).
    - #153 - Add TaxComponents handling (thanks Richard Bell).
    - #152/#150 - Improve Xero Exceptions handling (thanks Jarek Glowacki, Craig Handley and Brendan Jurd).
    - #151 - Add delete method in BaseManager (thanks Craig Handley).

*Bugfix:*
    - #173 - Send Content-Length as string for working attachment uploads (thanks João Neves).
    - #154 - Handle wrong date timestamp format received from Xero (thanks Matt Healy).
    - #149 - Change Tracking Category structure in Invoices API (thanks Jacob Hansson).
    - #142 - Extend BOOLEAN_FIELDS in BaseManager (thanks Alex Burbidge).
    - #138 - Indentation fix in BaseManager (thanks Asav Patel).
    - #137 - Fix incorrect field parsing with filters (thanks Alexander Rakowski).
    - #90/#91 - Pin version of cryptography (thanks Aidan Lister).

.. _v0.8.0:

0.8.0 (2016-03-21)
------------------
