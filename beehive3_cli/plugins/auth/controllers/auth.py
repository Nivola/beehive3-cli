# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from pygments import format
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.token import Token
from cement.ext.ext_argparse import ex
from beehive3_cli.core.controller import CliController, BaseController, ARGS
from beehive3_cli.core.util import TreeStyle


class AuthController(CliController):
    class Meta:
        label = "auth"
        stacked_on = "base"
        stacked_type = "nested"
        description = "authorization management"
        help = "authorization management"

    def _default(self):
        self._parser.print_help()


class AuthChildController(BaseController):
    class Meta:
        stacked_on = "auth"
        stacked_type = "nested"

        cmp = {"baseuri": "/v1.0/nas", "subsystem": "auth"}

        user_headers = [
            "uuid",
            "name",
            "email",
            "desc",
            "active",
            "creation",
            "modified",
            "last_login",
        ]
        user_fields = [
            "uuid",
            "name",
            "email",
            "desc",
            "active",
            "date.creation",
            "date.modified",
            "date.last_login",
        ]

        role_headers = [
            "uuid",
            "name",
            "alias",
            "active",
            "creation",
            "modified",
            "expiry",
        ]
        role_fields = [
            "uuid",
            "name",
            "alias",
            "active",
            "date.creation",
            "date.modified",
            "date.expiry",
        ]

        group_headers = [
            "uuid",
            "name",
            "desc",
            "active",
            "creation",
            "modified",
            "expiry",
        ]
        group_fields = [
            "uuid",
            "name",
            "desc",
            "active",
            "date.creation",
            "date.modified",
            "date.expiry",
        ]

        perm_headers = [
            "permission-id",
            "object-id",
            "authorization-id",
            "subsystem",
            "type",
            "action-id",
            "action",
        ]
        perm_fields = ["id", "oid", "objid", "subsystem", "type", "aid", "action"]

        obj_headers = ["object-id", "objid", "subsystem", "type", "desc", "creation"]
        obj_fields = ["id", "objid", "subsystem", "type", "desc", "date.creation"]

        type_headers = ["type-id", "subsystem", "type"]
        type_fields = ["id", "subsystem", "type"]

        act_headers = ["action-id", "value"]
        act_fields = ["id", "value"]

    def pre_command_run(self):
        super(AuthChildController, self).pre_command_run()

        self.configure_cmp_api_client()

    def __print_tree(self, resource, space="   "):
        for child in resource.get("children", []):
            relation = child.get("relation")
            if relation is None:

                def create_data():
                    yield (Token.Text.Whitespace, space)
                    yield (Token.Operator, "=>")
                    yield (Token.Name, " [%s] " % child.get("type"))
                    yield (Token.Literal.String, child.get("name"))
                    yield (Token.Text.Whitespace, " - ")
                    yield (
                        Token.Literal.String,
                        "%s {%s}" % (child.get("id"), child.get("ext_id")),
                    )
                    yield (Token.Literal.String, " [%s]" % child.get("state"))
                    yield (Token.Literal.String, " (%s)" % child.get("reuse"))

                data = format(create_data(), Terminal256Formatter(style=TreeStyle))
            else:

                def create_data():
                    yield (Token.Text.Whitespace, space)
                    yield (Token.Operator, "--%s-->" % relation)
                    yield (Token.Operator, " (%s) " % child.get("container_name"))
                    yield (Token.Name, "[%s] " % child.get("type"))
                    yield (Token.Literal.String, child.get("name"))
                    yield (Token.Text.Whitespace, " - ")
                    yield (
                        Token.Literal.String,
                        "%s {%s}" % (child.get("id"), child.get("ext_id")),
                    )
                    yield (Token.Literal.String, " [%s]" % child.get("state"))
                    yield (Token.Literal.String, " (%s)" % child.get("reuse"))

                data = format(create_data(), Terminal256Formatter(style=TreeStyle))
                print(data)
            self.__print_tree(child, space=space + "   ")


class ProviderController(AuthChildController):
    class Meta:
        label = "providers"
        description = "authentication provider management"
        help = "authentication provider management"

    @ex(
        help="get authentication providers",
        description="get authentication providers",
        arguments=ARGS([]),
    )
    def get(self):
        uri = "%s/providers" % self.baseuri
        res = self.cmp_get(uri)
        self.app.render(res, key="providers", headers=["type", "name"])
