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
        'all',
        'post',
        'filter',
        'put',
        'delete',
        'get_files',
        'upload_file',
        #'get_association',
        #'get_associations',
        #'get_content',
        )
    DATETIME_FIELDS = (
        'UpdatedDateUTC',
        'CreatedDateUTC',
        )
    DATE_FIELDS = ()
    BOOLEAN_FIELDS = (
        'IsInbox',
        )
    DECIMAL_FIELDS = ('Hours', 'NumberOfUnit')
    INTEGER_FIELDS = ('Size', 'FileCount')
    NO_SEND_FIELDS = ('UpdatedDateUTC', 'User')

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
            uri, params, method, body, headers, singleobject, files = func(*args, **kwargs)

            cert = getattr(self.credentials, 'client_cert', None)
            response = getattr(requests, method)(
                    uri, data=body, headers=headers, auth=self.credentials.oauth,
                    params=params, cert=cert, files = files)

            if response.status_code == 200 or response.status_code == 201:
                if response.headers['content-type'].startswith('application/json'):             
                    return response.json()
                else:
                    # return a byte string without doing any Unicode conversions
                    return response.content

            #Delete will return a response code of 204 - No Content
            elif response.status_code == 204:
                return "Deleted"

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

    def _get(self, id=None, headers=None):
        if not id is None:
            uri = '/'.join([self.base_url, self.name, id])
        else:
            uri = '/'.join([self.base_url, self.name])
        return uri, {}, 'get', None, headers, True, None

    def _get_files(self, folderId):
        """Retrieve the list of files contained in a folder"""
        uri = '/'.join([self.base_url, self.name, folderId, 'Files'])
        return uri, {}, 'get', None, None, False, None

    def _get_associations(self, id):
        """Retrieve a list of attachments associated with this Xero object."""
        uri = '/'.join([self.base_url, self.name, id, 'Associations']) + '/'
        return uri, {}, 'get', None, None, False, None

    def _get_association(self, fileId, objectId):
        """
        Retrieve the contents of a specific attachment (identified by filename).
        """
        uri = '/'.join([self.base_url, self.name, fileId, 'Associations', objectId])
        return uri, {}, 'get', None, None, False, None

    def save_or_put(self, data, method='post', headers=None, summarize_errors=True):
        if not "Id" in data:
            uri = '/'.join([self.base_url, self.name])
        else:
            uri = '/'.join([self.base_url, self.name, data["Id"]])
        body = data        
        if summarize_errors:
            params = {}
        else:
            params = {'summarizeErrors': 'false'}
        return uri, params, method, body, headers, False, None

    def _post(self, data):
        return self.save_or_put(data, method='post')

    def _put(self, data, summarize_errors=True):
        return self.save_or_put(data, method='put', summarize_errors=summarize_errors)

    def _delete(self, id):
        uri = '/'.join([self.base_url, self.name, id])
        return uri, {}, 'delete', None, None, False, None

    def _upload_file(self, path, folderId=None):
        if not folderId is None:
            uri = '/'.join([self.base_url, self.name, folderId])
        else:    
            uri = '/'.join([self.base_url, self.name])
        files = dict()
        files['File'] = open(path, mode="rb")
            
        return uri, {}, 'post', None, None, False, files


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

        return uri, params, 'get', None, headers, False, None

    def _all(self):
        uri = '/'.join([self.base_url, self.name])
        return uri, {}, 'get', None, None, False, None
