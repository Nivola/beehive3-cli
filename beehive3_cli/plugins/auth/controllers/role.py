# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beehive3_cli.core.controller import PARGS, ARGS, StringAction
from beehive3_cli.plugins.auth.controllers.auth import AuthChildController


class AuthRoleController(AuthChildController):
    class Meta:
        stacked_on = "auth"
        stacked_type = "nested"
        label = "roles"
        description = "roles management"
        help = "roles management"

    @ex(
        help="get roles",
        description="get roles",
        example="beehive auth roles get-perms <uuid>;beehive auth roles get -id <uuid>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "account uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-user"],
                    {
                        "help": "user uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group"],
                    {
                        "help": "group uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-names"],
                    {
                        "help": "name filter",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-alias"],
                    {
                        "help": "role alias",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-perms"],
                    {
                        "help": "comma separated permission data (objtype,objdef,objid,objaction) Es. service,Organization.Division.Account,aaa//bbb//ccc,*",
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
            uri = "%s/roles/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                # get users
                data = urlencode({"role": oid, "size": -1})
                uri = "%s/users" % self.baseuri
                users = self.cmp_get(uri, data).get("users")

                # get groups
                data = urlencode({"role": oid, "size": -1})
                uri = "%s/groups" % self.baseuri
                groups = self.cmp_get(uri, data).get("groups")

                self.app.render(res, key="role", details=True)
                self.c("\nusers", "underline")
                self.app.render(
                    users,
                    headers=self._meta.user_headers,
                    fields=self._meta.user_fields,
                )
                self.c("\ngroups", "underline")
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
                    ndata = "&perms.N=%s" % perm
                data += ndata

            # print("data: %s" % data)
            uri = "%s/roles" % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="roles",
                headers=self._meta.role_headers,
                fields=self._meta.role_fields,
            )

    @ex(
        help="add role",
        description="add role",
        arguments=ARGS(
            [
                (["name"], {"help": "role name", "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": "role description",
                        "action": "store",
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
        uri = "%s/roles" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "add role %s" % res["uuid"]})

    @ex(
        help="update role",
        description="update role",
        arguments=ARGS(
            [
                (["id"], {"help": "role uuid", "action": "store", "type": str}),
                (
                    ["-name"],
                    {
                        "help": "role name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "role description",
                        "action": "store",
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
        uri = "%s/roles/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "update role %s" % oid})

    @ex(
        help="delete role",
        description="delete role",
        arguments=ARGS(
            [
                (["id"], {"help": "role uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = "%s/roles/%s" % (self.baseuri, oid)
        self.cmp_delete(uri, entity="role %s" % oid)

    @ex(
        help="expire role",
        description="expire role",
        arguments=ARGS(
            [
                (["id"], {"help": "role uuid", "action": "store", "type": str}),
                (
                    ["-days"],
                    {
                        "help": "role name",
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
        uri = "%s/roles/%s/expire/%s" % (self.baseuri, oid, days)
        self.cmp_delete(uri, entity="role %s" % oid, output=False)

    @ex(
        help="get permissions of role",
        description="get permissions of role",
        example="beehive auth roles get-perms <uuid> -size 50;beehive auth roles get-perms <uuid>",
        arguments=PARGS(
            [
                (["id"], {"help": "role uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def get_perms(self):
        oid = self.app.pargs.id
        params = []
        data = self.format_paginated_query(params)
        data += "&role=%s" % oid
        uri = "%s/objects/perms" % self.baseuri
        res = self.cmp_get(uri, data=data)
        self.app.render(
            res,
            key="perms",
            headers=self._meta.perm_headers,
            fields=self._meta.perm_fields,
        )

    @ex(
        help="add permissions to role",
        description="add permissions to role",
        arguments=ARGS(
            [
                (["id"], {"help": "role uuid", "action": "store", "type": str}),
                (
                    ["perms"],
                    {
                        "help": "comma separated list of permission id",
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
        uri = "%s/roles/%s" % (self.baseuri, oid)
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": "add perm %s to role %s" % (res["perm_append"], oid)})

    @ex(
        help="delete permissions from role",
        description="delete permissions from role",
        arguments=ARGS(
            [
                (["id"], {"help": "role uuid", "action": "store", "type": str}),
                (
                    ["perms"],
                    {
                        "help": "comma separated list of permission id",
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
        uri = "%s/roles/%s" % (self.baseuri, oid)
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": "delete perm %s from role %s" % (res["perm_remove"], oid)})

    @ex(
        help="Use role",
        description="Modify session permission to role permission. ",
        arguments=ARGS(
            [
                (["roleid"], {"help": "role uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def use_role(self):
        oid = self.app.pargs.roleid
        uri = "%s/roles/use/%s" % (self.baseuri, oid)
        self.cmp_get(uri)
        self.app.render({"msg": f"set current session to role {oid} permission"})

    @ex(
        help="reset permissions to full user permission",
        description="Modify reset current sessione to full user permissions",
        arguments=ARGS([]),
    )
    def reset_role(self):
        uri = "%s/roles/reset" % (self.baseuri)
        self.cmp_get(uri)
        self.app.render({"msg": "reset permissions to full user permission"})
