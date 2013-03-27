

class XeroException(Exception):
    pass


class XeroNotVerified(Exception):
    pass


class XeroException404(XeroException):
    pass


class XeroException500(XeroException):
    pass


class XeroBadRequest(XeroException):
    def __init__(self, problem, msg):
        self.problem = problem
        super(XeroBadRequest, self).__init__(msg)


class XeroNotImplemented(XeroException):
    pass


class XeroExceptionUnknown(XeroException):
    pass
