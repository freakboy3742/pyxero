# coding: utf-8
from __future__ import unicode_literals

from datetime import date, datetime
import unittest
from xml.dom.minidom import parseString

from mock import Mock, patch

from xero import Xero
from xero.manager import Manager
from tests import mock_data


class ManagerTest(unittest.TestCase):
    def test_serialization(self):
        "An invoice can be correctly serialized for a POST/PUT request"

        # This checks:
        # * Date data types
        # * Normal string data types
        # * Inline dictionary data types (Contact)
        # * List of dict data types

        credentials = Mock(base_url="")
        xero = Xero(credentials)

        original = {
            'Invoice': {
                'Type': 'ACCREC',
                'Contact': {'ContactID': '3e776c4b-ea9e-4bb1-96be-6b0c7a71a37f'},
                'LineItems': [
                    {
                        'Description': 'Line item 1',
                        'Quantity': '1.0',
                        'UnitAmount': '100.00',
                        'AccountCode': '200',
                    },
                    {
                        'Description': 'Line item 2',
                        'Quantity': '2.0',
                        'UnitAmount': '750.00',
                        'AccountCode': '200',
                    },
                ],
                'Date': date(2013, 2, 1),
                'DueDate': date(2013, 2, 15),
                'InvoiceNumber': 'X0001'
            }
        }
        # Convert invoice to XML
        xml = xero.invoices._prepare_data_for_save(original['Invoice'])

        # Convert back into a dictionary.
        dom = parseString(xml)
        tuple_form = xero.invoices.walk_dom(dom)
        reproduced = xero.invoices.convert_to_dict(tuple_form)

        # Original should match reproduced version, embedded inside a parent key
        self.assertEqual(original, reproduced)

    @patch('requests.get')
    def test_unicode_content(self, r_get):
        "PyXero will correctly process unicode content"
        # Verified response from Xero API.
        # This reponse was generated by setting the contact on
        # "Yarra Transport" (ID dbb54b2b-8fdb-4277-ad03-2df50ce760fa)
        # to "John Sürname"
        r_get.return_value = Mock(status_code=200,
            headers={'content-type': 'text/xml; charset=utf-8'},
            encoding='utf-8', text=mock_data.unicode_content_text)

        credentials = Mock(base_url="")
        xero = Xero(credentials)

        contact = xero.contacts.get(id='755f1475-d255-43a8-bedc-5ea7fd26c71f')

        self.assertEqual(contact['FirstName'], 'John')
        self.assertEqual(contact['LastName'], 'Sürname')

    def test_filter(self):
        "The filter function should correctly handle various arguments"
        
        # filter() is wrapped by _get_data when the Manager
        # is instantiated. We save a copy so we can call it directly.
        Manager.filter_unwrapped = Manager.filter
        
        credentials = Mock(base_url="")
        manager = Manager('contacts', credentials)
        
        uri, params, method, body, headers = manager.filter_unwrapped(
                order="LastName",
                page=2,
                offset=5,
                since=datetime(2014, 8, 10, 15, 14, 46),
                Name="John")

        self.assertEqual(method, 'get')

        expected_params = {
                "order": "LastName",
                "page": 2,
                "offset": 5,
                "where": 'Name=="John"'
        }
        self.assertEqual(params, expected_params)

        expected_headers = {
                "If-Modified-Since" : "Sun, 10 Aug 2014 15:14:46 GMT"
        }
        self.assertEqual(headers, expected_headers)
        
        # Also make sure an empty call runs ok
        uri, params, method, body, headers = manager.filter_unwrapped()
        self.assertEqual(params, {})
        self.assertIsNone(headers)
