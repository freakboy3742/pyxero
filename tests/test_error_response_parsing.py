import json
from unittest.mock import Mock

import pytest
from requests import Response
from requests.structures import CaseInsensitiveDict
from requests.utils import get_encoding_from_headers

from xero import Xero
from xero.auth import OAuth2Credentials, PublicCredentials
from xero.exceptions import XeroBadRequest, XeroUnauthorized


def response(text, content_type=None):
    headers = CaseInsensitiveDict()
    if content_type is not None:
        headers["Content-Type"] = content_type
    return Mock(status_code=400, text=text, headers=headers, encoding=None)


def assert_error(error, original, message, errors, problem):
    assert str(error) == message
    assert error.errors == errors
    assert error.problem == problem
    assert error.response is original


@pytest.mark.parametrize(
    "content_type",
    [None, "", "text/plain", "unknown/type", "text/xml", "application/xml"],
)
@pytest.mark.parametrize(
    "body",
    [
        "",
        "Bad Request",
        "<ApiException>",
        "<ApiException/>",
        "<ApiException><Message/></ApiException>",
    ],
)
def test_unusable_xml_preserves_the_http_error(content_type, body):
    original = response(body, content_type)
    assert_error(XeroBadRequest(original), original, body, [body], body)


@pytest.mark.parametrize(
    "content_type", [None, "text/plain", "text/xml", "application/xml; charset=utf-8"]
)
def test_valid_xml_remains_supported_without_an_xml_header(content_type):
    original = response(
        '<?xml version="1.0" encoding="utf-8"?><ApiException>'
        "<Message>Invalid café</Message><Message/>"
        "<Message><![CDATA[Name required]]></Message></ApiException>",
        content_type,
    )
    assert_error(
        XeroBadRequest(original),
        original,
        "Invalid café",
        ["Name required"],
        "Name required",
    )


@pytest.mark.parametrize("wire_encoding", ["utf-8", "utf-16"])
def test_xml_declared_encoding_without_http_charset(wire_encoding):
    original = Response()
    original.status_code = 400
    original.headers["Content-Type"] = "text/xml"
    original.encoding = get_encoding_from_headers(original.headers)
    original._content = (
        f'<?xml version="1.0" encoding="{wire_encoding}"?>'
        "<ApiException><Message>Invalid café</Message>"
        "<Message>Name required</Message></ApiException>"
    ).encode(wire_encoding)
    assert_error(
        XeroBadRequest(original),
        original,
        "Invalid café",
        ["Name required"],
        "Name required",
    )


@pytest.mark.parametrize("encoding", ["unsupported", "ascii"])
def test_unusable_xml_encoding_preserves_the_http_error(encoding):
    body = "<ApiException><Message>Invalid café</Message></ApiException>"
    original = response(body, "text/xml")
    original.encoding = encoding
    assert_error(XeroBadRequest(original), original, body, [body], body)


@pytest.mark.parametrize(
    "body", ["not JSON", "{", "null", "[]", '"error"', "42", "true"]
)
@pytest.mark.parametrize("error_class", [XeroBadRequest, XeroUnauthorized])
def test_invalid_json_uses_the_original_body(error_class, body):
    original = response(body, " Application/Problem+JSON ; charset=utf-8 ")
    assert_error(error_class(original), original, body, [body], body)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (
            {"type": "Validation", "message": "Invalid project"},
            "Validation: Invalid project",
        ),
        (
            {"title": "Bad Request", "detail": "Invalid project"},
            "Bad Request: Invalid project",
        ),
        (
            {
                "Type": "Existing",
                "Title": "Title",
                "type": "New",
                "Message": "Existing message",
                "message": "New message",
            },
            "Existing: Existing message",
        ),
        (
            {
                "Title": "Existing",
                "type": "New",
                "Detail": "Existing detail",
                "message": "New message",
            },
            "Existing: Existing detail",
        ),
        (
            {"Type": None, "Message": 42, "message": "Invalid project"},
            "Error: Invalid project",
        ),
        ({}, "Error: No Message Provided"),
    ],
)
def test_json_summary_aliases_preserve_existing_precedence(data, message):
    original = response(json.dumps(data), "APPLICATION/JSON; charset=utf-8")
    assert_error(XeroBadRequest(original), original, message, [], None)


def test_projects_details_append_to_accounting_validation_errors():
    data = {
        "message": "Invalid project",
        "Elements": [
            {
                "ValidationErrors": [
                    {"Message": "Accounting error"},
                    {},
                    {"Message": None},
                ]
            }
        ],
        "modelState": {
            "name": ["Name required", None, "Name required"],
            "deadline": "Date required",
            "other": {"nested": ["Unsupported"]},
            "null": None,
        },
    }
    original = response(json.dumps(data), "application/json")
    errors = ["Accounting error", "Name required", "Name required", "Date required"]
    assert_error(
        XeroBadRequest(original),
        original,
        "Error: Invalid project (Accounting error, and 4 other issues)",
        errors,
        errors[0],
    )


@pytest.mark.parametrize(
    "data",
    [
        {"Elements": None, "modelState": None},
        {"Elements": "invalid", "modelState": []},
        {
            "Elements": [
                None,
                {"ValidationErrors": None},
                {"ValidationErrors": [None, {}, {"Message": 42}]},
            ]
        },
    ],
)
def test_unusable_validation_containers_do_not_hide_the_summary(data):
    original = response(json.dumps(data), "application/json")
    assert_error(
        XeroBadRequest(original), original, "Error: No Message Provided", [], None
    )


@pytest.mark.parametrize("content_type", [None, "text/plain", "text/html"])
@pytest.mark.parametrize("error_class", [XeroBadRequest, XeroUnauthorized])
def test_oauth_forms_keep_their_first_problem_and_advice(error_class, content_type):
    original = response(
        "oauth_problem=invalid&oauth_problem=other&oauth_problem_advice=Try+again%3A+later",
        content_type,
    )
    assert_error(
        error_class(original), original, "Try again: later", ["invalid"], "invalid"
    )


@pytest.mark.parametrize("advice", ["", "&oauth_problem_advice="])
def test_oauth_missing_or_blank_advice_uses_the_problem(advice):
    original = response("oauth_problem=invalid" + advice)
    assert_error(XeroBadRequest(original), original, "invalid", ["invalid"], "invalid")


@pytest.mark.parametrize(
    ("data", "message", "problem"),
    [
        (
            {"detail": "TokenExpired: Access expired"},
            "TokenExpired: Access expired",
            "TokenExpired",
        ),
        (
            {"Detail": "Existing: detail", "detail": "New: detail"},
            "Existing: detail",
            "Existing",
        ),
        ({"Detail": None, "detail": "Invalid"}, "Invalid", "Invalid"),
        ({"detail": 42}, "", ""),
        ({}, "", ""),
    ],
)
def test_unauthorized_lowercase_detail_keeps_its_message_contract(
    data, message, problem
):
    original = response(json.dumps(data), "application/json")
    assert_error(XeroUnauthorized(original), original, message, [problem], problem)


def test_all_raise_owners_preserve_a_plain_text_bad_request():
    original = response("Bad Request")
    xero = Xero(Mock(base_url=""))
    owners = [
        xero.contacts.all,
        xero.filesAPI.files.all,
        xero.projectsAPI.projects.all,
        lambda: PublicCredentials._handle_error_response(Mock(), original),
        lambda: OAuth2Credentials._handle_error_response(original),
    ]
    for owner in owners:
        with pytest.MonkeyPatch.context() as patcher:
            patcher.setattr("requests.get", Mock(return_value=original))
            with pytest.raises(XeroBadRequest) as caught:
                owner()
        assert_error(
            caught.value, original, "Bad Request", ["Bad Request"], "Bad Request"
        )
