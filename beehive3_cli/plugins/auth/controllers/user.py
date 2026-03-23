# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from datetime import datetime, timedelta
from re import match
from urllib.parse import urlencode
from cement import ex

from beecell.simple import format_date
from beehive3_cli.core.controller import PARGS, ARGS, StringAction
from beehive3_cli.plugins.auth.controllers.auth import AuthChildController
from beehive3_cli.translate import _


class AuthUserController(AuthChildController):
    class Meta:
        stacked_on = "auth"
        stacked_type = "nested"
        label = "users"
        description = _("users management")
        help = _("users management")

    @ex(
        help=_("get users"),
        description=_("get users"),
        example="beehive auth users get -group GR-xxxx; beehive auth users get -id <uuid>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("user uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": _("role uuid"),
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
                        "help": _("user desc"),
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
                    ["-taxcode"],
                    {
                        "help": _("taxcode"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ldap"],
                    {
                        "help": _("ldap address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-expiry-date"],
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
                        "help": _("comma separated list of permission id"),
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
            uri = f"{self.baseuri}/users/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                self.app.render(res, key="user", details=True)

                # get roles
                data = urlencode({"user": oid, "size": -1})
                uri = f"{self.baseuri}/roles"
                roles = self.cmp_get(uri, data).get("roles")
                self.print_section_heading("roles")
                role_headers = [
                    "uuid",
                    "name",
                    "alias",
                    "active",
                    "creation",
                    "modified",
                    "expiry user relation",
                ]
                self.app.render(
                    roles,
                    headers=role_headers,
                    fields=self._meta.role_fields,
                )

                # get groups
                data = urlencode({"user": oid, "size": -1})
                uri = f"{self.baseuri}/groups"
                groups = self.cmp_get(uri, data).get("groups")
                self.print_section_heading("groups")
                self.app.render(
                    groups,
                    headers=self._meta.group_headers,
                    fields=self._meta.group_fields,
                )

                # get attributes
                uri = f"{self.baseuri}/users/{oid}/attributes"
                attribs = self.cmp_get(uri).get("user_attributes", [])
                self.print_section_heading("attributes")
                self.app.render(attribs, headers=["name", "value", "desc"])
            else:
                self.app.render(res, key="user", details=True)
        else:
            params = ["role", "group", "name", "desc", "expiry-date", "email", "taxcode", "ldap"]
            mappings = {
                "name": lambda n: "%" + n + "%",
                "desc": lambda n: "%" + n + "%",
            }
            data = self.format_paginated_query(params, mappings=mappings)
            if self.app.pargs.perms:
                ndata = {"perms.N": self.app.pargs.perms.split(",")}
                data += urlencode(ndata)
            uri = f"{self.baseuri}/users"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="users",
                headers=self._meta.user_headers,
                fields=self._meta.user_fields,
            )

    @ex(
        help=_("add user"),
        description=_("add user"),
        example=(
            "beehive auth users add abc.def@ghi.lmno -storetype LDAPUSER "
            "-email abc.def@ghi.lmno -desc Abc_Def"
        ),
        arguments=ARGS(
            [
                (["name"], {"help": _("user name"), "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": _("user description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": "",
                    },
                ),
                (
                    ["-storetype"],
                    {
                        "help": _("can be DBUSER, LDAPUSER"),
                        "action": "store",
                        "type": str,
                        "default": "DBUSER",
                    },
                ),
                (
                    ["-password"],
                    {
                        "help": _("user password. Set only for DBUSER"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-expirydate"],
                    {
                        "help": _("user expire date. Syntax yyyy-mm-dd"),
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
                    ["-taxcode"],
                    {
                        "help": _("taxcode"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ldap"],
                    {
                        "help": _("ldap address"),
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
        email = self.app.pargs.email
        taxcode = self.app.pargs.taxcode
        ldap = self.app.pargs.ldap

        if name is not None and not match(r"[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", name):
            raise Exception("name is not correct. Name syntax is <name>@<domain>")

        if self.app.pargs.expirydate is None:
            expirydate = datetime.today() + timedelta(days=365)
            expirydate = format_date(expirydate, format="%Y-%m-%d", microsec=False)
        else:
            expirydate = self.app.pargs.expirydate

        data = {
            "user": {
                "name": name,
                "active": True,
                "desc": self.app.pargs.desc,
                "base": True,
                "storetype": self.app.pargs.storetype,
                "expirydate": expirydate,
            }
        }
        if self.app.pargs.password is not None:
            data["user"]["password"] = self.app.pargs.password

        if email is not None:
            if not match(r"[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", email):
                raise Exception("email is not correct. Email syntax is <name>@<domain>")
            data["user"]["email"] = email

        if taxcode is not None:
            data["user"]["taxcode"] = taxcode

        if ldap is not None:
            if not match(r"[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", ldap):
                raise Exception("ldap is not correct. Ldap syntax is <name>@<domain>")
            data["user"]["ldap"] = ldap

        uri = f"{self.baseuri}/users"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add user {res['uuid']}"})

    @ex(
        help=_("add system user"),
        description=_("add system user"),
        arguments=ARGS(
            [
                (["name"], {"help": _("user name"), "action": "store", "type": str}),
                (
                    ["password"],
                    {
                        "help": _("user password. Set only for DBUSER"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def add_system(self):
        data = {
            "user": {
                "name": self.app.pargs.name,
                "active": True,
                "pwd": self.app.pargs.password,
                "desc": f"User {self.app.pargs.name}",
                "system": True,
            }
        }
        uri = f"{self.baseuri}/users"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add user {res['uuid']}"})

    @ex(
        help=_("update user"),
        description=_("update user"),
        arguments=ARGS(
            [
                (["id"], {"help": _("user uuid"), "action": "store", "type": str}),
                (
                    ["-name"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("user description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-active"],
                    {
                        "help": _("user active"),
                        "action": "store",
                        "type": bool,
                        "default": True,
                    },
                ),
                (
                    ["-provider"],
                    {
                        "help": _("authentication provider"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-password"],
                    {
                        "help": _("user password. Set only for DBUSER"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-expirydate"],
                    {
                        "help": _("user expire date. Syntax yyyy-mm-dd"),
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
                    ["-taxcode"],
                    {
                        "help": _("taxcode (codice fiscale)"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ldap"],
                    {
                        "help": _("ldap (servizi rete)"),
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

        name = self.app.pargs.name
        if name is not None and not match(r"[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", name):
            raise Exception("name is not correct. Name syntax is <name>@<domain>")

        email = self.app.pargs.email
        if email is not None and not match(r"[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", email):
            raise Exception("email is not correct. Email syntax is <name>@<domain>")

        taxcode = self.app.pargs.taxcode
        ldap = self.app.pargs.ldap

        data_user = {
            "name": name,
            "desc": self.app.pargs.desc,
            "active": self.app.pargs.active,
            "password": self.app.pargs.password,
            "expiry_date": self.app.pargs.expirydate,
        }
        if email is not None:
            data_user.update(
                {
                    "email": email,
                }
            )

        if taxcode is not None:
            data_user.update(
                {
                    "taxcode": taxcode,
                }
            )

        if ldap is not None:
            if not match(r"[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", ldap):
                raise Exception("ldap is not correct. Ldap syntax is <name>@<domain>")
            data_user.update(
                {
                    "ldap": ldap,
                }
            )

        data = {"user": data_user}
        uri = f"{self.baseuri}/users/{oid}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update user {oid}"})

    @ex(
        help=_("delete user"),
        description=_("delete user"),
        example="beehive auth users delete <uuid>; beehive auth users delete abc.def@ghi.lmn ",
        arguments=ARGS(
            [
                (["id"], {"help": _("user uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/users/{oid}"
        self.cmp_delete(uri, entity=f"user {oid}")

    @ex(
        help=_("get user secret"),
        description=_("get user secret"),
        example="beehive auth users get-secret <uuid> -e <env> ",
        arguments=ARGS(
            [
                (["id"], {"help": _("user uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def get_secret(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/users/{oid}/secret"
        res = self.cmp_get(uri)
        self.app.render(res, key="user", headers=["secret"], details=True, maxsize=200)

    @ex(
        help=_("add role to user"),
        description=_("add role to user"),
        arguments=ARGS(
            [
                (["id"], {"help": _("user uuid"), "action": "store", "type": str}),
                (["role"], {"help": _("role uuid"), "action": "store", "type": str}),
                (
                    ["-expirydate"],
                    {
                        "help": _("user expire date. Syntax yyyy-mm-dd"),
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
            "user": {
                "roles": {"append": [(role, expirydate)], "remove": []},
            }
        }
        uri = f"{self.baseuri}/users/{oid}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add role {role} to user {oid}"})

    @ex(
        help=_("delete role from user"),
        description=_("delete role from user"),
        arguments=ARGS(
            [
                (["id"], {"help": _("user uuid"), "action": "store", "type": str}),
                (["role"], {"help": _("role uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def del_role(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        data = {
            "user": {
                "roles": {"append": [], "remove": [role]},
            }
        }
        uri = f"{self.baseuri}/users/{oid}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"del role {role} from user {oid}"})

    @ex(
        help=_("add group to user"),
        description=_("add group to user"),
        arguments=ARGS(
            [
                (["id"], {"help": _("user uuid"), "action": "store", "type": str}),
                (["group"], {"help": _("group uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def add_group(self):
        oid = self.app.pargs.id
        group = self.app.pargs.group

        data = {
            "group": {
                "users": {"append": [oid], "remove": []},
            }
        }
        uri = f"{self.baseuri}/groups/{group}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add group {group} to user {oid}"})

    @ex(
        help=_("delete group from user"),
        description=_("delete group from user"),
        arguments=ARGS(
            [
                (["id"], {"help": _("user uuid"), "action": "store", "type": str}),
                (["group"], {"help": _("group uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def del_group(self):
        oid = self.app.pargs.id
        group = self.app.pargs.group
        data = {
            "group": {
                "users": {"append": [], "remove": [oid]},
            }
        }
        uri = f"{self.baseuri}/groups/{group}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"del group {group} from user {oid}"})

    @ex(
        help=_("get permissions of user"),
        description=_("get permissions of user"),
        example="beehive auth users get-perms clientabc.def@ghi.lmno",
        arguments=PARGS(
            [
                (["id"], {"help": _("user uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def get_perms(self):
        oid = self.app.pargs.id
        params = []
        data = self.format_paginated_query(params)
        data += f"&user={oid}"
        uri = f"{self.baseuri}/objects/perms"
        res = self.cmp_get(uri, data=data)
        self.app.render(
            res,
            key="perms",
            headers=self._meta.perm_headers,
            fields=self._meta.perm_fields,
        )

    @ex(
        help=_("add permissions to user"),
        description=_("add permissions to user"),
        example="beehive auth users add-perms abc.def@ghi.lmno <uuid>",
        arguments=ARGS(
            [
                (["id"], {"help": _("user uuid"), "action": "store", "type": str}),
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
            "user": {
                "perms": {"append": perms, "remove": []},
            }
        }
        uri = f"{self.baseuri}/users/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add perm {res['perm_append']} to user {oid}"})

    @ex(
        help=_("delete permissions from user"),
        description=_("delete permissions from user"),
        arguments=ARGS(
            [
                (["id"], {"help": _("user uuid"), "action": "store", "type": str}),
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
            "user": {
                "perms": {"append": [], "remove": perms},
            }
        }
        uri = f"{self.baseuri}/users/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"delete perm {res['perm_remove']} from user {oid}"})

    @ex(
        help=_("add attribute to user"),
        description=_("add attribute to user"),
        arguments=ARGS(
            [
                (["id"], {"help": _("user uuid"), "action": "store", "type": str}),
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
            "user_attribute": {
                "name": attrib,
                "value": self.app.pargs.value,
                "desc": self.app.pargs.desc,
            }
        }
        uri = f"{self.baseuri}/users/{oid}/attributes"
        self.cmp_post(uri, data=data)
        self.app.render({"msg": f"dd/update user {oid} attrib {attrib}"})

    @ex(
        help=_("delete attribute from user"),
        description=_("delete attribute from user"),
        arguments=ARGS(
            [
                (["id"], {"help": _("user uuid"), "action": "store", "type": str}),
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
        uri = f"{self.baseuri}/users/{oid}/attributes/{attrib}"
        self.cmp_delete(uri)
        self.app.render({"msg": f"delete user {oid} attrib {attrib}"})
