import requests
from requests_oauthlib import OAuth1
from oauthlib.oauth1 import SIGNATURE_RSA, SIGNATURE_TYPE_AUTH_HEADER
from urlparse import parse_qs
from urllib import urlencode

from .constants import REQUEST_TOKEN_URL, AUTHORIZE_URL, ACCESS_TOKEN_URL
from .exceptions import XeroNotVerified, XeroBadRequest, XeroExceptionUnknown


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
                 oauth_token=None, oauth_token_secret=None):
        """Construct the auth instance.

        Must provide the consumer key and secret.
        A callback URL may be provided as an option. If provided, the
        Xero verification process will redirect to that URL when

        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.callback_uri = callback_uri
        self.verified = verified
        self._oauth = None

        if oauth_token and oauth_token_secret:
            if self.verified:
                # If provided, this is a fully verified set of
                # crednetials. Store the oauth_token and secret
                # and initialize OAuth around those
                self._init_oauth(oauth_token, oauth_token_secret)

            else:
                # If provided, we are reconstructing an initalized
                # (but non-verified) set of public credentials.
                self.oauth_token = oauth_token
                self.oauth_token_secret = oauth_token_secret

        else:
            oauth = OAuth1(
                consumer_key,
                client_secret=self.consumer_secret,
                callback_uri=self.callback_uri
            )

            response = requests.post(url=REQUEST_TOKEN_URL, auth=oauth)

            if response.status_code == 200:
                credentials = parse_qs(response.text)
                self.oauth_token = credentials.get('oauth_token')[0]
                self.oauth_token_secret = credentials.get('oauth_token_secret')[0]
            elif response.status_code == 400 or response.status_code == 401:
                payload = parse_qs(response.text)
                raise XeroBadRequest(
                    payload['oauth_problem'][0],
                    payload['oauth_problem_advice'][0]
                )
            else:
                raise XeroExceptionUnknown(response.text)

    def _init_oauth(self, oauth_token, oauth_token_secret):
        "Store and initialize the OAuth credentials"
        self.oauth_token = oauth_token
        self.oauth_token_secret = oauth_token_secret
        self.verified = True

        self._oauth = OAuth1(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.oauth_token,
            resource_owner_secret=self.oauth_token_secret
        )

    @property
    def state(self):
        """Obtain the useful state of this credentials object so that
        we can reconstruct it independently.
        """
        return dict(
            (attr, getattr(self, attr))
            for attr in (
                'consumer_key', 'consumer_secret', 'callback_uri',
                'verified', 'oauth_token', 'oauth_token_secret'
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
            verifier=verifier
        )

        # Make the verification request, gettiung back an access token
        response = requests.post(url=ACCESS_TOKEN_URL, auth=oauth)

        if response.status_code == 200:
            credentials = parse_qs(response.text)
            # Initialize the oauth credentials
            self._init_oauth(
                credentials.get('oauth_token')[0],
                credentials.get('oauth_token_secret')[0]
            )
        elif response.status_code == 400 or response.status_code == 401:
            payload = parse_qs(response.text)
            raise XeroBadRequest(
                payload['oauth_problem'][0],
                payload['oauth_problem_advice'][0]
            )
        else:
            raise XeroExceptionUnknown(response.text)

    @property
    def url(self):
        "Returns the URL that can be visited to obtain a verifier code"
        return AUTHORIZE_URL + '?' + urlencode({'oauth_token': self.oauth_token})

    @property
    def oauth(self):
        "Returns the requests-compatible OAuth object"
        if self._oauth is None:
            raise XeroNotVerified("Public credentials haven't been verified")
        return self._oauth
