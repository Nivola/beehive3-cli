# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from urllib.parse import urlencode, quote
from cement import ex
from beehive3_cli.core.controller import PARGS, ARGS, StringAction
from beehive3_cli.plugins.auth.controllers.auth import AuthChildController
from beehive3_cli.translate import _


class AuthObjectController(AuthChildController):
    class Meta:
        stacked_on = "auth"
        stacked_type = "nested"
        label = "perms"
        description = _("permission management")
        help = _("permission management")

    @ex(
        help=_("list permissions"),
        arguments=PARGS(
            [
                (
                    ["-objid"],
                    {
                        "help": _("autorization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subsystem"],
                    {
                        "help": _("subsystem (service, ssh...)"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-cascade"],
                    {
                        "action": "store_true",
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def list(self):
        data = self.format_paginated_query(["objid", "cascade", "subsystem"])
        uri = f"{self.baseuri}/objects/perms"
        perms = self.cmp_get(uri, data=data)
        self.app.render(
            perms,
            key="perms",
            headers=["object-id", "objid", "subsystem", "type", "permission-id", "action-id", "action", "desc"],
            fields=["oid", "objid", "subsystem", "type", "id", "aid", "action", "desc"],
        )

    @ex(
        help=_("get permission"),
        description=_("get permission"),
        example="beehive auth perms get ######",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("permission id"),
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
        uri = f"{self.baseuri}/objects/perms/{oid}"
        res = self.cmp_get(uri)

        if self.is_output_text():
            self.app.render(res, key="perm", details=True)

            # get roles
            data = urlencode({"perms.N": oid, "size": -1})
            uri = f"{self.baseuri}/roles"
            roles = self.cmp_get(uri, data).get("roles")

            # get users
            data = urlencode({"perms.N": oid, "size": -1})
            uri = f"{self.baseuri}/users"
            users = self.cmp_get(uri, data).get("users")

            # get groups
            data = urlencode({"perms.N": oid, "size": -1})
            uri = f"{self.baseuri}/groups"
            groups = self.cmp_get(uri, data).get("groups")

            self.print_section_heading("roles")
            self.app.render(roles, headers=self._meta.role_headers, fields=self._meta.role_fields)
            self.print_section_heading("groups")
            self.app.render(groups, headers=self._meta.group_headers, fields=self._meta.group_fields)
            self.print_section_heading("users")
            self.app.render(users, headers=self._meta.user_headers, fields=self._meta.user_fields)
        else:
            self.app.render(res, key="perm", details=True)

    @ex(
        help=_("get object actions"),
        description=_("get object actions"),
        example="beehive auth perms get-actions",
    )
    def get_actions(self):
        uri = f"{self.baseuri}/objects/actions"
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="object_actions",
            headers=self._meta.act_headers,
            fields=self._meta.act_fields,
        )

    @ex(
        help=_("get object types"),
        description=_("get object types"),
        example="beehive auth perms get-types -size 50",
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
                    ["-subsystem"],
                    {
                        "help": _("subsystem"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {"help": _("type"), "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def get_types(self):
        uri = f"{self.baseuri}/objects/types"
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
        help=_("add object type"),
        description=_("add object type"),
        arguments=PARGS(
            [
                (
                    ["subsystem"],
                    {
                        "help": _("subsystem"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["type"],
                    {"help": _("type"), "action": "store", "type": str, "default": None},
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
        uri = f"{self.baseuri}/objects/types"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add object type: {res}"})

    @ex(
        help=_("delete object type"),
        description=_("delete object type"),
        arguments=ARGS(
            [
                (["id"], {"help": _("object type uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def del_type(self):
        object_id = self.app.pargs.id
        uri = f"{self.baseuri}/objects/types/{object_id}"
        self.cmp_delete(uri)
        self.app.render({"msg": f"delete object type {object_id}"})

    @ex(
        help=_("get objects"),
        description=_("get objects"),
        example="beehive auth perms get-objects -objid #####; beehive auth perms get-objects -group GR-xxxx",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("object id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": _("autorization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subsystem"],
                    {
                        "help": _("subsystem"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {"help": _("type"), "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def get_objects(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/objects/{oid}"
            res = self.cmp_get(uri)

            # get perms
            data = "oid=" + oid
            uri = f"{self.baseuri}/objects/perms"
            perms = self.cmp_get(uri, data=data).get("perms")

            if self.is_output_text():
                self.app.render(res, key="object", details=True)
                self.print_section_heading("permissions")
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
            uri = f"{self.baseuri}/objects"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="objects",
                headers=self._meta.obj_headers,
                fields=self._meta.obj_fields,
            )

    @ex(
        help=_("get method"),
        description=_("get method"),
        arguments=PARGS(
            [
                (
                    ["rule"],
                    {
                        "help": _("method url/rule "),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subsystem"],
                    {
                        "help": _("subsystem"),
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
        uri = f"{self.baseuri}/objects"
        res = self.cmp_get(uri, data=data)

        os = res["objects"]
        if len(os) > 0:
            oid = os[0]["id"]
            uri = f"{self.baseuri}/objects/{oid}"
            res = self.cmp_get(uri)

            # get perms
            data = f"oid={oid}"
            uri = f"{self.baseuri}/objects/perms"
            perms = self.cmp_get(uri, data=data).get("perms")

            if self.is_output_text():
                self.app.render(res, key="object", details=True)
                self.print_section_heading("permissions")
                self.app.render(
                    perms,
                    headers=["permission-id", "action-id", "action"],
                    fields=["id", "aid", "action"],
                )
            else:
                self.app.render(res, key="object", details=True)

    @ex(
        help=_("add object"),
        description=_("add object"),
        arguments=ARGS(
            [
                (
                    ["desc"],
                    {
                        "help": _("user description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": "",
                    },
                ),
                (
                    ["objid"],
                    {
                        "help": _("autorization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["subsystem"],
                    {
                        "help": _("subsystem"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["type"],
                    {"help": _("type"), "action": "store", "type": str, "default": None},
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
        uri = f"{self.baseuri}/objects"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add object {res}"})

    @ex(
        help=_("delete object"),
        description=_("delete object"),
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": _("comma separated list of object id"),
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
            uri = f"{self.baseuri}/objects/{oid}"
            self.cmp_delete(uri, entity=f"object {oid}")
