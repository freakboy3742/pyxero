import json
from urllib.parse import parse_qs
from xml.dom.minidom import parseString


class XeroException(Exception):
    def __init__(self, response, msg=None):
        self.response = response
        super().__init__(msg)


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
            msg = "{}: {}".format(data["Type"], data["Message"])
            self.errors = [
                err["Message"]
                for elem in data.get("Elements", [])
                for err in elem.get("ValidationErrors", [])
            ]
            if len(self.errors) > 0:
                self.problem = self.errors[0]
                if len(self.errors) > 1:
                    msg += " ({}, and {} other issues)".format(
                        self.problem,
                        len(self.errors),
                    )
                else:
                    msg += " (%s)" % self.problem
            else:
                self.problem = None
            super().__init__(response, msg=msg)

        elif response.headers["content-type"].startswith("text/html"):
            payload = parse_qs(response.text)
            if payload:
                self.errors = [payload["oauth_problem"][0]]
                self.problem = self.errors[0]
                super().__init__(response, payload["oauth_problem_advice"][0])
            else:
                # Sometimes xero returns the error message as pure text
                # Not sure how to validate this is always the case
                self.errors = [response.text]
                self.problem = self.errors[0]
                super().__init__(response, response.text)
        else:
            # Extract the messages from the text.
            # parseString takes byte content, not unicode.
            dom = parseString(response.text.encode(response.encoding))
            messages = dom.getElementsByTagName("Message")

            msg = messages[0].childNodes[0].data
            self.errors = [m.childNodes[0].data for m in messages[1:]]
            self.problem = self.errors[0]
            super().__init__(response, msg)


class XeroUnauthorized(XeroException):
    # HTTP 401: Unauthorized
    def __init__(self, response):
        if response.headers["content-type"].startswith("application/json"):
            data = json.loads(response.text)
            msg = data.get("Detail", "")
            self.errors = [msg.split(":")[0]]
            self.problem = self.errors[0]
            super().__init__(response, msg)
        else:
            payload = parse_qs(response.text)
            self.errors = [payload["oauth_problem"][0]]
            self.problem = self.errors[0]
            super().__init__(response, payload["oauth_problem_advice"][0])


class XeroForbidden(XeroException):
    # HTTP 403: Forbidden
    def __init__(self, response):
        super().__init__(response, response.text)


class XeroNotFound(XeroException):
    # HTTP 404: Not Found
    def __init__(self, response):
        super().__init__(response, response.text)


class XeroUnsupportedMediaType(XeroException):
    # HTTP 415: UnsupportedMediaType
    def __init__(self, response):
        super().__init__(response, response.text)


class XeroInternalError(XeroException):
    # HTTP 500: Internal Error
    def __init__(self, response):
        super().__init__(response, response.text)


class XeroNotImplemented(XeroException):
    # HTTP 501
    def __init__(self, response):
        # Extract the useful error message from the text.
        # parseString takes byte content, not unicode.
        dom = parseString(response.text.encode(response.encoding))
        messages = dom.getElementsByTagName("Message")

        msg = messages[0].childNodes[0].data
        super().__init__(response, msg)


class XeroRateLimitExceeded(XeroException):
    # HTTP 503 - Rate limit exceeded
    def __init__(self, response, payload):
        try:
            self.errors = [payload["oauth_problem"][0]]
        except KeyError:
            return super().__init__(response, response.text)
        self.problem = self.errors[0]
        super().__init__(response, payload["oauth_problem_advice"][0])


class XeroNotAvailable(XeroException):
    # HTTP 503 - Not available
    def __init__(self, response):
        super().__init__(response, response.text)


class XeroExceptionUnknown(XeroException):
    # Any other exception.
    pass
