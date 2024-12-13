# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import ARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


class LogaaServiceController(BusinessControllerChild):
    class Meta:
        label = "logaas"
        description = "logging service management"
        help = "logging service management"

    @ex(
        help="get logging service info",
        description="This command retrieves information about the logging service for the specified account. The required 'account' argument should provide the account ID to get the logging service info for.",
        example="beehive bu logaas info gaspeell-preprod;beehive bu logaas info gaspeell-preprod",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
            ]
        ),
    )
    def info(self):
        account = self.app.pargs.account
        account = self.get_account(account).get("uuid")
        data = {"owner-id": account}
        uri = "%s/loggingservices" % self.baseuri
        res = self.cmp_get(uri, data=data)

        res = dict_get(res, "DescribeLoggingResponse", default={})
        if len(res.get("loggingSet")) > 0:
            res = dict_get(res, "loggingSet.0")
            self.app.render(res, details=True, maxsize=400)

    @ex(
        help="get logging service quotas",
        description="This command gets the logging service quotas for a specific account. The account id is required to retrieve the quotas allocated to that account.",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
            ]
        ),
    )
    def quotas(self):
        account = self.app.pargs.account
        account = self.get_account(account).get("uuid")
        data = {"owner-id": account}
        uri = "%s/loggingservices/describeaccountattributes" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data))
        res = dict_get(res, "DescribeAccountAttributesResponse.accountAttributeSet")
        headers = ["name", "value", "used"]
        fields = [
            "attributeName",
            "attributeValueSet.0.item.attributeValue",
            "attributeValueSet.0.item.nvl-attributeUsed",
        ]
        self.app.render(res, headers=headers, fields=fields)


class LoggingServiceInstanceController(BusinessControllerChild):
    class Meta:
        stacked_on = "logaas"
        stacked_type = "nested"
        label = "instances"
        description = "logging instance service management"
        help = "logging instance service management"

        cmp = {"baseuri": "/v1.0/nws", "subsystem": "service"}

    @ex(
        help="get logging module configs",
        description="This command is used to retrieve the logging module configurations for all instances or a specific instance. The logging module configs contain information like log levels, destinations etc that are used by the logging service. No arguments are required to get configs for all instances. If an instance name is provided, it will return configs only for that particular instance.",
        example="beehive bu logaas instances configs gaspeell-preprod;beehive bu logaas instances configs gaspeell-preprod",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": "parent account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def configs(self):
        data = {"owner-id": self.get_account(self.app.pargs.account)["uuid"]}
        uri = "/v1.0/nws/loggingservices/instance/describelogconfig"
        res = self.cmp_get(uri, data=data).get("DescribeLoggingInstanceLogConfigResponse")
        self.app.render(res, headers=["name", "title", "type"], fields=["name", "title", "type"], key="logConfigSet")

    @ex(
        help="list logging instances",
        description="This command lists all the logging instances in the current account or provided accounts. Logging instances are used to aggregate and store logs from applications and services. The list provides details like instance ID, name, status and other metadata for each logging instance.",
        example="beehive bu logaas instances list -account ptw;beehive bu logaas instances list -accounts dev-webfarm",
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": "list of account id comma separated",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "logging instances name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": "list of tag comma separated",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": "list page [default=0]",
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": "list page size [default=20]",
                        "action": "store",
                        "type": int,
                        "default": 20,
                    },
                ),
                (
                    ["-detail"],
                    {
                        "help": "detail show in list",
                        "action": "store",
                        "type": str,
                        "default": "False",
                    },
                ),
            ]
        ),
    )
    def list(self):
        params = ["accounts", "name", "tags", "detail"]
        mappings = {"accounts": self.get_account_ids, "tags": lambda x: x.split(",")}
        aliases = {
            "accounts": "owner-id.N",
            "name": "InstanceName",
            "tags": "tag-key.N",
            "size": "MaxItems",
            "page": "Marker",
            "detail": "Detail",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/loggingservices/instance/describeinstances" % self.baseuri

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeLoggingInstancesResponse")

            total = res.get("nvl-instanceTotal")
            res = res.get("instanceInfo", [])
            resp = {
                "count": len(res),
                "page": page,
                "total": total,
                "sort": {"field": "date.creation", "order": "desc"},
                "instances": res,
            }

            headers = ["id", "name", "status", "creation", "instance", "type", "modules", "account", "site"]
            fields = [
                "id",
                "name",
                "state",
                "creationDate",
                "computeInstanceId",
                "plugintype",
                "modules",
                "ownerAlias",
                "site",
            ]
            transform = {
                "modules": lambda x: list(x.keys()) if x is not None and isinstance(x, dict) else "",
                "plugintype": lambda x: "db" if x is not None and x == "DatabaseInstance" else "vm",
            }
            self.app.render(
                resp,
                key="instances",
                headers=headers,
                fields=fields,
                maxsize=40,
                transform=transform,
            )

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=100,
            key_total_name="DescribeLoggingInstancesResponse.nvl-instanceTotal",
            key_list_name="DescribeLoggingInstancesResponse.instanceInfo",
            fn_render=render,
        )

    @ex(
        help="get logging instance",
        description="This command retrieves details of a specific logging instance. The required 'id' argument specifies the unique identifier of the logging instance to fetch details for.",
        example="beehive bu logaas instances get <uuid>;beehive bu logaas instances get LoggingInstance-vmPPlog5w -e <env>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "logging instance id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {"instance-id.N": [oid]}
        elif self.is_name(oid):
            data = {"InstanceName": oid}

        # data.update({"Detail": True})
        uri = "%s/loggingservices/instance/describeinstances" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeLoggingInstancesResponse", default={})

        if len(res.get("instanceInfo")) > 0:
            res = dict_get(res, "instanceInfo.0")
            self.app.render(res, details=True, maxsize=400)

    @ex(
        help="create a logging instance",
        description="This CLI command creates a logging instance by adding it. It requires the parent account id and instance id as arguments to identify the account and instance to add. This allows administrators to provision new logging instances under accounts in the Nivola CMP platform.",
        example="beehive bu logaas instances add sicradem <uuid>;beehive bu logaas instances add gaspeell-preprod <uuid>",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (["instance"], {"help": "instance", "action": "store", "type": str}),
                (
                    ["-definition"],
                    {
                        "help": "definition",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-norescreate"],
                    {
                        "help": "don't create physical resource of the space",
                        "action": "store",
                        "type": str,
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get("uuid")
        instance = self.app.pargs.instance
        definition = self.app.pargs.definition
        norescreate = self.app.pargs.norescreate

        data = {"owner-id": account, "ComputeInstanceId": instance}

        if definition is not None:
            definition = self.get_service_definition(definition)
            data["InstanceType"] = definition.uuid

        if norescreate is not None:
            data.update({"norescreate": norescreate})

        uri = "%s/loggingservices/instance/createinstance" % self.baseuri
        res = self.cmp_post(uri, data={"instance": data}, timeout=600)
        uuid = dict_get(res, "CreateLoggingInstanceResponse.instanceId")
        self.wait_for_service(uuid)
        self.app.render({"msg": "Add logging instance %s" % uuid})

    @ex(
        help="delete a logging instance",
        description="This command deletes a logging instance by specifying its instance id. The instance id identifies the logging instance that needs to be deleted from the Nivola CMP logging service.",
        example="beehive bu logaas instances delete LoggingInstance-vmPPlog5w -e <env>;beehive bu logaas instances delete <uuid>",
        arguments=ARGS(
            [
                (
                    ["instance_id"],
                    {"help": "logging instance id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete(self):
        logging_instance_id = self.app.pargs.instance_id
        uri = "%s/loggingservices/instance/deleteteinstance" % self.baseuri
        entity = "logging instance %s" % logging_instance_id
        self.cmp_delete(uri, data={"InstanceId": logging_instance_id}, entity=entity, output=False)
        self.wait_for_service(logging_instance_id, accepted_state="DELETED")

    #
    # action
    #
    @ex(
        help="enable logging module",
        description="This command enables a logging module on a specified logging instance. It requires the instance ID and module configuration as arguments. The instance ID identifies the logging instance to modify and the module configuration specifies which module to enable, like 'apache'.",
        example="beehive bu logaas instances enable-module <uuid> apache;beehive bu logaas instances enable-module <uuid> apache",
        arguments=ARGS(
            [
                (
                    ["instance_id"],
                    {"help": "logging instance id", "action": "store", "type": str},
                ),
                (
                    ["conf"],
                    {"help": "module configuration", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def enable_module(self):
        instance_id = self.app.pargs.instance_id
        conf = self.app.pargs.conf
        uri = "%s/loggingservices/instance/enablelogconfig" % self.baseuri
        res = self.cmp_put(uri, data={"InstanceId": instance_id, "Config": conf}, task_key="EnableLogConfigResponse")
        self.app.render({"msg": "enable logging module %s" % conf})

    @ex(
        help="disable logging module",
        description="This command disables a logging module on a specified logging instance. It requires the instance ID and module configuration as arguments. The instance ID identifies the logging instance and the module configuration specifies which module to disable, like 'apache'.",
        example="beehive bu logaas instances disable-module <uuid> apache;beehive bu logaas instances disable-module <uuid> apache",
        arguments=ARGS(
            [
                (
                    ["instance_id"],
                    {"help": "logging instance id", "action": "store", "type": str},
                ),
                (
                    ["conf"],
                    {"help": "module configuration", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def disable_module(self):
        instance_id = self.app.pargs.instance_id
        conf = self.app.pargs.conf
        uri = "%s/loggingservices/instance/disablelogconfig" % self.baseuri
        self.cmp_put(uri, data={"InstanceId": instance_id, "Config": conf}, task_key="DisableLogConfigResponse")
        self.app.render({"msg": "disable logging module %s" % conf})


class LoggingServiceSpaceController(BusinessControllerChild):
    class Meta:
        stacked_on = "logaas"
        stacked_type = "nested"
        label = "spaces"
        description = "logging space service management"
        help = "logging space service management"

        cmp = {"baseuri": "/v1.0/nws", "subsystem": "service"}

    @ex(
        help="list logging spaces",
        description="This command lists all the logging spaces configured in the current environment. Logging spaces are logical containers that group log sources together for centralized logging and monitoring. The list displays the name and ID of each space.",
        example="beehive bu logaas spaces list -e <env>;beehive bu logaas spaces list -e <env>",
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": "list of account id comma separated",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "list of logging instances id comma separated",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": "list of tag comma separated",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": "list page [default=0]",
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": "list page size [default=20]",
                        "action": "store",
                        "type": int,
                        "default": 20,
                    },
                ),
            ]
        ),
    )
    def list(self):
        params = ["accounts", "name", "tags"]
        mappings = {"accounts": self.get_account_ids, "tags": lambda x: x.split(",")}
        aliases = {
            "accounts": "owner-id.N",
            "name": "name",
            "tags": "tag-key.N",
            "size": "MaxItems",
            "page": "Marker",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/loggingservices/spaces/describespaces" % self.baseuri

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeSpacesResponse")

            total = res.get("spaceTotal")
            res = res.get("spaceInfo", [])
            resp = {
                "count": len(res),
                "page": page,
                "total": total,
                "sort": {"field": "date.creation", "order": "desc"},
                "spaces": res,
            }

            headers = [
                "id",
                "name",
                "status",
                "account",
                "template",
                "creation",
                "endpoint",
            ]
            fields = [
                "id",
                "name",
                "state",
                "ownerAlias",
                "templateName",
                "creationDate",
                "endpoints.home",
            ]
            transform = {}
            self.app.render(
                resp,
                key="spaces",
                headers=headers,
                fields=fields,
                maxsize=100,
                transform=transform,
            )

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="DescribeSpacesResponse.spaceTotal",
            key_list_name="DescribeSpacesResponse.spaceInfo",
            fn_render=render,
        )

    @ex(
        help="get logging space",
        description="This command retrieves information about a specific logging space by its id. The space id is required as an argument to identify the space to get details for. Details returned include the space name, description, status and other metadata.",
        example="beehive bu logaas spaces get DefaultSpace;beehive bu logaas spaces get <uuid>",
        arguments=ARGS(
            [
                (["id"], {"help": "space id", "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {"space-id.N": [oid]}  # logging-space-id
        elif self.is_name(oid):
            data = {"SpaceName": oid}
        uri = "%s/loggingservices/spaces/describespaces" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeSpacesResponse", default={})

        if len(res.get("spaceInfo")) > 0:
            if self.is_output_text():
                res = dict_get(res, "spaceInfo.0")
                dashboards = res.pop("dashboards", [])
                self.app.render(res, details=True, maxsize=400)

                self.c("\ndashboards", "underline")
                headers = ["id", "title", "name", "endpoint"]
                fields = ["dashboardId", "dashboardTitle", "dashboardName", "endpoint"]
                self.app.render(dashboards, headers=headers, fields=fields, maxsize=400)
            else:
                self.app.render(res, details=True, maxsize=400)

    @ex(
        help="create a logging space",
        description="This command creates a logging space. It requires the parent account id as an argument to associate the new space with.",
        example="beehive bu logaas spaces add prodis-preprod;beehive bu logaas spaces add gaspeell-preprod -e <env>",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["-name"],
                    {
                        "help": "space name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-definition"],
                    {
                        "help": "service definition of the space",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-norescreate"],
                    {
                        "help": "don't create physical resource of the space",
                        "action": "store",
                        "type": str,
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get("uuid")
        name = self.app.pargs.name
        definition = self.app.pargs.definition
        norescreate = self.app.pargs.norescreate

        data = {
            "owner-id": account,
        }

        if name is not None:
            data.update({"Name": name})
        if definition is not None:
            data.update({"definition": definition})
        if norescreate is not None:
            data.update({"norescreate": norescreate})

        uri = "%s/loggingservices/spaces/createspace" % self.baseuri
        res = self.cmp_post(uri, data={"space": data}, timeout=600)

        createSpaceResponse = dict_get(res, "CreateSpaceResponse")
        spaceId = dict_get(createSpaceResponse, "spaceId")
        self.wait_for_service(spaceId)
        self.app.render({"msg": "Add logging space %s" % spaceId})

    @ex(
        help="delete a logging space",
        description="Delete a logging space by specifying the logging space id. This will delete all the logs associated with the logging space.",
        example="beehive bu logaas spaces delete <uuid>;beehive bu logaas spaces delete avc",
        arguments=ARGS(
            [
                (
                    ["logging_space_id"],
                    {"help": "logging space id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete(self):
        logging_space_id = self.app.pargs.logging_space_id
        uri = "%s/loggingservices/spaces/deletespace" % self.baseuri
        data = {"SpaceId": logging_space_id}
        entity = "logging space %s" % logging_space_id
        res = self.cmp_delete(uri, data=data, timeout=600, entity=entity, output=False)
        state = self.wait_for_service(logging_space_id, delta=2)
        if state == "DELETED":
            print("%s deleted" % entity)

    @ex(
        help="synchronize users of logging space",
        description="This command synchronizes the users of a logging space by its ID. The logging space ID is required to identify which space to synchronize users for. This will update the users that have access to the logs and events within that specific logging space.",
        example="beehive bu logaas spaces sync-users <uuid>",
        arguments=ARGS(
            [
                (
                    ["logging_space_id"],
                    {"help": "logging space id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def sync_users(self):
        logging_space_id = self.app.pargs.logging_space_id
        uri = "%s/loggingservices/spaces/syncspaceusers" % (self.baseuri)
        self.cmp_put(uri, data={"SpaceId": logging_space_id}, task_key="SyncSpaceUsersResponse")
        self.app.render({"msg": "sync space %s users" % logging_space_id})

    @ex(
        help="get logging space configs",
        description="This command is used to get logging space configurations from Nivola Cloud. It retrieves the configuration of a specific space identified by its UUID, or lists the configurations of all spaces associated with a particular account.",
        example="beehive bu logaas spaces dashboards 02abf643-41b2-46a6-8878-f55522165b54",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": "parent account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def dashboards(self):
        data = {"owner-id": self.get_account(self.app.pargs.account)["uuid"]}
        uri = "%s/loggingservices/spaces/describespaceconfig" % (self.baseuri)
        res = self.cmp_get(uri, data=data).get("DescribeSpaceConfigResponse")
        self.app.render(
            res,
            headers=["name", "title", "default"],
            fields=["name", "title", "default"],
            key="logConfigSet",
        )

    # action

    @ex(
        help="enable logging dashboard",
        description="This command enables the logging dashboard for a specific space. It requires the space ID and dashboard configuration as arguments. The space ID identifies the space to enable the dashboard for. The dashboard configuration specifies the type of dashboard (e.g. Linux or Windows) to configure for that space.",
        example="beehive bu logaas spaces enable-dashboard uuid dashboard-name",
        arguments=ARGS(
            [
                (
                    ["space_id"],
                    {"help": "spaces id", "action": "store", "type": str},
                ),
                (
                    ["conf"],
                    {"help": "dashboard configuration", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def enable_dashboard(self):
        space_id = self.app.pargs.space_id
        conf = self.app.pargs.conf
        uri = "%s/loggingservices/spaces/enabledashconfig" % self.baseuri
        self.cmp_put(uri, data={"SpaceId": space_id, "Config": conf})
        self.app.render({"msg": "enable logging dashboard %s" % conf})

    @ex(
        help="disable logging dashboard",
        description="This command disables the logging dashboard for a specific space. It requires the space ID and dashboard configuration as arguments. The space ID identifies the space to disable the dashboard for. The dashboard configuration specifies the type of dashboard (e.g. Linux or Windows) to configure for that space.",
        example="beehive bu logaas spaces disable-dashboard uuid dashboard-name;",
        arguments=ARGS(
            [
                (
                    ["space_id"],
                    {"help": "spaces id", "action": "store", "type": str},
                ),
                (
                    ["conf"],
                    {"help": "dashboard configuration", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def disable_dashboard(self):
        space_id = self.app.pargs.space_id
        conf = self.app.pargs.conf
        uri = "%s/loggingservices/spaces/disabledashconfig" % self.baseuri
        self.cmp_put(uri, data={"SpaceId": space_id, "Config": conf})
        self.app.render({"msg": "disable logging dashboard %s" % conf})
