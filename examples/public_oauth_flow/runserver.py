import sys
import os
import SimpleHTTPServer
import SocketServer
from urlparse import urlparse, parse_qsl

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from xero.auth import PublicCredentials
from xero.exceptions import XeroException
from xero import Xero

PORT = 8000


# You should use redis or a file based persistent
# storage handler if you are running multiple servers.
OAUTH_PERSISTENT_SERVER_STORAGE = {}


class ExampleHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def page_response(self, title='', body=''):
        """
        Helper to render an html page with dynamic content
        """
        f = StringIO()
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n')
        f.write('<html>\n')
        f.write('<head><title>{}</title><head>\n'.format(title))
        f.write('<body>\n<h2>Directory listing for {}</h2>\n'.format(title))
        f.write('<div class="content">{}</div>\n'.format(body))
        f.write('</body>\n</html>\n')
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        self.copyfile(f, self.wfile)
        f.close()

    def redirect_response(self, url, permanent=False):
        """
        Generate redirect response
        """
        if permanent:
            self.send_response(301)
        else:
            self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def do_GET(self):
        """
        Handle GET request
        """
        consumer_key = os.environ.get('XERO_CONSUMER_KEY')
        consumer_secret = os.environ.get('XERO_CONSUMER_SECRET')

        if consumer_key is None or consumer_secret is None:
            raise KeyError(
                'Please define both XERO_CONSUMER_KEY and XERO_CONSUMER_SECRET environment variables')

        print("Serving path: {}".format(self.path))
        path = urlparse(self.path)

        if path.path == '/do-auth':
            credentials = PublicCredentials(
                consumer_key, consumer_secret, callback_uri='http://localhost:8000/oauth')

            # Save generated credentials details to persistent storage
            for key, value in credentials.state.items():
                OAUTH_PERSISTENT_SERVER_STORAGE.update({key: value})

            # Redirect to Xero at url provided by credentials generation
            self.redirect_response(credentials.url)
            return

        elif path.path == '/oauth':
            params = dict(parse_qsl(path.query))
            if 'oauth_token' not in params or 'oauth_verifier' not in params or 'org' not in params:
                self.send_error(500, message='Missing parameters required.')
                return

            stored_values = OAUTH_PERSISTENT_SERVER_STORAGE
            credentials = PublicCredentials(**stored_values)

            try:
                credentials.verify(params['oauth_verifier'])

                # Resave our verified credentials
                for key, value in credentials.state.items():
                    OAUTH_PERSISTENT_SERVER_STORAGE.update({key: value})

            except XeroException as e:
                self.send_error(500, message='{}: {}'.format(e.__class__, e.message))
                return

            # Once verified, api can be invoked with xero = Xero(credentials)
            self.redirect_response('/verified')
            return

        elif path.path == '/verified':
            stored_values = OAUTH_PERSISTENT_SERVER_STORAGE
            credentials = PublicCredentials(**stored_values)

            try:
                xero = Xero(credentials)

            except XeroException as e:
                self.send_error(500, message='{}: {}'.format(e.__class__, e.message))
                return

            page_body = 'Your contacts:<br><br>'

            contacts = xero.contacts.all()

            if contacts:
                page_body += '<br>'.join([str(contact) for contact in contacts])
            else:
                page_body += 'No contacts'
            self.page_response(title='Xero Contacts', body=page_body)
            return

        SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)


if __name__ == '__main__':
    httpd = SocketServer.TCPServer(("", PORT), ExampleHandler)

    print "serving at port", PORT
    httpd.serve_forever()