from urlparse import parse_qs
from xml.dom.minidom import parseString


class XeroException(Exception):
    def __init__(self, response, msg=None):
        self.response = response
        super(XeroException, self).__init__(msg)


class XeroNotVerified(Exception):
    # Credentials haven't been verified
    pass


class XeroBadRequest(XeroException):
    # HTTP 400: Bad Request
    def __init__(self, response):
        # Extract the messages from the text.
        # parseString takes byte content, not unicode.
        dom = parseString(response.text.encode(response.encoding))
        messages = dom.getElementsByTagName('Message')

        msg = messages[0].childNodes[0].data
        self.errors = [
            m.childNodes[0].data for m in messages[1:]
        ]
        super(XeroBadRequest, self).__init__(response, msg)


class XeroUnauthorized(XeroException):
    # HTTP 401: Unauthorized
    def __init__(self, response):
        payload = parse_qs(response.text)
        self.problem = payload['oauth_problem'][0]
        super(XeroUnauthorized, self).__init__(response, payload['oauth_problem_advice'][0])


class XeroForbidden(XeroException):
    # HTTP 403: Forbidden
    def __init__(self, response):
        super(XeroForbidden, self).__init__(response, response.text)


class XeroNotFound(XeroException):
    # HTTP 404: Not Found
    def __init__(self, response):
        super(XeroNotFound, self).__init__(response, response.text)


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
        messages = dom.getElementsByTagName('Message')

        msg = messages[0].childNodes[0].data
        super(XeroNotImplemented, self).__init__(response, msg)


class XeroRateLimitExceeded(XeroException):
    # HTTP 503 - Rate limit exceeded
    def __init__(self, response, payload):
        self.problem = payload['oauth_problem'][0]
        super(XeroRateLimitExceeded, self).__init__(response, payload['oauth_problem_advice'][0])


class XeroNotAvailable(XeroException):
    # HTTP 503 - Not available
    def __init__(self, response):
        super(XeroNotAvailable, self).__init__(response, response.text)


class XeroExceptionUnknown(XeroException):
    # Any other exception.
    pass
