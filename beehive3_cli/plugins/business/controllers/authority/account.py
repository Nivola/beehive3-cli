# SPDX-License-Identifier: EUPL-1.2
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

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
        description="This command is used to retrieve accounts information from the Nivola CMP platform. It allows fetching accounts without any filtering criteria by not specifying optional arguments like size or environment. The accounts returned will not be limited or filtered in any way. This command is useful to get a complete list of all accounts to check or work with.",
        example="beehive bu accounts get -size 0 > head 10;beehive bu accounts get DOIT -e <env>",
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
                (
                    ["-active"],
                    {
                        "help": "deleted account",
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
        active = getattr(self.app.pargs, "active", None)
        from beecell.types.type_string import str2bool

        b_active = str2bool(active)

        if oid is not None:
            res = self.get_account(oid, b_active)
            oid = res["uuid"]

            if self.is_output_text():
                self.app.render(res, details=True)

                self.c("\ncapabilities", "underline")
                uri = "%s/accounts/%s/capabilities" % (self.baseuri, oid)
                capabilities = self.cmp_get(uri).get("capabilities")
                headers = [
                    "name",
                    "status",
                    "services required",
                    "error",
                    "created",
                    "definitions required",
                    "created",
                    "application date",
                ]
                fields = [
                    "name",
                    "status",
                    "report.services.required",
                    "report.services.error",
                    "report.services.created",
                    "report.definitions.required",
                    "report.definitions.created",
                    "application_date",
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

            if b_active == False:
                data += "&filter_expired=True&active=False"

            uri = "%s/accounts" % self.baseuri
            res = self.cmp_get(uri, data=data)

            from cement import App

            app: App = self.app
            app.render(
                res,
                key="accounts",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    @ex(
        help="get account triplet",
        description="This command get account triplet",
        example="beehive bu accounts triplet prodis",
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
    def triplet(self):
        oid = getattr(self.app.pargs, "id", None)
        res_account = self.get_account(oid, True)

        # get account
        account_name = res_account["name"]
        division_id = res_account["division_id"]

        # get parent division
        res_division = self.get_division(division_id)
        div_name = res_division["name"]
        organization_id = res_division["organization_id"]

        # get parent organization
        res_org = self.get_organization(organization_id)
        org_name = res_org["name"]

        triplet = "%s.%s.%s" % (org_name, div_name, account_name)
        print("triplet: %s" % triplet)

    @ex(
        help="check account exists",
        description="This command is used to check if account exists.",
        example="beehive bu accounts check aaa -e <env>",
        arguments=PARGS(
            [
                (
                    ["triplet"],
                    {
                        "help": "account triplet name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def check(self):
        triplet = self.app.pargs.triplet
        uri = "/v2.0/nws/accounts/%s/checkname" % triplet
        res = self.cmp_get(uri, data={})
        print("res: %s" % res)

    @ex(
        help="get account definitions",
        description="This command retrieves the account definition for a specified account id. The required 'id' argument expects the unique identifier of the account whose definition is being retrieved. This allows viewing the details of an account's configuration and settings.",
        example="beehive bu accounts definition-get UPO;beehive bu accounts definition-get id <uuid>",
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
        description="This CLI command adds account definitions to the specified account. The required 'id' argument specifies the account ID to add definitions to. Additional definition IDs can also be provided as arguments to add multiple definitions in a single command. Definitions provide additional context and categorization for accounts.",
        example="beehive bu accounts definition-add <uuid> <uuid> -e <env>;beehive bu accounts definition-add aou-novara-siovc OracleLinux85",
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
        description="This command allows you to add a new account to the system. You need to provide the name of the account and the division UUID it belongs to as required arguments.",
        example="beehive bu accounts add test123 Datacenter;beehive bu accounts add smranags Agricoltura -managed True -acronym smranags",
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
                (
                    ["-account_type"],
                    {
                        "help": "account account type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-management_model"],
                    {
                        "help": "account management model",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-pods"],
                    {
                        "help": "account pods",
                        "action": "store",
                        "type": str,
                        "default": None,
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
        if self.app.pargs.account_type is not None:
            data["account"].update({"account_type": self.app.pargs.account_type})

        if self.app.pargs.management_model is not None:
            data["account"].update({"management_model": self.app.pargs.management_model})

        if self.app.pargs.pods is not None:
            data["account"].update({"pods": self.app.pargs.pods})

        uri = "%s/accounts" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "Add account %s" % res})

    @ex(
        help="update account",
        description="This command updates an existing account. It requires the account id as the only required argument to identify which account needs to be updated.",
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
                        "default": None,
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
                (
                    ["-account_type"],
                    {
                        "help": "account account type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-management_model"],
                    {
                        "help": "account management model",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-pods"],
                    {
                        "help": "account pods",
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
        account_type = self.app.pargs.account_type
        management_model = self.app.pargs.management_model
        pods = self.app.pargs.pods

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

        if account_type is not None:
            account.update(
                {
                    "account_type": account_type,
                }
            )

        if management_model is not None:
            account.update(
                {
                    "management_model": management_model,
                }
            )

        if pods is not None:
            account.update(
                {
                    "pods": pods,
                }
            )

        data = {"account": account}
        # print("data: %s" % data)

        uri = "%s/accounts/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "Update resource %s with data %s" % (oid, account)})

    @ex(
        help="refresh account",
        description="This command refreshes an existing account by updating it with the latest information from the backend. The account id is required to identify which account to refresh.",
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
        description="This command closes an existing account. It requires the account id as the only required argument to identify the account to close.",
        example="beehive bu accounts delete <uuid> -e <env>;beehive bu accounts delete <uuid>",
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
                (
                    ["-delete_tags"],
                    {
                        "help": "if true delete all tags",
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        delete_services = str2bool(self.app.pargs.delete_services)
        delete_tags = str2bool(self.app.pargs.delete_tags)
        oid = self.get_account(oid).get("uuid")
        uri = "/v2.0/nws/accounts/%s" % oid
        data = {
            "delete_services": delete_services,
            "delete_tags": delete_tags,
            "close_account": True,
        }
        entity = "account %s" % oid
        res = self.cmp_delete(uri, entity=entity, data=data, output=False)
        if res is not None:
            print("%s closed" % entity)

    @ex(
        help="get account active services info",
        description="This command retrieves the active services information for a given account. The 'id' argument is required and specifies the account identifier for which to retrieve the active services info.",
        example="beehive bu accounts service-active-get CloudEntiMgmt|more;beehive bu accounts service-active-get CloudEntiMgmt",
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
        description="This command deletes account services by specifying the account id as a required argument. It also accepts a -y flag to skip confirmation prompt.",
        example="beehive bu accounts service-del <uuid> -y;beehive bu accounts service-del <uuid> -y",
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

    def loop_roles(self, x):
        sout = ""
        if x is not None:
            for s in x:
                sout += "%s - %s - %s \n" % (s["id"], s["name"], s["desc"])
        return sout

    @ex(
        help="get account user roles",
        description="This command retrieves the user roles associated with a specific account. The account is identified by supplying the account ID as the only required argument. The account ID can be specified as either an integer value or a UUID string.",
        example="beehive bu accounts user-role-get 672;beehive bu accounts user-role-get <uuid>",
        arguments=ARGS([(["id"], {"help": "account id", "action": "store", "type": str})]),
    )
    def user_role_get(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        uri = "%s/accounts/%s/userroles" % (self.baseuri, oid)
        params = []
        data = self.format_paginated_query(params)
        res = self.cmp_get(uri, data=data)

        transform = {"roles": lambda x: self.loop_roles(x), "roles.colortext": True}
        from cement import App

        app: App = self.app
        app.render(
            res,
            key="usernames",
            headers=["id", "name", "desc", "roles"],
            fields=["id", "name", "desc", "roles"],
            maxsize=200,
            transform=transform,
        )

    #############################
    @ex(
        help="Administer account",
        description="This CLI command 'beehive bu accounts manage' is used to administer account. It configures session permission in order to manage an account. There are no required arguments for this command.",
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
        description="This CLI command allows you to view details of an account. It does not require any arguments as it will display the details of the currently active account based on the session permissions.",
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
        description="This CLI command operates on accounts in the beehive bu system. It configures the session permission needed to perform operations on accounts.",
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
        description="This command retrieves the roles associated with a specific account. The account is identified by its unique id, which must be provided. Roles define access permissions and privileges for accounts in Nivola CMP.",
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
        self.app.render(res, key="roles", headers=["name", "desc", "role"], maxsize=200)

    @ex(
        help="get account users",
        description="This command retrieves account user details by specifying the account id as a required argument. It accepts the account id as a required parameter and returns user details for that specific account.",
        example="beehive bu accounts-auth user-get <uuid>;beehive bu accounts-auth user-get <uuid>",
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
        description="This command adds an account role to a specific user for the given account. It requires the account id, role name and user name as arguments to identify the account, role and user respectively to add the role association.",
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
        help="add account user from account",
        description=""" This command reaads user an roles from a source accont in ordere to add the same roles to the same users for the destination account.
        It requires the source account id and the destination account id.
        """,
        arguments=ARGS(
            [
                (["srcid"], {"help": "source account id", "action": "store", "type": str}),
                (["destid"], {"help": "destintion account id", "action": "store", "type": str}),
                (
                    ["--onebyone"],
                    {
                        "help": "confirm for each user",
                        "action": "store_true",
                        # "type": bool,
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def users_add_from_account(self):
        srcid = self.app.pargs.srcid
        destid = self.app.pargs.destid
        onebyone = self.app.pargs.onebyone
        srcuuid = self.get_account(srcid).get("uuid")
        destuuid = self.get_account(destid).get("uuid")
        uri = "%s/accounts/%s/users" % (self.baseuri, srcuuid)
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="users",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            # maxsize=200,
        )
        if self.confirm("add user roles to %s (%s)" % (destid, destuuid)):
            srcdata = res.get("users", [])
            counter = 0
            for user in srcdata:
                user_role = user.get("role", "viewer")
                msg: str = "adding %s (%s) as %s to %s" % (
                    user.get("name", ""),
                    user.get("desc", ""),
                    user_role,
                    destid,
                )
                if not onebyone or self.confirm(msg):
                    print(msg, end="...", flush=True)
                    data = {"user": {"user_id": user.get("uuid"), "role": user_role}}
                    try:
                        addres = self.cmp_post(f"{self.baseuri}/accounts/{destuuid}/users", data)
                        if addres.get("uuid"):
                            print(self.app.colored_text.green("OK"))
                            counter += 1
                        else:
                            print(self.app.colored_text.red("Fail"))
                    except:
                        print(self.app.colored_text.red("Fail"))
            print(f"added {counter} users to {destid}")

        # self.app.render(
        #     res,
        #     key="users",
        #     headers=["id", "name", "desc", "role"],
        #     fields=["uuid", "name", "desc", "role"],
        #     maxsize=200,
        # )

        pass

    @ex(
        help="remove account role from a user",
        description="This command removes an account role from a specific user. The required arguments are the account id, role and user to delete the authorization for. This deletes the permission for the given user to access the specified role on the account.",
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
        description="This command retrieves account groups for a specified account id. The required 'id' argument should provide the account identifier to fetch groups for.",
        example="beehive bu accounts-auth group-get procedo;beehive bu accounts-auth group-get master",
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
        description="This command adds an account role to an authorization group. The required arguments are the account ID, the account role to add, and the name of the authorization group to add the role to.",
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
        description="This command removes an account role from an authorization group. The required arguments are the account ID, the account role, and the authorization group to remove the role from.",
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
        description="This command retrieves the capabilities of an account. Capabilities determine the actions and resources an account is authorized to access. By specifying an account ID, this command will return the capabilities assigned to that specific account.",
        example="beehive bu accounts-capabilities get  EnteCloud-ComputeService-rupar73;beehive bu accounts-capabilities get EnteCloud-ComputeService-rupar73",
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
        help="add account capabilities",
        description="This command adds capabilities for a given account. It requires the account id and a comma separated list of capability names or ids as arguments.",
        example="beehive bu accounts-capabilities add prd_regpie CsiCloud-MonitoringService-base;beehive bu accounts-capabilities add <uuid> EnteCloud-NetworkService-base ",
        arguments=PARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["capabilities"],
                    {
                        "help": "comma separated list of capability names or ids",
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
        capabilities = capabilities.split(",")
        uri = "%s/accounts/%s/capabilities" % (self.baseuri, oid)
        for capability in capabilities:
            print("adding capability %s ..." % capability)
            try:
                self.cmp_post(uri, data={"capabilities": [capability]})
            except Exception as ex:
                msg = self.app.colored_text.red(str(ex))
                print(msg)
                continue

    @ex(
        help="update account capabilities",
        description="This command updates capabilities for a given account. It requires the account id and a comma separated list of capability names or ids as arguments.",
        example="beehive bu accounts-capabilities update prd_regpie CsiCloud-MonitoringService-base;beehive bu accounts-capabilities update <uuid> EnteCloud-NetworkService-base ",
        arguments=PARGS(
            [
                (["id"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["capabilities"],
                    {
                        "help": "comma separated list of capability names or ids",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        capabilities = self.app.pargs.capabilities
        capabilities = capabilities.split(",")
        uri = "%s/accounts/%s/capabilities" % (self.baseuri, oid)
        for capability in capabilities:
            print("updating capability %s ..." % capability)
            try:
                self.cmp_put(uri, data={"capabilities": [capability]})
            except Exception as ex:
                msg = self.app.colored_text.red(str(ex))
                print(msg)
                continue


class AccountTagController(AuthorityControllerChild):
    class Meta:
        label = "accounts_tags"
        description = "manage tags for account"
        help = "manage tags for account"

    @ex(
        help="get accounts",
        description="This command is used to retrieve accounts information from the Nivola CMP platform. It allows fetching accounts without any filtering criteria by not specifying optional arguments like size or environment. The accounts returned will not be limited or filtered in any way. This command is useful to get a complete list of all accounts to check or work with.",
        example="beehive bu accounts get -size 0 > head 10;beehive bu accounts get DOIT -e <env>",
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
