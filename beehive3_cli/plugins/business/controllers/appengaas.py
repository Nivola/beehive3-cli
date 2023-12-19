# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import ARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


class AppEngineServiceController(BusinessControllerChild):
    class Meta:
        label = "appeng"
        description = "appengine service management"
        help = "appengine service management"

    @ex(
        help="get appengine service info",
        description="get appengine service info",
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
        uri = "%s/appengineservices" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data))
        res = dict_get(res, "DescribeAppengineResponse.appengineSet.0")
        self.app.render(res, details=True, maxsize=100)

    @ex(
        help="get appengine service quotas",
        description="get appengine service quotas",
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
        uri = "%s/appengineservices/describeaccountattributes" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data))
        res = dict_get(res, "DescribeAccountAttributesResponse.accountAttributeSet")
        headers = ["name", "value", "used"]
        fields = [
            "attributeName",
            "attributeValueSet.0.item.attributeValue",
            "attributeValueSet.0.item.nvl-attributeUsed",
        ]
        self.app.render(res, headers=headers, fields=fields)


class AppEngineInstanceController(BusinessControllerChild):
    class Meta:
        stacked_on = "appeng"
        stacked_type = "nested"
        label = "app_instances"
        description = "appengine instances service management"
        help = "appengine instances service management"

    @ex(help="get appengine types", description="get appengine types", arguments=ARGS())
    def types(self):
        data = {"plugintype": "AppEngineInstance", "page": 0, "size": 100}
        uri = "%s/srvcatalogs/all/defs" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data))
        headers = ["id", "instance_type", "desc", "status", "active", "creation"]
        fields = ["uuid", "name", "desc", "status", "active", "date.creation"]
        self.app.render(res, key="servicedefs", headers=headers, fields=fields)

    @ex(
        help="list app engine",
        description="list app engine",
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
                    ["-ida"],
                    {
                        "help": "list of appengin id comma separated",
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
            "ids": "instance-id.N",
            "tags": "tag-key.N",
            "size": "MaxResults",
            "page": "NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/appengineservices/instance/describeappinstances" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeAppInstancesResponse")
        page = self.app.pargs.page
        resp = {
            "count": len(res.get("instancesSet")),
            "page": page,
            "total": res.get("instancesTotal"),
            "sort": {"field": "id", "order": "asc"},
            "instances": res.get("instancesSet"),
        }
        headers = [
            "id",
            "name",
            "status",
            "account",
            "Engine",
            "EngineVersion",
            "AvailabilityZone",
            "Subnet",
            "Uris",
            "Date",
        ]
        fields = [
            "instanceId",
            "name",
            "instanceState.name",
            "OwnerAlias",
            "engine",
            "version",
            "placement.availabilityZone",
            "subnetName",
            "uris",
            "launchTime",
        ]
        transform = {"instanceState.name": self.color_error}
        self.app.render(
            resp,
            key="instances",
            headers=headers,
            fields=fields,
            maxsize=40,
            transform=transform,
        )

    @ex(
        help="get appengine",
        description="get appengine",
        arguments=ARGS(
            [
                (
                    ["appengine"],
                    {"help": "appengine id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def get(self):
        appengine = self.app.pargs.appengine
        data = {}
        data["InstanceId.N"] = [appengine]

        uri = "%s/appengineservices/instance/describeappinstances" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))

        if self.format == "text":
            res = res.get("DescribeAppInstancesResponse")
            if len(res.get("instancesSet")) > 0:
                resp = res.get("instancesSet")[0]
                self.app.render(resp, details=True)
        else:
            self.app.render(res, details=True)

    @ex(
        help="create a share",
        description="create a share",
        arguments=ARGS(
            [
                (["name"], {"help": "appengine name", "action": "store", "type": str}),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["farm-name"],
                    {"help": "name of the farm", "action": "store", "type": int},
                ),
                (["type"], {"help": "appengine type", "action": "store", "type": str}),
                (
                    ["subnet"],
                    {"help": "appengine subnet id", "action": "store", "type": str},
                ),
                (["sg"], {"help": "security group id", "action": "store", "type": str}),
                (
                    ["-key-name"],
                    {
                        "help": "ssh key name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sharesize"],
                    {
                        "help": "share size in GB",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-public"],
                    {
                        "help": "if True appengine has public ip address",
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
                (
                    ["-public-subnet"],
                    {
                        "help": "public subnet",
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
        farm_name = self.app.pargs.farm_name
        account = self.get_account(self.app.pargs.account).get("uuid")
        template = self.get_service_def(self.app.pargs.type)
        subnet = self.get_service_instance(self.app.pargs.subnet, account_id=account)
        is_public = self.app.pargs.public
        public_subnet = self.app.pargs.public_subnet
        sg = self.get_service_instance(self.app.pargs.security_group, account_id=account)
        key_name = self.app.pargs.key_name
        share_dimension = self.app.pargs.sharesize

        if is_public is True:
            if public_subnet is not None:
                public_subnet = self.get_service_instance(public_subnet, account_id=account)
            else:
                raise Exception("if public is True yuo must specify public-subnet")

        data = {
            "instance": {
                "owner_id": account,
                "Name": name,
                "AdditionalInfo": name,
                "IsPublic": is_public,
                "InstanceType": template,
                "SubnetId": subnet,
                "SecurityGroupId.N": [sg],
                "EngineConfigs": {"FarmName": farm_name},
            }
        }
        if key_name is not None:
            data["instance"]["KeyName"] = key_name
        if share_dimension is not None:
            data["instance"]["EngineConfigs"]["ShareDimension"] = share_dimension
        if is_public is True:
            data["instance"]["PublicSubnetId"] = self.get_service_instance(public_subnet, account_id=account)

        uri = "%s/appengineservices/instance/createappinstances" % self.baseuri
        res = self.cmp_post(uri, data=data, timeout=600)
        res = dict_get(res, "CreateAppInstanceResponse.instancesSet.0.instanceId")
        self.app.render({"msg": "add appengine %s" % res})

    @ex(
        help="delete an appengine",
        description="delete an appengine",
        arguments=ARGS([(["appengine"], {"help": "appengine id", "action": "store", "type": str})]),
    )
    def delete(self):
        uuid = self.app.pargs.appengine
        uri = "%s/appengineservices/instance/deleteappinstances" % self.baseuri
        res = self.cmp_delete(
            uri,
            data={"InstanceId.N": [uuid]},
            timeout=600,
            entity="appengine %s uuid",
        )
