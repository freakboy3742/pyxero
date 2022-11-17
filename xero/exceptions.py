import json
from six.moves.urllib.parse import parse_qs
from xml.dom.minidom import parseString


class XeroException(Exception):
    def __init__(self, response, msg=None):
        self.response = response
        super(XeroException, self).__init__(msg)


class XeroNotVerified(Exception):
    # Credentials haven't been verified
    pass


class XeroAccessDenied(Exception):
    # Access was denied
    pass


class XeroTenantIdNotSet(Exception):
    # Tenant Id must be set when using API with OAuth2 credentials
    pass


class XeroBadRequest(XeroException):
    # HTTP 400: Bad Request
    def __init__(self, response):
        if response.headers["content-type"].startswith("application/json"):
            data = json.loads(response.text)
            msg = "%s: %s" % (
                data.get("Type", "Unknown"),
                data.get("Message", "Not provided"),
            )
            self.errors = [
                err["Message"]
                for elem in data.get("Elements", [])
                for err in elem.get("ValidationErrors", [])
            ]
            if len(self.errors) > 0:
                self.problem = self.errors[0]
                if len(self.errors) > 1:
                    msg += " (%s, and %s other issues)" % (
                        self.problem,
                        len(self.errors),
                    )
                else:
                    msg += " (%s)" % self.problem
            else:
                self.problem = None
            super(XeroBadRequest, self).__init__(response, msg=msg)

        elif response.headers["content-type"].startswith("application/problem+json"):
            data = json.loads(response.text)
            msg = ""
            self.errors = [
                err["detail"]
                for item in data.get("items", [])
                for err in item.get("errors", [])
            ]
            if len(self.errors) > 0:
                self.problem = self.errors[0]
                if len(self.errors) > 1:
                    msg += " (%s, and %s other issues)" % (
                        self.problem,
                        len(self.errors),
                    )
                else:
                    msg += " (%s)" % self.problem
            else:
                self.problem = None
            super(XeroBadRequest, self).__init__(response, msg=msg)

        elif response.headers["content-type"].startswith("text/html"):
            payload = parse_qs(response.text)
            self.errors = [payload["oauth_problem"][0]]
            self.problem = self.errors[0]
            super(XeroBadRequest, self).__init__(
                response, payload["oauth_problem_advice"][0]
            )

        else:
            # Extract the messages from the text.
            # parseString takes byte content, not unicode.
            dom = parseString(response.text.encode(response.encoding))
            messages = dom.getElementsByTagName("Message")

            msg = messages[0].childNodes[0].data
            self.errors = [m.childNodes[0].data for m in messages[1:]]
            self.problem = self.errors[0]
            super(XeroBadRequest, self).__init__(response, msg)


class XeroUnauthorized(XeroException):
    # HTTP 401: Unauthorized
    def __init__(self, response):
        payload = parse_qs(response.text)
        problems = payload.get("oauth_problem", [])
        self.errors = problems[0] if problems else []
        self.problem = self.errors[0] if self.errors else None
        advice = payload.get("oauth_problem_advice", [])
        super(XeroUnauthorized, self).__init__(response, advice[0] if advice else None)


class XeroForbidden(XeroException):
    # HTTP 403: Forbidden
    def __init__(self, response):
        super(XeroForbidden, self).__init__(response, response.text)


class XeroNotFound(XeroException):
    # HTTP 404: Not Found
    def __init__(self, response):
        super(XeroNotFound, self).__init__(response, response.text)


class XeroUnsupportedMediaType(XeroException):
    # HTTP 415: UnsupportedMediaType
    def __init__(self, response):
        super(XeroUnsupportedMediaType, self).__init__(response, response.text)


class XeroInternalError(XeroException):
    # HTTP 500: Internal Error
    def __init__(self, response):
        super(XeroInternalError, self).__init__(response, response.text)


class XeroNotImplemented(XeroException):
    # HTTP 501
    def __init__(self, response):
        # Extract the useful error message from the text.
        # parseString takes byte content, not unicode.
        dom = parseString(response.text.encode(response.encoding))
        messages = dom.getElementsByTagName("Message")

        msg = messages[0].childNodes[0].data
        super(XeroNotImplemented, self).__init__(response, msg)


class XeroRateLimitExceeded(XeroException):
    # HTTP 503 - Rate limit exceeded
    def __init__(self, response, payload):
        try:
            self.errors = [payload["oauth_problem"][0]]
        except KeyError:
            return super(XeroRateLimitExceeded, self).__init__(response, response.text)
        self.problem = self.errors[0]
        super(XeroRateLimitExceeded, self).__init__(
            response, payload["oauth_problem_advice"][0]
        )


class XeroNotAvailable(XeroException):
    # HTTP 503 - Not available
    def __init__(self, response):
        super(XeroNotAvailable, self).__init__(response, response.text)


class XeroExceptionUnknown(XeroException):
    # Any other exception.
    pass
