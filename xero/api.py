from __future__ import unicode_literals
from .manager import Manager


class Xero(object):
    """An ORM-like interface to the Xero API"""

    OBJECT_LIST = (
        'Contacts', 'Accounts', 'CreditNotes', 'Currencies', 'Invoices',
        'Items', 'Organisation', 'Payments', 'TaxRates', 'TrackingCategories',
        'ManualJournals', 'BankTransactions', 'BankTransfers', 'BrandingThemes',
        )

    def __init__(self, credentials):
        # Iterate through the list of objects we support, for
        # each of them create an attribute on our self that is
        # the lowercase name of the object and attach it to an
        # instance of a Manager object to operate on it
        for name in self.OBJECT_LIST:
            setattr(self, name.lower(), Manager(name, credentials))
