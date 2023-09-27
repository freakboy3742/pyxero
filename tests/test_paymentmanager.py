import unittest
from unittest.mock import Mock

from xero.paymentmanager import PaymentManager

from .helpers import assertXMLEqual


class ManagerTest(unittest.TestCase):
    def test_delete(self):
        credentials = Mock(base_url="")
        manager = PaymentManager("payments", credentials)

        uri, params, method, body, headers, singleobject = manager._delete(
            "768e44ef-c1e3-4d7f-8e06-f6e8bc4eefa4"
        )

        self.assertEqual(
            uri, "/api.xro/2.0/payments/768e44ef-c1e3-4d7f-8e06-f6e8bc4eefa4"
        )

        self.assertEqual(params, {})
        self.assertEqual(method, "post")

        assertXMLEqual(self, body, "<Status>DELETED</Status>")

        self.assertIsNone(headers)
