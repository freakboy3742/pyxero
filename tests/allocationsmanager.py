from mock import Mock
import unittest

from xero.allocationsmanager import PrepaymentAllocationsManager
from tests.mock_data import allocations_list

class AllocationTest(unittest.TestCase):
    def test__put(self):
        credentials = Mock(base_url="")

        prepaymentallocations = PrepaymentAllocationsManager(credentials)
        uri, params, method, body, headers, singleobject = prepaymentallocations._put("a_prepayment_id", allocations_list)
        last_three_uri_fragments = uri.split('/')[3:]
        assert last_three_uri_fragments == ['Prepayments', 'a_prepayment_id', 'Allocations']
        assert body == {
            'xml': b'<Allocations><Allocation><AppliedAmount>100'
                   b'</AppliedAmount><Invoice><InvoiceID>'
                   b'some_invoice_id</InvoiceID></Invoice>'
                   b'</Allocation></Allocations>'
        }
        assert singleobject == False
