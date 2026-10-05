import json
from urllib.parse import parse_qs
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError


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


def _content_type(response):
    return response.headers.get("content-type", "").split(";", 1)[0].strip().lower()


def _json_object(text):
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        return None
    return data if isinstance(data, dict) else None


def _string_field(data, names, default=""):
    for name in names:
        value = data.get(name)
        if isinstance(value, str) and value:
            return value
    return default


class XeroBadRequest(XeroException):
    # HTTP 400: Bad Request
    def __init__(self, response):
        content_type = _content_type(response)
        msg = response.text
        self.errors = [msg]
        self.problem = msg
        if content_type in ("application/json", "application/problem+json"):
            data = _json_object(response.text)
            if data is None:
                super().__init__(response, msg)
                return
            # ApiException bodies carry Type and Message; problem details bodies
            # (such as the OAuth2 layer's) carry Title and Detail instead.
            error_type = _string_field(
                data, ("Type", "Title", "type", "title"), "Error"
            )
            message = _string_field(
                data, ("Message", "Detail", "message", "detail"), "No Message Provided"
            )
            msg = f"{error_type}: {message}"
            self.errors = []
            elements = data.get("Elements")
            if isinstance(elements, list):
                for elem in elements:
                    errors = (
                        elem.get("ValidationErrors") if isinstance(elem, dict) else None
                    )
                    if isinstance(errors, list):
                        for err in errors:
                            message = (
                                _string_field(err, ("Message",))
                                if isinstance(err, dict)
                                else ""
                            )
                            if message:
                                self.errors.append(message)
            model_state = data.get("modelState")
            if isinstance(model_state, dict):
                for errors in model_state.values():
                    if isinstance(errors, str):
                        errors = [errors]
                    if isinstance(errors, list):
                        self.errors.extend(
                            error
                            for error in errors
                            if isinstance(error, str) and error
                        )
            if len(self.errors) > 0:
                self.problem = self.errors[0]
                if len(self.errors) > 1:
                    msg += f" ({self.problem}, and {len(self.errors)} other issues)"
                else:
                    msg += f" ({self.problem})"
            else:
                self.problem = None
        else:
            if content_type != "text/html":
                try:
                    xml_input = (
                        response.text.encode(response.encoding)
                        if response.encoding
                        else response.text
                    )
                    with parseString(xml_input) as dom:
                        messages = [
                            "".join(
                                child.data
                                for child in node.childNodes
                                if child.nodeType
                                in (child.TEXT_NODE, child.CDATA_SECTION_NODE)
                            )
                            for node in dom.getElementsByTagName("Message")
                        ]
                except (ExpatError, ValueError, LookupError, RecursionError):
                    messages = []
                if messages and messages[0]:
                    self.errors = [message for message in messages[1:] if message]
                    self.problem = self.errors[0] if self.errors else None
                    super().__init__(response, messages[0])
                    return
            oauth_problem = _oauth_problem(response.text)
            if oauth_problem:
                self.problem, advice = oauth_problem
                self.errors = [self.problem]
                msg = advice
        super().__init__(response, msg)


class XeroUnauthorized(XeroException):
    # HTTP 401: Unauthorized
    def __init__(self, response):
        if _content_type(response) in ("application/json", "application/problem+json"):
            data = _json_object(response.text)
            if data is None:
                self.errors = [response.text]
                self.problem = response.text
                super().__init__(response, response.text)
                return
            msg = _string_field(data, ("Detail", "detail"))
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
