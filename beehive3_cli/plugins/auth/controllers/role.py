# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beehive3_cli.core.controller import PARGS, ARGS, StringAction
from beehive3_cli.plugins.auth.controllers.auth import AuthChildController
from beehive3_cli.translate import _


class AuthRoleController(AuthChildController):
    class Meta:
        stacked_on = "auth"
        stacked_type = "nested"
        label = "roles"
        description = _("roles management")
        help = _("roles management")

    @ex(
        help=_("get roles"),
        description=_("get roles"),
        example="beehive auth roles get -id <uuid>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("account uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-user"],
                    {
                        "help": _("user uuid"),
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
                    ["-names"],
                    {
                        "help": _("name filter"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-alias"],
                    {
                        "help": _("role alias"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-perms"],
                    {
                        "help": _(
                            "comma separated permission data (objtype,objdef,objid,objaction) "
                            "E.g.. service,Organization.Division.Account,aaa//bbb//ccc,*"
                        ),
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
            uri = f"{self.baseuri}/roles/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                # get users
                data = urlencode({"role": oid, "size": -1})
                uri = f"{self.baseuri}/users"
                users = self.cmp_get(uri, data).get("users")

                # get groups
                data = urlencode({"role": oid, "size": -1})
                uri = f"{self.baseuri}/groups"
                groups = self.cmp_get(uri, data).get("groups")

                self.app.render(res, key="role", details=True)
                self.print_section_heading("users")
                self.app.render(
                    users,
                    headers=self._meta.user_headers,
                    fields=self._meta.user_fields,
                )
                self.print_section_heading("groups")
                self.app.render(
                    groups,
                    headers=self._meta.group_headers,
                    fields=self._meta.group_fields,
                )
            else:
                self.app.render(res, key="role", details=True)
        else:
            params = ["user", "group", "names", "alias"]
            data = self.format_paginated_query(params)

            if self.app.pargs.perms:
                # ndata = {"perms.N": self.app.pargs.perms.split("|")}
                # data += "&" + urlencode(ndata)
                perms = self.app.pargs.perms.split("|")
                for perm in perms:
                    ndata = f"&perms.N={perm}"
                data += ndata

            # print("data: %s" % data)
            uri = f"{self.baseuri}/roles"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="roles",
                headers=self._meta.role_headers,
                fields=self._meta.role_fields,
            )

    @ex(
        help=_("add role"),
        description=_("add role"),
        arguments=ARGS(
            [
                (["name"], {"help": _("role name"), "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": _("role description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": "",
                    },
                ),
            ]
        ),
    )
    def add(self):
        name = self.app.pargs.name
        data = {"role": {"name": name, "desc": self.app.pargs.desc}}
        uri = f"{self.baseuri}/roles"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add role {res['uuid']}"})

    @ex(
        help=_("update role"),
        description=_("update role"),
        arguments=ARGS(
            [
                (["id"], {"help": _("role uuid"), "action": "store", "type": str}),
                (
                    ["-name"],
                    {
                        "help": _("role name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("role description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.id
        data = {
            "role": {
                "name": self.app.pargs.name,
                "desc": self.app.pargs.desc,
            }
        }
        uri = f"{self.baseuri}/roles/{oid}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update role {oid}"})

    @ex(
        help=_("delete role"),
        description=_("delete role"),
        arguments=ARGS(
            [
                (["id"], {"help": _("role uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/roles/{oid}"
        self.cmp_delete(uri, entity=f"role {oid}")

    @ex(
        help=_("expire role"),
        description=_("expire role"),
        arguments=ARGS(
            [
                (["id"], {"help": _("role uuid"), "action": "store", "type": str}),
                (
                    ["-days"],
                    {
                        "help": _("role name"),
                        "action": "store",
                        "type": str,
                        "default": "0",
                    },
                ),
            ]
        ),
    )
    def expire(self):
        oid = self.app.pargs.id
        days = self.app.pargs.days
        uri = f"{self.baseuri}/roles/{oid}/expire/{days}"
        self.cmp_delete(uri, entity=f"role {oid}", output=False)

    @ex(
        help=_("get permissions of role"),
        description=_("get permissions of role"),
        example="beehive auth roles get-perms <uuid>",
        arguments=PARGS(
            [
                (["id"], {"help": _("role uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def get_perms(self):
        oid = self.app.pargs.id
        params = []
        data = self.format_paginated_query(params)
        data += f"&role={oid}"
        uri = f"{self.baseuri}/objects/perms"
        res = self.cmp_get(uri, data=data)
        self.app.render(
            res,
            key="perms",
            headers=self._meta.perm_headers,
            fields=self._meta.perm_fields,
        )

    @ex(
        help=_("add permissions to role"),
        description=_("add permissions to role"),
        arguments=ARGS(
            [
                (["id"], {"help": _("role uuid"), "action": "store", "type": str}),
                (
                    ["perms"],
                    {
                        "help": _("comma separated list of permission id"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def add_perms(self):
        oid = self.app.pargs.id
        permids = self.app.pargs.perms
        perms = []
        for permid in permids.split(","):
            perms.append({"id": permid})

        data = {
            "role": {
                "perms": {"append": perms, "remove": []},
            }
        }
        uri = f"{self.baseuri}/roles/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add perm {res['perm_append']} to role {oid}"})

    @ex(
        help=_("delete permissions from role"),
        description=_("delete permissions from role"),
        arguments=ARGS(
            [
                (["id"], {"help": _("role uuid"), "action": "store", "type": str}),
                (
                    ["perms"],
                    {
                        "help": _("comma separated list of permission id"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def del_perms(self):
        oid = self.app.pargs.id
        permids = self.app.pargs.perms
        perms = []
        for permid in permids.split(","):
            perms.append({"id": permid})

        data = {
            "role": {
                "perms": {"append": [], "remove": perms},
            }
        }
        uri = f"{self.baseuri}/roles/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"delete perm {res['perm_remove']} from role {oid}"})

    @ex(
        help=_("Use role"),
        description=_("Modify session permission to role permission. "),
        arguments=ARGS(
            [
                (["roleid"], {"help": _("role uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def use_role(self):
        oid = self.app.pargs.roleid
        uri = f"{self.baseuri}/roles/use/{oid}"
        self.cmp_get(uri)
        self.app.render({"msg": f"set current session to role {oid} permission"})

    @ex(
        help=_("reset permissions to full user permission"),
        description=_("Modify reset current sessione to full user permissions"),
        arguments=ARGS([]),
    )
    def reset_role(self):
        uri = f"{self.baseuri}/roles/reset"
        self.cmp_get(uri)
        self.app.render({"msg": "reset permissions to full user permission"})
