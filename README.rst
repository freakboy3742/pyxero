PyXero
======

PyXero is a Python API for accessing the REST API provided by the `Xero`_
accounting tool.

It allows access to both Public and Private applications.

This code is based off the `sample code provided by Xero`_, which was
contributed by `IRESS Wealth Management`_, and the `XeroPy`_ packaged version of
that code.

This packages differs in three significant was from `XeroPy`_:

 * It uses the popular `requests`_ library (and the `requests-oauthlib`_
   extension) instead of httplib2.

 * It uses the pure-python `PyCrypto`_ library instead of the hard-to-compile
   native M2Crypto wrapper for RSA signing.

 * It has been tested on both Public and Private Xero Applications.


Quickstart:
-----------

In addition to the instructions shown here, you'll need to follow the `Xero
Developer documentation`_ to register your application.

Public Applications
~~~~~~~~~~~~~~~~~~~

Public applications use a 3-step OAuth process.

When you `register your public application with Xero`_, you'll be given a
**Consumer Key** and a **Consumer secret**. These are both strings.

To access the Xero API you must first create some credentials::

    >>> from xero.auth import PublicCredentials
    >>> credentials = PublicCredentials(<consumer_key>, <consumer_secret>)
    >>> print credentials.url
    'http://my.xero.com/.....'

You now direct the user to visit the URL described by `credentials.url`. They
will be asked to log into their Xero account, and then shown a request to
authenticate your request to access the user's account. When the allow access,
they will be directed to a page that gives them a 6-digit verification number.
Put this verifier number into a string, and call `verify()` on the credentials
object::

    >>> credentials.verify(<verifier string>)

This will verify your credentials, and retrieve an access token. You can
then use your credentials to instantiate an instance of the Xero API::

    >>> from xero import Xero
    >>> xero = Xero(credentials)

Public Applications with verification by callback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Public applications can also be validated using a callback URI. If this
approach is used, the user won't be given a verification number. Instead,
when they authorize the OAuth request, their browser will be redirected to
a pre-configured callback URI, which will deliver the validation token
directly to your application.

To use a callback, you must provide a domain as part of your Xero application
registration; then, you provide a URL under that domain as the third argument
when creating the credentials::

    >>> credentials = PublicCredentials(<consumer_key>, <consumer_secret>, <callback_uri>)
    >>> print credentials.url
    'http://my.xero.com/.....'

When the user authorizes access to their Xero account, the `callback_url`
will be called with three GET arguments:

 * `oauth_token`: The oauth_token that this request belongs to

 * `verifier`: The verifier string

 * `org`: An identifier for the organization that is allowing access.

The verifier can then be used to verify the credentials, as with the manual
process.

Reconstructing Public credentials
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Public Applications use a 3-step OAuth process, and if you're doing this in a
web application, you will usually lose the credentials object over the
verification step. This means you need to be able to restore the credentials
object when verification has been provided.

The `state` attribute of a credentials object contains all the details needed
to reconstruct an instance of the credentials::

    >>> saved_state = credentials.state
    >>> print saved_state
    {'consumer_key': '...', 'consumer_secret': '...', ...}

    >>> new_credentials = PublicCredentials(**saved_state)

Private Applications
~~~~~~~~~~~~~~~~~~~~

If using a Private application, you will need to install `PyCrypto`_, a pure
Python cryptographic module. You'll also need to generate an signed RSA
certificate, and submit that certificate as part of registering your
application with Xero. See the `Xero Developer documentation`_ for more
details.

When you `register your private application with Xero`_, you'll be given a
**Consumer Key**. You'll also be given a **Consumer secret** - this can be
ignored.

Using the Private credentials is much simpler than the Public credentials,
because there's no verification step -- verification is managed using RSA
signed API requests::

    >>> from xero import Xero
    >>> from xero.auth import PrivateCredentials
    >>> with open(<path to rsa key file>) as keyfile:
    ...     rsa_key = keyfile.read()
    >>> credentials = PrivateCredentials(<consumer_key>, <rsa_key>)
    >>> xero = Xero(credentials)

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

Using the Xero API
~~~~~~~~~~~~~~~~~~

*This API is a work in progress. At present, there is no wrapper layer
to help create real objects, it just returns dictionaries in the exact
format provided by the Xero API. This will change into a more useful API
before 1.0*

The Xero API object exposes a simple API for retrieving and updating objects.
For example, to deal with contacts::

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

    # Create a new object
    >>> xero.contacts.put([{...contact info...}, {...contact info...}, {...contact info...}])

    # Save an update to an existing object
    >>> c = xero.contacts.get(u'b2b5333a-2546-4975-891f-d71a8a640d23')
    >>> c['Name'] = 'John Smith'
    >>> xero.contacts.save(c)

    # Save multiple objects
    >>> xero.contacts.save([c1, c2])

This same API pattern exists for the following API objects:

 * Accounts
 * Contacts
 * CreditNotes
 * Currencies
 * Invoices
 * Organisation
 * Payments
 * TaxRates
 * TrackingCategories


.. _Xero: http://developer.xero.com
.. _requests: http://python-requests.org
.. _requests-oauthlib: https://github.com/requests/requests-oauthlib
.. _pycrypto: https://www.dlitz.net/software/pycrypto/
.. _Xero Developer documentation: http://developer.xero.com/api-overview/
.. _sample code provided by Xero: http://developer.xero.com/getting-started/code/python/
.. _IRESS Wealth Management: http://www.iress.com.au
.. _XeroPy: https://github.com/fatbox/XeroPy
.. _register your public application with Xero: http://developer.xero.com/api-overview/public-applications/
.. _register your private application with Xero: http://developer.xero.com/api-overview/private-applications/

Contributing
------------

If you're going to run the PyXero test suite, you need to add the following
dependencies to your environment:

    mock >= 1.0

These aren't included in the formal dependencies because they aren't required
for normal operation of PyXero. They're only required for testing purposes.

Once you've installed these dependencies, you can run the test suite by
running the following from the root directory of the project:

    $ python setup.py test

If you find any problems with pyxero, you can log them on `Github Issues`_.
When reporting problems, it's extremely helpful if you can provide
reproduction instructions -- the sequence of calls and/or test data that
can be used to reproduce the issue.

New features or bug fixes can be submitted via a pull request. If you want
your pull request to be merged quickly, make sure you either include
regression test(s) for the behavior you are adding/fixing, or provide a
good explanation of why a regression test isn't possible.

.. _Github Issues: https://github.com/freakboy3742/pyxero/issues
