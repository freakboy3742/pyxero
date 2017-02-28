from __future__ import unicode_literals

import datetime
import re
import six
import unittest

from collections import defaultdict
from mock import Mock
from xml.dom.minidom import parseString

from xero.manager import Manager


class ManagerTest(unittest.TestCase):
    def assertXMLEqual(self, xml1, xml2, message=''):
        def to_str(s):
            return s.decode('utf-8') if six.PY3 and isinstance(s, bytes) else str(s)

        def clean_xml(xml):
            xml = '<root>%s</root>' % to_str(xml)
            return str(re.sub('>\n *<','><', parseString(xml).toxml()))

        def xml_to_dict(xml):
            nodes = re.findall('(<([^>]*)>(.*?)</\\2>)', xml)
            if len(nodes) == 0:
                return xml
            d = defaultdict(list)
            for node in nodes:
                d[node[1]].append(xml_to_dict(node[2]))
            return d

        cleaned = map(clean_xml, (xml1, xml2))
        d1, d2 = tuple(map(xml_to_dict, cleaned))

        self.assertEqual(d1, d2, message)


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
        resultant_xml = '<Invoice>%s</Invoice>' % resultant_xml

        expected_xml = """
        <Invoice>
          <Status>DRAFT</Status>
          <Contact>
            <Name>Basket Case</Name>
          </Contact>
          <Reference>ABAS 123</Reference>
          <Date>2015-06-06T16:25:02</Date>
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
          <DueDate>2015-07-06T16:25:02</DueDate>
        </Invoice>
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
        resultant_xml = '<Contact>%s</Contact>' % resultant_xml

        expected_xml = """
        <Contact>
          <ContactID>565acaa9-e7f3-4fbf-80c3-16b081ddae10</ContactID>
          <Name>Southside Office Supplies</Name>
          <HasAttachments>false</HasAttachments>
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
          <IsCustomer>false</IsCustomer>
          <Addresses>
            <Address>
              <AddressType>POBOX</AddressType>
            </Address>
            <Address>
              <AddressType>STREET</AddressType>
            </Address>
          </Addresses>
          <IsSupplier>false</IsSupplier>
          <ContactStatus>ACTIVE</ContactStatus>
        </Contact>
        """

        self.assertXMLEqual(
            resultant_xml,
            expected_xml,
            "Resultant XML does not match expected."
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
            <Date>2015-06-06T16:25:02</Date>
            <LineAmountTypes>Exclusive</LineAmountTypes>
            <LineItems>
              <LineItem>
                <Description>Example description only</Description>
              </LineItem>
            </LineItems>
            <Type>ACCREC</Type>
            <DueDate>2015-07-06T16:25:02</DueDate>
        """

        self.assertXMLEqual(
            resultant_xml,
            expected_xml,
        )


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

    def test_boolean_filter(self):
        """The filter function should correctly handle various arguments"""
        credentials = Mock(base_url="")
        manager = Manager('invoices', credentials)
        uri, params, method, body, headers, singleobject = manager._filter(
            CanApplyToRevenue=True
        )
        self.assertEqual(
            params,
            {'where': 'CanApplyToRevenue==true'}
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

    def test_get_params(self):
        """The 'get' methods should pass GET parameters if provided.
        """

        credentials = Mock(base_url="")
        manager = Manager("reports", credentials)

        # test no parameters or headers sent by default
        uri, params, method, body, headers, singleobject = manager._get("ProfitAndLoss")
        self.assertEqual(params, {}, "test params not sent by default")

        # test params can be provided
        passed_params = {
            "fromDate": "2015-01-01",
            "toDate": "2015-01-15",
        }
        uri, params, method, body, headers, singleobject = manager._get(
            "ProfitAndLoss", params=passed_params
        )
        self.assertEqual(params, passed_params, "test params can be set")

        # test params respect, but can override, existing configuration
        manager = Manager("reports", credentials, unit_price_4dps=True)
        uri, params, method, body, headers, singleobject = manager._get(
            "ProfitAndLoss", params=passed_params
        )
        self.assertEqual(params, {
            "fromDate": "2015-01-01",
            "toDate": "2015-01-15",
            "unitdp": 4,
        }, "test params respects existing values")
