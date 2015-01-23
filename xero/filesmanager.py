from __future__ import unicode_literals
from xml.dom.minidom import parseString
from xml.etree.ElementTree import tostring, SubElement, Element
from datetime import datetime
from dateutil.parser import parse
from decimal import Decimal
import requests
import json
from six.moves.urllib.parse import parse_qs
import six
from .constants import XERO_API_URL, XERO_FILES_URL
from .exceptions import *

class FilesManager(object):
    DECORATED_METHODS = (
        'get',
        'post',
        'filter',
        'put',
        )
    DATETIME_FIELDS = (
        'UpdatedDateUTC',
        'Updated',
        'FullyPaidOnDate',
        'DateTimeUTC',
        'CreatedDateUTC',
        )
    DATE_FIELDS = (
        'DueDate',
        'Date',
        'PaymentDate',
        'StartDate',
        'EndDate',
        'PeriodLockDate',
        'DateOfBirth',
        'OpeningBalanceDate',
        )
    BOOLEAN_FIELDS = (
        'IsSupplier',
        'IsCustomer',
        'IsDemoCompany',
        'PaysTax',
        'IsAuthorisedToApproveTimesheets',
        'IsAuthorisedToApproveLeave',
        'HasHELPDebt',
        'AustralianResidentForTaxPurposes',
        'TaxFreeThresholdClaimed',
        'HasSFSSDebt',
        'EligibleToReceiveLeaveLoading',
        'IsExemptFromTax',
        'IsExemptFromSuper',
        'SentToContact',
        )
    DECIMAL_FIELDS = ('Hours', 'NumberOfUnit')
    INTEGER_FIELDS = ('FinancialYearEndDay', 'FinancialYearEndMonth')
    PLURAL_EXCEPTIONS = {'Addresse': 'Address'}

    NO_SEND_FIELDS = ('UpdatedDateUTC',)

    def __init__(self, name, credentials):
        self.credentials = credentials
        self.name = name
        self.base_url = credentials.base_url + XERO_FILES_URL

        for method_name in self.DECORATED_METHODS:
            method = getattr(self, '_%s' % method_name)
            setattr(self, method_name, self._get_data(method))

    def _get_results(self, data):
        response = data['Response']
        if self.name in response:
            result = response[self.name]
        elif 'Attachments' in response:
            result = response['Attachments']
        else:
            return None

        if isinstance(result, tuple) or isinstance(result, list):
            return result

        if isinstance(result, dict) and self.singular in result:
            return result[self.singular]

    def _get_data(self, func):
        """ This is the decorator for our DECORATED_METHODS.
        Each of the decorated methods must return:
            uri, params, method, body, headers, singleobject
        """
        def wrapper(*args, **kwargs):
            uri, params, method, body, headers, singleobject = func(*args, **kwargs)

            cert = getattr(self.credentials, 'client_cert', None)
            response = getattr(requests, method)(
                    uri, data=body, headers=headers, auth=self.credentials.oauth,
                    params=params, cert=cert)

            if response.status_code == 200:
                if response.headers['content-type'].startswith('application/json'):             
                    return response.json()
                else:
                    # return a byte string without doing any Unicode conversions
                    return response.content

            elif response.status_code == 400:
                print(response.text)
                raise XeroBadRequest(response)

            elif response.status_code == 401:
                raise XeroUnauthorized(response)

            elif response.status_code == 403:
                raise XeroForbidden(response)

            elif response.status_code == 404:
                raise XeroNotFound(response)

            elif response.status_code == 500:
                raise XeroInternalError(response)

            elif response.status_code == 501:
                raise XeroNotImplemented(response)

            elif response.status_code == 503:
                # Two 503 responses are possible. Rate limit errors
                # return encoded content; offline errors don't.
                # If you parse the response text and there's nothing
                # encoded, it must be a not-available error.
                payload = parse_qs(response.text)
                if payload:
                    raise XeroRateLimitExceeded(response, payload)
                else:
                    raise XeroNotAvailable(response)
            else:
                raise XeroExceptionUnknown(response)

        return wrapper

    def _get(self, id=None, headers=None):
        if not id is None:
            uri = '/'.join([self.base_url, self.name, id])
        else:
            uri = '/'.join([self.base_url, self.name])
        return uri, {}, 'get', None, headers, True

    def _get_attachments(self, id):
        """Retrieve a list of attachments associated with this Xero object."""
        uri = '/'.join([self.base_url, self.name, id, 'Attachments']) + '/'
        return uri, {}, 'get', None, None, False

    def _get_attachment_data(self, id, filename):
        """
        Retrieve the contents of a specific attachment (identified by filename).
        """
        uri = '/'.join([self.base_url, self.name, id, 'Attachments', filename])
        return uri, {}, 'get', None, None, False

    def get_attachment(self, id, filename, file):
        """
        Retrieve the contents of a specific attachment (identified by filename).

        Writes data to file object, returns length of data written.
        """
        data = self.get_attachment_data(id, filename)
        file.write(data)
        return len(data)

    def save_or_put(self, data, method='post', headers=None, summarize_errors=True):
        if not data["Id"] is None:
            uri = '/'.join([self.base_url, self.name])
        else:
            uri = '/'.join([self.base_url, self.name, data["Id"]])

        print(uri)
        body = data        
        if summarize_errors:
            params = {}
        else:
            params = {'summarizeErrors': 'false'}
        return uri, params, method, body, headers, False

    def _post(self, data):
        return self.save_or_put(data, method='post')

    def _put(self, data, summarize_errors=True):
        return self.save_or_put(data, method='put', summarize_errors=summarize_errors)

    def prepare_filtering_date(self, val):
        if isinstance(val, datetime):
            val = val.strftime('%a, %d %b %Y %H:%M:%S GMT')
        else:
            val = '"%s"' % val
        return {'If-Modified-Since': val}

    def _filter(self, **kwargs):
        params = {}
        headers = None
        uri = '/'.join([self.base_url, self.name])
        if kwargs:
            if 'since' in kwargs:
                val = kwargs['since']
                headers = self.prepare_filtering_date(val)
                del kwargs['since']

            def get_filter_params(key, value):
                last_key = key.split('_')[-1]
                if last_key.upper().endswith('ID'):
                    return 'Guid("%s")' % six.text_type(value)

                if key in self.BOOLEAN_FIELDS:
                    return 'true' if value else 'false'
                elif key in self.DATETIME_FIELDS:
                    return value.isoformat()
                else:
                    return '"%s"' % six.text_type(value)

            def generate_param(key, value):
                parts = key.split("__")
                field = key.replace('_', '.')
                fmt = '%s==%s'
                if len(parts) == 2:
                    # support filters:
                    # Name__Contains=John becomes Name.Contains("John")
                    if parts[1] in ["contains", "startswith", "endswith"]:
                        field = parts[0]
                        fmt = ''.join(['%s.', parts[1], '(%s)'])
                    elif parts[1] in ["isnull"]:
                        sign = '=' if value else '!'
                        return '%s%s=null' % (parts[0], sign)

                return fmt % (
                    field,
                    get_filter_params(key, value)
                )

            # Move any known parameter names to the query string
            KNOWN_PARAMETERS = ['order', 'offset', 'page']
            for param in KNOWN_PARAMETERS:
                if param in kwargs:
                    params[param] = kwargs.pop(param)

            # Treat any remaining arguments as filter predicates
            # Xero will break if you search without a check for null in the first position:
            # http://developer.xero.com/documentation/getting-started/http-requests-and-responses/#title3
            sortedkwargs = sorted(six.iteritems(kwargs),
                    key=lambda item: -1 if 'isnull' in item[0] else 0)
            filter_params = [generate_param(key, value) for key, value in sortedkwargs]
            if filter_params:
                params['where'] = '&&'.join(filter_params)

        return uri, params, 'get', None, headers, False
