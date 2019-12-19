import json
from datetime import datetime

import requests
from requests_oauthlib import OAuth2Session, OAuth2
from xero import Xero
from xero.constants import XERO_BASE_URL

# Use service discovery to find the endpoints we're going to use
connections_url = "https://api.xero.com/connections"
discovery_url = "https://identity.xero.com/.well-known/openid-configuration"
discovery = requests.get(discovery_url).json()
authorization_base_url = discovery['authorization_endpoint']
token_url = discovery['token_endpoint']
default_scopes = [
    'openid',
    'profile',
    'email',
]


class XeroToken:
    def __init__(self, token):
        self.access_token = token['access_token']
        self.id_token = token['id_token']
        self.refresh_token = token['refresh_token']
        self.token_type = token['token_type']
        self.expires_at = datetime.utcfromtimestamp(token['expires_at'])

    def as_json(self):
        return json.dumps(self.as_dict())

    def as_dict(self):
        return {
            "access_token": self.access_token,
            "id_token": self.id_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.timestamp(),
            "token_type": self.token_type
        }


class Flow:
    def __init__(self, client_id, client_secret, scopes, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or default_scopes
        self.redirect_uri = redirect_uri

    def start(self):
        session = OAuth2Session(self.client_id, scope=self.scopes, redirect_uri=self.redirect_uri)
        return session.authorization_url(authorization_base_url)

    def complete(self, state, response_url):
        client = OAuth2Session(client_id=self.client_id, state=state, scope=self.scopes, redirect_uri=self.redirect_uri)
        token = client.fetch_token(token_url, client_secret=self.client_secret, authorization_response=response_url)
        return XeroToken(token)


# OAuth2 version of pyxero PublicCredentials
class XeroOAuthV2:
    base_url = XERO_BASE_URL

    def __init__(self, client_id, token):
        self.oauth = OAuth2(client_id=client_id, token=token)


class Client(Xero):
    def __init__(self, client_id, token, tenant_id=None):
        creds = XeroOAuthV2(client_id=client_id, token=token)
        creds.tenant_id = tenant_id
        self.credentials = creds
        super(Client, self).__init__(credentials=creds)

    def load_connections(self):
        creds = self.credentials.oauth
        response = requests.get(connections_url, auth=creds)
        return response.json()
