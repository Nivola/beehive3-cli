# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from os import path
from sys import version
from typing import Union, Dict
from json import loads
from urllib.parse import urlencode
from yaml import safe_dump, safe_load
from cement import ex

from beecell.types.type_string import str2bool, truncate
from beecell.simple import set_request_params
from beehive3_cli.core.controller import CliController, PARGS, ARGS, StringAction
from beehive3_cli.core.util import load_config
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild
from beehive3_cli.plugins.platforms.util.customize_plugins.service import ServiceCustomizePlugin
from beehive3_cli.translate import _


class ServiceController(CliController):
    class Meta:
        label = "bu_service"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("business service management")
        help = _("business service management")


class ServiceControllerChild(BusinessControllerChild):
    class Meta:
        stacked_on = "bu"
        stacked_type = "nested"


class ServiceTypeController(ServiceControllerChild):
    class Meta:
        label = "service_types"
        description = _("service type management")
        help = _("service type management")

    @ex(
        help=_("get service type plugins"),
        description=_(
            "This command is used to retrieve the available service type plugins that can be used "
            "to define services in Nivola CMP. Service type plugins define the schema and lifecycle "
            "of different types of services that can be created and managed in Nivola CMP. "
            "Executing this command without any arguments will return a list of all "
            "available service type plugins along with their description and metadata."
        ),
        example="beehive bu service-types plugin-get",
        arguments=PARGS([]),
    )
    def plugin_get(self):
        """List all plugin_types"""
        params = []
        mappings = {}
        data = self.format_paginated_query(params, mappings=mappings)
        uri = f"{self.baseuri}/servicetypes/plugintypes"
        res = self.cmp_get(uri, data=data)
        self.app.render(res, key="plugintypes", headers=["id", "name", "objclass"], maxsize=200)

    @ex(
        help=_("get service types"),
        description=_(
            "This command is used to retrieve all the available service types from the Nivola CMP platform. "
            "Service types are categories or types of services that can be provisioned through the platform, "
            "like compute, storage etc. "
            "Without any arguments, this command will return all the service types. "
            "Optionally an ID can be passed to get details of a specific service type."
        ),
        example="beehive bu service-types get -id 36",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("entity id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": _("authorization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-version"],
                    {
                        "help": _("type version"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": _("type status"),
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
            uri = f"{self.baseuri}/servicetypes/{oid}"
            res = self.cmp_get(uri).get("servicetype")

            if self.is_output_text():
                self.app.render(res, details=True)
            else:
                self.app.render(res, key="resource", details=True)
        else:
            params = ["name", "objid", "flag_container", "version", "status"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/servicetypes"
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
        help=_("add service type"),
        description=_(
            "This command allows you to add a new service type to the system by specifying its name and "
            "the Python class that implements it. "
            "The name argument is used to identify the service type in the system. "
            "The objclass argument specifies the full Python path to the class that implements this service type."
        ),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("service type name"), "action": "store", "type": str},
                ),
                (
                    ["objclass"],
                    {"help": _("python class full path"), "action": "store", "type": str},
                ),
                (
                    ["-version"],
                    {
                        "help": _("service type version"),
                        "action": "store",
                        "type": str,
                        "default": "v1.0",
                    },
                ),
                (
                    ["-flag_container"],
                    {
                        "help": _("if True service is a container"),
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": _("service type status"),
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
        flag_container = self.app.pargs.flag_container
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
        uri = f"{self.baseuri}/servicetypes"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"Add service type {res}"})

    @ex(
        help=_("update service type"),
        description=_(
            "This command updates an existing service type in Nivola CMP. "
            "It requires the service type id, name and Python class full path "
            "as required arguments to identify and update the service type details."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("service type id"), "action": "store", "type": str}),
                (
                    ["-name"],
                    {"help": _("service type name"), "action": "store", "type": str},
                ),
                (
                    ["-objclass"],
                    {"help": _("python class full path"), "action": "store", "type": str},
                ),
                (
                    ["-version"],
                    {
                        "help": _("service type version"),
                        "action": "store",
                        "type": str,
                        "default": "v1.0",
                    },
                ),
                (
                    ["-flag_container"],
                    {
                        "help": _("if True service is a container"),
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": _("service type status"),
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
        uri = f"{self.baseuri}/servicetypes/{oid}"
        self.cmp_put(uri, data={"servicetype": data})
        self.app.render({"msg": f"update service type {oid} with data {data}"})

    @ex(
        help=_("delete service type"),
        description=_(
            "This command deletes service type(s) from the Nivola CMP platform. "
            "The 'ids' argument is required and accepts one or more service type ids "
            "to delete as a space separated list."
        ),
        arguments=ARGS(
            [
                (["ids"], {"help": _("service type id"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        value = self.app.pargs.id
        uri = f"{self.baseuri}/servicetypes/{value}"
        self.cmp_delete(uri, entity=f"service type {value}")

    @ex(
        help=_("get service type process"),
        description=_(
            "This command retrieves the details of a specific service type process based on "
            "the provided service type id. "
            "It requires the id of the service type as the only required argument to "
            "uniquely identify and return the process details of that service type."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("service type id"), "action": "store", "type": str}),
            ]
        ),
    )
    def process_get(self):
        value = self.app.pargs.id
        uri = f"{self.baseuri}/serviceprocesses"
        res = self.cmp_get(uri, data=f"service_type_id={value}").get("serviceprocesses", [])
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
        help=_("set service type process"),
        description=_(
            "This command sets the process method for a specific service type. "
            "It requires the service type id and process method name as "
            "required arguments to identify and update the correct service type record."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("service type id"), "action": "store", "type": str}),
                (
                    ["method"],
                    {
                        "help": _("service type process method"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-name"],
                    {"help": _("name"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-desc"],
                    {
                        "help": _("description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-process"],
                    {
                        "help": _("process"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-template"],
                    {
                        "help": _("template file"),
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
            uri = f"{self.baseuri}/servicetypes/{typeoid}"
            res = self.cmp_get(uri).get("servicetype", {})
            typeid = res.get("id", typeid)
            if typeid is None:
                raise Exception(f"could not found a type whose oid is {typeoid}")

        uri = f"{self.baseuri}/serviceprocesses"
        res = self.cmp_get(uri, data=f"service_type_id={typeid}&method_key={method}").get("serviceprocesses", [])

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
                desc = f"description-{name}"
            if process is None:
                process = "invalid_key"
            if template is None:
                template = "{}"


        if template.startswith("@"):
            filename = template[1:]
            if path.isfile(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    template = f.read()
            else:
                raise Exception(f"Jinja template {filename} is not a file")

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
        if prev is None:
            uri = f"{self.baseuri}/serviceprocesses"
            res = self.cmp_post(uri, data=data)
            self.app.render(res)
        else:
            uri = f"{self.baseuri}/serviceprocesses/{prev['uuid']}"
            res = self.cmp_put(uri, data=data)
            self.app.render(res)


class ServiceStatusController(ServiceControllerChild):
    class Meta:
        label = "service_status"
        description = "service status management"
        help = "service status management"

    @ex(
        help="get service status",
        description="This command is used to retrieve a service status from the Nivola CMP platform.",
        example="beehive bu service-status get; beehive bu service-status get -id ACTIVE",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("entity id"),
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
            uri = f"{self.baseuri}/servicestatus/{oid}"
            res = self.cmp_get(uri).get("service_status")
            self.app.render(res, details=True)
        else:
            params = ["name"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/servicestatus"
            res = self.cmp_get(uri, data=data)
            headers = [
                "id",
                "name",
                "desc",
            ]
            self.app.render(
                res,
                key="service_statuses",
                headers=headers,
                maxsize=200,
            )


class ServiceDefinitionController(ServiceControllerChild):
    class Meta:
        label = "service_defs"
        description = _("service definition management")
        help = _("service definition management")

    @ex(
        help=_("get product codes"),
        description=_("This command retrieves product codes"),
        example="beehive bu get-product-code STILO",
        arguments=PARGS(
            [
                (
                    ["filter_name"],
                    {
                        "help": _("filter name"),
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
        uri = f"{self.baseuri}/product_codes"
        res = self.cmp_get(uri, data=data)
        print(res)

    @ex(
        help=_("get service definitions"),
        description=_(
            "This command retrieves service definitions from the service registry. "
            "Service definitions describe the interfaces, endpoints and other metadata for microservices. "
            "By default, all definitions are returned. "
            "The -id option can be used to retrieve a single definition by ID."
        ),
        example="beehive bu service-defs get; beehive bu service-defs get -id <uuid>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("entity id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": _("authorization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-version"],
                    {
                        "help": _("definition version"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": _("type status"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-plugintype"],
                    {
                        "help": _("serch for plugintype "),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["--tofile"],
                    {
                        "help": _(
                            "store output to a customization yaml file. In order to get or modify the cmp configuration"
                        ),
                        "action": "store_true",
                        "dest": "tofile",
                        "default": False,
                    },
                ),
                (
                    ["-o"],
                    {
                        "help": _("when --tofile specify filename "),
                        "action": "store",
                        "dest": "outfilename",
                        "type": str,
                        "default": "definitions",
                    },
                ),
            ]
        ),
    )
    def get(self):
        tofile: bool = self.app.pargs.tofile
        outfilename = self.app.pargs.outfilename
        oid = getattr(self.app.pargs, "id", None)
        service_types: Dict[str, str] = {}

        def get_service_types(st_id: Union[int, str]) -> str:
            """get service type name

            Args:
                id (Union[int,str]): _description_

            Returns:
                str: _description_
            """
            ret = service_types.get(str(st_id))
            if ret is None:
                st = self.cmp_get(f"{self.baseuri}/servicetypes/{st_id}").get("servicetype")
                service_types[str(st_id)] = st["name"]
                return service_types[str(st_id)]
            return ret

        if oid is not None:
            uri = f"{self.baseuri}/servicedefs/{oid}"
            definition = self.cmp_get(uri).get("servicedef")
            # get configs
            uri = f"{self.baseuri}/servicecfgs"
            config = self.cmp_get(uri, data=f"service_definition_id={oid}").get("servicecfgs", [{}])[0]
            params = config.pop("params", [])

            if self.is_output_text():
                self.app.render(definition, details=True)
                self.c("\nconfigs", "underline")
                self.app.render(params, details=True)

            else:
                definition["configs"] = params
                self.app.render(definition, key="resource", details=True)
            if tofile:
                stname = get_service_types(st_id=definition.get("service_type_id"))
                outdata = {
                    "configs": {
                        "service": {
                            "definitions": [
                                {
                                    "name": definition.get("name"),
                                    "desc": definition.get("desc"),
                                    "version": definition.get("version"),
                                    "status": definition.get("status"),
                                    "service_type_id": stname,
                                    "parent_id": definition.get("parent_id"),
                                    "priority": definition.get("priority"),
                                    "is_default": definition.get("is_default"),
                                    "configs": params,
                                }
                            ]
                        }
                    }
                }
                name = definition.get("name", outfilename).replace(".", "_")
                with open(f"{name}.yml", "w", encoding="utf-8") as o_stream:
                    safe_dump(outdata, stream=o_stream, sort_keys=False)
        else:
            params = ["name", "objid", "version", "status", "plugintype"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/servicedefs"
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
            if tofile:
                definitions = []
                for sdef in res.get("servicedefs", []):
                    stname = get_service_types(sdef.get("service_type_id"))
                    config = self.cmp_get(
                        f"{self.baseuri}/servicecfgs", data=f"service_definition_id={sdef['id']}"
                    ).get("servicecfgs", [{}])[0]
                    params = config.get("params", {})
                    definitions.append(
                        {
                            "name": sdef.get("name"),
                            "desc": sdef.get("desc"),
                            "version": sdef.get("version"),
                            "status": sdef.get("status"),
                            "service_type_id": stname,
                            "parent_id": sdef.get("parent_id"),
                            "priority": sdef.get("priority"),
                            "is_default": sdef.get("is_default"),
                            "configs": params,
                        }
                    )
                outdata = {"configs": {"service": {"definitions": definitions}}}

                with open(f"{outfilename}.yml", "w", encoding="utf-8") as o_stream:
                    safe_dump(outdata, stream=o_stream, sort_keys=False)

    @ex(
        help=_("add service definition"),
        description=_(
            "This command adds a new service definition to Nivola CMP. "
            "It requires the name, type and params of the service definition "
            "to be provided as required arguments. "
            "The name is used to uniquely identify the service definition, "
            "type specifies the type of service (e.g. 'http') and params "
            "contains configuration parameters for the service in JSON format."
        ),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("service definition name"), "action": "store", "type": str},
                ),
                (["type"], {"help": _("service type id"), "action": "store", "type": str}),
                (
                    ["params"],
                    {
                        "help": _("service definition params"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("service definition description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-version"],
                    {
                        "help": _("service definition version"),
                        "action": "store",
                        "type": str,
                        "default": "v1.0",
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": _("service definition status"),
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
        uri = f"{self.baseuri}/servicedefs"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add service definition {res}"})

        data = {
            "servicecfg": {
                "name": f"{name}-config",
                "desc": f"{name}-config",
                "service_definition_id": res["uuid"],
                "params": params,
                "params_type": "JSON",
                "version": version,
            }
        }
        uri = f"{self.baseuri}/servicecfgs"
        res = self.cmp_post(uri, data=data)
        self.app.render(f"Add service definition config: {res}")
    @ex(
        help=_("add Kms domain definition"),
        description=_(
            "This command adds a new service definition to Nivola which describe a Kms Domain. "
        ),
        arguments=ARGS(
            [
                (
                    ["domain"],
                    {"help": _("domain name"), "action": "store", "type": str},
                ),
                (
                    ["user"], 
                    {"help": _("domain administration user"), "action": "store", "type": str}
                ),
                (
                    ["--kms-env", "-ke"], 
                    {"help": _("domain environment"), "action": "store", "type": str, "dest":"kms_env", "default":"p"}
                ),
                (
                    ["password"],
                    {
                        "help": _("password"),
                        "action": "store",
                        "type": str,
                    },
                ),            
            ]
        ),
    )
    def add_kms_domain(self):
        # service_type_id = self.app.pargs.service_type
        domain = self.app.pargs.domain
        user = self.app.pargs.user
        password = self.app.pargs.password
        kms_env = self.app.pargs.kms_env
        kms_env
        name = f"KMS-DOMAIN-{domain}"
        desc = f"KMS DOMAIN {domain}"
        # status = self.app.pargs.status
        # parent_id = None
        # priority = None
        # version = "v1.0"
        # status = "ACTIVE"
        # read params from file

        data = {
            "servicedef": {
                "name": name,
                "version": "v1.0",
                "desc": desc,
                "status": "ACTIVE",
                "service_type_id": "VirtualServiceSync",
                "parent_id": None,
                "priority": None,
            }
        }
        uri = f"{self.baseuri}/servicedefs"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add service definition {res}"})

        data = {
            "servicecfg": {
                "name": f"{name}-config",
                "desc": f"{name}-config",
                "service_definition_id": res["uuid"],
                "params": {
                    "kms_domain": domain,
                    "kms_env": kms_env,
                    "kms_domain_user": user,
                    "kms_domain_pwd": password,
                },
                "params_type": "JSON",
                "version": "v1.0",
            }
        }
        uri = f"{self.baseuri}/servicecfgs"
        res = self.cmp_post(uri, data=data)
        self.app.render(f"Add service definition config: {res}")

    @ex(
        help=_("update service definition"),
        description=_(
            "This command updates an existing service definition in Nivola CMP. "
            "It requires the service definition id and name as required arguments "
            "to identify and update the correct definition. "
            "The updated definition data is passed via stdin in JSON format."
        ),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("service definition id"), "action": "store", "type": str},
                ),
                (
                    ["-name"],
                    {"help": _("service definition name"), "action": "store", "type": str},
                ),
                (
                    ["-desc"],
                    {
                        "help": _("service definition description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": _("service definition status"),
                        "action": "store",
                        "type": str,
                        "default": "ACTIVE",
                    },
                ),
                (
                    ["-config"],
                    {
                        "help": _("service definition config key:value"),
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
        uri = f"{self.baseuri}/servicedefs/{oid}"
        self.cmp_put(uri, data={"servicedef": data})
        self.app.render({"msg": f"update service definition {oid} with data {data}"})

    @ex(
        help=_("delete service definition"),
        description=_(
            "This command deletes a service definition from the system by specifying its unique id. "
            "The service definition id is a required argument for this command to identify "
            "which existing service definition to delete from the system."
        ),
        example="beehive bu service-defs delete <uuid>; beehive bu service-defs delete <uuid>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("service definition id"), "action": "store", "type": str},
                )
            ]
        ),
    )
    def delete(self):
        value = self.app.pargs.id
        uri = f"{self.baseuri}/servicedefs/{value}"
        self.cmp_delete(uri, entity=f"service definition {value}")

    @ex(
        help=_("Applay a service definition from customization file"),
        description=_("This command create or modify the definitions from a customzation file"),
        example="",
        arguments=ARGS(
            [
                (
                    ["filename"],
                    {"help": _("service definition customization file (yml)"), "action": "store", "type": str},
                )
            ]
        ),
    )
    def applay(self):
        class Manager:
            def __init__(self, controller):
                self.controller = controller

        dry = self.app._parse_args.dryrun
        filename = self.app.pargs.filename
        with open(filename, "r", encoding="utf-8") as r_stream:
            data = safe_load(r_stream)

        srvcustom = ServiceCustomizePlugin(Manager(self))
        srvcustom.run_definitions(data, dry=dry)


class ServiceInstanceController(ServiceControllerChild):
    class Meta:
        label = "service_insts"
        description = _("service instance management")
        help = _("service instance management")

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
        help=_("get service instances"),
        description=_(
            "This command gets service instances. It retrieves service instances without any filtering criteria."
        ),
        example="beehive bu service-insts get -id <uuid> -e <env>; beehive bu service-insts get -id <uuid>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("entity id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-legacy"],
                    {"help": _("use legacy v1"), "action": "store_true", "default": False},
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": _("authorization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-version"],
                    {
                        "help": _("definition version"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": _("type status"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-resource"],
                    {
                        "help": _("resource uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("parent service instance"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-plugintype"],
                    {
                        "help": _("service plugintype"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("comma separated tag list"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-iscontainer"],
                    {
                        "help": _("if True show only container service instance"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
                (
                    ["-details"],
                    {
                        "help": _("if False it does not show details (resource)"),
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
            uri = f"/{version}/nws/serviceinsts/{oid}"
            res = self.cmp_get(uri).get("serviceinst")

            if self.is_output_text():
                config = res.pop("config")
                self.app.render(res, details=True)

                # get configs
                self.c("\nconfigs", "underline")
                self.app.render(config, details=True)

                self.c("\nlinks", "underline")
                uri = f"{self.baseuri}/links"
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
                    uri = f"/v1.0/nrs/entities/{resource_uuid}"
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
            uri = f"/{version}/nws/serviceinsts"

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
        help=_("import service instance from resource"),
        description=_(
            "This command imports a service instance from a resource. "
            "It requires the service instance name, account id, "
            "plugin type of the service instance and plugin type "
            "of the container to be provided as required arguments."
        ),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("service instance name"), "action": "store", "type": str},
                ),
                (
                    ["-desc"],
                    {
                        "help": _("service instance description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (["account"], {"help": _("account id"), "action": "store", "type": str}),
                (
                    ["plugintype"],
                    {
                        "help": _("plugin type of the service instance"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["container_plugintype"],
                    {
                        "help": _("plugin type of the container"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-service_definition_id"],
                    {
                        "help": _("service definition id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["resource"],
                    {
                        "help": _("resource id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("parent service instance id"),
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
        self.app.render({"msg": f"import service plugin instance {name}"})

    @ex(
        help=_("check service instance"),
        description=_(
            "This command checks the status of service instances running on Nivola Cloud. "
            "It allows the user to verify if their services are running properly "
            "without having to log into the platform directly. "
            "The command does not require any arguments as it will check all service instances by default. "
            "The output provides the name, status and other details of each service instance "
            "so the user can easily monitor them."
        ),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("service instance id"),
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
        uri = f"/v2.0/nws/serviceinsts/{oid}/check"
        res = self.cmp_get(uri).get("serviceinst")
        self.app.render(res, details=True)

    @ex(
        help=_("update service instance"),
        description=_(
            "This CLI command updates an existing service instance in Nivola Cloud. "
            "The service instance is identified by its name or ID. "
            "No arguments are required as the instance details will need to be "
            "provided via a configuration file or interactive prompts."
        ),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("service instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-resource_uuid"],
                    {
                        "help": _("resource uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("parent service instance"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("service instance name"),
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
        uri = f"/v2.0/nws/serviceinsts/{oid}"
        self.cmp_put(uri, data={"serviceinst": data})
        self.app.render({"msg": f"update service plugin instance {oid}"})

    @ex(
        help=_("patch service instance"),
        description=_(
            "This CLI command patches or updates an existing service instance. "
            "Since there are no required arguments listed, it likely accepts the "
            "service instance ID or name as a parameter to identify which instance to "
            "update, along with other optional arguments to specify which attributes or "
            "fields of the instance should be modified."
        ),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("service instance id"),
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
        uri = f"/v2.0/nws/serviceinsts/{oid}"
        self.cmp_patch(uri, data={"serviceinst": {}})
        self.app.render({"msg": f"patch service plugin instance {oid}"})

    @ex(
        help=_("""update service instance forcing his status to "error" or "active" """),
        description=_("""update service instance forcing his status to "error" or "active" """),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("service instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["status"],
                    {
                        "help": _("""service instance status must be "active" or "error" """),
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
        uri = f"/v2.0/nws/serviceinsts/{oid}/status"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update service instance {oid} status with {status}"})

    @ex(
        help=_("delete service instance"),
        description=_(
            "This command deletes a service instance. "
            "It requires the service instance ID as a parameter to identify "
            "which instance to delete. "
            "The command also supports optional flags to specify the environment (-e) "
            "of the instance and assume yes (-y) without confirmation."
        ),
        example="beehive bu service-insts delete <uuid> -e <env>",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("service instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["--no-propagate"],
                    {
                        "help": _("do not propagate propagate delete to all cmp modules [default=true]"),
                        "action": "store_false",
                        "dest": "propagate",
                    },
                ),
                (
                    ["--force"],
                    {"help": _("if True force delete [default=false]"), "action": "store_true", "dest": "force"},
                ),
            ]
        ),
    )
    def delete(self):
        value = self.app.pargs.id
        # force = str2bool(self.app.pargs.force)
        # propagate = str2bool(self.app.pargs.propagate)
        force = self.app.pargs.force
        propagate = self.app.pargs.propagate

        uri = f"/v2.0/nws/serviceinsts/{value}"
        res = self.cmp_get(uri).get("serviceinst")

        plugintype = res["plugintype"]
        accountname = res["account"]["name"]
        uuid = res["uuid"]
        name = res["name"]
        if plugintype in [
            "ComputeService",
            "DatabaseService",
            "StorageService",
            "AppEngineService",
            "NetworkService",
            "LoggingService",
            "MonitoringService",
            "ContainerService",
        ]:
            print(f"Core service {plugintype} cannot be deleted")
            return
        print(f"you are about to delete a {plugintype} in  account {accountname} uuid {uuid}, and name {name}")
        if not propagate:
            msg = self.app.colored_text.yellow(
                "This command could leave the linked resources on the platform. Continue [y/n]? "
            )
            i = input(msg)
            if i != "y":
                return
            data = {"force": force, "propagate": propagate}
            uri = f"/v2.0/nws/serviceinsts/{value}"
            self.cmp_delete(uri, data=data, timeout=180, entity=f"service instance {value}")
        else:
            self.generic_service_delete(uuid=uuid, name=name, plugin=plugintype, force=force)

    @ex(
        help=_("add tag to service instance"),
        description=_(
            "This command allows adding one or more tags to a service instance. "
            "The tags argument requires a comma separated list of tag names "
            "that will be added to the specified service instance. "
            "Tags can be used to logically group and filter service instances for management purposes."
        ),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("service instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["tags"],
                    {
                        "help": _("comma separated list of tags"),
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
        uri = f"/v2.0/nws/serviceinsts/{value}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add tags {tags} to service instance {value}"})

    @ex(
        help=_("add tag to account's service instances"),
        description=_(
            "This command allows adding one or more tags to account's service instances. "
            "The tags argument requires a comma separated list of tag names that "
            "will be added to the specified service instance. "
            "Tags can be used to logically group and filter service instances for management purposes."
        ),
        arguments=PARGS(
            [
                (
                    ["account_id"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["tags"],
                    {
                        "help": _("comma separated list of tags"),
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
        uri = f"/v2.0/nws/serviceinsts/account/{account}"
        res = self.cmp_put(uri, data=data)
        num_services = res["num_services"]
        self.app.render(
            {"msg": f"added tags {tags} to {num_services} service instances of account {account_id}"}
        )

    @ex(
        help=_("delete tag from service instance"),
        description=_(
            "This command deletes one or more tags from a service instance. "
            "The tags argument requires a comma separated list of tag names to remove from the instance. "
            "This allows an operator to untag or remove labels from resources in the platform."
        ),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("service instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["tags"],
                    {
                        "help": _("comma separated list of tags"),
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
        uri = f"/v2.0/nws/serviceinsts/{value}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"delete tags {tags} from service instance {value}"})

    @ex(
        help=_("update resource entity config"),
        description=_("Update resource entity config"),
        example="beehive bu service-insts config-set <uuid> instance.ImageId -value <uuid>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
                (
                    ["config_key"],
                    {
                        "help": _("config key like config.key"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-value"],
                    {
                        "help": _("config value"),
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
        uri = f"/v2.0/nws/serviceinsts/{oid}/config"
        self.cmp_put(uri, data={"config": {"key": key, "value": value}})
        self.app.render({"msg": f"update service entity {oid} config"})

    @ex(
        help=_("get tag of service instance"),
        description=_(
            "This command retrieves the tag of a specific service instance "
            "by providing its id as a required argument. "
            "The service instance id is a unique identifier "
            "that can be used to fetch additional details like tags for that particular instance."
        ),
        example="beehive bu service-insts tag-get id 90; beehive bu service-insts tag-get",
        arguments=ARGS([(["id"], {"help": _("service instance id"), "action": "store", "type": str})]),
    )
    def tag_get(self):
        oid = self.app.pargs.id
        data = {"service": oid}
        uri = f"{self.baseuri}/tags"
        res = self.cmp_get(uri, data=data)

        fields = ["id", "name"]
        headers = ["id", "name"]
        self.app.render(res, key="tags", headers=headers, fields=fields, maxsize=45)


class ServiceLinkController(ServiceControllerChild):
    class Meta:
        label = "service_links"
        description = _("service link management")
        help = _("service link management")

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
        help=_("list service links"),
        description=_(
            "This command lists all the service links in the platform. "
            "Service links are used to connect services together and "
            "allow them to communicate securely. "
            "Without any additional parameters, this command will display all service links. "
            "The -id parameter can be used to filter the output to just a single service link "
            "by its unique identifier."
        ),
        example="beehive bu service-links get -id <uuid> -e <env> ",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("link uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("link name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-service"],
                    {
                        "help": _("start or end service uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("link type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": _("link authorization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("link tags"),
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
            uri = f"{self.baseuri}/links/{oid}"
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
            uri = f"{self.baseuri}/links"
            res = self.cmp_get(uri, data=data)

            self.app.render(
                res,
                key="links",
                headers=self._meta.headers,
                fields=self._meta.fields,
                maxsize=40,
            )

    @ex(
        help=_("add service link"),
        description=_(
            "This command adds a service link between two services by specifying "
            "the required arguments - service link name, account id, "
            "start service uuid and end service uuid. "
            "A service link defines the relationship between two services in "
            "an account and allows them to communicate with each other."
        ),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("service link name"), "action": "store", "type": str},
                ),
                (["account"], {"help": _("account id"), "action": "store", "type": str}),
                (
                    ["type"],
                    {
                        "help": _("service link type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["start_service"],
                    {"help": _("start service uuid"), "action": "store", "type": str},
                ),
                (
                    ["end_service"],
                    {"help": _("end service uuid"), "action": "store", "type": str},
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("service link attributes"),
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
        uri = f"{self.baseuri}/links"
        res = self.cmp_post(uri, data={"link": data})
        self.app.render({"msg": f"add service link {res['uuid']}"})

    @ex(
        help=_("update service link"),
        description=_(
            "This command updates an existing service link. "
            "It requires the service link uuid as the id argument to identify which service link to update."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("service link uuid"), "action": "store", "type": str}),
                (
                    ["-name"],
                    {
                        "help": _("service link name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("service link type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-start_service"],
                    {
                        "help": _("start service uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-end_service"],
                    {
                        "help": _("end service uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("service link attributes"),
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
        uri = f"{self.baseuri}/links/{oid}"
        self.cmp_put(uri, data={"link": data})
        self.app.render({"msg": f"update service link {oid}"})

    @ex(
        help=_("delete service links"),
        description=_(
            "This command deletes service links by their UUIDs. "
            "The 'ids' argument requires a comma separated list of "
            "service link UUIDs to delete as input. "
            "This allows deleting multiple service links with a single command."
        ),
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": _("comma separated service link uuids"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
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
            uri = f"{self.baseuri}/links/{oid}"
            if force is True:
                uri += "?force=true"
            self.cmp_delete(uri, entity=f"link {oid}")

    @ex(
        help=_("add tag to service link"),
        description=_(
            "This command adds a tag to an existing service link. "
            "It requires the service link id and the tag name as required arguments. "
            "The tag will be added to the service link with the provided id."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("service link id"), "action": "store", "type": str}),
                (["tag"], {"help": _("tag"), "action": "store", "type": str}),
            ]
        ),
    )
    def tag_add(self):
        value = self.app.pargs.id
        tag = self.app.pargs.tag
        data = {"link": {"tags": {"cmd": "add", "values": [tag]}}}
        uri = f"{self.baseuri}/links/{value}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add tag {tag} to service link {value}"})

    @ex(
        help=_("delete tag from service link"),
        description=_(
            "This command deletes a specific tag from a service link. "
            "The service link id and tag name that needs to be deleted "
            "must be provided as required arguments. "
            "This allows removing tags from service links as needed."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("service link id"), "action": "store", "type": str}),
                (["tag"], {"help": _("tag"), "action": "store", "type": str}),
            ]
        ),
    )
    def tag_del(self):
        value = self.app.pargs.id
        tag = self.app.pargs.tag
        data = {"link": {"tags": {"cmd": "delete", "values": [tag]}}}
        uri = f"{self.baseuri}/links/{value}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"delete tag {tag} from service link {value}"})

    @ex(
        help=_("get tag of service link"),
        description=_(
            "This command retrieves the tag of a service link by specifying its ID. "
            "The service link ID is a required argument for this command to work. "
            "It will return the tag associated with the given service link ID."
        ),
        arguments=ARGS([(["id"], {"help": _("service link id"), "action": "store", "type": str})]),
    )
    def tag_get(self):
        oid = self.app.pargs.id
        data = {"link": oid}
        uri = f"{self.baseuri}/tags"
        res = self.cmp_get(uri, data=data)

        fields = ["id", "name"]
        headers = ["id", "name"]
        self.app.render(res, key="tags", headers=headers, fields=fields, maxsize=45)


class ServiceTagController(ServiceControllerChild):
    class Meta:
        label = "service_tags"
        description = _("service tag management")
        help = _("service tag management")

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
        help=_("list service tags"),
        description=_(
            "This command lists all the service tags configured in the Nivola CMP platform. "
            "Service tags are used to group services for organizational and access control purposes. "
            "Without any additional options, this command will display all service tags and their "
            "associated services in the Nivola CMP deployment."
        ),
        arguments=PARGS(
            [
                (
                    ["-value"],
                    {
                        "help": _("tag value"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-service"],
                    {
                        "help": _("service id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-link"],
                    {
                        "help": _("service link id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-account"],
                    {
                        "help": _("account id"),
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
            uri = f"{self.baseuri}/tags/{oid}"
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

            uri = f"{self.baseuri}/tags"
            res = self.cmp_get(uri, data=data)

            self.app.render(
                res,
                key="tags",
                headers=self._meta.headers,
                fields=self._meta.fields,
                maxsize=80,
            )

    @ex(
        help=_("add service tag"),
        description=_(
            "This command adds a new service tag to an account. "
            "It requires the service tag value to be provided along with "
            "the account id to which the tag needs to be added."
        ),
        arguments=ARGS(
            [
                (
                    ["value"],
                    {"help": _("service tag value"), "action": "store", "type": str},
                ),
                (["account"], {"help": _("account id"), "action": "store", "type": str}),
            ]
        ),
    )
    def add(self):
        value = self.app.pargs.value
        account = self.get_account(self.app.pargs.account).get("uuid")

        data = {"value": value, "account": account}
        uri = f"{self.baseuri}/tags"
        res = self.cmp_post(uri, data={"tag": data})
        self.app.render({"msg": f"add service tag {res['uuid']}"})

    @ex(
        help=_("update service tag"),
        description=_(
            "This command updates an existing service tag. "
            "It requires the UUID of the service tag to update as the 'id' argument. "
            "The service tag details will be updated with any new information provided."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("service tag uuid"), "action": "store", "type": str}),
                (
                    ["-value"],
                    {
                        "help": _("service tag value"),
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
        uri = f"{self.baseuri}/tags/{oid}"
        self.cmp_put(uri, data={"tag": {"value": value}})
        self.app.render({"msg": f"update service tag {oid}"})

    @ex(
        help=_("delete service tags"),
        description=_(
            "This command deletes service tags from the Nivola CMP platform. "
            "It requires a comma separated list of IDs of the service tags to delete as an argument. "
            "This allows administrators to remove unused or unnecessary service tags from the system."
        ),
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": _("comma separated service tag id"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
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
            uri = f"{self.baseuri}/tags/{oid}"
            if force is True:
                uri += "?force=true"
            self.cmp_delete(uri, entity=f"tag {oid}")


class ServiceMetricsController(ServiceControllerChild):
    class Meta:
        label = "service_metrics"
        description = _("service metric management")
        help = _("service metric management")

    @ex(
        help=_("list service metrics"),
        description=_(
            "This command is used to list the metrics collected for services running on Nivola Cloud. "
            "Some of the metrics that could be listed are CPU and memory usage, "
            "request counts, error rates etc. These metrics help monitor "
            "the performance and health of services."
        ),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("metric id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-day"],
                    {
                        "help": _("sample day"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-value"],
                    {
                        "help": _("metric value"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-num"],
                    {
                        "help": _("metric num"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-service"],
                    {
                        "help": _("metric service instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("metric type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-jobid"],
                    {
                        "help": _("sample job id"),
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
            uri = f"{self.baseuri}/services/metrics/{oid}"
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
            uri = f"{self.baseuri}/services/metrics"
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
        help=_("list service metric types"),
        description=_(
            "This command lists the available service metric types that can be used to "
            "monitor services on Nivola Cloud. Service metrics are collected and stored to "
            "provide insights into service performance and health. "
            "The 'type-get' command retrieves the predefined metric types that services can "
            "report to provide standardized monitoring data without requiring "
            "custom metrics to be defined."
        ),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("metric type id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("metric type name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group"],
                    {
                        "help": _("metric type group name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("metric type"),
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
            uri = f"{self.baseuri}/services/metricstypes/{oid}"
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
            uri = f"{self.baseuri}/services/metricstypes"
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
        help=_("add service metric type"),
        description=_(
            "This CLI command is used to add a new service metric type to the monitoring system. "
            "The 'beehive bu service-metrics type-add' command does not require any arguments as "
            "it will launch an interactive prompt to gather the details of the new metric type "
            "being added such as the name, unit of measure, aggregation method and more. "
            "Once provided, the new metric type will be created and available for association "
            "to services and collection of metrics."
        ),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("metric type name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("metric type description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["group"],
                    {
                        "help": _("metric type group"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["type"],
                    {
                        "help": _("metric type. Supported values: CONSUME|BUNDLE|OPT_BUNDLE|PROF_SERVICE"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["unit"],
                    {
                        "help": _("metric type unit"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["status"],
                    {
                        "help": _("metric type status"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-active"],
                    {
                        "help": _("metric type active"),
                        "action": "store",
                        "type": bool,
                        "default": True,
                    },
                ),
                (
                    ["-limits"],
                    {
                        "help": 
                            _('json file with limit definition.') + " " + _('E.g.:') + " " +
                            '{"limits" : [{ "name" : "LimitCPU", "value": 2.0, "metric_type_id" : "1" }]}',
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
        uri = f"{self.baseuri}/services/metricstypes"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add service metric type {res}"})

    @ex(
        help=_("acquire metric"),
        description=_(
            "This CLI command acquires metric data from a Nivola CMP service. "
            "It does not require any arguments as it will acquire metrics for all "
            "services by default. "
            "The command connects to the Nivola CMP platform and retrieves "
            "the latest metrics captured for services that are being monitored."
        ),
        arguments=ARGS(
            [
                (
                    ["-account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("metric type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-service"],
                    {
                        "help": _("metric service instance id"),
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
        if account_id is not None:
            data["acquire_metric"]["account_id"] = account_id
        if metric_type_id is not None:
            data["acquire_metric"]["metric_type_id"] = metric_type_id
        if instance_id is not None:
            data["acquire_metric"]["service_instance_id"] = instance_id

        uri = f"{self.baseuri}/services/metrics/acquire"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"acquire metric with task {res}"})


class ServiceJobSchedulerController(ServiceControllerChild):
    class Meta:
        label = "service_schedules"
        description = _("service schedule management")
        help = _("service schedule management")

    @ex(
        help=_("list service job schedule"),
        description=_("This command lists the service job schedules."),
        example="beehive bu service-schedules get -id <uuid> -e <env> ",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("job schedule id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("job schedule name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-job_name"],
                    {
                        "help": _("job schedule job name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-job_id"],
                    {
                        "help": _("job schedule job id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("job schedule type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-metric_type"],
                    {
                        "help": _("job schedule metric type"),
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
            uri = f"{self.baseuri}/services/job_schedules/{oid}"
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
            uri = f"{self.baseuri}/services/job_schedules"
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
        help=_("list service job schedule"),
        description=_("This command lists the service job schedules."),
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
        help=_("add service job schedule"),
        description=_(
            "This CLI command is used to add a new service job schedule to the beehive service scheduler. "
            "The service scheduler allows scheduling recurring jobs that run services or "
            "tasks on a defined schedule. "
            "This add subcommand does not require any arguments as all schedule details will need "
            "to be provided interactively after running the command."
        ),
        arguments=ARGS(
            [
                (
                    ["config"],
                    {
                        "help": _("job schedule config file"),
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

        uri = f"{self.baseuri}/services/job_schedules"
        res = self.cmp_post(uri, data={"job_schedule": data})
        self.app.render({"msg": f"add job schedule {res}"})

    @ex(
        help=_("delete service job schedule"),
        description=_(
            "This command deletes a service job schedule. "
            "Service schedules are used to automate recurring jobs like backups, "
            "deployments etc. on a scheduled basis. "
            "Since this command deletes the schedule, any future scheduled jobs "
            "for that service will not run."
        ),
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("job schedule id"),
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
        uri = f"{self.baseuri}/services/job_schedules/{oid}"
        self.cmp_delete(uri)
        self.app.render({"msg": f"delete job schedule {oid}"})

    def __exec_schedule_cmd(self, cmd):
        oid = self.app.pargs.oid
        uri = f"{self.baseuri}/services/job_schedules/{oid}/{cmd}"
        res = self.cmp_put(uri)
        self.app.render({"msg": f"exec {cmd} job_schedule {res} "})

    @ex(
        help=_("start service job schedule"),
        description=_(
            "This command starts an existing service job schedule. "
            "Service schedules allow running jobs on a recurring basis like daily, "
            "weekly etc. "
            "This command requires no arguments as it simply starts "
            "the existing schedule to begin running jobs based on the schedule configuration."
        ),
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("job schedule id"),
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
        help=_("stop service job schedule"),
        description=_(
            "This command stops a service job schedule that was previously created. "
            "Service schedules allow running jobs on a recurring basis like daily, "
            "weekly etc. "
            "This command stops the execution of the scheduled job so "
            "it does not run on the scheduled intervals anymore."
        ),
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("job schedule id"),
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
        help=_("restart service job schedule"),
        description=_(
            "This command is used to restart the service job schedules on the Nivola CMP platform. "
            "Service schedules are used to automate recurring jobs like backups, "
            "deployments etc. "
            "Restarting the schedules would trigger the first run immediately and "
            "reset the schedule times."
        ),
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("job schedule id"),
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
        description = _("service consume management")
        help = _("service consume management")

    @ex(
        help=_("list service job schedule"),
        description=_("This command lists the service job schedules."),
        example="beehive bu service-schedules get -id <uuid> -e <env> ",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("consume id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("consume type id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-aggr_type"],
                    {
                        "help": _("aggregation type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-period"],
                    {
                        "help": _("aggregation period"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-task"],
                    {
                        "help": _("execution task"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-date_start"],
                    {
                        "help": _("start date"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-date_end"],
                    {
                        "help": _("stop date"),
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
        uri = f"{self.baseuri}/services/consumes"
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
        help=_("generate aggregated consume"),
        description=_(
            "This command aggregates the service consumption data over a given period. "
            "The required 'period' argument specifies the aggregation period which can "
            "be specified in year-month or year-month-day format like yyyy-mm or yyyy-mm-dd. "
            "This generates a report of the total consumption aggregated for that specified period."
        ),
        arguments=ARGS(
            [
                (
                    ["period"],
                    {
                        "help": _("aggregation period. Ex. YYYY-MM o YYYY-MM-GG"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def aggregate(self):
        period = self.app.pargs.period

        data = {
            "consume": {
                "aggregation_type": "daily",
                "period": period,
            }
        }

        uri = f"{self.baseuri}/services/consumes/generate"
        self.cmp_post(uri, data=data)
        self.app.render({"msg": f"run daily consume aggregation for period {period}"})
