from __future__ import unicode_literals

import os
import requests
from six.moves.urllib.parse import parse_qs

from .constants import XERO_PROJECTS_URL
from .exceptions import (
    XeroBadRequest,
    XeroExceptionUnknown,
    XeroForbidden,
    XeroInternalError,
    XeroNotAvailable,
    XeroNotFound,
    XeroNotImplemented,
    XeroRateLimitExceeded,
    XeroUnauthorized,
    XeroUnsupportedMediaType,
)


class ProjectManager(object):
    DECORATED_METHODS = (
        "get",
        "all",
        "create",
        "delete",
        "get_tasks",
        "get_time",
        "set_status",
    )

    def __init__(self, name, credentials):
        self.credentials = credentials
        self.name = name
        self.base_url = credentials.base_url + XERO_PROJECTS_URL

        for method_name in self.DECORATED_METHODS:
            method = getattr(self, "_%s" % method_name)
            setattr(self, method_name, self._get_data(method))

    def _get_results(self, data):
        response = data["Response"]
        if self.name in response:
            result = response[self.name]
        elif "Attachments" in response:
            result = response["Attachments"]
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
            uri, params, method, body, headers, singleobject, files = func(
                *args, **kwargs
            )

            response = getattr(requests, method)(
                uri,
                data=body,
                headers=headers,
                auth=self.credentials.oauth,
                params=params,
                files=files,
            )

            if response.status_code == 200 or response.status_code == 201:
                if response.headers["content-type"].startswith("application/json"):
                    return response.json()
                else:
                    # return a byte string without doing any Unicode conversions
                    return response.content

            # Delete will return a response code of 204 - No Content
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
        uri = "/".join([self.base_url, self.name, id])
        return uri, {}, "get", None, headers, True, None

    def _get_tasks(self, projectId):
        """Retrieve the list of tasks contained in a project"""
        uri = "/".join([self.base_url, self.name, projectId, "Tasks"])
        return uri, {}, "get", None, None, False, None

    def _get_time(self, projectId):
        """Retrieve the list of times contained in a project"""
        uri = "/".join([self.base_url, self.name, projectId, "Time"])
        return uri, {}, "get", None, None, False, None

    def _set_status(self, projectId, data):
        uri = "/".join([self.base_url, self.name, projectId])
        body = data
        return uri, {}, "patch", body, None, False, None

    def create_or_save(self, data, method="post", headers=None, summarize_errors=True):
        if "Id" not in data:
            uri = "/".join([self.base_url, self.name])
        else:
            uri = "/".join([self.base_url, self.name, data["Id"]])
        body = data
        if summarize_errors:
            params = {}
        else:
            params = {"summarizeErrors": "false"}
        return uri, params, method, body, headers, False, None

    def _create(self, data):
        return self.create_or_save(data, method="post")

    def _delete(self, id):
        uri = "/".join([self.base_url, self.name, id])
        return uri, {}, "delete", None, None, False, None

    def _all(self):
        uri = "/".join([self.base_url, self.name])
        return uri, {}, "get", None, None, False, None

    def filename(self, path):
        head, tail = os.path.split(path)
        return tail or os.path.basename(head)
