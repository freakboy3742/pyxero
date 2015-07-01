import sys
import os
import re
import SimpleHTTPServer
import SocketServer
import Cookie
import datetime

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

from xero.auth import PublicCredentials
from xero.exceptions import XeroException

PORT = 8000
verify_params_regex = re.compile(r'^access_token=(?P<access_token>[\w]+).*$')

class ExampleHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def redirect(self, url, permanent=False):
        if permanent:
            self.send_response(301)
        else:
            self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def do_GET(self):
        consumer_key = os.environ.get('XERO_CONSUMER_KEY')
        consumer_secret = os.environ.get('XERO_CONSUMER_SECRET')

        if consumer_key is None or consumer_secret is None:
            raise KeyError(
                'Please define both XERO_CONSUMER_KEY and XERO_CONSUMER_SECRET environment variables')

        cookie_prefix = 'credentials'
        parts = self.path.split('?', 1)

        if len(parts) > 1:
            self.path = parts[0]
            request_params = parts[1]
        else:
            request_params = ''

        if self.path == '/do-auth/':
            credentials = PublicCredentials(
                consumer_key, consumer_secret, callback_uri='http://localhost:8000/oauth')

            # Set cookies of all the credentials details.
            # HIGHLY INSECURE. Do not persist credentials between requests this way in production.
            # Use a session key etc instead
            credentials_cookie = Cookie.SimpleCookie()
            for key, value in credentials.state.items():
                if isinstance(value, datetime.datetime):
                    value = value.strftime('%a, %d %b %Y %H:%M:%S')
                cookie_key = '{}_{}'.format(cookie_prefix, str(key))
                credentials_cookie[cookie_key] = value
                credentials_cookie[cookie_key]['path'] = '/'

            # Redirect to credentials.url
            print(credentials.url)
            self.send_response(302)
            self.send_header("Location", credentials.url)
            self.wfile.write(str(credentials_cookie))
            self.end_headers()
            return None

        elif self.path == '/verify/':
            match = verify_params_regex.match(request_params)
            if match:
                # Great, got a match for the access_token request parameter. Parse out the
                # credentials cookies to re-instantiate the same credentials object
                credentials_cookie = Cookie.SimpleCookie(self.headers['cookie'])
                credentials_kwargs = {}
                for key, value in credentials_cookie.items():
                    if key.startswith(cookie_prefix):
                        key = key.split('_', 1)[1]
                        credentials_kwargs[key] = str(value)

                credentials = PublicCredentials(**credentials_kwargs)

                params = match.groupdict()
                try:
                    credentials.verify(params['access_token'])
                except XeroException as e:
                    self.send_error(500, message='{}: {}'.format(e.__class__, e.message))
                    return None
                else:
                    # Once verified, api can be invoked with xero = Xero(credentials)
                    self.redirect('/verified.html')
                    return None

        return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == '__main__':
    httpd = SocketServer.TCPServer(("", PORT), ExampleHandler)

    print "serving at port", PORT
    httpd.serve_forever()


