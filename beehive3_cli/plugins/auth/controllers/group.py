# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from datetime import datetime, timedelta
from urllib.parse import urlencode
from cement import ex

from beecell.simple import format_date
from beehive3_cli.core.controller import PARGS, ARGS, StringAction
from beehive3_cli.plugins.auth.controllers.auth import AuthChildController
from beehive3_cli.translate import _


class AuthGroupController(AuthChildController):

    class Meta: # type: ignore
        stacked_on = "auth"
        stacked_type = "nested"
        label = "groups"
        description = _("groups management")
        help = _("groups management")

    @ex(
        help=_("get groups"),
        description=_("get groups"),
        example="beehive auth groups get -id Group1Role; beehive auth groups get -name xxxxx",
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
                    ["-role"],
                    {
                        "help": _("role id or name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-user"],
                    {
                        "help": _("user id or name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("name filter"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("group desc"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": _("email address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-expiry-date "],
                    {
                        "help": _("expiry date. Syntax YYYY-MM-DD"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-perms"],
                    {
                        "help": _("rcomma separated list of permissions"),
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
            uri = f"{self.baseuri}/groups/{oid}"
            res = self.cmp_get(uri)

            # get roles
            data = urlencode({"group": oid, "size": -1})
            uri = f"{self.baseuri}/roles"
            roles = self.cmp_get(uri, data).get("roles")

            # get users
            data = urlencode({"group": oid, "size": -1})
            uri = f"{self.baseuri}/users"
            users = self.cmp_get(uri, data).get("users")

            if self.is_output_text():
                self.app.render(res, key="group", details=True)
                self.print_section_heading("roles")
                # headers and fields read from parent class's inner Meta
                self.app.render(
                    roles,
                    headers=self._meta.role_headers, # type: ignore
                    fields=self._meta.role_fields, # type: ignore
                )
                self.print_section_heading("users")
                self.app.render(
                    users,
                    headers=self._meta.user_headers, # type: ignore
                    fields=self._meta.user_fields, # type: ignore
                )
            else:
                self.app.render(res, key="group", details=True)
        else:
            params = ["user", "role", "name", "desc", "expiry-date"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            if self.app.pargs.perms:
                ndata = {"perms.N": self.app.pargs.perms.split(",")}
                data += urlencode(ndata)
            uri = f"{self.baseuri}/groups"
            res = self.cmp_get(uri, data=data)
            # headers and fields read from parent class's inner Meta
            self.app.render(
                res,
                key="groups",
                headers=self._meta.group_headers, # type: ignore
                fields=self._meta.group_fields, # type: ignore
            )

    @ex(
        help=_("add group"),
        description=_("add group"),
        example="beehive auth groups add-user GR-xxxx abc.def@ghi.lmno",
        arguments=ARGS(
            [
                (["name"], {"help": _("group name"), "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": _("group description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": "",
                    },
                ),
                (
                    ["-expirydate"],
                    {
                        "help": _("group expire date. Syntax yyyy-mm-dd"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add(self):
        name = self.app.pargs.name

        if self.app.pargs.expirydate is None:
            expirydate = datetime.today() + timedelta(days=365)
        else:
            expirydate = self.app.pargs.expirydate
        expirydate = format_date(expirydate, format="%Y-%m-%d", microsec=False)

        data = {
            "group": {
                "name": name,
                "active": True,
                "desc": self.app.pargs.desc,
                "expirydate": expirydate,
            }
        }
        uri = f"{self.baseuri}/groups"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add group {res['uuid']}"})

    @ex(
        help=_("update group"),
        description=_("update group"),
        arguments=ARGS(
            [
                (["id"], {"help": _("group uuid"), "action": "store", "type": str}),
                (
                    ["-name"],
                    {
                        "help": _("group name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("group description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-active"],
                    {
                        "help": _("group active"),
                        "action": "store",
                        "type": bool,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.id

        data = {
            "group": {
                "name": self.app.pargs.name,
                "desc": self.app.pargs.desc,
                "active": self.app.pargs.active,
            }
        }
        uri = f"{self.baseuri}/groups/{oid}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update group {oid}"})

    @ex(
        help=_("delete group"),
        description=_("delete group"),
        arguments=ARGS(
            [
                (["id"], {"help": _("group uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/groups/{oid}"
        self.cmp_delete(uri, entity=f"group {oid}")

    @ex(
        help=_("add role to group"),
        description=_("add role to group"),
        arguments=ARGS(
            [
                (["id"], {"help": _("group uuid"), "action": "store", "type": str}),
                (["role"], {"help": _("role uuid"), "action": "store", "type": str}),
                (
                    ["-expirydate"],
                    {
                        "help": _("group expire date. Syntax yyyy-mm-dd"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add_role(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role

        if self.app.pargs.expirydate is None:
            expirydate = datetime.today() + timedelta(days=365)
        else:
            expirydate = self.app.pargs.expirydate
        expirydate = format_date(expirydate, format="%Y-%m-%d", microsec=False)

        data = {
            "group": {
                "roles": {"append": [(role, expirydate)], "remove": []},
            }
        }
        uri = f"{self.baseuri}/groups/{oid}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add role {role} to group {oid}"})

    @ex(
        help=_("delete role from group"),
        description=_("delete role from group"),
        arguments=ARGS(
            [
                (["id"], {"help": _("group uuid"), "action": "store", "type": str}),
                (["role"], {"help": _("role uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def del_role(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        data = {
            "group": {
                "roles": {"append": [], "remove": [role]},
            }
        }
        uri = f"{self.baseuri}/groups/{oid}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"del role {role} from group {oid}"})

    @ex(
        help=_("add user to group"),
        description=_("add user to group"),
        example="beehive auth groups add-user GR-xxxx abc.def@ghi.lmno",
        arguments=ARGS(
            [
                (["id"], {"help": _("group uuid"), "action": "store", "type": str}),
                (["user"], {"help": _("user uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def add_user(self):
        oid = self.app.pargs.id
        user = self.app.pargs.user

        data = {
            "group": {
                "users": {"append": [user], "remove": []},
            }
        }
        uri = f"{self.baseuri}/groups/{oid}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add user {user} to group {oid}"})

    @ex(
        help=_("delete user from group"),
        description=_("delete user from group"),
        example="beehive auth groups del-user GR-xxxx uuid",
        arguments=ARGS(
            [
                (["id"], {"help": _("group uuid"), "action": "store", "type": str}),
                (["user"], {"help": _("user uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def del_user(self):
        oid = self.app.pargs.id
        user = self.app.pargs.user
        data = {
            "group": {
                "users": {"append": [], "remove": [user]},
            }
        }
        uri = f"{self.baseuri}/groups/{oid}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"del user {user} from group {oid}"})

    @ex(
        help=_("get permissions of group"),
        description=_("get permissions of group"),
        example="beehive auth groups get-perms GR-xxxx; beehive auth groups get-perms #####",
        arguments=PARGS(
            [
                (["id"], {"help": _("group uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def get_perms(self):
        oid = self.app.pargs.id
        params = []
        data = self.format_paginated_query(params)
        data += f"&group={oid}"
        uri = f"{self.baseuri}/objects/perms"
        res = self.cmp_get(uri, data=data)
        self.app.render(
            res,
            key="perms",
            headers=self._meta.perm_headers,
            fields=self._meta.perm_fields,
        )

    @ex(
        help=_("add permissions to group"),
        description=_("add permissions to group"),
        example="beehive auth groups add-perms GR-xxxx ##### ",
        arguments=ARGS(
            [
                (["id"], {"help": _("group uuid"), "action": "store", "type": str}),
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
            "group": {
                "perms": {"append": perms, "remove": []},
            }
        }
        uri = f"{self.baseuri}/groups/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add perm {res['perm_append']} to group {oid}"})

    @ex(
        help=_("delete permissions from group"),
        description=_("delete permissions from group"),
        arguments=ARGS(
            [
                (["id"], {"help": _("group uuid"), "action": "store", "type": str}),
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
            "group": {
                "perms": {"append": [], "remove": perms},
            }
        }
        uri = f"{self.baseuri}/groups/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"delete perm {res['perm_remove']} from group {oid}"})

    @ex(
        help=_("add attribute to group"),
        description=_("add attribute to group"),
        arguments=ARGS(
            [
                (["id"], {"help": _("group uuid"), "action": "store", "type": str}),
                (
                    ["attrib"],
                    {"help": _("attribute name"), "action": "store", "type": str},
                ),
                (
                    ["value"],
                    {"help": _("attribute value"), "action": "store", "type": str},
                ),
                (
                    ["desc"],
                    {"help": _("attribute description"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def add_attrib(self):
        oid = self.app.pargs.id
        attrib = self.app.pargs.attrib
        data = {
            "group_attribute": {
                "name": attrib,
                "value": self.app.pargs.value,
                "desc": self.app.pargs.desc,
            }
        }
        uri = f"{self.baseuri}/groups/{oid}/attributes"
        self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add/update group {oid} attrib {attrib}"})

    @ex(
        help=_("delete attribute from group"),
        description=_("delete attribute from group"),
        arguments=ARGS(
            [
                (["id"], {"help": _("group uuid"), "action": "store", "type": str}),
                (
                    ["attrib"],
                    {"help": _("attribute name"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def del_attrib(self):
        oid = self.app.pargs.id
        attrib = self.app.pargs.attrib
        uri = f"{self.baseuri}/groups/{oid}/attributes/{attrib}"
        self.cmp_delete(uri)
        self.app.render({"msg": f"delete group {oid} attrib {attrib}"})
