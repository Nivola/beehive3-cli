# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.business.controllers.authority import AuthorityControllerChild
from beehive3_cli.translate import _


class DivisionController(AuthorityControllerChild):
    class Meta:
        label = "divs"
        description = _("division management")
        help = _("division management")

        headers = [
            "uuid",
            "name",
            "organization",
            "accounts",
            "contact",
            "email",
            "postaladdress",
            "status",
            "date",
        ]
        fields = [
            "uuid",
            "name",
            "organization_name",
            "accounts",
            "contact",
            "email",
            "postaladdress",
            "status",
            "date.creation",
        ]

    @ex(
        help=_("get divisions"),
        description=_(
            "This command is used to retrieve all the configured divisions or a specific division "
            "based on name or id from the Nivola CMP platform. "
            "Divisions in Nivola CMP are logical groupings of environments like Dev, Test, "
            "Staging etc that can be used for authorization and access control purposes."
        ),
        example="beehive bu divs get -id Sanita-Regione -e <env>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("division uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": _("authorization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("division name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-organization-id"],
                    {
                        "help": _("organization uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-contact"],
                    {
                        "help": _("division contact"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": _("division email"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-postaladdress"],
                    {
                        "help": _("division legalemail"),
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
            res = self.get_division(oid)

            if self.is_output_text():
                data = f"division_id={res.get('id')}&size=100"
                uri = f"{self.baseuri}/accounts"
                accounts = self.cmp_get(uri, data=data)
                self.app.render(res, details=True)
                self.c("\naccounts", "underline")
                self.app.render(
                    accounts,
                    key="accounts",
                    headers=[
                        "id",
                        "uuid",
                        "name",
                        "contact",
                        "email",
                        "active",
                        "date.creation",
                        "status",
                    ],
                )
            else:
                self.app.render(res, key="division", details=True)
        else:
            params = [
                "name",
                "objid",
                "organization_id",
                "contact",
                "email",
                "postaladdress",
            ]
            data = self.format_paginated_query(params)
            uri = f"{self.baseuri}/divisions"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="divisions",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    @ex(
        help=_("add division"),
        description=_(
            "This command adds a new division to an organization. "
            "It requires the division name and organization UUID as arguments. "
            "The division name is used to identify the division being added and "
            "the organization UUID specifies which organization this new division will belong to."
        ),
        arguments=ARGS(
            [
                (["name"], {"help": _("division name"), "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": _("division description"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["organization"],
                    {"help": _("organization uuid"), "action": "store", "type": str},
                ),
                (
                    ["-contact"],
                    {
                        "help": _("division contact"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": _("division email"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-postaladdress"],
                    {
                        "help": _("division postaladdress"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-price_list"],
                    {
                        "help": _("division price list id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add(self):
        data = {
            "division": {
                "name": self.app.pargs.name,
                "desc": self.app.pargs.desc,
                "organization_id": self.app.pargs.organization,
                "contact": self.app.pargs.contact,
                "email": self.app.pargs.email,
                "postaladdress": self.app.pargs.postaladdress,
                "price_list_id": self.app.pargs.price_list,
            }
        }
        uri = f"{self.baseuri}/divisions"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"Add division {res}"})

    @ex(
        help=_("update division"),
        description=_(
            "This command updates an existing division in Nivola CMP. "
            "The division name argument is required to identify which division to update."
        ),
        arguments=ARGS(
            [
                (["name"], {"help": _("division name"), "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": _("division description"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["organization"],
                    {
                        "help": _("organization uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-contact"],
                    {
                        "help": _("division contact"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": _("division email"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-postaladdress"],
                    {
                        "help": _("division postaladdress"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-price_list_id"],
                    {
                        "help": _("division price list id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def update(self):
        """todo:"""
        oid = self.app.pargs.id
        params = self.app.kvargs
        data = {"division": params}
        uri = f"{self.baseuri}/divisions/{oid}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"Update resource {oid} with data {params}"})

    @ex(
        help=_("refresh division"),
        description=_(
            "This command refreshes a division by its unique ID. "
            "The ID argument is required to identify which division to refresh. "
            "Refreshing a division updates it with any changes from the server."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("division uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def patch(self):
        oid = self.app.pargs.id
        data = {"division": {}}
        uri = f"{self.baseuri}/divisions/{oid}"
        self.cmp_patch(uri, data=data, timeout=600)
        self.app.render({"msg": f"Refresh division {oid}"})

    @ex(
        help=_("delete division"),
        description=_(
            "This command deletes a division from the Nivola CMP platform by its unique ID. "
            "The ID of the division to delete must be provided as the only required argument."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("division uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/divisions/{oid}"
        self.cmp_delete(uri, entity=f"division {oid}")

class DivisionAuthController(AuthorityControllerChild):
    class Meta:
        label = "divs_auth"
        # aliases = ['auth']
        # stacked_on = 'divisions'
        # stacked_type = 'nested'
        description = _("division authorization")
        help = _("division authorization")

    @ex(
        help=_("get division roles"),
        description=_(
            "This command retrieves the roles associated with a specific division. "
            "The division is identified by its UUID which must be provided using the 'id' argument. "
            "The roles are returned for authorization on the specified division."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("division uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def role_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/divisions/{oid}/roles"
        res = self.cmp_get(uri)
        self.app.render(res, key="roles", headers=["name", "desc", "role"], maxsize=200)

    @ex(
        help=_("get division users"),
        description=_(
            "This command retrieves user details for a specific division. "
            "The division uuid must be provided using the required 'id' argument."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("division uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def user_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/divisions/{oid}/users"
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="users",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            maxsize=200,
        )

    @ex(
        help=_("add division role to a user"),
        description=_(
            "This command adds a division role to a user. "
            "It requires the division UUID, the role to assign within that division, "
            "and the user to assign the role to as required arguments."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("division uuid"), "action": "store", "type": str}),
                (["role"], {"help": _("division role"), "action": "store", "type": str}),
                (
                    ["user"],
                    {"help": _("authorization user"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = f"{self.baseuri}/divisions/{oid}/users"
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help=_("remove division role from a user"),
        description=_(
            "This command removes a division role from a specific user. "
            "It requires the division UUID, the role within that division "
            "(such as 'admin' or 'member'), and the username to remove the role from."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("division uuid"), "action": "store", "type": str}),
                (["role"], {"help": _("division role"), "action": "store", "type": str}),
                (
                    ["user"],
                    {"help": _("authorization user"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = f"{self.baseuri}/divisions/{oid}/users"
        res = self.cmp_delete(uri, data)
        self.app.render({"msg": res})

    @ex(
        help=_("get division groups"),
        description=_(
            "This command retrieves the groups associated with a specific division. "
            "The division is identified by its UUID which must be provided with the 'id' argument. "
            "This allows retrieving all the groups that have access to the specified division "
            "for authorization purposes."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("division uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def group_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/divisions/{oid}/groups"
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="groups",
            headers=["id", "name", "role"],
            fields=["uuid", "name", "role"],
            maxsize=200,
        )

    @ex(
        help=_("add division role to a group"),
        description=_(
            "This command adds an authorization group to a division role. "
            "It requires the division UUID, role and group name as arguments."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("division uuid"), "action": "store", "type": str}),
                (["role"], {"help": _("division role"), "action": "store", "type": str}),
                (
                    ["group"],
                    {"help": _("authorization group"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = f"{self.baseuri}/divisions/{oid}/groups"
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help=_("remove division role from a group"),
        description=_(
            "This command removes a division role from an authorization group. "
            "It requires the division UUID, role and group name as arguments to "
            "identify which specific division role assignment to remove from the group."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("division uuid"), "action": "store", "type": str}),
                (["role"], {"help": _("division role"), "action": "store", "type": str}),
                (
                    ["group"],
                    {"help": _("authorization group"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = f"{self.baseuri}/divisions/{oid}/groups"
        res = self.cmp_delete(uri, data)
        self.app.render({"msg": res})
