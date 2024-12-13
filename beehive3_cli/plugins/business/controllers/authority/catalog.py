# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from cement import ex
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.business.controllers.authority import AuthorityControllerChild


class CatalogController(AuthorityControllerChild):
    class Meta:
        label = "service_catalogs"
        description = "service catalog management"
        help = "service catalog management"

        headers = ["id", "name", "version", "active", "date"]
        fields = ["uuid", "name", "version", "active", "date.creation"]

    @ex(
        help="get srvcatalogs",
        description="This CLI command is used to retrieve the list of available service catalogs in the Nivola CMP platform. Service catalogs allow users to browse and provision different types of managed services offered by the platform. The 'get' subcommand fetches the catalog data without any additional parameters as no arguments are required according to the JSON. This provides administrators with an easy way to check the available service options through the CLI.",
        example="beehive bu service-catalogs get ",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "service catalog id",
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
                        "help": "service catalog name",
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
            uri = "%s/srvcatalogs/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri).get("catalog")

            if self.is_output_text():
                self.app.render(res, details=True)
                self.c("\nservice definitions", "underline")
                params = []
                data = self.format_paginated_query(params)
                uri = "%s/srvcatalogs/%s/defs" % (self.baseuri, oid)
                res = self.cmp_get(uri, data=data)
                headers = [
                    "id",
                    "uuid",
                    "name",
                    "version",
                    "status",
                    "service_type_id",
                    "active",
                    "date.creation",
                ]
                self.app.render(res, key="servicedefs", headers=headers)
            else:
                self.app.render(res, key="srvcatalog", details=True)
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
            uri = "%s/srvcatalogs" % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="catalogs",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    @ex(
        help="add service catalog",
        description="This CLI command is used to add a new service catalog to the Nivola CMP platform. The 'name' argument is required and is used to specify the name of the service catalog being added.",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "service catalog name", "action": "store", "type": str},
                ),
                (
                    ["-desc"],
                    {
                        "help": "service catalog description",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
            ]
        ),
    )
    def add(self):
        data = {
            "srvcatalog": {
                "name": self.app.pargs.name,
                "desc": self.app.pargs.desc,
            }
        }
        uri = "%s/srvcatalogs" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "Add service catalog %s" % res})

    @ex(
        help="update service catalog",
        description="This command updates an existing service catalog in Nivola CMP. It requires the ID of the service catalog to update as the only required argument. The ID is used to identify and retrieve the existing service catalog object from the database to then apply the update changes to and save it back.",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service catalog id", "action": "store", "type": str},
                ),
                (
                    ["-name"],
                    {
                        "help": "service catalog name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "service catalog description",
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
        params = self.app.kvargs
        data = {"srvcatalog": params}
        uri = "%s/srvcatalogs/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "update service catalog %s" % oid})

    @ex(
        help="refresh service catalog",
        description="This CLI command patches or refreshes an existing service catalog in Nivola CMP. It requires the service catalog ID as a required argument to identify which catalog needs to be refreshed. Refreshing a catalog updates it with any changes to the available services, plans or metadata from the upstream catalog provider.",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service catalog id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def patch(self):
        oid = self.app.pargs.id
        data = {"srvcatalog": {}}
        uri = "%s/srvcatalogs/%s" % (self.baseuri, oid)
        self.cmp_patch(uri, data=data, timeout=600)
        self.app.render({"msg": "refresh service catalog %s" % oid})

    @ex(
        help="delete service catalog",
        description="This command deletes a service catalog from Nivola CMP. It requires the id of the service catalog to delete as a required argument. The id uniquely identifies the service catalog that is to be removed from the system.",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service catalog id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = "%s/srvcatalogs/%s" % (self.baseuri, oid)
        self.cmp_delete(uri, entity="service catalog %s" % oid)

    @ex(
        help="delete service catalog service definition",
        description="This command adds service definitions to a service catalog. It requires the service catalog id and a comma separated list of definition ids to add to the catalog. This allows adding multiple preexisting definitions to a catalog in one command.",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service catalog id", "action": "store", "type": str},
                ),
                (
                    ["definitions"],
                    {
                        "help": "comma separated list of definition id",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def definition_add(self):
        oid = self.app.pargs.id
        definitions = self.app.pargs.definitions
        data = {"definitions": {"oids": definitions.split(",")}}
        uri = "%s/srvcatalogs/%s/defs" % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "ddd service definitions %s to catalog %s" % (definitions, oid)})

    @ex(
        help="delete service catalog service definition",
        description="This command adds service definitions to a service catalog. It requires the service catalog id and a comma separated list of definition ids to add to the catalog. This allows adding multiple preexisting definitions to a catalog in one command.",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service catalog id", "action": "store", "type": str},
                ),
                (
                    ["definitions"],
                    {
                        "help": "comma separated list of definition id",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def definition_del(self):
        oid = self.app.pargs.id
        definitions = self.app.pargs.definitions
        data = {"definitions": {"oids": definitions.split(",")}}
        uri = "%s/srvcatalogs/%s/defs" % (self.baseuri, oid)
        self.cmp_delete(uri, data=data, entity="service definitions %s" % definitions)


class CatalogAuthController(AuthorityControllerChild):
    class Meta:
        label = "service_catalogs_auth"
        # aliases = ['auth']
        # stacked_on = 'srvcatalogs'
        # stacked_type = 'nested'
        description = "service catalog authorization"
        help = "service catalog authorization"

    @ex(
        help="get service catalog  roles",
        description="This command gets the roles associated with a service catalog. It requires the service catalog id as the only required argument to identify the catalog and retrieve its roles.",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service catalog id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def role_get(self):
        oid = self.app.pargs.id
        uri = "%s/srvcatalogs/%s/roles" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key="roles", headers=["name", "desc"], maxsize=200)

    @ex(
        help="get service catalog  users",
        description="This command retrieves information about a specific user belonging to a service catalog. It requires the ID of the service catalog as a required argument to identify which catalog's users are being accessed. The command outputs details about the requested user, including their name, email and role within the specified service catalog.",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service catalog id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_get(self):
        oid = self.app.pargs.id
        uri = "%s/srvcatalogs/%s/users" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="users",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            maxsize=200,
        )

    @ex(
        help="add service catalog  role to a user",
        description="This command adds a user to a service catalog role. It requires the service catalog id, role and user name as arguments to identify the service catalog, role and user respectively to add the authorization. This allows assigning access control permissions to users for service catalogs.",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service catalog id", "action": "store", "type": str},
                ),
                (
                    ["role"],
                    {"help": "service catalog role", "action": "store", "type": str},
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
        uri = "%s/srvcatalogs/%s/users" % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="remove service catalog  role from a user",
        description="This command removes a user's authorization for a specific role from a service catalog. The service catalog is identified by its ID, the role is specified, and the user to remove authorization for is provided. This allows managing what users have access to perform certain operations on a given service catalog.",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service catalog id", "action": "store", "type": str},
                ),
                (
                    ["role"],
                    {"help": "service catalog role", "action": "store", "type": str},
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
        uri = "%s/srvcatalogs/%s/users" % (self.baseuri, oid)
        res = self.cmp_delete(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="get service catalog  groups",
        description="This command retrieves the groups associated with a specific service catalog. It requires the service catalog ID as the only required argument to identify the catalog. The groups returned would be those that have access to the resources provisioned by that catalog.",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service catalog id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_get(self):
        oid = self.app.pargs.id
        uri = "%s/srvcatalogs/%s/groups" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="groups",
            headers=["id", "name", "role"],
            fields=["uuid", "name", "role"],
            maxsize=200,
        )

    @ex(
        help="add service catalog  role to a group",
        description="This command adds an authorization group to a service catalog role. The required arguments are the service catalog id, the role within the catalog (e.g. viewer or editor), and the name of the authorization group to add to that role.",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service catalog id", "action": "store", "type": str},
                ),
                (
                    ["role"],
                    {"help": "service catalog role", "action": "store", "type": str},
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
        uri = "%s/srvcatalogs/%s/groups" % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="remove service catalog  role from a group",
        description="This command removes a service catalog role from an authorization group. It requires the service catalog ID, role and group name as arguments to identify which role assignment to remove.",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service catalog id", "action": "store", "type": str},
                ),
                (
                    ["role"],
                    {"help": "service catalog role", "action": "store", "type": str},
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
        uri = "%s/srvcatalogs/%s/groups" % (self.baseuri, oid)
        res = self.cmp_delete(uri, data)
        self.app.render({"msg": res})
