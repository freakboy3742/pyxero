from __future__ import unicode_literals

from datetime import date
import unittest
from xml.dom.minidom import parseString

from mock import Mock

from xero import Xero


class InvoiceTest(unittest.TestCase):
    def test_invoice(self):
        "An invoice can be correctly serialized for a POST/PUT request"

        # This checks:
        # * Date data types
        # * Normal string data types
        # * Inline dictionary data types (Contact)
        # * List of dict data types

        credentials = Mock()
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

