# ChangeLog

## Unreleased

- #225 - Raise XeroUnexpectedResponse when a JSON-expecting call receives a non-JSON 200 response (e.g. an HTML error page served with status 200)
- #431 - Expose the underlying response object (headers, rate-limit info) alongside parsed list data
- #393 - Support idempotent requests via an idempotency key header
- #389 - Allow allocating Prepayments and Overpayments, like CreditNotes; removed OAuth 1.0 examples
- #401 - Corrected `AddToWatchlist` field on Account to be boolean, not string
- #384 - `Manager.save()` now accepts a `summarize_errors` boolean, matching `.put()`
- #381 - Fixed a timesheet XML serialization bug with `NumberOfUnits`
- #392 - Clarified `datetime` import and added a relative-date example in the README

## 0.9.5 (2025-06-05)

- #375 - Add support for allocating credit notes
- #358 - Add support for the `pageSize` argument to queries
- #308 - Include tenant-id when using the Files API
- Dropped support for Python 3.8; added support for Python 3.13 and 3.14

## 0.9.4 (2023-09-30)

- #337 - Added support for JSON-formatted Unauthorised messages
- #344 - Dropped support for Python 3.7
- #339 - Corrected error handling in filtering
- #341 - Added support for object-specific filtering
- #343 - Corrected JSON/XML tagging in PaymentManager
- #325 - Added support for the PKCE OAuth2 login flow
- #321 - Corrected an issue with Content-Type handling when attaching files
- #215 - Added support for saving objects with a specific ID
- #318 - Added support for retrieving the Actions of an Organisation
- #287 - Added support for passing on token scope-change warnings
- #323 - Improved error messages when a rate limit is hit

## 0.9.3 (2021-06-29)

- #291 - Correct representation of boolean fields
- #294 - Correct saving of updated Invoices
- #300 - Add filtering by ID
- #302 - Correct handling of XML body format
- #303 - Removed support for Private Apps
- #304 - Add support for the Payment Services API
- #309 - Allow an (optional) authorization event ID when retrieving tenants
- #310 - Add Python 3.9 support
- #314 - Added support for HTTP429 rate limit handling

## 0.9.2 (2020-03-01)

- #208 - Support the journal date field
- #211 - Improve error handling when an API response is unparsable
- #219 - Corrected declaration of boolean fields on Items
- #222 - Correct the handling of the AmountPaid field
- #232 - Made the API URL configurable
- #245 - Ensure `put_attachment` returns a response.
- #249 - Add support for the Batch Payments API
- #250 - Correct the handling of user agents.
- #254 - Add support for the History API
- #259 - Corrected boolean handling of DiscountEnteredAsPercent
- #265 - Add support for Super Funds to the Payroll API
- #266 - Add support for Payroll object names.
- #269 - Added new endpoints to support the Invoice API
- #271 - Improved example of OAuth flow
- #273 - Add support for the Projects API
- #278 - Added an OAuth2 authentication implementation
- #282 - Add support for the Quotes API

## 0.9.1 (2018-08-27)

- #241 - Added support for Python 3.5-3.7
- #234 - Correct PyJWT pinned version
- #207 - Correct PyJWT pinned version
- #165 - Correct declaration of some Boolean fields

## 0.9.0 (2017-07-05)

- #179 - Change cryptography setup version (thanks João Miguel Neves).
- #170 - Add User-Agent customisation on OAuth related requests.
- #168 - Deprecate Entrust Certificates for Partners API (thanks Sidney Allen).
- #157 - Add PurchaseOrders handling (thanks vadim-pavlov).
- #153 - Add TaxComponents handling (thanks Richard Bell).
- #152/#150 - Improve Xero Exceptions handling (thanks Jarek Glowacki, Craig Handley and Brendan Jurd).
- #151 - Add delete method in BaseManager (thanks Craig Handley).

**Bugfix:**

- #173 - Send Content-Length as string for working attachment uploads (thanks João Neves).
- #154 - Handle wrong date timestamp format received from Xero (thanks Matt Healy).
- #149 - Change Tracking Category structure in Invoices API (thanks Jacob Hansson).
- #142 - Extend BOOLEAN_FIELDS in BaseManager (thanks Alex Burbidge).
- #138 - Indentation fix in BaseManager (thanks Asav Patel).
- #137 - Fix incorrect field parsing with filters (thanks Alexander Rakowski).
- #90/#91 - Pin version of cryptography (thanks Aidan Lister).

## 0.8.0 (2016-03-21)

- Bugfix release; no new features.

## 0.7.0 (2015-07-01)

- Switched from XML parsing to JSON, fixing a number of list-vs-object bugs
- Added examples for Public and Private applications

## 0.6.0 (2015-01-30)

- Added Attachments API support for all objects
- Added support for order, offset and paging
- Added support for filtering and nullable fields
- `filter()` now always returns a list
- Added PartnerApplication support
- Fixed unicode handling issues

## 0.5.2 (2013-07-29)

- Corrected a packaging problem
- Corrected examples in the README

## 0.5.1 (2013-05-31)

- Corrected handling of non-ASCII data in XML responses
- Fixed `Manager.all()`/`Manager.filter()` to accept list results, not just tuples
- Cleaned up exception handling to match Xero docs
- Fixed `setup.py` to work before `dateutil` is installed

## 0.5 (2013-03-28)

- Initial release
