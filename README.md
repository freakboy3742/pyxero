PyXero
======

[![Build Status](https://travis-ci.org/freakboy3742/pyxero.svg?branch=master)](https://travis-ci.org/freakboy3742/pyxero)

PyXero is a Python API for accessing the REST API provided by the [Xero](http://developer.xero.com)
accounting tool. It allows access to both Public, Private and Partner applications.

## Quickstart:

In addition to the instructions shown here, you'll need to follow the [Xero
Developer documentation](http://developer.xero.com/) to register your application.

### Public Applications

Public applications use a 3-step OAuth process.

When you [register your public application with Xero](http://developer.xero.com/documentation/auth-and-limits/public-applications/), you'll be given a
**Consumer Key** and a **Consumer secret**. These are both strings.

To access the Xero API you must first create some credentials:

```python
>>> from xero.auth import PublicCredentials
>>> credentials = PublicCredentials(<consumer_key>, <consumer_secret>)
>>> print credentials.url
'http://my.xero.com/.....'
```

You now direct the user to visit the URL described by `credentials.url`. They
will be asked to log into their Xero account, and then shown a request to
authenticate your request to access the user's account. When the allow access,
they will be directed to a page that gives them a 6-digit verification number.
Put this verifier number into a string, and call `verify()` on the credentials
object::

```python
>>> credentials.verify(<verifier string>)
```

This will verify your credentials, and retrieve an access token. You can
then use your credentials to instantiate an instance of the Xero API::

```python
>>> from xero import Xero
>>> xero = Xero(credentials)
```

### Public Applications with verification by callback

Public applications can also be validated using a callback URI. If this
approach is used, the user won't be given a verification number. Instead,
when they authorize the OAuth request, their browser will be redirected to
a pre-configured callback URI, which will deliver the validation token
directly to your application.

To use a callback, you must provide a domain as part of your Xero application
registration; then, you provide a URL under that domain as the third argument
when creating the credentials::

```python
>>> credentials = PublicCredentials(<consumer_key>, <consumer_secret>, <callback_uri>)
>>> print credentials.url
'http://my.xero.com/.....'
```

When the user authorizes access to their Xero account, the `callback_url`
will be called with three GET arguments:

* `oauth_token`: The oauth_token that this request belongs to
* `oauth_verifier`: The verifier string
* `org`: An identifier for the organization that is allowing access.

The verifier can then be used to verify the credentials, as with the manual
process.

### Reconstructing Public credentials

Public Applications use a 3-step OAuth process, and if you're doing this in a
web application, you will usually lose the credentials object over the
verification step. This means you need to be able to restore the credentials
object when verification has been provided.

The `state` attribute of a credentials object contains all the details needed
to reconstruct an instance of the credentials::

```python
>>> saved_state = credentials.state
>>> print saved_state
{'consumer_key': '...', 'consumer_secret': '...', ...}

>>> new_credentials = PublicCredentials(**saved_state)
```

### Private Applications

If using a Private application, you will need to install `PyCrypto`, a pure
Python cryptographic module. You'll also need to generate an signed RSA
certificate, and submit that certificate as part of registering your
application with Xero. See the [Xero Developer documentation](http://developer.xero.com/) for more
details.

When you [register your private application with Xero](http://developer.xero.com/documentation/auth-and-limits/private-applications/), you'll be given a
**Consumer Key**. You'll also be given a **Consumer secret** - this can be
ignored.

Using the Private credentials is much simpler than the Public credentials,
because there's no verification step -- verification is managed using RSA
signed API requests::

```python
>>> from xero import Xero
>>> from xero.auth import PrivateCredentials
>>> with open(<path to rsa key file>) as keyfile:
...     rsa_key = keyfile.read()
>>> credentials = PrivateCredentials(<consumer_key>, rsa_key)
>>> xero = Xero(credentials)
```

[Follow these steps](http://developer.xero.com/documentation/api-guides/create-publicprivate-key/) to generate a public/private key pair to sign your requests.  You'll upload your public key when you create your Xero Private app at https://app.xero.com.  You'll use the private key (aka RSA key) to generate your oAuth signature.

The RSA key is a multi-line string that will look something like::

    -----BEGIN RSA PRIVATE KEY-----
    MIICXgIBAAKBgQDWJbmxJjQLGM76sZkk2EhsdpV0Gxtrhzh/wiNBGffa5JHV/Ex4
    ....
    mtXGQjKqsOpuCw7HwgnRQUWKYbaJ3a+yTCFjVwa9keQhDQ==
    -----END RSA PRIVATE KEY-----

You can get this string by either reading the contents of your private key
file into a variable, or storing the key value as a constant. If you choose to
store the key value as a constant, remember two things:

* **DO NOT UNDER ANY CIRCUMSTANCES** check this file into a public
  repository. It is your identity, and anyone with access to this file
  could masquerade as you.

* Make sure there is no leading space before
  the ``-----BEGIN PRIVATE KEY-----`` portion of the string.


### Partner Applications

Partner Application authentication works similarly to the 3-step OAuth used by
Public Applications, but with RSA signed requests and a client-side SSL
certificate which is issued by Xero. Partner OAuth tokens still have a 30 minute
expiry, but can be swapped for a new token at any time.

When you [register your partner application with Xero](http://developer.xero.com/documentation/auth-and-limits/partner-applications/), you'll have a
**Consumer Key**, **Consumer Secret** and **RSA Key**
All three elements are required.


```python
>>> from xero import Xero
>>> from xero.auth import PartnerCredentials
>>> credentials = PartnerCredentials(<consumer_key>, <consumer_secret>,
...                                  <rsa_key>)
>>> xero = Xero(credentials)
```

When using the API over an extended period, you will need to exchange tokens
when they expire.

```python
>>> if credentials.expired():
...     credentials.refresh()
```

**Important**: ``credentials.state`` changes after a token swap. Be sure to persist
the new state.


## Using the Xero API

*This API is a work in progress. At present, there is no wrapper layer
to help create real objects, it just returns dictionaries in the exact
format provided by the Xero API. This will change into a more useful API
before 1.0*

The Xero API object exposes a simple API for retrieving and updating objects.
For example, to deal with contacts::

```python
# Retrieve all contact objects
>>> xero.contacts.all()
[{...contact info...}, {...contact info...}, {...contact info...}, ...]

# Retrieve a specific contact object
>>> xero.contacts.get(u'b2b5333a-2546-4975-891f-d71a8a640d23')
{...contact info...}

# Retrive all contacts updated since 1 Jan 2013
>>> xero.contacts.filter(since=datetime(2013, 1, 1))
[{...contact info...}, {...contact info...}, {...contact info...}]

# Retrive all contacts whose name is 'John Smith'
>>> xero.contacts.filter(Name='John Smith')
[{...contact info...}, {...contact info...}, {...contact info...}]

# Retrive all contacts whose name starts with 'John'
>>> xero.contacts.filter(Name__startswith='John')
[{...contact info...}, {...contact info...}, {...contact info...}]

# Retrive all contacts whose name ends with 'Smith'
>>> xero.contacts.filter(Name__endswith='Smith')
[{...contact info...}, {...contact info...}, {...contact info...}]

# Retrive all contacts whose name starts with 'John' and ends with 'Smith'
>>> xero.contacts.filter(Name__startswith='John', Name__endswith='Smith')
[{...contact info...}, {...contact info...}, {...contact info...}]

# Retrive all contacts whose name contains 'mit'
>>> xero.contacts.filter(Name__contains='mit')
[{...contact info...}, {...contact info...}, {...contact info...}]

# Create a new object
>>> xero.contacts.put({...contact info...})

# Create multiple new objects
>>> xero.contacts.put([{...contact info...}, {...contact info...}, {...contact info...}])

# Save an update to an existing object
>>> c = xero.contacts.get(u'b2b5333a-2546-4975-891f-d71a8a640d23')
>>> c['Name'] = 'John Smith'
>>> xero.contacts.save(c)

# Save multiple objects
>>> xero.contacts.save([c1, c2])
```

Complex filters can be constructed in the Django-way, for example retrieving invoices for a contact::

```python
>>> xero.invoices.filter(Contact_ContactID='83ad77d8-48a7-4f77-9146-e6933b7fb63b')
```

Be careful when dealing with large amounts of data, the Xero API will take an
increasingly long time to respond, or an error will be returned. If a query might
return more than 100 results, you should make use of the ``page`` parameter::

```python
# Grab 100 invoices created after 01-01-2013
>>> xero.invoices.filter(since=datetime(2013, 1, 1), page=1)
```

You can also order the results to be returned::

```python
# Grab contacts ordered by EmailAddress
>>> xero.contacts.filter(order='EmailAddress DESC')
```

For invoices (and other objects that can be retrieved as PDFs), accessing the PDF is done
via setting the Accept header:

```python
# Fetch a PDF
invoice = xero.invoices.get('af722e93-b64f-482d-9955-1b027bfec896', \
    headers={'Accept': 'application/pdf'})
# Stream the PDF to the user (Django specific example)
response = HttpResponse(invoice, content_type='application/pdf')
response['Content-Disposition'] = 'attachment; filename="invoice.pdf"'
return response
```

Download and uploading attachments is supported using the Xero GUID of the relevant object::

```python
# List attachments on a contact
>>> xero.contacts.get_attachments(c['ContactID'])
[{...attachment info...}, {...attachment info...}]

# Attach a PDF to a contact
>>> f = open('form.pdf', 'rb')
>>> xero.contacts.put_attachment(c['ContactID'], 'form.pdf', f, 'application/pdf')
>>> f.close()

>>> xero.contacts.put_attachment_data(c['ContactID'], 'form.pdf', data, 'application/pdf')

# Download an attachment
>>> f = open('form.pdf', 'wb')
>>> xero.contacts.get_attachment(c['ContactID'], 'form.pdf', f)
>>> f.close()

>>> data = xero.contacts.get_attachment_data(c['ContactID'], 'form.pdf')
```

This same API pattern exists for the following API objects:

* Accounts
* Attachments
* BankTransactions
* BankTransfers
* BrandingThemes
* ContactGroups
* Contacts
* CreditNotes
* Currencies
* Employees
* ExpenseClaims
* Invoices
* Items
* Journals
* ManualJournals
* Organisation
* Overpayments
* Payments
* Prepayments
* Purchase Orders
* Receipts
* RepeatingInvoices
* Reports
* TaxRates
* TrackingCategories
* Users


## Tracking Category Options API

As this api diverges somewhat from the 'normal' api and has sub options a special endpoint has been added
to it.

While all the currently available options and tracking categories are returned with xero.trackingcategories.all(),
it doesn't let you create new options on the fly which you may need to do if you need to add these dynamically.

The URLS that are used are generated based on the ID of the TrackingCategory, so these need 'setup' prior to use.

So, lets assume you have a Tracking Category that you've named Region.  Run xero.populate_tracking_categories(),
this will add one or two (xero restricts us to two tracking categories), and this will create two new API objects
called TC%{YourCategoryName} - in this example it'll be called 'TCRegion'.

For example:

```python
>>> xero.populate_tracking_categories()

>>> xero.TCRegion.options.put([{'Name': 'one'}, {'Name':'two'} ]
```

Note: As far as I can tell there is no way to search tracking options using filter, but you should be able to update and
archive these through this api.

## Debugging

While developing its useful to see what the api is submitting to Xero.  By calling the save_or_put method,
you get an idea of the URL its trying to hit and the XML that's being submitted, eg.

```python
>>> xero.TCRegion.options.save_or_put([{'Name': 'one'}, {'Name':'two'} ]

(u'https://api.xero.com/api.xro/2.0/TrackingCategories/your-category-id-will-be-here/Options',
 {},
 u'post',
 {u'xml': u'<Options><Option><Name>one</Name></Option><Option><Name>two</Name></Option></Options>'},
 None,
 False)
```


## Contributing

If you're going to run the PyXero test suite, in addition to the dependencies
for PyXero, you need to add the following dependency to your environment:

    mock >= 1.0

Mock isn't included in the formal dependencies because they aren't required
for normal operation of PyXero. It's only required for testing purposes.

Once you've installed these dependencies, you can run the test suite by
running the following from the root directory of the project:

    $ python setup.py test

If you find any problems with PyXero, you can log them on [Github Issues](https://github.com/freakboy3742/pyxero/issues).
When reporting problems, it's extremely helpful if you can provide
reproduction instructions -- the sequence of calls and/or test data that
can be used to reproduce the issue.

New features or bug fixes can be submitted via a pull request. If you want
your pull request to be merged quickly, make sure you either include
regression test(s) for the behavior you are adding/fixing, or provide a
good explanation of why a regression test isn't possible.

