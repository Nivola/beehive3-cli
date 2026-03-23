# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from os.path import split
from typing import List, Dict
from urllib.parse import urlencode

from cement import ex
from beecell.file import read_file_v2
from beecell.types.type_dict import dict_get, flatten_dict
from beecell.types.type_string import str2bool
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.business.controllers.authority import AuthorityControllerChild
from beehive3_cli.translate import _


class AccountController(AuthorityControllerChild):
    class Meta:
        label = "accounts"
        description = _("account management")
        help = _("account management")

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
            "date creation",
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

    def pre_command_run(self):
        super().pre_command_run()
        self.config_path = self.app.config.get("beehive", "cmp_post_install_path")

    @ex(
        help=_("get accounts"),
        description=_(
            "This command is used to retrieve accounts information from the Nivola CMP platform. "
            "It allows fetching accounts without any filtering criteria by not specifying "
            "optional arguments like size or environment. "
            "The accounts returned will not be limited or filtered in any way. "
            "This command is useful to get a complete list of all accounts to check or work with."
        ),
        example="beehive bu accounts get DOIT -e <env>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("account id"),
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
                        "help": _("account name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-division-id"],
                    {
                        "help": _("division uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-contact"],
                    {
                        "help": _("account contact"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": _("account email"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email-support"],
                    {
                        "help": _("account email support"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-expired"],
                    {
                        "help": _("search expired account") + "; 'True'/'False' 'y'/'n' ",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": _("status account"),
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
        status = getattr(self.app.pargs, "status", None)
        expired = getattr(self.app.pargs, "expired", None)
        b_expired = str2bool(expired)

        if oid is not None:
            res = self.get_account(oid, b_expired)
            oid = res["uuid"]

            if self.is_output_text():
                self.app.render(res, details=True)

                if b_expired:
                    return

                self.c("\ncapabilities", "underline")
                uri = f"{self.baseuri}/accounts/{oid}/capabilities"
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

            if status is not None:
                status_d = {
                    "ACTIVE": 1,
                    "CLOSED": 22,
                    "DELETED": 6,
                }
                data += f"&service_status_id={status_d[status]}"

            if b_expired is True:
                # data += "&filter_expired=True&active=False"
                data += "&filter_expired=True"

            uri = f"{self.baseuri}/accounts"
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
        help=_("get account triplet"),
        description=_("This command get account triplet"),
        example="beehive bu accounts triplet prodis",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("account id"),
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
        res_account = self.get_account(oid)

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

        triplet = f"{org_name}.{div_name}.{account_name}"
        print(f"triplet: {triplet}")

    @ex(
        help=_("check account exists"),
        description=_("This command is used to check if account exists."),
        example="beehive bu accounts check aaa -e <env>",
        arguments=PARGS(
            [
                (
                    ["triplet"],
                    {
                        "help": _("account triplet name"),
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
        uri = f"/v2.0/nws/accounts/{triplet}/checkname"
        res = self.cmp_get(uri, data={})
        print(f"res: {res}")

    @ex(
        help=_("get account definitions"),
        description=_(
            "This command retrieves the account definition for a specified account id. "
            "The required 'id' argument expects the unique identifier of the account "
            "whose definition is being retrieved. This allows viewing the details "
            "of an account's configuration and settings."
        ),
        example="beehive bu accounts definition-get id <uuid>",
        arguments=PARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
                (
                    ["-plugintype"],
                    {
                        "help": _("filter by definition plugin"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-category"],
                    {
                        "help": _("filet by category "),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-container"],
                    {
                        "help": _("get only containers definitions"),
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
        if self.app.pargs.name:
            data["name"] = self.app.pargs.name

        uri = f"/v2.0/nws/accounts/{oid}/definitions"
        res = self.cmp_get(uri, data=data)

        if self.is_output_text():
            self.c("\ndefinitions", "underline")
            headers = ["name", "category", "plugintype", "is a", "is_default"]
            fields = ["name", "category", "plugintype", "is_a", "is_default"]
            self.app.render(res, key="definitions", headers=headers, fields=fields, maxsize=80)
        else:
            self.app.render(res, key="definitions", details=True)

    @ex(
        help=_("add account definitions"),
        description=_(
            "This CLI command adds account definitions to the specified account. "
            "The required 'id' argument specifies the account ID to add definitions to. "
            "Additional definition IDs can also be provided as arguments to add "
            "multiple definitions in a single command. "
            "Definitions provide additional context and categorization for accounts."
        ),
        example="beehive bu accounts definition-add aou-novara-siovc OracleLinux85",
        arguments=PARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
                (
                    ["definitions"],
                    {
                        "help": _("comma separated list of definition ids"),
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
        uri = f"/v2.0/nws/accounts/{oid}/definitions"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add definitions {res.get('definitions', [])} to account {oid}"})
   
    @ex(
        help=_("add Kms Domain definition to an account"),
        description=_( "This command adds a kms domain definitions to the specified account. " ),
        arguments=PARGS(
            [
                (["id"], {"help": _("account id or name"), "action": "store", "type": str}),
                (
                    ["domain"],
                    {
                        "help": _("Kms domain name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def kms_domain_add(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        domain = self.app.pargs.domain
        data = {"definitions": [f"KMS-DOMAIN-{domain}"]}
        uri = f"/v2.0/nws/accounts/{oid}/definitions"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add definitions {res.get('definitions', [])} to account {oid}"})

    @ex(
        help=_("delete account definitions"),
        description=_(
            "This CLI command delete account definitions from  the specified account. "
            "It requires to specifies the account ID and the definition to remove. "
            "Definitions provide additional context and categorization for accounts."
        ),
        example="beehive bu accounts definition-del <uuid> <uuid> -e <env>",
        arguments=PARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
                (
                    ["definition"],
                    {
                        "help": _("definition uuid or name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def definition_del(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        definition = self.app.pargs.definition
        uri = f"/v2.0/nws/accounts/{oid}/definitions/{definition}"
        self.cmp_delete(uri)
        self.app.render({"msg": f"deleted definition {definition} from account {oid}"})

    @ex(
        help=_("add account"),
        description=_(
            "This command allows you to add a new account to the system. "
            "You need to provide the name of the account and the division UUID it belongs to as required arguments."
        ),
        example="beehive bu accounts add smranags Agricoltura -managed True -acronym smranags",
        arguments=ARGS(
            [
                (["name"], {"help": _("account name"), "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": _("account description"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["division"],
                    {"help": _("division uuid"), "action": "store", "type": str},
                ),
                # (['-price_list'], {'help': 'account price list id', 'action': 'store', 'type': int, 'default': None}),
                (
                    ["-contact"],
                    {
                        "help": _("account contact"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": _("account email"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email-support"],
                    {
                        "help": _("account email support"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email-support-link"],
                    {
                        "help": _("account email support link"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-note"],
                    {
                        "help": _("account note"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-acronym"],
                    {
                        "help": _("account acronym"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-managed"],
                    {
                        "help": _("if true set account as managed"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
                (
                    ["-account_type"],
                    {
                        "help": _("account account type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-management_model"],
                    {
                        "help": _("account management model"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-pods"],
                    {
                        "help": _("account pods"),
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

        uri = f"{self.baseuri}/accounts"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"Add account {res}"})

    @ex(
        help=_("update account"),
        description=_(
            "This command updates an existing account. "
            "It requires the account id as the only required argument to identify which account needs to be updated."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
                # (["-name"], {"help": _("account name"), "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": _("account description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                # (
                #     ["-division"],
                #     {"help": _("division uuid"), "action": "store", "type": str},
                # ),
                (
                    ["-price_list"],
                    {
                        "help": _("account price list id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-contact"],
                    {
                        "help": _("account contact"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": _("account email"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email-support"],
                    {
                        "help": _("account email support"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email-support-link"],
                    {
                        "help": _("account email support link"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-acronym"],
                    {
                        "help": _("account acronym"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-note"],
                    {
                        "help": _("account note"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-account_type"],
                    {
                        "help": _("account account type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-management_model"],
                    {
                        "help": _("account management model"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-pods"],
                    {
                        "help": _("account pods"),
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

        uri = f"{self.baseuri}/accounts/{oid}"
        res = self.cmp_put(uri, data=data)
        print(res)
        self.app.render({"msg": f"Update resource {oid} with data {account}"})

    @ex(
        help=_("refresh account"),
        description=_(
            "This command refreshes an existing account by updating it with the latest information from the backend. "
            "The account id is required to identify which account to refresh."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
            ]
        ),
    )
    def patch(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        data = {"account": {}}
        uri = f"{self.baseuri}/accounts/{oid}"
        self.cmp_patch(uri, data=data, timeout=600)
        self.app.render({"msg": f"Refresh account {oid}"})

    @ex(
        help=_("close account"),
        description=_(
            "This command closes an existing account. "
            "It requires the account id as the only required argument to identify the account to close."
        ),
        example="beehive bu accounts delete <uuid>",
        arguments=ARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
                (
                    ["--no-delete-services"],
                    {
                        "help": _("no delete all child services"),
                        "action": "store_false",
                        # "type": bool,
                        "dest": "delete_services",
                        # "default": True,
                    },
                ),
                (
                    ["--no-delete-tags"],
                    {
                        "help": _("if true delete all tags"),
                        "action": "store_false",
                        "dest": "delete_tags",
                        # "type": bool,
                        # "default": True,
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        # delete_services = str2bool(self.app.pargs.delete_services)
        # delete_tags = str2bool(self.app.pargs.delete_tags)
        delete_services = self.app.pargs.delete_services
        delete_tags = self.app.pargs.delete_tags

        oid = self.get_account(oid).get("uuid")
        uri = f"/v2.0/nws/accounts/{oid}"
        data = {
            "delete_services": delete_services,
            "delete_tags": delete_tags,
            "close_account": True,
        }
        entity = f"account {oid}"
        res = self.cmp_delete(uri, entity=entity, data=data, output=False)
        if res is not None:
            print(f"{entity} closed")

    @ex(
        help=_("dev: real delete account"),
        description=_(
            "This command real delete an existing account. "
            "It requires the account id as the only required argument to identify the account to delete."
        ),
        example="beehive bu accounts real-delete <uuid> -e <env>",
        arguments=ARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
                (
                    ["-delete_services"],
                    {
                        "help": _("if true delete all child services"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-delete_tags"],
                    {
                        "help": _("if true delete all tags"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
        hide=True,
    )
    def real_delete(self):
        oid = self.app.pargs.id
        delete_services = str2bool(self.app.pargs.delete_services)
        delete_tags = str2bool(self.app.pargs.delete_tags)
        oid = self.get_account(oid).get("uuid")
        uri = f"/v2.0/nws/accounts/{oid}"
        data = {
            "delete_services": delete_services,
            "delete_tags": delete_tags,
        }
        entity = f"account {oid}"
        res = self.cmp_delete(uri, entity=entity, data=data, output=False)
        if res is not None:
            print(f"{entity} deleted")

    @ex(
        help=_("get account active services info"),
        description=_(
            "This command retrieves the active services information for a given account. "
            "The 'id' argument is required and specifies the account identifier for "
            "which to retrieve the active services info."
        ),
        example="beehive bu accounts service-active-get CloudEntiMgmt -plugin_name DatabaseService",
        arguments=ARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
                (["-plugin_name"], {"help": _("plugin_name"), "action": "store", "type": str, "default": None}),
            ]
        ),
    )
    def service_active_get(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        uri = f"{self.baseuri}/accounts/{oid}/activeservices"
        data_filter = {}

        plugin_name = self.app.pargs.plugin_name
        if plugin_name is not None:
            data_filter.update({
                "plugin_name": plugin_name
            })

        res = self.cmp_get(uri, data=data_filter).get("services", {}).get("service_container", [])
        for item in res:
            metrics = item.pop("tot_metrics", [])
            self.c(f"\nservice {item['plugin_type']}", "underline")
            self.app.render(item, details=True)
            self.app.render(metrics, headers=["metric", "unit", "value", "quota"])

    @ex(
        help=_("delete account services one by one"),
        description=_(
            "This command deletes account services by specifying the account id as a required argument. "
            "It also accepts a -y flag to skip confirmation prompt."
        ),
        example="beehive bu accounts service-del <uuid> -y",
        arguments=ARGS([(["id"], {"help": _("account id"), "action": "store", "type": str})]),
    )
    def service_del(self):
        """delete  serivices in account one by one in correct order
        | plugintype             |objclass
        | MonitoringAlert        |beehive_service.plugins.monitoringservice.controller_alert.ApiMonitoringAlert
        | NetworkSshGateway      |beehive_service_netaas.networkservice.controller.ApiSshGateway
        | NetworkLoadBalancer    |beehive_service_netaas.networkservice.controller.ApiNetworkLoadBalancer
        | NetworkListener        |beehive_service_netaas.networkservice.controller.ApiNetworkListener
        | NetworkTargetGroup     |beehive_service_netaas.networkservice.controller.ApiNetworkTargetGroup
        | NetworkHealthMonitor   |beehive_service_netaas.networkservice.controller.ApiNetworkHealthMonitor
        | MonitoringInstance     |beehive_service.plugins.monitoringservice.controller.ApiMonitoringInstance
        | MonitoringFolder       |beehive_service.plugins.monitoringservice.controller.ApiMonitoringFolder
        | MonitoringService      |beehive_service.plugins.monitoringservice.controller.ApiMonitoringService
        | LoggingInstance        |beehive_service.plugins.loggingservice.controller.ApiLoggingInstance
        | LoggingSpace           |beehive_service.plugins.loggingservice.controller.ApiLoggingSpace
        | LoggingService         |beehive_service.plugins.loggingservice.controller.ApiLoggingService
        | ComputeCustomization   |beehive_service.plugins.computeservice.controller.ApiComputeCustomization
        | VirtualService         |beehive_service.entity.service_type.ApiServiceType
        | NetworkGateway         |beehive_service_netaas.networkservice.controller.ApiNetworkGateway
        | NetworkService         |beehive_service_netaas.networkservice.controller.ApiNetworkService
        | ComputeKeyPairs        |beehive_service.plugins.computeservice.controller.ApiComputeKeyPairs
        | ComputeVolume          |beehive_service.plugins.computeservice.controller.ApiComputeVolume
        | AppEngineInstance      |beehive_service.plugins.appengineservice.controller.ApiAppEngineInstance
        | AppEngineService       |beehive_service.plugins.appengineservice.controller.ApiAppEngineService
        | StorageEFS             |beehive_service.plugins.storageservice.controller.ApiStorageEFS
        | StorageService         |beehive_service.plugins.storageservice.controller.ApiStorageService
        | DatabaseInstance       |beehive_service.plugins.databaseservice.controller.ApiDatabaseServiceInstance
        | DatabaseService        |beehive_service.plugins.databaseservice.controller.ApiDatabaseService
        | ComputeSecurityGroup   |beehive_service.plugins.computeservice.controller.ApiComputeSecurityGroup
        | ComputeVPC             |beehive_service.plugins.computeservice.controller.ApiComputeVPC
        | ComputeSubnet          |beehive_service.plugins.computeservice.controller.ApiComputeSubnet
        | ComputeImage           |beehive_service.plugins.computeservice.controller.ApiComputeImage
        | ComputeInstance        |beehive_service.plugins.computeservice.controller.ApiComputeInstance
        | ComputeService         |beehive_service.plugins.computeservice.controller.ApiComputeService
        """
        oid = self.app.pargs.id
        account = self.get_account(oid)
        oid = account.get("uuid")
        account_type = account.get("account_type")
        accountname = account.get("name")

        plugintypes: List[str] = []
        # delete all child services
        # print(f"Account {accountname} {oid} is {account_type}")
        uri = "/v2.0/nws/serviceinsts"
        if account_type == "private":
            print(f"No network services deleted on Account {accountname}[{oid}] it is {account_type}")
            plugintypes = [
                "ComputeImage",
                "LoggingInstance",
                "MonitoringInstance",
                "ComputeInstance",
                "AppEngineInstance",
                "StorageEFS",
                "DatabaseInstance",
                "ComputeVolume",
                "ComputeSecurityGroup",
            ]
        else:
            plugintypes = [
                "LoggingSpace",
                "MonitoringFolder",
                "MonitoringAlert",
                "LoggingInstance",
                "MonitoringInstance",
                "ComputeInstance",
                "AppEngineInstance",
                "DatabaseInstance",
                "StorageEFS",
                "ComputeVolume",
                "ComputeKeyPairs",
                "ComputeSecurityGroup",
                "ComputeSubnet",
                "ComputeVPC",
                "ComputeImage",
            ]
        for plugin in plugintypes:
            print(f"Searching for {plugin} ...")
            res = self.cmp_get(uri, data={"account_id": oid, "plugintype": plugin, "size": -1}).get("serviceinsts", [])
            for item in res:
                print(
                    f" account: {item['account']['name'] } plugintype {item['plugintype']} "
                    f" uuid{item['uuid']} name: {item['name']}  [{plugin}]"
                )
                self.generic_service_delete(uuid=item["uuid"], name=item["name"], plugin=plugin)

    def loop_roles(self, x):
        sout = ""
        if x is not None:
            for s in x:
                sout += f"{s['id']} - {s['name']} - {s['desc']} \n"
        return sout

    @ex(
        help=_("get account user roles"),
        description=_(
            "This command retrieves the user roles associated with a specific account. "
            "The account is identified by supplying the account ID as the only required argument. "
            "The account ID can be specified as either an integer value or a UUID string."
        ),
        example="beehive bu accounts user-role-get <uuid>",
        arguments=ARGS([(["id"], {"help": _("account id"), "action": "store", "type": str})]),
    )
    def user_role_get(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        uri = f"{self.baseuri}/accounts/{oid}/userroles"
        params = []
        data = self.format_paginated_query(params)
        res = self.cmp_get(uri, data=data)

        transform = {"roles": self.loop_roles, "roles.colortext": True}
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
        help=_("Administer account"),
        description=_(
            "This CLI command 'beehive bu accounts manage' is used to administer account. "
            "It configures session permission in order to manage an account. "
            "There are no required arguments for this command."
        ),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("the account id to manage"),
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
        help=_("View account"),
        description=_(
            "This CLI command allows you to view details of an account. "
            "It does not require any arguments as it will display the details "
            "of the currently active account based on the session permissions."
        ),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("the account id to manage"),
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
        help=_("Operate on account"),
        description=_(
            "This CLI command operates on accounts in the beehive bu system. "
            "It configures the session permission needed to perform operations on accounts."
        ),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("the account id to manage"),
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

    @ex(
        help=_("set account svms"),
        description=_("set zone svms account can see"),
        arguments=ARGS(
            [
                (
                    ["account_id"],
                    {
                        "help": _("the account id to manage"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("svm data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def svm_set(self):
        """
        sets the svms the account can see, by setting them in the core storage service
        """

        def get_orchestrator(site_name, orch_type, cluster):
            uri = f"/v1.0/nrs/provider/sites/{site_name}"
            site = self.cmp_get(uri)
            orchestrators = dict_get(site, "site.attributes.orchestrators")
            container_id = None
            for orch in orchestrators:
                if orch.get("type") == orch_type and orch.get("name") == cluster:
                    return orch.get("id"), orch.get("name")
            if container_id is None:
                raise Exception(f"No {orch_type} orchestrator {cluster} found in {site_name}")
            return None

        def get_remote_svm(site_name, svm_name, cid):
            data = urlencode({"type": "OntapNetapp.Svm", "name": svm_name}, doseq=True)
            uri = f"/v1.0/nrs/containers/{cid}/discover_remote"
            svms = self.cmp_get(uri, data=data, timeout=20)
            svms = svms.get("discover_resources")
            count = len(svms)
            if count != 1:
                raise Exception(f"Svm {svm_name} not found or is not unique in site {site_name} (container id {cid})")
            return svms[0]

        def storage_service_info(account_uuid):
            self.app.render({"msg": f"Retrieving storage core service for account {account_uuid} ..."})
            data = {"owner-id": account_uuid}
            uri = "/v1.0/nws/storageservices"
            res = self.cmp_get(uri, data=urlencode(data)).get("DescribeStorageResponse")
            total = res.get("storageTotal")
            storage_set = res.get("storageSet")
            if total != 1 or not storage_set or (isinstance(storage_set, list) and len(storage_set) > 1):
                raise Exception(
                    f"Account {account_id} has {total} StorageService instance! It should have ONE."
                )
            return storage_set[0]

        account_id = self.app.pargs.account_id
        data_filepath = self.app.pargs.file
        filepath = f"{self.config_path}/{data_filepath}"

        self.app.render({"msg": f"Checking account {account_id} configuration..."})

        # query account
        uri = f"/v1.0/nws/accounts/{account_id}"
        account = self.cmp_get(uri).get("account")

        # check account has storage core service and compute zone
        storage_service = storage_service_info(account.get("uuid"))
        # storage_service_uuid = storage_service.get("uuid")
        compute_zone_uuid = storage_service.get("resource_uuid")
        if compute_zone_uuid is None:
            raise Exception("compute zone uuid not found")

        # verify account isn't already configured for staas v2
        config = self.api.resource.entity.get_config(compute_zone_uuid).get("config")
        if config.get("staas"):
            self.app.error("Account is already configured: ")
            self.app.render(config.get("staas"), details=True)
            self.app.warning("If the configuration is not correct, unset it with svm-unset")
            return

        # parse configuration file
        _, filename = split(filepath)
        if not filename:
            raise Exception(f"Invalid path {filepath}")

        # get the name of the division the account belongs to and verify it is equal to that in file name
        division_id = account.get("division_id")
        uri = f"/v1.0/nws/divisions/{division_id}"
        division = self.cmp_get(uri).get("division")
        division_name = division.get("name")
        if not division_name:
            raise Exception(f"Unable to find division name for account {account_id}")

        if division_name.lower() not in filename.lower():
            raise Exception(
                f"The account's division ({division_name}) is different from that "
                "specified inside the file name ({filename})"
            )

        # read svm config file
        self.app.render({"msg": f"Reading file {filename}..."})
        data = read_file_v2(filepath)

        # querying remote ontap to validate svms
        self.app.render({"msg": "Validating data ..."})

        staas_cfg_root = dict_get(data, "configs.staas")
        if not isinstance(staas_cfg_root, dict):
            raise Exception("Invalid type for configs staas element configuration")

        staas_sites_cfg: List[Dict] = staas_cfg_root.get("sites")
        if not isinstance(staas_sites_cfg, list):
            raise Exception("Invalid sites element configuration")

        for item in staas_sites_cfg:
            site_name = item.get("site")
            cluster = item.get("cluster")
            if not site_name or not cluster:
                raise Exception(f"Invalid site configuration. Site or cluster missing. Parsed: {item}")
            # get ontap orchestrator id for given site
            container_id, container_name = get_orchestrator(site_name, "ontap", cluster)
            self.app.render({"msg": f"Site: {site_name} - Cluster: {cluster} - Container: {container_name}"})

            for svm in item.get("svm"):
                svm_name = svm.get("name")

                if not svm_name:
                    raise Exception(f"Invalid site svm configuration. Parsed: {svm}")

                self.app.render({"msg": f"Checking svm {svm_name} is valid..."})
                # verify remote svm exists
                remote_svm = get_remote_svm(site_name, svm_name, container_id)
                svm.update({"ext_id": remote_svm.get("uuid")})
                self.app.render({"msg": f"{svm_name} verified"})

        # write metadata in compute zone
        self.app.render({"msg": "Updating account compute zone"})
        staas_sites_cfg = {item.pop("site"): item for item in staas_sites_cfg}
        staas_cfg_flat = flatten_dict({"staas.sites": staas_sites_cfg}, delimiter=".")
        for k, v in staas_cfg_flat.items():
            self.api.resource.entity.set_config(compute_zone_uuid, key=k, value=v)
        staas_relationships_cfg = staas_cfg_root.get("relationships")
        staas_relationships_cfg_flat = flatten_dict({"staas.relationships": staas_relationships_cfg}, delimiter=".")
        for k, v in staas_relationships_cfg_flat.items():
            self.api.resource.entity.set_config(compute_zone_uuid, key=k, value=v)

        # update core storage service
        # self.api.business.service.instance.set_config(storage_service_uuid, key="api_version", value="v2.0")
        self.app.render({"msg": "Done"})

    @ex(
        help=_("unset account svms"),
        description=_("unset zone svms account can see"),
        arguments=ARGS(
            [
                (
                    ["account_id"],
                    {
                        "help": _("the account id to manage"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def svm_unset(self):
        def get_core_service(account_id, plugintype):
            self.app.render({"msg": f"Retrieving storage core service for account {account_id} ..."})
            data = {"flag_container": True, "plugintype": plugintype, "account_id": account_id}
            uri = "/v1.0/nws/serviceinsts"
            res = self.cmp_get(uri, data=data)
            count = res.get("count", 0)
            if count != 1:
                raise Exception(
                    f"Account {account_id} has {count} StorageService instance! It should have ONE."
                )
            return res.get("serviceinsts")[0]

        account_id = self.app.pargs.account_id

        # get account core storage service
        storage_service = get_core_service(account_id, "StorageService")
        storage_service_uuid = storage_service.get("uuid")
        compute_zone_uuid = storage_service.get("resource_uuid")
        if compute_zone_uuid is None:
            raise Exception("compute zone uuid not found")
        self.app.render({"msg": f"Got storage core service {storage_service_uuid}"})

        self.api.resource.entity.set_config(compute_zone_uuid, "staas", None)
        # self.api.business.service.instance.set_config(storage_service_uuid, key="api_version", value="v1.0")


class AccountAuthController(AuthorityControllerChild):
    class Meta:
        label = "accounts_auth"
        description = _("account authorization")
        help = _("account authorization")

    @ex(
        help=_("get account roles"),
        description=_(
            "This command retrieves the roles associated with a specific account. "
            "The account is identified by its unique id, which must be provided. "
            "Roles define access permissions and privileges for accounts in Nivola CMP."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
            ]
        ),
    )
    def role_get(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        uri = f"{self.baseuri}/accounts/{oid}/roles"
        res = self.cmp_get(uri)
        self.app.render(res, key="roles", headers=["name", "desc", "role"], maxsize=200)

    @ex(
        help=_("get account users"),
        description=_(
            "This command retrieves account user details by specifying the account id as a required argument. "
            "It accepts the account id as a required parameter and returns user details for that specific account."
        ),
        example="beehive bu accounts-auth user-get <uuid>",
        arguments=ARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
            ]
        ),
    )
    def user_get(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        uri = f"{self.baseuri}/accounts/{oid}/users"
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="users",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            maxsize=200,
        )

    @ex(
        help=_("add account role to a user"),
        description=_(
            "This command adds an account role to a specific user for the given account. "
            "It requires the account id, role name and user name as arguments to identify "
            "the account, role and user respectively to add the role association."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
                (["role"], {"help": _("account role"), "action": "store", "type": str}),
                (
                    ["user"],
                    {"help": _("authorization user"), "action": "store", "type": str},
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
        uri = f"{self.baseuri}/accounts/{oid}/users"
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help=_("add account user from account"),
        description=_(
            "This command reaads user an roles from a source accont in ordere "
            "to add the same roles to the same users for the destination account."
            "It requires the source account id and the destination account id."
        ),
        arguments=ARGS(
            [
                (["srcid"], {"help": _("source account id"), "action": "store", "type": str}),
                (["destid"], {"help": _("destintion account id"), "action": "store", "type": str}),
                (
                    ["--onebyone"],
                    {
                        "help": _("confirm for each user"),
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
        uri = f"{self.baseuri}/accounts/{srcuuid}/users"
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="users",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            # maxsize=200,
        )
        if self.confirm(f"add user roles to {destid} ({destuuid})"):
            srcdata = res.get("users", [])
            counter = 0
            for user in srcdata:
                user_role = user.get("role", "viewer")
                user_name = user.get("name", "")
                user_desc = user.get("desc", "")
                msg = f"adding {user_name} ({user_desc}) as {user_role} to {destid}"
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

    @ex(
        help=_("remove account role from a user"),
        description=_(
            "This command removes an account role from a specific user. "
            "The required arguments are the account id, role and user to delete the authorization for. "
            "This deletes the permission for the given user to access the specified role on the account."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
                (["role"], {"help": _("account role"), "action": "store", "type": str}),
                (
                    ["user"],
                    {"help": _("authorization user"), "action": "store", "type": str},
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
        uri = f"{self.baseuri}/accounts/{oid}/users"
        res = self.cmp_delete(uri, data)
        self.app.render({"msg": res})

    @ex(
        help=_("get account groups"),
        description=_(
            "This command retrieves account groups for a specified account id. "
            "The required 'id' argument should provide the account identifier to fetch groups for."
        ),
        example="beehive bu accounts-auth group-get master",
        arguments=ARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
            ]
        ),
    )
    def group_get(self):
        oid = self.app.pargs.id
        oid = self.get_account(oid).get("uuid")
        uri = f"{self.baseuri}/accounts/{oid}/groups"
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="groups",
            headers=["id", "name", "role"],
            fields=["uuid", "name", "role"],
            maxsize=200,
        )

    @ex(
        help=_("add account role to a group"),
        description=_(
            "This command adds an account role to an authorization group. "
            "The required arguments are the account ID, the account role to add, "
            "and the name of the authorization group to add the role to."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
                (["role"], {"help": _("account role"), "action": "store", "type": str}),
                (
                    ["group"],
                    {"help": _("authorization group"), "action": "store", "type": str},
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
        uri = f"{self.baseuri}/accounts/{oid}/groups"
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help=_("remove account role from a group"),
        description=_(
            "This command removes an account role from an authorization group. "
            "The required arguments are the account ID, the account role, "
            "and the authorization group to remove the role from."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
                (["role"], {"help": _("account role"), "action": "store", "type": str}),
                (
                    ["group"],
                    {"help": _("authorization group"), "action": "store", "type": str},
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
        uri = f"{self.baseuri}/accounts/{oid}/groups"
        res = self.cmp_delete(uri, data)
        self.app.render({"msg": res})


class AccountCapabilityController(AuthorityControllerChild):
    class Meta:
        label = "accounts_capabilities"
        description = _("accounts capabilities")
        help = _("accounts capabilities")

    @ex(
        help=_("get account capabilities"),
        description=_(
            "This command retrieves the capabilities of an account. "
            "Capabilities determine the actions and resources an account is authorized to access. "
            "By specifying an account ID, this command will return the capabilities "
            "assigned to that specific account."
        ),
        example="beehive bu accounts-capabilities get  EnteCloud-ComputeService-rupar73",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-capability"],
                    {
                        "help": _("capability name"),
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
        uri = f"{self.baseuri}/accounts/{oid}/capabilities"
        res = self.cmp_get(uri, data=data)
        if self.is_output_text():
            for item in res.get("capabilities"):
                self.c(f"\n{item.pop('name')}", "underline")
                services = item.pop("services")
                self.app.render(item, details=True)
                print()
                headers = ["type", "name", "status", "require"]
                fields = ["type", "name", "status", "require.name"]
                self.app.render(services, headers=headers, fields=fields, maxsize=200)
        else:
            self.app.render(res, details=True)

    @ex(
        help=_("add account capabilities"),
        description=_(
            "This command adds capabilities for a given account. "
            "It requires the account id and a comma separated list of capability names or ids as arguments."
        ),
        example="beehive bu accounts-capabilities add prd_regpie CsiCloud-MonitoringService-base",
        arguments=PARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
                (
                    ["capabilities"],
                    {
                        "help": _("comma separated list of capability names or ids"),
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
        uri = f"{self.baseuri}/accounts/{oid}/capabilities"
        for capability in capabilities:
            print(f"adding capability {capability} ...")
            try:
                self.cmp_post(uri, data={"capabilities": [capability]})
            except Exception as exc:
                msg = self.app.colored_text.red(str(exc))
                print(msg)
                continue

    @ex(
        help=_("update account capabilities"),
        description=_(
            "This command updates capabilities for a given account. "
            "It requires the account id and a comma separated list of capability names or ids as arguments."
        ),
        example="beehive bu accounts-capabilities update prd_regpie CsiCloud-MonitoringService-base",
        arguments=PARGS(
            [
                (["id"], {"help": _("account id"), "action": "store", "type": str}),
                (
                    ["capabilities"],
                    {
                        "help": _("comma separated list of capability names or ids"),
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
        uri = f"{self.baseuri}/accounts/{oid}/capabilities"
        for capability in capabilities:
            print(f"updating capability {capability} ...")
            try:
                self.cmp_put(uri, data={"capabilities": [capability]})
            except Exception as exception:
                msg = self.app.colored_text.red(str(exception))
                print(msg)
                continue


class AccountTagController(AuthorityControllerChild):
    class Meta:
        label = "accounts_tags"
        description = _("manage tags for account")
        help = _("manage tags for account")

    @ex(
        help=_("get account tag"),
        description=_(
            "This command is used to retrieve account tags."
        ),
        example="beehive bu accounts-tags get <account-id> -e <env>",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("account id"),
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
        uri = f"{self.baseuri}/accounts/{oid}/tags"
        res = self.cmp_get(uri, data=data)
        self.app.render(
            res,
            key="tags",
            headers=["uuid", "name", "desc", "active", "creation"],
            fields=["uuid", "name", "desc", "active", "date.creation"],
        )


    @ex(
        help=_("add account tag"),
        description=_(
            "This CLI command adds account tag to the specified account."
        ),
        example="beehive bu accounts-tags add <account> <value> -e <env>",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {"help": _("account id"), "action": "store", "type": str}),
                (
                    ["tagvalue"],
                    {
                        "help": _("tag value"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add(self):
        oid = self.app.pargs.id
        account_oid = self.get_account(oid).get("uuid")
        tagvalue = self.app.pargs.tagvalue
        data = {
            "tag": {
                "account": account_oid,
                "value": tagvalue,
            }
        }
        uri = "/v1.0/nws/tags"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add tag {res.get('uuid', '')} to account {oid}"})
