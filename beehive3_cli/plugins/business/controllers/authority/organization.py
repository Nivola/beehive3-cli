# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

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
        description="This command is used to retrieve organizations from the platform. It does not require any arguments. The organizations returned can optionally be filtered and paginated using optional arguments like -name, -size and -page.",
        example="beehive bu orgs get -name AOU-Novara;beehive bu orgs get -size 40 -page 2",
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
        description="This command allows you to add a new organization to the Nivola CMP platform. You need to provide the name of the organization being added as well as the type of organization (e.g business, non-profit etc).",
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
        description="This command updates an existing organization in Nivola CMP. The required arguments are the name of the organization to update and the new organization type. The organization type can be one of 'customer', 'vendor' or 'partner'.",
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
        description="This command refreshes an organization by its uuid or name. It retrieves the latest details of the organization from the server and updates the local cache. The 'id' argument is required to identify the organization to refresh by its uuid or name.",
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
        description="This command deletes an organization from Nivola CMP. The organization to delete must be specified using either the uuid or name of the organization in the 'id' argument.",
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
        description="This command retrieves active services information for a specific organization. It requires the organization ID or name as the only required argument to identify which organization's active services to retrieve. The information returned would include details on all services that are currently active/running for the given organization.",
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
        description="This command gets the roles for a specific organization. The organization is identified by its UUID which must be provided as the required 'id' argument.",
        example="beehive bu orgs-auth role-get 1",
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
        self.app.render(res, key="roles", headers=["name", "desc", "role"], maxsize=200)

    @ex(
        help="get organization users",
        description="This command gets the users of an organization. It requires the organization uuid as the only required argument identified as 'id'. This will retrieve the users that belong to the specified organization.",
        example="beehive bu orgs-auth user-get 1",
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
        description="This command adds an organization role to a user. It requires the organization UUID, the role to assign (e.g. member, admin etc.), and the user ID to assign the role to as required arguments.",
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
        description="This command removes an organization role from a specific user. It requires the organization UUID, the role within the organization (e.g. member, admin etc.), and the username of the user to remove the role from.",
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
        description="This command retrieves the groups associated with an organization. The organization is identified by its UUID which must be provided as the 'id' argument. This allows administrators to view the existing groups and their permissions within an organization.",
        example="beehive bu orgs-auth group-get 1",
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
        description="This command adds an organization role to an authorization group by specifying the organization UUID, role and group name. The organization UUID identifies the organization, the role specifies the level of access (e.g. admin, user) and the group name is the group to which the role is being assigned.",
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
        description="This command removes an organization role from an authorization group. It requires the organization UUID, role and group name as arguments to identify which role assignment to remove.",
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
