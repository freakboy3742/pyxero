from .manager import Manager


class Xero(object):
    """An ORM-like interface to the Xero API"""

    OBJECT_LIST = (
      u"Attachments",
      u"Accounts",
      u"BankTransactions",
      u"BankTransfers",
      u"BrandingThemes",
      u"Contacts",
      u"CreditNotes",
      u"Currencies",
      u"Employees",
      u"ExpenseClaims",
      u"Invoices",
      u"Items",
      u"Journals",
      u"ManualJournals",
      u"Organisation",
      u"Payments",
      u"Receipts",
      u"RepeatingInvoices",
      u"Reports",
      u"TaxRates",
      u"TrackingCategories",
      u"Users",
    )

    def __init__(self, credentials):
        # Iterate through the list of objects we support, for
        # each of them create an attribute on our self that is
        # the lowercase name of the object and attach it to an
        # instance of a Manager object to operate on it
        for name in self.OBJECT_LIST:
            setattr(self, name.lower(), Manager(name, credentials.oauth))
