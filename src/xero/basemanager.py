from __future__ import annotations

import io
import json
from datetime import date, datetime
from typing import BinaryIO
from urllib.parse import parse_qs
from uuid import UUID
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.parsers.expat import ExpatError

import requests

from .auth import OAuth2Credentials
from .exceptions import (
    XeroBadRequest,
    XeroExceptionUnknown,
    XeroForbidden,
    XeroInternalError,
    XeroNotAvailable,
    XeroNotFound,
    XeroNotImplemented,
    XeroRateLimitExceeded,
    XeroTenantIdNotSet,
    XeroUnauthorized,
)
from .utils import isplural, json_load_object_hook, singular


class BaseManager:
    DECORATED_METHODS = (
        "get",
        "save",
        "filter",
        "all",
        "put",
        "delete",
        "get_history",
        "put_history",
        "get_attachments",
        "get_attachment_data",
        "put_attachment_data",
    )
    OBJECT_DECORATED_METHODS = {
        "Invoices": ["email", "online_invoice"],
        "Organisations": ["actions"],
        "CreditNotes": ["put_allocation", "delete_allocation"],
        "Prepayments": ["put_allocation", "delete_allocation"],
        "Overpayments": ["put_allocation", "delete_allocation"],
    }
    OBJECT_FILTER_FIELDS = {
        "Invoices": {
            "createdByMyApp": bool,
            "summaryOnly": bool,
            "IDs": list,
            "InvoiceNumbers": list,
            "ContactIDs": list,
            "Statuses": list,
        },
        "PurchaseOrders": {
            "DateFrom": date,
            "DateTo": date,
            "Status": str,
        },
        "Quotes": {
            "ContactID": UUID,
            "ExpiryDateFrom": date,
            "ExpiryDateTo": date,
            "DateFrom": date,
            "DateTo": date,
            "Status": str,
            "QuoteNumber": str,
        },
        "Journals": {
            "paymentsOnly": bool,
        },
        "Budgets": {
            "DateFrom": date,
            "DateTo": date,
        },
        "Contacts": {
            "IDs": list,
            "includeArchived": bool,
            "summaryOnly": bool,
            "searchTerm": str,
        },
        "TrackingCategories": {
            "includeArchived": bool,
        },
    }
    DATETIME_FIELDS = (
        "UpdatedDateUTC",
        "Updated",
        "FullyPaidOnDate",
        "DateTimeUTC",
        "CreatedDateUTC",
        "JournalDate",
    )
    DATE_FIELDS = (
        "DueDate",
        "Date",
        "PaymentDate",
        "StartDate",
        "EndDate",
        "PeriodLockDate",
        "DateOfBirth",
        "OpeningBalanceDate",
        "PaymentDueDate",
        "ReportingDate",
        "DeliveryDate",
        "ExpectedArrivalDate",
    )
    BOOLEAN_FIELDS = (
        "IsSupplier",
        "IsCustomer",
        "IsDemoCompany",
        "PaysTax",
        "IsAuthorisedToApproveTimesheets",
        "IsAuthorisedToApproveLeave",
        "HasHELPDebt",
        "AustralianResidentForTaxPurposes",
        "TaxFreeThresholdClaimed",
        "HasSFSSDebt",
        "EligibleToReceiveLeaveLoading",
        "IsExemptFromTax",
        "IsExemptFromSuper",
        "SentToContact",
        "IsSubscriber",
        "HasAttachments",
        "ShowOnCashBasisReports",
        "IncludeInEmails",
        "SentToContact",
        "CanApplyToRevenue",
        "CanApplyToLiabilities",
        "CanApplyToExpenses",
        "CanApplyToEquity",
        "CanApplyToAssets",
        "IsReconciled",
        "EnablePaymentsToAccount",
        "ShowInExpenseClaims",
        "DiscountEnteredAsPercent",
        "IsPurchased",
        "IsSold",
        "IsTrackedAsInventory",
    )
    DECIMAL_FIELDS = (
        "Hours",
        "NumberOfUnit",
    )
    INTEGER_FIELDS = (
        "FinancialYearEndDay",
        "FinancialYearEndMonth",
    )
    NO_SEND_FIELDS = (
        "UpdatedDateUTC",
        "HasValidationErrors",
        "IsDiscounted",
        "DateString",
        "HasErrors",
        "DueDateString",
        "HasAccount",
        "ID",
    )
    OPERATOR_MAPPINGS = {
        "gt": ">",
        "lt": "<",
        "lte": "<=",
        "gte": ">=",
        "ne": "!=",
    }

    def __init__(self):
        pass

    def dict_to_xml(self, root_elm, data):
        for key in data.keys():
            # Xero will complain if we send back these fields.
            if key in self.NO_SEND_FIELDS:
                continue

            sub_data = data[key]
            elm = SubElement(root_elm, key)

            # Key references a dict. Unroll the dict
            # as it's own XML node with subnodes
            if isinstance(sub_data, dict):
                self.dict_to_xml(elm, sub_data)

            # Key references a list/tuple
            elif isinstance(sub_data, (list, tuple)):
                # key name is a plural. This means each item
                # in the list needs to be wrapped in an XML
                # node that is a singular version of the list name.
                if isplural(key):
                    for d in sub_data:
                        sub_elm = SubElement(elm, singular(key))
                        if isinstance(d, dict):
                            self.dict_to_xml(sub_elm, d)
                        else:
                            sub_elm.text = str(d)
                # key name isn't a plural. Just insert the content
                # as an XML node with subnodes
                else:
                    for d in sub_data:
                        if isinstance(d, dict):
                            self.dict_to_xml(elm, d)
                        else:
                            sub_elm = SubElement(elm, "Value")
                            sub_elm.text = str(d)

            # Normal element - just insert the data.
            else:
                if key in self.BOOLEAN_FIELDS:
                    val = "true" if sub_data else "false"
                elif key in self.DATE_FIELDS:
                    val = sub_data.strftime("%Y-%m-%dT%H:%M:%S")
                else:
                    val = str(sub_data)
                elm.text = val

        return root_elm

    def _prepare_data_for_save(
        self,
        data: dict | list[dict] | tuple[dict],
    ) -> bytes:
        if isinstance(data, list) or isinstance(data, tuple):
            root_elm = Element(self.name)
            for d in data:
                sub_elm = SubElement(root_elm, self.singular)
                self.dict_to_xml(sub_elm, d)
        else:
            root_elm = self.dict_to_xml(Element(self.singular), data)

        # In python3 this seems to return a bytestring
        return tostring(root_elm)

    def _parse_api_response(self, response, resource_name):
        data = json.loads(response.text, object_hook=json_load_object_hook)
        assert data["Status"] == "OK", (
            "Expected the API to say OK but received %s" % data["Status"]
        )

        try:
            return data[resource_name]
        except KeyError:
            return data

    def _get_data(self, func):
        """This is the decorator for our DECORATED_METHODS.
        Each of the decorated methods must return:
            uri, params, method, body, headers, singleobject
        """

        def wrapper(*args, **kwargs):
            timeout = kwargs.pop("timeout", None)

            uri, params, method, body, headers, singleobject = func(*args, **kwargs)

            if headers is None:
                headers = {}

            # Send xml by default, but remember we might upload a binary attachment with a custom mime-type
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/xml"

            # Validate any idempotency key provided by the wrapped function
            # Xero docs suggest a max of 128 chars, but also kill an empty string
            # if that was somehow provided. Additionally, force the user to
            # coerce any other type to string before calling.
            if "Idempotency-Key" in headers:
                idempotency_key = headers["Idempotency-Key"]
                if not isinstance(idempotency_key, str):
                    raise TypeError("Idempotency key must be a string.")
                if not (0 < len(idempotency_key) <= 128):
                    raise ValueError(
                        "A provided Idempotency key must be between 1 and 128 characters long."
                    )

            if isinstance(self.credentials, OAuth2Credentials):
                if self.credentials.tenant_id:
                    headers["Xero-tenant-id"] = self.credentials.tenant_id
                else:
                    raise XeroTenantIdNotSet

            # Use the JSON API by default, but remember we might request a PDF (application/pdf)
            # so don't force the Accept header.
            if "Accept" not in headers:
                headers["Accept"] = "application/json"

            # Set a user-agent so Xero knows the traffic is coming from pyxero
            # or individual user/partner
            headers["User-Agent"] = self.user_agent

            response = getattr(requests, method)(
                uri,
                data=body,
                headers=headers,
                auth=self.credentials.oauth,
                params=params,
                timeout=timeout,
            )

            if response.status_code == 200:
                # If we haven't got XML or JSON, assume we're being returned a
                # binary file
                if not response.headers["content-type"].startswith("application/json"):
                    return response.content

                return self._parse_api_response(response, self.name)

            elif response.status_code == 204:
                return response.content

            elif response.status_code == 400:
                try:
                    raise XeroBadRequest(response)
                except (ValueError, ExpatError):
                    raise XeroExceptionUnknown(
                        response, msg="Unable to parse Xero API response"
                    )

            elif response.status_code == 401:
                raise XeroUnauthorized(response)

            elif response.status_code == 403:
                raise XeroForbidden(response)

            elif response.status_code == 404:
                raise XeroNotFound(response)

            elif response.status_code == 429:
                limit_reason = response.headers.get("X-Rate-Limit-Problem") or "unknown"
                payload = {
                    "oauth_problem": ["rate limit exceeded: " + limit_reason],
                    "oauth_problem_advice": [
                        "please wait before retrying the xero api, "
                        "the limit exceeded is: " + limit_reason
                    ],
                }
                raise XeroRateLimitExceeded(response, payload)

            elif response.status_code == 500:
                raise XeroInternalError(response)

            elif response.status_code == 501:
                raise XeroNotImplemented(response)

            elif response.status_code == 503:
                # Two 503 responses are possible. Rate limit errors
                # return encoded content; offline errors don't.
                # If you parse the response text and there's nothing
                # encoded, it must be a not-available error.
                payload = parse_qs(response.text)
                if payload:
                    raise XeroRateLimitExceeded(response, payload)
                else:
                    raise XeroNotAvailable(response)
            else:
                raise XeroExceptionUnknown(response)

        return wrapper

    def _get(self, id, headers=None, params=None):
        uri = "/".join([self.base_url, self.name, id])
        uri_params = self.extra_params.copy()
        uri_params.update(params if params else {})
        return uri, uri_params, "get", None, headers, True

    def _get_history(self, id):
        uri = "/".join([self.base_url, self.name, id, "history"]) + "/"
        return uri, {}, "get", None, None, False

    def _get_attachments(self, id):
        """Retrieve a list of attachments associated with this Xero object."""
        uri = "/".join([self.base_url, self.name, id, "Attachments"]) + "/"
        return uri, {}, "get", None, None, False

    def _get_attachment_data(self, id, filename):
        """
        Retrieve the contents of a specific attachment (identified by filename).
        """
        uri = "/".join([self.base_url, self.name, id, "Attachments", filename])
        return uri, {}, "get", None, None, False

    def get_attachment(self, id, filename, file):
        """
        Retrieve the contents of a specific attachment (identified by filename).

        Writes data to file object, returns length of data written.
        """
        data = self.get_attachment_data(id, filename)
        file.write(data)
        return len(data)

    def _email(self, id):
        uri = "/".join([self.base_url, self.name, id, "Email"])
        return uri, {}, "post", None, None, True

    def _online_invoice(self, id):
        uri = "/".join([self.base_url, self.name, id, "OnlineInvoice"])
        return uri, {}, "get", None, None, True

    def _actions(self):
        uri = "/".join([self.base_url, self.name, "Actions"])
        return uri, {}, "get", None, None, False

    def _put_allocation(self, id, data):
        uri = "/".join([self.base_url, self.name, id, "Allocations"])
        root_elm = Element("Allocation")
        if "Amount" in data:
            data["AppliedAmount"] = data["Amount"]
            del data["Amount"]
        self.dict_to_xml(root_elm, data)
        body = tostring(root_elm)
        return uri, {}, "put", body, None, False

    def _delete_allocation(self, cn_id, allocation_id):
        uri = "/".join([self.base_url, self.name, cn_id, "Allocations", allocation_id])
        return uri, {}, "delete", None, None, True

    def save_or_put(
        self,
        data: dict | list[dict] | tuple[dict],
        method: str = "post",
        headers: dict | None = None,
        summarize_errors: bool = True,
        *,
        idempotency_key: str | None = None,
    ):
        uri = "/".join([self.base_url, self.name])
        body = self._prepare_data_for_save(data)
        params = self.extra_params.copy()
        headers = headers or {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if not summarize_errors:
            params["summarizeErrors"] = "false"
        return uri, params, method, body, headers, False

    def _save(
        self,
        data: dict | list[dict] | tuple[dict],
        summarize_errors: bool = True,
        *,
        idempotency_key: str | None = None,
    ):
        """
        POST one or more items to the Xero API.

        :param data: The item (as a dictionary) or list/tuple of items to send.
        :param summarize_errors: If set to False, the response from Xero will itemise any errors against the item that they relate to.
        :param idempotency_key: Optional idempotency key for the request. See https://developer.xero.com/documentation/guides/idempotent-requests/idempotency/ for more information.
        """
        return self.save_or_put(
            data,
            method="post",
            summarize_errors=summarize_errors,
            idempotency_key=idempotency_key,
        )

    def _put(
        self,
        data: dict | list[dict] | tuple[dict],
        summarize_errors: bool = True,
        *,
        idempotency_key: str | None = None,
    ):
        """
        PUT one or more items to the Xero API.

        :param data: The item (as a dictionary) or list/tuple of items to send.
        :param summarize_errors: If set to False, the response from Xero will itemise any errors against the item that they relate to.
        :param idempotency_key: Optional idempotency key for the request. See https://developer.xero.com/documentation/guides/idempotent-requests/idempotency/ for more information.
        """
        return self.save_or_put(
            data,
            method="put",
            summarize_errors=summarize_errors,
            idempotency_key=idempotency_key,
        )

    def _delete(self, id):
        uri = "/".join([self.base_url, self.name, id])
        return uri, {}, "delete", None, None, False

    def _put_history_data(
        self,
        id: str,
        details: str,
        *,
        idempotency_key: str | None = None,
    ):
        """Add a history note to the Xero object."""
        if not isinstance(details, str):
            raise TypeError("details must be a string")
        if len(details) > 2500:
            raise ValueError(
                "Xero allows a maximum of 2500 characters for history details.\n"
                "See https://developer.xero.com/documentation/api/accounting/historyandnotes#put-history"
            )

        uri = "/".join([self.base_url, self.name, id, "history"])
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        details_data = {"Details": details}
        root_elm = Element("HistoryRecord")
        self.dict_to_xml(root_elm, details_data)
        data = tostring(root_elm)
        return uri, {}, "put", data, headers, False

    def _put_history(
        self,
        id: str,
        details: str,
        *,
        idempotency_key: str | None = None,
    ):
        """
        Upload a history note to the Xero object.

        :param id: The UUID of the object you wish to add a history note against.
        :param details: A string (up to 2500 characters) containing the note you wish to add. See https://developer.xero.com/documentation/api/accounting/historyandnotes#put-history for more information.
        :param idempotency_key: Optional idempotency key for the request. See https://developer.xero.com/documentation/guides/idempotent-requests/idempotency/ for more information.
        """
        return self._put_history_data(id, details, idempotency_key=idempotency_key)

    def _put_attachment_data(
        self,
        id: str,
        filename: str,
        data: bytes,
        content_type: str,
        include_online: bool = False,
        *,
        idempotency_key: str | None = None,
    ):
        """
        Upload an attachment to the Xero object from a bytestring.

        :param id: The UUID of the Xero object you wish to add an attachment to.
        :param filename: The filename of the file you are uploading. This will display in the Xero UI for end users.
        :param data: The binary data of the file you are uploading. To upload a file-like object instead, use the put_attachment() method.
        :param content_type: The content type of the file you are uploading.
        :param include_online: Whether to make this file available to the public via the online invoice URL. If false it will still be available in the Xero UI, but only for members of the organisation.
        :param idempotency_key: Optional idempotency key for the request. See https://developer.xero.com/documentation/guides/idempotent-requests/idempotency/ for more information.

        """
        uri = "/".join([self.base_url, self.name, id, "Attachments", filename])
        params = {"IncludeOnline": "true"} if include_online else {}
        headers = {"Content-Type": content_type, "Content-Length": str(len(data))}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return uri, params, "put", io.BytesIO(data), headers, False

    def put_attachment(
        self,
        id: str,
        filename: str,
        file: BinaryIO,
        content_type: str,
        include_online: bool = False,
        *,
        idempotency_key: str | None = None,
    ):
        """
        Upload an attachment to the Xero object (from file object).

        :param id: The UUID of the Xero object you wish to add an attachment to.
        :param filename: The filename of the file you are uploading. This will display in the Xero UI for end users.
        :param file: A file-like object containing the attachment to upload.
        :param content_type: The content type of the file you are uploading.
        :param include_online: Whether to make this file available to the public via the online invoice URL. If false it will still be available in the Xero UI, but only for members of the organisation.
        :param idempotency_key: Optional idempotency key for the request. See https://developer.xero.com/documentation/guides/idempotent-requests/idempotency/ for more information.
        """
        return self.put_attachment_data(
            id,
            filename,
            file.read(),
            content_type,
            include_online=include_online,
            idempotency_key=idempotency_key,
        )

    def prepare_filtering_date(self, val):
        if isinstance(val, datetime):
            val = val.strftime("%a, %d %b %Y %H:%M:%S GMT")
        else:
            val = '"%s"' % val
        return {"If-Modified-Since": val}

    def _filter(self, **kwargs):
        params = self.extra_params.copy()
        headers = None
        uri = "/".join([self.base_url, self.name])

        if kwargs:
            if "since" in kwargs:
                val = kwargs["since"]
                headers = self.prepare_filtering_date(val)
                del kwargs["since"]

            def get_filter_value(key, value, value_type=None):
                if key in self.BOOLEAN_FIELDS or value_type == bool:
                    return "true" if value else "false"
                elif key in self.DATE_FIELDS or value_type == date:
                    return f"{value.year}-{value.month}-{value.day}"
                elif key in self.DATETIME_FIELDS or value_type == datetime:
                    return value.isoformat()
                elif key.endswith("ID") or value_type == UUID:
                    return "%s" % (
                        value.hex if type(value) is UUID else UUID(value).hex
                    )
                else:
                    return value

            def get_filter_params(key, value):
                last_key = key.split("_")[-1]
                if last_key.endswith("ID"):
                    return 'Guid("%s")' % str(value)
                if key in self.BOOLEAN_FIELDS:
                    return "true" if value else "false"
                elif key in self.DATE_FIELDS:
                    return "DateTime({},{},{})".format(
                        value.year, value.month, value.day
                    )
                elif key in self.DATETIME_FIELDS:
                    return value.isoformat()
                else:
                    return '"%s"' % str(value)

            def generate_param(key, value):
                parts = key.split("__")
                field = key.replace("_", ".")
                fmt = "%s==%s"
                if len(parts) == 2:
                    # support filters:
                    # Name__Contains=John becomes Name.Contains("John")
                    if parts[1] in ["contains", "startswith", "endswith"]:
                        field = parts[0]
                        fmt = "".join(["%s.", parts[1], "(%s)"])
                    elif parts[1] in ["tolower", "toupper"]:
                        field = parts[0]
                        fmt = "".join(["%s.", parts[1], "()==%s"])
                    elif parts[1] in self.OPERATOR_MAPPINGS:
                        field = parts[0]
                        key = field
                        fmt = "%s" + self.OPERATOR_MAPPINGS[parts[1]] + "%s"
                    elif parts[1] in ["isnull"]:
                        sign = "=" if value else "!"
                        return f"{parts[0]}{sign}=null"
                    field = field.replace("_", ".")
                return fmt % (field, get_filter_params(key, value))

            KNOWN_PARAMETERS = ["order", "offset", "page", "pageSize"]
            object_params = self.OBJECT_FILTER_FIELDS.get(self.name, {})
            LIST_PARAMETERS = list(
                filter(lambda x: object_params[x] == list, object_params)
            )
            EXTRA_PARAMETERS = list(
                filter(lambda x: object_params[x] != list, object_params)
            )

            # Move any known parameter names to the query string
            for param in KNOWN_PARAMETERS + EXTRA_PARAMETERS:
                if param in kwargs:
                    params[param] = get_filter_value(
                        param, kwargs.pop(param), object_params.get(param, None)
                    )
            # Support xero optimised list filtering; validate IDs we send but may need other validation
            for param in LIST_PARAMETERS:
                if param in kwargs:
                    if param.endswith("IDs"):
                        params[param] = ",".join(
                            map(lambda x: UUID(x).hex, kwargs.pop(param))
                        )
                    else:
                        params[param] = ",".join(kwargs.pop(param))

            filter_params = []

            if "raw" in kwargs:
                raw = kwargs.pop("raw")
                filter_params.append(raw)

            # Treat any remaining arguments as filter predicates
            # Xero will break if you search without a check for null in the first position:
            # http://developer.xero.com/documentation/getting-started/http-requests-and-responses/#title3
            sortedkwargs = sorted(
                kwargs.items(), key=lambda item: -1 if "isnull" in item[0] else 0
            )
            for key, value in sortedkwargs:
                filter_params.append(generate_param(key, value))

            if filter_params:
                params["where"] = "&&".join(filter_params)

        return uri, params, "get", None, headers, False

    def _all(self):
        uri = "/".join([self.base_url, self.name])
        return uri, {}, "get", None, None, False
