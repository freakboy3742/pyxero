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


def _oauth_problem(text):
    """Return (problem, advice) from a form-encoded OAuth error body, or None."""
    payload = parse_qs(text)
    if "oauth_problem" not in payload:
        return None
    problem = payload["oauth_problem"][0]
    return problem, payload.get("oauth_problem_advice", [problem])[0]


class XeroBadRequest(XeroException):
    # HTTP 400: Bad Request
    def __init__(self, response):
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            data = json.loads(response.text)
            # ApiException bodies carry Type and Message; problem details bodies
            # (such as the OAuth2 layer's) carry Title and Detail instead.
            error_type = data.get("Type") or data.get("Title") or "Error"
            message = data.get("Message") or data.get("Detail") or "No Message Provided"
            msg = f"{error_type}: {message}"
            self.errors = [
                err["Message"]
                for elem in data.get("Elements", [])
                for err in elem.get("ValidationErrors", [])
            ]
            if len(self.errors) > 0:
                self.problem = self.errors[0]
                if len(self.errors) > 1:
                    msg += f" ({self.problem}, and {len(self.errors)} other issues)"
                else:
                    msg += f" ({self.problem})"
            else:
                self.problem = None
            super().__init__(response, msg=msg)

        elif content_type.startswith("text/html"):
            oauth_problem = _oauth_problem(response.text)
            if oauth_problem:
                self.problem, advice = oauth_problem
                self.errors = [self.problem]
                super().__init__(response, advice)
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
            self.problem = self.errors[0] if self.errors else None
            super().__init__(response, msg)


class XeroUnauthorized(XeroException):
    # HTTP 401: Unauthorized
    def __init__(self, response):
        if response.headers.get("content-type", "").startswith("application/json"):
            data = json.loads(response.text)
            msg = data.get("Detail") or ""
            self.errors = [msg.split(":")[0]]
            self.problem = self.errors[0]
            super().__init__(response, msg)
        else:
            oauth_problem = _oauth_problem(response.text)
            if oauth_problem:
                self.problem, advice = oauth_problem
                self.errors = [self.problem]
                super().__init__(response, advice)
            else:
                self.errors = [response.text]
                self.problem = response.text
                super().__init__(response, response.text)


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


class XeroUnexpectedResponse(XeroException):
    # A 200 response arrived with a content type the endpoint never produces,
    # typically an HTML error page served with a 200 status.
    def __init__(self, response, msg=None):
        super().__init__(response, msg)


class XeroExceptionUnknown(XeroException):
    # Any other exception.
    pass
