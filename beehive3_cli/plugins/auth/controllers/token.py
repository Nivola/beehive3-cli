# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from binascii import a2b_base64
from datetime import datetime, timedelta
from jwt import encode as jwt_encode
from cement import ex
from requests_oauthlib import OAuth2Session
from beehive.common.jwtclient import JWTClient
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.auth.controllers.auth import AuthChildController
from beehive3_cli.translate import _


class AuthTokenController(AuthChildController):
    class Meta:
        stacked_on = "auth"
        stacked_type = "nested"
        label = "tokens"
        description = _("tokens management")
        help = _("tokens management")

        headers = [
            "token",
            "type",
            "provider",
            "user",
            "email",
            "ip",
            "ttl",
            "timestamp",
        ]
        fields = [
            "token",
            "type",
            "provider",
            "user",
            "email",
            "ip",
            "ttl",
            "timestamp",
        ]

    @ex(
        help=_("get tokens"),
        description=_("get tokens"),
        example="beehive auth tokens get",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("token uuid"),
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
            uri = f"{self.baseuri}/tokens/{oid}"
            res = self.cmp_get(uri)
            self.app.render(res, key="token", details=True)
        else:
            data = self.format_paginated_query([])
            uri = f"{self.baseuri}/tokens"
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="tokens", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("return your own authentication token"),
        description=_("return your own authentication token"),
        arguments=ARGS(),
    )
    def get_my_token(self):
        # make a simple request to refresh token if expired
        uri = "/v1.0/nws/accounts"
        self.cmp_get(uri, data={"size": 1})
        token, _ = self.api.get_token()
        res = {"token:": token}
        self.app.render(res, details=True)

    @ex(
        help=_("create keyauth or oauth2 jwt token"),
        description=_("create keyauth or oauth2 jwt token"),
        arguments=ARGS(
            [
                (
                    ["-type"],
                    {
                        "help": _("can be keyauth, oauth2. oauth2 create a token using a jwt client"),
                        "action": "store",
                        "type": str,
                        "default": "keyauth",
                    },
                ),
                (["user"], {"help": _("login user"), "action": "store", "type": str}),
                (["pwd"], {"help": _("login password"), "action": "store", "type": str}),
                (
                    ["-client"],
                    {
                        "help": _("oauth client uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sub"],
                    {
                        "help": _("sub field for oauth2 jwt login"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add(self):
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        client_id = self.app.pargs.client
        auth_type = self.app.pargs.type
        sub = self.app.pargs.sub

        if auth_type == "keyauth":
            data = {"user": user, "password": pwd}
            res = self.cmp_post("/v1.0/nas/keyauth/token", data=data)
            token = res["access_token"]
        elif auth_type == "oauth2":
            # get client
            uri = f"/v1.0/oauth2/clients/{client_id}"
            client = self.cmp_get(uri).get("client")

            client_id = client["uuid"]
            client_email = client["client_email"]
            client_scope = client["scopes"]
            private_key = a2b_base64(client["private_key"])
            client_token_uri = client["token_uri"]

            client = JWTClient(client_id=client_id)
            oauth = OAuth2Session(client=client)

            now = datetime.utcnow()
            claims = {
                "iss": client_email,
                # 'aud': client_token_uri,
                "aud": "nivola",
                "exp": now + timedelta(seconds=60),
                "iat": now,
                "nbf": now,
            }
            if sub is not None:
                claims["sub"] = sub

            encoded = jwt_encode(claims, private_key, algorithm="RS512")
            res = client.prepare_request_body(assertion=encoded, client_id=client_id, scope=client_scope)
            token = oauth.fetch_token(token_url=client_token_uri, body=res, verify=False)

        res = {"msg": f"Get token {token}"}
        self.app.render(res)

    @ex(
        help=_("delete token"),
        description=_("delete token"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("token uuid or all for all"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        if oid == "all":
            uri = f"{self.baseuri}/tokens"
            tokens = self.cmp_get(uri, data="").get("tokens")
            for token in tokens:
                token = token.get("token")
                uri = f"{self.baseuri}/tokens/{token}"
                self.cmp_delete(uri, entity=f"token {token}")
        else:
            uri = f"{self.baseuri}/tokens/{oid}"
            self.cmp_delete(uri, entity=f"token {oid}")
