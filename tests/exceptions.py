from __future__ import unicode_literals

from datetime import date
import unittest
from xml.dom.minidom import parseString

from mock import Mock, patch

from xero import Xero
from xero.exceptions import *


class ExceptionsTest(unittest.TestCase):

    @patch('requests.put')
    def test_bad_request(self, r_put):
        "Data with validation errors raises a bad request exception"
        # Verified response from the live API
        r_put.return_value = Mock(status_code=400, text="""<ApiException xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <ErrorNumber>10</ErrorNumber>
  <Type>ValidationException</Type>
  <Message>A validation exception occurred</Message>
  <Elements>
    <DataContractBase xsi:type="Invoice">
      <ValidationErrors>
        <ValidationError>
          <Message>One or more line items must be specified</Message>
        </ValidationError>
        <ValidationError>
          <Message>Invoice not of valid status for creation</Message>
        </ValidationError>
        <ValidationError>
          <Message>A Contact must be specified for this type of transaction</Message>
        </ValidationError>
      </ValidationErrors>
      <Warnings />
      <Date>2013-04-29T00:00:00</Date>
      <DueDate>2013-04-29T00:00:00</DueDate>
      <BrandingThemeID xsi:nil="true" />
      <Status>PAID</Status>
      <LineAmountTypes>Exclusive</LineAmountTypes>
      <LineItems />
      <SubTotal>18.00</SubTotal>
      <TotalTax>1.05</TotalTax>
      <Total>19.05</Total>
      <UpdatedDateUTC xsi:nil="true" />
      <CurrencyCode>AUD</CurrencyCode>
      <FullyPaidOnDate xsi:nil="true" />
      <Type>ACCREC</Type>
      <InvoiceID>00000000-0000-0000-0000-000000000000</InvoiceID>
      <Reference>Order # 123456</Reference>
      <Payments />
      <CreditNotes />
      <AmountDue>0.00</AmountDue>
      <AmountPaid>19.05</AmountPaid>
      <AmountCredited xsi:nil="true" />
      <SentToContact xsi:nil="true" />
      <CurrencyRate xsi:nil="true" />
      <TotalDiscount xsi:nil="true" />
      <HasAttachments xsi:nil="true" />
      <Attachments />
    </DataContractBase>
  </Elements>
</ApiException>""")

        credentials = Mock()
        xero = Xero(credentials)

        try:
            xero.invoices.put({
                'Type': 'ACCREC',
                'LineAmountTypes': 'Exclusive',
                'Date': date(2013, 4, 29),
                'DueDate': date(2013, 4, 29),
                'Reference': 'Order # 123456',
                'Status': 'PAID',
                'AmountPaid': '19.05',
                'TotalTax': '1.05',
                'AmountDue': '0.00',
                'Total': '19.05',
                'SubTotal': '18.00',
            })
            self.fail("Should raise a XeroBadRequest.")

        except XeroBadRequest, e:
            # Error messages have been extracted
            self.assertEqual(e.message, 'A validation exception occurred')
            self.assertEqual(e.errors, [
                'One or more line items must be specified',
                'Invoice not of valid status for creation',
                'A Contact must be specified for this type of transaction',
            ])

            # The response has also been stored
            self.assertEqual(e.response.status_code, 400)
            self.assertTrue(e.response.text.startswith('<ApiException'))
        except Exception, e:
            self.fail("Should raise a XeroBadRequest, not %s" % e)

    @patch('requests.get')
    def test_unauthorized_invalid(self, r_get):
        "A session with an invalid token raises an unauthorized exception"
        # Verified response from the live API
        r_get.return_value = Mock(status_code=401, text='oauth_problem=signature_invalid&oauth_problem_advice=Failed%20to%20validate%20signature')

        credentials = Mock()
        xero = Xero(credentials)

        try:
            xero.contacts.all()
            self.fail("Should raise a XeroUnauthorized.")

        except XeroUnauthorized, e:
            # Error messages have been extracted
            self.assertEqual(e.message, 'Failed to validate signature')
            self.assertEqual(e.problem, 'signature_invalid')

            # The response has also been stored
            self.assertEqual(e.response.status_code, 401)
            self.assertEqual(e.response.text, 'oauth_problem=signature_invalid&oauth_problem_advice=Failed%20to%20validate%20signature')
        except Exception, e:
            self.fail("Should raise a XeroUnauthorized, not %s" % e)

    @patch('requests.get')
    def test_unauthorized_expired(self, r_get):
        "A session with an expired token raises an unauthorized exception"
        # Verified response from the live API
        r_get.return_value = Mock(status_code=401, text="oauth_problem=token_expired&oauth_problem_advice=The%20access%20token%20has%20expired")

        credentials = Mock()
        xero = Xero(credentials)

        try:
            xero.contacts.all()
            self.fail("Should raise a XeroUnauthorized.")

        except XeroUnauthorized, e:
            # Error messages have been extracted
            self.assertEqual(e.message, 'The access token has expired')
            self.assertEqual(e.problem, 'token_expired')

            # The response has also been stored
            self.assertEqual(e.response.status_code, 401)
            self.assertEqual(e.response.text, 'oauth_problem=token_expired&oauth_problem_advice=The%20access%20token%20has%20expired')
        except Exception, e:
            self.fail("Should raise a XeroUnauthorized, not %s" % e)

    @patch('requests.get')
    def test_forbidden(self, r_get):
        "In case of an SSL failure, a Forbidden exception is raised"
        # This is unconfirmed; haven't been able to verify this response from API.
        r_get.return_value = Mock(status_code=403, text="The client SSL certificate was not valid.")

        credentials = Mock()
        xero = Xero(credentials)

        try:
            xero.contacts.all()
            self.fail("Should raise a XeroForbidden.")

        except XeroForbidden, e:
            # Error messages have been extracted
            self.assertEqual(e.message, "The client SSL certificate was not valid.")

            # The response has also been stored
            self.assertEqual(e.response.status_code, 403)
            self.assertEqual(e.response.text, "The client SSL certificate was not valid.")
        except Exception, e:
            self.fail("Should raise a XeroForbidden, not %s" % e)

    @patch('requests.get')
    def test_not_found(self, r_get):
        "If you request an object that doesn't exist, a Not Found exception is raised"
        # Verified response from the live API
        r_get.return_value = Mock(status_code=404, text="The resource you're looking for cannot be found")

        credentials = Mock()
        xero = Xero(credentials)

        try:
            xero.contacts.get(id='deadbeef')
            self.fail("Should raise a XeroNotFound.")

        except XeroNotFound, e:
            # Error messages have been extracted
            self.assertEqual(e.message, "The resource you're looking for cannot be found")

            # The response has also been stored
            self.assertEqual(e.response.status_code, 404)
            self.assertEqual(e.response.text, "The resource you're looking for cannot be found")
        except Exception, e:
            self.fail("Should raise a XeroNotFound, not %s" % e)

    @patch('requests.get')
    def test_internal_error(self, r_get):
        "In case of an SSL failure, a Forbidden exception is raised"
        # This is unconfirmed; haven't been able to verify this response from API.
        r_get.return_value = Mock(status_code=500, text='An unhandled error with the Xero API occurred. Contact the Xero API team if problems persist.')

        credentials = Mock()
        xero = Xero(credentials)

        try:
            xero.contacts.all()
            self.fail("Should raise a XeroInternalError.")

        except XeroInternalError, e:
            # Error messages have been extracted
            self.assertEqual(e.message, 'An unhandled error with the Xero API occurred. Contact the Xero API team if problems persist.')

            # The response has also been stored
            self.assertEqual(e.response.status_code, 500)
            self.assertEqual(e.response.text, 'An unhandled error with the Xero API occurred. Contact the Xero API team if problems persist.')
        except Exception, e:
            self.fail("Should raise a XeroInternalError, not %s" % e)

    @patch('requests.post')
    def test_not_implemented(self, r_post):
        "In case of an SSL failure, a Forbidden exception is raised"
        # Verified response from the live API
        r_post.return_value = Mock(status_code=501, text="""<ApiException xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <ErrorNumber>20</ErrorNumber>
    <Type>ApiMethodNotImplementedException</Type>
    <Message>The Api Method called is not implemented</Message>
</ApiException>""")

        credentials = Mock()
        xero = Xero(credentials)

        try:
            xero.organisation.save({})
            self.fail("Should raise a XeroNotImplemented.")

        except XeroNotImplemented, e:
            # Error messages have been extracted
            self.assertEqual(e.message, 'The Api Method called is not implemented')

            # The response has also been stored
            self.assertEqual(e.response.status_code, 501)
            self.assertTrue(e.response.text.startswith, '<ApiException')
        except Exception, e:
            self.fail("Should raise a XeroNotImplemented, not %s" % e)

    @patch('requests.get')
    def test_rate_limit_exceeded(self, r_get):
        "If you exceed the rate limit, an exception is raised."
        # Response based off Xero documentation; not confirmed by reality.
        r_get.return_value = Mock(status_code=503, text="oauth_problem=rate%20limit%20exceeded&oauth_problem_advice=please%20wait%20before%20retrying%20the%20xero%20api")

        credentials = Mock()
        xero = Xero(credentials)

        try:
            xero.contacts.all()
            self.fail("Should raise a XeroRateLimitExceeded.")

        except XeroRateLimitExceeded, e:
            # Error messages have been extracted
            self.assertEqual(e.message, 'please wait before retrying the xero api')
            self.assertEqual(e.problem, 'rate limit exceeded')

            # The response has also been stored
            self.assertEqual(e.response.status_code, 503)
            self.assertEqual(e.response.text, "oauth_problem=rate%20limit%20exceeded&oauth_problem_advice=please%20wait%20before%20retrying%20the%20xero%20api")
        except Exception, e:
            self.fail("Should raise a XeroRateLimitExceeded, not %s" % e)

    @patch('requests.get')
    def test_not_available(self, r_get):
        "If Xero goes down for maintenance, an exception is raised"
        # Response based off Xero documentation; not confirmed by reality.
        r_get.return_value = Mock(status_code=503, text="The Xero API is currently offline for maintenance")

        credentials = Mock()
        xero = Xero(credentials)

        try:
            xero.contacts.all()
            self.fail("Should raise a XeroNotAvailable.")

        except XeroNotAvailable, e:
            # Error messages have been extracted
            self.assertEqual(e.message, "The Xero API is currently offline for maintenance")

            # The response has also been stored
            self.assertEqual(e.response.status_code, 503)
            self.assertEqual(e.response.text, "The Xero API is currently offline for maintenance")
        except Exception, e:
            self.fail("Should raise a XeroNotAvailable, not %s" % e)

