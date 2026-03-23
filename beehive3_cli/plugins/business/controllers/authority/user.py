# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex
from beehive3_cli.core.controller import PARGS
from beehive3_cli.plugins.business.controllers.authority import AuthorityControllerChild
from beehive3_cli.translate import _


class UserController(AuthorityControllerChild):
    class Meta:
        label = "users_auth"
        description = _("user authorization")
        help = _("user authorization")

        headers = [
            "role",
            "organization id",
            "organization name",
            "division id",
            "division name",
            "account id",
            "account name",
            "account desc",
        ]
        fields = [
            "user_role",
            "org_id",
            "org_name",
            "div_id",
            "div_name",
            "account_id",
            "account_name",
            "account_desc",
        ]
 

    @ex(
        help=_("get user roles"),
        description=_(
            "This command retrieves the roles associated with a specific user."
        ),
        example="beehive bu users-auth roles-get <user name> -e <env>",
        arguments=PARGS(
            [
                (
                    ["user_name"],
                    {
                        "help": _("user_name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def roles_get(self):
        user_name = getattr(self.app.pargs, "user_name", None)
        data = {
            "user_name": user_name
        }
        uri = f"{self.baseuri}/services/objects/filter/byusername"
        res = self.cmp_get(uri, data=data)
        self.app.render(
            res,
            key="services",
            headers=self._meta.headers,
            fields=self._meta.fields,
        )
