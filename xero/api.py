from __future__ import unicode_literals

from .filesmanager import FilesManager
from .payrollmanager import PayrollManager
from .manager import Manager
from .trackingcategoryoptionsmanager import TrackingCategoryOptionsManager

class Xero(object):
    """An ORM-like interface to the Xero API"""

    OBJECT_LIST = (
        "Attachments",
        "Accounts",
        "BankTransactions",
        "BankTransfers",
        "BrandingThemes",
        "ContactGroups",
        "Contacts",
        "CreditNotes",
        "Currencies",
        "Employees",
        "ExpenseClaims",
        "Invoices",
        "Items",
        "Journals",
        "ManualJournals",
        "Organisations",
        "Overpayments",
        "Payments",
        "Prepayments",
        "PurchaseOrders",
        "Receipts",
        "RepeatingInvoices",
        "Reports",
        "TaxRates",
        "TrackingCategories",
        "Users",
    )

    def __init__(self, credentials, unit_price_4dps=False, user_agent=None):
        # Iterate through the list of objects we support, for
        # each of them create an attribute on our self that is
        # the lowercase name of the object and attach it to an
        # instance of a Manager object to operate on it
        for name in self.OBJECT_LIST:
            setattr(self, name.lower(), Manager(name, credentials, unit_price_4dps,
                                                user_agent))

        setattr(self, "filesAPI", Files(credentials))
        setattr(self, "payrollAPI", Payroll(credentials))
        
        # Might be a better place to hold onto this?
        self.credentials = credentials

    def populate_tracking_categories(self):
        """
        If you wish to set new tracking category options you'll need to call this method to pre-populate the options 
        """
        categories = self.trackingcategories.all()

        self.trackingCategoryNames = {x['Name']:x['TrackingCategoryID'] for x in categories}
        for name, tracking_category_id in self.trackingCategoryNames.items():
            setattr(self, "TC%s" % name, TrackingCategoryOptions(self.credentials, tracking_category_id))
        return categories


class Files(object):
    """An ORM-like interface to the Xero Files API"""

    OBJECT_LIST = (
        "Associations",
        "Files",
        "Folders",
        "Inbox",
    )

    def __init__(self, credentials):
        # Iterate through the list of objects we support, for
        # each of them create an attribute on our self that is
        # the lowercase name of the object and attach it to an
        # instance of a Manager object to operate on it
        for name in self.OBJECT_LIST:
            setattr(self, name.lower(), FilesManager(name, credentials))


class Payroll(object):
    """An ORM-like interface to the Xero Payroll API"""

    OBJECT_LIST = (
        "Employees",
        "Timesheets",
        "PayItems",
        "PayRuns",
        "PayrollCalendars",
        "Payslip",
        "LeaveApplications",
    )

    def __init__(self, credentials, unit_price_4dps=False, user_agent=None):
        for name in self.OBJECT_LIST:
            setattr(self, name.lower(), PayrollManager(name, credentials))

class TrackingCategoryOptions(object):
    """An ORM-like interface to the Xero Tracking Category API"""

    OBJECT_LIST = (
        "Options",
    )

    def __init__(self, credentials, tracking_category_id):
        for name in self.OBJECT_LIST:
            setattr(self, name.lower(), TrackingCategoryOptionsManager(name, credentials, tracking_category_id))


