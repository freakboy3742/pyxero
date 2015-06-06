# coding: utf-8
from __future__ import unicode_literals

from datetime import date, datetime
try:
    # Try importing from unittest2 first. This is primarily for Py2.6 support.
    import unittest2 as unittest
except ImportError:
    import unittest

from xml.dom.minidom import parseString

from mock import Mock, patch

from xero import Xero
from xero.manager import Manager
from tests import mock_data


class ManagerTest(unittest.TestCase):
    def test_filter(self):
        """The filter function should correctly handle various arguments"""
        credentials = Mock(base_url="")
        manager = Manager('contacts', credentials)

        uri, params, method, body, headers, singleobject = manager._filter(
                order="LastName",
                page=2,
                offset=5,
                since=datetime(2014, 8, 10, 15, 14, 46),
                Name="John")

        self.assertEqual(method, 'get')
        self.assertFalse(singleobject)

        expected_params = {
                "order": "LastName",
                "page": 2,
                "offset": 5,
                "where": 'Name=="John"'
        }
        self.assertEqual(params, expected_params)

        expected_headers = {
            "If-Modified-Since": "Sun, 10 Aug 2014 15:14:46 GMT"
        }
        self.assertEqual(headers, expected_headers)

        # Also make sure an empty call runs ok
        uri, params, method, body, headers, singleobject = manager._filter()
        self.assertEqual(params, {})
        self.assertIsNone(headers)

        manager = Manager('invoices', credentials)
        uri, params, method, body, headers, singleobject = manager._filter(
                **{'Contact.ContactID': '3e776c4b-ea9e-4bb1-96be-6b0c7a71a37f'})

        self.assertEqual(
            params,
            {'where': 'Contact.ContactID==Guid("3e776c4b-ea9e-4bb1-96be-6b0c7a71a37f")'}
        )

    def test_magnitude_filters(self):
        """The filter function should correctlu handle date arguments and gt, lt operators"""
        credentials = Mock(base_url="")

        manager = Manager('invoices', credentials)
        uri, params, method, body, headers, singleobject = manager._filter(**{'Date__gt': datetime(2007, 12, 6)})

        self.assertEqual(
            params,
            {u'where': u'Date>DateTime(2007,12,6)'}
        )

        manager = Manager('invoices', credentials)
        uri, params, method, body, headers, singleobject = manager._filter(**{'Date__lte': datetime(2007, 12, 6)})

        self.assertEqual(
            params,
            {u'where': u'Date<=DateTime(2007,12,6)'}
        )

    def test_unit4dps(self):
        """The manager should add a query param of unitdp iff enabled"""

        credentials = Mock(base_url="")

        # test 4dps is disabled by default
        manager = Manager('contacts', credentials)
        uri, params, method, body, headers, singleobject = manager._filter()
        self.assertEqual(params, {}, "test 4dps not enabled by default")

        # test 4dps is enabled by default
        manager = Manager('contacts', credentials, unit_price_4dps=True)
        uri, params, method, body, headers, singleobject = manager._filter()
        self.assertEqual(params, {"unitdp": 4}, "test 4dps can be enabled explicitly")

        # test 4dps can be disable explicitly
        manager = Manager('contacts', credentials, unit_price_4dps=False)
        uri, params, method, body, headers, singleobject = manager._filter()
        self.assertEqual(params, {}, "test 4dps can be disabled explicitly")
