# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from json import loads
from os import path
from urllib.parse import urlencode
from cement import ex
from beecell.types.type_string import str2bool, truncate
from beecell.simple import set_request_params
from beehive3_cli.core.controller import CliController, PARGS, ARGS, StringAction
from beehive3_cli.core.util import load_config
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


class ServiceController(CliController):
    class Meta:
        label = "bu_service"
        stacked_on = "base"
        stacked_type = "nested"
        description = "business service management"
        help = "business service management"


class ServiceControllerChild(BusinessControllerChild):
    class Meta:
        stacked_on = "bu"
        stacked_type = "nested"


class ServiceTypeController(ServiceControllerChild):
    class Meta:
        label = "service_types"
        description = "service type management"
        help = "service type management"

    @ex(
        help="get service type plugins",
        description="This command is used to retrieve the available service type plugins that can be used to define services in Nivola CMP. Service type plugins define the schema and lifecycle of different types of services that can be created and managed in Nivola CMP. Executing this command without any arguments will return a list of all available service type plugins along with their description and metadata.",
        example="beehive bu service-types plugin-get ;beehive bu service-types plugin-get ",
        arguments=PARGS([]),
    )
    def plugin_get(self):
        """List all plugin_types"""
        params = []
        mappings = {}
        data = self.format_paginated_query(params, mappings=mappings)
        uri = "%s/servicetypes/plugintypes" % self.baseuri
        res = self.cmp_get(uri, data=data)
        self.app.render(res, key="plugintypes", headers=["id", "name", "objclass"], maxsize=200)

    @ex(
        help="get service types",
        description="This command is used to retrieve all the available service types from the Nivola CMP platform. Service types are categories or types of services that can be provisioned through the platform, like compute, storage etc. Without any arguments, this command will return all the service types. Optionally an ID can be passed to get details of a specific service type.",
        example="beehive bu service-types get -id 36;beehive bu service-types get ",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "entity id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "entity name",
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
                    ["-version"],
                    {
                        "help": "type version",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": "type status",
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
            uri = "%s/servicetypes/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri).get("servicetype")

            if self.is_output_text():
                self.app.render(res, details=True)
            else:
                self.app.render(res, key="resource", details=True)
        else:
            params = ["name", "objid", "flag_container", "version", "status"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "%s/servicetypes" % self.baseuri
            res = self.cmp_get(uri, data=data)
            transform = {"status": self.color_error}
            headers = [
                "id",
                "uuid",
                "name",
                "version",
                "plugintype",
                "status",
                "active",
                "flag_container",
                "objclass",
                "date.creation",
            ]
            self.app.render(
                res,
                key="servicetypes",
                headers=headers,
                transform=transform,
                maxsize=200,
            )

    @ex(
        help="add service type",
        description="This command allows you to add a new service type to the system by specifying its name and the Python class that implements it. The name argument is used to identify the service type in the system. The objclass argument specifies the full Python path to the class that implements this service type.",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "service type name", "action": "store", "type": str},
                ),
                (
                    ["objclass"],
                    {"help": "python class full path", "action": "store", "type": str},
                ),
                (
                    ["-version"],
                    {
                        "help": "service type version",
                        "action": "store",
                        "type": str,
                        "default": "v1.0",
                    },
                ),
                (
                    ["-flag_container"],
                    {
                        "help": "if True service is a container",
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": "service type status",
                        "action": "store",
                        "type": str,
                        "default": "ACTIVE",
                    },
                ),
            ]
        ),
    )
    def add(self):
        name = self.app.pargs.name
        objclass = self.app.pargs.objclass
        version = self.app.pargs.version
        flag_container = self.app.pargs.container
        status = self.app.pargs.status
        data = {
            "servicetype": {
                "name": name,
                "version": version,
                "desc": name,
                "objclass": objclass,
                "flag_container": flag_container,
                "status": status,
                "template_cfg": "{{}}",
            }
        }
        uri = "%s/servicetypes" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "Add service type %s" % res})

    @ex(
        help="update service type",
        description="This command updates an existing service type in Nivola CMP. It requires the service type id, name and Python class full path as required arguments to identify and update the service type details.",
        arguments=ARGS(
            [
                (["id"], {"help": "service type id", "action": "store", "type": str}),
                (
                    ["-name"],
                    {"help": "service type name", "action": "store", "type": str},
                ),
                (
                    ["-objclass"],
                    {"help": "python class full path", "action": "store", "type": str},
                ),
                (
                    ["-version"],
                    {
                        "help": "service type version",
                        "action": "store",
                        "type": str,
                        "default": "v1.0",
                    },
                ),
                (
                    ["-flag_container"],
                    {
                        "help": "if True service is a container",
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": "service type status",
                        "action": "store",
                        "type": str,
                        "default": "ACTIVE",
                    },
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.oid
        data = set_request_params(self.app.pargs, ["name", "objclass", "version", "flag_container", "status"])
        uri = "%s/servicetypes/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data={"servicetype": data})
        self.app.render({"msg": "update service type %s with data %s" % (oid, data)})

    @ex(
        help="delete service type",
        description="This command deletes service type(s) from the Nivola CMP platform. The 'ids' argument is required and accepts one or more service type ids to delete as a space separated list.",
        arguments=ARGS(
            [
                (["ids"], {"help": "service type id", "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        value = self.app.pargs.id
        uri = "%s/servicetypes/%s" % (self.baseuri, value)
        self.cmp_delete(uri, entity="service type %s" % value)

    @ex(
        help="get service type process",
        description="This command retrieves the details of a specific service type process based on the provided service type id. It requires the id of the service type as the only required argument to uniquely identify and return the process details of that service type.",
        arguments=ARGS(
            [
                (["id"], {"help": "service type id", "action": "store", "type": str}),
            ]
        ),
    )
    def process_get(self):
        value = self.app.pargs.id
        uri = "%s/serviceprocesses" % self.baseuri
        res = self.cmp_get(uri, data="service_type_id=%s" % value).get("serviceprocesses", [])
        self.app.render(
            res,
            headers=[
                "id",
                "uuid",
                "name",
                "method_key",
                "process_key",
                "active",
                "date.creation",
            ],
        )

    @ex(
        help="set service type process",
        description="This command sets the process method for a specific service type. It requires the service type id and process method name as required arguments to identify and update the correct service type record.",
        arguments=ARGS(
            [
                (["id"], {"help": "service type id", "action": "store", "type": str}),
                (
                    ["method"],
                    {
                        "help": "service type process method",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-name"],
                    {"help": "name", "action": "store", "type": str, "default": None},
                ),
                (
                    ["-desc"],
                    {
                        "help": "description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-process"],
                    {
                        "help": "process",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-template"],
                    {
                        "help": "template file",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def process_set(self):
        typeid = None
        typeoid = self.app.pargs.id
        method = self.app.pargs.method
        if typeoid is not None:
            uri = "%s/servicetypes/%s" % (self.baseuri, typeoid)
            res = self.cmp_get(uri).get("servicetype", {})
            typeid = res.get("id", typeid)
            if typeid is None:
                raise Exception("could not found a type whose oid is %s" % typeoid)

        uri = "%s/serviceprocesses" % self.baseuri
        res = self.cmp_get(uri, data="service_type_id=%s&method_key=%s" % (typeid, method)).get("serviceprocesses", [])

        name = self.app.pargs.name
        desc = self.app.pargs.desc
        process = self.app.pargs.process
        template = self.app.pargs.template
        if len(res) >= 1:
            prev = res[0]
        else:
            prev = None
            if name is None:
                name = "proc"
            if desc is None:
                desc = "description-%s" % name
            if process is None:
                process = "invalid_key"
            if template is None:
                template = "{}"

        if template[0] == "@":
            filename = template[1:]
            if path.isfile(filename):
                f = open(filename, "r")
                template = f.read()
                f.close()
            else:
                raise Exception("Jinja template %s is not a file" % filename)

        data = {
            "serviceprocess": {
                "name": name,
                "desc": desc,
                "service_type_id": str(typeid),
                "method_key": method,
                "process_key": process,
                "template": template,
            }
        }
        if prev == None:
            uri = "%s/serviceprocesses" % self.baseuri
            res = self.cmp_post(uri, data=data)
            self.app.render(res)
        else:
            uri = "%s/serviceprocesses/%s" % (self.baseuri, prev["uuid"])
            res = self.cmp_put(uri, data=data)
            self.app.render(res)


class ServiceDefinitionController(ServiceControllerChild):
    class Meta:
        label = "service_defs"
        description = "service definition management"
        help = "service definition management"

    @ex(
        help="get product codes",
        description="This command retrieves product codes",
        example="beehive bu get-product-code STILO",
        arguments=PARGS(
            [
                (
                    ["filter_name"],
                    {
                        "help": "filter name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get_product_code(self):
        filter_name = getattr(self.app.pargs, "filter_name", None)
        data = {"filter_name": filter_name}
        uri = "%s/product_codes" % self.baseuri
        res = self.cmp_get(uri, data=data)
        print(res)

    @ex(
        help="get service definitions",
        description="This command retrieves service definitions from the service registry. Service definitions describe the interfaces, endpoints and other metadata for microservices. By default, all definitions are returned. The -id option can be used to retrieve a single definition by ID.",
        example="beehive bu service-defs get ;beehive bu service-defs get -id <uuid>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "entity id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "entity name",
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
                    ["-version"],
                    {
                        "help": "definition version",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": "type status",
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
            uri = "%s/servicedefs/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri).get("servicedef")

            if self.is_output_text():
                self.app.render(res, details=True)

                # get configs
                uri = "%s/servicecfgs" % self.baseuri
                res = self.cmp_get(uri, data="service_definition_id=%s" % oid).get("servicecfgs", [{}])[0]
                params = res.pop("params", [])
                self.c("\nconfigs", "underline")
                self.app.render(params, details=True)
            else:
                self.app.render(res, key="resource", details=True)
        else:
            params = ["name", "objid", "version", "status"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "%s/servicedefs" % self.baseuri
            res = self.cmp_get(uri, data=data)
            transform = {"status": self.color_error}
            headers = [
                "id",
                "name",
                "desc",
                "version",
                "status",
                "type",
                "active",
                "is_default",
                "date",
            ]
            fields = [
                "uuid",
                "name",
                "desc",
                "version",
                "status",
                "service_type_id",
                "active",
                "is_default",
                "date.creation",
            ]
            self.app.render(
                res,
                key="servicedefs",
                headers=headers,
                fields=fields,
                transform=transform,
            )

    @ex(
        help="add service definition",
        description="This command adds a new service definition to Nivola CMP. It requires the name, type and params of the service definition to be provided as required arguments. The name is used to uniquely identify the service definition, type specifies the type of service (e.g. 'http') and params contains configuration parameters for the service in JSON format.",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "service definition name", "action": "store", "type": str},
                ),
                (["type"], {"help": "service type id", "action": "store", "type": str}),
                (
                    ["params"],
                    {
                        "help": "service definition params",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "service definition description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-version"],
                    {
                        "help": "service definition version",
                        "action": "store",
                        "type": str,
                        "default": "v1.0",
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": "service definition status",
                        "action": "store",
                        "type": str,
                        "default": "ACTIVE",
                    },
                ),
            ]
        ),
    )
    def add(self):
        # service_type_id = self.app.pargs.service_type
        service_type_id = self.app.pargs.type
        name = self.app.pargs.name
        params = self.app.pargs.params
        version = self.app.pargs.version
        desc = self.app.pargs.desc
        status = self.app.pargs.status
        parent_id = None
        priority = None

        # read params from file
        if params.find("@") >= 0:
            params = load_config(params.replace("@", ""))
        else:
            params = loads(params)

        data = {
            "servicedef": {
                "name": name,
                "version": version,
                "desc": desc,
                "status": status,
                "service_type_id": service_type_id,
                "parent_id": parent_id,
                "priority": priority,
            }
        }
        uri = "%s/servicedefs" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "add service definition %s" % res})

        data = {
            "servicecfg": {
                "name": "%s-config" % name,
                "desc": "%s-config" % name,
                "service_definition_id": res["uuid"],
                "params": params,
                "params_type": "JSON",
                "version": version,
            }
        }
        uri = "%s/servicecfgs" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render("Add service definition config: %s" % res)

    @ex(
        help="update service definition",
        description="This command updates an existing service definition in Nivola CMP. It requires the service definition id and name as required arguments to identify and update the correct definition. The updated definition data is passed via stdin in JSON format.",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service definition id", "action": "store", "type": str},
                ),
                (
                    ["-name"],
                    {"help": "service definition name", "action": "store", "type": str},
                ),
                (
                    ["-desc"],
                    {
                        "help": "service definition description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": "service definition status",
                        "action": "store",
                        "type": str,
                        "default": "ACTIVE",
                    },
                ),
                (
                    ["-config"],
                    {
                        "help": "service definition config key:value",
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
        data = set_request_params(self.app.pargs, ["name", "desc", "status", "config"])
        uri = "%s/servicedefs/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data={"servicedef": data})
        self.app.render({"msg": "update service definition %s with data %s" % (oid, data)})

    @ex(
        help="delete service definition",
        description="This command deletes a service definition from the system by specifying its unique id. The service definition id is a required argument for this command to identify which existing service definition to delete from the system.",
        example="beehive bu service-defs delete <uuid>;beehive bu service-defs delete <uuid>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "service definition id", "action": "store", "type": str},
                )
            ]
        ),
    )
    def delete(self):
        value = self.app.pargs.id
        uri = "%s/servicedefs/%s" % (self.baseuri, value)
        self.cmp_delete(uri, entity="service definition %s" % value)


class ServiceInstanceController(ServiceControllerChild):
    class Meta:
        label = "service_insts"
        description = "service instance management"
        help = "service instance management"

        task_headers = [
            "uuid",
            "name",
            "parent",
            "api_id",
            "status",
            "start_time",
            "stop_time",
            "duration",
        ]
        task_fields = [
            "uuid",
            "alias",
            "parent",
            "api_id",
            "status",
            "start_time",
            "stop_time",
            "duration",
        ]

    @ex(
        help="get service instances",
        description="This command gets service instances. It retrieves service instances without any filtering criteria.",
        example="beehive bu service-insts get -id <uuid> -e <env>;beehive bu service-insts get -id <uuid>",
        arguments=ARGS(
            [
                (
                    ["user_name"],
                    {
                        "help": "user name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def filter(self):
        params = ["user_name"]
        aliases = {"user_name": "user_name"}
        mappings = {}
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "/v1.0/nws/services/objects/filter/byusername"
        res = self.cmp_get(uri, data=data)
        fields = [
            "uuid",
            "name",
            "plugintype",
            "account.name",
            "definition_name",
            "status",
            "resource_uuid",
            "is_container",
            "parent.name",
            "date.creation",
        ]
        headers = [
            "id",
            "name",
            "type",
            "account",
            "definition",
            "status",
            "resource",
            "is_container",
            "parent",
            "creation",
        ]
        self.app.render(res, key="services", headers=headers, fields=fields)

    @ex(
        help="get service instances",
        description="This command gets service instances. It retrieves service instances without any filtering criteria.",
        example="beehive bu service-insts get -id <uuid> -e <env>;beehive bu service-insts get -id <uuid>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "entity id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-legacy"],
                    {"help": "use legacy v1", "action": "store_true", "default": False},
                ),
                (
                    ["-name"],
                    {
                        "help": "entity name",
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
                    ["-version"],
                    {
                        "help": "definition version",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": "type status",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-account"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-resource"],
                    {
                        "help": "resource uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": "parent service instance",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-plugintype"],
                    {
                        "help": "service plugintype",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": "comma separated tag list",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-iscontainer"],
                    {
                        "help": "if True show only container service instance",
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
                (
                    ["-details"],
                    {
                        "help": "if False it does not show details (resource)",
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
        legacy = getattr(self.app.pargs, "legacy", False)
        # details = str2bool(getattr(self.app.pargs, "details", True))
        if legacy:
            version = "v1.0"
        else:
            version = "v2.0"

        if oid is not None:
            # uri = '/v2.0/nws/serviceinsts/%s' %  oid
            uri = "/%s/nws/serviceinsts/%s" % (version, oid)
            res = self.cmp_get(uri).get("serviceinst")

            if self.is_output_text():
                config = res.pop("config")
                self.app.render(res, details=True)

                # get configs
                self.c("\nconfigs", "underline")
                self.app.render(config, details=True)

                self.c("\nlinks", "underline")
                uri = "%s/links" % self.baseuri
                links = self.cmp_get(uri, data={"service": oid, "size": -1})
                fields = [
                    "id",
                    "name",
                    "active",
                    "details.type",
                    "details.start_service.id",
                    "details.end_service.id",
                    "details.attributes",
                    "date.creation",
                    "date.modified",
                ]
                headers = [
                    "id",
                    "name",
                    "type",
                    "start",
                    "end",
                    "attributes",
                    "creation",
                    "modified",
                ]
                self.app.render(links.get("links"), headers=headers, fields=fields)

                data = urlencode({"objid": res["__meta__"]["objid"]})
                uri = "/v2.0/nws/worker/tasks"
                task = self.cmp_get(uri, data=data).get("task_instances")
                transform = {
                    # 'name': lambda n: n.split('.')[-1],
                    "parent": lambda n: truncate(n, 20),
                    "status": self.color_error,
                }
                self.c("\ntasks [last 10]", "underline")
                self.app.render(
                    task,
                    headers=self._meta.task_headers,
                    fields=self._meta.task_fields,
                    maxsize=80,
                    transform=transform,
                )

                # get resource
                self.c("\nresource", "underline")
                resource_uuid = res.get("resource_uuid", None)
                if resource_uuid is not None and resource_uuid != "":
                    uri = "/v1.0/nrs/entities/%s" % resource_uuid
                    resource = self.cmp_get(uri).get("resource")
                    self.app.render(resource, details=True)
            else:
                self.app.render(res, key="resource", details=True)
        else:
            params = [
                "name",
                "objid",
                "version",
                "status",
                "account",
                "resource",
                "parent",
                "plugintype",
                "tags",
                "iscontainer",
                "details",
            ]
            aliases = {
                "account": "account_id",
                "resource": "resource_uuid",
                "parent": "parent_id",
                "iscontainer": "flag_container",
            }
            mappings = {"name": lambda n: "%" + n + "%", "iscontainer": str2bool}
            data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
            # uri = '/v2.0/nws/serviceinsts'
            uri = "/%s/nws/serviceinsts" % version

            def render(self, res, **kwargs):
                transform = {"status": self.color_error}
                fields = [
                    "uuid",
                    "name",
                    "plugintype",
                    "account.name",
                    "definition_name",
                    "status",
                    "resource_uuid",
                    "is_container",
                    "parent.name",
                    "date.creation",
                ]
                headers = [
                    "id",
                    "name",
                    "type",
                    "account",
                    "definition",
                    "status",
                    "resource",
                    "is_container",
                    "parent",
                    "creation",
                ]
                self.app.render(
                    res,
                    key="serviceinsts",
                    headers=headers,
                    fields=fields,
                    transform=transform,
                )

            self.cmp_get_pages(
                uri, data=data, pagesize=20, key_total_name="total", key_list_name="serviceinsts", fn_render=render
            )

    @ex(
        help="import service instance from resource",
        description="This command imports a service instance from a resource. It requires the service instance name, account id, plugin type of the service instance and plugin type of the container to be provided as required arguments.",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "service instance name", "action": "store", "type": str},
                ),
                (
                    ["-desc"],
                    {
                        "help": "service instance description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["plugintype"],
                    {
                        "help": "plugin type of the service instance",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["container_plugintype"],
                    {
                        "help": "plugin type of the container",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-service_definition_id"],
                    {
                        "help": "service definition id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["resource"],
                    {
                        "help": "resource id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": "parent service instance id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def import_from_resource(self):
        """
        example:
        - name: test-micro-volume-0
        - account: account_ale_gw2 (or id, or uuid)
        - plugintype: ComputeService
        - container_plugintype: ComputeService
        - resource: <uuid>
        [ optional
            - service_definition_id: 13
            - parent: <uuid>
        ] optional

        creates service instance and service instance config for existing resource
        """
        name = self.app.pargs.name
        account_id = self.get_account(self.app.pargs.account).get("uuid")
        plugintype = self.app.pargs.plugintype
        container_plugintype = self.app.pargs.container_plugintype
        resource_id = self.app.pargs.resource
        service_definition_id = self.app.pargs.service_definition_id
        parent_id = self.app.pargs.parent
        desc = self.app.pargs.desc

        data = {
            "serviceinst": {
                "name": name,
                "desc": desc,
                "account_id": account_id,
                "plugintype": plugintype,
                "container_plugintype": container_plugintype,
                "resource_id": resource_id,
                "service_definition_id": service_definition_id,
                "parent_id": parent_id,
            }
        }
        uri = "/v2.0/nws/serviceinsts/import"
        self.cmp_post(uri, data=data)
        self.app.render({"msg": "import service plugin instance %s" % name})

    @ex(
        help="check service instance",
        description="This command checks the status of service instances running on Nivola Cloud. It allows the user to verify if their services are running properly without having to log into the platform directly. The command does not require any arguments as it will check all service instances by default. The output provides the name, status and other details of each service instance so the user can easily monitor them.",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "service instance id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def check(self):
        oid = self.app.pargs.id
        uri = "/v2.0/nws/serviceinsts/%s/check" % oid
        res = self.cmp_get(uri).get("serviceinst")
        self.app.render(res, details=True)

    @ex(
        help="update service instance",
        description="This CLI command updates an existing service instance in Nivola Cloud. The service instance is identified by its name or ID. No arguments are required as the instance details will need to be provided via a configuration file or interactive prompts.",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "service instance id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-resource_uuid"],
                    {
                        "help": "resource uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": "parent service instance",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "service instance name",
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
        data = set_request_params(self.app.pargs, ["resource_uuid", "parent", "name"])
        uri = "/v2.0/nws/serviceinsts/%s" % oid
        self.cmp_put(uri, data={"serviceinst": data})
        self.app.render({"msg": "update service plugin instance %s" % oid})

    @ex(
        help="patch service instance",
        description="This CLI command patches or updates an existing service instance. Since there are no required arguments listed, it likely accepts the service instance ID or name as a parameter to identify which instance to update, along with other optional arguments to specify which attributes or fields of the instance should be modified.",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "service instance id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def patch(self):
        oid = self.app.pargs.id
        # data = set_request_params(self.app.pargs, ['resource_uuid', 'parent'])
        uri = "/v2.0/nws/serviceinsts/%s" % oid
        self.cmp_patch(uri, data={"serviceinst": {}})
        self.app.render({"msg": "patch service plugin instance %s" % oid})

    @ex(
        help="""update service instance forcing his status to "error" or "active" """,
        description="""update service instance forcing his status to "error" or "active" """,
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "service instance id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["status"],
                    {
                        "help": """service instance status must be "active" or "error" """,
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def status(self):
        oid = self.app.pargs.id
        status = self.app.pargs.status
        if status not in ["active", "error"]:
            raise Exception("Status must be active or error")
        data = {"serviceinst": {"status": status.upper()}}
        uri = "/v2.0/nws/serviceinsts/%s/status" % oid
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "update service instance %s status with %s" % (oid, status)})

    @ex(
        help="delete service instance",
        description="This command deletes a service instance. It requires the service instance ID as a parameter to identify which instance to delete. The command also supports optional flags to specify the environment (-e) of the instance and assume yes (-y) without confirmation.",
        example="beehive bu service-insts delete <uuid> -e <env>;beehive bu service-insts delete <uuid> -e <env> -y",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "service instance id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-propagate"],
                    {
                        "help": "if True propagate delete to all cmp modules [default=false]",
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": "if True force delete [default=false]",
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
            ]
        ),
    )
    def delete(self):
        value = self.app.pargs.id
        force = str2bool(self.app.pargs.force)
        propagate = str2bool(self.app.pargs.propagate)
        data = {"force": force, "propagate": propagate}

        version = "v2.0"
        uri = "/%s/nws/serviceinsts/%s" % (version, value)
        res = self.cmp_get(uri).get("serviceinst")
        plugintype = res["plugintype"]
        name = res["name"]
        if plugintype in [
            "ComputeService",
            "DatabaseService",
            "StorageService",
            "AppEngineService",
            "NetworkService",
            "LoggingService",
            "MonitoringService",
        ]:
            print("Core service %s cannot be deleted" % plugintype)

        else:
            msg = self.app.colored_text.yellow(
                "This command could leave the linked resources on the platform. Continue [y/n]? "
            )
            i = input(msg)
            if i == "y":
                uri = "/v2.0/nws/serviceinsts/%s" % value
                self.cmp_delete(uri, data=data, timeout=180, entity="service instance %s" % value)

    @ex(
        help="add tag to service instance",
        description="This command allows adding one or more tags to a service instance. The tags argument requires a comma separated list of tag names that will be added to the specified service instance. Tags can be used to logically group and filter service instances for management purposes.",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "service instance id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["tags"],
                    {
                        "help": "comma separated list of tags",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def tag_add(self):
        value = self.app.pargs.id
        tags = self.app.pargs.tags.split(",")
        data = {"serviceinst": {"tags": {"cmd": "add", "values": tags}}}
        uri = "/v2.0/nws/serviceinsts/%s" % value
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": "add tags %s to service instance %s" % (tags, value)})

    @ex(
        help="add tag to account's service instances",
        description="This command allows adding one or more tags to account's service instances. The tags argument requires a comma separated list of tag names that will be added to the specified service instance. Tags can be used to logically group and filter service instances for management purposes.",
        arguments=PARGS(
            [
                (
                    ["account_id"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["tags"],
                    {
                        "help": "comma separated list of tags",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def tag_add_account_insts(self):
        account_id = self.app.pargs.account_id
        account = self.get_account(account_id).get("uuid")
        tags = self.app.pargs.tags.split(",")
        data = {"serviceinst": {"tags": {"cmd": "add", "values": tags}}}
        uri = "/v2.0/nws/serviceinsts/account/%s" % account
        res = self.cmp_put(uri, data=data)
        num_services = res["num_services"]
        self.app.render(
            {"msg": "added tags %s to %s service instances of account %s" % (tags, num_services, account_id)}
        )

    @ex(
        help="delete tag from service instance",
        description="This command deletes one or more tags from a service instance. The tags argument requires a comma separated list of tag names to remove from the instance. This allows an operator to untag or remove labels from resources in the platform.",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "service instance id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["tags"],
                    {
                        "help": "comma separated list of tags",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def tag_del(self):
        value = self.app.pargs.id
        tags = self.app.pargs.tags.split(",")
        data = {"serviceinst": {"tags": {"cmd": "delete", "values": tags}}}
        uri = "/v2.0/nws/serviceinsts/%s" % value
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": "delete tags %s from service instance %s" % (tags, value)})

    @ex(
        help="update resource entity config",
        description="Update resource entity config",
        example="beehive bu service-insts config-set <uuid> instance.ImageId -value <uuid>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
                (
                    ["config_key"],
                    {
                        "help": "config key like config.key",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-value"],
                    {
                        "help": "config value",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def config_set(self):
        oid = self.app.pargs.id
        key = self.app.pargs.config_key
        value = self.app.pargs.value
        uri = "/v2.0/nws/serviceinsts/%s/config" % oid
        self.cmp_put(uri, data={"config": {"key": key, "value": value}})
        self.app.render({"msg": "update service entity %s config" % oid})

    @ex(
        help="get tag of service instance",
        description="This command retrieves the tag of a specific service instance by providing its id as a required argument. The service instance id is a unique identifier that can be used to fetch additional details like tags for that particular instance.",
        example="beehive bu service-insts tag-get id 90;beehive bu service-insts tag-get",
        arguments=ARGS([(["id"], {"help": "service instance id", "action": "store", "type": str})]),
    )
    def tag_get(self):
        oid = self.app.pargs.id
        data = {"service": oid}
        uri = "%s/tags" % self.baseuri
        res = self.cmp_get(uri, data=data)

        fields = ["id", "name"]
        headers = ["id", "name"]
        self.app.render(res, key="tags", headers=headers, fields=fields, maxsize=45)


class ServiceLinkController(ServiceControllerChild):
    class Meta:
        label = "service_links"
        description = "service link management"
        help = "service link management"

        fields = [
            "id",
            "name",
            "active",
            "details.type",
            "details.start_service.id",
            "details.end_service.id",
            "details.attributes",
            "date.creation",
            "date.modified",
        ]
        headers = [
            "id",
            "name",
            "type",
            "start",
            "end",
            "attributes",
            "creation",
            "modified",
        ]

    @ex(
        help="list service links",
        description="This command lists all the service links in the platform. Service links are used to connect services together and allow them to communicate securely. Without any additional parameters, this command will display all service links. The -id parameter can be used to filter the output to just a single service link by its unique identifier.",
        example="beehive bu service-links get -id <uuid> -e <env> ",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "link uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "link name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-service"],
                    {
                        "help": "start or end service uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "link type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": "link authorization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": "link tags",
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
            uri = "%s/links/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("link")
                details = res.pop("details")
                start_service = details.pop("start_service", {})
                end_service = details.pop("end_service", {})

                self.app.render(res, details=True)
                self.c("\ndetails", "underline")
                self.app.render(details, details=True)
                self.c("\nstart_service", "underline")
                self.app.render(start_service, details=True)
                self.c("\nend_service", "underline")
                self.app.render(end_service, details=True)
            else:
                self.app.render(res, key="link", details=True)
        else:
            params = ["name", "service", "type", "objid", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "%s/links" % self.baseuri
            res = self.cmp_get(uri, data=data)

            self.app.render(
                res,
                key="links",
                headers=self._meta.headers,
                fields=self._meta.fields,
                maxsize=40,
            )

    @ex(
        help="add service link",
        description="This command adds a service link between two services by specifying the required arguments - service link name, account id, start service uuid and end service uuid. A service link defines the relationship between two services in an account and allows them to communicate with each other.",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "service link name", "action": "store", "type": str},
                ),
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["type"],
                    {
                        "help": "service link type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["start_service"],
                    {"help": "start service uuid", "action": "store", "type": str},
                ),
                (
                    ["end_service"],
                    {"help": "end service uuid", "action": "store", "type": str},
                ),
                (
                    ["-attributes"],
                    {
                        "help": "service link attributes",
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
        account = self.app.pargs.account
        link_type = self.app.pargs.type
        start_service = self.app.pargs.start_service
        end_service = self.app.pargs.end_service
        attrib = self.app.pargs.attributes
        if attrib is not None:
            attrib = loads(attrib)
        else:
            attrib = {}

        data = {
            "account": account,
            "type": link_type,
            "name": name,
            "attributes": attrib,
            "start_service": start_service,
            "end_service": end_service,
        }
        uri = "%s/links" % self.baseuri
        res = self.cmp_post(uri, data={"link": data})
        self.app.render({"msg": "add service link %s" % res["uuid"]})

    @ex(
        help="update service link",
        description="This command updates an existing service link. It requires the service link uuid as the id argument to identify which service link to update.",
        arguments=ARGS(
            [
                (["id"], {"help": "service link uuid", "action": "store", "type": str}),
                (
                    ["-name"],
                    {
                        "help": "service link name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "service link type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-start_service"],
                    {
                        "help": "start service uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-end_service"],
                    {
                        "help": "end service uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": "service link attributes",
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
        attrib = self.app.pargs.attributes
        data = set_request_params(
            self.app.pargs,
            ["name", "type", "start_service", "end_service", "attributes"],
        )
        if "attributes" in list(data.keys()):
            data["attributes"] = loads(attrib)
        else:
            attrib = {}
        uri = "%s/links/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data={"link": data})
        self.app.render({"msg": "update service link %s" % oid})

    @ex(
        help="delete service links",
        description="This command deletes service links by their UUIDs. The 'ids' argument requires a comma separated list of service link UUIDs to delete as input. This allows deleting multiple service links with a single command.",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": "comma separated service link uuids",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": "if true force the delete",
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oids = self.app.pargs.ids.split(",")
        force = self.app.pargs.force
        for oid in oids:
            uri = "%s/links/%s" % (self.baseuri, oid)
            if force is True:
                uri += "?force=true"
            self.cmp_delete(uri, entity="link %s" % oid)

    @ex(
        help="add tag to service link",
        description="This command adds a tag to an existing service link. It requires the service link id and the tag name as required arguments. The tag will be added to the service link with the provided id.",
        arguments=ARGS(
            [
                (["id"], {"help": "service link id", "action": "store", "type": str}),
                (["tag"], {"help": "tag", "action": "store", "type": str}),
            ]
        ),
    )
    def tag_add(self):
        value = self.app.pargs.id
        tag = self.app.pargs.tag
        data = {"link": {"tags": {"cmd": "add", "values": [tag]}}}
        uri = "%s/links/%s" % (self.baseuri, value)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "add tag %s to service link %s" % (tag, value)})

    @ex(
        help="delete tag from service link",
        description="This command deletes a specific tag from a service link. The service link id and tag name that needs to be deleted must be provided as required arguments. This allows removing tags from service links as needed.",
        arguments=ARGS(
            [
                (["id"], {"help": "service link id", "action": "store", "type": str}),
                (["tag"], {"help": "tag", "action": "store", "type": str}),
            ]
        ),
    )
    def tag_del(self):
        value = self.app.pargs.id
        tag = self.app.pargs.tag
        data = {"link": {"tags": {"cmd": "delete", "values": [tag]}}}
        uri = "%s/links/%s" % (self.baseuri, value)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "delete tag %s from service link %s" % (tag, value)})

    @ex(
        help="get tag of service link",
        description="This command retrieves the tag of a service link by specifying its ID. The service link ID is a required argument for this command to work. It will return the tag associated with the given service link ID.",
        arguments=ARGS([(["id"], {"help": "service link id", "action": "store", "type": str})]),
    )
    def tag_get(self):
        oid = self.app.pargs.id
        data = {"link": oid}
        uri = "%s/tags" % self.baseuri
        res = self.cmp_get(uri, data=data)

        fields = ["id", "name"]
        headers = ["id", "name"]
        self.app.render(res, key="tags", headers=headers, fields=fields, maxsize=45)


class ServiceTagController(ServiceControllerChild):
    class Meta:
        label = "service_tags"
        description = "service tag management"
        help = "service tag management"

        fields = [
            "id",
            "__meta__.objid",
            "name",
            "date.creation",
            "date.modified",
            "services",
            "containers",
            "links",
            "ownerAlias",
        ]
        headers = ["id", "objid", "name", "creation", "modified", "services", "containers", "links", "account"]

    @ex(
        help="list service tags",
        description="This command lists all the service tags configured in the Nivola CMP platform. Service tags are used to group services for organizational and access control purposes. Without any additional options, this command will display all service tags and their associated services in the Nivola CMP deployment.",
        arguments=PARGS(
            [
                (
                    ["-value"],
                    {
                        "help": "tag value",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-service"],
                    {
                        "help": "service id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-link"],
                    {
                        "help": "service link id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-account"],
                    {
                        "help": "account id",
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
            uri = "%s/tags/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("tag")
                self.app.render(res, details=True)
            else:
                self.app.render(res, key="servicetag", details=True)
        else:
            params = ["value", "service", "link"]
            mappings = {}  # {"name": lambda n: "%" + n + "%"}
            data: str = self.format_paginated_query(params, mappings=mappings)

            # account filter
            account_id = self.app.pargs.account
            if account_id is not None:
                account = self.get_account(account_id)
                meta = account["__meta__"]
                objid_filter = meta["objid"] + "%"
                data_obj = {}
                data_obj["objid"] = objid_filter
                data += "&" + urlencode(data_obj, doseq=True)

            uri = "%s/tags" % self.baseuri
            res = self.cmp_get(uri, data=data)

            self.app.render(
                res,
                key="tags",
                headers=self._meta.headers,
                fields=self._meta.fields,
                maxsize=80,
            )

    @ex(
        help="add service tag",
        description="This command adds a new service tag to an account. It requires the service tag value to be provided along with the account id to which the tag needs to be added.",
        arguments=ARGS(
            [
                (
                    ["value"],
                    {"help": "service tag value", "action": "store", "type": str},
                ),
                (["account"], {"help": "account id", "action": "store", "type": str}),
            ]
        ),
    )
    def add(self):
        value = self.app.pargs.value
        account = self.get_account(self.app.pargs.account).get("uuid")

        data = {"value": value, "account": account}
        uri = "%s/tags" % self.baseuri
        res = self.cmp_post(uri, data={"tag": data})
        self.app.render({"msg": "add service tag %s" % res["uuid"]})

    @ex(
        help="update service tag",
        description="This command updates an existing service tag. It requires the UUID of the service tag to update as the 'id' argument. The service tag details will be updated with any new information provided.",
        arguments=ARGS(
            [
                (["id"], {"help": "service tag uuid", "action": "store", "type": str}),
                (
                    ["-value"],
                    {
                        "help": "service tag value",
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
        value = self.app.pargs.value
        uri = "%s/tags/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data={"tag": {"value": value}})
        self.app.render({"msg": "update service tag %s" % oid})

    @ex(
        help="delete service tags",
        description="This command deletes service tags from the Nivola CMP platform. It requires a comma separated list of IDs of the service tags to delete as an argument. This allows administrators to remove unused or unnecessary service tags from the system.",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": "comma separated service tag id",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": "if true force the delete",
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oids = self.app.pargs.ids.split(",")
        force = self.app.pargs.force
        for oid in oids:
            uri = "%s/tags/%s" % (self.baseuri, oid)
            if force is True:
                uri += "?force=true"
            self.cmp_delete(uri, entity="tag %s" % oid)


class ServiceMetricsController(ServiceControllerChild):
    class Meta:
        label = "service_metrics"
        description = "service metric management"
        help = "service metric management"

    @ex(
        help="list service metrics",
        description="This command is used to list the metrics collected for services running on Nivola Cloud. Some of the metrics that could be listed are CPU and memory usage, request counts, error rates etc. These metrics help monitor the performance and health of services.",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "metric id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-day"],
                    {
                        "help": "sample day",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-value"],
                    {
                        "help": "metric value",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-num"],
                    {
                        "help": "metric num",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-service"],
                    {
                        "help": "metric service instance id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "metric type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-jobid"],
                    {
                        "help": "sample job id",
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
            uri = "%s/services/metrics/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("metric")
                self.app.render(res, details=True)
            else:
                self.app.render(res, key="metric", details=True)
        else:
            params = ["day", "value", "type", "num", "service", "parent", "joibid"]
            mappings = {}
            aliases = {
                "num": "metric_num",
                "service": "instance",
                "type": "metric_type",
                "jobid": "job_id",
                "day": "creation_date",
            }
            data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
            uri = "%s/services/metrics" % self.baseuri
            res = self.cmp_get(uri, data=data)
            headers = ["id", "date", "num", "type", "value", "instance", "job_id"]
            fields = [
                "id",
                "date.creation",
                "metric_num",
                "metric_type",
                "value",
                "service_instance_id",
                "job_id",
            ]
            self.app.render(res, key="metrics", headers=headers, fields=fields, maxsize=45)

    @ex(
        help="list service metric types",
        description="This command lists the available service metric types that can be used to monitor services on Nivola Cloud. Service metrics are collected and stored to provide insights into service performance and health. The 'type-get' command retrieves the predefined metric types that services can report to provide standardized monitoring data without requiring custom metrics to be defined.",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "metric type id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "metric type name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group"],
                    {
                        "help": "metric type group name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "metric type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def type_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = "%s/services/metricstypes/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("metric_type")
                self.app.render(res, details=True)
            else:
                self.app.render(res, key="metric_type", details=True)
        else:
            params = ["name", "group", "type"]
            mappings = {}
            aliases = {"group": "group_name", "type": "metric_type"}
            data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
            uri = "%s/services/metricstypes" % self.baseuri
            res = self.cmp_get(uri, data=data)
            headers = [
                "uuid",
                "id",
                "name",
                "group_name",
                "metric_type",
                "measure_unit",
                "status",
                "creation",
                "expiration",
                "active",
            ]
            fields = [
                "uuid",
                "id",
                "name",
                "group_name",
                "metric_type",
                "measure_unit",
                "status",
                "date.creation",
                "date.expiration",
                "active",
            ]
            self.app.render(res, key="metric_types", headers=headers, fields=fields, maxsize=45)

    @ex(
        help="add service metric type",
        description="This CLI command is used to add a new service metric type to the monitoring system. The 'beehive bu service-metrics type-add' command does not require any arguments as it will launch an interactive prompt to gather the details of the new metric type being added such as the name, unit of measure, aggregation method and more. Once provided, the new metric type will be created and available for association to services and collection of metrics.",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "metric type name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "metric type description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["group"],
                    {
                        "help": "metric type group",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["type"],
                    {
                        "help": "metric type. Supported values: CONSUME|BUNDLE|OPT_BUNDLE|PROF_SERVICE",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["unit"],
                    {
                        "help": "metric type unit",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["status"],
                    {
                        "help": "metric type status",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-active"],
                    {
                        "help": "metric type active",
                        "action": "store",
                        "type": bool,
                        "default": True,
                    },
                ),
                (
                    ["-limits"],
                    {
                        "help": 'json file with limit definition.Ex. {"limits" : [{ "name" : "LimitCPU", '
                        '"desc" : "LimitCPU", "value": 2.0, "metric_type_id" : "1" }]}',
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def type_add(self):
        name = self.app.pargs.name
        metric_type = self.app.pargs.type
        desc = self.app.pargs.desc
        group_name = self.app.pargs.group
        measure_unit = self.app.pargs.unit
        data_json = self.app.pargs.limits
        status = self.app.pargs.status

        limits = []
        if data_json is not None:
            limits = load_config(data_json).get("limits", [])
        data = {
            "metric_type": {
                "name": name,
                "metric_type": metric_type,
                "group_name": group_name,
                "desc": desc,
                "measure_unit": measure_unit,
                "limits": limits,
                "status": status,
            }
        }
        uri = "%s/services/metricstypes" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "add service metric type %s" % res})

    # @ex(
    #     help="update service metric type",
    #     description="update service metric type",
    #     arguments=ARGS(
    #         [
    #             (
    #                 ["id"],
    #                 {
    #                     "help": "metric type id",
    #                     "action": "store",
    #                     "type": str,
    #                     "default": None,
    #                 },
    #             ),
    #             (
    #                 ["-name"],
    #                 {
    #                     "help": "metric type name",
    #                     "action": "store",
    #                     "type": str,
    #                     "default": None,
    #                 },
    #             ),
    #             (
    #                 ["-desc"],
    #                 {
    #                     "help": "metric type description",
    #                     "action": "store",
    #                     "action": StringAction,
    #                     "type": str,
    #                     "nargs": "+",
    #                     "default": None,
    #                 },
    #             ),
    #             (
    #                 ["-group"],
    #                 {
    #                     "help": "metric type group",
    #                     "action": "store",
    #                     "type": str,
    #                     "default": "unknown",
    #                 },
    #             ),
    #             (
    #                 ["-type"],
    #                 {
    #                     "help": "metric type. Supported values: CONSUME|BUNDLE|OPT_BUNDLE|PROF_SERVICE",
    #                     "action": "store",
    #                     "type": str,
    #                     "default": None,
    #                 },
    #             ),
    #             (
    #                 ["-unit"],
    #                 {
    #                     "help": "metric type unit",
    #                     "action": "store",
    #                     "type": str,
    #                     "default": None,
    #                 },
    #             ),
    #             (
    #                 ["-status"],
    #                 {
    #                     "help": "metric type status",
    #                     "action": "store",
    #                     "type": str,
    #                     "default": None,
    #                 },
    #             ),
    #             (
    #                 ["-active"],
    #                 {
    #                     "help": "metric type active",
    #                     "action": "store",
    #                     "type": bool,
    #                     "default": True,
    #                 },
    #             ),
    #             (
    #                 ["-limits"],
    #                 {
    #                     "help": 'json file with limit definition.Ex. {"limits" : [{ "name" : "LimitCPU", '
    #                     '"desc" : "LimitCPU", "value": 2.0, "metric_type_id" : "1" }]}',
    #                     "action": "store",
    #                     "type": str,
    #                     "default": None,
    #                 },
    #             ),
    #         ]
    #     ),
    # )
    # def type_update(self):
    #     oid = self.app.pargs.id
    #     data = set_request_params(
    #         self.app.pargs,
    #         ["name", "desc", "group", "type", "unit", "status", "active"],
    #     )
    #     data_json = self.app.pargs.limits
    #     if data_json is not None:
    #         data["limits"] = load_config(data_json).get("limits", [])

    #     data = {"metric_type": data}
    #     uri = "%s/services/metricstypes/%s" % (self.baseuri, oid)
    #     self.cmp_put(uri, data={"metric_type": data})
    #     self.app.render({"msg": "update service metric type %s" % oid})

    # @ex(
    #     help="delete service metric types",
    #     description="delete service metric types",
    #     arguments=PARGS(
    #         [
    #             (
    #                 ["id"],
    #                 {
    #                     "help": "metric type id",
    #                     "action": "store",
    #                     "type": str,
    #                     "default": None,
    #                 },
    #             ),
    #         ]
    #     ),
    # )
    # def type_delete(self):
    #     instance_id = self.app.pargs.id
    #     uri = "%s/services/metricstypes" % (self.baseuri)
    #     res = self.cmp_delete(uri, data={"InstanceId": instance_id})
    #     # self.app.render({"msg": "delete service metric type %s" % instance_id})

    @ex(
        help="acquire metric",
        description="This CLI command acquires metric data from a Nivola CMP service. It does not require any arguments as it will acquire metrics for all services by default. The command connects to the Nivola CMP platform and retrieves the latest metrics captured for services that are being monitored.",
        arguments=ARGS(
            [
                (
                    ["-account"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "metric type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-service"],
                    {
                        "help": "metric service instance id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def acquire(self):
        account_id = self.app.pargs.account
        metric_type_id = self.app.pargs.type
        instance_id = self.app.pargs.service

        data = {"acquire_metric": {}}
        # 'metric_type_id': metric_type_id,
        #     'account_id': account_id,
        #     'service_instance_id': instance_id
        # }
        # }
        if account_id is not None:
            data["acquire_metric"]["account_id"] = account_id
        if metric_type_id is not None:
            data["acquire_metric"]["metric_type_id"] = metric_type_id
        if instance_id is not None:
            data["acquire_metric"]["service_instance_id"] = instance_id

        uri = "%s/services/metrics/acquire" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "acquire metric with task %s" % res})


class ServiceJobSchedulerController(ServiceControllerChild):
    class Meta:
        label = "service_schedules"
        description = "service schedule management"
        help = "service schedule management"

    @ex(
        help="list service job schedule",
        description="This command lists the service job schedules.",
        example="beehive bu service-schedules get -id <uuid> -e <env> ",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "job schedule id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "job schedule name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-job_name"],
                    {
                        "help": "job schedule job name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-job_id"],
                    {
                        "help": "job schedule job id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "job schedule type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-metric_type"],
                    {
                        "help": "job schedule metric type",
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
            uri = "%s/services/job_schedules/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("job_schedule")
                params = res.pop("schedule_params", {})
                self.app.render(res, details=True)
                self.c("\nparams", "underline")
                self.app.render(params, details=True)
            else:
                self.app.render(res, key="job_schedule", details=True)
        else:
            params = ["name", "job_name", "job_id", "type", "metric_type"]
            mappings = {}
            aliases = {
                "type": "schedule_type",
            }
            data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
            uri = "%s/services/job_schedules" % self.baseuri
            res = self.cmp_get(uri, data=data)
            headers = ["id", "name", "job name", "type", "args", "schedule_params"]
            fields = [
                "uuid",
                "name",
                "job_name",
                "schedule_type",
                "job_args",
                "schedule_params",
            ]
            self.app.render(res, key="job_schedule", headers=headers, fields=fields, maxsize=45)

    @ex(
        help="list service job schedule",
        description="This command lists the service job schedules.",
        example="beehive bu service-schedules get -id <uuid> -e <env> ",
        arguments=ARGS(),
    )
    def add_example(self):
        data = {
            "retry": False,
            "desc": "acquire metrics for account",
            "schedule_type": "crontab",
            "job_args": ["*", {}],
            "retry_policy": {},
            "relative": False,
            "job_options": {},
            "job_kvargs": {},
            "schedule_params": {
                "day_of_month": "*",
                "minute": "*/5",
                "day_of_week": "*",
                "hour": "*",
                "month_of_year": "*",
            },
            "job_name": "beehive_service.task.metrics.acquire_service_metrics",
            "name": "acquire_metric",
        }
        self.app.render(data, details=True)

    @ex(
        help="add service job schedule",
        description="This CLI command is used to add a new service job schedule to the beehive service scheduler. The service scheduler allows scheduling recurring jobs that run services or tasks on a defined schedule. This add subcommand does not require any arguments as all schedule details will need to be provided interactively after running the command.",
        arguments=ARGS(
            [
                (
                    ["config"],
                    {
                        "help": "job schedule config file",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add(self):
        filedata = self.app.pargs.config

        if filedata is not None:
            data = load_config(filedata)

        uri = "%s/services/job_schedules" % self.baseuri
        res = self.cmp_post(uri, data={"job_schedule": data})
        self.app.render({"msg": "add job schedule %s" % res})

    @ex(
        help="delete service job schedule",
        description="This command deletes a service job schedule. Service schedules are used to automate recurring jobs like backups, deployments etc. on a scheduled basis. Since this command deletes the schedule, any future scheduled jobs for that service will not run.",
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "job schedule id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = "%s/services/job_schedules/%s" % (self.baseuri, oid)
        self.cmp_delete(uri)
        self.app.render({"msg": "delete job schedule %s" % oid})

    def __exec_schedule_cmd(self, cmd):
        oid = self.app.pargs.oid
        uri = "%s/services/job_schedules/%s/%s" % (self.baseuri, oid, cmd)
        res = self.cmp_put(uri)
        self.app.render({"msg": "exec %s job_schedule %s " % (cmd, res)})

    @ex(
        help="start service job schedule",
        description="This command starts an existing service job schedule. Service schedules allow running jobs on a recurring basis like daily, weekly etc. This command requires no arguments as it simply starts the existing schedule to begin running jobs based on the schedule configuration.",
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "job schedule id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def start(self):
        self.__exec_schedule_cmd("start")

    @ex(
        help="stop service job schedule",
        description="This command stops a service job schedule that was previously created. Service schedules allow running jobs on a recurring basis like daily, weekly etc. This command stops the execution of the scheduled job so it does not run on the scheduled intervals anymore.",
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "job schedule id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def stop(self):
        self.__exec_schedule_cmd("stop")

    @ex(
        help="restart service job schedule",
        description="This command is used to restart the service job schedules on the Nivola CMP platform. Service schedules are used to automate recurring jobs like backups, deployments etc. Restarting the schedules would trigger the first run immediately and reset the schedule times.",
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "job schedule id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def restart(self):
        self.__exec_schedule_cmd("restart")


class ServiceAggregateConsumesController(ServiceControllerChild):
    class Meta:
        label = "service_consumes"
        description = "service consume management"
        help = "service consume management"

    @ex(
        help="list service job schedule",
        description="This command lists the service job schedules.",
        example="beehive bu service-schedules get -id <uuid> -e <env> ",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "consume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "consume type id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-account"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-aggr_type"],
                    {
                        "help": "aggregation type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-period"],
                    {
                        "help": "aggregation period",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-task"],
                    {
                        "help": "execution task",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-date_start"],
                    {
                        "help": "start date",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-date_end"],
                    {
                        "help": "stop date",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        params = [
            "id",
            "type",
            "instance",
            "account",
            "aggr_type",
            "period",
            "task",
            "date_start",
            "date_end",
        ]
        mappings = {}
        aliases = {
            "id": "id",
            "type": "metric_type_id",
            "instance": "instance_oid",
            "account": "account_oid",
            "aggr_type": "aggregation_type",
            "period": "period",
            "task": "job_id",
            "date_start": "evaluation_date_start",
            "date_end": "evaluation_date_end",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/services/consumes" % self.baseuri
        res = self.cmp_get(uri, data=data)
        headers = [
            "id",
            "type_id",
            "consumed",
            "cost",
            "account",
            "instance",
            "aggr_type",
            "period",
            "job_id",
            "date",
        ]
        fields = [
            "id",
            "type_id",
            "consumed",
            "cost",
            "account_id",
            "service_instance_id",
            "aggregation_type",
            "period",
            "job_id",
            "evaluation_date",
        ]
        self.app.render(res, key="consume", headers=headers, fields=fields, maxsize=45)

    @ex(
        help="generate aggregated consume",
        description="This command aggregates the service consumption data over a given period. The required 'period' argument specifies the aggregation period which can be specified in year-month or year-month-day format like yyyy-mm or yyyy-mm-dd. This generates a report of the total consumption aggregated for that specified period.",
        arguments=ARGS(
            [
                (
                    ["period"],
                    {
                        "help": "aggregation period. Ex. YYYY-MM o YYYY-MM-GG",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def aggregate(self):
        period = self.app.pargs.period
        # account_id = self.get_arg(name='account', keyvalue=True)
        # metric_type_id = self.get_arg(name='metric_type_id', keyvalue=True)
        # overwrite = self.get_arg(name='overwrite', keyvalue=True)
        # instance_id = self.get_arg(name='instance_id', keyvalue=True)

        data = {
            "consume": {
                "aggregation_type": "daily",
                "period": period,
                # 'metric_type_id': metric_type_id,
                # 'account_id': account_id,
                # 'service_instance_id': instance_id,
                # 'overwrite': overwrite
            }
        }

        uri = "%s/services/consumes/generate" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "run daily consume aggregation for period %s" % period})


# class ServiceAggregateCostsController(ServiceControllerChild):
#     AGGREGATION_COST_TYPE = ['daily', 'monthly']
#
#     class Meta:
#         label = 'service.consumes'
#         aliases = ['consumes']
#         aliases_only = True
#         description = "Service Consume management"
#
#     @expose(aliases=['list [field=value]'], aliases_only=True)
#     @check_error
#     def list(self):
#         """List all service consumes
#
# fields:
#   id                    consume id
#   day
#   value
#   metric_num
#   instance
#   account
#   metric_type
#   job_id"""
#         params = self.get_query_params(*self.app.pargs.extra_arguments)
#
#         header_field = {
#             'id': 'id',
#             'type_id': 'metric_type_id',
#             'instance': 'instance_oid',
#             'account': 'account_oid',
#             'aggr_type': 'aggregation_type',
#             'period': 'period',
#             'job_id': 'job_id',
#             'date_start': 'evaluation_date_start',
#             'date_end': 'evaluation_date_end',
#         }
#         data = self.get_list_default_arg()
#         for k in header_field:
#             par = params.get(k, None)
#             if par is not None:
#                 if k.startswith('date_'):
#                     g, m, y = par.split('-')
#                     data[header_field[k]] = datetime(int(y), int(m), int(g))
#                 else:
#                     data[header_field[k]] = par
#
#         uri = '%s/services/consumes' % self.baseuri
#         res = self._call(uri, 'GET', data=urlencode(data))
#         headers = ['id', 'type_id', 'consumed', 'cost', 'account', 'instance', 'aggr_type', 'period',
#                    'job_id', 'date']
#         fields = ['id', 'type_id', 'consumed', 'cost', 'account_id', 'service_instance_id', 'aggregation_type',
#                   'period', 'job_id', 'evaluation_date']
#         self.result(res, key='consume', headers=headers, fields=fields)
#
#     #     @expose(aliases=['get <id>'], aliases_only=True)
#     #     @check_error
#     #     def get(self):
#     #         """Get service consume
#     #
#     # fields:
#     #   id                    consume id"""
#     #         value = self.get_arg(name='id')
#     #         uri = '%s/services/consumes/%s' % (self.baseuri, value)
#     #         res = self._call(uri, 'GET')
#     #         self.result(res, key='consume', details=True)
#
#     #     @expose(aliases=['list-ext [field=value]'], aliases_only=True)
#     #     @check_error
#     #     def list_ext(self):
#     #         """List all service consumes
#     #
#     # fields:
#     #   id                    consume id
#     #   type
#     #   num
#     #   root_id
#     #   instance_id
#     #   account_id
#     #   job_id
#     #   date_start
#     #   date_end"""
#     #         params = self.get_query_params(*self.app.pargs.extra_arguments)
#     #
#     #         header_field = {
#     #             'id': 'id',
#     #             'type': 'metric_type_name',
#     #             'num': 'metric_num',
#     #             'root_id': 'instance_parent_id',
#     #             'instance_id': 'instance_id',
#     #             'account_id': 'account_id',
#     #             'job_id': 'job_id',
#     #             'date_start': 'extraction_date_start',
#     #             'date_end': 'extraction_date_end',
#     #         }
#     #         data = self.get_query_params(*self.app.pargs.extra_arguments)
#     #         for k in header_field:
#     #             par = params.get(k, None)
#     #             if par is not None:
#     #                 if k.startswith('date_'):
#     #                     y, m, g = par.split('-')
#     #                     data.pop(k)
#     #                     data[header_field[k]] = datetime(int(y), int(m), int(g))
#     #                 else:
#     #                     data.pop(k)
#     #                     data[header_field[k]] = par
#     #
#     #         uri = '%s/services/consume_views' % self.baseuri
#     #         res = self._call(uri, 'GET', data=urlencode(data))
#     #         self.result(res, key='metric_consume',
#     #                     headers=['id', 'eval_date', 'type', 'value', 'num', 'instance_id', 'account_id', 'job_id'],
#     #                     fields=['metric_id', 'extraction_date', 'type_name', 'value', 'metric_num', 'instance_id',
#     #                             'account_id', 'job_id'])
#     #
#     #     @expose(aliases=['get-ext <id>'], aliases_only=True)
#     #     @check_error
#     #     def get_ext(self):
#     #         """Get service catalog by value id or uuid
#     #         """
#     #         value = self.get_arg(name='id')
#     #         uri = '%s/services/consume_views/%s' % (self.baseuri, value)
#     #         res = self._call(uri, 'GET')
#     #         self.result(res, key='metric_consume',
#     #                     headers=['id', 'eval_date', 'type', 'value', 'num', 'instance', 'account', 'job_id'],
#     #                     fields=['metric_id', 'extraction_date', 'type_name', 'value', 'metric_num', 'instance_id',
#     #                             'account_id', 'job_id'])
#
#     #     @expose(aliases=['add <id> <consumed> <cost> <instance_id> <aggr_type> <period> <job_id> [field=..]'],
#     #             aliases_only=True)
#     #     @check_error
#     #     def add(self):
#     #         """Add consume
#     #
#     # fields:
#     #   id                    consume id
#     #   consumed
#     #   cost
#     #   instance_id
#     #   aggr_type
#     #   period
#     #   job_id
#     #   """
#     #         metric_type_id = self.get_arg(name='metric_type_id')
#     #         consumed = self.get_arg(name='consumed')
#     #         cost = self.get_arg(name='cost')
#     #         instance_oid = self.get_arg(name='instance_id')
#     #         aggregation_type = self.get_arg(name='aggr_type')
#     #         period = self.get_arg(name='period')
#     #         job_id = self.get_arg(name='job_id', keyvalue=True)
#     #         evaluation_date = self.get_arg(name='date', default=format_date(datetime.today()), keyvalue=True)
#     #
#     #         data = {
#     #             'consume': {
#     #                 'metric_type_id': metric_type_id,
#     #                 'consumed': consumed,
#     #                 'cost': cost,
#     #                 'service_instance_oid': instance_oid,
#     #                 'aggregation_type': aggregation_type,
#     #                 'period': period,
#     #                 'job_id': job_id,
#     #                 'evaluation_date':evaluation_date
#     #             }
#     #         }
#     #
#     #         uri = '%s/services/consumes' % self.baseuri
#     #         res = self._call(uri, 'POST', data=data)
#     #         logger.info('Add consume: %s' % truncate(res))
#     #         res = {'msg': 'Add ggregate cost %s' % res}
#     #         self.result(res, headers=['msg'])
#     #
#     #     @expose(aliases=['batch_delete [field=..]'], aliases_only=True)
#     #     @check_error
#     #     def batch_delete(self):
#     #         """Batch delete consumes
#     #
#     # fields:
#     #   id                    consume id
#     #   instance
#     #   aggr_type
#     #   period
#     #   job_id
#     #   date_start
#     #   date_end
#     #   limit
#     #   """
#     #         data = {
#     #             'consume':{
#     #                 'metric_type_id': self.get_arg(name='id', keyvalue=True),
#     #                 'service_instance_id': self.get_arg(name='instance', keyvalue=True),
#     #                 'aggregation_type': self.get_arg(name='aggr_type', keyvalue=True),
#     #                 'period': self.get_arg(name='period', keyvalue=True),
#     #                 'job_id': self.get_arg(name='job_id', keyvalue=True),
#     #                 'limit': self.get_arg(name='limit', default=1000, keyvalue=True),
#     #                 'evaluation_date_start':self.get_arg(name='date_start', keyvalue=True),
#     #                 'evaluation_date_end':self.get_arg(name='date_end', keyvalue=True)
#     #             }
#     #         }
#     #
#     #         uri = '%s/services/consumes' % self.baseuri
#     #         res = self._call(uri, 'DELETE', data=data)
#     #         logger.info(res)
#     #         res = {'msg': 'Delete n. %s aggregation costs' % res.get('deleted')}
#     #         self.result(res, headers=['msg'])
#
#     @expose(aliases=['aggregate <aggr-type> [field=..]'], aliases_only=True)
#     @check_error
#     def aggregate(self):
#         """Generate consume
#
# fields:
#   aggr-type             aggragation type. Can by 'daily' or 'monthly'
#   account               account id or composed name (org.div.account) [optional]
#   overwrite             force rewrite of an consume [optional]
#   period                aggreagate period. Ex. YYYY-MM o YYYY-MM-GG [optional]"""
#         aggregation_type = self.get_arg(name='aggr-type')
#         period = self.get_arg(name='period', required=False, keyvalue=True)
#         # account_id = self.get_arg(name='account', keyvalue=True)
#         # metric_type_id = self.get_arg(name='metric_type_id', keyvalue=True)
#         # overwrite = self.get_arg(name='overwrite', keyvalue=True)
#         # instance_id = self.get_arg(name='instance_id', keyvalue=True)
#
#         if aggregation_type not in self.AGGREGATION_COST_TYPE:
#             raise Exception('aggr-type can be %s' % self.AGGREGATION_COST_TYPE)
#
#         data = {
#             'consume': {
#                 'aggregation_type': aggregation_type,
#                 'period': period,
#                 # 'metric_type_id': metric_type_id,
#                 # 'account_id': account_id,
#                 # 'service_instance_id': instance_id,
#                 # 'overwrite': overwrite
#             }
#         }
#
#         uri = '%s/services/consumes/generate' % self.baseuri
#         res = self._call(uri, 'POST', data=data)
#         logger.info('consume: %s' % truncate(res))
#         res = {'msg': 'Aggregate task %s' % res}
#         self.result(res, headers=['msg'], maxsize=80)
