# SPDX-License-Identifier: EUPL-1.2
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from cement import ex
from beecell.types.type_string import str2bool
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.business.controllers.authority import AuthorityControllerChild


class AccountController(AuthorityControllerChild):
    class Meta:
        label = "accounts"
        description = "account management"
        help = "account management"

        headers = [
            "uuid",
            "name",
            "acronym",
            "division",
            "contact",
            "email_support",
            "managed",
            "core services",
            "base services",
            "status",
            "date",
        ]
        fields = [
            "uuid",
            "name",
            "acronym",
            "division_name",
            "contact",
            "email_support",
            "managed",
            "services.core",
            "services.base",
            "status",
            "date.creation",
        ]

    @ex(
        help="get accounts",
        description="get accounts",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "account id",
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
                        "help": "account name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-division-id"],
                    {
                        "help": "division uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-contact"],
                    {
                        "help": "account contact",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": "account email",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email-support"],
                    {
                        "help": "account email support",
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
            res = self.get_account(oid)
            oid = res["uuid"]

            if self.is_output_text():
                self.app.render(res, details=True)

                self.c("\ncapabilities", "underline")
                uri = "%s/accounts/%s/capabilities" % (self.baseuri, oid)
                capabilities = self.cmp_get(uri).get("capabilities")
                headers = [
                    "name",
                    "status",
                    "services.required",
                    "services.error",
                    "services.created",
                    "definitions.required",
                    "definitions.created",
                ]
                fields = [
                    "name",
                    "status",
                    "report.services.required",
                    "report.services.error",
                    "report.services.created",
                    "report.definitions.required",
                    "report.definitions.created",
                ]
                self.app.render(capabilities, headers=headers, fields=fields)

                self.c("\ncore services", "underline")
                data = {"account_id": oid, "size": -1, "flag_container": True}
                services = self.cmp_get("/v2.0/nws/serviceinsts", data=data).get("serviceinsts")
                fields = [
                    "uuid",
                    "name",
                    "plugintype",
                    "definition_name",
                    "status",
                    "resource_uuid",
                    "is_container",
                    "parent.name",
                    "date.creation",
                ]
                headers = [
                    "id",
                    "name",
                    "type",
                    "definition",
                    "status",
                    "resource",
                    "is_container",
                    "parent",
                    "creation",
                ]
                self.app.render(services, headers=headers, fields=fields)

                self.c("\nservices", "underline")
                data = {"account_id": oid, "size": -1, "flag_container": False}
                services = self.cmp_get("/v2.0/nws/serviceinsts", data=data).get("serviceinsts")
                fields = [
                    "uuid",
                    "name",
                    "plugintype",
                    "definition_name",
                    "status",
                    "resource_uuid",
                    "is_container",
                    "parent.name",
                    "date.creation",
                ]
                headers = [
                    "id",
                    "name",
                    "type",
                    "definition",
                    "status",
                    "resource",
                    "is_container",
                    "parent",
                    "creation",
                ]
                self.app.render(services, headers=headers, fields=fields)
            else:
                self.app.render(res, key="account", details=True)
        else:
            params = [
                "name",
                "objid",
                "division_id",
                "contact",
                "email",
                "email_support",
            ]
            data = self.format_paginated_query(params)
            uri = "%s/accounts" % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="accounts",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    @ex(
        help="get account definitions",
        description="get account definition ",
        arguments=PARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["-plugintype"],
                    {
                        "help": "filter by definition plugin",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-category"],
                    {
                        "help": "filet by category ",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-container"],
                    {
                        "help": "get only containers definitions",
                        "action": "store",
                        "type": bool,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def definition_get(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        data = {
            "size": self.app.pargs.size,
            "page": self.app.pargs.page,
            "field": self.app.pargs.field,
            "order": self.app.pargs.order,
        }
        if self.app.pargs.plugintype is not None:
            data["plugintype"] = self.app.pargs.plugintype
        if self.app.pargs.category is not None:
            data["category"] = self.app.pargs.category
        if self.app.pargs.container:
            data["only_container"] = self.app.pargs.container

        uri = "%s/accounts/%s/definitions" % ("/v2.0/nws", oid)
        res = self.cmp_get(uri, data=data)

        if self.is_output_text():
            self.c("\ndefinitions", "underline")
            headers = ["name", "category", "plugintype", "is a", "is_default"]
            fields = ["name", "category", "plugintype", "is_a", "is_default"]
            self.app.render(res, key="definitions", headers=headers, fields=fields, maxsize=80)
        else:
            self.app.render(res, key="definitions", details=True)

    @ex(
        help="add account definitions",
        description="add account definitions",
        arguments=PARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["definitions"],
                    {
                        "help": "comma separated list of definition ids",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def definition_add(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        definitions = self.app.pargs.definitions
        data = {"definitions": definitions.split(",")}
        uri = "%s/accounts/%s/definitions" % ("/v2.0/nws", oid)
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "add definitions %s to account %s" % (res.get("definitions", []), oid)})

    @ex(
        help="add account",
        description="add account",
        arguments=ARGS(
            [
                (["name"], {"help": "account name", "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": "account description",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["division"],
                    {"help": "division uuid", "action": "store", "type": str},
                ),
                # (['-price_list'], {'help': 'account price list id', 'action': 'store', 'type': int, 'default': None}),
                (
                    ["-contact"],
                    {
                        "help": "account contact",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": "account email",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email-support"],
                    {
                        "help": "account email support",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email-support-link"],
                    {
                        "help": "account email support link",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-note"],
                    {
                        "help": "account note",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-acronym"],
                    {
                        "help": "account acronym",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-managed"],
                    {
                        "help": "if true set account as managed",
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def add(self):
        data = {
            "account": {
                "name": self.app.pargs.name,
                "desc": self.app.pargs.desc,
                "division_id": self.app.pargs.division,
                "contact": self.app.pargs.contact,
                # 'price_list_id': self.app.pargs.price_list_id,
                "email": self.app.pargs.email,
                "note": self.app.pargs.note,
                "email_support": self.app.pargs.email_support,
                "email_support_link": self.app.pargs.email_support_link,
                "managed": self.app.pargs.managed,
                "acronym": self.app.pargs.acronym,
            }
        }
        uri = "%s/accounts" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "Add account %s" % res})

    @ex(
        help="update account",
        description="update account",
        arguments=ARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
                # (["-name"], {"help": "account name", "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": "account description",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                # (
                #     ["-division"],
                #     {"help": "division uuid", "action": "store", "type": str},
                # ),
                (
                    ["-price_list"],
                    {
                        "help": "account price list id",
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-contact"],
                    {
                        "help": "account contact",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": "account email",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email-support"],
                    {
                        "help": "account email support",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email-support-link"],
                    {
                        "help": "account email support link",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-acronym"],
                    {
                        "help": "account acronym",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-note"],
                    {
                        "help": "account note",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")

        # name = self.app.pargs.name
        desc = self.app.pargs.desc
        # division = self.app.pargs.division
        price_list_id = self.app.pargs.price_list
        contact = self.app.pargs.contact
        email = self.app.pargs.email
        email_support = self.app.pargs.email_support
        email_support_link = self.app.pargs.email_support_link
        acronym = self.app.pargs.acronym
        note = self.app.pargs.note

        account = {}

        # if name is not None:
        #     account.update({
        #         "name": name
        #     })

        if desc is not None:
            account.update({"desc": desc})

        # if division is not None:
        #     account.update({
        #         "division": division
        #     })

        if price_list_id is not None:
            account.update(
                {
                    "price_list_id": price_list_id,
                }
            )

        if contact is not None:
            account.update(
                {
                    "contact": contact,
                }
            )

        if email is not None:
            account.update(
                {
                    "email": email,
                }
            )

        if email_support is not None:
            account.update(
                {
                    "email_support": email_support,
                }
            )

        if email_support_link is not None:
            account.update(
                {
                    "email_support_link": email_support_link,
                }
            )

        if acronym is not None:
            account.update(
                {
                    "acronym": acronym,
                }
            )

        if note is not None:
            account.update(
                {
                    "note": note,
                }
            )

        data = {"account": account}
        # print("data: %s" % data)

        uri = "%s/accounts/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "Update resource %s with data %s" % (oid, account)})

    @ex(
        help="refresh account",
        description="refresh account",
        arguments=ARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
            ]
        ),
    )
    def patch(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        data = {"account": {}}
        uri = "%s/accounts/%s" % (self.baseuri, oid)
        self.cmp_patch(uri, data=data, timeout=600)
        self.app.render({"msg": "Refresh account %s" % oid})

    @ex(
        help="delete account",
        description="delete account",
        arguments=ARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["-delete_services"],
                    {
                        "help": "if true delete all child services",
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        delete_services = str2bool(self.app.pargs.delete_services)
        oid = self.get_account(oid).get("uuid")
        uri = "/v2.0/nws/accounts/%s" % oid
        data = {"delete_services": delete_services}
        self.cmp_delete(uri, entity="account %s" % oid, data=data)

    @ex(
        help="get account active services info",
        description="get account active services info",
        arguments=ARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
            ]
        ),
    )
    def service_active_get(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        uri = "%s/accounts/%s/activeservices" % (self.baseuri, oid)
        res = self.cmp_get(uri).get("services", {}).get("service_container", [])
        for item in res:
            metrics = item.pop("tot_metrics", [])
            self.c("\nservice %s" % item["plugin_type"], "underline")
            self.app.render(item, details=True)
            self.app.render(metrics, headers=["metric", "unit", "value", "quota"])

    @ex(
        help="delete account services",
        description="delete account services",
        arguments=ARGS([(["id"], {"help": "account id", "action": "store", "type": str})]),
    )
    def service_del(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")

        # delete all child services
        uri = "/v2.0/nws/serviceinsts"
        res = self.cmp_get(uri, data={"account_id": oid, "size": -1}).get("serviceinsts", [])
        for item in res:
            # delete service
            uri = "/v2.0/nws/serviceinsts/%s" % item["uuid"]
            entity = "service %s" % item["name"]
            res = self.cmp_delete(uri, data={}, timeout=600, entity=entity, output=False)
            state = self.wait_for_service(item["uuid"], delta=2)
            if state == "DELETED":
                print("%s deleted" % entity)

    # @ex(
    #     help='get account consumes',
    #     description='get account consumes',
    #     arguments=PARGS([
    #         (['id'], {'help': 'account id', 'action': 'store', 'type': str})
    #     ])
    # )
    # def consume_get(self):
    #     oid = self.app.pargs.id
    #     oid = self.get_account(oid).get('uuid')
    #     uri = '%s/accounts/%s/costs' % (self.baseuri, oid)
    #     params = []
    #     data = self.format_paginated_query(params)
    #     res = self.cmp_get(uri, data=data)
    #     self.app.render(res, key='reports', headers=['id', 'period', 'plugin_name', 'metric_type_id', 'value',
    #                                                  'cost', 'is_reported'], maxsize=80)

    @ex(
        help="get account user roles",
        description="get account user roles",
        arguments=ARGS([(["id"], {"help": "account id", "action": "store", "type": str})]),
    )
    def user_role_get(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        uri = "%s/accounts/%s/userroles" % (self.baseuri, oid)
        params = []
        data = self.format_paginated_query(params)
        res = self.cmp_get(uri, data=data)
        self.app.render(res, key="usernames", headers=["id", "name", "desc", "roles"], maxsize=200)

    #############################
    @ex(
        help="Aminister account",
        description="Configure session permission in order to manage an account",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "the account id to manage",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def manage(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.get_account(oid)
            uuid = res["uuid"]
            result = self.cmp_get(f"/v1.0/nws/accounts/{uuid}/manage", data={})
            if self.is_output_text():
                print(result.get("msg"))

    @ex(
        help="View account",
        description="Configure session permission in order to view an account",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "the account id to manage",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def view(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.get_account(oid)
            uuid = res["uuid"]
            result = self.cmp_get(f"/v1.0/nws/accounts/{uuid}/view", data={})
            if self.is_output_text():
                print(result.get("msg"))

    @ex(
        help="Operate on account",
        description="Configure session permission in order to operato on account",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "the account id to manage",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def operate(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.get_account(oid)
            uuid = res["uuid"]
            result = self.cmp_get(f"/v1.0/nws/accounts/{uuid}/operate", data={})
            if self.is_output_text():
                print(result.get("msg"))


class AccountAuthController(AuthorityControllerChild):
    class Meta:
        label = "accounts_auth"
        description = "account authorization"
        help = "account authorization"

    @ex(
        help="get account roles",
        description="get account roles",
        arguments=ARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
            ]
        ),
    )
    def role_get(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        uri = "%s/accounts/%s/roles" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key="roles", headers=["name", "desc"], maxsize=200)

    @ex(
        help="get account users",
        description="get account users",
        arguments=ARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
            ]
        ),
    )
    def user_get(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        uri = "%s/accounts/%s/users" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="users",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            maxsize=200,
        )

    @ex(
        help="add account role to a user",
        description="add account role to a user",
        arguments=ARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
                (["role"], {"help": "account role", "action": "store", "type": str}),
                (
                    ["user"],
                    {"help": "authorization user", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_add(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = "%s/accounts/%s/users" % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="remove account role from a user",
        description="remove account role from a user",
        arguments=ARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
                (["role"], {"help": "account role", "action": "store", "type": str}),
                (
                    ["user"],
                    {"help": "authorization user", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_del(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = "%s/accounts/%s/users" % (self.baseuri, oid)
        res = self.cmp_delete(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="get account groups",
        description="get account groups",
        arguments=ARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
            ]
        ),
    )
    def group_get(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        uri = "%s/accounts/%s/groups" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="groups",
            headers=["id", "name", "role"],
            fields=["uuid", "name", "role"],
            maxsize=200,
        )

    @ex(
        help="add account role to a group",
        description="add account role to a group",
        arguments=ARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
                (["role"], {"help": "account role", "action": "store", "type": str}),
                (
                    ["group"],
                    {"help": "authorization group", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_add(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = "%s/accounts/%s/groups" % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="remove account role from a group",
        description="remove account role from a group",
        arguments=ARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
                (["role"], {"help": "account role", "action": "store", "type": str}),
                (
                    ["group"],
                    {"help": "authorization group", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_del(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = "%s/accounts/%s/groups" % (self.baseuri, oid)
        res = self.cmp_delete(uri, data)
        self.app.render({"msg": res})


class AccountCapabilityController(AuthorityControllerChild):
    class Meta:
        label = "accounts_capabilities"
        description = "accounts capabilities"
        help = "accounts capabilities"

    @ex(
        help="get account capabilities",
        description="get account capabilities",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-capability"],
                    {
                        "help": "capability name",
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
        oid = self.get_account(oid).get("uuid")
        data = self.format_paginated_query([])
        uri = "%s/accounts/%s/capabilities" % (self.baseuri, oid)
        res = self.cmp_get(uri, data=data)
        if self.is_output_text():
            for item in res.get("capabilities"):
                self.c("\n%s" % item.pop("name"), "underline")
                services = item.pop("services")
                self.app.render(item, details=True)
                print()
                headers = ["type", "name", "status", "require"]
                fields = ["type", "name", "status", "require.name"]
                self.app.render(services, headers=headers, fields=fields, maxsize=200)
        else:
            self.app.render(res, details=True)

        # name = getattr(self.app.pargs, 'capability', None)
        #
        # if name is not None:
        #     data = urlencode({'name': name})
        #     uri = '%s/accounts/%s/capabilities' % (self.baseuri, oid)
        #     res = self.cmp_get(uri, data=data)
        #
        #     if self.is_output_text():
        #         res = res.get('capabilities')
        #         if len(res) == 0:
        #             raise Exception('No capability find with name %s' % name)
        #         services = res[0].pop('services')
        #         self.app.render(res[0], details=True)
        #         print('\nservices:')
        #         self.app.render(services, headers=['type', 'name', 'status', 'require.name'], maxsize=200)
        #     else:
        #         self.app.render(res, details=True)
        # else:
        #     data = self.format_paginated_query([])
        #     uri = '%s/accounts/%s/capabilities' % (self.baseuri, oid)
        #     res = self.cmp_get(uri, data=data)
        #     headers = ['status', 'name', 'services.required', 'services.created', 'services.error']
        #     fields = ['status', 'name', 'report.required', 'report.created', 'report.error']
        #     self.app.render(res, key='capabilities', headers=headers, fields=fields, maxsize=40)

    @ex(
        help="add or update account capabilities",
        description="add or update account capabilities",
        arguments=PARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["capabilities"],
                    {
                        "help": "comma separated list of capability name",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def add(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        capabilities = self.app.pargs.capabilities
        data = {"capabilities": capabilities.split(",")}
        uri = "%s/accounts/%s/capabilities" % (self.baseuri, oid)
        res = self.cmp_post(uri, data=data)


class AccountTagController(AuthorityControllerChild):
    class Meta:
        label = "accounts_tags"
        description = "manage tags for account"
        help = "manage tags for account"

    @ex(
        help="get accounts",
        description="get accounts",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "account id",
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
        oid = self.get_account(oid).get("uuid")
        params = []
        data = self.format_paginated_query(params)
        uri = "%s/accounts/%s/tags" % (self.baseuri, oid)
        res = self.cmp_get(uri, data=data)
        self.app.render(
            res,
            key="tags",
            headers=["uuid", "name", "desc", "active", "creation"],
            fields=["uuid", "name", "desc", "active", "date.creation"],
        )
