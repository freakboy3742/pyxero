from __future__ import unicode_literals

import requests

from .constants import XERO_TRACKING_CATEGORY_OPTIONS_URL
from .utils import singular
from .basemanager import BaseManager


class TrackingCategoryOptionsManager(BaseManager):
    """
    A new manager needs to be instantiated for each tracking category with its
    id as a parameter.  This is because the id is part of the submission url.
    """

    def __init__(self, name, credentials, TrackingCategoryID, unit_price_4dps=False, user_agent=None):
        from xero import __version__ as VERSION
        self.credentials = credentials
        self.name = name
        self.base_url = credentials.base_url + XERO_TRACKING_CATEGORY_OPTIONS_URL % {'TrackingCategoryID': TrackingCategoryID}
        self.extra_params = {"unitdp": 4} if unit_price_4dps else {}
        self.singular = singular(name)

        if user_agent is None:
            self.user_agent = 'pyxero/%s ' % VERSION + requests.utils.default_user_agent()
        else:
            self.user_agent = user_agent

        for method_name in self.DECORATED_METHODS:
            method = getattr(self, '_%s' % method_name)
            setattr(self, method_name, self._get_data(method))
