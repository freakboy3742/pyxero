from __future__ import unicode_literals

import requests
from six.moves.urllib.parse import parse_qs

from .constants import XERO_BANK_FEEDS_URL
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


class BankFeedsManager(object):
    DECORATED_METHODS = ("get", "all", "create", "delete_requests")

    def __init__(self, name, credentials):
        self.credentials = credentials
        self.name = name
        self.base_url = credentials.base_url + XERO_BANK_FEEDS_URL

        for method_name in self.DECORATED_METHODS:
            method = getattr(self, "_%s" % method_name)
            setattr(self, method_name, self._get_data(method))

    def _get_data(self, func):
        """ This is the decorator for our DECORATED_METHODS.
        Each of the decorated methods must return:
            uri, params, method, body, headers, singleobject
        """

        def wrapper(*args, **kwargs):
            uri, params, method, body, headers, singleobject = func(*args, **kwargs)

            response = getattr(requests, method)(
                uri,
                data=body,
                headers=headers,
                auth=self.credentials.oauth,
                params=params,
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

    def _create(self, data, method="post", headers=None, summarize_errors=True):
        uri = "/".join([self.base_url, self.name])
        body = data
        if summarize_errors:
            params = {}
        else:
            params = {"summarizeErrors": "false"}
        return uri, params, method, body, headers, False, None

    def _all(self):
        uri = "/".join([self.base_url, self.name])
        return uri, {}, "get", None, None, False

    def _delete_requests(self, data):
        uri = "/".join([self.base_url, self.name, "DeleteRequests"])
        return uri, {}, "post", data, None, False
