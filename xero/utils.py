from __future__ import unicode_literals

import datetime
import re
import requests
import six

DATE = re.compile(
    r"^(\/Date\((?P<timestamp>-?\d+)((?P<offset_h>[-+]\d\d)(?P<offset_m>\d\d))?\)\/)"
    r"|"
    r"((?P<year>\d{4})-(?P<month>[0-2]\d)-0?(?P<day>[0-3]\d)"
    r"T"
    r"(?P<hour>[0-5]\d):(?P<minute>[0-5]\d):(?P<second>[0-6]\d))$"
)

OBJECT_NAMES = {
    "Addresses": "Address",
    "Attachments": "Attachment",
    "Accounts": "Account",
    "BankAccounts": "BankAccount",
    "BankTransactions": "BankTransaction",
    "BankTransfers": "BankTransfer",
    "BrandingThemes": "BrandingTheme",
    "BatchPayments": "BatchPayment",
    "ContactGroups": "ContactGroup",
    "ContactPersons": "ContactPerson",
    "Contacts": "Contact",
    "CreditNotes": "CreditNote",
    "Currencies": "Currency",
    "DeductionLines": "DeductionLine",
    "Employees": "Employee",
    "EarningsLines": "EarningsLine",
    "ExpenseClaims": "ExpenseClaim",
    "Invoices": "Invoice",
    "Items": "Item",
    "Journals": "Journal",
    "LeaveAccrualLines": "LeaveAccrualLine",
    "LeaveBalances": "LeaveBalance",
    "LeaveLines": "LeaveLine",
    "ManualJournals": "ManualJournal",
    "Organisation": "Organisation",
    "Overpayments": "Overpayment",
    "Payments": "Payment",
    "PayrollCalendars": "PayrollCalendar",
    "PayRuns": "PayRun",
    "Phones": "Phone",
    "Prepayments": "Prepayment",
    "Projects": "Project",
    "Receipts": "Receipt",
    "ReimbursementLines": "ReimbursementLine",
    "RepeatingInvoices": "RepeatingInvoice",
    "Reports": "Report",
    "SuperannuationLines": "SuperannuationLine",
    "SuperLines": "SuperLine",
    "SuperMemberships": "SuperMembership",
    "TaxComponents": "TaxComponent",
    "TaxLines": "TaxLine",
    "TaxRates": "TaxRate",
    "TimesheetEarningsLines": "TimesheetEarningsLine",
    "TrackingCategories": "TrackingCategory",
    "Tracking": "TrackingCategory",
    "Users": "User",
    "Associations": "Association",
    "Files": "File",
    "Folders": "Folder",
    "Inbox": "Inbox",
    "LineItems": "LineItem",
    "JournalLines": "JournalLine",
    "PurchaseOrders": "PurchaseOrder",
    "Quotes": "Quote",
}


def isplural(word):
    return word in OBJECT_NAMES.keys()


def singular(word):
    return OBJECT_NAMES.get(word)


def parse_date(string, force_datetime=False):
    """ Takes a Xero formatted date, e.g. /Date(1426849200000+1300)/"""
    matches = DATE.match(string)
    if not matches:
        return None

    values = dict(
        [
            (k, v if v[0] in "+-" else int(v))
            for k, v in matches.groupdict().items()
            if v and int(v)
        ]
    )

    if "timestamp" in values:
        value = datetime.datetime.utcfromtimestamp(0) + datetime.timedelta(
            hours=int(values.get("offset_h", 0)),
            minutes=int(values.get("offset_m", 0)),
            seconds=int(values["timestamp"]) / 1000.0,
        )
        return value

    # I've made an assumption here, that a DateTime value will not
    # ever be YYYY-MM-DDT00:00:00, which is probably bad. I'm not
    # really sure how to handle this, other than to hard-code the
    # names of the field that are actually Date rather than DateTime.
    if len(values) > 3 or force_datetime:
        return datetime.datetime(**values)

    # Sometimes Xero returns Date(0+0000), so we end up with no
    # values. Return None for this case
    if not values:
        return None

    return datetime.date(**values)


def json_load_object_hook(dct):
    """ Hook for json.parse(...) to parse Xero date formats.
    """
    for key, value in dct.items():
        if isinstance(value, six.string_types):
            value = parse_date(value)
            if value:
                dct[key] = value

    return dct


def resolve_user_agent(user_agent, default_override=None):
    from xero import __version__ as VERSION

    return (
        user_agent
        or default_override
        or "pyxero/%s " % VERSION + requests.utils.default_user_agent()
    )
