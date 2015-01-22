from __future__ import unicode_literals
from .manager import Manager
from .constants import XERO_FILES_URL


class Xero(object):
    """An ORM-like interface to the Xero API"""

    OBJECT_LIST = (
      "Attachments",
      "Accounts",
      "BankTransactions",
      "BankTransfers",
      "BrandingThemes",
      "Contacts",
      "CreditNotes",
      "Currencies",
      "Employees",
      "ExpenseClaims",
      "Invoices",
      "Items",
      "Journals",
      "ManualJournals",
      "Organisation",
      "Payments",
      "Receipts",
      "RepeatingInvoices",
      "Reports",
      "TaxRates",
      "TrackingCategories",
      "Users",
    )

    FILES_OBJECT_LIST = (
      "Folders",
    )

    def __init__(self, credentials):
        # Iterate through the list of objects we support, for
        # each of them create an attribute on our self that is
        # the lowercase name of the object and attach it to an
        # instance of a Manager object to operate on it
        for name in self.OBJECT_LIST:
            setattr(self, name.lower(), Manager(name, credentials))

        for name in self.FILES_OBJECT_LIST:
            setattr(self, name.lower(), Manager(name, credentials, url=XERO_FILES_URL))
