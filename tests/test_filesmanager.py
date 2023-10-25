import unittest
from time import time
from unittest.mock import patch

from xero import Xero
from xero.auth import OAuth2Credentials


class FilesManagerTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        # Create an expired token to be used by tests
        self.expired_token = {
            "access_token": "1234567890",
            "expires_in": 1800,
            "token_type": "Bearer",
            "refresh_token": "0987654321",
            "expires_at": time(),
        }

    @patch("requests.get")
    def test_tenant_is_used_in_xero_request(self, r_get):
        credentials = OAuth2Credentials(
            "client_id", "client_secret", token=self.expired_token, tenant_id="12345"
        )
        xero = Xero(credentials)
        # Just return any old response
        r_get.return_value = None
        try:
            xero.filesAPI.files.all()
        except:  # NOQA: E722
            pass

        self.assertEqual(r_get.call_args[1]["headers"]["Xero-tenant-id"], "12345")
