# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import ARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


class MonitoraaServiceController(BusinessControllerChild):
    class Meta:
        label = "maas"
        description = "monitoring service management"
        help = "monitoring service management"

    @ex(
        help="get monitoring service info",
        description="get monitoring service info",
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
        uri = "%s/monitoringservices" % self.baseuri
        res = self.cmp_get(uri, data=data)

        res = dict_get(res, "DescribeMonitoringResponse", default={})
        if len(res.get("monitoringSet")) > 0:
            res = dict_get(res, "monitoringSet.0")
            self.app.render(res, details=True, maxsize=400)

    @ex(
        help="get monitoring service quotas",
        description="get monitoring service quotas",
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
        uri = "%s/monitoringservices/describeaccountattributes" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data))
        res = dict_get(res, "DescribeAccountAttributesResponse.accountAttributeSet")
        headers = ["name", "value", "used"]
        fields = [
            "attributeName",
            "attributeValueSet.0.item.attributeValue",
            "attributeValueSet.0.item.nvl-attributeUsed",
        ]
        self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="get monitoring service availibility zones",
        description="get monitoring service availibility zones",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
            ]
        ),
    )
    def availability_zones(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get("uuid")
        data = {"owner-id": account_id}

        uri = "%s/monitoringservices/describeavailabilityzones" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, "DescribeAvailabilityZonesResponse.availabilityZoneInfo")

        headers = ["name", "state", "region", "message"]
        fields = ["zoneName", "zoneState", "regionName", "messageSet.0.message"]
        self.app.render(res, headers=headers, fields=fields)


class MonitoringServiceInstanceController(BusinessControllerChild):
    class Meta:
        stacked_on = "maas"
        stacked_type = "nested"
        label = "monitor-instances"
        description = "monitoring instance service management"
        help = "monitoring instance service management"

        cmp = {"baseuri": "/v1.0/nws", "subsystem": "service"}

    @ex(
        help="list monitoring instances",
        description="list monitoring instances",
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
                        "help": "list of monitoring instances id comma separated",
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
        page = self.app.pargs.page
        uri = "%s/monitoringservices/instance/describeinstances" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeMonitoringInstancesResponse")

        total = res.get("nvl-instanceTotal")
        res = res.get("instanceInfo", [])
        resp = {
            "count": len(res),
            "page": page,
            "total": total,
            "sort": {"field": "date.creation", "order": "desc"},
            "instances": res,
        }

        headers = ["id", "name", "status", "creation", "instance", "account"]
        fields = [
            "id",
            "name",
            "state",
            "creationDate",
            "computeInstanceId",
            "ownerAlias",
        ]
        transform = {"modules": lambda x: list(x.keys()) if x is not None and isinstance(x, dict) else ""}
        self.app.render(
            resp,
            key="instances",
            headers=headers,
            fields=fields,
            maxsize=40,
            transform=transform,
        )

    @ex(
        help="get monitoring instance",
        description="get monitoring instance",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "monitoring instance id", "action": "store", "type": str},
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
        uri = "%s/monitoringservices/instance/describeinstances" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeMonitoringInstancesResponse", default={})

        if len(res.get("instanceInfo")) > 0:
            res = dict_get(res, "instanceInfo.0")
            self.app.render(res, details=True, maxsize=400)

    @ex(
        help="create a monitoring instance",
        description="create a monitoring instance",
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
                        "help": "don't create physical resource of the folder",
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

        uri = "%s/monitoringservices/instance/createinstance" % self.baseuri
        res = self.cmp_post(uri, data={"instance": data}, timeout=600)
        uuid = dict_get(res, "CreateMonitoringInstanceResponse.instanceId")
        self.wait_for_service(uuid)
        self.app.render({"msg": "Add monitoring instance %s" % uuid})

    @ex(
        help="delete a monitoring instance",
        description="delete a monitoring instance",
        arguments=ARGS(
            [
                (
                    ["instance_id"],
                    {"help": "monitoring instance id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete(self):
        monitoring_instance_id = self.app.pargs.instance_id
        uri = "%s/monitoringservices/instance/deleteteinstance" % self.baseuri
        entity = "monitoring instance %s" % monitoring_instance_id
        self.cmp_delete(uri, data={"InstanceId": monitoring_instance_id}, entity=entity, output=False)
        state = self.wait_for_service(monitoring_instance_id, accepted_state="DELETED")
        if state == "DELETED":
            print("%s deleted" % entity)

    #
    # action
    #
    # @ex(
    #     help='enable monitoring module',
    #     description='enable monitoring module',
    #     arguments=ARGS([
    #         (['instance_id'], {'help': 'monitoring instance id', 'action': 'store', 'type': str}),
    #         (['conf'], {'help': 'module configuration', 'action': 'store', 'type': str}),
    #     ])
    # )
    # def enable_module(self):
    #     instance_id = self.app.pargs.instance_id
    #     conf = self.app.pargs.conf
    #     uri = '%s/monitoringservices/instance/enablemonitorconfig' % self.baseuri
    #     self.cmp_put(uri, data={'InstanceId': instance_id, 'Config': conf})
    #     self.app.render({'msg': 'enable monitoring module %s' % conf})

    # @ex(
    #     help='disable monitoring module',
    #     description='disable monitoring module',
    #     arguments=ARGS([
    #         (['instance_id'], {'help': 'monitoring instance id', 'action': 'store', 'type': str}),
    #         (['conf'], {'help': 'module configuration', 'action': 'store', 'type': str}),
    #     ])
    # )
    # def disable_module(self):
    #     instance_id = self.app.pargs.instance_id
    #     conf = self.app.pargs.conf
    #     uri = '%s/monitoringservices/instance/disablemonitorconfig' % self.baseuri
    #     self.cmp_put(uri, data={'InstanceId': instance_id, 'Config': conf})
    #     self.app.render({'msg': 'disable monitoring module %s' % conf})


class MonitoringServiceFolderController(BusinessControllerChild):
    class Meta:
        stacked_on = "maas"
        stacked_type = "nested"
        label = "folders"
        description = "monitoring folder service management"
        help = "monitoring folder service management"

        cmp = {"baseuri": "/v1.0/nws", "subsystem": "service"}

    @ex(
        help="list monitoring folders",
        description="list monitoring folders",
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
                        "help": "list of monitoring instances id comma separated",
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
        page = self.app.pargs.page
        uri = "%s/monitoringservices/folders/describefolders" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeFoldersResponse")

        total = res.get("folderTotal")
        res = res.get("folderInfo", [])
        resp = {
            "count": len(res),
            "page": page,
            "total": total,
            "sort": {"field": "date.creation", "order": "desc"},
            "folders": res,
        }

        headers = ["id", "name", "status", "account", "template", "creation"]
        fields = ["id", "name", "state", "ownerAlias", "templateName", "creationDate"]
        transform = {}
        self.app.render(
            resp,
            key="folders",
            headers=headers,
            fields=fields,
            maxsize=100,
            transform=transform,
        )

    @ex(
        help="get monitoring folder",
        description="get monitoring folder",
        arguments=ARGS(
            [
                (["id"], {"help": "folder id", "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {"folder-id.N": [oid]}  # monitoring-folder-id
        elif self.is_name(oid):
            data = {"FolderName": oid}
        uri = "%s/monitoringservices/folders/describefolders" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeFoldersResponse", default={})

        if len(res.get("folderInfo")) > 0:
            if self.is_output_text():
                res = dict_get(res, "folderInfo.0")
                dashboards = res.pop("dashboards", [])
                permissions = res.pop("permissions", [])
                self.app.render(res, details=True, maxsize=400)

                self.c("\ndashboards", "underline")
                headers = ["id", "name", "endpoint"]
                fields = ["dashboardId", "dashboardName", "endpoint"]
                self.app.render(dashboards, headers=headers, fields=fields, maxsize=400)

                self.c("\npermissions", "underline")
                headers = ["name", "teamName", "modificationDate"]
                fields = ["permissionName", "teamName", "modificationDate"]
                self.app.render(permissions, headers=headers, fields=fields, maxsize=400)
            else:
                self.app.render(res, details=True, maxsize=400)

    @ex(
        help="create a monitoring folder",
        description="create a monitoring folder",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["-name"],
                    {
                        "help": "folder name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-definition"],
                    {
                        "help": "service definition of the folder",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-norescreate"],
                    {
                        "help": "don't create physical resource of the folder",
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

        # print('data: %s' % data)

        uri = "%s/monitoringservices/folders/createfolder" % self.baseuri
        res = self.cmp_post(uri, data={"folder": data}, timeout=600)

        createFolderResponse = dict_get(res, "CreateFolderResponse")
        folderId = dict_get(createFolderResponse, "folderId")
        self.wait_for_service(folderId)
        self.app.render({"msg": "Add monitoring folder %s" % folderId})

    @ex(
        help="delete a monitoring folder",
        description="delete a monitoring folder",
        arguments=ARGS(
            [
                (
                    ["monitoring_folder_id"],
                    {"help": "monitoring folder id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete(self):
        monitoring_folder_id = self.app.pargs.monitoring_folder_id
        uri = "%s/monitoringservices/folders/deletefolder" % self.baseuri
        self.cmp_delete(
            uri,
            data={"FolderId": monitoring_folder_id},
            entity="monitoring folder %s" % monitoring_folder_id,
        )
        self.wait_for_service(monitoring_folder_id, accepted_state="DELETED")

    @ex(
        help="synchronize users of monitoring folder",
        description="synchronize users of monitoring folder",
        arguments=ARGS(
            [
                (
                    ["monitoring_folder_id"],
                    {"help": "monitoring folder id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def sync_users(self):
        monitoring_folder_id = self.app.pargs.monitoring_folder_id
        uri = "%s/monitoringservices/folders/syncfolderusers" % (self.baseuri)
        self.cmp_put(uri, data={"FolderId": monitoring_folder_id})
        self.app.render({"msg": "sync folder %s users" % monitoring_folder_id})

    @ex(
        help="get monitoring folder configs",
        description="get monitoring folder configs",
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
        uri = "%s/monitoringservices/folders/describefolderconfig" % (self.baseuri)
        res = self.cmp_get(uri, data=data).get("DescribeFolderConfigResponse")
        self.app.render(
            res,
            headers=["name", "default"],
            fields=["name", "default"],
            key="monitorConfigSet",
        )

    # action

    @ex(
        help="enable monitoring dashboard",
        description="enable monitoring dashboard",
        arguments=ARGS(
            [
                (
                    ["folders_id"],
                    {"help": "folders id", "action": "store", "type": str},
                ),
                (
                    ["conf"],
                    {"help": "dashboard configuration", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def enable_dashboard(self):
        folders_id = self.app.pargs.folders_id
        conf = self.app.pargs.conf
        uri = "%s/monitoringservices/folders/enabledashconfig" % self.baseuri
        self.cmp_put(uri, data={"FolderId": folders_id, "Config": conf})
        self.app.render({"msg": "enable monitoring dashboard %s" % conf})


class MonitoringServiceAlertController(BusinessControllerChild):
    class Meta:
        stacked_on = "maas"
        stacked_type = "nested"
        label = "alerts"
        description = "monitoring alert service management"
        help = "monitoring alert service management"

        cmp = {"baseuri": "/v1.0/nws", "subsystem": "service"}

    @ex(
        help="list monitoring alerts",
        description="list monitoring alerts",
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
                        "help": "list of monitoring instances id comma separated",
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
        page = self.app.pargs.page
        uri = "%s/monitoringservices/alerts/describealerts" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeAlertsResponse")

        total = res.get("alertTotal")
        res = res.get("alertInfo", [])
        resp = {
            "count": len(res),
            "page": page,
            "total": total,
            "sort": {"field": "date.creation", "order": "desc"},
            "alerts": res,
        }

        headers = ["id", "name", "status", "account", "template", "creation"]
        fields = ["id", "name", "state", "ownerAlias", "templateName", "creationDate"]
        transform = {}
        self.app.render(
            resp,
            key="alerts",
            headers=headers,
            fields=fields,
            maxsize=100,
            transform=transform,
        )

    @ex(
        help="get monitoring alert",
        description="get monitoring alert",
        arguments=ARGS(
            [
                (["id"], {"help": "alert id", "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {"alert-id.N": [oid]}  # monitoring-alert-id
        elif self.is_name(oid):
            data = {"AlertName": oid}
        uri = "%s/monitoringservices/alerts/describealerts" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeAlertsResponse", default={})

        if len(res.get("alertInfo")) > 0:
            if self.is_output_text():
                res = dict_get(res, "alertInfo.0")
                # users_email = res.pop("users_email")
                # user_severities = res.pop("user_severities")
                self.app.render(res, details=True, maxsize=400)
            else:
                self.app.render(res, details=True, maxsize=400)

    @ex(
        help="create a monitoring alert",
        description="create a monitoring alert",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["zone"],
                    {"help": "availability zone", "action": "store", "type": str},
                ),
                (
                    ["-name"],
                    {
                        "help": "alert name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-definition"],
                    {
                        "help": "service definition of the alert",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-norescreate"],
                    {
                        "help": "don't create physical resource of the alert",
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
        zone = self.app.pargs.zone
        definition = self.app.pargs.definition
        norescreate = self.app.pargs.norescreate

        data = {
            "owner-id": account,
            "AvailabilityZone": zone,
        }

        if name is not None:
            data.update({"Name": name})
        if definition is not None:
            data.update({"definition": definition})
        if norescreate is not None:
            data.update({"norescreate": norescreate})

        # print('data: %s' % data)

        uri = "%s/monitoringservices/alerts/createalert" % self.baseuri
        res = self.cmp_post(uri, data={"alert": data}, timeout=600)

        createAlertResponse = dict_get(res, "CreateAlertResponse")
        alertId = dict_get(createAlertResponse, "alertId")
        self.wait_for_service(alertId)
        self.app.render({"msg": "Add monitoring alert %s" % alertId})

    @ex(
        help="delete a monitoring alert",
        description="delete a monitoring alert",
        arguments=ARGS(
            [
                (
                    ["monitoring_alert_id"],
                    {"help": "monitoring alert id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete(self):
        monitoring_alert_id = self.app.pargs.monitoring_alert_id
        uri = "%s/monitoringservices/alerts/deletealert" % self.baseuri

        entity = "monitoring alert %s" % monitoring_alert_id
        self.cmp_delete(uri, data={"AlertId": monitoring_alert_id}, entity=entity, output=False)
        state = self.wait_for_service(monitoring_alert_id, accepted_state="DELETED")
        if state == "DELETED":
            print("%s deleted" % entity)

    @ex(
        help="update user of monitoring alert",
        description="update user of monitoring alert",
        arguments=ARGS(
            [
                (["id"], {"help": "alert id", "action": "store", "type": str}),
                (
                    ["users_email"],
                    {"help": "users email that will receive alerts - comma separated", "action": "store", "type": str},
                ),
                (["severity"], {"help": "list of alert severity - comma separated", "action": "store", "type": str}),
            ]
        ),
    )
    def user_update(self):
        oid = self.app.pargs.id
        users_email = self.app.pargs.users_email
        severity = self.app.pargs.severity
        data = {
            "AlertId": oid,
            "UsersEmail": users_email,
            "Severity": severity,
        }

        uri = "%s/monitoringservices/alerts/updatealertusers" % self.baseuri
        res = self.cmp_put(uri, data=data)
        # res = dict_get(res, "UpdateAlertUsersResponse", default={})
        self.app.render({"msg": "update alert %s users" % oid})

    @ex(
        help="get monitoring alert user severities",
        description="get monitoring alert user severities",
        arguments=ARGS([]),
    )
    def user_severities(self):
        uri = "%s/monitoringservices/alerts/describealertuserseverity" % self.baseuri
        res = self.cmp_get(uri)
        res = dict_get(res, "DescribeAlertUserSeverityResponse", default=None)
        user_severities = dict_get(res, "user_severities", default=[])
        print(user_severities)
