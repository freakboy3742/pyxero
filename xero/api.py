from __future__ import unicode_literals

from .filesmanager import FilesManager
from .manager import Manager
from .payrollmanager import PayrollManager
from .projectmanager import ProjectManager


class Xero(object):
    """An ORM-like interface to the Xero API"""

    OBJECT_LIST = (
        "Attachments",
        "Accounts",
        "BankTransactions",
        "BankTransfers",
        "BrandingThemes",
        "BatchPayments",
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
        "Quotes",
    )

    def __init__(self, credentials, unit_price_4dps=False, user_agent=None):
        # Iterate through the list of objects we support, for
        # each of them create an attribute on our self that is
        # the lowercase name of the object and attach it to an
        # instance of a Manager object to operate on it
        for name in self.OBJECT_LIST:
            setattr(
                self,
                name.lower(),
                Manager(name, credentials, unit_price_4dps, user_agent),
            )

        setattr(self, "filesAPI", Files(credentials))
        setattr(self, "payrollAPI", Payroll(credentials, unit_price_4dps, user_agent))
        setattr(self, "projectsAPI", Project(credentials))


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
        "SuperFunds",
        "Timesheets",
        "PayItems",
        "PayRuns",
        "PayrollCalendars",
        "Payslip",
        "LeaveApplications",
    )

    def __init__(self, credentials, unit_price_4dps=False, user_agent=None):
        for name in self.OBJECT_LIST:
            setattr(
                self,
                name.lower(),
                PayrollManager(name, credentials, unit_price_4dps, user_agent),
            )


class Project(object):
    """An ORM-like interface to the Xero Projects API"""

    OBJECT_LIST = (
        "Projects",
        "Projectsusers",
        "Tasks",
        "Time",
    )

    def __init__(self, credentials):
        # Iterate through the list of objects we support, for
        # each of them create an attribute on our self that is
        # the lowercase name of the object and attach it to an
        # instance of a Manager object to operate on it
        for name in self.OBJECT_LIST:
            setattr(self, name.lower(), ProjectManager(name, credentials))
