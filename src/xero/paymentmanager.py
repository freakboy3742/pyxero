from .basemanager import BaseManager
from .constants import XERO_API_URL
from .utils import resolve_user_agent, singular


class PaymentManager(BaseManager):
    def __init__(self, name, credentials, unit_price_4dps=False, user_agent=None):
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

    def _delete(self, id):
        uri = "/".join([self.base_url, self.name, id])
        data = {"Status": "DELETED"}
        body = self._prepare_data_for_save(data)
        return uri, {}, "post", body, None, False
