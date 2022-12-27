# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import logging
from urllib.parse import urlencode

from cement.ext.ext_argparse import ex
from oauthlib.oauth2.rfc6749.clients.backend_application import BackendApplicationClient
from oauthlib.oauth2.rfc6749.clients.legacy_application import LegacyApplicationClient
from requests_oauthlib.oauth2_session import OAuth2Session
from beehive3_cli.core.controller import ARGS, PARGS
from beehive3_cli.plugins.auth.controllers.auth import AuthChildController

logger = logging.getLogger(__name__)


class Oauth2ControllerChild(AuthChildController):
    class Meta:
        cmp = {'baseuri': '/v1.0/nas/oauth2', 'subsystem': 'auth'}

        obj_headers = ['id', 'objid', 'subsystem', 'type', 'desc']
        type_headers = ['id', 'subsystem', 'type']
        act_headers = ['id', 'value']
        perm_headers = ['id', 'oid', 'objid', 'subsystem', 'type', 'aid', 'action']
        user_headers = ['id', 'uuid', 'name', 'active', 'date.creation', 'date.modified', 'date.expiry']
        role_headers = ['id', 'uuid', 'name', 'active', 'date.creation', 'date.modified', 'date.expiry']
        group_headers = ['id', 'uuid', 'name', 'active', 'date.creation', 'date.modified', 'date.expiry']
        token_headers = ['token', 'type', 'user', 'ip', 'ttl', 'timestamp'] 


class Oauth2TokenController(Oauth2ControllerChild):
    class Meta:
        label = 'oauth2_tokens'
        description = "oauth2 token"
        help = "oauth2 token"

    @ex(
        help='create oauth2 access token using resource_owner or client_credentials grant. For resource_owner grant '
             'specify user and pwd. For client_credentials specify client secret.',
        description='create oauth2 access token using resource_owner or client_credentials grant. For resource_owner '
                    'grant specify user and pwd. For client_credentials specify client secret.',
        arguments=ARGS([
            (['client'], {'help': 'client id', 'action': 'store', 'type': str}),
            (['-user'], {'help': 'login user', 'action': 'store', 'type': str, 'default': None}),
            (['-pwd'], {'help': 'user password', 'action': 'store', 'type': str, 'default': None}),
            (['-secret'], {'help': 'client secret', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def create(self):
        client_id = self.app.pargs.client
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        client_secret = self.app.pargs.secret

        # get client
        uri = '%s/clients/%s' % (self.baseuri, client_id)
        client = self.cmp_get(uri).get('client')

        client_id = client['uuid']
        client_scope = client['scopes']
        client_token_uri = client['token_uri']
        auth_type = ''

        if user is not None and pwd is not None:
            auth_type = 'resource_owner'
            client = LegacyApplicationClient(client_id=client_id)
            oauth = OAuth2Session(client=client)
            token = oauth.fetch_token(token_url=client_token_uri,
                                      username=user,
                                      password=pwd,
                                      client_id=client_id,
                                      verify=False)
        elif client_secret is not None:
            auth_type = 'client_credentials'
            client = BackendApplicationClient(client_id=client_id)
            oauth = OAuth2Session(client=client)
            token = oauth.fetch_token(token_url=client_token_uri,
                                      include_client_id=client_id,
                                      client_secret=client_secret,
                                      verify=False)

        logger.debug('Get %s token: %s' % (auth_type, token))
        self.app.render({'msg': 'Get token %s' % token})


class Oauth2SessionController(Oauth2ControllerChild):
    class Meta:
        label = 'oauth2_user_sessions'
        description = "oauth2 user session"
        help = "oauth2 user session"

        headers = ['sid', 'ttl', 'oauth2_user', 'oauth2_credentials']

    @ex(
        help='get oauth2 sessions',
        description='get oauth2 sessions',
        arguments=PARGS([
            (['-id'], {'help': 'session id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/user_sessions/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                self.app.render(res, key='user_session', details=True)
            else:
                self.app.render(res, key='user_session', details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/user_sessions' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='user_sessions', headers=self._meta.headers)

    @ex(
        help='delete oauth2 session',
        description='delete oauth2 session',
        arguments=ARGS([
            (['id'], {'help': 'comma separated session ids', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oids = self.app.pargs.id
        for oid in oids.split(','):
            uri = '%s/user_sessions/%s' % (self.baseuri, oid)
            self.cmp_delete(uri, entity='user session %s' % oid)


class AuthorizationCodeController(Oauth2ControllerChild):
    class Meta:
        label = 'oauth2_authorization_codes'
        description = "oauth2 authorization code"
        help = "oauth2 authorization code"

        headers = ['id', 'code', 'expires_at', 'client', 'user', 'scope', 'expired']

    @ex(
        help='get oauth2 authorization codes',
        description='get oauth2 authorization codes',
        arguments=PARGS([
            (['-id'], {'help': 'authorization code id', 'action': 'store', 'type': str, 'default': None}),
            (['-valid'], {'help': 'valid', 'action': 'store', 'type': str, 'default': None}),
            (['-client'], {'help': 'client', 'action': 'store', 'type': str, 'default': None}),
            (['-user'], {'help': '', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/authorization_codes/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                self.app.render(res, key='authorization_code', details=True)
            else:
                self.app.render(res, key='authorization_code', details=True)
        else:
            params = ['valid', 'client', 'user']
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/authorization_codes' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='authorization_codes', headers=self._meta.headers)

    @ex(
        help='delete oauth2 authorization code',
        description='delete oauth2 authorization code',
        arguments=ARGS([
            (['id'], {'help': 'comma separated authorization code ids', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oids = self.app.pargs.id
        for oid in oids.split(','):
            uri = '%s/authorization_codes/%s' % (self.baseuri, oid)
            self.cmp_delete(uri, entity='user session %s' % oid)


class ClientController(Oauth2ControllerChild):
    class Meta:
        label = 'oauth2_clients'
        description = "oauth2 client"
        help = "oauth2 client"

        headers = ['id', 'uuid', 'name', 'response_type', 'grant_type', 'scopes']
        fields = ['id', 'uuid', 'name', 'response_type', 'grant_type', 'scopes']

    @ex(
        help='add oauth2 client',
        description='add oauth2 client',
        arguments=ARGS([
            (['name'], {'help': 'client name', 'action': 'store', 'type': str}),
            (['grant_type'], {'help': 'valid grant_type: authorization_code, implicit, password, client_credentials, '
                                      'urn:ietf:params:oauth:grant-type:jwt-bearer', 'action': 'store', 'type': str}),
            (['-redirect_uri'], {'help': 'redirect_uri', 'action': 'store', 'type': str,
                                 'default': 'http://localhost'}),
            (['-scopes'], {'help': 'comma separated list of scopes', 'action': 'store', 'type': str,
                           'default': 'beehive'}),
            (['-expirydate'], {'help': 'client expire date. Syntax yyyy-mm-dd', 'action': 'store', 'type': str,
                               'default': None})
        ])
    )
    def add(self):
        name = self.app.pargs.name
        grant_type = self.app.pargs.grant_type
        redirect_uri = self.app.pargs.redirect_uri
        scopes = self.app.pargs.scopes
        expiry_date = self.app.pargs.expirydate
        if expiry_date is None:
            expiry_date = '2031-12-31'
        data = {
            'client': {
                'name': name,
                'grant_type': grant_type,
                'redirect_uri': redirect_uri,
                'desc': 'Client %s' % name,
                'response_type': 'code',
                'scopes': scopes,
                'expirydate': expiry_date
            }
        }
        uri = '%s/clients' % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add client %s' % res['uuid']})

    @ex(
        help='get oauth2 clients',
        description='get oauth2 clients',
        arguments=PARGS([
            (['-id'], {'help': 'client uuid', 'action': 'store', 'type': str, 'default': None}),
            (['-role'], {'help': 'role uuid', 'action': 'store', 'type': str, 'default': None}),
            (['-group'], {'help': 'group uuid', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'name filter', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'client desc', 'action': 'store', 'type': str, 'default': None}),
            (['-email'], {'help': 'email address', 'action': 'store', 'type': str, 'default': None}),
            (['-expiry-date '], {'help': 'expiry date. Syntax YYYY-MM-DD', 'action': 'store', 'type': str,
                                 'default': None}),
            (['-perms'], {'help': 'comma separated list of permission id', 'action': 'store', 'type': str,
                          'default': None}),
        ])
    )
    def get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/clients/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                self.app.render(res, key='client', details=True)
            else:
                self.app.render(res, key='client', details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/clients' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='clients', headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help='delete oauth2 client',
        description='delete oauth2 client',
        arguments=ARGS([
            (['id'], {'help': 'client uuid', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = '%s/clients/%s' % (self.baseuri, oid)
        self.cmp_delete(uri, entity='client %s' % oid)


class ScopeController(Oauth2ControllerChild):
    class Meta:
        label = 'oauth2_scopes'
        description = "oauth2 scope"
        help = "oauth2 scope"

        headers = ['id', 'uuid', 'name', 'active', 'date.creation']
        fields = ['id', 'uuid', 'name', 'active', 'date.creation']

    @ex(
        help='add oauth2 scope',
        description='add oauth2 scope',
        arguments=ARGS([
            (['name'], {'help': 'scope name', 'action': 'store', 'type': str})
        ])
    )
    def add(self):
        name = self.app.pargs.name
        data = {
            'scope': {
                'name': name,
                'desc': 'Scope %s' % name
            }
        }
        uri = '%s/scopes' % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add scope %s' % res['uuid']})

    @ex(
        help='get oauth2 scopes',
        description='get oauth2 scopes',
        arguments=PARGS([
            (['-id'], {'help': 'scope uuid', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/scopes/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                self.app.render(res, key='scope', details=True)
            else:
                self.app.render(res, key='scope', details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/scopes' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='scopes', headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help='delete oauth2 scope',
        description='delete oauth2 scope',
        arguments=ARGS([
            (['id'], {'help': 'scope uuid', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = '%s/scopes/%s' % (self.baseuri, oid)
        self.cmp_delete(uri, entity='scope %s' % oid)
