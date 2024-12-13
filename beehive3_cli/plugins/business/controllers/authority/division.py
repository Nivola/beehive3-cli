# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from cement import ex
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.business.controllers.authority import AuthorityControllerChild


class DivisionController(AuthorityControllerChild):
    class Meta:
        label = "divs"
        description = "division management"
        help = "division management"

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
        help="get divisions",
        description="This command is used to retrieve all the configured divisions or a specific division based on name or id from the Nivola CMP platform. Divisions in Nivola CMP are logical groupings of environments like Dev, Test, Staging etc that can be used for authorization and access control purposes.",
        example="beehive bu divs get -name Staging;beehive bu divs get -id Sanita-Regione -e <env>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "division uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": "authorization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "division name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-organization-id"],
                    {
                        "help": "organization uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-contact"],
                    {
                        "help": "division contact",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": "division email",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-postaladdress"],
                    {
                        "help": "division legalemail",
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
                data = "division_id=%s&size=100" % res.get("id")
                uri = "%s/accounts" % self.baseuri
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
            uri = "%s/divisions" % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="divisions",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    @ex(
        help="add division",
        description="This command adds a new division to an organization. It requires the division name and organization UUID as arguments. The division name is used to identify the division being added and the organization UUID specifies which organization this new division will belong to.",
        arguments=ARGS(
            [
                (["name"], {"help": "division name", "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": "division description",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["organization"],
                    {"help": "organization uuid", "action": "store", "type": str},
                ),
                (
                    ["-contact"],
                    {
                        "help": "division contact",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": "division email",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-postaladdress"],
                    {
                        "help": "division postaladdress",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-price_list"],
                    {
                        "help": "division price list id",
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
        uri = "%s/divisions" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "Add division %s" % res})

    @ex(
        help="update division",
        description="This command updates an existing division in Nivola CMP. The division name argument is required to identify which division to update.",
        arguments=ARGS(
            [
                (["name"], {"help": "division name", "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": "division description",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["organization"],
                    {
                        "help": "organization uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-contact"],
                    {
                        "help": "division contact",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": "division email",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-postaladdress"],
                    {
                        "help": "division postaladdress",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-price_list_id"],
                    {
                        "help": "division price list id",
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
        uri = "%s/divisions/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "Update resource %s with data %s" % (oid, params)})

    @ex(
        help="refresh division",
        description="This command refreshes a division by its unique ID. The ID argument is required to identify which division to refresh. Refreshing a division updates it with any changes from the server.",
        arguments=ARGS(
            [
                (["id"], {"help": "division uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def patch(self):
        oid = self.app.pargs.id
        data = {"division": {}}
        uri = "%s/divisions/%s" % (self.baseuri, oid)
        self.cmp_patch(uri, data=data, timeout=600)
        self.app.render({"msg": "Refresh division %s" % oid})

    @ex(
        help="delete division",
        description="This command deletes a division from the Nivola CMP platform by its unique ID. The ID of the division to delete must be provided as the only required argument.",
        arguments=ARGS(
            [
                (["id"], {"help": "division uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = "%s/divisions/%s" % (self.baseuri, oid)
        self.cmp_delete(uri, entity="division %s" % oid)

    # @ex(
    #     help='get division active services info',
    #     description='get division active services info',
    #     arguments=ARGS([
    #         (['id'], {'help': 'division uuid', 'action': 'store', 'type': str}),
    #     ])
    # )
    # def active_services(self):
    #     oid = self.app.pargs.id
    #     uri = '%s/divisions/%s/activeservices' % (self.baseuri, oid)
    #     res = self.cmp_get(uri)
    #     self.app.render(res, key='services', details=True)
    #
    # @ex(
    #     help='get division wallet',
    #     description='get division wallet',
    #     arguments=ARGS([
    #         (['id'], {'help': 'division uuid', 'action': 'store', 'type': str}),
    #         (['-year'], {'help': 'wallet year', 'action': 'store', 'type': str, 'default': None}),
    #     ])
    # )
    # def wallet(self):
    #     oid = self.app.pargs.id
    #     year = self.app.pargs.year
    #     data = {'division_id': oid}
    #     if year is not None:
    #         data['year'] = year
    #     data = urlencode(data)
    #
    #     uri = '%s/wallets' % self.baseuri
    #     wallets = self.cmp_get(uri, data=data).get('wallets')
    #     print('Wallets:')
    #     self.app.render(wallets, headers=['year', 'id', 'uuid', 'name', 'capital_total', 'capital_used', 'active',
    #                                       'status', 'date.creation'])
    #
    #     # get agreements
    #     uri = '%s/divisions/%s/agreements' % (self.baseuri, oid)
    #     res = self.cmp_get(uri, data=data).get('agreements', [])
    #     print('Agreements:')
    #     self.app.render(res, headers=['wallet_id', 'id', 'uuid', 'name', 'amount', 'agreement_date_start', 'active',
    #                                   'date.creation'])


class DivisionAuthController(AuthorityControllerChild):
    class Meta:
        label = "divs_auth"
        # aliases = ['auth']
        # stacked_on = 'divisions'
        # stacked_type = 'nested'
        description = "division authorization"
        help = "division authorization"

    @ex(
        help="get division roles",
        description="This command retrieves the roles associated with a specific division. The division is identified by its UUID which must be provided using the 'id' argument. The roles are returned for authorization on the specified division.",
        arguments=ARGS(
            [
                (["id"], {"help": "division uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def role_get(self):
        oid = self.app.pargs.id
        uri = "%s/divisions/%s/roles" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key="roles", headers=["name", "desc", "role"], maxsize=200)

    @ex(
        help="get division users",
        description="This command retrieves user details for a specific division. The division uuid must be provided using the required 'id' argument.",
        arguments=ARGS(
            [
                (["id"], {"help": "division uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def user_get(self):
        oid = self.app.pargs.id
        uri = "%s/divisions/%s/users" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="users",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            maxsize=200,
        )

    @ex(
        help="add division role to a user",
        description="This command adds a division role to a user. It requires the division UUID, the role to assign within that division, and the user to assign the role to as required arguments.",
        arguments=ARGS(
            [
                (["id"], {"help": "division uuid", "action": "store", "type": str}),
                (["role"], {"help": "division role", "action": "store", "type": str}),
                (
                    ["user"],
                    {"help": "authorization user", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = "%s/divisions/%s/users" % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="remove division role from a user",
        description="This command removes a division role from a specific user. It requires the division UUID, the role within that division (such as 'admin' or 'member'), and the username to remove the role from.",
        arguments=ARGS(
            [
                (["id"], {"help": "division uuid", "action": "store", "type": str}),
                (["role"], {"help": "division role", "action": "store", "type": str}),
                (
                    ["user"],
                    {"help": "authorization user", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = "%s/divisions/%s/users" % (self.baseuri, oid)
        res = self.cmp_delete(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="get division groups",
        description="This command retrieves the groups associated with a specific division. The division is identified by its UUID which must be provided with the 'id' argument. This allows retrieving all the groups that have access to the specified division for authorization purposes.",
        arguments=ARGS(
            [
                (["id"], {"help": "division uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def group_get(self):
        oid = self.app.pargs.id
        uri = "%s/divisions/%s/groups" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="groups",
            headers=["id", "name", "role"],
            fields=["uuid", "name", "role"],
            maxsize=200,
        )

    @ex(
        help="add division role to a group",
        description="This command adds an authorization group to a division role. It requires the division UUID, role and group name as arguments.",
        arguments=ARGS(
            [
                (["id"], {"help": "division uuid", "action": "store", "type": str}),
                (["role"], {"help": "division role", "action": "store", "type": str}),
                (
                    ["group"],
                    {"help": "authorization group", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = "%s/divisions/%s/groups" % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="remove division role from a group",
        description="This command removes a division role from an authorization group. It requires the division UUID, role and group name as arguments to identify which specific division role assignment to remove from the group.",
        arguments=ARGS(
            [
                (["id"], {"help": "division uuid", "action": "store", "type": str}),
                (["role"], {"help": "division role", "action": "store", "type": str}),
                (
                    ["group"],
                    {"help": "authorization group", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = "%s/divisions/%s/groups" % (self.baseuri, oid)
        res = self.cmp_delete(uri, data)
        self.app.render({"msg": res})
