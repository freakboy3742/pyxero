from __future__ import unicode_literals

import requests

from .constants import XERO_API_URL
from .utils import singular
from .basemanager import BaseManager


class Manager(BaseManager):

    def __init__(self, name, credentials, unit_price_4dps=False, user_agent=None):
        from xero import __version__ as VERSION
        self.credentials = credentials
        self.name = name
        self.base_url = credentials.base_url + XERO_API_URL
        self.extra_params = {"unitdp": 4} if unit_price_4dps else {}
        self.singular = singular(name)

        if user_agent is None:
            self.user_agent = 'pyxero/%s ' % VERSION + requests.utils.default_user_agent()
        else:
            self.user_agent = user_agent

        for method_name in self.DECORATED_METHODS:
            method = getattr(self, '_%s' % method_name)
            setattr(self, method_name, self._get_data(method))

        if self.name in self.OBJECT_DECORATED_METHODS.keys():
            object_decorated_methods = self.OBJECT_DECORATED_METHODS[self.name]
            for method_name in object_decorated_methods:
                method = getattr(self, '_%s' % method_name)
                setattr(self, method_name, self._get_data(method))