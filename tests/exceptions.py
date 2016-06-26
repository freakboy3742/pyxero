from __future__ import unicode_literals

import unittest

from datetime import date
from mock import Mock, patch

from xero import Xero
from xero.exceptions import (
    XeroBadRequest, XeroForbidden, XeroInternalError, XeroNotAvailable,
    XeroNotFound, XeroNotImplemented, XeroRateLimitExceeded, XeroUnauthorized
)

from . import mock_data


class ExceptionsTest(unittest.TestCase):

    @patch('requests.put')
    def test_bad_request(self, r_put):
        "Data with validation errors raises a bad request exception"
        # Verified response from the live API
        head = dict()
        head['content-type'] = 'text/xml; charset=utf-8'
        r_put.return_value = Mock(
            status_code=400,
            encoding='utf-8',
            text=mock_data.bad_request_text,
            headers=head
        )

        credentials = Mock(base_url="")
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

        except XeroBadRequest as e:
            # Error messages have been extracted
            self.assertEqual(str(e), 'A validation exception occurred')
            self.assertEqual(e.errors, [
                'One or more line items must be specified',
                'Invoice not of valid status for creation',
                'A Contact must be specified for this type of transaction',
            ])

            # The response has also been stored
            self.assertEqual(e.response.status_code, 400)
            self.assertTrue(e.response.text.startswith('<ApiException'))
        except Exception as e:
            self.fail("Should raise a XeroBadRequest, not %s" % e)

    @patch('requests.get')
    def test_unregistered_app(self, r_get):
        "An app without a signature raises a BadRequest exception, but with HTML payload"
        # Verified response from the live API
        head = dict()
        head['content-type'] = 'text/html; charset=utf-8'
        r_get.return_value = Mock(
            status_code=400,
            text='oauth_problem=signature_method_rejected&oauth_problem_advice=No%20certificates%20have%20been%20registered%20for%20the%20consumer',
            headers=head
        )

        credentials = Mock(base_url="")
        xero = Xero(credentials)

        try:
            xero.contacts.all()
            self.fail("Should raise a XeroUnauthorized.")

        except XeroBadRequest as e:
            # Error messages have been extracted
            self.assertEqual(str(e), 'No certificates have been registered for the consumer')
            self.assertEqual(e.errors[0], 'signature_method_rejected')

            # The response has also been stored
            self.assertEqual(e.response.status_code, 400)
            self.assertEqual(e.response.text, 'oauth_problem=signature_method_rejected&oauth_problem_advice=No%20certificates%20have%20been%20registered%20for%20the%20consumer')

        except Exception as e:
            self.fail("Should raise a XeroBadRequest, not %s" % e)

    @patch('requests.get')
    def test_unauthorized_invalid(self, r_get):
        "A session with an invalid token raises an unauthorized exception"
        # Verified response from the live API
        r_get.return_value = Mock(
            status_code=401,
            text='oauth_problem=signature_invalid&oauth_problem_advice=Failed%20to%20validate%20signature'
        )

        credentials = Mock(base_url="")
        xero = Xero(credentials)

        try:
            xero.contacts.all()
            self.fail("Should raise a XeroUnauthorized.")

        except XeroUnauthorized as e:
            # Error messages have been extracted
            self.assertEqual(str(e), 'Failed to validate signature')
            self.assertEqual(e.errors[0], 'signature_invalid')

            # The response has also been stored
            self.assertEqual(e.response.status_code, 401)
            self.assertEqual(e.response.text, 'oauth_problem=signature_invalid&oauth_problem_advice=Failed%20to%20validate%20signature')
        except Exception as e:
            self.fail("Should raise a XeroUnauthorized, not %s" % e)

    @patch('requests.get')
    def test_unauthorized_expired(self, r_get):
        "A session with an expired token raises an unauthorized exception"
        # Verified response from the live API
        r_get.return_value = Mock(
            status_code=401,
            text="oauth_problem=token_expired&oauth_problem_advice=The%20access%20token%20has%20expired"
        )

        credentials = Mock(base_url="")
        xero = Xero(credentials)

        try:
            xero.contacts.all()
            self.fail("Should raise a XeroUnauthorized.")

        except XeroUnauthorized as e:
            # Error messages have been extracted
            self.assertEqual(str(e), 'The access token has expired')
            self.assertEqual(e.errors[0], 'token_expired')

            # The response has also been stored
            self.assertEqual(e.response.status_code, 401)
            self.assertEqual(e.response.text, 'oauth_problem=token_expired&oauth_problem_advice=The%20access%20token%20has%20expired')
        except Exception as e:
            self.fail("Should raise a XeroUnauthorized, not %s" % e)

    @patch('requests.get')
    def test_forbidden(self, r_get):
        "In case of an SSL failure, a Forbidden exception is raised"
        # This is unconfirmed; haven't been able to verify this response from API.
        r_get.return_value = Mock(
            status_code=403,
            text="The client SSL certificate was not valid."
        )

        credentials = Mock(base_url="")
        xero = Xero(credentials)

        try:
            xero.contacts.all()
            self.fail("Should raise a XeroForbidden.")

        except XeroForbidden as e:
            # Error messages have been extracted
            self.assertEqual(str(e), "The client SSL certificate was not valid.")

            # The response has also been stored
            self.assertEqual(e.response.status_code, 403)
            self.assertEqual(e.response.text, "The client SSL certificate was not valid.")
        except Exception as e:
            self.fail("Should raise a XeroForbidden, not %s" % e)

    @patch('requests.get')
    def test_not_found(self, r_get):
        "If you request an object that doesn't exist, a Not Found exception is raised"
        # Verified response from the live API
        r_get.return_value = Mock(
            status_code=404,
            text="The resource you're looking for cannot be found"
        )

        credentials = Mock(base_url="")
        xero = Xero(credentials)

        try:
            xero.contacts.get(id='deadbeef')
            self.fail("Should raise a XeroNotFound.")

        except XeroNotFound as e:
            # Error messages have been extracted
            self.assertEqual(str(e), "The resource you're looking for cannot be found")

            # The response has also been stored
            self.assertEqual(e.response.status_code, 404)
            self.assertEqual(e.response.text, "The resource you're looking for cannot be found")
        except Exception as e:
            self.fail("Should raise a XeroNotFound, not %s" % e)

    @patch('requests.get')
    def test_internal_error(self, r_get):
        "In case of an SSL failure, a Forbidden exception is raised"
        # This is unconfirmed; haven't been able to verify this response from API.
        r_get.return_value = Mock(
            status_code=500,
            text='An unhandled error with the Xero API occurred. Contact the Xero API team if problems persist.'
        )

        credentials = Mock(base_url="")
        xero = Xero(credentials)

        try:
            xero.contacts.all()
            self.fail("Should raise a XeroInternalError.")

        except XeroInternalError as e:
            # Error messages have been extracted
            self.assertEqual(str(e), 'An unhandled error with the Xero API occurred. Contact the Xero API team if problems persist.')

            # The response has also been stored
            self.assertEqual(e.response.status_code, 500)
            self.assertEqual(e.response.text, 'An unhandled error with the Xero API occurred. Contact the Xero API team if problems persist.')
        except Exception as e:
            self.fail("Should raise a XeroInternalError, not %s" % e)

    @patch('requests.post')
    def test_not_implemented(self, r_post):
        "In case of an SSL failure, a Forbidden exception is raised"
        # Verified response from the live API
        r_post.return_value = Mock(
            status_code=501,
            encoding='utf-8',
            text=mock_data.not_implemented_text
        )

        credentials = Mock(base_url="")
        xero = Xero(credentials)

        try:
            xero.organisations.save({})
            self.fail("Should raise a XeroNotImplemented.")

        except XeroNotImplemented as e:
            # Error messages have been extracted
            self.assertEqual(str(e), 'The Api Method called is not implemented')

            # The response has also been stored
            self.assertEqual(e.response.status_code, 501)
            self.assertTrue(e.response.text.startswith, '<ApiException')
        except Exception as e:
            self.fail("Should raise a XeroNotImplemented, not %s" % e)

    @patch('requests.get')
    def test_rate_limit_exceeded(self, r_get):
        "If you exceed the rate limit, an exception is raised."
        # Response based off Xero documentation; not confirmed by reality.
        r_get.return_value = Mock(
            status_code=503,
            text="oauth_problem=rate%20limit%20exceeded&oauth_problem_advice=please%20wait%20before%20retrying%20the%20xero%20api"
        )

        credentials = Mock(base_url="")
        xero = Xero(credentials)

        try:
            xero.contacts.all()
            self.fail("Should raise a XeroRateLimitExceeded.")

        except XeroRateLimitExceeded as e:
            # Error messages have been extracted
            self.assertEqual(str(e), 'please wait before retrying the xero api')
            self.assertEqual(e.errors[0], 'rate limit exceeded')

            # The response has also been stored
            self.assertEqual(e.response.status_code, 503)
            self.assertEqual(e.response.text, "oauth_problem=rate%20limit%20exceeded&oauth_problem_advice=please%20wait%20before%20retrying%20the%20xero%20api")
        except Exception as e:
            self.fail("Should raise a XeroRateLimitExceeded, not %s" % e)

    @patch('requests.get')
    def test_not_available(self, r_get):
        "If Xero goes down for maintenance, an exception is raised"
        # Response based off Xero documentation; not confirmed by reality.
        r_get.return_value = Mock(
            status_code=503,
            text="The Xero API is currently offline for maintenance"
        )

        credentials = Mock(base_url="")
        xero = Xero(credentials)

        try:
            xero.contacts.all()
            self.fail("Should raise a XeroNotAvailable.")

        except XeroNotAvailable as e:
            # Error messages have been extracted
            self.assertEqual(str(e), "The Xero API is currently offline for maintenance")

            # The response has also been stored
            self.assertEqual(e.response.status_code, 503)
            self.assertEqual(e.response.text, "The Xero API is currently offline for maintenance")
        except Exception as e:
            self.fail("Should raise a XeroNotAvailable, not %s" % e)
