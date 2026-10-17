import os.path
import unittest
from time import time
from unittest.mock import Mock, patch

import requests

from xero import Xero
from xero.auth import OAuth2Credentials
from xero.exceptions import XeroTenantIdNotSet


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

        self.filepath = "test_file.txt"
        with open(self.filepath, "w") as f:
            f.write("test")

    def tearDown(self):
        os.remove(self.filepath)

    @patch("requests.get")
    def test_tenant_is_used_in_xero_request(self, r_get):
        credentials = OAuth2Credentials(
            "client_id", "client_secret", token=self.expired_token, tenant_id="12345"
        )
        xero = Xero(credentials)
        r_get.return_value = Mock(
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
        )
        xero.filesAPI.files.all()

        self.assertEqual(r_get.call_args[1]["headers"]["Xero-tenant-id"], "12345")

    @patch("requests.post")
    def test_upload_file_as_path(self, r_get):
        credentials = OAuth2Credentials(
            "client_id", "client_secret", token=self.expired_token, tenant_id="12345"
        )
        xero = Xero(credentials)
        r_get.return_value = Mock(
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
        )

        def upload(*args, **kwargs):
            stream = kwargs["files"][self.filepath]
            self.assertFalse(stream.closed)
            self.assertEqual(stream.read(), b"test")
            return r_get.return_value

        r_get.side_effect = upload
        xero.filesAPI.files.upload_file(
            os.path.abspath(self.filepath), folderId="folder", filename="ignored.txt"
        )

        self.assertIn(self.filepath, r_get.call_args[1]["files"])
        self.assertTrue(r_get.call_args[0][0].endswith("/Files/folder"))
        stream = r_get.call_args[1]["files"][self.filepath]
        try:
            self.assertTrue(stream.closed)
        finally:
            stream.close()

    @patch("requests.post")
    def test_upload_file_as_file(self, r_get):
        credentials = OAuth2Credentials(
            "client_id", "client_secret", token=self.expired_token, tenant_id="12345"
        )
        xero = Xero(credentials)
        r_get.return_value = Mock(
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
        )

        with open(self.filepath) as f:
            xero.filesAPI.files.upload_file(
                file=f, filename=os.path.basename(self.filepath)
            )
            self.assertFalse(f.closed)
            self.assertIs(r_get.call_args[1]["files"][self.filepath], f)

        self.assertIn(self.filepath, r_get.call_args[1]["files"])

    @patch("requests.post")
    def test_upload_path_is_closed_on_request_error(self, r_post):
        credentials = OAuth2Credentials(
            "client_id", "client_secret", token=self.expired_token, tenant_id="12345"
        )
        xero = Xero(credentials)
        r_post.side_effect = requests.ConnectionError("upload failed")

        with self.assertRaisesRegex(requests.ConnectionError, "upload failed"):
            xero.filesAPI.files.upload_file(path=self.filepath)

        stream = r_post.call_args[1]["files"][self.filepath]
        try:
            self.assertTrue(stream.closed)
        finally:
            stream.close()

    @patch("requests.post")
    def test_upload_path_is_closed_on_response_error(self, r_post):
        credentials = OAuth2Credentials(
            "client_id", "client_secret", token=self.expired_token, tenant_id="12345"
        )
        xero = Xero(credentials)
        r_post.return_value = Mock(
            status_code=200,
            headers={"content-type": "application/json"},
            json=Mock(side_effect=ValueError("invalid response")),
        )

        with self.assertRaisesRegex(ValueError, "invalid response"):
            xero.filesAPI.files.upload_file(path=self.filepath)

        stream = r_post.call_args[1]["files"][self.filepath]
        try:
            self.assertTrue(stream.closed)
        finally:
            stream.close()

    @patch("requests.post")
    def test_upload_file_is_not_closed_on_request_error(self, r_post):
        credentials = OAuth2Credentials(
            "client_id", "client_secret", token=self.expired_token, tenant_id="12345"
        )
        xero = Xero(credentials)
        r_post.side_effect = requests.ConnectionError("upload failed")

        with open(self.filepath) as stream:
            with self.assertRaisesRegex(requests.ConnectionError, "upload failed"):
                xero.filesAPI.files.upload_file(file=stream, filename=self.filepath)
            self.assertFalse(stream.closed)
            self.assertIs(r_post.call_args[1]["files"][self.filepath], stream)

    @patch("requests.post")
    def test_upload_path_is_closed_without_tenant(self, r_post):
        credentials = OAuth2Credentials(
            "client_id", "client_secret", token=self.expired_token
        )
        xero = Xero(credentials)
        opened = []
        real_open = open

        def open_upload(*args, **kwargs):
            stream = real_open(*args, **kwargs)
            opened.append(stream)
            return stream

        try:
            with (
                patch("xero.filesmanager.open", side_effect=open_upload, create=True),
                self.assertRaises(XeroTenantIdNotSet),
            ):
                xero.filesAPI.files.upload_file(path=self.filepath)
            r_post.assert_not_called()
            self.assertEqual(len(opened), 1)
            self.assertTrue(opened[0].closed)
        finally:
            for stream in opened:
                stream.close()
