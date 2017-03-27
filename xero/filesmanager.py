from __future__ import unicode_literals

import os
import requests

from six.moves.urllib.parse import parse_qs

from .constants import XERO_FILES_URL
from .exceptions import (
    XeroBadRequest, XeroExceptionUnknown, XeroForbidden, XeroInternalError,
    XeroNotAvailable, XeroNotFound, XeroNotImplemented, XeroRateLimitExceeded,
    XeroUnauthorized, XeroUnsupportedMediaType
)


class FilesManager(object):
    DECORATED_METHODS = (
        'get',
        'all',
        'create',
        'save',
        'delete',
        'get_files',
        'upload_file',
        'get_association',
        'get_associations',
        'make_association',
        'delete_association',
        'get_content',
        )
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

            response = getattr(requests, method)(
                    uri, data=body, headers=headers, auth=self.credentials.oauth,
                    params=params, files=files)

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

            elif response.status_code == 415:
                raise XeroUnsupportedMediaType(response)

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
        return uri, {}, 'get', None, headers, True, None

    def _get_files(self, folderId):
        """Retrieve the list of files contained in a folder"""
        uri = '/'.join([self.base_url, self.name, folderId, 'Files'])
        return uri, {}, 'get', None, None, False, None

    def _get_associations(self, id):
        uri = '/'.join([self.base_url, self.name, id, 'Associations']) + '/'
        return uri, {}, 'get', None, None, False, None

    def _get_association(self, fileId, objectId):
        uri = '/'.join([self.base_url, self.name, fileId, 'Associations', objectId])
        return uri, {}, 'get', None, None, False, None

    def _delete_association(self, fileId, objectId):
        uri = '/'.join([self.base_url, self.name, fileId, 'Associations', objectId])
        return uri, {}, 'delete', None, None, False, None


    def create_or_save(self, data, method='post', headers=None, summarize_errors=True):
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

    def _create(self, data):
        return self.create_or_save(data, method='post')

    def _save(self, data, summarize_errors=True):
        return self.create_or_save(data, method='put', summarize_errors=summarize_errors)

    def _delete(self, id):
        uri = '/'.join([self.base_url, self.name, id])
        return uri, {}, 'delete', None, None, False, None

    def _upload_file(self, path, folderId=None):
        if not folderId is None:
            uri = '/'.join([self.base_url, self.name, folderId])
        else:
            uri = '/'.join([self.base_url, self.name])
        filename = self.filename(path)

        files = dict()
        files[filename] = open(path, mode="rb")

        return uri, {}, 'post', None, None, False, files

    def _get_content(self, fileId):
        uri = '/'.join([self.base_url, self.name, fileId, "Content"])
        return uri, {}, 'get', None, None, False, None

    def _make_association(self, id, data):
        uri = '/'.join([self.base_url, self.name, id, 'Associations'])
        body = data
        return uri, {}, 'post', body, None, False, None

    def _all(self):
        uri = '/'.join([self.base_url, self.name])
        return uri, {}, 'get', None, None, False, None

    def filename(self, path):
        head, tail = os.path.split(path)
        return tail or os.path.basename(head)
