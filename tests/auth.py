import unittest

from datetime import datetime, timedelta
from mock import patch, Mock

from xero.auth import PublicCredentials, PartnerCredentials
from xero.exceptions import XeroException, XeroNotVerified, XeroUnauthorized


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
