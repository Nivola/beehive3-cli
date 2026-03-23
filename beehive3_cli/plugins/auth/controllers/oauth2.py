# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from logging import getLogger
from oauthlib.oauth2.rfc6749.clients.backend_application import BackendApplicationClient
from oauthlib.oauth2.rfc6749.clients.legacy_application import LegacyApplicationClient
from cement.ext.ext_argparse import ex
from requests_oauthlib.oauth2_session import OAuth2Session
from beehive3_cli.core.controller import ARGS, PARGS
from beehive3_cli.plugins.auth.controllers.auth import AuthChildController
from beehive3_cli.translate import _

logger = getLogger(__name__)


class Oauth2ControllerChild(AuthChildController):
    class Meta:
        cmp = {"baseuri": "/v1.0/nas/oauth2", "subsystem": "auth"}

        obj_headers = ["id", "objid", "subsystem", "type", "desc"]
        type_headers = ["id", "subsystem", "type"]
        act_headers = ["id", "value"]
        perm_headers = ["id", "oid", "objid", "subsystem", "type", "aid", "action"]
        user_headers = [
            "id",
            "uuid",
            "name",
            "active",
            "date.creation",
            "date.modified",
            "date.expiry",
        ]
        role_headers = [
            "id",
            "uuid",
            "name",
            "active",
            "date.creation",
            "date.modified",
            "date.expiry",
        ]
        group_headers = [
            "id",
            "uuid",
            "name",
            "active",
            "date.creation",
            "date.modified",
            "date.expiry",
        ]
        token_headers = ["token", "type", "user", "ip", "ttl", "timestamp"]


class Oauth2TokenController(Oauth2ControllerChild):
    class Meta:
        label = "oauth2_tokens"
        description = _("oauth2 token")
        help = _("oauth2 token")

    @ex(
        help=_(
            "create oauth2 access token using resource_owner or client_credentials grant. For resource_owner grant "
            "specify user and pwd. For client_credentials specify client secret."
        ),
        description=_(
            "create oauth2 access token using resource_owner or client_credentials grant. For resource_owner "
            "grant specify user and pwd. For client_credentials specify client secret."
        ),
        arguments=ARGS(
            [
                (["client"], {"help": _("client id"), "action": "store", "type": str}),
                (
                    ["-user"],
                    {
                        "help": _("login user"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-pwd"],
                    {
                        "help": _("user password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-secret"],
                    {
                        "help": _("client secret"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def create(self):
        client_id = self.app.pargs.client
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        client_secret = self.app.pargs.secret

        # get client
        uri = f"{self.baseuri}/clients/{client_id}"
        client = self.cmp_get(uri).get("client")

        client_id = client["uuid"]
        #client_scope = client["scopes"]
        client_token_uri = client["token_uri"]
        auth_type = ""

        if user is not None and pwd is not None:
            auth_type = "resource_owner"
            client = LegacyApplicationClient(client_id=client_id)
            oauth = OAuth2Session(client=client)
            token = oauth.fetch_token(
                token_url=client_token_uri,
                username=user,
                password=pwd,
                client_id=client_id,
                verify=False,
            )
        elif client_secret is not None:
            auth_type = "client_credentials"
            client = BackendApplicationClient(client_id=client_id)
            oauth = OAuth2Session(client=client)
            token = oauth.fetch_token(
                token_url=client_token_uri,
                include_client_id=client_id,
                client_secret=client_secret,
                verify=False,
            )

        logger.debug("Get %s token: %s", auth_type, token)
        self.app.render({"msg": f"Get token {token}"})


class Oauth2SessionController(Oauth2ControllerChild):
    class Meta:
        label = "oauth2_user_sessions"
        description = _("oauth2 user session")
        help = _("oauth2 user session")

        headers = ["sid", "ttl", "oauth2_user", "oauth2_credentials"]

    @ex(
        help=_("get oauth2 sessions"),
        description=_("get oauth2 sessions"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("session id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/user_sessions/{oid}"
            res = self.cmp_get(uri)

            # if self.is_output_text():
            #     self.app.render(res, key="user_session", details=True)
            # else:
            self.app.render(res, key="user_session", details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/user_sessions"
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="user_sessions", headers=self._meta.headers)

    @ex(
        help=_("delete oauth2 session"),
        description=_("delete oauth2 session"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("comma separated session ids"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oids = self.app.pargs.id
        for oid in oids.split(","):
            uri = f"{self.baseuri}/user_sessions/{oid}"
            self.cmp_delete(uri, entity=f"user session {oid}")


class AuthorizationCodeController(Oauth2ControllerChild):
    class Meta:
        label = "oauth2_authorization_codes"
        description = _("oauth2 authorization code")
        help = _("oauth2 authorization code")

        headers = ["id", "code", "expires_at", "client", "user", "scope", "expired"]

    @ex(
        help=_("get oauth2 authorization codes"),
        description=_("get oauth2 authorization codes"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("authorization code id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-valid"],
                    {"help": _("valid"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-client"],
                    {"help": _("client"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-user"],
                    {"help": _(""), "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/authorization_codes/{oid}"
            res = self.cmp_get(uri)

            # if self.is_output_text():
            #     self.app.render(res, key="authorization_code", details=True)
            # else:
            self.app.render(res, key="authorization_code", details=True)
        else:
            params = ["valid", "client", "user"]
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/authorization_codes"
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="authorization_codes", headers=self._meta.headers)

    @ex(
        help=_("delete oauth2 authorization code"),
        description=_("delete oauth2 authorization code"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("comma separated authorization code ids"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oids = self.app.pargs.id
        for oid in oids.split(","):
            uri = f"{self.baseuri}/authorization_codes/{oid}"
            self.cmp_delete(uri, entity=f"user session {oid}")


class ClientController(Oauth2ControllerChild):
    class Meta:
        label = "oauth2_clients"
        description = _("oauth2 client")
        help = _("oauth2 client")

        headers = ["id", "uuid", "name", "response_type", "grant_type", "scopes"]
        fields = ["id", "uuid", "name", "response_type", "grant_type", "scopes"]

    @ex(
        help=_("add oauth2 client"),
        description=_("add oauth2 client"),
        arguments=ARGS(
            [
                (["name"], {"help": _("client name"), "action": "store", "type": str}),
                (
                    ["grant_type"],
                    {
                        "help": _(
                            "valid grant_type: authorization_code, implicit, password, client_credentials, "
                            "urn:ietf:params:oauth:grant-type:jwt-bearer"
                        ),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-redirect_uri"],
                    {
                        "help": _("redirect_uri"),
                        "action": "store",
                        "type": str,
                        "default": "http://localhost",
                    },
                ),
                (
                    ["-scopes"],
                    {
                        "help": _("comma separated list of scopes"),
                        "action": "store",
                        "type": str,
                        "default": "beehive",
                    },
                ),
                (
                    ["-expirydate"],
                    {
                        "help": _("client expire date. Syntax yyyy-mm-dd"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add(self):
        name = self.app.pargs.name
        grant_type = self.app.pargs.grant_type
        redirect_uri = self.app.pargs.redirect_uri
        scopes = self.app.pargs.scopes
        expiry_date = self.app.pargs.expirydate
        if expiry_date is None:
            expiry_date = "2031-12-31"
        data = {
            "client": {
                "name": name,
                "grant_type": grant_type,
                "redirect_uri": redirect_uri,
                "desc": f"Client {name}",
                "response_type": "code",
                "scopes": scopes,
                "expirydate": expiry_date,
            }
        }
        uri = f"{self.baseuri}/clients"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add client {res['uuid']}"})

    @ex(
        help=_("get oauth2 clients"),
        description=_("get oauth2 clients"),
        example="beehive auth oauth2-clients get -id uuid",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("client uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": _("role uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group"],
                    {
                        "help": _("group uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("name filter"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("client desc"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": _("email address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-expiry-date "],
                    {
                        "help": _("expiry date. Syntax YYYY-MM-DD"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-perms"],
                    {
                        "help": _("comma separated list of permission id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/clients/{oid}"
            res = self.cmp_get(uri)

            # if self.is_output_text():
            #     self.app.render(res, key="client", details=True)
            # else:
            self.app.render(res, key="client", details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/clients"
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="clients", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("delete oauth2 client"),
        description=_("delete oauth2 client"),
        arguments=ARGS(
            [
                (["id"], {"help": _("client uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/clients/{oid}"
        self.cmp_delete(uri, entity=f"client {oid}")


class ScopeController(Oauth2ControllerChild):
    class Meta:
        label = "oauth2_scopes"
        description = _("oauth2 scope")
        help = _("oauth2 scope")

        headers = ["id", "uuid", "name", "active", "date.creation"]
        fields = ["id", "uuid", "name", "active", "date.creation"]

    @ex(
        help=_("add oauth2 scope"),
        description=_("add oauth2 scope"),
        arguments=ARGS([(["name"], {"help": _("scope name"), "action": "store", "type": str})]),
    )
    def add(self):
        name = self.app.pargs.name
        data = {"scope": {"name": name, "desc": f"Scope {name}"}}
        uri = f"{self.baseuri}/scopes"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add scope {res['uuid']}"})

    @ex(
        help=_("get oauth2 scopes"),
        description=_("get oauth2 scopes"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("scope uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/scopes/{oid}"
            res = self.cmp_get(uri)

            # if self.is_output_text():
            #     self.app.render(res, key="scope", details=True)
            # else:
            self.app.render(res, key="scope", details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/scopes"
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="scopes", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("delete oauth2 scope"),
        description=_("delete oauth2 scope"),
        arguments=ARGS(
            [
                (["id"], {"help": _("scope uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/scopes/{oid}"
        self.cmp_delete(uri, entity=f"scope {oid}")
