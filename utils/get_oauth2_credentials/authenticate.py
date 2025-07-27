#!/usr/bin/env python3

import http.server
import subprocess
import webbrowser
import ssl
import sys
import json
import io
from functools import cached_property
from urllib.parse import urlparse
from pathlib import Path
from dataclasses import dataclass
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
from collections import namedtuple

# Allow using the local source version of PyXero if not installed in Python env.
# This would mostly be useful for anyone making changes to PyXero's auth flow and needing
# to test it still works.
try:
    import xero
    print('Using PyXero installed in Python environment.')
except ImportError:

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

    import xero

    print('Using PyXero from local source directory.')


DOMAIN = 'localhost'
PORT = 9376  # XERO on a pin-pad/telephone
CERT_FILE = '.cert'
KEY_FILE = '.key'
CALLBACK_PATH = 'c'
STATE_FILE = str(Path(__file__).resolve().parents[0] / '.auth_state.json')

URL_PATHS = namedtuple(
    'URLPaths', [
        'callback',
        'select_tenant',
        'success',
        'favicon',
        'index',
    ])(
    callback='c',
    select_tenant='tenant',
    success='success',
    favicon='favicon.ico',
    index='',
)

CALLBACK_URL = f'https://{DOMAIN}:{PORT}/{URL_PATHS.callback}/'

MESSAGES = []  # cache to provide user feedback

def generate_self_signed_certificate(cert_path, key_path, common_name, days=365):
    command = [
        "openssl", "req", "-x509", "-newkey", "rsa:4096", "-nodes",
        "-out", cert_path, "-keyout", key_path, "-days", str(days),
        "-subj", f"/CN={common_name}"
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def read_state_file() -> dict:
    try:
        with open(STATE_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.decoder.JSONDecodeError:
                return {}
    except FileNotFoundError:
        return {}


def write_state_file(state: dict) -> None:
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, sort_keys=True)


class Context(dict):
    def __missing__(self, key):
        return key


@dataclass
class FormTextInput:
    name: str
    title: str
    value: str = ''

    def __str__(self):
        return (
            f'<div class="mb-3">'
            f'<label for="input_{self.name}" class="form-label">{self.title}</label>'
            f'<input type="text" name="{self.name}" id="input_{self.name}" class="form-control" value="{self.value}" required>'
            f'</div>'
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
            f'</div>'
        )

@dataclass
class TenantRadio:
    tenant_id: str
    name: str
    kind: str

    def __str__(self):
        return (
            f'<tr>'
            f'<td>'
            f'<input class="form-check-input" type="radio" name="tenant" value="{self.tenant_id}" id="tenant__{self.tenant_id}" required>'
            f'</td>'
            f'<td>'
            f'<label for="tenant__{self.tenant_id}" class="d-flex">{self.name}</label>'
            f'</td>'
            f'<td>'
            f'<label for="tenant__{self.tenant_id}" class="d-flex">{self.kind}</label>'
            f'</td>'
            f'</tr>'
        )


def get_scopes():
    restricted_scopes = [
        xero.constants.XeroScopes.PAYMENTSERVICES,
        xero.constants.XeroScopes.BANKFEEDS,
    ]
    scopes = []
    for (key, val) in xero.constants.XeroScopes.__dict__.items():
        if key.upper() == key:
            if val not in restricted_scopes:
                scopes.append(val)

    return {
        'scopes': scopes,
        'restricted_scopes': restricted_scopes,
    }


class HTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_request(self, code='-', message='-'):
        pass

    def copyfile(self, source, outputfile):
        http.server.SimpleHTTPRequestHandler.copyfile(self, source, outputfile)

    def send_redirect_response(self, url):
        """
        Send a 303 temporary redirect response to the given URI.
        303 is used to ensure the response is always changed to GET rather than POST.
        """
        self.send_response(303)
        self.send_header("Location", url)
        self.end_headers()

    def redirect_to_index(self):
        self.send_redirect_response(f'/{URL_PATHS.index}/')

    def redirect_to_select_tenant(self):
        self.send_redirect_response(f'/{URL_PATHS.select_tenant}/')

    def redirect_to_success(self):
        self.send_redirect_response(f'/{URL_PATHS.success}/')

    def send_html_response(self, body: str, status_code: int = 200, encoding: str = 'utf-8') -> None:
        with io.BytesIO() as f:
            f.write(body.encode(encoding))
            length = f.tell()
            f.seek(0)
            self.send_response(status_code)
            self.send_header("Content-type", f"text/html; charset={encoding}")
            self.send_header("Content-Length", str(length))
            self.end_headers()
            self.copyfile(f, self.wfile)

    @cached_property
    def templates(self):
        with open(Path(__file__).resolve().parent / 'templates' / 'base.html', 'r') as f:
            base_template = f.read()
        with open(Path(__file__).resolve().parent / 'templates' / 'form.html', 'r') as f:
            form_template = f.read()
        with open(Path(__file__).resolve().parent / 'templates' / 'tenant.html', 'r') as f:
            tenant_template = f.read()
        with open(Path(__file__).resolve().parent / 'templates' / 'success.html', 'r') as f:
            success_template = f.read()

        return {
            'base': base_template,
            'form': form_template,
            'tenant': tenant_template,
            'success': success_template,
        }

    @property
    def clean_path(self) -> str:
        # Parse request path, handle both presence and absense of trailing slash
        return urlparse(self.path).path.lstrip('/').rstrip('/')

    @staticmethod
    def add_message(message: str, *, level: str = 'info') -> None:
        MESSAGES.append((level, message))

    @staticmethod
    def add_success_message(message: str) -> None:
        MESSAGES.append(('success', message))

    @staticmethod
    def add_error_message(message: str) -> None:
        MESSAGES.append(('error', message))

    @staticmethod
    def get_messages() -> str:
        messages = []
        while MESSAGES:
            level, message = MESSAGES.pop()
            level = 'danger' if level == 'error' else level
            messages.append("""
                <section class="row">
                    <div class="alert alert-{level}">
                        {message}
                    </div>
                </section>
                """.format(message=message, level=level)
            )
        return '\n'.join(messages)

    def do_GET(self):
        path = self.clean_path

        state = read_state_file()

        if path == URL_PATHS.callback:
            if not '?' in self.path:
                self.redirect_to_index()
                return

            if state:
                credentials = xero.auth.OAuth2Credentials(
                    # In development a user may need to experiment with requesting fewer scopes.
                    relax_token_scope=True,
                    **state,
                )
                auth_secret = f'https://{DOMAIN}:{PORT}{self.path}'
                try:
                    credentials.verify(auth_secret)
                except Exception as e:
                    self.add_error_message(f'Failed to verify credentials: {e}. Please try re-authenticating to Xero.')
                    self.redirect_to_index()
                    return
                write_state_file(credentials.state)

                self.redirect_to_select_tenant()
                return

        elif path == URL_PATHS.select_tenant:
            if state:
                credentials = xero.auth.OAuth2Credentials(**state)
                if credentials.expired(seconds=200):
                    try:
                        credentials.refresh()
                    except Exception as e:
                        self.add_error_message(f'Failed to refresh credentials: {e}. Please try re-authenticating to Xero.')
                        self.redirect_to_index()
                        return
                    else:
                        write_state_file(credentials.state)
                if credentials.tenant_id:
                    self.redirect_to_success()
                try:
                    tenants = credentials.get_tenants()
                except TokenExpiredError:
                    self.add_error_message('Your token has expired, please re-authenticate to Xero.')
                    self.redirect_to_index()
                    return
                else:
                    if len(tenants) == 1:
                        if tenant_id := tenants[0].get('tenantId'):
                            credentials.tenant_id = tenant_id
                            write_state_file(credentials.state)
                            self.redirect_to_success()
                            return
                    self.send_html_response(self.templates['base'].format_map(Context(
                        title='Select a tenant',
                        content=self.templates['tenant'].format_map(Context(
                            tenants='\n'.join([
                                str(TenantRadio(
                                    tenant_id=tenant['tenantId'],
                                    name=tenant['tenantName'],
                                    kind=tenant['tenantType'].title(),
                                ))
                                for tenant in tenants
                            ]),
                        )),
                        messages=self.get_messages(),
                    )))
                    return
            else:
                self.add_error_message('Auth state has expired, please re-authenticate to Xero.')
                self.redirect_to_index()
                return

        elif path == URL_PATHS.success:
            if state:
                credentials = xero.auth.OAuth2Credentials(**state)
                if credentials.expired(seconds=200):
                    try:
                        credentials.refresh()
                    except Exception as e:
                        self.add_error_message(f'Failed to refresh credentials: {e}. Please try re-authenticating to Xero.')
                        self.redirect_to_index()
                        return
                    else:
                        write_state_file(credentials.state)
                if not credentials.tenant_id:
                    self.redirect_to_select_tenant()
                    return
                xero_api = xero.api.Xero(credentials)
                organisation = xero_api.organisations.all()[0]
                short_code = organisation['ShortCode']
                contacts = xero_api.contacts.filter(page=1)[:10]
                self.send_html_response(self.templates['base'].format_map(Context(
                    title='Success!',
                    content=self.templates['success'].format_map(Context(
                        contacts='\n'.join([
                            f'<tr>'
                            f'<td>{contact["Name"]}</td>'
                            f'<td><a href="https://go.xero.com/app/{short_code}/contacts/contact/{contact["ContactID"]}" target="_blank">{contact["ContactID"]}</a></td>'
                            f'</tr>'
                            for contact
                            in contacts
                        ]),
                        organisation=organisation['Name'],
                        state_file_path = STATE_FILE,
                    )),
                    messages=self.get_messages(),
                )))
                sys.exit(0)
                return   # unreachable but here in case I comment out the previous line
            self.add_error_message('Auth state has expired, please re-authenticate to Xero.')
            self.redirect_to_index()
            return

        elif path == URL_PATHS.index:

            all_scopes = get_scopes()

            if state.get('scope') and isinstance(state.get('scope'), list):
                scopes = '\n'.join([
                    str(ScopeCheckBox(
                        name=scope,
                        checked=(scope in state['scope']),
                    ))
                    for scope in all_scopes['scopes']
                ])
                restricted_scopes = '\n'.join([
                    str(ScopeCheckBox(
                        name=scope,
                        checked=(scope in state['scope']),
                    ))
                    for scope in all_scopes['restricted_scopes']
                ])

            else:
                scopes = '\n'.join([
                    str(ScopeCheckBox(name=scope, checked=False))
                    for scope in all_scopes['scopes']
                ])

                restricted_scopes = '\n'.join([
                    str(ScopeCheckBox(name=scope, checked=False))
                    for scope in all_scopes['restricted_scopes']
                ])
            self.send_html_response(self.templates['base'].format_map(Context(
                title='Connect to Xero via OAuth 2.0',
                content=self.templates['form'].format_map(Context(
                    fields='\n'.join([
                        str(FormTextInput(
                            title='Xero Client ID',
                            name='client_id',
                            value=state.get('client_id') or '',
                        )),
                        str(FormTextInput(
                            title='Xero Client Secret',
                            name='client_secret',
                            value=state.get('client_secret') or '',
                        )),
                    ]),
                    scopes=scopes,
                    restricted_scopes=restricted_scopes,
                    callback_url=CALLBACK_URL,
                )),
                messages=self.get_messages(),
            )))
            return

        elif path == URL_PATHS.favicon:
            self.send_redirect_response('https://edge.xero.com/images/1.0.0/favicon/favicon.ico')
            return
        else:
            self.add_error_message(f'Unknown path: /{path}/')
            self.redirect_to_index()
            return

    def do_POST(self):
        path = self.clean_path
        content_length = int(self.headers['Content-Length'])
        post_data = dict([
            (item.split('=') if '=' in item else (item,''))   # not-nice fallback in case of malformed POST
            for item
            in self.rfile.read(content_length).decode('utf-8').split('&')
        ])

        if path == URL_PATHS.select_tenant:
            tenant_id = post_data.get('tenant')
            if not tenant_id:
                self.add_error_message('No tenant was selected')

            state = read_state_file()
            if state:
                credentials = xero.auth.OAuth2Credentials(**state)
                if credentials.expired(seconds=200):
                    try:
                        credentials.refresh()
                    except Exception as e:
                        self.add_error_message(f'Failed to refresh credentials: {e}. Please try re-authenticating to Xero.')
                        self.redirect_to_index()
                        return
                    else:
                        write_state_file(credentials.state)
                try:
                    tenants = credentials.get_tenants()
                except TokenExpiredError:
                    self.add_error_message('Your token has expired, please re-authenticate to Xero.')
                    self.redirect_to_index()
                    return
                else:
                    tenant_ids = [
                        tenant['tenantId']
                        for tenant
                        in tenants
                    ]
                    if tenant_id not in tenant_ids:
                        self.add_error_message('The selected tenant is somehow not valid. (???wtf???)')
                        self.redirect_to_index()
                        return
                    credentials.tenant_id = tenant_id
                    write_state_file(credentials.state)
                    self.redirect_to_success()
                    return
            else:
                self.add_error_message('Auth state has expired, please re-authenticate to Xero.')
                self.redirect_to_index()
                return

        elif path == URL_PATHS.index:
            scopes = [
                scope.split('__')[1]
                for scope
                in filter(lambda x: 'scope__' in x, post_data.keys())
            ]

            credentials = xero.auth.OAuth2Credentials(
                client_id=post_data.get('client_id'),
                client_secret=post_data.get('client_secret'),
                callback_uri=CALLBACK_URL,
                scope=scopes,
            )

            url = credentials.generate_url()
            write_state_file(credentials.state)

            self.send_redirect_response(url)
            return

        else:
            self.redirect_to_index()
            return


if __name__ == '__main__':
    print(
        '\n\n\n---- Generating a self-signed certificate. Xero requires the OAuth callback URI to use HTTPS.\n'
        'You will receive a certificate warning from your browser but the callback will still work.'
    )
    generate_self_signed_certificate(
        cert_path=CERT_FILE,
        key_path=KEY_FILE,
        common_name=DOMAIN,
    )
    print('\n\n\n---- Starting a web server to begin the authentication process with Xero.')

    httpd = http.server.HTTPServer(
        server_address=(DOMAIN, PORT,),
        RequestHandlerClass=HTTPRequestHandler,
    )
    context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    httpd.socket = context.wrap_socket(
        httpd.socket,
        server_side=True,
    )
    url = f'https://{DOMAIN}:{PORT}/'
    webbrowser.open(url)
    print(f'Please open your web browser and navigate to {url} if it did not automatically open.')
    httpd.serve_forever()

