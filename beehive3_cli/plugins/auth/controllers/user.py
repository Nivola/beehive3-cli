# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from datetime import datetime, timedelta
from re import match
from urllib.parse import urlencode
from cement import ex
from beecell.simple import format_date
from beehive3_cli.core.controller import PARGS, ARGS, StringAction
from beehive3_cli.plugins.auth.controllers.auth import AuthChildController


class AuthUserController(AuthChildController):
    class Meta:
        stacked_on = "auth"
        stacked_type = "nested"
        label = "users"
        description = "users management"
        help = "users management"

    @ex(
        help="get users",
        description="get users",
        example="beehive auth users get -group GR-xxxx;beehive auth users get -id <uuid>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "user uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": "role uuid",
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
                    ["-name"],
                    {
                        "help": "name filter",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "user desc",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": "email address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-taxcode"],
                    {
                        "help": "taxcode",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ldap"],
                    {
                        "help": "ldap address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-expiry-date"],
                    {
                        "help": "expiry date. Syntax YYYY-MM-DD",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-perms"],
                    {
                        "help": "comma separated list of permission id",
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
            uri = "%s/users/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                self.app.render(res, key="user", details=True)

                # get roles
                data = urlencode({"user": oid, "size": -1})
                uri = "%s/roles" % self.baseuri
                roles = self.cmp_get(uri, data).get("roles")
                self.c("\nroles", "underline")
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
                uri = "%s/groups" % self.baseuri
                groups = self.cmp_get(uri, data).get("groups")
                self.c("\ngroups", "underline")
                self.app.render(
                    groups,
                    headers=self._meta.group_headers,
                    fields=self._meta.group_fields,
                )

                # get attributes
                uri = "%s/users/%s/attributes" % (self.baseuri, oid)
                attribs = self.cmp_get(uri).get("user_attributes", [])
                self.c("\nattributes", "underline")
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
            uri = "%s/users" % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="users",
                headers=self._meta.user_headers,
                fields=self._meta.user_fields,
            )

    @ex(
        help="add user",
        description="add user",
        example="beehive auth users add abc.def@ghi.lmno -storetype LDAPUSER -email abc.def@ghi.lmno -desc 'Abc Def';beehive auth users add abc.def@ghi.lmno -storetype LDAPUSER -email abc.def@ghi.lmno -desc Abc_Def",
        arguments=ARGS(
            [
                (["name"], {"help": "user name", "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": "user description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": "",
                    },
                ),
                (
                    ["-storetype"],
                    {
                        "help": "can be DBUSER, LDAPUSER",
                        "action": "store",
                        "type": str,
                        "default": "DBUSER",
                    },
                ),
                (
                    ["-password"],
                    {
                        "help": "user password. Set only for DBUSER",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-expirydate"],
                    {
                        "help": "user expire date. Syntax yyyy-mm-dd",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": "email address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-taxcode"],
                    {
                        "help": "taxcode",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ldap"],
                    {
                        "help": "ldap address",
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

        if name is not None and not match("[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", name):
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
            if not match("[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", email):
                raise Exception("email is not correct. Email syntax is <name>@<domain>")
            data["user"]["email"] = email

        if taxcode is not None:
            data["user"]["taxcode"] = taxcode

        if ldap is not None:
            if not match("[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", ldap):
                raise Exception("ldap is not correct. Ldap syntax is <name>@<domain>")
            data["user"]["ldap"] = ldap

        uri = "%s/users" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "add user %s" % res["uuid"]})

    @ex(
        help="add system user",
        description="add system user",
        arguments=ARGS(
            [
                (["name"], {"help": "user name", "action": "store", "type": str}),
                (
                    ["password"],
                    {
                        "help": "user password. Set only for DBUSER",
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
                "desc": "User %s" % self.app.pargs.name,
                "system": True,
            }
        }
        uri = "%s/users" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "add user %s" % res["uuid"]})

    @ex(
        help="update user",
        description="update user",
        arguments=ARGS(
            [
                (["id"], {"help": "user uuid", "action": "store", "type": str}),
                (
                    ["-name"],
                    {
                        "help": "user name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "user description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-active"],
                    {
                        "help": "user active",
                        "action": "store",
                        "type": bool,
                        "default": True,
                    },
                ),
                (
                    ["-provider"],
                    {
                        "help": "authentication provider",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-password"],
                    {
                        "help": "user password. Set only for DBUSER",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-expirydate"],
                    {
                        "help": "user expire date. Syntax yyyy-mm-dd",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": "email address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-taxcode"],
                    {
                        "help": "taxcode (codice fiscale)",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ldap"],
                    {
                        "help": "ldap (servizi rete)",
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
        if name is not None and not match("[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", name):
            raise Exception("name is not correct. Name syntax is <name>@<domain>")

        email = self.app.pargs.email
        if email is not None and not match("[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", email):
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
            if not match("[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", ldap):
                raise Exception("ldap is not correct. Ldap syntax is <name>@<domain>")
            data_user.update(
                {
                    "ldap": ldap,
                }
            )

        data = {"user": data_user}
        uri = "%s/users/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "update user %s" % oid})

    @ex(
        help="delete user",
        description="delete user",
        example="beehive auth users delete <uuid>;beehive auth users delete abc.def@ghi.lmn ",
        arguments=ARGS(
            [
                (["id"], {"help": "user uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = "%s/users/%s" % (self.baseuri, oid)
        self.cmp_delete(uri, entity="user %s" % oid)

    @ex(
        help="get user secret",
        description="get user secret",
        example="beehive auth users get-secret <uuid> -e <env> ",
        arguments=ARGS(
            [
                (["id"], {"help": "user uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def get_secret(self):
        oid = self.app.pargs.id
        uri = "%s/users/%s/secret" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key="user", headers=["secret"], details=True, maxsize=200)

    @ex(
        help="add role to user",
        description="add role to user",
        arguments=ARGS(
            [
                (["id"], {"help": "user uuid", "action": "store", "type": str}),
                (["role"], {"help": "role uuid", "action": "store", "type": str}),
                (
                    ["-expirydate"],
                    {
                        "help": "user expire date. Syntax yyyy-mm-dd",
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
        uri = "%s/users/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "add role %s to user %s" % (role, oid)})

    @ex(
        help="delete role from user",
        description="delete role from user",
        arguments=ARGS(
            [
                (["id"], {"help": "user uuid", "action": "store", "type": str}),
                (["role"], {"help": "role uuid", "action": "store", "type": str}),
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
        uri = "%s/users/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "del role %s from user %s" % (role, oid)})

    @ex(
        help="add group to user",
        description="add group to user",
        arguments=ARGS(
            [
                (["id"], {"help": "user uuid", "action": "store", "type": str}),
                (["group"], {"help": "group uuid", "action": "store", "type": str}),
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
        uri = "%s/groups/%s" % (self.baseuri, group)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "add group %s to user %s" % (group, oid)})

    @ex(
        help="delete group from user",
        description="delete group from user",
        arguments=ARGS(
            [
                (["id"], {"help": "user uuid", "action": "store", "type": str}),
                (["group"], {"help": "group uuid", "action": "store", "type": str}),
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
        uri = "%s/groups/%s" % (self.baseuri, group)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "del group %s from user %s" % (group, oid)})

    @ex(
        help="get permissions of user",
        description="get permissions of user",
        example="beehive auth users get-perms client_abc.def@ghi.lmno;beehive auth users get-perms clientabc.def@ghi.lmno",
        arguments=PARGS(
            [
                (["id"], {"help": "user uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def get_perms(self):
        oid = self.app.pargs.id
        params = []
        data = self.format_paginated_query(params)
        data += "&user=%s" % oid
        uri = "%s/objects/perms" % self.baseuri
        res = self.cmp_get(uri, data=data)
        self.app.render(
            res,
            key="perms",
            headers=self._meta.perm_headers,
            fields=self._meta.perm_fields,
        )

    @ex(
        help="add permissions to user",
        description="add permissions to user",
        example="beehive auth users add-perms abc.def@ghi.lmno <uuid>",
        arguments=ARGS(
            [
                (["id"], {"help": "user uuid", "action": "store", "type": str}),
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
            "user": {
                "perms": {"append": perms, "remove": []},
            }
        }
        uri = "%s/users/%s" % (self.baseuri, oid)
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": "add perm %s to user %s" % (res["perm_append"], oid)})

    @ex(
        help="delete permissions from user",
        description="delete permissions from user",
        arguments=ARGS(
            [
                (["id"], {"help": "user uuid", "action": "store", "type": str}),
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
            "user": {
                "perms": {"append": [], "remove": perms},
            }
        }
        uri = "%s/users/%s" % (self.baseuri, oid)
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": "delete perm %s from user %s" % (res["perm_remove"], oid)})

    @ex(
        help="add attribute to user",
        description="add attribute to user",
        arguments=ARGS(
            [
                (["id"], {"help": "user uuid", "action": "store", "type": str}),
                (
                    ["attrib"],
                    {"help": "attribute name", "action": "store", "type": str},
                ),
                (
                    ["value"],
                    {"help": "attribute value", "action": "store", "type": str},
                ),
                (
                    ["desc"],
                    {"help": "attribute description", "action": "store", "type": str},
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
        uri = "%s/users/%s/attributes" % (self.baseuri, oid)
        self.cmp_post(uri, data=data)
        self.app.render({"msg": "dd/update user %s attrib %s" % (oid, attrib)})

    @ex(
        help="delete attribute from user",
        description="delete attribute from user",
        arguments=ARGS(
            [
                (["id"], {"help": "user uuid", "action": "store", "type": str}),
                (
                    ["attrib"],
                    {"help": "attribute name", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def del_attrib(self):
        oid = self.app.pargs.id
        attrib = self.app.pargs.attrib
        uri = "%s/users/%s/attributes/%s" % (self.baseuri, oid, attrib)
        self.cmp_delete(uri)
        self.app.render({"msg": "delete user %s attrib %s" % (oid, attrib)})
