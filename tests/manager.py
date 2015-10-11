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
from . import compare_xml
from unittest.util import safe_repr
import difflib
import six


class ManagerTest(unittest.TestCase):
    maxDiff = None

    def assertXMLEqual(self, xml1, xml2, msg=None):
        """
        Asserts that two XML snippets are semantically the same.
        Whitespace in most cases is ignored, and attribute ordering is not
        significant. The passed-in arguments must be valid XML.
        """
        try:
            result = compare_xml(xml1, xml2)
        except Exception as e:
            standardMsg = 'First or second argument is not valid XML\n%s' % e
            self.fail(self._formatMessage(msg, standardMsg))
        else:
            if not result:
                standardMsg = '%s != %s' % (safe_repr(xml1, True), safe_repr(xml2, True))
                diff = ('\n' + '\n'.join(
                    difflib.ndiff(
                        six.text_type(xml1).splitlines(),
                        six.text_type(xml2).splitlines(),
                    )
                ))
                standardMsg = self._truncateMessage(standardMsg, diff)
                self.fail(self._formatMessage(msg, standardMsg))

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

        self.assertXMLEqual(
            resultant_xml,
            expected_xml,
        )


    def test_serializer_phones_addresses(self):
        credentials = Mock(base_url="")
        manager = Manager('contacts', credentials)

        example_contact_input = {
            'ContactID': '565acaa9-e7f3-4fbf-80c3-16b081ddae10',
            'ContactStatus': 'ACTIVE',
            'Name': 'Southside Office Supplies',
            'Addresses': [
                {
                    'AddressType': 'POBOX',
                },
                {
                    'AddressType': 'STREET',
                },
            ],
            'Phones': [
                {
                    'PhoneType': 'DDI',
                },
                {
                    'PhoneType': 'DEFAULT',
                },
                {
                    'PhoneType': 'FAX',
                },
                {
                    'PhoneType': 'MOBILE',
                },
            ],
            'UpdatedDateUTC': datetime.datetime(2015, 9, 18, 5, 6, 56, 893),
            'IsSupplier': False,
            'IsCustomer': False,
            'HasAttachments': False,
        }
        resultant_xml = manager._prepare_data_for_save(example_contact_input)

        expected_xml = """
            <Contact>
              <ContactID>565acaa9-e7f3-4fbf-80c3-16b081ddae10</ContactID>
              <ContactStatus>ACTIVE</ContactStatus>
              <Name>Southside Office Supplies</Name>
              <Addresses>
                <Address>
                  <AddressType>POBOX</AddressType>
                </Address>
                <Address>
                  <AddressType>STREET</AddressType>
                </Address>
              </Addresses>
              <Phones>
                <Phone>
                  <PhoneType>DDI</PhoneType>
                </Phone>
                <Phone>
                  <PhoneType>DEFAULT</PhoneType>
                </Phone>
                <Phone>
                  <PhoneType>FAX</PhoneType>
                </Phone>
                <Phone>
                  <PhoneType>MOBILE</PhoneType>
                </Phone>
              </Phones>
              <UpdatedDateUTC>2015-09-18T05:06:56.893</UpdatedDateUTC>
              <IsSupplier>false</IsSupplier>
              <IsCustomer>false</IsCustomer>
              <HasAttachments>false</HasAttachments>
            </Contact>
        """

        self.assertXMLEqual(
            resultant_xml,
            expected_xml,
        )


    def test_serializer_nested_singular(self):
        credentials = Mock(base_url="")
        manager = Manager('contacts', credentials)

        example_invoice_input = {
            'Date': datetime.datetime(2015, 6, 6, 16, 25, 2, 711109),
            'Reference': 'ABAS 123',
            'LineItems': [
                {'Description': 'Example description only'},
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
            </LineItems>
            <Type>ACCREC</Type>
            <DueDate>2015-07-06 16:25:02.711136</DueDate>
        """

        # @todo Need a py2/3 way to compare XML easily.
        # self.assertEqual(
        #     resultant_xml,
        #     expected_xml,
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
