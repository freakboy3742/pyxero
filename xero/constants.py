XERO_BASE_URL = "https://api.xero.com"

REQUEST_TOKEN_URL = "/oauth/RequestToken"
AUTHORIZE_URL = "/oauth/Authorize"
ACCESS_TOKEN_URL = "/oauth/AccessToken"
XERO_API_URL = "/api.xro/2.0"
XERO_FILES_URL = "/files.xro/1.0"
XERO_PAYROLL_URL = "/payroll.xro/1.0"
XERO_PROJECTS_URL = "/projects.xro/2.0"

XERO_OAUTH2_AUTHORIZE_URL = "https://login.xero.com/identity/connect/authorize"
XERO_OAUTH2_TOKEN_URL = "https://identity.xero.com/connect/token"
XERO_OAUTH2_CONNECTIONS_URL = "/connections"


class XeroScopes:
    # Offline Access
    OFFLINE_ACCESS = "offline_access"

    # OpenID connection
    OPENID = "openid"
    PROFILE = "profile"
    EMAIL = "email"

    # Accounting API
    ACCOUNTING_TRANSACTIONS = "accounting.transactions"
    ACCOUNTING_TRANSACTIONS_READ = "accounting.transactions.read"
    ACCOUNTING_REPORTS_READ = "accounting.reports.read"
    ACCOUNTING_JOURNALS_READ = "accounting.journals.read"
    ACCOUNTING_SETTINGS = "accounting.settings"
    ACCOUNTING_SETTINGS_READ = "accounting.settings.read"
    ACCOUNTING_CONTACTS = "accounting.contacts"
    ACCOUNTING_CONTACTS_READ = "accounting.contacts.read"
    ACCOUNTING_ATTACHMENTS = "accounting.attachments"
    ACCOUNTING_ATTACHMENTS_READ = "accounting.attachments.read"

    # Payroll API
    PAYROLL_EMPLOYEES = "payroll.employees"
    PAYROLL_EMPLOYEES_READ = "payroll.employees.read"
    PAYROLL_PAYRUNS = "payroll.payruns"
    PAYROLL_PAYRUNS_READ = "payroll.payruns.read"
    PAYROLL_PAYSLIP = "payroll.payslip"
    PAYROLL_PAYSLIP_READ = "payroll.payslip.read"
    PAYROLL_TIMESHEETS = "payroll.timesheets"
    PAYROLL_TIMESHEETS_READ = "payroll.timesheets.read"
    PAYROLL_SETTINGS = "payroll.settings"
    PAYROLL_SETTINGS_READ = "payroll.settings.read"

    # Files API
    FILES = "files"
    FILES_READ = "files.read"

    # Asssets API
    ASSETS = "assets"
    ASSETS_READ = "assets.read"

    # Projects API
    PROJECTS = "projects"
    PROJECTS_READ = "projects.read"

    # Restricted Scopes
    PAYMENTSERVICES = "paymentservices"
    BANKFEEDS = "bankfeeds"
