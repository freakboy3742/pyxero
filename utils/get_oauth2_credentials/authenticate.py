#!/usr/bin/env python3

import http.server
import subprocess
import webbrowser
import ssl
import sys
import json
import io
from urllib.parse import urlparse
from pathlib import Path
from dataclasses import dataclass
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
from collections import namedtuple

file_path = Path(__file__).resolve()
src_path = str(file_path.parents[2] / "src")

# Allow using the local source version of PyXero if not installed in Python env.
# This would mostly be useful for anyone making changes to PyXero's auth flow and needing
# to test it still works.
try:
    import xero

    print("Using PyXero installed in Python environment.")
except ImportError:
    sys.path.insert(0, src_path)
    import xero

    print(f"Using PyXero from local source directory ({src_path}).")


DOMAIN = "localhost"
PORT = 9376  # XERO on a pin-pad/telephone

CERT_FILE_PATH = str(file_path.parents[0] / ".cert")
KEY_FILE_PATH = str(file_path.parents[0] / ".key")
STATE_FILE_PATH = str(file_path.parents[0] / ".auth_state.json")
EXAMPLE_FILE_PATH = str(file_path.parents[0] / "example.py")

TEMPLATES: dict[str, str] = {}
for extension, templates in (
    (
        "html",
        (
            "base",
            "form",
            "success",
            "tenant",
        ),
    ),
    ("py", ("example",)),
):
    for template in templates:
        with open(
            file_path.parent / "templates" / f"{template}.{extension}.template", "r"
        ) as f:
            TEMPLATES[template] = f.read()

URL_PATHS = namedtuple(
    typename="URLPaths",
    field_names=[
        "callback",
        "select_tenant",
        "success",
        "favicon",
        "index",
    ],
)(
    callback="c",
    select_tenant="tenant",
    success="success",
    favicon="favicon.ico",
    index="",
)

CALLBACK_URL = f"https://{DOMAIN}:{PORT}/{URL_PATHS.callback}/"

MESSAGES = []  # cache to provide user feedback


def generate_self_signed_certificate(
    cert_path: str, key_path: str, common_name: str, days: int = 365
) -> None:
    command = [
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:4096",
        "-nodes",
        "-out",
        cert_path,
        "-keyout",
        key_path,
        "-days",
        str(days),
        "-subj",
        f"/CN={common_name}",
    ]
    subprocess.run(
        command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )


def read_state_file() -> dict:
    try:
        with open(STATE_FILE_PATH, "r") as f:
            try:
                return json.load(f)
            except json.decoder.JSONDecodeError:
                return {}
    except FileNotFoundError:
        return {}


def write_state_file(state: dict) -> None:
    with open(STATE_FILE_PATH, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)


class Context(dict):
    """
    Modified dictionary that won't ever raise a KeyError.

    "Templates" are handled using `str.format()` and if a particular
    key is in the template but not provided, then we want to fail
    gracefully instead of raising KeyError.
    """

    def __missing__(self, key):
        return key


@dataclass
class FormTextInput:
    name: str
    title: str
    value: str = ""

    def __str__(self):
        return (
            f'<div class="mb-3">'
            f'<label for="input_{self.name}" class="form-label">{self.title}</label>'
            f'<input type="text" name="{self.name}" id="input_{self.name}" class="form-control" value="{self.value}" required>'
            f"</div>"
        )


@dataclass
class ScopeCheckBox:
    name: str
    checked: bool

    def __str__(self):
        return (
            f'<div class="form-check my-1">'
            f'<input class="form-check-input" type="checkbox" name="scope__{self.name}" id="scope__{self.name}" {"checked" if self.checked else ""}>'
            f'<label for="scope__{self.name}" class="form-check-label">{self.name}</label>'
            f"</div>"
        )


@dataclass
class TenantRadio:
    tenant_id: str
    name: str
    kind: str

    def __str__(self):
        return (
            f"<tr>"
            f"<td>"
            f'<input class="form-check-input" type="radio" name="tenant" value="{self.tenant_id}" id="tenant__{self.tenant_id}" required>'
            f"</td>"
            f"<td>"
            f'<label for="tenant__{self.tenant_id}" class="d-flex">{self.name}</label>'
            f"</td>"
            f"<td>"
            f'<label for="tenant__{self.tenant_id}" class="d-flex">{self.kind}</label>'
            f"</td>"
            f"</tr>"
        )


def get_scopes() -> dict[str, list[str]]:
    restricted_scopes = [
        xero.constants.XeroScopes.PAYMENTSERVICES,
        xero.constants.XeroScopes.BANKFEEDS,
    ]
    scopes = []
    for key, val in xero.constants.XeroScopes.__dict__.items():
        if key.upper() == key:
            if val not in restricted_scopes:
                scopes.append(val)

    return {
        "scopes": scopes,
        "restricted_scopes": restricted_scopes,
    }


class HTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_request(self, *args, **kwargs) -> None:
        # Override the default to not log successful requests.
        pass

    def copyfile(self, source, outputfile) -> None:
        http.server.SimpleHTTPRequestHandler.copyfile(self, source, outputfile)

    def send_redirect_response(self, url: str, permanent: bool = False) -> None:
        if permanent:
            self.send_response(
                301
            )  # Using 301 over 308 because we actually WANT browsers to switch to GET (implicit)
        else:
            self.send_response(303)  # 303 to ensure browsers switch to GET (explicit)

        self.send_header("Location", url)
        self.end_headers()

    def redirect_to_index(self) -> None:
        self.send_redirect_response(f"/{URL_PATHS.index}/")

    def redirect_to_select_tenant(self) -> None:
        self.send_redirect_response(f"/{URL_PATHS.select_tenant}/")

    def redirect_to_success(self) -> None:
        self.send_redirect_response(f"/{URL_PATHS.success}/")

    def send_html_response(
        self, body: str, status_code: int = 200, encoding: str = "utf-8"
    ) -> None:
        with io.BytesIO() as f:
            f.write(body.encode(encoding))
            length = f.tell()
            f.seek(0)
            self.send_response(status_code)
            self.send_header("Content-type", f"text/html; charset={encoding}")
            self.send_header("Content-Length", str(length))
            self.end_headers()
            self.copyfile(f, self.wfile)

    @property
    def clean_path(self) -> str:
        # Parse request path, handle both presence and absense of trailing slash
        return urlparse(self.path).path.lstrip("/").rstrip("/")

    @staticmethod
    def add_message(message: str, *, level: str = "info") -> None:
        MESSAGES.append((level, message))

    def add_error_message(self, message: str) -> None:
        self.add_message(
            message=message,
            level="error",
        )

    @staticmethod
    def get_messages() -> str:
        messages = []
        while MESSAGES:
            level, message = MESSAGES.pop()
            level = "danger" if level == "error" else level
            messages.append(
                """
                <section class="row">
                    <div class="alert alert-{level}">
                        {message}
                    </div>
                </section>
                """.format(
                    message=message, level=level
                )
            )
        return "\n".join(messages)

    def do_GET(self) -> None:
        path = self.clean_path

        state = read_state_file()

        if path == URL_PATHS.callback:
            if not "?" in self.path:
                return self.redirect_to_index()

            if state:
                credentials = xero.auth.OAuth2Credentials(
                    # In development a user may need to experiment with requesting fewer scopes.
                    relax_token_scope=True,
                    **state,
                )
                auth_secret = f"https://{DOMAIN}:{PORT}{self.path}"
                try:
                    credentials.verify(auth_secret)
                except Exception as e:
                    self.add_error_message(
                        f"Failed to verify credentials: {e}. Please try re-authenticating to Xero."
                    )
                    return self.redirect_to_index()
                write_state_file(credentials.state)

                return self.redirect_to_select_tenant()
            else:
                self.add_error_message(
                    "Auth state has expired, please re-authenticate to Xero."
                )
                return self.redirect_to_index()

        elif path == URL_PATHS.select_tenant:
            if state:
                credentials = xero.auth.OAuth2Credentials(**state)
                if credentials.expired(seconds=200):
                    try:
                        credentials.refresh()
                    except Exception as e:
                        self.add_error_message(
                            f"Failed to refresh credentials: {e}. Please try re-authenticating to Xero."
                        )
                        return self.redirect_to_index()
                    else:
                        write_state_file(credentials.state)
                if credentials.tenant_id:
                    self.redirect_to_success()
                try:
                    tenants = credentials.get_tenants()
                except TokenExpiredError:
                    self.add_error_message(
                        "Your token has expired, please re-authenticate to Xero."
                    )
                    return self.redirect_to_index()
                else:
                    if len(tenants) == 1:
                        if tenant_id := tenants[0].get("tenantId"):
                            credentials.tenant_id = tenant_id
                            write_state_file(credentials.state)
                            return self.redirect_to_success()

                    return self.send_html_response(
                        TEMPLATES["base"].format_map(
                            Context(
                                title="Select a tenant",
                                content=TEMPLATES["tenant"].format_map(
                                    Context(
                                        tenants="\n".join(
                                            [
                                                str(
                                                    TenantRadio(
                                                        tenant_id=tenant["tenantId"],
                                                        name=tenant["tenantName"],
                                                        kind=tenant[
                                                            "tenantType"
                                                        ].title(),
                                                    )
                                                )
                                                for tenant in tenants
                                            ]
                                        ),
                                    )
                                ),
                                messages=self.get_messages(),
                            )
                        )
                    )
            else:
                self.add_error_message(
                    "Auth state has expired, please re-authenticate to Xero."
                )
                return self.redirect_to_index()

        elif path == URL_PATHS.success:
            if state:
                credentials = xero.auth.OAuth2Credentials(**state)
                if credentials.expired(seconds=200):
                    try:
                        credentials.refresh()
                    except Exception as e:
                        self.add_error_message(
                            f"Failed to refresh credentials: {e}. Please try re-authenticating to Xero."
                        )
                        return self.redirect_to_index()
                    else:
                        write_state_file(credentials.state)

                if not credentials.tenant_id:
                    return self.redirect_to_select_tenant()

                xero_api = xero.api.Xero(credentials)
                organisation = xero_api.organisations.all()[0]
                short_code = organisation["ShortCode"]
                contacts = xero_api.contacts.filter(page=1)[:10]

                example = TEMPLATES["example"].format_map(
                    Context(
                        state_file_path=STATE_FILE_PATH,
                        src_path=src_path,
                    )
                )

                with open(EXAMPLE_FILE_PATH, "w") as f:
                    f.write(example)

                print(
                    "\n\n\n"
                    "---- Authentication is now complete. This web server will now self-terminate."
                    "\n\n"
                    f"An example file has been saved at {EXAMPLE_FILE_PATH} to allow you to access and use the Xero API."
                    "\n\n"
                    "Please remember this tool is only intended for development uses."
                )

                self.send_html_response(
                    TEMPLATES["base"].format_map(
                        Context(
                            title="Success!",
                            content=TEMPLATES["success"].format_map(
                                Context(
                                    contacts="\n".join(
                                        [
                                            f"<tr>"
                                            f'<td>{contact["Name"]}</td>'
                                            f"<td>"
                                            f'<a href="https://go.xero.com/app/{short_code}/contacts/contact/{contact["ContactID"]}" '
                                            f'target="_blank">{contact["ContactID"]}</a>'
                                            f"</td>"
                                            f"</tr>"
                                            for contact in contacts
                                        ]
                                    ),
                                    organisation=organisation["Name"],
                                    example=example,
                                    example_path=EXAMPLE_FILE_PATH,
                                )
                            ),
                            messages=self.get_messages(),
                        )
                    )
                )
                sys.exit(0)

            else:
                self.add_error_message(
                    "Auth state has expired, please re-authenticate to Xero."
                )
                return self.redirect_to_index()

        elif path == URL_PATHS.index:

            all_scopes = get_scopes()

            if state.get("scope") and isinstance(state.get("scope"), list):
                scopes = "\n".join(
                    [
                        str(
                            ScopeCheckBox(
                                name=scope,
                                checked=(scope in state["scope"]),
                            )
                        )
                        for scope in all_scopes["scopes"]
                    ]
                )
                restricted_scopes = "\n".join(
                    [
                        str(
                            ScopeCheckBox(
                                name=scope,
                                checked=(scope in state["scope"]),
                            )
                        )
                        for scope in all_scopes["restricted_scopes"]
                    ]
                )

            else:
                scopes = "\n".join(
                    [
                        str(ScopeCheckBox(name=scope, checked=False))
                        for scope in all_scopes["scopes"]
                    ]
                )

                restricted_scopes = "\n".join(
                    [
                        str(ScopeCheckBox(name=scope, checked=False))
                        for scope in all_scopes["restricted_scopes"]
                    ]
                )

            return self.send_html_response(
                TEMPLATES["base"].format_map(
                    Context(
                        title="Connect to Xero via OAuth 2.0",
                        content=TEMPLATES["form"].format_map(
                            Context(
                                fields="\n".join(
                                    [
                                        str(
                                            FormTextInput(
                                                title="Xero Client ID",
                                                name="client_id",
                                                value=state.get("client_id") or "",
                                            )
                                        ),
                                        str(
                                            FormTextInput(
                                                title="Xero Client Secret",
                                                name="client_secret",
                                                value=state.get("client_secret") or "",
                                            )
                                        ),
                                    ]
                                ),
                                scopes=scopes,
                                restricted_scopes=restricted_scopes,
                                callback_url=CALLBACK_URL,
                            )
                        ),
                        messages=self.get_messages(),
                    )
                )
            )

        elif path == URL_PATHS.favicon:
            return self.send_redirect_response(
                url="https://edge.xero.com/images/1.0.0/favicon/favicon.ico",
                permanent=True,
            )
        else:
            self.add_error_message(f"Unknown path: /{path}/")
            return self.redirect_to_index()

    def do_POST(self) -> None:
        path = self.clean_path
        content_length = int(self.headers["Content-Length"])
        post_data = dict(
            [
                (
                    item.split("=") if "=" in item else (item, "")
                )  # not-nice fallback in case of malformed POST
                for item in self.rfile.read(content_length).decode("utf-8").split("&")
            ]
        )

        if path == URL_PATHS.select_tenant:
            tenant_id = post_data.get("tenant")
            if not tenant_id:
                self.add_error_message("No tenant was selected")

            state = read_state_file()
            if state:
                credentials = xero.auth.OAuth2Credentials(**state)
                if credentials.expired(seconds=200):
                    try:
                        credentials.refresh()
                    except Exception as e:
                        self.add_error_message(
                            f"Failed to refresh credentials: {e}. Please try re-authenticating to Xero."
                        )
                        return self.redirect_to_index()
                    else:
                        write_state_file(credentials.state)
                try:
                    tenants = credentials.get_tenants()
                except TokenExpiredError:
                    self.add_error_message(
                        "Your token has expired, please re-authenticate to Xero."
                    )
                    return self.redirect_to_index()
                else:
                    tenant_ids = [tenant["tenantId"] for tenant in tenants]

                    if tenant_id not in tenant_ids:
                        self.add_error_message(
                            "The selected tenant is somehow not valid. (???wtf???)"
                        )
                        return self.redirect_to_index()

                    credentials.tenant_id = tenant_id
                    write_state_file(credentials.state)
                    return self.redirect_to_success()

            else:
                self.add_error_message(
                    "Auth state has expired, please re-authenticate to Xero."
                )
                return self.redirect_to_index()

        elif path == URL_PATHS.index:
            scopes = [
                scope.split("__")[1]
                for scope in filter(lambda x: "scope__" in x, post_data.keys())
            ]

            credentials = xero.auth.OAuth2Credentials(
                client_id=post_data.get("client_id"),
                client_secret=post_data.get("client_secret"),
                callback_uri=CALLBACK_URL,
                scope=scopes,
            )

            url = credentials.generate_url()
            write_state_file(credentials.state)

            return self.send_redirect_response(url)

        else:
            return self.redirect_to_index()


if __name__ == "__main__":

    print(
        "\n\n\n---- Generating a self-signed certificate. Xero requires the OAuth callback URI to use HTTPS.\n"
        "You will receive a certificate warning from your browser but the callback will still work."
    )

    generate_self_signed_certificate(
        cert_path=CERT_FILE_PATH,
        key_path=KEY_FILE_PATH,
        common_name=DOMAIN,
    )
    context = ssl.SSLContext(
        protocol=ssl.PROTOCOL_TLS_SERVER,
    )
    context.load_cert_chain(
        certfile=CERT_FILE_PATH,
        keyfile=KEY_FILE_PATH,
    )

    print(
        "\n\n\n---- Starting a web server to begin the authentication process with Xero."
    )

    httpd = http.server.HTTPServer(
        server_address=(
            DOMAIN,
            PORT,
        ),
        RequestHandlerClass=HTTPRequestHandler,
    )
    httpd.socket = context.wrap_socket(
        httpd.socket,
        server_side=True,
    )
    app_url = f"https://{DOMAIN}:{PORT}/"

    webbrowser.open(app_url)

    print(
        f"Please open your web browser and navigate to {app_url} if it did not automatically open."
    )

    httpd.serve_forever()
