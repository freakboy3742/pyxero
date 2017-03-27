from __future__ import unicode_literals

import datetime
import requests

from oauthlib.oauth1 import (
    SIGNATURE_RSA, SIGNATURE_TYPE_AUTH_HEADER, SIGNATURE_HMAC
)
from requests_oauthlib import OAuth1
from six.moves.urllib.parse import urlencode, parse_qs

from .constants import (
    XERO_BASE_URL, REQUEST_TOKEN_URL, AUTHORIZE_URL, ACCESS_TOKEN_URL
)
from .exceptions import (
    XeroBadRequest, XeroException, XeroExceptionUnknown, XeroForbidden,
    XeroInternalError, XeroNotAvailable, XeroNotFound, XeroNotImplemented,
    XeroNotVerified, XeroRateLimitExceeded, XeroUnauthorized
)


OAUTH_EXPIRY_SECONDS = 3600 # Default unless a response reports differently

class PrivateCredentials(object):
    """An object wrapping the 2-step OAuth process for Private Xero API access.

    Usage:

     1) Construct a PrivateCredentials() instance:

        >>> from xero.auth import PrivateCredentials
        >>> credentials = PrivateCredentials(<consumer_key>, <rsa_key>)

        rsa_key should be a multi-line string, starting with:

            -----BEGIN RSA PRIVATE KEY-----\n

     2) Use the credentials:

        >>> from xero import Xero
        >>> xero = Xero(credentials)
        >>> xero.contacts.all()
        ...
    """
    def __init__(self, consumer_key, rsa_key):
        self.consumer_key = consumer_key
        self.rsa_key = rsa_key

        self.base_url = XERO_BASE_URL

        # Private API uses consumer key as the OAuth token.
        self.oauth_token = consumer_key

        self.oauth = OAuth1(
            self.consumer_key,
            resource_owner_key=self.oauth_token,
            rsa_key=self.rsa_key,
            signature_method=SIGNATURE_RSA,
            signature_type=SIGNATURE_TYPE_AUTH_HEADER,
        )


class PublicCredentials(object):
    """An object wrapping the 3-step OAuth process for Public Xero API access.

    Usage:

     1) Construct a PublicCredentials() instance:

        >>> from xero import PublicCredentials
        >>> credentials = PublicCredentials(<consumer_key>, <consumer_secret>)

     2) Visit the authentication URL:

        >>> credentials.url

        If a callback URI was provided (e.g., https://example.com/oauth),
        the user will be redirected to a URL of the form:

        https://example.com/oauth?oauth_token=<token>&oauth_verifier=<verifier>&org=<organization ID>

        from which the verifier can be extracted. If no callback URI is
        provided, the verifier will be shown on the screen, and must be
        manually entered by the user.

     3) Verify the instance:

        >>> credentials.verify(<verifier string>)

     4) Use the credentials.

        >>> from xero import Xero
        >>> xero = Xero(credentials)
        >>> xero.contacts.all()
        ...
    """
    def __init__(self, consumer_key, consumer_secret,
                 callback_uri=None, verified=False,
                 oauth_token=None, oauth_token_secret=None,
                 oauth_expires_at=None, oauth_authorization_expires_at=None,
                 scope=None, user_agent=None):
        """Construct the auth instance.

        Must provide the consumer key and secret.
        A callback URL may be provided as an option. If provided, the
        Xero verification process will redirect to that URL when

        """
        from xero import __version__ as VERSION
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.callback_uri = callback_uri
        self.verified = verified
        self._oauth = None
        self.oauth_expires_at = oauth_expires_at
        self.oauth_authorization_expires_at = oauth_authorization_expires_at
        self.scope = scope

        if user_agent is None:
            self.user_agent = 'pyxero/%s ' % VERSION + requests.utils.default_user_agent()
        else:
            self.user_agent = user_agent

        self.base_url = XERO_BASE_URL
        self._signature_method = SIGNATURE_HMAC

        # These are not strictly used by Public Credentials, but
        # are reserved for use by other credentials (i.e. Partner)
        self.rsa_key = None
        self.oauth_session_handle = None

        self._init_credentials(oauth_token, oauth_token_secret)

    def _init_credentials(self, oauth_token, oauth_token_secret):
        "Depending on the state passed in, get self._oauth up and running"
        if oauth_token and oauth_token_secret:
            if self.verified:
                # If provided, this is a fully verified set of
                # credentials. Store the oauth_token and secret
                # and initialize OAuth around those
                self._init_oauth(oauth_token, oauth_token_secret)

            else:
                # If provided, we are reconstructing an initalized
                # (but non-verified) set of public credentials.
                self.oauth_token = oauth_token
                self.oauth_token_secret = oauth_token_secret

        else:
            # This is a brand new set of credentials - we need to generate
            # an oauth token so it's available for the url property.
            oauth = OAuth1(
                self.consumer_key,
                client_secret=self.consumer_secret,
                callback_uri=self.callback_uri,
                rsa_key=self.rsa_key,
                signature_method=self._signature_method
            )

            url = self.base_url + REQUEST_TOKEN_URL
            headers = {'User-Agent': self.user_agent}
            response = requests.post(url=url, headers=headers, auth=oauth)
            self._process_oauth_response(response)

    def _init_oauth(self, oauth_token, oauth_token_secret):
        "Store and initialize a verified set of OAuth credentials"
        self.oauth_token = oauth_token
        self.oauth_token_secret = oauth_token_secret

        self._oauth = OAuth1(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.oauth_token,
            resource_owner_secret=self.oauth_token_secret,
            rsa_key=self.rsa_key,
            signature_method=self._signature_method
        )

    def _process_oauth_response(self, response):
        "Extracts the fields from an oauth response"
        if response.status_code == 200:
            credentials = parse_qs(response.text)

            # Initialize the oauth credentials
            self._init_oauth(
                credentials.get('oauth_token')[0],
                credentials.get('oauth_token_secret')[0]
            )

            # If tokens are refreshable, we'll get a session handle
            self.oauth_session_handle = credentials.get(
                    'oauth_session_handle', [None])[0]

            # Calculate token/auth expiry
            oauth_expires_in = credentials.get(
                    'oauth_expires_in',
                    [OAUTH_EXPIRY_SECONDS])[0]
            oauth_authorisation_expires_in = credentials.get(
                    'oauth_authorization_expires_in',
                    [OAUTH_EXPIRY_SECONDS])[0]

            self.oauth_expires_at = datetime.datetime.now() + \
                                    datetime.timedelta(seconds=int(
                                        oauth_expires_in))
            self.oauth_authorization_expires_at = \
                                    datetime.datetime.now() + \
                                    datetime.timedelta(seconds=int(
                                        oauth_authorisation_expires_in))
        else:
            self._handle_error_response(response)

    def _handle_error_response(self, response):
        if response.status_code == 400:
            raise XeroBadRequest(response)

        elif response.status_code == 401:
            raise XeroUnauthorized(response)

        elif response.status_code == 403:
            raise XeroForbidden(response)

        elif response.status_code == 404:
            raise XeroNotFound(response)

        elif response.status_code == 500:
            raise XeroInternalError(response)

        elif response.status_code == 501:
            raise XeroNotImplemented(response)

        elif response.status_code == 503:
            # Two 503 responses are possible. Rate limit errors
            # return encoded content; offline errors don't.
            # If you parse the response text and there's nothing
            # encoded, it must be a not-available error.
            payload = parse_qs(response.text)
            if payload:
                raise XeroRateLimitExceeded(response, payload)
            else:
                raise XeroNotAvailable(response)
        else:
            raise XeroExceptionUnknown(response)

    @property
    def state(self):
        """Obtain the useful state of this credentials object so that
        we can reconstruct it independently.
        """
        return dict(
            (attr, getattr(self, attr))
            for attr in (
                'consumer_key', 'consumer_secret', 'callback_uri',
                'verified', 'oauth_token', 'oauth_token_secret',
                'oauth_session_handle', 'oauth_expires_at',
                'oauth_authorization_expires_at', 'scope'
            )
            if getattr(self, attr) is not None
        )

    def verify(self, verifier):
        "Verify an OAuth token"

        # Construct the credentials for the verification request
        oauth = OAuth1(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.oauth_token,
            resource_owner_secret=self.oauth_token_secret,
            verifier=verifier,
            rsa_key=self.rsa_key,
            signature_method=self._signature_method
        )

        # Make the verification request, gettiung back an access token
        url = self.base_url + ACCESS_TOKEN_URL
        headers = {'User-Agent': self.user_agent}
        response = requests.post(url=url, headers=headers, auth=oauth)
        self._process_oauth_response(response)
        self.verified = True

    @property
    def url(self):
        "Returns the URL that can be visited to obtain a verifier code"
        # The authorize url is always api.xero.com
        query_string = {'oauth_token': self.oauth_token}

        if self.scope:
            query_string['scope'] = self.scope

        url = XERO_BASE_URL + AUTHORIZE_URL + '?' + \
              urlencode(query_string)
        return url

    @property
    def oauth(self):
        "Returns the requests-compatible OAuth object"
        if self._oauth is None:
            raise XeroNotVerified("OAuth credentials haven't been verified")
        return self._oauth

    def expired(self, now=None):
        if now is None:
            now = datetime.datetime.now()

        # Credentials states from older versions might not have
        # oauth_expires_at available
        if self.oauth_expires_at is None:
            raise XeroException(None, "Expiry time is not available")

        # Allow a bit of time for clock differences and round trip times
        # to prevent false negatives. If users want the precise expiry,
        # they can use self.oauth_expires_at
        CONSERVATIVE_SECONDS = 30

        return self.oauth_expires_at <= \
               (now + datetime.timedelta(seconds=CONSERVATIVE_SECONDS))

class PartnerCredentials(PublicCredentials):
    """An object wrapping the 3-step OAuth process for Partner Xero API access.

    Usage is very similar to Public Credentials with the following changes:

     1) You'll need to pass the private key for your RSA certificate.

        >>> rsa_key = "-----BEGIN RSA PRIVATE KEY----- ..."

     2) Once a token has expired, you can refresh it to get another 30 mins

        >>> credentials = PartnerCredentials(**state)
        >>> if credentials.expired():
                credentials.refresh()

     3) Authorization expiry and token expiry become different things.

        oauth_expires_at tells when the current token expires (~30 min window)

        oauth_authorization_expires_at tells when the overall access
        permissions expire (~10 year window)
    """
    def __init__(self, consumer_key, consumer_secret, rsa_key,
                 callback_uri=None, verified=False,
                 oauth_token=None, oauth_token_secret=None,
                 oauth_expires_at=None, oauth_authorization_expires_at=None,
                 oauth_session_handle=None, scope=None, user_agent=None,
                 **kwargs):
        """Construct the auth instance.

        Must provide the consumer key and secret.
        A callback URL may be provided as an option. If provided, the
        Xero verification process will redirect to that URL when

        """
        from xero import __version__ as VERSION
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.callback_uri = callback_uri
        self.verified = verified
        self._oauth = None
        self.oauth_expires_at = oauth_expires_at
        self.oauth_authorization_expires_at = oauth_authorization_expires_at
        self.scope = scope
        if user_agent is None:
            self.user_agent = 'pyxero/%s ' % VERSION + requests.utils.default_user_agent()
        else:
            self.user_agent = user_agent

        self._signature_method = SIGNATURE_RSA
        self.base_url = XERO_BASE_URL

        self.rsa_key = rsa_key
        self.oauth_session_handle = oauth_session_handle

        self._init_credentials(oauth_token, oauth_token_secret)

    def refresh(self):
        "Refresh an expired token"

        # Construct the credentials for the verification request
        oauth = OAuth1(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.oauth_token,
            resource_owner_secret=self.oauth_token_secret,
            rsa_key=self.rsa_key,
            signature_method=self._signature_method
        )

        # Make the verification request, getting back an access token
        headers = {'User-Agent': self.user_agent}
        params = {'oauth_session_handle': self.oauth_session_handle}
        response = requests.post(url=self.base_url + ACCESS_TOKEN_URL,
                params=params, headers=headers, auth=oauth)
        self._process_oauth_response(response)
