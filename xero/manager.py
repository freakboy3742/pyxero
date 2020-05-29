from __future__ import unicode_literals

from .basemanager import BaseManager
from .constants import XERO_API_URL
from .utils import resolve_user_agent, singular


class Manager(BaseManager):
    def __init__(self, name, credentials, unit_price_4dps=False, user_agent=None):
        from xero import __version__ as VERSION  # noqa

        self.credentials = credentials
        self.name = name
        self.base_url = credentials.base_url + XERO_API_URL
        self.extra_params = {"unitdp": 4} if unit_price_4dps else {}
        self.singular = singular(name)
        self.user_agent = resolve_user_agent(
            user_agent, getattr(credentials, "user_agent", None)
        )

        for method_name in self.DECORATED_METHODS:
            method = getattr(self, "_%s" % method_name)
            setattr(self, method_name, self._get_data(method))

        if self.name in self.OBJECT_DECORATED_METHODS.keys():
            object_decorated_methods = self.OBJECT_DECORATED_METHODS[self.name]
            for method_name in object_decorated_methods:
                method = getattr(self, "_%s" % method_name)
                setattr(self, method_name, self._get_data(method))
