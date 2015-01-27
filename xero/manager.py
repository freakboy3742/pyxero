from __future__ import unicode_literals
from xml.dom.minidom import parseString
from xml.etree.ElementTree import tostring, SubElement, Element
from datetime import datetime
from dateutil.parser import parse
from decimal import Decimal
import requests
from six.moves.urllib.parse import parse_qs
import six
from .constants import XERO_API_URL
from .exceptions import *

def isplural(word):
    return word[-1].lower() == 's'

def singular(word):
    if isplural(word):
        return word[:-1]
    return word


class Manager(object):
    DECORATED_METHODS = (
        'get',
        'save',
        'filter',
        'all',
        'put',
        'get_attachments',
        'get_attachment_data',
        'put_attachment_data',
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
        self.base_url = credentials.base_url + XERO_API_URL

        # setup our singular variants of the name
        # only if the name ends in 's'
        if name[-1] == "s":
            self.singular = name[:len(name)-1]
        else:
            self.singular = name

        for method_name in self.DECORATED_METHODS:
            method = getattr(self, '_%s' % method_name)
            setattr(self, method_name, self._get_data(method))

    def walk_dom(self, dom):
        tree_list = tuple()
        for node in dom.childNodes:
            tagName = getattr(node, 'tagName', None)
            if tagName:
                tree_list += (tagName, self.walk_dom(node),)
            else:
                data = node.data.strip()
                if data:
                    tree_list += (node.data.strip(),)
        return tree_list

    def convert_to_dict(self, deep_list):
        out = {}

        if len(deep_list) > 2:
            lists = [l for l in deep_list if isinstance(l, tuple)]
            keys = [l for l in deep_list if isinstance(l, six.string_types)]

            if len(keys) > 1 and len(set(keys)) == 1:
                # This is a collection... all of the keys are the same.
                return [self.convert_to_dict(data) for data in lists]

            for key, data in zip(keys, lists):
                if not data:
                    # Skip things that are empty tags?
                    continue

                if len(data) == 1:
                    # we're setting a value
                    # check to see if we need to apply any special
                    # formatting to the value
                    val = data[0]
                    if key in self.DECIMAL_FIELDS:
                        val = Decimal(val)
                    elif key in self.BOOLEAN_FIELDS:
                        val = True if val.lower() == 'true' else False
                    elif key in self.DATETIME_FIELDS:
                        val = parse(val)
                    elif key in self.DATE_FIELDS:
                        if val.isdigit():
                          val = int(val)
                        else:
                          val = parse(val).date()
                    elif key in self.INTEGER_FIELDS:
                        val = int(val)
                    data = val
                else:
                    # We have a deeper data structure, that we need
                    # to recursively process.
                    data = self.convert_to_dict(data)
                    # Which may itself be a collection. Quick, check!
                    if isinstance(data, dict) and isplural(key) and [singular(key)] == data.keys():
                        data = [data[singular(key)]]

                out[key] = data

        elif len(deep_list) == 2:
            key = deep_list[0]
            data = self.convert_to_dict(deep_list[1])

            # If our key is repeated in our child object, but in singular
            # form (and is the only key), then this object is a collection.
            if isplural(key) and [singular(key)] == data.keys():
                data = [data[singular(key)]]

            out[key] = data
        else:
            out = deep_list[0]
        return out

    def dict_to_xml(self, root_elm, data):
        for key in data.keys():
            # Xero will complain if we send back these fields.
            if key in self.NO_SEND_FIELDS:
                continue

            sub_data = data[key]
            elm = SubElement(root_elm, key)

            is_list = isinstance(sub_data, list) or isinstance(sub_data, tuple)
            is_plural = key[len(key)-1] == "s"
            plural_name = key[:len(key)-1]

            # Key references a dict. Unroll the dict
            # as it's own XML node with subnodes
            if isinstance(sub_data, dict):
                self.dict_to_xml(elm, sub_data)

            # Key references a list/tuple
            elif is_list:
                # key name is a plural. This means each item
                # in the list needs to be wrapped in an XML
                # node that is a singular version of the list name.
                if is_plural:
                    for d in sub_data:
                        plural_name = self.PLURAL_EXCEPTIONS.get(plural_name, plural_name)
                        self.dict_to_xml(SubElement(elm, plural_name), d)

                # key name isn't a plural. Just insert the content
                # as an XML node with subnodes
                else:
                    for d in sub_data:
                        self.dict_to_xml(elm, d)

            # Normal element - just insert the data.
            else:
                if key in self.BOOLEAN_FIELDS:
                    val = 'true' if sub_data else 'false'
                else:
                    val = six.text_type(sub_data)
                elm.text = val

        return root_elm

    def _prepare_data_for_save(self, data):
        if isinstance(data, list) or isinstance(data, tuple):
            root_elm = Element(self.name)
            for d in data:
                sub_elm = SubElement(root_elm, self.singular)
                self.dict_to_xml(sub_elm, d)
        else:
            root_elm = self.dict_to_xml(Element(self.singular), data)

        return tostring(root_elm)

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
                if not response.headers['content-type'].startswith('text/xml'):
                    # return a byte string without doing any Unicode conversions
                    return response.content
                # parseString takes byte content, not unicode.
                dom = parseString(response.text.encode(response.encoding))
                data = self.convert_to_dict(self.walk_dom(dom))
                results = self._get_results(data)
                # If we're dealing with Manager.get, return a single object.
                if singleobject and isinstance(results, list):
                    return results[0]
                return results

            elif response.status_code == 400:
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

    def _get(self, id, headers=None):
        uri = '/'.join([self.base_url, self.name, id])
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
        uri = '/'.join([self.base_url, self.name])
        body = {'xml': self._prepare_data_for_save(data)}
        if summarize_errors:
            params = {}
        else:
            params = {'summarizeErrors': 'false'}
        return uri, params, method, body, headers, False

    def _save(self, data):
        return self.save_or_put(data, method='post')

    def _put(self, data, summarize_errors=True):
        return self.save_or_put(data, method='put', summarize_errors=summarize_errors)

    def _put_attachment_data(self, id, filename, data, content_type, include_online=False):
        """Upload an attachment to the Xero object."""
        uri = '/'.join([self.base_url, self.name, id, 'Attachments', filename])
        params = {'IncludeOnline': 'true'} if include_online else {}
        headers = {'Content-Type': content_type, 'Content-Length': len(data)}
        return uri, params, 'put', data, headers, False

    def put_attachment(self, id, filename, file, content_type, include_online=False):
        """Upload an attachment to the Xero object (from file object)."""
        self.put_attachment_data(id, filename, file.read(), content_type,
                                 include_online=include_online)

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

    def _all(self):
        uri = '/'.join([self.base_url, self.name])
        return uri, {}, 'get', None, None, False
