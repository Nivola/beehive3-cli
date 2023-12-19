# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from urllib.parse import urlencode, quote
from cement import ex
from beehive3_cli.core.controller import PARGS, ARGS, StringAction
from beehive3_cli.plugins.auth.controllers.auth import AuthChildController


class AuthObjectController(AuthChildController):
    class Meta:
        stacked_on = "auth"
        stacked_type = "nested"
        label = "perms"
        description = "permission management"
        help = "permission management"

    @ex(
        help="get permission",
        description="get permission",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "permission id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        uri = "%s/objects/perms/%s" % (self.baseuri, oid)
        res = self.cmp_get(uri)

        if self.is_output_text():
            self.app.render(res, key="perm", details=True)

            # get roles
            data = urlencode({"perms.N": oid, "size": -1})
            uri = "%s/roles" % self.baseuri
            roles = self.cmp_get(uri, data).get("roles")

            # get users
            data = urlencode({"perms.N": oid, "size": -1})
            uri = "%s/users" % self.baseuri
            users = self.cmp_get(uri, data).get("users")

            # get groups
            data = urlencode({"perms.N": oid, "size": -1})
            uri = "%s/groups" % self.baseuri
            groups = self.cmp_get(uri, data).get("groups")

            self.c("\nroles", "underline")
            self.app.render(roles, headers=self._meta.role_headers, fields=self._meta.role_fields)
            self.c("\ngroups", "underline")
            self.app.render(groups, headers=self._meta.group_headers, fields=self._meta.group_fields)
            self.c("\nusers", "underline")
            self.app.render(users, headers=self._meta.user_headers, fields=self._meta.user_fields)
        else:
            self.app.render(res, key="perm", details=True)

    @ex(help="get object actions", description="get object actions")
    def get_actions(self):
        uri = "%s/objects/actions" % self.baseuri
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="object_actions",
            headers=self._meta.act_headers,
            fields=self._meta.act_fields,
        )

    @ex(
        help="get object types",
        description="get object types",
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
                    ["-subsystem"],
                    {
                        "help": "subsystem",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {"help": "type", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def get_types(self):
        uri = "%s/objects/types" % self.baseuri
        data = {
            "size": self.app.pargs.size,
            "page": self.app.pargs.page,
            "field": self.app.pargs.field,
            "order": self.app.pargs.order,
        }

        p = getattr(self.app.pargs, "subsystem", None)
        if p is not None:
            data["subsystem"] = p

        p = getattr(self.app.pargs, "type", None)
        if p is not None:
            data["type"] = p

        res = self.cmp_get(uri, data=data)
        self.app.render(
            res,
            key="object_types",
            headers=self._meta.type_headers,
            fields=self._meta.type_fields,
        )

    @ex(
        help="add object type",
        description="add object type",
        arguments=PARGS(
            [
                (
                    ["subsystem"],
                    {
                        "help": "subsystem",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["type"],
                    {"help": "type", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def add_type(self):
        data = {
            "object_types": [
                {
                    "subsystem": self.app.pargs.subsystem,
                    "type": self.app.pargs.type,
                }
            ]
        }
        uri = "%s/objects/types" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "add object type: %s" % res})

    @ex(
        help="delete object type",
        description="delete object type",
        arguments=ARGS(
            [
                (["id"], {"help": "object type uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def del_type(self):
        object_id = self.app.pargs.id
        uri = "%s/objects/types/%s" % (self.baseuri, object_id)
        self.cmp_delete(uri)
        self.app.render({"msg": "delete object type %s" % object_id})

    @ex(
        help="get objects",
        description="get objects",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "object id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": "autorization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subsystem"],
                    {
                        "help": "subsystem",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {"help": "type", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def get_objects(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = "%s/objects/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            # get perms
            data = "oid=" + oid
            uri = "%s/objects/perms" % self.baseuri
            perms = self.cmp_get(uri, data=data).get("perms")

            if self.is_output_text():
                self.app.render(res, key="object", details=True)
                self.c("\npermissions", "underline")
                self.app.render(
                    perms,
                    headers=["permission-id", "action-id", "action"],
                    fields=["id", "aid", "action"],
                )
            else:
                self.app.render(res, key="object", details=True)

        else:
            params = ["objid", "subsystem", "type"]
            data = self.format_paginated_query(params)
            uri = "%s/objects" % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="objects",
                headers=self._meta.obj_headers,
                fields=self._meta.obj_fields,
            )

    @ex(
        help="get method",
        description="get method",
        arguments=PARGS(
            [
                (
                    ["rule"],
                    {
                        "help": "method url/rule ",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subsystem"],
                    {
                        "help": "subsystem",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get_method(self):
        rule = getattr(self.app.pargs, "rule", "")
        from Crypto.Hash import SHA256

        objid = SHA256.new(bytes(rule, encoding="utf-8")).hexdigest()
        subsystem = getattr(self.app.pargs, "subsystem")
        if subsystem is None:
            subsystem = "service"
        data = f"objid={objid}&subsystem={subsystem}&type=ApiMethod"
        uri = "%s/objects" % self.baseuri
        res = self.cmp_get(uri, data=data)

        os = res["objects"]
        if len(os) > 0:
            oid = os[0]["id"]
            uri = "%s/objects/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            # get perms
            data = f"oid={oid}"
            uri = "%s/objects/perms" % self.baseuri
            perms = self.cmp_get(uri, data=data).get("perms")

            if self.is_output_text():
                self.app.render(res, key="object", details=True)
                self.c("\npermissions", "underline")
                self.app.render(
                    perms,
                    headers=["permission-id", "action-id", "action"],
                    fields=["id", "aid", "action"],
                )
            else:
                self.app.render(res, key="object", details=True)

    @ex(
        help="add object",
        description="add object",
        arguments=ARGS(
            [
                (
                    ["desc"],
                    {
                        "help": "user description",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": "",
                    },
                ),
                (
                    ["objid"],
                    {
                        "help": "autorization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["subsystem"],
                    {
                        "help": "subsystem",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["type"],
                    {"help": "type", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def add_object(self):
        data = {
            "objects": [
                {
                    "subsystem": self.app.pargs.subsystem,
                    "type": self.app.pargs.type,
                    "objid": self.app.pargs.objid,
                    "desc": self.app.pargs.desc,
                }
            ]
        }
        uri = "%s/objects" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "add object %s" % res})

    @ex(
        help="delete object",
        description="delete object",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": "comma separated list of object id",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def del_object(self):
        oids = self.app.pargs.ids.split(",")
        for oid in oids:
            print(oid)
            if oid.find(":") >= 0:
                oid = quote(oid)
                oid = oid.replace("//", "__")
            uri = "%s/objects/%s" % (self.baseuri, oid)
            self.cmp_delete(uri, entity="object %s" % oid)
