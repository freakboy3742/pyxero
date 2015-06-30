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

from xero.auth import PublicCredentials

PORT = 8000
verify_params_regex = re.compile(r'^access_token=(?P<access_token>[\w]+).*$')

class ExampleHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    consumer_key = None
    consumer_secret = None

    def __init__(self, request, client_address, server, consumer_key=None, consumer_secret=None):
        if consumer_key is None:
            self.consumer_key = os.environ.get('XERO_CONSUMER_KEY')
        else:
            self.consumer_key = consumer_key

        if consumer_secret is None:
            self.consumer_secret = os.environ.get('XERO_CONSUMER_SECRET')
        else:
            self.consumer_secret = consumer_secret

        SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)

    def redirect(self, url, permanent=False):
        if permanent:
            self.send_response(301)
        else:
            self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def do_GET(self):
        cookie_prefix = 'credentials'
        parts = self.path.split('?', 1)

        if len(parts) > 1:
            self.path = parts[0]
            request_params = parts[1]
        else:
            request_params = ''

        if self.path == '/do-auth/':
            credentials = PublicCredentials(
                self.consumer_key, self.consumer_secret,
                callback_uri='/verify.html')

            # Set cookies of all the credentials details.
            # HIGHLY INSECURE but needed for persistence of credential details between requests for
            # this example
            credentials_cookie = Cookie.SimpleCookie()
            for key, value in credentials.state.items():
                if isinstance(value, datetime.datetime):
                    value = value.strftime('%a, %d %b %Y %H:%M:%S')
                cookie_key = '{}_{}'.format(cookie_prefix, str(key))
                credentials_cookie[cookie_key] = value
                credentials_cookie[cookie_key]['path'] = '/'

            # Redirect to credentials.url
            self.send_response(302)
            self.send_header("Location", credentials.url)
            self.wfile.write(str(credentials_cookie))
            self.end_headers()
            return None
        else:
            match = verify_params_regex.match(request_params)
            if match:
                # Great, got a match. Parse out the credentials cookies to re-instantiate the
                # same credentials object
                credentials_cookie = Cookie.SimpleCookie(self.headers['cookie'])
                credentials_kwargs = {}
                for key, value in credentials_cookie.items():
                    if key.startswith(cookie_prefix):
                        key = key.split('_', 1)[1]
                        credentials_kwargs[key] = str(value)

                credentials = PublicCredentials(**credentials_kwargs)

                params = match.groupdict()
                credentials.verify(params['access_token'])

                # Once verified, api can be invoked with xero = Xero(credentials)
                self.redirect('/verified.html')

        return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == '__main__':
    httpd = SocketServer.TCPServer(("", PORT), ExampleHandler)

    print "serving at port", PORT
    httpd.serve_forever()


