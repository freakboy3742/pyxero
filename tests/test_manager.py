import datetime
import unittest
from io import BytesIO
from unittest.mock import Mock, patch

from xero.exceptions import XeroExceptionUnknown
from xero.manager import Manager
from xero.utils import generate_idempotency_key

from .helpers import assertXMLEqual


class ManagerTest(unittest.TestCase):
    def test_serializer(self):
        credentials = Mock(base_url="")
        manager = Manager("Invoice", credentials)

        example_invoice_input = {
            "Date": datetime.datetime(2015, 6, 6, 16, 25, 2, 711109),
            "Reference": "ABAS 123",
            "LineItems": [
                {"Description": "Example description only"},
                {
                    "UnitAmount": "0.0000",
                    "Quantity": 1,
                    "AccountCode": "200",
                    "Description": "Example line item 2",
                    "TaxType": "OUTPUT",
                },
                {
                    "UnitAmount": "231.0000",
                    "Quantity": 1,
                    "AccountCode": "200",
                    "Description": "Example line item 3",
                    "TaxType": "OUTPUT",
                },
            ],
            "Status": "DRAFT",
            "Type": "ACCREC",
            "DueDate": datetime.datetime(2015, 7, 6, 16, 25, 2, 711136),
            "LineAmountTypes": "Exclusive",
            "Contact": {"Name": "Basket Case"},
        }
        resultant_xml = manager._prepare_data_for_save(example_invoice_input)
        resultant_xml = "<Invoice>%s</Invoice>" % resultant_xml

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

        assertXMLEqual(self, resultant_xml, expected_xml)

    def test_serializer_phones_addresses(self):
        credentials = Mock(base_url="")
        manager = Manager("Contacts", credentials)

        example_contact_input = {
            "ContactID": "565acaa9-e7f3-4fbf-80c3-16b081ddae10",
            "ContactStatus": "ACTIVE",
            "Name": "Southside Office Supplies",
            "Addresses": [{"AddressType": "POBOX"}, {"AddressType": "STREET"}],
            "Phones": [
                {"PhoneType": "DDI"},
                {"PhoneType": "DEFAULT"},
                {"PhoneType": "FAX"},
                {"PhoneType": "MOBILE"},
            ],
            "UpdatedDateUTC": datetime.datetime(2015, 9, 18, 5, 6, 56, 893),
            "IsSupplier": False,
            "IsCustomer": False,
            "HasAttachments": False,
        }
        resultant_xml = manager._prepare_data_for_save(example_contact_input)
        resultant_xml = "<Contact>%s</Contact>" % resultant_xml

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

        assertXMLEqual(
            self, resultant_xml, expected_xml, "Resultant XML does not match expected."
        )

    def test_serializer_nested_singular(self):
        credentials = Mock(base_url="")
        manager = Manager("Invoice", credentials)

        example_invoice_input = {
            "Date": datetime.datetime(2015, 6, 6, 16, 25, 2, 711109),
            "Reference": "ABAS 123",
            "LineItems": [{"Description": "Example description only"}],
            "Status": "DRAFT",
            "Type": "ACCREC",
            "DueDate": datetime.datetime(2015, 7, 6, 16, 25, 2, 711136),
            "LineAmountTypes": "Exclusive",
            "Contact": {"Name": "Basket Case"},
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

        assertXMLEqual(self, resultant_xml, expected_xml)

    def test_filter(self):
        """The filter function should correctly handle various arguments"""
        credentials = Mock(base_url="")
        manager = Manager("Contacts", credentials)

        uri, params, method, body, headers, singleobject = manager._filter(
            order="LastName",
            page=2,
            offset=5,
            since=datetime.datetime(2014, 8, 10, 15, 14, 46),
            Name="John",
        )

        self.assertEqual(method, "get")
        self.assertFalse(singleobject)

        expected_params = {
            "order": "LastName",
            "page": 2,
            "offset": 5,
            "where": 'Name=="John"',
        }
        self.assertEqual(params, expected_params)

        expected_headers = {"If-Modified-Since": "Sun, 10 Aug 2014 15:14:46 GMT"}
        self.assertEqual(headers, expected_headers)

        # Also make sure an empty call runs ok
        uri, params, method, body, headers, singleobject = manager._filter()
        self.assertEqual(params, {})
        self.assertIsNone(headers)

        manager = Manager("Invoices", credentials)
        uri, params, method, body, headers, singleobject = manager._filter(
            **{"Contact.ContactID": "3e776c4b-ea9e-4bb1-96be-6b0c7a71a37f"}
        )

        self.assertEqual(
            params,
            {
                "where": 'Contact.ContactID==Guid("3e776c4b-ea9e-4bb1-96be-6b0c7a71a37f")'
            },
        )

        (uri, params, method, body, headers, singleobject) = manager._filter(
            **{"AmountPaid": 0.0}
        )

        self.assertEqual(params, {"where": 'AmountPaid=="0.0"'})

    def test_filter_ids(self):
        """The filter function should correctly handle various arguments"""
        credentials = Mock(base_url="")
        manager = Manager("Contacts", credentials)

        uri, params, method, body, headers, singleobject = manager._filter(
            IDs=[
                "3e776c4b-ea9e-4bb1-96be-6b0c7a71a37f",
                "12345678901234567890123456789012",
            ]
        )

        self.assertEqual(method, "get")
        self.assertFalse(singleobject)

        expected_params = {
            "IDs": "3e776c4bea9e4bb196be6b0c7a71a37f,12345678901234567890123456789012"
        }
        self.assertEqual(params, expected_params)

    def test_rawfilter(self):
        """The filter function should correctly handle various arguments"""
        credentials = Mock(base_url="")
        manager = Manager("Invoices", credentials)
        uri, params, method, body, headers, singleobject = manager._filter(
            Status="VOIDED", raw='Name.ToLower()=="test contact"'
        )
        self.assertEqual(
            params, {"where": 'Name.ToLower()=="test contact"&&Status=="VOIDED"'}
        )

    def test_boolean_filter(self):
        """The filter function should correctly handle various arguments"""
        credentials = Mock(base_url="")
        manager = Manager("Invoices", credentials)
        uri, params, method, body, headers, singleobject = manager._filter(
            CanApplyToRevenue=True
        )
        self.assertEqual(params, {"where": "CanApplyToRevenue==true"})

    def test_magnitude_filters(self):
        """The filter function should correctlu handle date arguments and gt, lt operators"""
        credentials = Mock(base_url="")

        manager = Manager("Invoices", credentials)
        uri, params, method, body, headers, singleobject = manager._filter(
            **{"Date__gt": datetime.datetime(2007, 12, 6)}
        )

        self.assertEqual(params, {"where": "Date>DateTime(2007,12,6)"})

        manager = Manager("Invoices", credentials)
        uri, params, method, body, headers, singleobject = manager._filter(
            **{"Date__lte": datetime.datetime(2007, 12, 6)}
        )

        self.assertEqual(params, {"where": "Date<=DateTime(2007,12,6)"})

    def test_unit4dps(self):
        """The manager should add a query param of unitdp iff enabled"""

        credentials = Mock(base_url="")

        # test 4dps is disabled by default
        manager = Manager("Contacts", credentials)
        uri, params, method, body, headers, singleobject = manager._filter()
        self.assertEqual(params, {}, "test 4dps not enabled by default")

        # test 4dps is enabled by default
        manager = Manager("Contacts", credentials, unit_price_4dps=True)
        uri, params, method, body, headers, singleobject = manager._filter()
        self.assertEqual(params, {"unitdp": 4}, "test 4dps can be enabled explicitly")

        # test 4dps can be disable explicitly
        manager = Manager("Contacts", credentials, unit_price_4dps=False)
        uri, params, method, body, headers, singleobject = manager._filter()
        self.assertEqual(params, {}, "test 4dps can be disabled explicitly")

    def test_get_params(self):
        """The 'get' methods should pass GET parameters if provided."""

        credentials = Mock(base_url="")
        manager = Manager("Reports", credentials)

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
        manager = Manager("Reports", credentials, unit_price_4dps=True)
        uri, params, method, body, headers, singleobject = manager._get(
            "ProfitAndLoss", params=passed_params
        )
        self.assertEqual(
            params,
            {"fromDate": "2015-01-01", "toDate": "2015-01-15", "unitdp": 4},
            "test params respects existing values",
        )

    def test_user_agent_inheritance(self):
        """The user_agent should be inherited from the provided credentials when not set explicitly."""

        # Default used when no user_agent set on manager and credentials has nothing to offer.
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("Reports", credentials)
        self.assertTrue(manager.user_agent.startswith("pyxero/"))

        # Taken from credentials when no user_agent set on manager.
        credentials = Mock(base_url="", user_agent="MY_COMPANY-MY_CONSUMER_KEY")
        manager = Manager("Reports", credentials)
        self.assertEqual(manager.user_agent, "MY_COMPANY-MY_CONSUMER_KEY")

        # Manager's user_agent used when explicitly set.
        credentials = Mock(base_url="", user_agent="MY_COMPANY-MY_CONSUMER_KEY")
        manager = Manager("Reports", credentials, user_agent="DemoCompany-1234567890")
        self.assertEqual(manager.user_agent, "DemoCompany-1234567890")

    @patch("xero.basemanager.requests.post")
    def test_request_content_type(self, request):
        """The Content-Type should be application/xml"""

        # Default used when no user_agent set on manager and credentials has nothing to offer.
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("Reports", credentials)
        try:
            manager._get_data(lambda: ("_", {}, "post", {}, {}, True))()
        except XeroExceptionUnknown:
            pass

        kwargs = request.mock_calls[0][2]
        self.assertTrue(kwargs["headers"]["Content-Type"], "application/xml")

    def test_request_body_format(self):
        """The body content should be in valid XML format"""

        # Default used when no user_agent set on manager and credentials has nothing to offer.
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("Reports", credentials)

        body = manager.save_or_put({"bing": "bong"})[3]

        self.assertTrue(body, "<Invoice><bing>bong</bing></Invoice>")

    @patch("xero.basemanager.requests.post")
    def test_idempotency_key_absent(self, mock_post):
        """No idempotency key header is inclduded if a key isn't provided."""
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("Invoices", credentials)

        try:
            # Try/Except here because we're not actually talking to Xero
            # and PyXero will raise an error about not knowing what to do with
            # the response (we don't care, just checking for headers!)
            manager.save(
                {
                    "foo": "bar",
                },
            )
        except XeroExceptionUnknown:
            pass

        # Header should not exist.
        assert "Idempotency-Key" not in mock_post.mock_calls[0][2]["headers"]

    @patch("xero.basemanager.requests.post")
    def test_idempotency_key_is_string(self, _):
        """Idempotency keys must be strings."""
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("Invoices", credentials)

        with self.assertRaises(TypeError):
            manager.save(
                {
                    "foo": "bar",
                },
                idempotency_key=12345,
            )

    @patch("xero.basemanager.requests.post")
    def test_idempotency_key_length(self, _):
        """Idempotency keys must be no longer than 128 characters."""
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("Invoices", credentials)

        bad_key = "a" * 129
        with self.assertRaises(ValueError):
            manager.save(
                {
                    "foo": "bar",
                },
                idempotency_key=bad_key,
            )

    @patch("xero.basemanager.requests.post")
    def test_idempotency_key_on_save(self, mock_post):
        """An idempotency key can be included on a Manager.save() call."""
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("Invoices", credentials)
        idempotency_key = generate_idempotency_key()

        try:
            # Try/Except here because we're not actually talking to Xero
            # and PyXero will raise an error about not knowing what to do with
            # the response (we don't care, just checking for headers!)
            manager.save(
                {
                    "foo": "bar",
                },
                idempotency_key=idempotency_key,
            )
        except XeroExceptionUnknown:
            pass

        headers = mock_post.mock_calls[0][2]["headers"]
        self.assertEqual(headers["Idempotency-Key"], idempotency_key)

    @patch("xero.basemanager.requests.put")
    def test_idempotency_key_on_put(self, mock_put):
        """An idempotency key can be included on a Manager.put() call."""
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("Invoices", credentials)
        idempotency_key = generate_idempotency_key()

        try:
            # Try/Except here because we're not actually talking to Xero
            # and PyXero will raise an error about not knowing what to do with
            # the response (we don't care, just checking for headers!)
            manager.put(
                {
                    "foo": "bar",
                },
                idempotency_key=idempotency_key,
            )
        except XeroExceptionUnknown:
            pass

        headers = mock_put.mock_calls[0][2]["headers"]
        self.assertEqual(headers["Idempotency-Key"], idempotency_key)

    @patch("xero.basemanager.requests.put")
    def test_idempotency_key_on_upload_attachment(self, mock_put):
        """An idempotency key can be included on a Manager.put_attachment() call."""
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("Invoices", credentials)
        idempotency_key = generate_idempotency_key()

        try:
            # Try/Except here because we're not actually talking to Xero
            # and PyXero will raise an error about not knowing what to do with
            # the response (we don't care, just checking for headers!)
            manager.put_attachment(
                id="foobar",
                filename="upload.pdf",
                content_type="application/pdf",
                file=BytesIO(b"foobar"),
                idempotency_key=idempotency_key,
            )
        except XeroExceptionUnknown:
            pass

        headers = mock_put.mock_calls[0][2]["headers"]
        self.assertEqual(headers["Idempotency-Key"], idempotency_key)

    @patch("xero.basemanager.requests.put")
    def test_history_note_is_string(self, _):
        """Manager.put_history expects a string as "details"."""

        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("Invoices", credentials)

        with self.assertRaises(TypeError):
            manager.put_history(
                id="foobar",
                details={
                    "foo": "bar",
                },
            )

    @patch("xero.basemanager.requests.post")
    def test_history_note_length(self, _):
        """History notes are limited to 2500 characters."""
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("Invoices", credentials)

        long_details = "a" * 2501
        with self.assertRaises(ValueError):
            # Try/Except here because we're not actually talking to Xero
            # and PyXero will raise an error about not knowing what to do with
            # the response (we don't care, just checking for headers!)
            manager.put_history(
                id="foobar",
                details=long_details,
            )

    @patch("xero.basemanager.requests.put")
    def test_idempotency_key_on_put_history(self, mock_put):
        """Generate a valid idempotency key and use it on a
        Manager.put_history() call. We should find the key stored as a request
        header called 'Idempotency-Key'.
        """
        credentials = Mock(base_url="", user_agent=None)
        manager = Manager("Invoices", credentials)
        idempotency_key = generate_idempotency_key()

        try:
            # Try/Except here because we're not actually talking to Xero
            # and PyXero will raise an error about not knowing what to do with
            # the response (we don't care, just checking for headers!)
            manager.put_history(
                id="foobar",
                details="This is a comment!",
                idempotency_key=idempotency_key,
            )
        except XeroExceptionUnknown:
            pass

        headers = mock_put.mock_calls[0][2]["headers"]
        self.assertEqual(headers["Idempotency-Key"], idempotency_key)
