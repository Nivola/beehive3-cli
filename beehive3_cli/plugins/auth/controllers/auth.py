# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement.ext.ext_argparse import ex

from beehive3_cli.core.controller import CliController, BaseController, ARGS
from beehive3_cli.translate import _

class AuthController(CliController):
    class Meta: # type: ignore
        label = "auth"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("authorization management")
        help = _("authorization management")

    def _default(self):
        self._parser.print_help()


class AuthChildController(BaseController):

    class Meta: # type: ignore
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
        super().pre_command_run()

        self.configure_cmp_api_client()


class ProviderController(AuthChildController):
    class Meta: # type: ignore
        label = "providers"
        description = _("authentication provider management")
        help = _("authentication provider management")

    @ex(
        help=_("get authentication providers"),
        description=_("get authentication providers"),
        arguments=ARGS([]),
    )
    def get(self):
        uri = f"{self.baseuri}/providers"
        res = self.cmp_get(uri)
        self.app.render(res, key="providers", headers=["type", "name"])
