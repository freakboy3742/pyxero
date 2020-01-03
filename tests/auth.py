import unittest
import json
import time

from datetime import datetime, timedelta
from mock import patch, Mock
from six.moves.urllib.parse import urlparse, parse_qs

from xero.auth import PublicCredentials, PartnerCredentials, OAuth2Credentials
from xero.exceptions import (XeroException, XeroNotVerified, XeroUnauthorized,
                             XeroAccessDenied, XeroTenantIdNotSet)
from xero.constants import OAUTH2_AUTHORIZE_URL
from xero.api import Xero


class PublicCredentialsTest(unittest.TestCase):
    @patch('requests.post')
    def test_initial_constructor(self, r_post):
        "Initial construction causes a requst to get a request token"
        r_post.return_value = Mock(
            status_code=200,
            text='oauth_token=token&oauth_token_secret=token_secret'
        )

        credentials = PublicCredentials(
            consumer_key='key',
            consumer_secret='secret',
            scope='payroll.endpoint'
        )

        # A HTTP request was made
        self.assertTrue(r_post.called)

        state = credentials.state

        # Expiry times should be calculated
        self.assertIsNotNone(state.pop("oauth_authorization_expires_at"))
        self.assertIsNotNone(state.pop("oauth_expires_at"))

        self.assertEqual(state, {
            'consumer_key': 'key',
            'consumer_secret': 'secret',
            'oauth_token': 'token',
            'oauth_token_secret': 'token_secret',
            'verified': False,
            'scope': 'payroll.endpoint'
        })

    @patch('requests.post')
    def test_bad_credentials(self, r_post):
        "Initial construction with bad credentials raises an exception"
        r_post.return_value = Mock(
            status_code=401,
            text='oauth_problem=consumer_key_unknown&oauth_problem_advice=Consumer%20key%20was%20not%20recognised'
        )

        with self.assertRaises(XeroUnauthorized):
            PublicCredentials(
                consumer_key='unknown',
                consumer_secret='unknown'
            )

    @patch('requests.post')
    def test_unvalidated_constructor(self, r_post):
        "Credentials with an unverified request token can be constructed"
        credentials = PublicCredentials(
            consumer_key='key',
            consumer_secret='secret',
            oauth_token='token',
            oauth_token_secret='token_secret',
        )

        self.assertEqual(credentials.state, {
            'consumer_key': 'key',
            'consumer_secret': 'secret',
            'oauth_token': 'token',
            'oauth_token_secret': 'token_secret',
            'verified': False
        })

        # No HTTP requests were made
        self.assertFalse(r_post.called)

    @patch('requests.post')
    def test_validated_constructor(self, r_post):
        "A validated set of credentials can be reconstructed"
        credentials = PublicCredentials(
            consumer_key='key',
            consumer_secret='secret',
            oauth_token='validated_token',
            oauth_token_secret='validated_token_secret',
            verified=True
        )

        self.assertEqual(credentials.state, {
            'consumer_key': 'key',
            'consumer_secret': 'secret',
            'oauth_token': 'validated_token',
            'oauth_token_secret': 'validated_token_secret',
            'verified': True
        })

        try:
            credentials.oauth
        except XeroNotVerified:
            self.fail('Credentials should have been verified')

        # No HTTP requests were made
        self.assertFalse(r_post.called)

    @patch('requests.post')
    def test_url(self, r_post):
        "The request token URL can be obtained"
        r_post.return_value = Mock(
            status_code=200,
            text='oauth_token=token&oauth_token_secret=token_secret'
        )

        credentials = PublicCredentials(
            consumer_key='key',
            consumer_secret='secret'
        )

        self.assertEqual(credentials.url, 'https://api.xero.com/oauth/Authorize?oauth_token=token')

    @patch('requests.post')
    def test_url_with_scope(self, r_post):
        "The request token URL includes the scope parameter"
        r_post.return_value = Mock(
            status_code=200,
            text='oauth_token=token&oauth_token_secret=token_secret'
        )

        credentials = PublicCredentials(
            consumer_key='key',
            consumer_secret='secret',
            scope="payroll.endpoint"
        )

        self.assertIn('scope=payroll.endpoint', credentials.url)

    @patch('requests.post')
    def test_verify(self, r_post):
        "Unverfied credentials can be verified"
        r_post.return_value = Mock(
            status_code=200,
            text='oauth_token=verified_token&oauth_token_secret=verified_token_secret'
        )

        credentials = PublicCredentials(
            consumer_key='key',
            consumer_secret='secret',
            oauth_token='token',
            oauth_token_secret='token_secret',
        )

        credentials.verify('verifier')

        # A HTTP request was made
        self.assertTrue(r_post.called)

        state = credentials.state

        # Expiry times should be calculated
        self.assertIsNotNone(state.pop("oauth_authorization_expires_at"))
        self.assertIsNotNone(state.pop("oauth_expires_at"))

        self.assertEqual(state, {
            'consumer_key': 'key',
            'consumer_secret': 'secret',
            'oauth_token': 'verified_token',
            'oauth_token_secret': 'verified_token_secret',
            'verified': True
        })

        try:
            credentials.oauth
        except XeroNotVerified:
            self.fail('Credentials should have been verified')

    @patch('requests.post')
    def test_verify_failure(self, r_post):
        "If verification credentials are bad, an error is raised"
        r_post.return_value = Mock(
            status_code=401,
            text='oauth_problem=bad_verifier&oauth_problem_advice=The consumer was denied access to this resource.'
        )

        credentials = PublicCredentials(
            consumer_key='key',
            consumer_secret='secret',
            oauth_token='token',
            oauth_token_secret='token_secret',
        )

        with self.assertRaises(XeroUnauthorized):
            credentials.verify('badverifier')

        with self.assertRaises(XeroNotVerified):
            credentials.oauth

    def test_expired(self):
        "Expired credentials are correctly detected"
        now = datetime(2014, 1, 1, 12, 0, 0)
        soon = now + timedelta(minutes=30)

        credentials = PublicCredentials(
            consumer_key='key',
            consumer_secret='secret',
            oauth_token='token',
            oauth_token_secret='token_secret',
        )

        # At this point, oauth_expires_at isn't set
        with self.assertRaises(XeroException):
            credentials.expired(now)

        # Not yet expired
        credentials.oauth_expires_at = soon
        self.assertFalse(credentials.expired(now=now))

        # Expired
        self.assertTrue(credentials.expired(now=soon))


class PartnerCredentialsTest(unittest.TestCase):
    @patch('requests.post')
    def test_initial_constructor(self, r_post):
        "Initial construction causes a request to get a request token"
        r_post.return_value = Mock(
            status_code=200,
            text='oauth_token=token&oauth_token_secret=token_secret'
        )

        credentials = PartnerCredentials(
            consumer_key='key',
            consumer_secret='secret',
            rsa_key='abc',
            scope='payroll.endpoint'
        )

        # A HTTP request was made
        self.assertTrue(r_post.called)

        state = credentials.state

        # Expiry times should be calculated
        self.assertIsNotNone(state.pop("oauth_authorization_expires_at"))
        self.assertIsNotNone(state.pop("oauth_expires_at"))

        self.assertEqual(state, {
            'consumer_key': 'key',
            'consumer_secret': 'secret',
            'oauth_token': 'token',
            'oauth_token_secret': 'token_secret',
            'verified': False,
            'scope': 'payroll.endpoint'
        })

    @patch('requests.post')
    def test_refresh(self, r_post):
        "Refresh function gets a new token"
        r_post.return_value = Mock(
            status_code=200,
            text='oauth_token=token2&oauth_token_secret=token_secret2&oauth_session_handle=session'
        )

        credentials = PartnerCredentials(
            consumer_key='key',
            consumer_secret='secret',
            rsa_key="key",
            oauth_token='token',
            oauth_token_secret='token_secret',
            verified=True
        )

        credentials.refresh()

        # Expiry times should be calculated
        state = credentials.state
        self.assertIsNotNone(state.pop("oauth_authorization_expires_at"))
        self.assertIsNotNone(state.pop("oauth_expires_at"))

        self.assertEqual(state, {
            'consumer_key': 'key',
            'consumer_secret': 'secret',
            'oauth_token': 'token2',
            'oauth_token_secret': 'token_secret2',
            'oauth_session_handle': 'session',
            'verified': True
        })


class OAuth2CredentialsTest(unittest.TestCase):
    callback_uri = 'https://myapp.example.com/xero/auth/callback/'

    def setUp(self):
        super(OAuth2CredentialsTest, self).setUp()
        # Create an expired token to be used by tests
        self.expired_token = {'access_token': '1234567890',
                              'expires_in': 1800,
                              'token_type': 'Bearer',
                              'refresh_token': '0987654321',
                              # 'expires_at': datetime.utcnow().timestamp()}
                              'expires_at': time.time()}

    def test_authorisation_url_and_random_state(self):
        credentials = OAuth2Credentials('client_id', 'client_secret',
                                        callback_uri=self.callback_uri)
        url = credentials.generate_url()
        self.assertTrue(url.startswith(OAUTH2_AUTHORIZE_URL))
        qs = parse_qs(urlparse(url).query)
        # Test that the credentials object can be dumped by state
        cred_state = credentials.state
        # Then test that the relevant attributes are in the querystring
        self.assertEqual(qs['client_id'][0], cred_state['client_id'])
        self.assertEqual(qs['redirect_uri'][0], cred_state['callback_uri'])
        self.assertEqual(qs['response_type'][0], 'code')
        self.assertEqual(qs['scope'][0], " ".join(cred_state['scope']))
        self.assertEqual(qs['state'][0], cred_state['auth_state'])

    def test_authorisation_url_using_initial_state(self):
        credentials = OAuth2Credentials('client_id', 'client_secret',
                                        callback_uri=self.callback_uri,
                                        auth_state='test_state')
        url = urlparse(credentials.generate_url())
        self.assertEqual(credentials.auth_state, 'test_state')
        qs = parse_qs(url.query)
        self.assertEqual(qs['state'][0], 'test_state')

    @patch('requests_oauthlib.OAuth2Session.request')
    def test_verification_using_bad_auth_uri(self, r_request):
        credentials = OAuth2Credentials('client_id', 'client_secret',
                                        auth_state='test_state')
        bad_auth_uri = '{}?error=access_denied&state={}'.format(
            self.callback_uri, credentials.auth_state
        )
        with self.assertRaises(XeroAccessDenied):
            credentials.verify(bad_auth_uri)
        with self.assertRaises(XeroAccessDenied):
            OAuth2Credentials('client_id', 'client_secret',
                              auth_state='test_state',
                              auth_secret=bad_auth_uri)
        self.assertFalse(r_request.called)

    @patch('requests_oauthlib.OAuth2Session.request')
    def test_verification_success(self, r_request):
        credentials = OAuth2Credentials('client_id', 'client_secret',
                                        auth_state='test_state')
        auth_uri = '{}?code=0123456789&scope={}&state={}'.format(
            self.callback_uri, '%20'.join(credentials.scope),
            credentials.auth_state
        )
        r_request.return_value = Mock(
            status_code=200,
            request=Mock(headers={}, body=''),
            headers={},
            text='{"access_token":"1234567890","expires_in":1800,'
                 '"token_type":"Bearer","refresh_token":"0987654321"}'
        )
        credentials.verify(auth_uri)
        self.assertTrue(r_request.called)
        self.assertTrue(credentials.token)
        self.assertTrue(credentials.oauth)
        self.assertFalse(credentials.expired())

        # Finally test the state
        self.assertEqual(
            credentials.state,
            {
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'auth_state': credentials.auth_state,
                'scope': credentials.scope,
                'user_agent': credentials.user_agent,
                'token': credentials.token
            }
        )

    @patch('requests_oauthlib.OAuth2Session.request')
    def test_verification_failure(self, r_request):
        credentials = OAuth2Credentials('client_id', 'client_secret',
                                        auth_state='test_state')
        auth_uri = '{}?code=0123456789&scope={}&state={}'.format(
            self.callback_uri, '%20'.join(credentials.scope),
            credentials.auth_state
        )
        r_request.return_value = Mock(
            status_code=400,
            request=Mock(headers={}, body=''),
            headers={},
            text='{"error":"invalid_grant"}'
        )
        with self.assertRaises(XeroAccessDenied):
            credentials.verify(auth_uri)
        with self.assertRaises(XeroAccessDenied):
            OAuth2Credentials('client_id', 'client_secret',
                              auth_state='test_state',
                              auth_secret=auth_uri)

    @patch('requests_oauthlib.OAuth2Session.post')
    def test_token_refresh(self, r_post):
        credentials = OAuth2Credentials('client_id', 'client_secret',
                                        token=self.expired_token)
        self.assertTrue(credentials.oauth)
        self.assertTrue(credentials.expired())
        
        r_post.return_value = Mock(status_code=200,
                                   headers={},
                                   text='{"access_token":"5555555555","expires_in":1800,'
                                        '"token_type":"Bearer","refresh_token":"44444444444"}'
                                   )
        credentials.refresh()
        self.assertTrue(r_post.called)
        self.assertFalse(credentials.expired())
        # Test that the headers were set correctly
        auth = r_post.call_args[1]['auth']
        self.assertEqual(auth.username, 'client_id')
        self.assertEqual(auth.password, 'client_secret')

    @patch('requests.get')
    def test_get_tenants(self, r_get):
        credentials = OAuth2Credentials('client_id', 'client_secret',
                                        token=self.expired_token)

        content = '[{"id":"1","tenantId":"12345","tenantType":"ORGANISATION"}]'

        def json_fct():
            return json.loads(content)
        r_get.return_value = Mock(
            status_code=200,
            json=json_fct
        )
        tenants = credentials.get_tenants()
        self.assertTrue(r_get.called)
        self.assertEqual(tenants,
                         [{"id": "1", "tenantId": "12345", "tenantType": "ORGANISATION"}])

    @patch('xero.auth.OAuth2Credentials.get_tenants')
    def test_set_default_tenant(self, get_tenants):
        get_tenants.return_value = [{"id": "1", "tenantId": "12345",
                                     "tenantType": "ORGANISATION"}]
        credentials = OAuth2Credentials('client_id', 'client_secret',
                                        token=self.expired_token)
        credentials.set_default_tenant()
        self.assertEqual(credentials.tenant_id, "12345")

    @patch('requests.get')
    def test_tenant_is_used_in_xero_request(self, r_get):
        credentials = OAuth2Credentials('client_id', 'client_secret',
                                        token=self.expired_token,
                                        tenant_id='12345')
        xero = Xero(credentials)
        # Just return any old response
        r_get.return_value = None
        try:
            xero.contacts.all()
        except:
            pass
        self.assertEqual(r_get.call_args[1]['headers']['Xero-tenant-id'], '12345')

    def test_tenant_id_not_set_raises_error(self):
        credentials = OAuth2Credentials('client_id', 'client_secret',
                                        token=self.expired_token)
        xero = Xero(credentials)
        with self.assertRaises(XeroTenantIdNotSet):
            xero.contacts.all()



