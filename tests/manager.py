# coding: utf-8
from __future__ import unicode_literals

import datetime

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
    def test_serializer(self):
        credentials = Mock(base_url="")
        manager = Manager('contacts', credentials)

        example_invoice_input = {
            'Date': datetime.datetime(2015, 6, 6, 16, 25, 2, 711109),
            'Reference': 'ABAS 123',
            'LineItems': [
                {'Description': 'Example description only'},
                {
                    'UnitAmount': '0.0000',
                    'Quantity': 1,
                    'AccountCode': '200',
                    'Description': 'Example line item 2',
                    'TaxType': 'OUTPUT'
                },
                {
                    'UnitAmount': '231.0000',
                    'Quantity': 1,
                    'AccountCode': '200',
                    'Description': 'Example line item 3',
                    'TaxType': 'OUTPUT'
                },
            ],
            'Status': 'DRAFT',
            'Type': 'ACCREC',
            'DueDate': datetime.datetime(2015, 7, 6, 16, 25, 2, 711136),
            'LineAmountTypes': 'Exclusive',
            'Contact': {'Name': 'Basket Case'}
        }
        resultant_xml = manager._prepare_data_for_save(example_invoice_input)

        expected_xml = """
            <Status>DRAFT</Status>
            <Contact><Name>Basket Case</Name></Contact>
            <Reference>ABAS 123</Reference>
            <Date>2015-06-06 16:25:02.711109</Date>
            <LineAmountTypes>Exclusive</LineAmountTypes>
            <LineItems>
              <LineItem>
                <Description>Example description only</Description>
              </LineItem>
              <LineItem>
                <TaxType>OUTPUT</TaxType>
                <AccountCode>200</AccountCode>
                <UnitAmount>0.0000</UnitAmount>
                <Description>Example line item 2</Description>
                <Quantity>1</Quantity>
              </LineItem>
              <LineItem>
                <TaxType>OUTPUT</TaxType>
                <AccountCode>200</AccountCode>
                <UnitAmount>231.0000</UnitAmount>
                <Description>Example line item 3</Description>
                <Quantity>1</Quantity>
              </LineItem>
            </LineItems>
            <Type>ACCREC</Type>
            <DueDate>2015-07-06 16:25:02.711136</DueDate>
        """

        # @todo Need a py2/3 way to compare XML easily.
        # self.assertEqual(
        #     resultant_xml,
        #     expected_xml,
        #     "Failed to serialize data to XML correctly."
        # )


    def test_filter(self):
        """The filter function should correctly handle various arguments"""
        credentials = Mock(base_url="")
        manager = Manager('contacts', credentials)

        uri, params, method, body, headers, singleobject = manager._filter(
                order="LastName",
                page=2,
                offset=5,
                since=datetime.datetime(2014, 8, 10, 15, 14, 46),
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

    def test_rawfilter(self):
        """The filter function should correctly handle various arguments"""
        credentials = Mock(base_url="")
        manager = Manager('invoices', credentials)
        uri, params, method, body, headers, singleobject = manager._filter(
            Status="VOIDED",
            raw='Name.ToLower()=="test contact"'
        )
        self.assertEqual(
            params,
            {'where': 'Name.ToLower()=="test contact"&&Status=="VOIDED"'}
        )

    def test_magnitude_filters(self):
        """The filter function should correctlu handle date arguments and gt, lt operators"""
        credentials = Mock(base_url="")

        manager = Manager('invoices', credentials)
        uri, params, method, body, headers, singleobject = manager._filter(**{'Date__gt': datetime.datetime(2007, 12, 6)})

        self.assertEqual(
            params,
            {u'where': u'Date>DateTime(2007,12,6)'}
        )

        manager = Manager('invoices', credentials)
        uri, params, method, body, headers, singleobject = manager._filter(**{'Date__lte': datetime.datetime(2007, 12, 6)})

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
