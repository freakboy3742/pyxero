import base64
import datetime
import hashlib
import http.server
import secrets
import sys
import threading
import webbrowser
from functools import partial
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from oauthlib.oauth1 import SIGNATURE_HMAC, SIGNATURE_RSA, SIGNATURE_TYPE_AUTH_HEADER
from requests_oauthlib import OAuth1, OAuth2, OAuth2Session

from .constants import (
    ACCESS_TOKEN_URL,
    AUTHORIZE_URL,
    REQUEST_TOKEN_URL,
    XERO_BASE_URL,
    XERO_OAUTH2_AUTHORIZE_URL,
    XERO_OAUTH2_CONNECTIONS_URL,
    XERO_OAUTH2_TOKEN_URL,
    XeroScopes,
)
from .exceptions import (
    XeroAccessDenied,
    XeroBadRequest,
    XeroException,
    XeroExceptionUnknown,
    XeroForbidden,
    XeroInternalError,
    XeroNotAvailable,
    XeroNotFound,
    XeroNotImplemented,
    XeroNotVerified,
    XeroRateLimitExceeded,
    XeroUnauthorized,
)
from .utils import resolve_user_agent

OAUTH_EXPIRY_SECONDS = 3600  # Default unless a response reports differently

DEFAULT_SCOPE = [
    XeroScopes.OFFLINE_ACCESS,
    XeroScopes.ACCOUNTING_TRANSACTIONS_READ,
    XeroScopes.ACCOUNTING_CONTACTS_READ,
]


class PrivateCredentials:
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

    def __init__(self, consumer_key, rsa_key, api_url=XERO_BASE_URL):
        self.consumer_key = consumer_key
        self.rsa_key = rsa_key

        self.base_url = api_url

        # Private API uses consumer key as the OAuth token.
        self.oauth_token = consumer_key

        self.oauth = OAuth1(
            self.consumer_key,
            resource_owner_key=self.oauth_token,
            rsa_key=self.rsa_key,
            signature_method=SIGNATURE_RSA,
            signature_type=SIGNATURE_TYPE_AUTH_HEADER,
        )


class PublicCredentials:
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

    def __init__(
        self,
        consumer_key,
        consumer_secret,
        callback_uri=None,
        verified=False,
        oauth_token=None,
        oauth_token_secret=None,
        oauth_expires_at=None,
        oauth_authorization_expires_at=None,
        scope=None,
        user_agent=None,
        api_url=XERO_BASE_URL,
    ):
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
        self.oauth_expires_at = oauth_expires_at
        self.oauth_authorization_expires_at = oauth_authorization_expires_at
        self.scope = scope
        self.user_agent = resolve_user_agent(user_agent)

        self.base_url = api_url
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
                signature_method=self._signature_method,
            )

            url = self.base_url + REQUEST_TOKEN_URL
            headers = {"User-Agent": self.user_agent}
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
            signature_method=self._signature_method,
        )

    def _process_oauth_response(self, response):
        "Extracts the fields from an oauth response"
        if response.status_code == 200:
            credentials = parse_qs(response.text)

            # Initialize the oauth credentials
            self._init_oauth(
                credentials.get("oauth_token")[0],
                credentials.get("oauth_token_secret")[0],
            )

            # If tokens are refreshable, we'll get a session handle
            self.oauth_session_handle = credentials.get("oauth_session_handle", [None])[
                0
            ]

            # Calculate token/auth expiry
            oauth_expires_in = credentials.get(
                "oauth_expires_in", [OAUTH_EXPIRY_SECONDS]
            )[0]
            oauth_authorisation_expires_in = credentials.get(
                "oauth_authorization_expires_in", [OAUTH_EXPIRY_SECONDS]
            )[0]

            self.oauth_expires_at = datetime.datetime.now() + datetime.timedelta(
                seconds=int(oauth_expires_in)
            )
            self.oauth_authorization_expires_at = (
                datetime.datetime.now()
                + datetime.timedelta(seconds=int(oauth_authorisation_expires_in))
            )
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
        return {
            attr: getattr(self, attr)
            for attr in (
                "consumer_key",
                "consumer_secret",
                "callback_uri",
                "verified",
                "oauth_token",
                "oauth_token_secret",
                "oauth_session_handle",
                "oauth_expires_at",
                "oauth_authorization_expires_at",
                "scope",
            )
            if getattr(self, attr) is not None
        }

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
            signature_method=self._signature_method,
        )

        # Make the verification request, gettiung back an access token
        url = self.base_url + ACCESS_TOKEN_URL
        headers = {"User-Agent": self.user_agent}
        response = requests.post(url=url, headers=headers, auth=oauth)
        self._process_oauth_response(response)
        self.verified = True

    @property
    def url(self):
        "Returns the URL that can be visited to obtain a verifier code"
        # The authorize url is always api.xero.com
        query_string = {"oauth_token": self.oauth_token}

        if self.scope:
            query_string["scope"] = self.scope

        url = self.base_url + AUTHORIZE_URL + "?" + urlencode(query_string)
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

        return self.oauth_expires_at <= (
            now + datetime.timedelta(seconds=CONSERVATIVE_SECONDS)
        )


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

    def __init__(
        self,
        consumer_key,
        consumer_secret,
        rsa_key,
        callback_uri=None,
        verified=False,
        oauth_token=None,
        oauth_token_secret=None,
        oauth_expires_at=None,
        oauth_authorization_expires_at=None,
        oauth_session_handle=None,
        scope=None,
        user_agent=None,
        api_url=XERO_BASE_URL,
        **kwargs,
    ):
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
        self.oauth_expires_at = oauth_expires_at
        self.oauth_authorization_expires_at = oauth_authorization_expires_at
        self.scope = scope
        self.user_agent = resolve_user_agent(user_agent)

        self._signature_method = SIGNATURE_RSA
        self.base_url = api_url

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
            signature_method=self._signature_method,
        )

        # Make the verification request, getting back an access token
        headers = {"User-Agent": self.user_agent}
        params = {"oauth_session_handle": self.oauth_session_handle}
        response = requests.post(
            url=self.base_url + ACCESS_TOKEN_URL,
            params=params,
            headers=headers,
            auth=oauth,
        )
        self._process_oauth_response(response)


class OAuth2Credentials:
    """An object wrapping the 3-step OAuth2.0 process for Xero API access.

        For detailed documentation see README.md.
    Usage:

     1) Construct an `OAuth2Credentials` instance:
        >>> credentials = OAuth2Credentials(client_id, client_secret,
        >>>                                 callback_uri=callback_uri, scope=scope)

     2) Generate a unique authentication URL and visit it:
        >>> credentials.generate_url()

        The user will be redirected to a URL in the form:
        https://example.com/oauth/xero/callback/?code=0123456789&scope=openid%20profile
        &state=87784234sdf5ds8ad546a8sd545ss6

     3) Verify the credentials using the full URL redirected to, including querystring:
        >>> credentials.verify(full_url_with_querystring)

     4) Use the credentials. It is usually necessary to set the tenant_id (Xero
        organisation id) to specify the organisation against which the queries should
        run:
        >>> from xero import Xero
        >>> credentials.set_default_tenant()
        >>> xero = Xero(credentials)
        >>> xero.contacts.all()
        ...

        To use a different organisation, set credentials.tenant_id:
        >>> tenants = credentials.get_tenants()
        >>> credentials.tenant_id = tenants[1]['tenantId']

     5) If a refresh token is available, it can be used to generate a new token:
        >>> if credentials.expired():
        >>>     credentials.refresh()

        Note that in order for tokens to be refreshable, Xero API requires
        `offline_access` to be included in the scope.
    """

    def __init__(
        self,
        client_id,
        client_secret,
        callback_uri=None,
        auth_state=None,
        auth_secret=None,
        token=None,
        scope=None,
        tenant_id=None,
        user_agent=None,
        relax_token_scope=False,
    ):
        from xero import __version__ as VERSION

        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_uri = callback_uri
        self.auth_state = auth_state
        self.token = None
        self.tenant_id = tenant_id  # Used by BaseManager
        self._oauth = None
        self.scope = scope or DEFAULT_SCOPE[:]
        self.relax_token_scope = relax_token_scope

        if user_agent is None:
            self.user_agent = (
                "pyxero/%s " % VERSION + requests.utils.default_user_agent()
            )
        else:
            self.user_agent = user_agent

        self.base_url = XERO_BASE_URL  # Used by BaseManager
        self._init_credentials(token, auth_secret)

    def _init_credentials(self, token, auth_secret):
        """
        Depending on the state passed in, get self._oauth up and running.
        """
        if token:
            self._init_oauth(token)
        elif auth_secret and self.auth_state:
            self.verify(auth_secret)

    def _init_oauth(self, token):
        """Set self._oauth for use by the xero client."""
        self.token = token
        if token:
            self._oauth = OAuth2(client_id=self.client_id, token=self.token)

    @property
    def state(self):
        """Obtain the useful state of this credentials object so that
        we can reconstruct it independently.
        """
        return {
            attr: getattr(self, attr)
            for attr in (
                "client_id",
                "client_secret",
                "callback_uri",
                "auth_state",
                "token",
                "scope",
                "tenant_id",
                "user_agent",
            )
            if getattr(self, attr) is not None
        }

    def verify(self, auth_secret):
        """Verify and return OAuth2 token."""
        session = OAuth2Session(
            self.client_id,
            state=self.auth_state,
            scope=self.scope,
            redirect_uri=self.callback_uri,
        )
        try:
            token = session.fetch_token(
                XERO_OAUTH2_TOKEN_URL,
                client_secret=self.client_secret,
                authorization_response=auth_secret,
                headers=self.headers,
            )
        # Various different exceptions may be raised, so pass the exception
        # through as XeroAccessDenied
        except Exception as e:
            # oauthlib raises a warning when returned token scope
            # is different from the client scope
            if self.relax_token_scope and isinstance(e, Warning):
                session.token = e.token
            else:
                raise XeroAccessDenied(e)
        self._init_oauth(token)

    def generate_url(self):
        """Get the authorization url. This will also set `self.auth_state` to a
        random string if it has not already been set.
        """
        session = OAuth2Session(
            self.client_id, scope=self.scope, redirect_uri=self.callback_uri
        )
        url, self.auth_state = session.authorization_url(
            XERO_OAUTH2_AUTHORIZE_URL, state=self.auth_state
        )
        return url

    @property
    def oauth(self):
        """Return the requests-compatible OAuth object"""
        if self._oauth is None:
            raise XeroNotVerified("OAuth credentials haven't been verified")
        return self._oauth

    @property
    def headers(self):
        return {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "User-Agent": self.user_agent,
        }

    @property
    def expires_at(self):
        """Return the expires_at value from the token as a UTC datetime."""
        if sys.version_info < (3, 11):
            return datetime.datetime.utcfromtimestamp(self.token["expires_at"])
        else:
            return datetime.datetime.fromtimestamp(
                self.token["expires_at"], datetime.UTC
            )

    def expired(self, seconds=30, now=None):
        """Check if the token has expired yet.
        :param seconds: the minimum number of seconds allowed before expiry.
        """
        if now is None:
            if sys.version_info < (3, 11):
                now = datetime.datetime.utcnow()
            else:
                now = datetime.datetime.now(datetime.UTC)

        # Allow a bit of time for clock differences and round trip times
        # to prevent false negatives. If users want the precise expiry,
        # they can use self.expires_at.
        return (self.expires_at - now) < datetime.timedelta(seconds=seconds)

    def refresh(self):
        """Obtain a refreshed token. Note that `offline_access` must be
        included in scope in order for a token to be refreshable.
        """
        if not self.token:
            raise XeroException(None, "Cannot refresh token, no token is present.")
        elif not self.client_secret:
            raise XeroException(
                None, "Cannot refresh token, " "client_secret must be supplied."
            )
        elif not self.token.get("refresh_token"):
            raise XeroException(
                None,
                "Token cannot be refreshed, was " "`offline_access` included in scope?",
            )
        session = OAuth2Session(
            client_id=self.client_id, scope=self.scope, token=self.token
        )
        auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
        token = session.refresh_token(
            XERO_OAUTH2_TOKEN_URL, auth=auth, headers=self.headers
        )
        self._init_oauth(token)
        return token

    def get_tenants(self, auth_event_id=None):
        """
        Get the list of tenants (Xero Organisations) to which this token grants access.

        Optionally, you may pass a UUID as auth_event_id that will be used to limit to
        only those tenants that were authorised in that authorisation event.
        """
        connection_url = self.base_url + XERO_OAUTH2_CONNECTIONS_URL

        if auth_event_id:
            connection_url += "?authEventId=" + auth_event_id

        response = requests.get(connection_url, auth=self.oauth, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            self._handle_error_response(response)

    def set_default_tenant(self):
        """A quick way to set the tenant to the first in the list of available
        connections.
        """
        try:
            self.tenant_id = self.get_tenants()[0]["tenantId"]
        except IndexError:
            raise XeroException(
                None,
                "This app is not authorised to access any Xero Organisations. Did the "
                "scopes requested include access to organisation data, or has access "
                "to the organisation(s) been removed?",
            )

    @staticmethod
    def _handle_error_response(response):
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


class PKCEAuthReceiver(http.server.BaseHTTPRequestHandler):
    """This is an http request processsor for server running on localhost,
    used by the PKCE auth system.
    Xero will redirect the browser after auth, from which we
    can collect the toke Xero provides.

    You can subclass this and override the `send_error_page` and
    `send_access_ok` methods to customise the sucess and failure
    pages displayed in the browser.
    """

    def __init__(self, credmanager, *args, **kwargs):
        self.credmanager = credmanager
        super().__init__(*args, **kwargs)

    @staticmethod
    def close_server(s):
        s.shutdown()

    def do_GET(self, *args):
        request = urlparse(self.path)
        params = parse_qs(request.query)

        if request.path == "/callback":
            self.credmanager.verify_url(params, self)
        else:
            self.send_error_page("Unknown endpoint")

    def send_error_page(self, error):
        """Display an Error page.
        Override this for a custom page.
        """
        print("Error:", error)

    def send_access_ok(self):
        """Display a success page"
        Override this to provide a custom page.
        """
        print("LOGIN SUCCESS")
        self.shutdown()

    def shutdown(self):
        """Start shutdowning our server and return immediately"""
        # Launch a thread to close our socket cleanly.
        threading.Thread(
            target=self.__class__.close_server, args=(self.server,)
        ).start()


class OAuth2PKCECredentials(OAuth2Credentials):
    """An object wrapping the PKCE credential flow for Xero access.

    Usage:
      1) Construct an `OAuth2Credentials` instance:

        >>> from xero.auth import OAuth2PKCECredentials
        >>> credentials = OAuth2Credentials(client_id,None, port=8080,
                                            scope=scope)

        A webserver will be setup to listen on the provded port
        number which is used for the Auth callback.

      2) Send the login request.
        >>> credentials.logon()

        This will open a browser window which will naviage to a Xero
        login page. The Use should grant your application access (or not),
        and will be redirected to a locally running webserver to capture
        the auth tokens.


      3) Use the credentials. It is usually necessary to set the tenant_id (Xero
         organisation id) to specify the organisation against which the queries should
         run:
         >>> from xero import Xero
         >>> credentials.set_default_tenant()
         >>> xero = Xero(credentials)
         >>> xero.contacts.all()
        ...

         To use a different organisation, set credentials.tenant_id:
         >>> tenants = credentials.get_tenants()
         >>> credentials.tenant_id = tenants[1]['tenantId']

      4) If a refresh token is available, it can be used to generate a new token:
         >>> if credentials.expired():
         >>>     credentials.refresh()

        Note that in order for tokens to be refreshable, Xero API requires
        `offline_access` to be included in the scope.

    :param port: the port the local webserver will listen ro
    :param verifier: (optional) a string verifier token if not
                     provided the module will generate it's own
    :param request_handler: An HTTP request handler class. This will
                            be used to handler the callback request. If
                            you wish to customise your error page, this is
                            where you pass in you custom class.
    :param callback_uri: Allow customisation of the callback uri. Only
                         useful if you've customised the request_handler
                         to match.

    :param scope: Inhereited from Oath2Credentials.
    """

    def __init__(self, *args, **kwargs):
        self.port = kwargs.pop("port", 8080)
        # Xero requires between 43 adn 128 bytes, it fails
        # with invlaid grant if this is not long enough
        self.verifier = kwargs.pop("verifier", secrets.token_urlsafe(64))
        self.handler_kls = kwargs.pop("request_handler", PKCEAuthReceiver)
        self.error = None
        if isinstance(self.verifier, str):
            self.verifier = self.verifier.encode("ascii")

        kwargs.setdefault("callback_uri", f"http://localhost:{self.port}/callback")
        super().__init__(*args, **kwargs)

    def logon(self):
        """Launch PKCE auth process and wait for completion"""
        challenge = str(
            base64.urlsafe_b64encode(hashlib.sha256(self.verifier).digest())[:-1],
            "ascii",
        )
        url_base = super().generate_url()
        webbrowser.open(
            f"{url_base}&code_challenge={challenge}&" "code_challenge_method=S256"
        )
        self.wait_for_callback()

    def wait_for_callback(self):
        listen_to = ("", self.port)
        s = http.server.HTTPServer(listen_to, partial(self.handler_kls, self))
        s.serve_forever()
        if self.error:
            raise self.error

    def verify_url(self, params, reqhandler):
        """Used to verify the parameters xero returns in the
        redirect callback"""
        error = params.get("error", None)
        if error:
            self.handle_error(error, reqhandler)
            return

        if params["state"][0] != self.state["auth_state"]:
            self.handle_error("State Mismatch", reqhandler)
            return

        code = params.get("code", None)
        if code:
            try:
                self.get_token(code[0])
            except Exception as e:
                self.error = e
                reqhandler.send_error_page(str(e))
                reqhandler.shutdown()

            reqhandler.send_access_ok()

    def get_token(self, code):
        # Does the third leg, to get the actual auth token from Xero,
        # once the authentication has been 'approved' by the user
        resp = requests.post(
            url=XERO_OAUTH2_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "redirect_uri": self.callback_uri,
                "code": code,
                "code_verifier": self.verifier,
            },
        )
        respdata = resp.json()
        error = respdata.get("error", None)
        if error:
            raise XeroAccessDenied(error)

        self._init_oauth(respdata)

    def handle_error(self, msg, handler):
        self.error = RuntimeError(msg)
        handler.send_error_page(msg)
        handler.shutdown()
