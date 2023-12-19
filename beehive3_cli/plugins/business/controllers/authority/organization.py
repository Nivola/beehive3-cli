# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from cement import ex
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.business.controllers.authority import AuthorityControllerChild


class OrganizationController(AuthorityControllerChild):
    class Meta:
        label = "orgs"
        description = "organization management"
        help = "organization management"

        headers = ["uuid", "name", "type", "divisions", "anagrafica", "status", "date"]
        fields = [
            "uuid",
            "name",
            "org_type",
            "divisions",
            "ext_anag_id",
            "status",
            "date.creation",
        ]

    @ex(
        help="get organizations",
        description="get organizations",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "organization uuid",
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
                        "help": "organization name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-org-type"],
                    {
                        "help": "organization type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext-anag-id"],
                    {
                        "help": "organization ext_anag_id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": "organization attributes",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-hasvat"],
                    {
                        "help": "organization hasvat",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-partner"],
                    {
                        "help": "organization partner",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-referent"],
                    {
                        "help": "organization referent",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": "organization email",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-legalemail"],
                    {
                        "help": "organization legalemail",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-postaladdress"],
                    {
                        "help": "organization legalemail",
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
            uri = "%s/organizations/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                data = {"organization_id": oid, "size": -1}
                uri = "%s/divisions" % self.baseuri
                divs = self.cmp_get(uri, data=data).get("divisions", [])
                self.app.render(res, key="organization", details=True)
                self.c("\ndivisions", "underline")
                headers = [
                    "uuid",
                    "name",
                    "organization",
                    "accounts",
                    "contact",
                    "email",
                    "postaladdress",
                    "status",
                    "date",
                ]
                fields = [
                    "uuid",
                    "name",
                    "organization_name",
                    "accounts",
                    "contact",
                    "email",
                    "postaladdress",
                    "status",
                    "date.creation",
                ]
                self.app.render(divs, headers=headers, fields=fields)
            else:
                self.app.render(res, key="organization", details=True)
        else:
            params = [
                "name",
                "objid",
                "org_type",
                "ext_anag_id",
                "attributes",
                "hasvat",
                "partner",
                "referent",
                "email",
                "legalemail",
                "postaladdress",
            ]
            data = self.format_paginated_query(params)
            uri = "%s/organizations" % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="organizations",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    @ex(
        help="add organization",
        description="add organization",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "organization name", "action": "store", "type": str},
                ),
                (
                    ["-desc"],
                    {
                        "help": "organization description",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-attrib"],
                    {
                        "help": "organization attributes",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["orgtype"],
                    {"help": "organization type", "action": "store", "type": str},
                ),
                (
                    ["-hasvat"],
                    {
                        "help": "organization hasvat",
                        "action": "store",
                        "type": str,
                        "default": False,
                    },
                ),
                (
                    ["-ext-anag-id"],
                    {
                        "help": "organization ext_anag_id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-partner"],
                    {
                        "help": "organization partner",
                        "action": "store",
                        "type": str,
                        "default": False,
                    },
                ),
                (
                    ["-referent"],
                    {
                        "help": "organization referent",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": "organization email",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-legalemail"],
                    {
                        "help": "organization legalemail",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-postaladdress"],
                    {
                        "help": "organization legalemail",
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
            "organization": {
                "name": self.app.pargs.name,
                "desc": self.app.pargs.desc,
                "org_type": self.app.pargs.orgtype,
                "ext_anag_id": self.app.pargs.ext_anag_id,
                "attributes": self.app.pargs.attrib,
                "hasvat": self.app.pargs.hasvat,
                "partner": self.app.pargs.partner,
                "referent": self.app.pargs.referent,
                "email": self.app.pargs.email,
                "legalemail": self.app.pargs.legalemail,
                "postaladdress": self.app.pargs.postaladdress,
            }
        }
        uri = "%s/organizations" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "Add organization %s" % res})

    @ex(
        help="update organization",
        description="update organization",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "organization name", "action": "store", "type": str},
                ),
                (
                    ["-desc"],
                    {
                        "help": "organization description",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-attrib"],
                    {
                        "help": "organization attributes",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["org-type"],
                    {"help": "organization type", "action": "store", "type": str},
                ),
                (
                    ["-hasvat"],
                    {
                        "help": "organization hasvat",
                        "action": "store",
                        "type": str,
                        "default": False,
                    },
                ),
                (
                    ["-ext-anag-id"],
                    {
                        "help": "organization ext_anag_id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-partner"],
                    {
                        "help": "organization partner",
                        "action": "store",
                        "type": str,
                        "default": False,
                    },
                ),
                (
                    ["-referent"],
                    {
                        "help": "organization referent",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": "organization email",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-legalemail"],
                    {
                        "help": "organization legalemail",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-postaladdress"],
                    {
                        "help": "organization legalemail",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def update(self):
        """todo:"""
        oid = self.app.pargs.id
        params = self.app.kvargs
        data = {"organization": params}
        uri = "%s/organizations/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "Update resource %s with data %s" % (oid, params)})

    @ex(
        help="refresh organization",
        description="refresh organization",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "organization uuid or name",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def refresh(self):
        oid = self.app.pargs.id
        data = {"organization": {}}
        uri = "%s/organizations/%s" % (self.baseuri, oid)
        self.self.cmp_patch(uri, data=data, timeout=600)
        self.app.render({"msg": "Refresh organization %s" % oid})

    @ex(
        help="delete organization",
        description="delete organization",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "organization uuid or name",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = "%s/organizations/%s" % (self.baseuri, oid)
        self.cmp_delete(uri, entity="organization %s" % oid)

    @ex(
        help="get organization active services info",
        description="get organization active services info",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "organization uuid or name",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def active_services(self):
        oid = self.app.pargs.id
        uri = "%s/organizations/%s/activeservices" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key="services", details=True)


class OrganizationAuthController(AuthorityControllerChild):
    class Meta:
        label = "orgs_auth"
        # aliases = ['auth']
        # stacked_on = 'organizations'
        # stacked_type = 'nested'
        description = "organization authorization"
        help = "organization authorization"

    @ex(
        help="get organization roles",
        description="get organization roles",
        arguments=ARGS(
            [
                (["id"], {"help": "organization uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def role_get(self):
        oid = self.app.pargs.id
        uri = "%s/organizations/%s/roles" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key="roles", headers=["name", "desc"], maxsize=200)

    @ex(
        help="get organization users",
        description="get organization users",
        arguments=ARGS(
            [
                (["id"], {"help": "organization uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def user_get(self):
        oid = self.app.pargs.id
        uri = "%s/organizations/%s/users" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="users",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            maxsize=200,
        )

    @ex(
        help="add organization role to a user",
        description="add organization role to a user",
        arguments=ARGS(
            [
                (["id"], {"help": "organization uuid", "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": "organization role", "action": "store", "type": str},
                ),
                (
                    ["user"],
                    {"help": "authorization user", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = "%s/organizations/%s/users" % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="remove organization role from a user",
        description="remove organization role from a user",
        arguments=ARGS(
            [
                (["id"], {"help": "organization uuid", "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": "organization role", "action": "store", "type": str},
                ),
                (
                    ["user"],
                    {"help": "authorization user", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = "%s/organizations/%s/users" % (self.baseuri, oid)
        res = self.cmp_delete(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="get organization groups",
        description="get organization groups",
        arguments=ARGS(
            [
                (["id"], {"help": "organization uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def group_get(self):
        oid = self.app.pargs.id
        uri = "%s/organizations/%s/groups" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="groups",
            headers=["id", "name", "role"],
            fields=["uuid", "name", "role"],
            maxsize=200,
        )

    @ex(
        help="add organization role to a group",
        description="add organization role to a group",
        arguments=ARGS(
            [
                (["id"], {"help": "organization uuid", "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": "organization role", "action": "store", "type": str},
                ),
                (
                    ["group"],
                    {"help": "authorization group", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = "%s/organizations/%s/groups" % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="remove organization role from a group",
        description="remove organization role from a group",
        arguments=ARGS(
            [
                (["id"], {"help": "organization uuid", "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": "organization role", "action": "store", "type": str},
                ),
                (
                    ["group"],
                    {"help": "authorization group", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = "%s/organizations/%s/groups" % (self.baseuri, oid)
        res = self.cmp_delete(uri, data)
        self.app.render({"msg": res})
