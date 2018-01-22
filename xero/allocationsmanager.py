from __future__ import unicode_literals

import requests

from .basemanager import BaseManager
from .constants import XERO_API_URL


class PrepaymentAllocationsManager(BaseManager):

    def __init__(self, credentials, unit_price_4dps=False, user_agent=None):
        from xero import __version__ as VERSION
        self.credentials = credentials
        self.singular = 'Allocation'
        self.name = 'Allocations'
        self.base_url = credentials.base_url + XERO_API_URL
        self.extra_params = {"unitdp": 4} if unit_price_4dps else {}
        if user_agent is None:
            self.user_agent = 'pyxero/%s ' % VERSION + requests.utils.default_user_agent()

        method = self._put
        setattr(self, 'put', self._get_data(method))

    def _put(self, prepayment_id, data, summarize_errors=True, headers=None):
        uri = '/'.join([self.base_url, 'Prepayments', prepayment_id, self.name])
        params = self.extra_params.copy()
        method = 'put'
        body = {'xml': self._prepare_data_for_save(data)}
        if not summarize_errors:
            params['summarizeErrors'] = 'false'
        return uri, params, method, body, headers, False


class CreditNoteAllocationsManager(BaseManager):

    def __init__(self, credentials, unit_price_4dps=False, user_agent=None):
        from xero import __version__ as VERSION
        self.credentials = credentials
        self.singular = 'Allocation'
        self.name = 'Allocations'
        self.base_url = credentials.base_url + XERO_API_URL
        self.extra_params = {"unitdp": 4} if unit_price_4dps else {}
        if user_agent is None:
            self.user_agent = 'pyxero/%s ' % VERSION + requests.utils.default_user_agent()

        method = self._put
        setattr(self, 'put', self._get_data(method))

    def _put(self, credit_note_id, data, summarize_errors=True, headers=None):
        uri = '/'.join([self.base_url, 'CreditNotes', credit_note_id, self.name])
        params = self.extra_params.copy()
        method = 'put'
        body = {'xml': self._prepare_data_for_save(data)}
        if not summarize_errors:
            params['summarizeErrors'] = 'false'
        return uri, params, method, body, headers, False
