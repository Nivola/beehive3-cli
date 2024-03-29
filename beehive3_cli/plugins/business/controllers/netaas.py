# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beecell.types.type_dict import dict_get
from beecell.types.type_string import str2bool
from beecell.types.type_id import is_name, is_uuid
from beehive3_cli.core.controller import ARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild
from beehive3_cli.plugins.administration.controllers.child import AdminChildController


class NetaaServiceController(BusinessControllerChild):
    class Meta:
        label = "netaas"
        description = "network service management"
        help = "network service management"

    @ex(
        help="get network service info",
        description="get network service info",
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
        uri = "%s/networkservices" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, "DescribeNetworkResponse.networkSet.0")
        self.app.render(res, details=True, maxsize=100)

    @ex(
        help="get network service quotas",
        description="get network service quotas",
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
        uri = "%s/networkservices/describeaccountattributes" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, "DescribeAccountAttributesResponse.accountAttributeSet")
        headers = ["name", "value", "used"]
        fields = [
            "attributeName",
            "attributeValueSet.0.item.attributeValue",
            "attributeValueSet.0.item.nvl-attributeUsed",
        ]
        self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="get network service availibility zones",
        description="get network service availibility zones",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
            ]
        ),
    )
    def availability_zones(self):
        account = self.app.pargs.account
        account = self.get_account(account).get("uuid")
        data = {"owner-id": account}
        uri = "%s/computeservices/describeavailabilityzones" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, "DescribeAvailabilityZonesResponse.availabilityZoneInfo")
        headers = ["name", "state", "region", "message"]
        fields = ["zoneName", "zoneState", "regionName", "messageSet.0.message"]
        self.app.render(res, headers=headers, fields=fields)


class VpcNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = "netaas"
        stacked_type = "nested"
        label = "vpcs"
        description = "virtual private cloud network service management"
        help = "virtual private cloud network service management"

    @ex(
        help="get private cloud networks",
        description="get private cloud networks",
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
                    ["-ids"],
                    {
                        "help": "list of private cloud network id comma separated",
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
        params = ["accounts", "ids", "tags"]
        mappings = {
            "accounts": self.get_account_ids,
            "tags": lambda x: x.split(","),
            "ids": lambda x: x.split(","),
        }
        aliases = {
            "accounts": "owner-id.N",
            "ids": "vpc-id.N",
            "tags": "tag-value.N",
            "size": "Nvl-MaxResults",
            "page": "Nvl-NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/computeservices/vpc/describevpcs" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeVpcsResponse")
        page = self.app.pargs.page
        for item in res.get("vpcSet"):
            item["cidr"] = ["%s" % (i["cidrBlock"]) for i in item["cidrBlockAssociationSet"]]
            item["cidr"] = ", ".join(item["cidr"])
        resp = {
            "count": len(res.get("vpcSet")),
            "page": page,
            "total": res.get("nvl-vpcTotal"),
            "sort": {"field": "id", "order": "asc"},
            "instances": res.get("vpcSet"),
        }

        headers = ["id", "name", "state", "account", "cidr", "subnet_cidrs", "tenancy"]
        fields = [
            "vpcId",
            "nvl-name",
            "state",
            "nvl-vpcOwnerAlias",
            "cidrBlock",
            "cidr",
            "instanceTenancy",
        ]
        self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=60)

    @ex(
        help="add virtual private cloud",
        description="add virtual private cloud",
        arguments=ARGS(
            [
                (["name"], {"help": "vpc name", "action": "store", "type": str}),
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["cidr_block"],
                    {"help": "vpc cidr block", "action": "store", "type": str},
                ),
                (
                    ["-template"],
                    {
                        "help": "vpc template",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tenancy"],
                    {
                        "help": "allowed tenancy of instances launched into the VPC. Use default for shared vpc. "
                        "Use dedicated for private vpc. default is dedicated",
                        "action": "store",
                        "type": str,
                        "default": "dedicated",
                    },
                ),
            ]
        ),
    )
    def add(self):
        data = {
            "VpcName": self.app.pargs.name,
            "owner_id": self.get_account(self.app.pargs.account).get("uuid"),
            "VpcType": self.app.pargs.template,
            "CidrBlock": self.app.pargs.cidr_block,
            "InstanceTenancy": self.app.pargs.tenancy,
        }
        uri = "%s/computeservices/vpc/createvpc" % self.baseuri
        res = self.cmp_post(uri, data={"vpc": data}, timeout=600)
        res = res.get("CreateVpcResponse").get("vpc").get("vpcId")
        self.wait_for_service(res)
        self.app.render({"msg": "add vpc %s" % res})

    @ex(
        help="delete a vpc",
        description="delete a vpc",
        arguments=ARGS(
            [
                (["vpc"], {"help": "vpc id", "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.vpc

        # check type
        version = "v2.0"
        uri = "/%s/nws/serviceinsts/%s" % (version, oid)
        res = self.cmp_get(uri).get("serviceinst")
        plugintype = res["plugintype"]
        name = res["name"]
        if plugintype != "ComputeVPC":
            print("Instance is not a ComputeVPC")
        else:
            data = {"force": False, "propagate": True}
            uri = "/v2.0/nws/serviceinsts/%s" % oid
            self.cmp_delete(uri, data=data, timeout=180, entity="vpc %s" % oid)
            self.wait_for_service(oid, accepted_state="DELETED")

    @ex(
        help="get vpc templates",
        description="get vpc templates",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": "template id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def templates(self):
        self.get_service_definitions("ComputeVPC")


class SubnetNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = "netaas"
        stacked_type = "nested"
        label = "subnets"
        description = "vpc subnet service management"
        help = "vpc subnet service management"

    @ex(
        help="get vpc subnets",
        description="get vpc subnets",
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
                    ["-ids"],
                    {
                        "help": "list of subnet id comma separated",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vpcs"],
                    {
                        "help": "list of vpc id comma separated",
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
        params = ["accounts", "ids", "tags", "vpcs"]
        mappings = {
            "accounts": self.get_account_ids,
            "tags": lambda x: x.split(","),
            "ids": lambda x: x.split(","),
            "vpcs": lambda x: x.split(","),
        }
        aliases = {
            "accounts": "owner-id.N",
            "ids": "subnet-id.N",
            "vpcs": "vpc-id.N",
            "size": "Nvl-MaxResults",
            "page": "Nvl-NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/computeservices/subnet/describesubnets" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeSubnetsResponse")
        page = self.app.pargs.page
        resp = {
            "count": len(res.get("subnetSet")),
            "page": page,
            "total": res.get("nvl-subnetTotal"),
            "sort": {"field": "id", "order": "asc"},
            "instances": res.get("subnetSet"),
        }

        headers = ["id", "name", "state", "account", "availabilityZone", "vpc", "cidr"]
        fields = [
            "subnetId",
            "nvl-name",
            "state",
            "nvl-subnetOwnerAlias",
            "availabilityZone",
            "nvl-vpcName",
            "cidrBlock",
        ]
        self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=40)

    @ex(
        help="add virtual private cloud subnet",
        description="add virtual private cloud subnet",
        arguments=ARGS(
            [
                (["name"], {"help": "subnet name", "action": "store", "type": str}),
                (["vpc"], {"help": "vpc id", "action": "store", "type": str}),
                (
                    ["cidr_block"],
                    {"help": "subnet cidr block", "action": "store", "type": str},
                ),
                (
                    ["zone"],
                    {"help": "availability zone", "action": "store", "type": str},
                ),
                (
                    ["-template"],
                    {
                        "help": "subnet template",
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
            "SubnetName": self.app.pargs.name,
            "VpcId": self.app.pargs.vpc,
            "Nvl_SubnetType": self.app.pargs.template,
            "CidrBlock": self.app.pargs.cidr_block,
            "AvailabilityZone": self.app.pargs.zone,
        }
        uri = "%s/computeservices/subnet/createsubnet" % self.baseuri
        res = self.cmp_post(uri, data={"subnet": data}, timeout=600)
        res = res.get("CreateSubnetResponse").get("subnet").get("subnetId")
        self.wait_for_service(res)
        self.app.render({"msg": "add subnet %s" % res})

    @ex(
        help="delete a subnet",
        description="delete a subnet",
        arguments=ARGS(
            [
                (["subnet"], {"help": "subnet id", "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.subnet

        # check type
        version = "v2.0"
        uri = "/%s/nws/serviceinsts/%s" % (version, oid)
        res = self.cmp_get(uri).get("serviceinst")
        plugintype = res["plugintype"]
        name = res["name"]
        if plugintype != "ComputeSubnet":
            print("Instance is not a ComputeSubnet")
        else:
            data = {"force": False, "propagate": True}
            uri = "/v2.0/nws/serviceinsts/%s" % oid
            self.cmp_delete(uri, data=data, timeout=180, entity="vpc subnet %s" % oid)
            self.wait_for_service(oid, accepted_state="DELETED")

    @ex(
        help="get vpc templates",
        description="get vpc templates",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": "template id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def templates(self):
        self.get_service_definitions("ComputeSubnet")


class SecurityGroupNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = "netaas"
        stacked_type = "nested"
        label = "securitygroups"
        description = "security groups service management"
        help = "security groups service management"

    @ex(
        help="get security group templates",
        description="get security group templates",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": "template id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def templates(self):
        self.get_service_definitions("ComputeSecurityGroup")

    @ex(
        help="create a security group",
        description="create a security group",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "security group name", "action": "store", "type": str},
                ),
                (["vpc"], {"help": "parent vpc", "action": "store", "type": str}),
                (
                    ["-template"],
                    {"help": "template id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def add(self):
        data = {"GroupName": self.app.pargs.name, "VpcId": self.app.pargs.vpc}
        sg_type = self.app.pargs.template
        if sg_type is not None:
            data["GroupType"] = sg_type
        uri = "%s/computeservices/securitygroup/createsecuritygroup" % self.baseuri
        res = self.cmp_post(uri, data={"security_group": data}, timeout=600)
        res = dict_get(res, "CreateSecurityGroupResponse.groupId")
        self.wait_for_service(res)
        self.app.render({"msg": "Add securitygroup %s" % res})

    @ex(
        help="get security groups",
        description="get security groups",
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
                    ["-ids"],
                    {
                        "help": "list of security group id comma separated",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vpcs"],
                    {
                        "help": "list of vpc id comma separated",
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
        params = ["accounts", "ids", "tags", "vpcs"]
        mappings = {
            "accounts": self.get_account_ids,
            "tags": lambda x: x.split(","),
            "vpcs": lambda x: x.split(","),
            "ids": lambda x: x.split(","),
        }
        aliases = {
            "accounts": "owner-id.N",
            "ids": "group-id.N",
            "tags": "tag-key.N",
            "vpcs": "vpc-id.N",
            "size": "MaxResults",
            "page": "NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/computeservices/securitygroup/describesecuritygroups" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeSecurityGroupsResponse", {})
        page = self.app.pargs.page

        for item in res.get("securityGroupInfo"):
            item["egress_rules"] = len(item["ipPermissionsEgress"])
            item["ingress_rules"] = len(item["ipPermissions"])

        resp = {
            "count": len(res.get("securityGroupInfo")),
            "page": page,
            "total": res.get("nvl-securityGroupTotal"),
            "sort": {"field": "id", "order": "asc"},
            "instances": res.get("securityGroupInfo"),
        }

        headers = [
            "id",
            "name",
            "state",
            "account",
            "vpc",
            "egress_rules",
            "ingress_rules",
        ]
        fields = [
            "groupId",
            "groupName",
            "nvl-state",
            "nvl-sgOwnerAlias",
            "nvl-vpcName",
            "egress_rules",
            "ingress_rules",
        ]
        self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=40)

    def __format_rule(self, rules):
        for rule in rules:
            if rule["ipProtocol"] == "-1":
                rule["ipProtocol"] = "*"
            if rule.get("fromPort", None) is None or rule["fromPort"] == "-1":
                rule["fromPort"] = "*"
            if rule.get("toPort", None) is None or rule["toPort"] == "-1":
                rule["toPort"] = "*"
            if len(rule.get("groups", None)) > 0:
                group = rule["groups"][0]
                rule["groups"] = "%s:%s [%s]" % (
                    group.get("nvl-userName", None),
                    group["groupName"],
                    group["groupId"],
                )
            else:
                rule["groups"] = ""
            if len(rule.get("ipRanges", None)) > 0:
                cidr = rule["ipRanges"][0]
                rule["ipRanges"] = "%s" % cidr["cidrIp"]
            else:
                rule["ipRanges"] = ""
        return rules

    @ex(
        help="get security group with rules",
        description="get security group with rules",
        arguments=ARGS(
            [
                (
                    ["securitygroup"],
                    {"help": "securitygroup id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def get(self):
        securitygroup = self.app.pargs.securitygroup
        data = {"GroupName.N": [securitygroup]}
        uri = "%s/computeservices/securitygroup/describesecuritygroups" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeSecurityGroupsResponse.securityGroupInfo", default={})
        if len(res) == 0:
            raise Exception("security group %s does not exist" % securitygroup)
        res = res[0]
        if self.is_output_text():
            egress_rules = self.__format_rule(res.pop("ipPermissionsEgress"))
            ingress_rules = self.__format_rule(res.pop("ipPermissions"))
            fields = [
                "groups",
                "ipRanges",
                "ipProtocol",
                "fromPort",
                "toPort",
                "nvl-reserved",
                "nvl-state",
            ]
            self.app.render(res, details=True, maxsize=200)
            self.c("\negress rules", "underline")
            headers = [
                "toSecuritygroup",
                "toCidr",
                "protocol",
                "fromPort",
                "toPort",
                "reserved",
                "state",
            ]
            self.app.render(egress_rules, headers=headers, fields=fields, maxsize=80)
            self.c("\ningress rules", "underline")
            headers = [
                "fromSecuritygroup",
                "fromCidr",
                "protocol",
                "fromPort",
                "toPort",
                "reserved",
                "state",
            ]
            self.app.render(ingress_rules, headers=headers, fields=fields, maxsize=80)
        else:
            self.app.render(res, details=True, maxsize=200)

    @ex(
        help="patch a security group",
        description="patch a security group",
        arguments=ARGS(
            [
                (
                    ["securitygroup"],
                    {"help": "securitygroup id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def patch(self):
        securitygroup = self.app.pargs.securitygroup
        data = {"GroupName": securitygroup}
        uri = "%s/computeservices/securitygroup/patchsecuritygroup" % self.baseuri
        res = self.cmp_patch(uri, data={"security_group": data}, timeout=600)
        res = dict_get("PatchSecurityGroupResponse.instancesSet.0.groupId")
        self.app.render({"msg": "Patch securitygroup %s" % res})

    @ex(
        help="delete a security group",
        description="delete a security group",
        arguments=ARGS(
            [
                (
                    ["securitygroup"],
                    {"help": "securitygroup id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.securitygroup
        group_name = {"GroupName": oid}
        data = {"security_group": group_name}
        uri = "%s/computeservices/securitygroup/deletesecuritygroup" % self.baseuri
        entity = "securitygroup %s" % oid
        res = self.cmp_delete(uri, data=data, timeout=600, entity=entity, output=False)
        state = self.wait_for_service(oid, delta=2)
        if state == "DELETED":
            print("%s deleted" % entity)

    @ex(
        help="add a security group rule",
        description="add a security group rule",
        arguments=ARGS(
            [
                (
                    ["type"],
                    {
                        "help": "egress or ingress. For egress rule the destination. For ingress rule specify the "
                        "source",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["securitygroup"],
                    {"help": "securitygroup id", "action": "store", "type": str},
                ),
                (
                    ["-proto"],
                    {
                        "help": "protocol. can be tcp, udp, icmp or -1 for all",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": "can be an integer between 0 and 65535 or a range with start and end in the same "
                        "interval. Range format is <start>-<end>. Use -1 for all ports. Set subprotocol if "
                        "proto is icmp (8 for ping)",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dest"],
                    {
                        "help": "rule destination. Syntax <type>:<value>. Destination type can be SG, CIDR. For SG "
                        "value must be <sg_id>. For CIDR value should like 10.102.167.0/24.",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-source"],
                    {
                        "help": "rule source. Syntax <type>:<value>. Source type can be SG, CIDR. For SG "
                        "value must be <sg_id>. For CIDR value should like 10.102.167.0/24.",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add_rule(self):
        rule_type = self.app.pargs.type
        group_id = self.app.pargs.securitygroup
        dest = self.app.pargs.dest
        source = self.app.pargs.source
        port = self.app.pargs.port
        proto = self.app.pargs.proto
        from_port = -1
        to_port = -1
        if port is not None:
            port = str(port)
            if port == "-1":
                from_port = to_port = port
            else:
                port = port.split("-")
                if len(port) == 1:
                    from_port = to_port = port[0]
                else:
                    from_port, to_port = port

        if proto is None:
            proto = "-1"

        if rule_type not in ["ingress", "egress"]:
            raise Exception("rule type must be ingress or egress")
        if rule_type == "ingress":
            if source is None:
                raise Exception("ingress rule require source")
            dest = source.split(":")
        elif rule_type == "egress":
            if dest is None:
                raise Exception("egress rule require destination")
            dest = dest.split(":")
        if dest[0] not in ["SG", "CIDR"]:
            raise Exception("source/destination type must be SG or CIDR")
        data = {
            "GroupName": group_id,
            "IpPermissions.N": [{"FromPort": from_port, "ToPort": to_port, "IpProtocol": proto}],
        }
        if dest[0] == "SG":
            data["IpPermissions.N"][0]["UserIdGroupPairs"] = [{"GroupName": dest[1]}]
        elif dest[0] == "CIDR":
            data["IpPermissions.N"][0]["IpRanges"] = [{"CidrIp": dest[1]}]
        else:
            raise Exception("Wrong rule type")

        if rule_type == "egress":
            uri = "%s/computeservices/securitygroup/authorizesecuritygroupegress" % self.baseuri
            key = "AuthorizeSecurityGroupEgressResponse"
        elif rule_type == "ingress":
            uri = "%s/computeservices/securitygroup/authorizesecuritygroupingress" % self.baseuri
            key = "AuthorizeSecurityGroupIngressResponse"
        res = self.cmp_post(uri, data={"rule": data}, timeout=600, task_key=key)
        res = res.get(key).get("Return")
        self.app.render("create securitygroup rule %s" % res)

    @ex(
        help="delete a security group rule",
        description="delete a security group rule",
        arguments=ARGS(
            [
                (
                    ["type"],
                    {
                        "help": "egress or ingress. For egress rule the destination. For ingress rule specify the "
                        "source",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["securitygroup"],
                    {"help": "securitygroup id", "action": "store", "type": str},
                ),
                (
                    ["-proto"],
                    {
                        "help": "protocol. can be tcp, udp, icmp or -1 for all",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": "can be an integer between 0 and 65535 or a range with start and end in the same "
                        "interval. Range format is <start>-<end>. Use -1 for all ports. Set subprotocol if "
                        "proto is icmp (8 for ping)",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dest"],
                    {
                        "help": "rule destination. Syntax <type>:<value>. Destination type can be SG, CIDR. For SG "
                        "value must be <sg_id>. For CIDR value should like 10.102.167.0/24.",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-source"],
                    {
                        "help": "rule source. Syntax <type>:<value>. Source type can be SG, CIDR. For SG "
                        "value must be <sg_id>. For CIDR value should like 10.102.167.0/24.",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def del_rule(self):
        rule_type = self.app.pargs.type
        group_id = self.app.pargs.securitygroup
        dest = self.app.pargs.dest
        source = self.app.pargs.source
        port = self.app.pargs.port
        proto = self.app.pargs.proto
        from_port = -1
        to_port = -1
        if port is not None:
            port = str(port)
            port = port.split("-")
            if len(port) == 1:
                from_port = to_port = port[0]
            else:
                from_port, to_port = port

        if proto is None:
            proto = "-1"

        if rule_type not in ["ingress", "egress"]:
            raise Exception("rule type must be ingress or egress")
        if rule_type == "ingress":
            if source is None:
                raise Exception("ingress rule require source")
            dest = source.split(":")
        elif rule_type == "egress":
            if dest is None:
                raise Exception("egress rule require destination")
            dest = dest.split(":")
        if dest[0] not in ["SG", "CIDR"]:
            raise Exception("source/destination type must be SG or CIDR")
        data = {
            "GroupName": group_id,
            "IpPermissions.N": [{"FromPort": from_port, "ToPort": to_port, "IpProtocol": proto}],
        }
        if dest[0] == "SG":
            data["IpPermissions.N"][0]["UserIdGroupPairs"] = [{"GroupName": dest[1]}]
        elif dest[0] == "CIDR":
            data["IpPermissions.N"][0]["IpRanges"] = [{"CidrIp": dest[1]}]
        else:
            raise Exception("wrong rule type")

        if rule_type == "egress":
            uri = "%s/computeservices/securitygroup/revokesecuritygroupegress" % self.baseuri
            key = "RevokeSecurityGroupEgressResponse"
        elif rule_type == "ingress":
            uri = "%s/computeservices/securitygroup/revokesecuritygroupingress" % self.baseuri
            key = "RevokeSecurityGroupIngressResponse"
        res = self.cmp_delete(
            uri,
            data={"rule": data},
            timeout=600,
            entity="securitygroup rule",
            task_key=key,
        )


class GatewayNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = "netaas"
        stacked_type = "nested"
        label = "internet_gateways"
        description = "gateways service management"
        help = "gateways service management"

    @ex(
        help="get gateway templates",
        description="get gateway templates",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": "template id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def templates(self):
        self.get_service_definitions("NetworkGateway")

    @ex(
        help="create a gateway",
        description="create a gateway",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["-template"],
                    {"help": "template id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get("uuid")
        data = {"owner-id": account}
        gateway_type = self.app.pargs.template
        if gateway_type is not None:
            data["Nvl_GatewayType"] = gateway_type
        uri = "%s/networkservices/gateway/createinternetgateway" % self.baseuri
        res = self.cmp_post(uri, data={"gateway": data}, timeout=600)
        res = dict_get(res, "CreateInternetGatewayResponse.internetGateway.internetGatewayId")
        self.app.render({"msg": "add gateway %s" % res})

    @ex(
        help="get gateways",
        description="get gateways",
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
                    ["-ids"],
                    {
                        "help": "list of gateway id comma separated",
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
        params = ["accounts", "ids", "tags"]
        mappings = {
            "accounts": self.get_account_ids,
            "tags": lambda x: x.split(","),
            "ids": lambda x: x.split(","),
        }
        aliases = {
            "accounts": "owner-id.N",
            "ids": "InternetGatewayId.N",
            "tags": "tag-key.N",
            "size": "MaxResults",
            "page": "NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/networkservices/gateway/describeinternetgateways" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeInternetGatewaysResponse", {})
        page = self.app.pargs.page

        resp = {
            "count": len(res.get("internetGatewaySet")),
            "page": page,
            "total": res.get("nvl-internetGatewayTotal"),
            "sort": {"field": "id", "order": "asc"},
            "instances": res.get("internetGatewaySet"),
        }

        headers = [
            "id",
            "name",
            "state",
            "account",
            "internal-vpc",
            "external-ip-address",
            "bastion",
        ]
        fields = [
            "internetGatewayId",
            "nvl-name",
            "nvl-state",
            "nvl-ownerAlias",
            "attachmentSet.0.VpcSecurityGroupMembership.nvl-vpcName",
            "nvl-external_ip_address",
            "nvl-bastion",
        ]
        self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=40)

    @ex(
        help="get gateway",
        description="get gateway",
        arguments=ARGS(
            [
                (["gateway"], {"help": "gateway id", "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        gateway = self.app.pargs.gateway
        data = {"InternetGatewayId.N": [gateway]}
        uri = "%s/networkservices/gateway/describeinternetgateways" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeInternetGatewaysResponse.internetGatewaySet", default={})

        if len(res) == 0:
            raise Exception("gateway %s does not exist" % gateway)
        res = res[0]
        vpcs = res.pop("attachmentSet")
        self.app.render(res, details=True, maxsize=200)
        self.c("\nattached vpcs", "underline")
        headers = ["id", "name", "state"]
        fields = [
            "VpcSecurityGroupMembership.vpcId",
            "VpcSecurityGroupMembership.nvl-vpcName",
            "VpcSecurityGroupMembership.state",
        ]
        self.app.render(vpcs, headers=headers, fields=fields, maxsize=80)

    @ex(
        help="patch a gateway",
        description="patch a gateway",
        arguments=ARGS(
            [
                (["gateway"], {"help": "gateway id", "action": "store", "type": str}),
            ]
        ),
    )
    def patch(self):
        gateway = self.app.pargs.gateway
        data = {"GroupName": gateway}
        uri = "%s/networkservices/gateway/patchgateway" % self.baseuri
        res = self.cmp_patch(uri, data={"gateway": data}, timeout=600)
        res = dict_get(res, "PatchSecurityGroupResponse.instancesSet.0.groupId")
        self.app.render({"msg": "Patch gateway %s" % res})

    @ex(
        help="delete a gateway",
        description="delete a gateway",
        arguments=ARGS(
            [
                (["gateway"], {"help": "gateway id", "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.gateway
        data = {"InternetGatewayId": oid}
        uri = "%s/networkservices/gateway/deleteinternetgateway" % self.baseuri
        self.cmp_delete(uri, data=data, timeout=600, entity="gateway %s" % oid)
        self.wait_for_service(oid, accepted_state="DELETED")

    @ex(
        help="attach vpc from gateway",
        description="attach vpc from gateway",
        arguments=ARGS(
            [
                (["gateway"], {"help": "gateway id", "action": "store", "type": str}),
                (["vpc"], {"help": "vpc id", "action": "store", "type": str}),
            ]
        ),
    )
    def vpc_attach(self):
        gateway_id = self.app.pargs.gateway
        vpc_id = self.app.pargs.vpc

        data = {"InternetGatewayId": gateway_id, "VpcId": vpc_id}
        uri = "%s/networkservices/gateway/attachinternetgateway" % self.baseuri
        self.cmp_put(uri, data={"gateway": data}, timeout=600, task_key="AttachInternetGatewayResponse")
        self.app.render("attach vpc %s to gateway %s" % (vpc_id, gateway_id))

    @ex(
        help="detach vpc from gateway",
        description="detach vpc from gateway",
        arguments=ARGS(
            [
                (["gateway"], {"help": "gateway id", "action": "store", "type": str}),
                (["vpc"], {"help": "vpc id", "action": "store", "type": str}),
            ]
        ),
    )
    def vpc_detach(self):
        gateway_id = self.app.pargs.gateway
        vpc_id = self.app.pargs.vpc

        data = {"InternetGatewayId": gateway_id, "VpcId": vpc_id}
        uri = "%s/networkservices/gateway/detachinternetgateway" % self.baseuri
        result = self.cmp_put(uri, data={"gateway": data}, timeout=600, task_key="DetachInternetGatewayResponse")
        self.app.render("detach vpc %s from gateway %s" % (vpc_id, gateway_id))

    @ex(
        help="get gateway bastion",
        description="get gateway bastion",
        arguments=ARGS(
            [
                (["gateway"], {"help": "gateway id", "action": "store", "type": str}),
            ]
        ),
    )
    def bastion_get(self):
        gateway = self.app.pargs.gateway
        data = {"InternetGatewayId": gateway}
        uri = "%s/networkservices/gateway/describinternetgatewayebastion" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(
            res,
            "DescribeInternetGatewayBastionResponse.internetGatewayBastion",
            default={},
        )
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="create a gateway bastion",
        description="create a gateway bastion",
        arguments=ARGS(
            [
                (["gateway"], {"help": "gateway id", "action": "store", "type": str}),
            ]
        ),
    )
    def bastion_add(self):
        gateway = self.app.pargs.gateway
        data = {"InternetGatewayId": gateway}
        uri = "%s/networkservices/gateway/createinternetgatewaybastion" % self.baseuri
        self.cmp_post(
            uri,
            data={"bastion": data},
            timeout=600,
            task_key="CreateInternetGatewayBastionResponse",
        )
        self.app.render({"msg": "add gateway %s bastion" % gateway})

    @ex(
        help="delete a gateway bastion",
        description="delete a gateway bastion",
        arguments=ARGS(
            [
                (["gateway"], {"help": "gateway id", "action": "store", "type": str}),
            ]
        ),
    )
    def bastion_del(self):
        gateway = self.app.pargs.gateway
        data = {"InternetGatewayId": gateway}
        uri = "%s/networkservices/gateway/deleteinternetgatewaybastion" % self.baseuri
        self.cmp_delete(
            uri,
            data={"bastion": data},
            timeout=600,
            task_key="DeleteInternetGatewayBastionResponse",
            entity="gateway %s bastion" % gateway,
        )


class HealthMonitorNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = "netaas"
        stacked_type = "nested"
        label = "health_monitors"
        description = "health monitor service management"
        help = "health monitor service management"

    protocols = ["http", "https", "tcp", "imcp", "udp"]
    methods = ["get", "post", "options"]

    @ex(
        help="get health monitor templates",
        description="get health monitor templates",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": "template id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def templates(self):
        self.get_service_definitions("NetworkHealthMonitor")

    @ex(
        help="list health monitors",
        description="list health monitors",
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": "list of comma separated account ids",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": "list of comma separated health monitor ids",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": "list of comma separated tags",
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
        params = ["accounts", "ids", "tags"]
        mappings = {
            "accounts": self.get_account_ids,
            "ids": lambda x: x.split(","),
            "tags": lambda x: x.split(","),
        }
        aliases = {
            "accounts": "owner-id.N",
            "ids": "HealthMonitorId.N",
            "tags": "tag-key.N",
            "size": "MaxResults",
            "page": "Nvl-NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/networkservices/loadbalancer/healthmonitor/describehealthmonitors" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeHealthMonitorsResponse", {})
        page = self.app.pargs.page

        resp = {
            "count": len(res.get("healthMonitorSet")),
            "page": page,
            "total": res.get("healthMonitorTotal"),
            "sort": {"field": "id", "order": "asc"},
            "instances": res.get("healthMonitorSet"),
        }

        headers = [
            "uuid",
            "name",
            "state",
            "predefined",
            "account",
            "protocol",
            "interval",
            "timeout",
            "max_retries",
            "method",
            "uri",
            "expected",
        ]
        fields = [
            "healthMonitorId",
            "name",
            "state",
            "predefined",
            "nvl-ownerAlias",
            "protocol",
            "interval",
            "timeout",
            "maxRetries",
            "method",
            "requestURI",
            "expected",
        ]
        self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=40)

    @ex(
        help="get health monitor",
        description="get health monitor",
        arguments=ARGS(
            [
                (["id"], {"help": "health monitor uuid or name", "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        if is_uuid(oid):
            data = {"HealthMonitorId.N": [oid]}
        elif is_name(oid):
            data = {"HealthMonitorName": oid}
        else:
            raise Exception("Provide a valid uuid or name")
        uri = "%s/networkservices/loadbalancer/healthmonitor/describehealthmonitors" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeHealthMonitorsResponse.healthMonitorSet", default={})
        if len(res) == 0:
            raise Exception("Health monitor %s not found" % oid)
        res = res[0]
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="create health monitor",
        description="create health monitor",
        arguments=ARGS(
            [
                (["name"], {"help": "monitor name", "action": "store", "type": str}),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["protocol"],
                    {
                        "metavar": "protocol",
                        "help": f"protocol used to perform targets health check: {protocols}",
                        "choices": protocols,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "health monitor description",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-interval"],
                    {
                        "help": "interval in seconds in which a server is to be tested",
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-timeout"],
                    {
                        "help": "maximum time in seconds in which a response from the server must be received",
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-max_retries"],
                    {
                        "help": "maximum number of times the server is tested before it is declared down",
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-method"],
                    {
                        "metavar": "METHOD",
                        "help": f"method to send the health check request to the server: {methods}",
                        "choices": methods,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-url"],
                    {"help": "URL to GET or POST", "action": "store", "type": str},
                ),
                (
                    ["-expected"],
                    {"help": "expected string", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get("uuid")
        protocol = self.app.pargs.protocol
        method = self.app.pargs.method
        if method is not None:
            method = method.upper()

        data = {
            "owner-id": account,
            "Name": self.app.pargs.name,
            "Protocol": protocol.upper(),
        }

        params = [
            {"key": "Interval", "value": self.app.pargs.interval},
            {"key": "Timeout", "value": self.app.pargs.timeout},
            {"key": "MaxRetries", "value": self.app.pargs.max_retries},
            {"key": "Method", "value": method},
            {"key": "RequestURI", "value": self.app.pargs.url},
            {"key": "Expected", "value": self.app.pargs.expected},
            {"key": "Description", "value": self.app.pargs.desc},
        ]
        for param in params:
            if param.get("value") is not None:
                data[param.get("key")] = param.get("value")

        uri = "%s/networkservices/loadbalancer/healthmonitor/createhealthmonitor" % self.baseuri
        res = self.cmp_post(uri, data={"health_monitor": data}, timeout=600)
        res = dict_get(res, "CreateHealthMonitorResponse.HealthMonitor.healthMonitorId")
        self.app.render({"msg": "Add health monitor %s" % res})

    @ex(
        help="update health monitor",
        description="update health monitor",
        arguments=ARGS(
            [
                (["id"], {"help": "health monitor id", "action": "store", "type": str}),
                (
                    ["-interval"],
                    {
                        "help": "interval in seconds in which a server is to be tested",
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-timeout"],
                    {
                        "help": "maximum time in seconds in which a response from the server must be received",
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-max_retries"],
                    {
                        "help": "maximum number of times the server is tested before it is declared down",
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-method"],
                    {
                        "metavar": "METHOD",
                        "help": f"method to send the health check request to the server: {methods}",
                        "choices": methods,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-url"],
                    {"help": "URL to GET or POST", "action": "store", "type": str},
                ),
                (
                    ["-expected"],
                    {"help": "expected string", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.id
        method = self.app.pargs.method

        data = {"healthMonitorId": oid}
        params = [
            {"key": "Interval", "value": self.app.pargs.interval},
            {"key": "Timeout", "value": self.app.pargs.timeout},
            {"key": "MaxRetries", "value": self.app.pargs.max_retries},
            {
                "key": "Method",
                "value": method.upper() if method is not None else method,
            },
            {"key": "RequestURI", "value": self.app.pargs.url},
            {"key": "Expected", "value": self.app.pargs.expected},
        ]
        for param in params:
            if param.get("value") is not None:
                data[param.get("key")] = param.get("value")

        uri = "%s/networkservices/loadbalancer/healthmonitor/modifyhealthmonitor" % self.baseuri
        self.cmp_put(uri, data={"health_monitor": data}, timeout=600)
        self.app.render({"msg": "Update health monitor %s" % oid})

    @ex(
        help="delete health monitors",
        description="delete health monitors",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": "comma separated health monitor ids",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oids = self.app.pargs.ids.split(",")
        for oid in oids:
            data = {"healthMonitorId": oid}
            uri = "%s/networkservices/loadbalancer/healthmonitor/deletehealthmonitor" % self.baseuri
            self.cmp_delete(uri, data=data, timeout=600, entity="Health monitor %s" % oid)


class TargetGroupNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = "netaas"
        stacked_type = "nested"
        label = "target_groups"
        description = "target group service management"
        help = "target group service management"

    balancing_algorithms = ["round-robin", "ip-hash", "leastconn", "uri"]
    target_types = ["vm", "container"]

    @ex(
        help="get target group templates",
        description="get target group templates",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": "template id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def templates(self):
        self.get_service_definitions("NetworkTargetGroup")

    @ex(
        help="list target groups",
        description="list target groups",
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": "list of comma separated account ids",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": "list of comma separated target group ids",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": "list of comma separated tags",
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
        params = ["accounts", "ids", "tags"]
        mappings = {
            "accounts": self.get_account_ids,
            "ids": lambda x: x.split(","),
            "tags": lambda x: x.split(","),
        }
        aliases = {
            "accounts": "owner-id.N",
            "ids": "TargetGroupId.N",
            "tags": "tag-key.N",
            "size": "MaxResults",
            "page": "Nvl-NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/networkservices/loadbalancer/targetgroup/describetargetgroups" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeTargetGroupsResponse", {})
        page = self.app.pargs.page

        resp = {
            "count": len(res.get("targetGroupSet")),
            "page": page,
            "total": res.get("targetGroupTotal"),
            "sort": {"field": "id", "order": "asc"},
            "instances": res.get("targetGroupSet"),
        }

        headers = [
            "uuid",
            "name",
            "state",
            "account",
            "balancing_algorithm",
            "target_type",
            "N.targets",
            "health_monitor",
        ]
        fields = [
            "targetGroupId",
            "name",
            "state",
            "nvl-ownerAlias",
            "balancingAlgorithm",
            "targetType",
            "attachmentSet.TargetSet.totalTargets",
            "attachmentSet.HealthMonitor.name",
        ]
        self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=40)

    @ex(
        help="get target group",
        description="get target group",
        arguments=ARGS(
            [
                (["id"], {"help": "target group uuid or name", "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        if is_uuid(oid):
            data = {"TargetGroupId.N": [oid]}
        elif is_name(oid):
            data = {"TargetGroupName": oid}
        else:
            raise Exception("Provide a valid uuid or name")
        uri = "%s/networkservices/loadbalancer/targetgroup/describetargetgroups" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeTargetGroupsResponse.targetGroupSet", default={})
        if len(res) == 0:
            raise Exception("Target group %s not found" % oid)
        res = res[0]
        if self.is_output_text():
            attachments = res.pop("attachmentSet")
            targets = dict_get(attachments, "TargetSet.Targets", default=None)
            health_monitor = dict_get(attachments, "HealthMonitor", default=None)
            self.app.render(res, details=True, maxsize=200)
            self.c("\nattached targets", "underline")
            if targets is not None and len(targets) > 0:
                headers = [
                    "uuid",
                    "name",
                    "state",
                    "ip_address",
                    "port",
                    "hm_port",
                    "site",
                ]
                fields = [
                    "id",
                    "name",
                    "state",
                    "ip_address",
                    "lb_port",
                    "hm_port",
                    "site.name",
                ]
                self.app.render(targets, headers=headers, fields=fields, maxsize=80)
            self.c("\nattached health monitor", "underline")
            if health_monitor is not None:
                headers = [
                    "uuid",
                    "name",
                    "state",
                    "predefined",
                    "protocol",
                    "interval",
                    "timeout",
                    "max_retries",
                    "method",
                    "uri",
                    "expected",
                ]
                fields = [
                    "healthMonitorId",
                    "name",
                    "state",
                    "predefined",
                    "protocol",
                    "interval",
                    "timeout",
                    "maxRetries",
                    "method",
                    "requestURI",
                    "expected",
                ]
                self.app.render(health_monitor, headers=headers, fields=fields, maxsize=80)
        else:
            self.app.render(res, details=True, maxsize=100)

    @ex(
        help="create empty target group",
        description="create empty target group",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "target group name", "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["balancing_algorithm"],
                    {
                        "metavar": "balancing_algorithm",
                        "help": f"algorithm used to load balance targets: {balancing_algorithms}",
                        "choices": balancing_algorithms,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["target_type"],
                    {
                        "metavar": "target_type",
                        "help": f"target type: {target_types}",
                        "choices": target_types,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "target group description",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-health_monitor"],
                    {
                        "help": "id of the custom monitor to perform health checks on targets",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-transparent"],
                    {
                        "metavar": "TRANSPARENT",
                        "help": f"whether client IP addresses are visible to the backend servers, {[True, False]}",
                        "action": "store",
                        "type": bool,
                        "default": False,
                        "choices": [True, False],
                    },
                ),
            ]
        ),
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get("uuid")
        data = {
            "owner-id": account,
            "Name": self.app.pargs.name,
            "Description": self.app.pargs.desc,
            "BalancingAlgorithm": self.app.pargs.balancing_algorithm,
            "TargetType": self.app.pargs.target_type,
            "HealthMonitor": self.app.pargs.health_monitor,
            "Transparent": self.app.pargs.transparent,
        }

        uri = "%s/networkservices/loadbalancer/targetgroup/createtargetgroup" % self.baseuri
        res = self.cmp_post(uri, data={"target_group": data}, timeout=600)
        res = dict_get(res, "CreateTargetGroupResponse.TargetGroup.targetGroupId")
        self.app.render({"msg": "Add target group %s" % res})

    @ex(
        help="update target group",
        description="update target group",
        arguments=ARGS(
            [
                (["id"], {"help": "target group id", "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": "target group description",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-balancing_algorithm"],
                    {
                        "metavar": "BALANCING_ALGORITHM",
                        "help": f"algorithm used to load balance targets: {balancing_algorithms}",
                        "choices": balancing_algorithms,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-transparent"],
                    {
                        "metavar": "TRANSPARENT",
                        "help": f"whether client IP addresses are visible to the backend servers, {[True, False]}",
                        "action": "store",
                        "type": bool,
                        "default": False,
                        "choices": [True, False],
                    },
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.id

        data = {"targetGroupId": oid}
        params = [
            {"key": "BalancingAlgorithm", "value": self.app.pargs.balancing_algorithm},
            {"key": "Description", "value": self.app.pargs.desc},
            {"key": "Transparent", "value": self.app.pargs.transparent},
        ]
        for param in params:
            if param.get("value") is not None:
                data[param.get("key")] = param.get("value")

        uri = "%s/networkservices/loadbalancer/targetgroup/modifytargetgroup" % self.baseuri
        self.cmp_put(uri, data={"target_group": data}, timeout=600)
        self.app.render({"msg": "Update target group %s" % oid})

    @ex(
        help="delete target groups",
        description="delete target groups",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": "comma separated target group ids",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oids = self.app.pargs.ids.split(",")
        for oid in oids:
            data = {"targetGroupId": oid}
            uri = "%s/networkservices/loadbalancer/targetgroup/deletetargetgroup" % self.baseuri
            self.cmp_delete(uri, data=data, timeout=600, entity="Target group %s" % oid)

    @ex(
        help="register targets with target group",
        description="register targets with target group",
        arguments=ARGS(
            [
                (["id"], {"help": "target group id", "action": "store", "type": str}),
                (
                    ["targets"],
                    {
                        "help": "comma separated list of couples <target_id>:<lb_port> or triplets "
                        "<target_id>:<target_port>:<hm_port>",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def targets_register(self):
        oid = self.app.pargs.id
        targets = self.app.pargs.targets

        data = {"TargetGroupId": oid, "Targets": []}

        # parse targets
        targets = targets.split(",")
        for item in targets:
            target = item.split(":")
            # remove white spaces
            target = [x for x in target if x.strip()]
            if 2 <= len(target) <= 3:
                target_id = target[0]
                target_port = target[1]
                d = {"Id": target_id, "LbPort": int(target_port)}
                if len(target) == 3:
                    target_hm_port = target[2]
                    d.update({"HmPort": int(target_hm_port)})
                data["Targets"].append(d)
            else:
                raise Exception("Bad format: %s" % item)

        uri = "%s/networkservices/loadbalancer/targetgroup/registertargets" % self.baseuri
        self.cmp_put(uri, data={"target_group": data}, timeout=600)
        for item in data["Targets"]:
            self.app.render({"msg": "Register target %s with target group %s" % (item.get("Id"), oid)})

    @ex(
        help="deregister targets from target group",
        description="deregister targets from target group",
        arguments=ARGS(
            [
                (["id"], {"help": "target group id", "action": "store", "type": str}),
                (
                    ["targets"],
                    {
                        "help": "comma separated list of target ids",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def targets_deregister(self):
        oid = self.app.pargs.id
        targets = self.app.pargs.targets

        data = {
            "TargetGroupId": oid,
            "Targets": [],
        }

        # parse targets
        target_ids = targets.strip().split(",")
        for target_id in target_ids:
            if target_id == "":
                raise Exception("Target ID cannot be empty")
            data["Targets"].append({"Id": target_id})

        uri = "%s/networkservices/loadbalancer/targetgroup/deregistertargets" % self.baseuri
        self.cmp_put(uri, data={"target_group": data}, timeout=600)
        for item in data["Targets"]:
            self.app.render({"msg": "Deregister target %s from target group %s" % (item.get("Id"), oid)})

    @ex(
        help="register health monitor with target group",
        description="register health monitor with target group",
        arguments=ARGS(
            [
                (["id"], {"help": "target group id", "action": "store", "type": str}),
                (
                    ["monitor"],
                    {"help": "health monitor id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def health_monitor_register(self):
        oid = self.app.pargs.id
        monitor_id = self.app.pargs.monitor

        data = {
            "TargetGroupId": oid,
            "HealthMonitorId": monitor_id,
        }

        uri = "%s/networkservices/loadbalancer/targetgroup/registerhealthmonitor" % self.baseuri
        self.cmp_put(uri, data={"target_group": data}, timeout=600)
        self.app.render({"msg": "Register health monitor %s with target group %s" % (monitor_id, oid)})

    @ex(
        help="deregister health monitor from target group",
        description="deregister health monitor from target group",
        arguments=ARGS([(["id"], {"help": "target group id", "action": "store", "type": str})]),
    )
    def health_monitor_deregister(self):
        oid = self.app.pargs.id
        data = {"TargetGroupId": oid}
        uri = "%s/networkservices/loadbalancer/targetgroup/deregisterhealthmonitor" % self.baseuri
        self.cmp_put(uri, data={"target_group": data}, timeout=600)
        self.app.render({"msg": "Deregister health monitor from target group %s" % oid})


class ListenerNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = "netaas"
        stacked_type = "nested"
        label = "listeners"
        description = "listener service management"
        help = "listener service management"

    traffic_types_mapping = {
        "tcp": {
            "template": "TCP",
            "sslPassthrough": False,
            "serverSslEnabled": False,
        },
        "http": {
            "template": "HTTP",
            "sslPassthrough": False,
            "serverSslEnabled": False,
        },
        "ssl-passthrough": {"template": "HTTPS", "sslPassthrough": True, "serverSslEnabled": False},
        "https-offloading": {
            "template": "HTTPS",
            "sslPassthrough": False,
            "serverSslEnabled": False,
        },
        "https-end-to-end": {"template": "HTTPS", "sslPassthrough": False, "serverSslEnabled": True},
    }

    traffic_types = list(traffic_types_mapping.keys())

    persistence_methods = ["sourceip", "cookie", "ssl-sessionid"]

    cookie_modes = ["insert", "prefix", "app-session"]

    cipher_suites = [
        "DEFAULT",
        "ECDHE-RSA-AES128-GCM-SHA256",
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES256-SHA",
        "ECDHE-ECDSA-AES256-SHA",
        "ECDH-ECDSA-AES256-SHA",
        "ECDH-RSA-AES256-SHA",
        "AES256-SHA",
        "AES128-SHA",
        "DES-CBC3-SHA",
    ]

    @ex(
        help="get listener templates",
        description="get listener templates",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": "template id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def templates(self):
        self.get_service_definitions("NetworkListener")

    @ex(
        help="list listeners",
        description="list listeners",
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": "list of comma separated account ids",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": "list of comma separated listener ids",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": "list of comma separated tags",
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
        params = ["accounts", "ids", "tags"]
        mappings = {
            "accounts": self.get_account_ids,
            "ids": lambda x: x.split(","),
            "tags": lambda x: x.split(","),
        }
        aliases = {
            "accounts": "owner-id.N",
            "ids": "ListenerId.N",
            "tags": "tag-key.N",
            "size": "MaxResults",
            "page": "Nvl-NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/networkservices/loadbalancer/listener/describelisteners" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeListenersResponse", {})
        page = self.app.pargs.page

        resp = {
            "count": len(res.get("listenerSet")),
            "page": page,
            "total": res.get("listenerTotal"),
            "sort": {"field": "id", "order": "asc"},
            "instances": res.get("listenerSet"),
        }

        headers = [
            "uuid",
            "name",
            "state",
            "predefined",
            "account",
            "traffic_type",
            "persistence",
        ]
        fields = [
            "listenerId",
            "name",
            "state",
            "predefined",
            "nvl-ownerAlias",
            "trafficType",
            "persistence.method",
        ]
        self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=40)

    @ex(
        help="get listener",
        description="get listener",
        arguments=ARGS(
            [
                (["id"], {"help": "listener uuid or name", "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        if is_uuid(oid):
            data = {"ListenerId.N": [oid]}
        elif is_name(oid):
            data = {"ListenerName": oid}
        else:
            raise Exception("Provide a valid uuid or name")
        uri = "%s/networkservices/loadbalancer/listener/describelisteners" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeListenersResponse.listenerSet", default={})
        if len(res) == 0:
            raise Exception("Listener %s not found" % oid)
        res = res[0]
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="create listener",
        description="create listener",
        arguments=ARGS(
            [
                (["name"], {"help": "listener name", "action": "store", "type": str}),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["traffic_type"],
                    {
                        "metavar": "traffic_type",
                        "help": f"incoming traffic profile; one of: {traffic_types}",
                        "choices": traffic_types,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-desc"],
                    {"help": "listener description", "action": "store", "type": str},
                ),
                (
                    ["-persistence"],
                    {
                        "metavar": "PERSISTENCE",
                        "help": f"persistence type: {persistence_methods}",
                        "choices": persistence_methods,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-cookie_name"],
                    {"help": "cookie name", "action": "store", "type": str},
                ),
                (
                    ["-cookie_mode"],
                    {
                        "metavar": "COOKIE_MODE",
                        "help": f"cookie mode: {cookie_modes}",
                        "choices": cookie_modes,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-expire"],
                    {"help": "expire time in seconds", "action": "store", "type": int},
                ),
                (
                    ["-client_cert_path"],
                    {"help": "client certificate path", "action": "store", "type": str},
                ),
                (
                    ["-server_cert_path"],
                    {"help": "server certificate path", "action": "store", "type": str},
                ),
                (
                    ["-client_cipher"],
                    {
                        "metavar": "CLIENT_CIPHER",
                        "help": f"cipher suite used by client; one of: {cipher_suites}",
                        "choices": cipher_suites,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-server_cipher"],
                    {
                        "metavar": "SERVER_CIPHER",
                        "help": f"cipher suite used by server; one of: {cipher_suites}",
                        "choices": cipher_suites,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-insert_x_forwarded_for"],
                    {
                        "metavar": "INSERT_X_FORWARDED_FOR",
                        "help": "insert X-Forwarded-For HTTP header",
                        "choices": [True, False],
                        "action": "store",
                        "type": bool,
                    },
                ),
                (
                    ["-redirect_to"],
                    {"help": "url to redirect client requests", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get("uuid")
        data = {
            "owner-id": account,
            "Name": self.app.pargs.name,
            "Description": self.app.pargs.desc,
            "TrafficType": self.app.pargs.traffic_type,
            "Persistence": self.app.pargs.persistence,
            "CookieName": self.app.pargs.cookie_name,
            "CookieMode": self.app.pargs.cookie_mode,
            "ExpireTime": self.app.pargs.expire,
            "URLRedirect": self.app.pargs.redirect_to,
            "InsertXForwardedFor": self.app.pargs.insert_x_forwarded_for,
        }

        client_cert_path = self.app.pargs.client_cert_path
        if client_cert_path is not None:
            client_cert = self.load_file(client_cert_path)
            data.update({"ClientCertificate": client_cert, "ClientCipher": self.app.pargs.client_cipher})
        server_cert_path = self.app.pargs.server_cert_path
        if server_cert_path is not None:
            server_cert = self.load_file(server_cert_path)
            data.update({"ServerCertificate": server_cert, "ServerCipher": self.app.pargs.server_cipher})

        uri = "%s/networkservices/loadbalancer/listener/createlistener" % self.baseuri
        res = self.cmp_post(uri, data={"listener": data}, timeout=600)
        res = dict_get(res, "CreateListenerResponse.Listener.listenerId")
        self.app.render({"msg": "Add listener %s" % res})

    @ex(
        help="update listener",
        description="update listener",
        arguments=ARGS(
            [
                (["id"], {"help": "listener id", "action": "store", "type": str}),
                (
                    ["-desc"],
                    {"help": "listener description", "action": "store", "type": str},
                ),
                (
                    ["-persistence"],
                    {
                        "metavar": "PERSISTENCE",
                        "help": f"persistence type: {persistence_methods}",
                        "choices": persistence_methods,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-cookie_name"],
                    {
                        "help": "cookie name",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-cookie_mode"],
                    {
                        "metavar": "COOKIE_MODE",
                        "help": f"cookie mode: {cookie_modes}",
                        "choices": cookie_modes,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-expire"],
                    {"help": "expire time in seconds", "action": "store", "type": int},
                ),
                # (['-client_cert_path'], {'help': 'client certificate path', 'action': 'store', 'type': str}),
                # (['-server_cert_path'], {'help': 'server certificate path', 'action': 'store', 'type': str}),
                # (['-client_cipher'], {'help': 'cipher suite used by client', 'choices': cipher_suites, 'action': 'store',
                #                       'type': str}),
                # (['-server_cipher'], {'help': 'cipher suite used by server', 'choices': cipher_suites, 'action': 'store',
                #                       'type': str}),
                (
                    ["-insert_x_forwarded_for"],
                    {
                        "metavar": "INSERT_X_FORWARDED_FOR",
                        "help": "insert X-Forwarded-For HTTP header, ['True', 'False']",
                        "choices": ["True", "False", "true", "false"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-redirect_to"],
                    {
                        "help": "url to redirect client requests",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.id
        data = {
            "listenerId": oid,
            "Description": self.app.pargs.desc,
            "Persistence": self.app.pargs.persistence,
            "CookieName": self.app.pargs.cookie_name,
            "CookieMode": self.app.pargs.cookie_mode,
            "ExpireTime": self.app.pargs.expire,
            "InsertXForwardedFor": str2bool(self.app.pargs.insert_x_forwarded_for),
            "URLRedirect": self.app.pargs.redirect_to,
        }
        data = {k: v for k, v in data.items() if v is not None}

        uri = "%s/networkservices/loadbalancer/listener/modifylistener" % self.baseuri
        self.cmp_put(uri, data={"listener": data}, timeout=600)
        self.app.render({"msg": "Update listener %s" % oid})

    @ex(
        help="delete listeners",
        description="delete listeners",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": "comma separated listener ids",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oids = self.app.pargs.ids.split(",")
        for oid in oids:
            data = {"listenerId": oid}
            uri = "%s/networkservices/loadbalancer/listener/deletelistener" % self.baseuri
            self.cmp_delete(uri, data=data, timeout=600, entity="Listener %s" % oid)

    @staticmethod
    def get_traffic_type(**kvargs):
        """

        :param kvargs:
        :return:
        """
        template = kvargs.get("template").upper()
        ssl_passthrough = str2bool(kvargs.get("sslPassthrough"))
        server_ssl_enabled = str2bool(kvargs.get("serverSslEnabled"))

        for k, v in ListenerNetServiceController.traffic_types_mapping.items():
            if (
                v.get("template") == template
                and v.get("sslPassthrough") == ssl_passthrough
                and v.get("serverSslEnabled") == server_ssl_enabled
            ):
                return k
        raise Exception("Malformed listener from hypervisor: %s" % kvargs)


class LoadBalancerNetServiceController(BusinessControllerChild, AdminChildController):
    class Meta:
        stacked_on = "netaas"
        stacked_type = "nested"
        label = "load_balancers"
        description = "load balancer service management"
        help = "load balancer service management"

    protocols = ["http", "https"]
    deployment_envs = ["prod", "preprod", "stage", "test"]

    @ex(
        help="get load balancer templates",
        description="get load balancer templates",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": "template id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def templates(self):
        self.get_service_definitions("NetworkLoadBalancer")

    @ex(
        help="list load balancers",
        description="list load balancers",
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": "list of comma separated account ids",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": "list of comma separated load balancer ids",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": "list of comma separated tags",
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
        params = ["accounts", "ids", "tags"]
        mappings = {
            "accounts": self.get_account_ids,
            "ids": lambda x: x.split(","),
            "tags": lambda x: x.split(","),
        }
        aliases = {
            "accounts": "owner-id.N",
            "ids": "LoadBalancerId.N",
            "tags": "tag-key.N",
            "size": "MaxResults",
            "page": "Nvl-NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/networkservices/loadbalancer/describeloadbalancers" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeLoadBalancersResponse", {})
        page = self.app.pargs.page

        resp = {
            "count": len(res.get("loadBalancerSet")),
            "page": page,
            "total": res.get("loadBalancerTotal"),
            "sort": {"field": "id", "order": "asc"},
            "instances": res.get("loadBalancerSet"),
        }

        headers = [
            "uuid",
            "name",
            "state",
            "runstate",
            "account",
            "vip",
            "protocol",
            "port",
            "listener",
            "target_group",
        ]
        fields = [
            "loadBalancerId",
            "name",
            "state",
            "runstate",
            "nvl-ownerAlias",
            "virtualIP",
            "protocol",
            "port",
            "attachmentSet.Listener.name",
            "attachmentSet.TargetGroup.name",
        ]
        self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=40)

    @ex(
        help="get load balancer",
        description="get load balancer",
        arguments=ARGS(
            [
                (["id"], {"help": "load balancer uuid or name", "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        if is_uuid(oid):
            data = {"LoadBalancerId.N": [oid]}
        elif is_name(oid):
            data = {"LoadBalancerName": oid}
        else:
            raise Exception("Provide a valid uuid or name")
        uri = "%s/networkservices/loadbalancer/describeloadbalancers" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeLoadBalancersResponse.loadBalancerSet", default={})
        if len(res) == 0:
            raise Exception("Load balancer %s not found" % oid)
        res = res[0]
        if self.is_output_text():
            attachments = res.pop("attachmentSet")
            listener = dict_get(attachments, "Listener", default=None)
            target_group = dict_get(attachments, "TargetGroup", default=None)
            balanced_target = dict_get(target_group, "attachmentSet.TargetSet.Targets", default=None)
            self.app.render(res, details=True, maxsize=200)
            self.c("\nattached listener", "underline")
            if listener is not None:
                headers = [
                    "uuid",
                    "name",
                    "state",
                    "predefined",
                    "traffic_type",
                    "persistence",
                ]
                fields = [
                    "listenerId",
                    "name",
                    "state",
                    "predefined",
                    "trafficType",
                    "persistence.method",
                ]
                self.app.render(listener, headers=headers, fields=fields, maxsize=80)
            self.c("\nattached target group", "underline")
            if target_group is not None:
                headers = [
                    "uuid",
                    "name",
                    "state",
                    "balancing_algorithm",
                    "target_type",
                ]
                fields = [
                    "targetGroupId",
                    "name",
                    "state",
                    "balancingAlgorithm",
                    "targetType",
                ]
                self.app.render(target_group, headers=headers, fields=fields, maxsize=80)
            self.c("\nbalanced targets", "underline")
            if balanced_target is not None:
                headers = ["uuid", "name", "state", "ip_address", "port", "hm_port", "site"]
                fields = ["id", "name", "state", "ip_address", "lb_port", "hm_port", "site.name"]
                self.app.render(balanced_target, headers=headers, fields=fields, maxsize=80)
        else:
            self.app.render(res, details=True, maxsize=100)

    @ex(
        help="create load balancer",
        description="create load balancer",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "load balancer name", "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["template"],
                    {
                        "help": "load balancer service definition",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["protocol"],
                    {
                        "metavar": "protocol",
                        "help": f"protocol for connections to load balancer: {protocols}",
                        "action": "store",
                        "type": str,
                        "choices": protocols,
                    },
                ),
                (["port"], {"help": "port number", "action": "store", "type": int}),
                (["listener"], {"help": "listener id", "action": "store", "type": str}),
                (
                    ["target_group"],
                    {"help": "target group id", "action": "store", "type": str},
                ),
                (
                    ["-desc"],
                    {
                        "help": "load balancer description",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-static_ip"],
                    {
                        "help": "load balancer frontend ip address",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-max_conn"],
                    {
                        "help": "maximum concurrent connections",
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-max_conn_rate"],
                    {
                        "help": "maximum connections per second",
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-deploy_env"],
                    {
                        "metavar": "DEPLOY_ENV",
                        "help": f"project deployment environment: {deployment_envs}",
                        "choices": deployment_envs,
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get("uuid")
        protocol = self.app.pargs.protocol
        data = {
            "owner-id": account,
            "Name": self.app.pargs.name,
            "Template": self.app.pargs.template,
            "Protocol": protocol.upper(),
            "Port": self.app.pargs.port,
            "Listener": self.app.pargs.listener,
            "TargetGroup": self.app.pargs.target_group,
        }

        params = [
            {"key": "Description", "value": self.app.pargs.desc},
            {"key": "StaticIP", "value": self.app.pargs.static_ip},
            {"key": "MaxConnections", "value": self.app.pargs.max_conn},
            {"key": "MaxConnectionRate", "value": self.app.pargs.max_conn_rate},
            {"key": "DeploymentEnvironment", "value": self.app.pargs.deploy_env},
        ]
        for param in params:
            if param.get("value") is not None:
                data[param.get("key")] = param.get("value")

        uri = "%s/networkservices/loadbalancer/createloadbalancer" % self.baseuri
        res = self.cmp_post(uri, data={"load_balancer": data}, timeout=600)
        uuid = dict_get(res, "CreateLoadBalancerResponse.LoadBalancer.loadBalancerId")
        self.wait_for_service(uuid)
        self.app.render({"msg": "Add load balancer %s" % uuid})

    @ex(
        help="update load balancer",
        description="update load balancer",
        arguments=ARGS(
            [
                (["id"], {"help": "load balancer id", "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": "load balancer description",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-protocol"],
                    {
                        "metavar": "PROTOCOL",
                        "help": f"protocol for connections to load balancer: {protocols}",
                        "action": "store",
                        "type": str,
                        "choices": protocols,
                    },
                ),
                (["-port"], {"help": "port number", "action": "store", "type": int}),
                (
                    ["-max_conn"],
                    {
                        "help": "maximum concurrent connections",
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-max_conn_rate"],
                    {
                        "help": "maximum connections per second",
                        "action": "store",
                        "type": int,
                    },
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.id

        data = {"loadBalancerId": oid}
        params = [
            {"key": "Description", "value": self.app.pargs.desc},
            {"key": "Protocol", "value": self.app.pargs.protocol},
            {"key": "Port", "value": self.app.pargs.port},
            {"key": "MaxConnections", "value": self.app.pargs.max_conn},
            {"key": "MaxConnectionRate", "value": self.app.pargs.max_conn_rate},
        ]
        for param in params:
            if param.get("value") is not None:
                data[param.get("key")] = param.get("value")

        uri = "%s/networkservices/loadbalancer/modifyloadbalancer" % self.baseuri
        res = self.cmp_put(uri, data={"load_balancer": data}, timeout=600)
        uuid = dict_get(res, "ModifyLoadBalancerResponse.LoadBalancer.loadBalancerId")
        self.wait_for_service(uuid)
        self.app.render({"msg": "Update load balancer %s" % oid})

    @ex(
        help="delete load balancer",
        description="delete load balancer",
        arguments=ARGS(
            [
                (["id"], {"help": "load balancer id", "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        uuid = self.app.pargs.id
        data = {"loadBalancerId": uuid}
        uri = "%s/networkservices/loadbalancer/deleteloadbalancer" % self.baseuri
        entity = "Load balancer %s" % uuid
        res = self.cmp_delete(uri, data=data, timeout=600, entity=entity, output=False)
        if res is not None:
            state = self.wait_for_service(uuid, accepted_state="DELETED")
            if state == "DELETED":
                print("%s deleted" % entity)

    @ex(
        help="enable load balancer",
        description="enable load balancer",
        arguments=ARGS(
            [
                (["id"], {"help": "load balancer id", "action": "store", "type": str}),
            ]
        ),
    )
    def start(self):
        uuid = self.app.pargs.id
        data = {"loadBalancerId": uuid}
        uri = "%s/networkservices/loadbalancer/enableloadbalancer" % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": "Load balancer %s enabled" % uuid})

    @ex(
        help="disable load balancer",
        description="disable load balancer",
        arguments=ARGS(
            [
                (["id"], {"help": "load balancer id", "action": "store", "type": str}),
            ]
        ),
    )
    def stop(self):
        uuid = self.app.pargs.id
        data = {"loadBalancerId": uuid}
        uri = "%s/networkservices/loadbalancer/disableloadbalancer" % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": "Load balancer %s disabled" % uuid})

    @ex(
        help="delete load balancer generic services",
        description="delete load balancer generic services",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {"help": "account id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete_predefined_service(self):
        account = self.app.pargs.account

        plugintypes = ["NetworkHealthMonitor", "NetworkListener"]
        for plugintype in plugintypes:
            version = "v2.0"
            uri = "/%s/nws/serviceinsts" % version

            data = {
                "account_id": account,
                "plugintype": plugintype,
                "page": 0,
                "size": 10,
            }
            res = self.cmp_get(uri, data=data)
            serviceinsts = res.get("serviceinsts")
            for serviceinst in serviceinsts:
                uuid = serviceinst["uuid"]
                name = serviceinst["name"]
                plugintype = serviceinst["plugintype"]
                if plugintype == plugintype:
                    print("deleting %s ..." % name)

                    value = uuid
                    force = False
                    propagate = False
                    data = {"force": force, "propagate": propagate}
                    uri = "/v2.0/nws/serviceinsts/%s" % value
                    self.cmp_delete(uri, data=data, timeout=180, entity="service instance %s" % value)


class SshGatewayNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = "netaas"
        stacked_type = "nested"
        label = "sshgw"
        description = "ssh gateway service management"
        help = "ssh gateway service management"

    @ex(
        help="get ssh gateway configurations",
        description="get ssh gateway configurations",
        # example="todo ",
        # epilog="ciao",
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
                    ["-ids"],
                    {
                        "help": "list of ssh gateway configurations id comma separated",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-names"],
                    {
                        "help": "list of ssh gateway configurations names comma separated",
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
    def conf_list(self):
        params = ["accounts", "ids", "tags", "gw_type", "names"]
        mappings = {
            "accounts": self.get_account_ids,
            "tags": lambda x: x.split(","),
            "ids": lambda x: x.split(","),
            "names": lambda x: x.split(","),
        }

        aliases = {
            "accounts": "owner-id.N",
            "ids": "sshgwconf-id.N",
            "names": "sshgwconf-name.N",
            "tags": "tag.N",
        }

        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/networkservices/ssh_gateway/configuration/list" % self.baseuri
        res = self.cmp_get(uri, data=data)

        res = res.get("DescribeSshGatewaysConfResponse", {})
        page = self.app.pargs.page

        resp = {
            "count": len(res.get("sshGatewaySet")),
            "page": page,
            "total": res.get("nvl-sshGatewayTotal"),
            "sort": {"field": "id", "order": "asc"},
            "instances": res.get("sshGatewaySet"),
        }

        transform = {"nvl-state": self.color_error}
        headers = ["id", "name", "status", "account", "gw_type", "destination", "allowed_ports"]
        fields = [
            "sshGatewayConfId",
            "nvl-name",
            "nvl-state",
            "nvl-ownerAlias",
            "gwType",
            "destination",
            "parsed_ports_set",
        ]
        self.app.render(
            resp,
            key="instances",
            headers=headers,
            fields=fields,
            transform=transform,
            maxsize=40,
        )

    @ex(
        help="get ssh gateway configuration",
        description="get ssh gateway configuration",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "ssh gateway configuration id",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def conf_get(self):
        data = {"size": 2}
        id = self.app.pargs.id
        if self.is_uuid(id):
            data["sshgwconf-id.N"] = [id]
        elif self.is_name(id):
            data["sshgwconf-name.N"] = [id]

        uri = f"{self.baseuri}/networkservices/ssh_gateway/configuration/list"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeSshGatewaysConfResponse.sshGatewaySet", default={})

        if len(res) == 0:
            raise Exception("ssh gateway configuration %s does not exist" % id)
        if len(res) > 1:
            raise Exception("found more than one ssh gateway configuration. Specify id or uuid instead of name.")
        res = res[0]
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="add ssh gateway configuration",
        description="add ssh gateway configuration",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "configuration name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["gw_type"],
                    {
                        "metavar": "gw_type",
                        "help": "ssh gateway type (gw_dbaas,gw_cpaas)",
                        "choices": ["gw_dbaas", "gw_cpaas"],
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "configuration description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["dest_uuid"],
                    {
                        "help": "destination service instance uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-allowed_ports"],
                    {
                        "help": "comma separated list of ranges (start-end) or single ports. e.g. 8000-9000,22",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-forbidden_ports"],
                    {
                        "help": "comma separated list of ranges (start-end) or single ports. e.g. 8000-9000,22",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def conf_add(self):
        # gw_dbaas automatically sets as allowed port only the db port
        if self.app.pargs.gw_type == "gw_dbaas":
            self.app.warning("the only allowed port is going to be the database port")
            self.app.pargs.allowed_ports = "DB_PORT"  # placeholder value
            self.app.pargs.forbidden_ports = None

        if self.app.pargs.gw_type == "gw_cpaas" and self.app.pargs.allowed_ports is None:
            self.app.error("Specify at least one port for -allowed_ports parameter")
            return

        from beecell.simple import set_request_params

        configuration = {}
        configuration.update(
            set_request_params(
                self.app.pargs,
                ["name", "desc", "gw_type", "dest_uuid", "allowed_ports", "forbidden_ports"],
            )
        )
        if configuration.get("allowed_ports", None):
            configuration["allowed_ports"] = configuration["allowed_ports"].split(",")

        if configuration.get("forbidden_ports", None):
            configuration["forbidden_ports"] = configuration["forbidden_ports"].split(",")

        data = {"configuration": configuration}
        uri = f"{self.baseuri}/networkservices/ssh_gateway/configuration/create"
        res = self.cmp_request_v2(
            "POST",
            uri=uri,
            data=data,
            ask_for_confirmation=True,
            entity="a new ssh gateway configuration instance",
            task_key_path=["CreateSshGatewayConfResponse"],
            action="create",
        )
        # res = self.cmp_post(uri, data=data)
        uuid = dict_get(res, "CreateSshGatewayConfResponse.uuid")
        # self.wait_for_service(uuid)
        self.wait_for_service_v2(uuid)
        transform = {"msg": lambda x: self.color_string(x, "GREEN")}
        self.app.render({"msg": f"Created ssh gateway configuration {uuid}"}, transform=transform)

    @ex(
        help="delete a ssh gateway configuration",
        description="delete a ssh gateway configuration",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "ssh gateway conf id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def conf_delete(self):
        """
        delete a ssh gateway configuration
        """
        data = {"ssh_gateway_id": self.app.pargs.id}
        uri = f"{self.baseuri}/networkservices/ssh_gateway/configuration/delete"
        self.cmp_request_v2(
            "DELETE",
            uri=uri,
            data=data,
            request_timeout=600,
            entity=f"ssh gateway conf {self.app.pargs.id}",
            output=False,
        )
        self.wait_for_service_v2(self.app.pargs.id, accepted_state="DELETED")
        transform = {"msg": lambda x: self.color_string(x, "GREEN")}
        self.app.render({"msg": f"Deleted configuration {self.app.pargs.id}"}, transform=transform)

    @ex(
        help="activate ssh gw configuration",
        description="activate ssh gw configuration",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "ssh gateway conf id", "action": "store", "type": str},
                ),
                (["port"], {"help": "destination port", "action": "store", "type": str}),
            ]
        ),
    )
    def conf_activate(self):
        """
        activate a ssgh gateway configuration, for target user
        """
        data = {"ssh_gateway_id": self.app.pargs.id, "destination_port": self.app.pargs.port}
        uri = f"{self.baseuri}/networkservices/ssh_gateway/configuration/activate"
        res = self.cmp_request_v2(
            "PUT", uri, data=data, entity=f"ssh gateway conf {self.app.pargs.id}", action="activate", output=False
        )
        self.wait_for_service_v2(self.app.pargs.id)
        res = res.get("ActivateSshGatewayConfResponse")
        sample_command = res.get("commandTemplate")
        private_key = res.get("keyMaterial")
        if sample_command:
            self.c("\nsample command", "underline")
            self.app.render({"msg": sample_command})
        if private_key:
            self.c("\nkey material", "underline")
            self.app.render({"msg": private_key})
