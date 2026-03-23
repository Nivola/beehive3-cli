# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

import os
from typing import List, Optional
from urllib.parse import urlencode, quote
from yaml import safe_load as yaml_load, dump as yaml_dump
from ujson import load as json_load, dump as json_dump
from cement import ex

from prompt_toolkit.shortcuts import choice
from prompt_toolkit.filters import is_done

from beecell.types.type_dict import dict_get
from beecell.types.type_string import str2bool
from beecell.types.bu.lbaas import UpdateLbaasDict, LbConfigurationDict, LbBackendDict
from beecell.types.type_id import is_name, is_uuid
from beehive3_cli.core.controller import ARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild
from beehive3_cli.plugins.administration.controllers.child import AdminChildController
from beehive3_cli.translate import _
from beehive3_cli.core.prompt_utils import PromptTool

DEPRECATED = "deprecated"
CURRENT = "netaas"


class NetaaServiceController(BusinessControllerChild):
    class Meta:
        label = CURRENT
        description = _("network service management")
        help = _("network service management")

    @ex(
        help=_("get network service info"),
        description=_(
            "This command retrieves network service information for the specified account. "
            "The account ID is required to get the info for a particular account. "
            "This provides details about the network services configured for that account."
        ),
        example="beehive bu netaas info openspace",
        arguments=ARGS(
            [
                (["account"], {"help": _("account id"), "action": "store", "type": str}),
            ]
        ),
    )
    def info(self):
        account = self.app.pargs.account
        account = self.get_account(account).get("uuid")
        data = {"owner-id": account}
        uri = f"{self.baseuri}/networkservices"
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, "DescribeNetworkResponse.networkSet.0")
        self.app.render(res, details=True, maxsize=100)

    @ex(
        help=_("get network service quotas"),
        description=_(
            "Get network service quotas. "
            "This command retrieves the quotas for network services like bandwidth, "
            "connections etc. for a given account id. "
            "The required account id argument specifies the account for which "
            "the quotas need to be retrieved."
        ),
        example="beehive bu netaas quotas Acc_demo1_nmsflike -e <env>",
        arguments=ARGS(
            [
                (["account"], {"help": _("account id"), "action": "store", "type": str}),
            ]
        ),
    )
    def quotas(self):
        account = self.app.pargs.account
        account = self.get_account(account).get("uuid")
        data = {"owner-id": account}
        uri = f"{self.baseuri}/networkservices/describeaccountattributes"
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
        help=_("get network service availibility zones"),
        description=_(
            "This command is used to get the network service availability zones for "
            "a given account id. "
            "The account id is a required argument that must be provided to retrieve the availability zones."
        ),
        example="beehive bu netaas availability-zones openspace",
        arguments=ARGS(
            [
                (["account"], {"help": _("account id"), "action": "store", "type": str}),
            ]
        ),
    )
    def availability_zones(self):
        account = self.app.pargs.account
        account = self.get_account(account).get("uuid")
        data = {"owner-id": account}
        uri = f"{self.baseuri}/computeservices/describeavailabilityzones"
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, "DescribeAvailabilityZonesResponse.availabilityZoneInfo")
        headers = ["name", "state", "region", "message"]
        fields = ["zoneName", "zoneState", "regionName", "messageSet.0.message"]
        self.app.render(res, headers=headers, fields=fields)


class DeprecatedServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = CURRENT
        stacked_type = "nested"
        label = "deprecated"
        description = _("Deprecated network service management")
        help = _("Deprecated network service management")

    # @ex()
    # def dummy(self):
    #     pass


class VpcNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = CURRENT
        stacked_type = "nested"
        label = "vpcs"
        description = _("virtual private cloud network service management")
        help = _("virtual private cloud network service management")

    @ex(
        help=_("get private cloud networks"),
        description=_(
            "This command is used to get private cloud networks configured in the specified account. "
            "It lists all the VPCs along with their IDs and names. "
            "The account can be specified using the -account flag followed by the account name. "
            "Alternatively, a specific VPC can be fetched by specifying its ID using the -ids flag."
        ),
        example="beehive bu netaas vpcs list -account silp; beehive bu netaas vpcs list -ids <uuid>",
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": _("list of account id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": _("list of private cloud network id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("list of tag comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": _("list page [default=0]"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": _("list page size [default=20]"),
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
        uri = f"{self.baseuri}/computeservices/vpc/describevpcs"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeVpcsResponse")
            for item in res.get("vpcSet"):
                item["cidr"] = [f"{i['cidrBlock']}" for i in item["cidrBlockAssociationSet"]]
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

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="DescribeVpcsResponse.nvl-vpcTotal",
            key_list_name="DescribeVpcsResponse.vpcSet",
            fn_render=render,
        )

    @ex(
        help=_("get vpc"),
        description=_(
            """\
This command retrieves information about a specific vpc
"""
        ),
        example="beehive bu netaas vpc get <uuid>",
        arguments=ARGS(
            [
                (
                    ["vpc"],
                    {"help": _("vpc id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def get(self):
        vpc_id = self.app.pargs.vpc
        data = {"vpc-id.N": [vpc_id]}
        uri = f"{self.baseuri}/computeservices/vpc/describevpcs"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = res.get("DescribeVpcsResponse")
        vpc_set = res.get("vpcSet")
        if len(vpc_set) == 0:
            raise Exception(f"vpc {vpc_id} does not exist")

        vpc = vpc_set[0]
        self.app.render(vpc, details=True, maxsize=200)

    @ex(
        help=_("add virtual private cloud"),
        description=_(
            "This command adds a new virtual private cloud (VPC) to the specified account. "
            "It requires the VPC name, account ID and CIDR block as required arguments. "
            "Optionally a template can also be provided to apply certain configuration to the new VPC."
        ),
        example="beehive bu netaas vpcs add VpcPrivate01 xxx ###.###.###.###/21 -template Vpc.Private",
        arguments=ARGS(
            [
                (["name"], {"help": _("vpc name"), "action": "store", "type": str}),
                (["account"], {"help": _("account id"), "action": "store", "type": str}),
                (
                    ["cidr_block"],
                    {"help": _("vpc cidr block"), "action": "store", "type": str},
                ),
                (
                    ["-template"],
                    {
                        "help": _("vpc template"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tenancy"],
                    {
                        "help": _(
                            "allowed tenancy of instances launched into the VPC. Use default for shared vpc. "
                            "Use dedicated for private vpc. default is dedicated"
                        ),
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
        uri = f"{self.baseuri}/computeservices/vpc/createvpc"
        res = self.cmp_post(uri, data={"vpc": data}, timeout=600)
        res = res.get("CreateVpcResponse").get("vpc").get("vpcId")
        self.wait_for_service(res)
        self.app.render({"msg": f"add vpc {res}"})

    @ex(
        help=_("delete a vpc"),
        description=_(
            "This command deletes a VPC (Virtual Private Cloud) by specifying its ID. "
            "The VPC ID is a required argument for this command to identify which VPC "
            "to delete from the account."
        ),
        example="beehive bu netaas vpcs delete <uuid> -e <env>",
        arguments=ARGS(
            [
                (["vpc"], {"help": _("vpc id"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.vpc

        # check type
        version = "v2.0"
        uri = f"/{version}/nws/serviceinsts/{oid}"
        res = self.cmp_get(uri).get("serviceinst")
        plugintype = res["plugintype"]

        if plugintype != "ComputeVPC":
            print("Instance is not a ComputeVPC")
        else:
            data = {"force": False, "propagate": True}
            uri = f"/v2.0/nws/serviceinsts/{oid}"
            self.cmp_delete(uri, data=data, timeout=180, entity=f"vpc {oid}")
            self.wait_for_service(oid, accepted_state="DELETED")

    @ex(
        help=_("get vpc templates"),
        description=_(
            "This command is used to retrieve VPC templates from Nivola Cloud. "
            "VPC templates define network configurations that can be used to "
            "quickly deploy new VPCs. "
            "This command with no arguments will return all available templates. "
            "A specific template can be retrieved by providing its unique identifier as an argument."
        ),
        example="beehive bu netaas vpcs templates <uuid>",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": _("template id"),
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
        stacked_on = CURRENT
        stacked_type = "nested"
        label = "subnets"
        description = _("vpc subnet service management")
        help = _("vpc subnet service management")

    @ex(
        help=_("get vpc subnet"),
        description=_("This command is used to get the subnet by uuid"),
        example="beehive bu netaas subnets get <uuid>",
        arguments=ARGS(
            [
                (
                    ["subnet_id"],
                    {"help": _("subnet id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def get(self):
        subnet_id = quote(self.app.pargs.subnet_id)
        uri = f"{self.baseuri}/describesubnet/{subnet_id}"
        res = self.cmp_get(uri)
        res = res.get("DescribeSubnetsResponse")
        resp = {
            "instances": res.get("subnetSet"),
        }
        headers = ["id", "name", "state", "account", "availabilityZone", "vpc", "cidr", "vsFreeIPs", "opsFreeIPs"]
        fields = [
            "subnetId",
            "nvl-name",
            "state",
            "nvl-subnetOwnerAlias",
            "availabilityZone",
            "nvl-vpcName",
            "cidrBlock",
            "vsphereAvailableIpAddressCount",
            "openstackAvailableIpAddressCount",
        ]
        self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=45)

    @ex(
        help=_("get vpc subnets"),
        description=_(
            "This command is used to get the subnets under a VPC. "
            "It lists all the subnets available in the given account. "
            "The account must be specified using the -account flag with the account name or ID."
        ),
        example="beehive bu netaas subnets list -account Sipal",
        arguments=ARGS(
            [
                (
                    ["-account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                        "required": True,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": _("list of subnet id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vpcs"],
                    {
                        "help": _("list of vpc id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": _("list page [default=0]"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": _("list page size [default=20]"),
                        "action": "store",
                        "type": int,
                        "default": 20,
                    },
                ),
                (
                    ["-allocation-pools-details"],
                    {
                        "help": _("show the allocation pools details"),
                        "action": "store_true",
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def list(self):
        # Define parameters that should be passed to the API as query strings.
        params = ["ids", "tags", "vpcs", "allocation_pools_details", "page", "size"]
        mappings = {
            "tags": lambda x: x.split(","),
            "ids": lambda x: x.split(","),
            "vpcs": lambda x: x.split(","),
            "allocation_pools_details": str2bool,
        }
        aliases = {
            "ids": "subnet-id.N",
            "vpcs": "vpc-id.N",
            "size": "Nvl-MaxResults",
            "page": "Nvl-NextToken",
        }

        # Get the single account ID from the command-line arguments.
        account_arg = getattr(self.app.pargs, "account", None)

        uri = f"{self.baseuri}/account/{account_arg}/describesubnets"

        # Define the rendering function for the final output.
        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeSubnetsResponse")
            resp = {
                "count": len(res.get("subnetSet")),
                "page": page,
                "total": res.get("nvl-subnetTotal"),
                "sort": {"field": "id", "order": "asc"},
                "instances": res.get("subnetSet"),
            }

            headers = ["id", "name", "state", "availabilityZone", "vpc", "cidr"]
            fields = [
                "subnetId",
                "nvl-name",
                "state",
                "nvl-subnetOwnerAlias",
                "availabilityZone",
                "nvl-vpcName",
                "cidrBlock",
            ]

            allocation_pools_details = getattr(self.app.pargs, "allocation_pools_details", False)
            if allocation_pools_details:
                additional_fields = ["vsphereAvailableIpAddressCount", "openstackAvailableIpAddressCount"]
                additional_headers = ["vsFreeIPs", "opsFreeIPs"]
                headers += additional_headers
                fields += additional_fields
            self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=45)

        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="DescribeSubnetsResponse.nvl-subnetTotal",
            key_list_name="DescribeSubnetsResponse.subnetSet",
            fn_render=render,
        )

    @ex(
        help=_("add virtual private cloud subnet"),
        description=_(
            "This command adds a new subnet to an existing VPC. "
            "It requires the name of the subnet, ID of the VPC it belongs to, "
            "the CIDR block of the subnet, and the availability zone where it will be created."
        ),
        arguments=ARGS(
            [
                (["name"], {"help": _("subnet name"), "action": "store", "type": str}),
                (["vpc"], {"help": _("vpc id"), "action": "store", "type": str}),
                (
                    ["cidr_block"],
                    {"help": _("subnet cidr block"), "action": "store", "type": str},
                ),
                (
                    ["zone"],
                    {"help": _("availability zone"), "action": "store", "type": str},
                ),
                (
                    ["-template"],
                    {
                        "help": _("subnet template"),
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
        uri = f"{self.baseuri}/computeservices/subnet/createsubnet"
        res = self.cmp_post(uri, data={"subnet": data}, timeout=600)
        res = res.get("CreateSubnetResponse").get("subnet").get("subnetId")
        self.wait_for_service(res)
        self.app.render({"msg": f"add subnet {res}"})

    @ex(
        help=_("delete a subnet"),
        description=_(
            "This command deletes a subnet from the Nivola CMP platform. "
            "The subnet id is required as an argument to identify which "
            "subnet needs to be deleted from the account. "
            "Once deleted, all resources associated with that subnet will be removed permanently."
        ),
        arguments=ARGS(
            [
                (["subnet"], {"help": _("subnet id"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.subnet

        # check type
        version = "v2.0"
        uri = f"/{version}/nws/serviceinsts/{oid}"
        res = self.cmp_get(uri).get("serviceinst")
        plugintype = res["plugintype"]
        #name = res["name"]
        if plugintype != "ComputeSubnet":
            print("Instance is not a ComputeSubnet")
        else:
            data = {"force": False, "propagate": True}
            uri = f"/v2.0/nws/serviceinsts/{oid}"
            self.cmp_delete(uri, data=data, timeout=180, entity=f"vpc subnet {oid}")
            self.wait_for_service(oid, accepted_state="DELETED")

    @ex(
        help=_("get subnets templates"),
        description=_(
            "This command is used to retrieve subnet templates from Nivola Cloud. "
            "Subnet templates define network configurations that can be applied "
            "when creating new subnets in a business unit's virtual network. "
            "The command accepts an optional business unit ID and template ID to filter the results."
        ),
        example="beehive bu netaas subnets templates <uuid> -id <uuid>",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": _("template id"),
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
        stacked_on = CURRENT
        stacked_type = "nested"
        label = "securitygroups"
        description = _("security groups service management")
        help = _("security groups service management")

    @ex(
        help=_("get security group templates"),
        description=_(
            "This command is used to retrieve security group templates from Nivola Cloud. "
            "Security group templates define a set of rules that can be applied to "
            "security groups to control ingress and egress network access. "
            "The templates command with no additional arguments will return all available templates. "
            "A template ID can also be provided to get details of a specific template."
        ),
        example="beehive bu netaas securitygroups templates procedo",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": _("template id"),
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
        help=_("create a security group"),
        description=_(
            "This CLI command creates a security group with the specified name in the given VPC. "
            "It requires the security group name, parent VPC and an optional template ID as arguments."
        ),
        example=(
            "beehive bu netaas securitygroups add-rule ingress <uuid> source CIDR:###.###.###.###/32 "
            "-proto tcp -port 80"
        ),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("security group name"), "action": "store", "type": str},
                ),
                (["vpc"], {"help": _("parent vpc"), "action": "store", "type": str}),
                (
                    ["-template"],
                    {"help": _("template id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def add(self):
        data = {"GroupName": self.app.pargs.name, "VpcId": self.app.pargs.vpc}
        sg_type = self.app.pargs.template
        if sg_type is not None:
            data["GroupType"] = sg_type
        uri = f"{self.baseuri}/computeservices/securitygroup/createsecuritygroup"
        res = self.cmp_post(uri, data={"security_group": data}, timeout=600)
        res = dict_get(res, "CreateSecurityGroupResponse.groupId")
        self.wait_for_service(res)
        self.app.render({"msg": f"Add securitygroup {res}"})

    @ex(
        help=_("get security groups"),
        description=_(
            "This command is used to retrieve and display the list of security groups "
            "associated with the current AWS account. "
            "Security groups act as a virtual firewall that controls the traffic for instances. "
            "This allows you to specify the protocols and ports that can reach your instances. "
            "By listing the security groups, you can view the existing rules and configurations "
            "for network access management."
        ),
        example="beehive bu netaas securitygroups list -account procedo",
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": _("list of account id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": _("list of security group id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vpcs"],
                    {
                        "help": _("list of vpc id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("list of tag comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": _("list page [default=0]"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": _("list page size [default=20]"),
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
        uri = f"{self.baseuri}/computeservices/securitygroup/describesecuritygroups"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeSecurityGroupsResponse", {})

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
            self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=45)

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="DescribeSecurityGroupsResponse.nvl-securityGroupTotal",
            key_list_name="DescribeSecurityGroupsResponse.securityGroupInfo",
            fn_render=render,
        )

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
                user_name = group.get("nvl-userName", None)
                group_name = group["groupName"]
                group_id = group["groupId"]
                rule["groups"] = f"{user_name}:{group_name} [{group_id}]"
            else:
                rule["groups"] = ""
            if len(rule.get("ipRanges", None)) > 0:
                cidr = rule["ipRanges"][0]
                rule["ipRanges"] = f"{cidr['cidrIp']}"
            else:
                rule["ipRanges"] = ""
        return rules

    @ex(
        help=_("get security group with rules"),
        description=_(
            "This command retrieves the security group details including its rules. "
            "The security group id is required as an argument to fetch the specific security group details."
        ),
        example="beehive bu netaas securitygroups get <uuid>",
        arguments=ARGS(
            [
                (
                    ["securitygroup"],
                    {"help": _("securitygroup id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def get(self):
        securitygroup = self.app.pargs.securitygroup
        data = {"GroupName.N": [securitygroup]}
        uri = f"{self.baseuri}/computeservices/securitygroup/describesecuritygroups"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeSecurityGroupsResponse.securityGroupInfo", default={})
        if len(res) == 0:
            raise Exception(f"security group {securitygroup} does not exist")
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
        help=_("patch a security group"),
        description=_(
            "This CLI command patches or updates an existing security group in Nivola Cloud. "
            "It requires the security group ID as the only required argument to identify "
            "which security group to update. "
            "This allows modifying attributes of the security group like its name, description or rules."
        ),
        example="beehive bu netaas securitygroups patch",
        arguments=ARGS(
            [
                (
                    ["securitygroup"],
                    {"help": _("securitygroup id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def patch(self):
        securitygroup = self.app.pargs.securitygroup
        data = {"GroupName": securitygroup}
        uri = f"{self.baseuri}/computeservices/securitygroup/patchsecuritygroup"
        res = self.cmp_patch(uri, data={"security_group": data}, timeout=600)
        res = dict_get("PatchSecurityGroupResponse.instancesSet.0.groupId")
        self.app.render({"msg": f"Patch securitygroup {res}"})

    @ex(
        help=_("delete a security group"),
        description=_(
            "This command deletes a security group. "
            "It requires the security group ID as the only required argument. "
            "The -y flag confirms deletion and -e <env> provides "
            "an environment name if multiple environments exist."
        ),
        example="beehive bu netaas securitygroups delete <uuid> -e <env>",
        arguments=ARGS(
            [
                (
                    ["securitygroup"],
                    {"help": _("securitygroup id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.securitygroup
        group_name = {"GroupName": oid}
        data = {"security_group": group_name}
        uri = f"{self.baseuri}/computeservices/securitygroup/deletesecuritygroup"
        entity = f"securitygroup {oid}"
        self.cmp_delete(uri, data=data, timeout=600, entity=entity, output=False)
        state = self.wait_for_service(oid, delta=2)
        if state == "DELETED":
            print(f"{entity} deleted")

    @ex(
        help=_("add a security group rule"),
        description=_(
            "This command allows you to add a new rule to an existing security group. "
            "You need to specify whether it is an egress or ingress rule by providing the 'type' argument. "
            "For egress rules, you also need to specify the destination using '-destination' flag and "
            "for ingress rules, you need to specify the source using '-source' flag. "
            "The 'securitygroup' argument is used to specify the security group id "
            "to which the rule needs to be added."
        ),
        example=(
            "beehive bu netaas securitygroups add-rule ingress <uuid> -source CIDR:###.###.###.###/32 "
            "-proto tcp -port 20443"
        ),
        arguments=ARGS(
            [
                (
                    ["type"],
                    {
                        "help": _(
                            "egress or ingress. For egress rule the destination. For ingress rule specify the source"
                        ),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["securitygroup"],
                    {"help": _("securitygroup id"), "action": "store", "type": str},
                ),
                (
                    ["-proto"],
                    {
                        "help": _("protocol. can be tcp, udp, icmp or -1 for all"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": _(
                            "can be an integer between 0 and 65535 or a range with start and end in the same "
                            "interval. Range format is <start>-<end>. Use -1 for all ports. Set subprotocol if "
                            "proto is icmp (8 for ping)"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dest"],
                    {
                        "help": _(
                            "rule destination. Syntax <type>:<value>. Destination type can be SG, CIDR. For SG "
                            "value must be <sg_id>. For CIDR value should like ###.###.###.###/24."
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-source"],
                    {
                        "help": _(
                            "rule source. Syntax <type>:<value>. Source type can be SG, CIDR. For SG "
                            "value must be <sg_id>. For CIDR value should like ###.###.###.###/24."
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-orchestrators"],
                    {
                        "help": _("orchestrators comma separated"),
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
        orchestrators = self.app.pargs.orchestrators

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
            "IpPermissions.N": [
                {
                    "FromPort": from_port,
                    "ToPort": to_port,
                    "IpProtocol": proto,
                }
            ],
        }

        if orchestrators is not None:
            data.update({"orchestrators": orchestrators})

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
            uri = f"{self.baseuri}/computeservices/securitygroup/authorizesecuritygroupingress"
            key = "AuthorizeSecurityGroupIngressResponse"
        res = self.cmp_post(uri, data={"rule": data}, timeout=600, task_key=key)
        res = res.get(key).get("Return")
        self.app.render(f"create securitygroup rule {res}")

    @ex(
        help=_("delete a security group rule"),
        description=_(
            "Delete a security group rule. This requires specifying the rule type (egress or ingress), "
            "the security group id, and optionally the source/destination, "
            "protocol and port details of the rule to delete."
        ),
        example="beehive bu netaas securitygroups del-rule egress <uuid> -dest CIDR:###.###.###.###/32 -e <env>",
        arguments=ARGS(
            [
                (
                    ["type"],
                    {
                        "help": _(
                            "egress or ingress. For egress rule the destination. For ingress rule specify the source"
                        ),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["securitygroup"],
                    {"help": _("securitygroup id"), "action": "store", "type": str},
                ),
                (
                    ["-proto"],
                    {
                        "help": _("protocol. can be tcp, udp, icmp or -1 for all"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": _(
                            "can be an integer between 0 and 65535 or a range with start and end in the same "
                            "interval. Range format is <start>-<end>. Use -1 for all ports. Set subprotocol if "
                            "proto is icmp (8 for ping)"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dest"],
                    {
                        "help": _(
                            "rule destination. Syntax <type>:<value>. Destination type can be SG, CIDR. For SG "
                            "value must be <sg_id>. For CIDR value should like ###.###.###.###/24."
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-source"],
                    {
                        "help": _(
                            "rule source. Syntax <type>:<value>. Source type can be SG, CIDR. For SG "
                            "value must be <sg_id>. For CIDR value should like ###.###.###.###/24."
                        ),
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
            uri = f"{self.baseuri}/computeservices/securitygroup/revokesecuritygroupegress"
            key = "RevokeSecurityGroupEgressResponse"
        elif rule_type == "ingress":
            uri = f"{self.baseuri}/computeservices/securitygroup/revokesecuritygroupingress"
            key = "RevokeSecurityGroupIngressResponse"
        self.cmp_delete(
            uri,
            data={"rule": data},
            timeout=600,
            entity="securitygroup rule",
            task_key=key,
        )


class GatewayNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = CURRENT
        stacked_type = "nested"
        label = "internet_gateways"
        description = _("gateways service management")
        help = _("gateways service management")

    @ex(
        help=_("get gateway templates"),
        description=_(
            "This command is used to retrieve gateway templates from Nivola Cloud. "
            "Gateway templates define the configuration of internet gateways that "
            "can be attached to VPC networks to provide internet access to instances. "
            "By calling this command without any arguments, it will return a list of "
            "all available gateway templates that can be used when creating new internet gateways."
        ),
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": _("template id"),
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
        help=_("create a gateway"),
        description=_(
            "This command creates a new internet gateway for the specified account using the provided template id. "
            "The account id and template id are required arguments that must be provided "
            "to create the gateway using the specified template configuration."
        ),
        arguments=ARGS(
            [
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (
                    ["-template"],
                    {"help": _("template id"), "action": "store", "type": str},
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
        uri = f"{self.baseuri}/networkservices/gateway/createinternetgateway"
        res = self.cmp_post(uri, data={"gateway": data}, timeout=600)
        uuid = dict_get(res, "CreateInternetGatewayResponse.internetGateway.internetGatewayId")
        self.wait_for_service(uuid)
        self.app.render({"msg": f"add gateway {uuid}"})

    @ex(
        help=_("get gateways"),
        description=_(
            "This command is used to retrieve a list of all internet gateways associated with the current account. "
            "An internet gateway is a horizontally scaled, redundant, and highly available VPC component that allows "
            "communication between instances in your VPC and the Internet. "
            "It therefore provides a path for internet-bound traffic to leave your VPC, "
            "and a path for internet-sourced traffic to enter your VPC."
        ),
        example="beehive bu netaas internet-gateways list -accounts BlahBlah",
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": _("list of account id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": _("list of gateway id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("list of tag comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": _("list page [default=0]"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": _("list page size [default=20]"),
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
        uri = f"{self.baseuri}/networkservices/gateway/describeinternetgateways"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeInternetGatewaysResponse", {})

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
            self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=45)

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="DescribeInternetGatewaysResponse.nvl-internetGatewayTotal",
            key_list_name="DescribeInternetGatewaysResponse.internetGatewaySet",
            fn_render=render,
        )

    @ex(
        help=_("get gateway"),
        description=_(
            "This command retrieves information about an existing internet gateway in the specified business unit. "
            "The gateway ID is required to identify the specific gateway to retrieve details for."
        ),
        example="beehive bu netaas internet-gateways get <uuid>",
        arguments=ARGS(
            [
                (["gateway"], {"help": _("gateway id"), "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        gateway = self.app.pargs.gateway
        data = {"InternetGatewayId.N": [gateway]}
        uri = f"{self.baseuri}/networkservices/gateway/describeinternetgateways"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeInternetGatewaysResponse.internetGatewaySet", default={})

        if len(res) == 0:
            raise Exception(f"gateway {gateway} does not exist")

        res = res[0]

        if self.is_output_text():
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
        else:
            self.app.render(res, details=True)

    @ex(
        help=_("patch a gateway"),
        description=_(
            "This command patches or updates a gateway. "
            "It requires the gateway ID as the only required argument to identify which gateway to update. "
            "The gateway fields can then be modified as needed through additional arguments or "
            "options and committed with this command."
        ),
        arguments=ARGS(
            [
                (["gateway"], {"help": _("gateway id"), "action": "store", "type": str}),
            ]
        ),
    )
    def patch(self):
        gateway = self.app.pargs.gateway
        data = {"GroupName": gateway}
        uri = f"{self.baseuri}/networkservices/gateway/patchgateway"
        res = self.cmp_patch(uri, data={"gateway": data}, timeout=600)
        res = dict_get(res, "PatchSecurityGroupResponse.instancesSet.0.groupId")
        self.app.render({"msg": f"Patch gateway {res}"})

    @ex(
        help=_("delete a gateway"),
        description=_(
            "This command deletes an internet gateway from your account. "
            "You need to provide the ID of the gateway you want to delete "
            "as the only required argument 'gateway'."
        ),
        arguments=ARGS(
            [
                (["gateway"], {"help": _("gateway id"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.gateway
        data = {"InternetGatewayId": oid}
        uri = f"{self.baseuri}/networkservices/gateway/deleteinternetgateway"
        entity = f"Internet Gateway {oid}"
        res = self.cmp_delete(uri, data=data, timeout=600, entity=entity, output=False)
        if res is not None:
            state = self.wait_for_service(oid, accepted_state="DELETED")
            if state == "DELETED":
                print(f"{entity} deleted")

    @ex(
        help=_("attach vpc from gateway"),
        description=_(
            "This command attaches a VPC to an internet gateway. "
            "It requires the gateway ID and VPC ID as arguments to specify which gateway "
            "and VPC to attach. "
            "Attaching a VPC to an internet gateway enables access to the internet for instances in the VPC."
        ),
        arguments=ARGS(
            [
                (["gateway"], {"help": _("gateway id"), "action": "store", "type": str}),
                (["vpc"], {"help": _("vpc id"), "action": "store", "type": str}),
            ]
        ),
    )
    def vpc_attach(self):
        gateway_id = self.app.pargs.gateway
        vpc_id = self.app.pargs.vpc

        data = {"InternetGatewayId": gateway_id, "VpcId": vpc_id}
        uri = f"{self.baseuri}/networkservices/gateway/attachinternetgateway"
        self.cmp_put(uri, data={"gateway": data}, timeout=600, task_key="AttachInternetGatewayResponse")
        self.app.render(f"attach vpc {vpc_id} to gateway {gateway_id}")

    @ex(
        help=_("detach vpc from gateway"),
        description=_(
            "This command detaches a VPC from an internet gateway. "
            "It requires the gateway ID and VPC ID as arguments to identify "
            "which gateway and VPC to detach. "
            "Detaching a VPC from its internet gateway will remove "
            "the public internet access to resources in the VPC like EC2 instances."
        ),
        arguments=ARGS(
            [
                (["gateway"], {"help": _("gateway id"), "action": "store", "type": str}),
                (["vpc"], {"help": _("vpc id"), "action": "store", "type": str}),
            ]
        ),
    )
    def vpc_detach(self):
        gateway_id = self.app.pargs.gateway
        vpc_id = self.app.pargs.vpc

        data = {"InternetGatewayId": gateway_id, "VpcId": vpc_id}
        uri = f"{self.baseuri}/networkservices/gateway/detachinternetgateway"
        self.cmp_put(uri, data={"gateway": data}, timeout=600, task_key="DetachInternetGatewayResponse")
        self.app.render(f"detach vpc {vpc_id} from gateway {gateway_id}")

    @ex(
        help=_("get gateway bastion"),
        description=_(
            "This command retrieves the bastion details of an internet gateway. "
            "The gateway id is required to identify the specific gateway to "
            "retrieve the bastion details from. "
            "The gateway id can be found using the internet-gateways list command."
        ),
        example="beehive bu netaas internet-gateways bastion-get <uuid>",
        arguments=ARGS(
            [
                (["gateway"], {"help": _("gateway id"), "action": "store", "type": str}),
            ]
        ),
    )
    def bastion_get(self):
        gateway = self.app.pargs.gateway
        data = {"InternetGatewayId": gateway}
        uri = f"{self.baseuri}/networkservices/gateway/describinternetgatewayebastion"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(
            res,
            "DescribeInternetGatewayBastionResponse.internetGatewayBastion",
            default={},
        )
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("create a gateway bastion"),
        description=_(
            "This command creates a bastion host for the specified internet gateway. "
            "A bastion host allows secure inbound access to private subnets "
            "from the public internet and helps manage and maintain resources "
            "within private subnets."
        ),
        example="beehive bu netaas internet-gateways bastion-add InternetGateway-458f7a0188",
        arguments=ARGS(
            [
                (["gateway"], {"help": _("gateway id"), "action": "store", "type": str}),
            ]
        ),
    )
    def bastion_add(self):
        gateway = self.app.pargs.gateway
        data = {"InternetGatewayId": gateway}
        uri = f"{self.baseuri}/networkservices/gateway/createinternetgatewaybastion"
        self.cmp_post(
            uri,
            data={"bastion": data},
            timeout=600,
            task_key="CreateInternetGatewayBastionResponse",
        )
        self.app.render({"msg": f"add gateway {gateway} bastion"})

    @ex(
        help=_("delete a gateway bastion"),
        description=_(
            "This command deletes a bastion host associated with an internet gateway. "
            "It requires the gateway id as the only required argument to identify the gateway "
            "and bastion host to delete."
        ),
        example="beehive bu netaas internet-gateways bastion-del InternetGateway-458f7a0188;",
        arguments=ARGS(
            [
                (["gateway"], {"help": _("gateway id"), "action": "store", "type": str}),
            ]
        ),
    )
    def bastion_del(self):
        gateway = self.app.pargs.gateway
        data = {"InternetGatewayId": gateway}
        uri = f"{self.baseuri}/networkservices/gateway/deleteinternetgatewaybastion"
        self.cmp_delete(
            uri,
            data={"bastion": data},
            timeout=600,
            task_key="DeleteInternetGatewayBastionResponse",
            entity=f"gateway {gateway} bastion",
        )


class HealthMonitorNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = DEPRECATED
        stacked_type = "nested"
        label = "health_monitors"
        description = _("health monitor service management")
        help = _("health monitor service management")

    protocols = ["http", "https", "tcp", "imcp", "udp"]
    methods = ["get", "post", "options"]

    @ex(
        help=_("get health monitor templates"),
        description=_(
            "This command is used to retrieve all the available health monitor templates "
            "that can be used to configure health monitors for load balancers. "
            "Health monitors are used to check the health status of backend servers in a load balancer pool. "
            "Templates define common configurations that can be selected while creating new health monitors. "
            "This command lists all the predefined templates without any parameters."
        ),
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": _("template id"),
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
        help=_("list health monitors"),
        description=_(
            "This command is used to list all the configured health monitors in the Nivola CMP Bu Netaas platform. "
            "Health monitors are used to check the health and availability of backend servers, load balancers, "
            "applications etc. "
            "This command will display the name, type, delay, timeout and other configuration details of all "
            "the existing health monitors."
        ),
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": _("list of comma separated account ids"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": _("list of comma separated health monitor ids"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("list of comma separated tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": _("list page [default=0]"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": _("list page size [default=20]"),
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
        uri = f"{self.baseuri}/networkservices/loadbalancer/healthmonitor/describehealthmonitors"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeHealthMonitorsResponse", {})

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
            self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=45)

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="DescribeHealthMonitorsResponse.healthMonitorTotal",
            key_list_name="DescribeHealthMonitorsResponse.healthMonitorSet",
            fn_render=render,
        )

    @ex(
        help=_("get health monitor"),
        description=_(
            "This command is used to retrieve details of a specific health monitor configured in Nivola Cloud. "
            "It requires the unique identifier or name of the health monitor as an argument. "
            "The details returned include configuration parameters like type of health check, interval, timeout etc. "
            "This helps to view the configuration of any existing health monitor to check/troubleshoot its working."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("health monitor uuid or name"), "action": "store", "type": str}),
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
        uri = f"{self.baseuri}/networkservices/loadbalancer/healthmonitor/describehealthmonitors"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeHealthMonitorsResponse.healthMonitorSet", default={})
        if len(res) == 0:
            raise Exception(f"Health monitor {oid} not found")
        res = res[0]
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("create health monitor"),
        description=_(
            "This command is used to create a new health monitor. "
            "It requires the monitor name, parent account id, protocol used to perform "
            "targets health check, health monitor description, interval in seconds "
            "in which a server is to be tested, maximum time in seconds in which "
            "a response from the server must be received, maximum number of times the server "
            "is tested before it is declared down, method to send the health check request "
            "to the server, url to get or post, and expected string as required arguments."
        ),
        arguments=ARGS(
            [
                (["name"], {"help": _("monitor name"), "action": "store", "type": str}),
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (
                    ["protocol"],
                    {
                        "metavar": "protocol",
                        "help": _("protocol used to perform targets health check: {protocols}").format(
                            protocols=protocols
                        ),
                        "choices": protocols,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("health monitor description"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-interval"],
                    {
                        "help": _("interval in seconds in which a server is to be tested"),
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-timeout"],
                    {
                        "help": _("maximum time in seconds in which a response from the server must be received"),
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-max_retries"],
                    {
                        "help": _("maximum number of times the server is tested before it is declared down"),
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-method"],
                    {
                        "metavar": "METHOD",
                        "help": _("method to send the health check request to the server: {methods}").format(
                            methods=methods
                        ),
                        "choices": methods,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-url"],
                    {"help": _("URL to GET or POST"), "action": "store", "type": str},
                ),
                (
                    ["-expected"],
                    {"help": _("expected string"), "action": "store", "type": str},
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

        uri = f"{self.baseuri}/networkservices/loadbalancer/healthmonitor/createhealthmonitor"
        res = self.cmp_post(uri, data={"health_monitor": data}, timeout=600)
        res = dict_get(res, "CreateHealthMonitorResponse.HealthMonitor.healthMonitorId")
        self.app.render({"msg": f"Add health monitor {res}"})

    @ex(
        help=_("update health monitor"),
        description=_(
            "This command updates an existing health monitor on Nivola Cloud. "
            "It requires the health monitor ID and allows updating the interval, "
            "timeout, max retries, method, url and expected values of "
            "the health monitor through the required arguments."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("health monitor id"), "action": "store", "type": str}),
                (
                    ["-interval"],
                    {
                        "help": _("interval in seconds in which a server is to be tested"),
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-timeout"],
                    {
                        "help": _("maximum time in seconds in which a response from the server must be received"),
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-max_retries"],
                    {
                        "help": _("maximum number of times the server is tested before it is declared down"),
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-method"],
                    {
                        "metavar": "METHOD",
                        "help": _("method to send the health check request to the server: {methods}").format(
                            methods=methods
                        ),
                        "choices": methods,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-url"],
                    {"help": _("URL to GET or POST"), "action": "store", "type": str},
                ),
                (
                    ["-expected"],
                    {"help": _("expected string"), "action": "store", "type": str},
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

        uri = f"{self.baseuri}/networkservices/loadbalancer/healthmonitor/modifyhealthmonitor"
        self.cmp_put(uri, data={"health_monitor": data}, timeout=600)
        self.app.render({"msg": f"Update health monitor {oid}"})

    @ex(
        help=_("delete health monitors"),
        description=_(
            "This command deletes health monitors from the configured BEEHIVE instance. "
            "The 'ids' argument requires a comma separated list of the IDs "
            "of the health monitors to delete as input. "
            "Upon successful deletion, no output is returned."
        ),
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": _("comma separated health monitor ids"),
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
            uri = f"{self.baseuri}/networkservices/loadbalancer/healthmonitor/deletehealthmonitor"
            self.cmp_delete(uri, data=data, timeout=600, entity=f"Health monitor {oid}")


class TargetGroupNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = DEPRECATED
        stacked_type = "nested"
        label = "target_groups"
        description = _("target group service management")
        help = _("target group service management")

    balancing_algorithms = ["round-robin", "ip-hash", "leastconn", "uri"]
    target_types = ["vm", "container"]

    @ex(
        help=_("get target group templates"),
        description=_(
            "This command is used to retrieve target group templates from Nivola Cloud. "
            "Target group templates define the configuration for target groups, "
            "which are used to route and load balance traffic in Nivola Cloud. "
            "This command will return the available target group templates "
            "that can be used when creating a new target group."
        ),
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": _("template id"),
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
        help=_("list target groups"),
        description=_(
            "This command is used to list all the target groups configured for the beehive application. "
            "Target groups in AWS refer to groups of targets (instances) that route traffic "
            "in an Application Load Balancer. "
            "This command will retrieve and display the names of all target groups associated "
            "with the specified beehive application."
        ),
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": _("list of comma separated account ids"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": _("list of comma separated target group ids"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("list of comma separated tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": _("list page [default=0]"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": _("list page size [default=20]"),
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
        uri = f"{self.baseuri}/networkservices/loadbalancer/targetgroup/describetargetgroups"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeTargetGroupsResponse", {})

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
            self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=45)

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="DescribeTargetGroupsResponse.targetGroupTotal",
            key_list_name="DescribeTargetGroupsResponse.targetGroupSet",
            fn_render=render,
        )

    @ex(
        help=_("get target group"),
        description=_(
            "This command is used to retrieve information about a specific target group configured in Nivola CMP. "
            "The target group is identified either by its UUID or name. "
            "The 'id' argument is required and should contain the target group identifier to fetch details "
            "for a particular target group."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("target group uuid or name"), "action": "store", "type": str}),
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
        uri = f"{self.baseuri}/networkservices/loadbalancer/targetgroup/describetargetgroups"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeTargetGroupsResponse.targetGroupSet", default={})
        if len(res) == 0:
            raise Exception(f"Target group {oid} not found")
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
        help=_("create empty target group"),
        description=_(
            "This command adds a target group to Nivola CMP. "
            "A target group contains a collection of targets (VMs or containers) that can "
            "receive traffic from Elastic Load Balancers. "
            "It requires specifying the target group name, parent account ID, "
            "load balancing algorithm, target type, and optionally a description "
            "and health monitor ID."
        ),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("target group name"), "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (
                    ["balancing_algorithm"],
                    {
                        "metavar": "balancing_algorithm",
                        "help": _("algorithm used to load balance targets: {balancing_algorithms}").format(
                            balancing_algorithms=balancing_algorithms
                        ),
                        "choices": balancing_algorithms,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["target_type"],
                    {
                        "metavar": "target_type",
                        "help": _("target type: {target_types}").format(target_types=target_types),
                        "choices": target_types,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("target group description"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-health_monitor"],
                    {
                        "help": _("id of the custom monitor to perform health checks on targets"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-transparent"],
                    {
                        "metavar": "TRANSPARENT",
                        "help": _("whether client IP addresses are visible to the backend servers, {[True, False]}"),
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

        uri = f"{self.baseuri}/networkservices/loadbalancer/targetgroup/createtargetgroup"
        res = self.cmp_post(uri, data={"target_group": data}, timeout=600)
        res = dict_get(res, "CreateTargetGroupResponse.TargetGroup.targetGroupId")
        self.app.render({"msg": f"Add target group {res}"})

    @ex(
        help=_("update target group"),
        description=_(
            "This command updates a target group in Nivola CMP. "
            "The required arguments are the target group id to update (-id), "
            "the new target group description (-desc) and "
            "the load balancing algorithm (-balancing_algorithm) "
            "to use among the target group targets."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("target group id"), "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": _("target group description"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-balancing_algorithm"],
                    {
                        "metavar": "BALANCING_ALGORITHM",
                        "help": _("algorithm used to load balance targets: {balancing_algorithms}").format(
                            balancing_algorithms=balancing_algorithms
                        ),
                        "choices": balancing_algorithms,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-transparent"],
                    {
                        "metavar": "TRANSPARENT",
                        "help": _("whether client IP addresses are visible to the backend servers, {[True, False]}"),
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

        uri = f"{self.baseuri}/networkservices/loadbalancer/targetgroup/modifytargetgroup"
        self.cmp_put(uri, data={"target_group": data}, timeout=600)
        self.app.render({"msg": f"Update target group {oid}"})

    @ex(
        help=_("delete target groups"),
        description=_(
            "This command deletes target groups from the Nivola CMP platform. "
            "The 'ids' argument is required and expects a comma separated list "
            "of target group IDs to delete."
        ),
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": _("comma separated target group ids"),
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
            uri = f"{self.baseuri}/networkservices/loadbalancer/targetgroup/deletetargetgroup"
            self.cmp_delete(uri, data=data, timeout=600, entity=f"Target group {oid}")

    @ex(
        help=_("register targets with target group"),
        description=_(
            "This command registers targets with a target group. "
            "It requires the target group id and a comma separated list of target identifiers "
            "and port mappings in the format <target_id>:<lb_port> or <target_id>:<target_port>:<hm_port>."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("target group id"), "action": "store", "type": str}),
                (
                    ["targets"],
                    {
                        "help": _(
                            "comma separated list of couples <target_id>:<lb_port> or triplets "
                            "<target_id>:<target_port>:<hm_port>"
                        ),
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
                raise Exception(f"Bad format: {item}")

        uri = f"{self.baseuri}/networkservices/loadbalancer/targetgroup/registertargets"
        self.cmp_put(uri, data={"target_group": data}, timeout=600)
        for item in data["Targets"]:
            self.app.render({"msg": f"Register target {item.get('Id')} with target group {oid}"})

    @ex(
        help=_("deregister targets from target group"),
        description=_(
            "This command deregisters targets from a target group. "
            "It requires the target group id and a comma separated list of target ids as arguments. "
            "The targets will be removed from load balancing of the target group."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("target group id"), "action": "store", "type": str}),
                (
                    ["targets"],
                    {
                        "help": _("comma separated list of target ids"),
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

        uri = f"{self.baseuri}/networkservices/loadbalancer/targetgroup/deregistertargets"
        self.cmp_put(uri, data={"target_group": data}, timeout=600)
        for item in data["Targets"]:
            self.app.render({"msg": f"Deregister target {item.get('Id')} from target group {oid}"})

    @ex(
        help=_("register health monitor with target group"),
        description=_(
            "This command registers a health monitor with a target group. "
            "It requires the target group id and health monitor id as required arguments "
            "to associate the health check with the target group."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("target group id"), "action": "store", "type": str}),
                (
                    ["monitor"],
                    {"help": _("health monitor id"), "action": "store", "type": str},
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

        uri = f"{self.baseuri}/networkservices/loadbalancer/targetgroup/registerhealthmonitor"
        self.cmp_put(uri, data={"target_group": data}, timeout=600)
        self.app.render({"msg": f"Register health monitor {monitor_id} with target group {oid}"})

    @ex(
        help=_("deregister health monitor from target group"),
        description=_(
            "This command deregisters a health monitor from a target group. "
            "It requires the target group ID as the only argument to "
            "identify which target group's health monitor will be deregistered."
        ),
        arguments=ARGS([(["id"], {"help": _("target group id"), "action": "store", "type": str})]),
    )
    def health_monitor_deregister(self):
        oid = self.app.pargs.id
        data = {"TargetGroupId": oid}
        uri = f"{self.baseuri}/networkservices/loadbalancer/targetgroup/deregisterhealthmonitor"
        self.cmp_put(uri, data={"target_group": data}, timeout=600)
        self.app.render({"msg": f"Deregister health monitor from target group {oid}"})


class ListenerNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = DEPRECATED
        stacked_type = "nested"
        label = "listeners"
        description = _("listener service management")
        help = _("listener service management")

    import builtins

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

    traffic_types = builtins.list(traffic_types_mapping.keys())

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
        help=_("get listener templates"),
        description=_(
            "This command is used to retrieve listener templates configured in Nivola Cloud. "
            "Listener templates define the frontend configuration for load balancers and "
            "application delivery controllers in Nivola Cloud. "
            "The command does not require any arguments as it will return all available listener "
            "templates by default. "
            "These templates can then be selected when creating a new listener on a load balancer "
            "or ADC to simplify configuration of common scenarios like HTTP, HTTPS or TCP load balancing."
        ),
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": _("template id"),
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
        help=_("list listeners"),
        description=_(
            "This command lists all the configured listeners for the Nivola CMP application running on Nivola Cloud. "
            "Listeners allow incoming connections from external clients or services and are configured "
            "during application deployment to expose specific ports. "
            "This command displays the listener name, port and protocol of each active listener without "
            "any other output."
        ),
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": _("list of comma separated account ids"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": _("list of comma separated listener ids"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("list of comma separated tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": _("list page [default=0]"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": _("list page size [default=20]"),
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
        uri = f"{self.baseuri}/networkservices/loadbalancer/listener/describelisteners"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeListenersResponse", {})

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
            self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=45)

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="DescribeListenersResponse.listenerTotal",
            key_list_name="DescribeListenersResponse.listenerSet",
            fn_render=render,
        )

    @ex(
        help=_("get listener"),
        description=_(
            "This command is used to retrieve information about a specific listener configured "
            "on the Nivola CMP platform. "
            "It requires the unique identifier or name of the listener as the only required argument. "
            "The listener details will be displayed upon running this command with a valid listener id or name."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("listener uuid or name"), "action": "store", "type": str}),
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
        uri = f"{self.baseuri}/networkservices/loadbalancer/listener/describelisteners"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeListenersResponse.listenerSet", default={})
        if len(res) == 0:
            raise Exception(f"Listener {oid} not found")
        res = res[0]
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("create listener"),
        description=_(
            "This command creates a new listener on a Nivola CMP load balancer. "
            "It requires specifying the listener name, parent account ID, "
            "traffic type (TCP, HTTP, etc.), and optionally can configure settings "
            "like persistence, certificates, ciphers, headers and redirections."
        ),
        arguments=ARGS(
            [
                (["name"], {"help": _("listener name"), "action": "store", "type": str}),
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (
                    ["traffic_type"],
                    {
                        "metavar": "traffic_type",
                        "help": _("incoming traffic profile; one of: {traffic_types}").format(
                            traffic_types=traffic_types
                        ),
                        "choices": traffic_types,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-desc"],
                    {"help": _("listener description"), "action": "store", "type": str},
                ),
                (
                    ["-persistence"],
                    {
                        "metavar": "PERSISTENCE",
                        "help": _("persistence type: {persistence_methods}").format(
                            persistence_methods=persistence_methods
                        ),
                        "choices": persistence_methods,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-cookie_name"],
                    {"help": _("cookie name"), "action": "store", "type": str},
                ),
                (
                    ["-cookie_mode"],
                    {
                        "metavar": "COOKIE_MODE",
                        "help": _("cookie mode: {cookie_modes}").format(cookie_modes=cookie_modes),
                        "choices": cookie_modes,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-expire"],
                    {"help": _("expire time in seconds"), "action": "store", "type": int},
                ),
                (
                    ["-client_cert_path"],
                    {"help": _("client certificate path"), "action": "store", "type": str},
                ),
                (
                    ["-server_cert_path"],
                    {"help": _("server certificate path"), "action": "store", "type": str},
                ),
                (
                    ["-client_cipher"],
                    {
                        "metavar": "CLIENT_CIPHER",
                        "help": _("cipher suite used by client; one of: ") + f"{cipher_suites}",
                        "choices": cipher_suites,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-server_cipher"],
                    {
                        "metavar": "SERVER_CIPHER",
                        "help": _("cipher suite used by server; one of: ") + f"{cipher_suites}",
                        "choices": cipher_suites,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-insert_x_forwarded_for"],
                    {
                        "metavar": "INSERT_X_FORWARDED_FOR",
                        "help": _("insert X-Forwarded-For HTTP header"),
                        "choices": [True, False],
                        "action": "store",
                        "type": bool,
                    },
                ),
                (
                    ["-redirect_to"],
                    {"help": _("url to redirect client requests"), "action": "store", "type": str},
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

        uri = f"{self.baseuri}/networkservices/loadbalancer/listener/createlistener"
        res = self.cmp_post(uri, data={"listener": data}, timeout=600)
        res = dict_get(res, "CreateListenerResponse.Listener.listenerId")
        self.app.render({"msg": f"Add listener {res}"})

    @ex(
        help=_("update listener"),
        description=_(
            "Update an existing load balancer listener configuration. "
            "The required arguments are the listener id to update and "
            "at least one configuration parameter like the description, "
            "persistence type, cookie settings etc. "
            "This allows modifying listener settings non-disruptively."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("listener id"), "action": "store", "type": str}),
                (
                    ["-desc"],
                    {"help": _("listener description"), "action": "store", "type": str},
                ),
                (
                    ["-persistence"],
                    {
                        "metavar": "PERSISTENCE",
                        "help": _("persistence type: {persistence_methods}").format(
                            persistence_methods=persistence_methods
                        ),
                        "choices": persistence_methods,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-cookie_name"],
                    {
                        "help": _("cookie name"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-cookie_mode"],
                    {
                        "metavar": "COOKIE_MODE",
                        "help": _("cookie mode: {cookie_modes}").format(cookie_modes=cookie_modes),
                        "choices": cookie_modes,
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-expire"],
                    {"help": _("expire time in seconds"), "action": "store", "type": int},
                ),
                (
                    ["-insert_x_forwarded_for"],
                    {
                        "metavar": "INSERT_X_FORWARDED_FOR",
                        "help": _("insert X-Forwarded-For HTTP header, ['True', 'False']"),
                        "choices": ["True", "False", "true", "false"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-redirect_to"],
                    {
                        "help": _("url to redirect client requests"),
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

        uri = f"{self.baseuri}/networkservices/loadbalancer/listener/modifylistener"
        self.cmp_put(uri, data={"listener": data}, timeout=600)
        self.app.render({"msg": f"Update listener {oid}"})

    @ex(
        help=_("delete listeners"),
        description=_(
            "This command deletes one or more listeners from a beehive cluster. "
            "The ids argument is required and expects a comma separated list of "
            "listener ids to delete from the cluster configured with the beehive CLI. "
            "Once deleted, the listeners will no longer accept or proxy requests."
        ),
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": _("comma separated listener ids"),
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
            uri = f"{self.baseuri}/networkservices/loadbalancer/listener/deletelistener"
            self.cmp_delete(uri, data=data, timeout=600, entity=f"Listener {oid}")

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
        raise Exception(f"Malformed listener from hypervisor: {kvargs}")


class LoadBalancerNetServiceController(BusinessControllerChild, AdminChildController):
    class Meta:
        stacked_on = DEPRECATED
        stacked_type = "nested"
        label = "load_balancers"
        description = _("load balancer service management")
        help = _("load balancer service management")

    protocols = ["http", "https"]
    deployment_envs = ["prod", "preprod", "stage", "test"]

    @ex(
        help=_("get load balancer templates"),
        description=_(
            "This command is used to retrieve all the available load balancer templates from Nivola Cloud. "
            "Load balancer templates define the configuration for load balancers that can be created. "
            "This command lists the available options without creating any resources."
        ),
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": _("template id"),
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
        help=_("list load balancers"),
        description=_(
            "This command lists all the load balancers in the accounts specified or "
            "in the default account if no account is specified. "
            "Load balancers are networking components that distribute incoming application traffic across "
            "multiple backend servers."
        ),
        example="beehive bu netaas load-balancers list -accounts dma",
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": _("list of comma separated account ids"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": _("list of comma separated load balancer ids"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("list of comma separated tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": _("list page [default=0]"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": _("list page size [default=20]"),
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
        uri = f"{self.baseuri}/networkservices/loadbalancer/describeloadbalancers"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeLoadBalancersResponse", {})

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
            self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=45)

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="DescribeLoadBalancersResponse.loadBalancerTotal",
            key_list_name="DescribeLoadBalancersResponse.loadBalancerSet",
            fn_render=render,
        )

    @ex(
        help=_("get load balancer"),
        description=_(
            "This command is used to retrieve information about a specific load balancer configured in Nivola Cloud. "
            "It requires the unique identifier (UUID) or name of the load balancer as the only required argument. "
            "The command will return details like the load balancer type, port, protocol, "
            "backend servers and health check configuration."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("load balancer uuid or name"), "action": "store", "type": str}),
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
        uri = f"{self.baseuri}/networkservices/loadbalancer/describeloadbalancers"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeLoadBalancersResponse.loadBalancerSet", default={})
        if len(res) == 0:
            raise Exception(f"Load balancer {oid} not found")
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
        help=_("create load balancer"),
        description=_("create load balancer"),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("load balancer name"), "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (
                    ["template"],
                    {
                        "help": _("load balancer service definition"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["protocol"],
                    {
                        "metavar": "protocol",
                        "help": _("protocol for connections to load balancer: {protocols}").format(protocols=protocols),
                        "action": "store",
                        "type": str,
                        "choices": protocols,
                    },
                ),
                (["port"], {"help": _("port number"), "action": "store", "type": int}),
                (["listener"], {"help": _("listener id"), "action": "store", "type": str}),
                (
                    ["target_group"],
                    {"help": _("target group id"), "action": "store", "type": str},
                ),
                (
                    ["-desc"],
                    {
                        "help": _("load balancer description"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-static_ip"],
                    {
                        "help": _("load balancer frontend ip address"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-max_conn"],
                    {
                        "help": _("maximum concurrent connections"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-max_conn_rate"],
                    {
                        "help": _("maximum connections per second"),
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-deploy_env"],
                    {
                        "metavar": "DEPLOY_ENV",
                        "help": _("project deployment environment: {deployment_envs}").format(
                            deployment_envs=deployment_envs
                        ),
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

        uri = f"{self.baseuri}/networkservices/loadbalancer/createloadbalancer"
        res = self.cmp_post(uri, data={"load_balancer": data}, timeout=600)
        uuid = dict_get(res, "CreateLoadBalancerResponse.LoadBalancer.loadBalancerId")
        self.wait_for_service(uuid)
        self.app.render({"msg": f"Add load balancer {uuid}"})

    @ex(
        help=_("update load balancer"),
        description=_(
            "This CLI command updates a load balancer on Nivola Cloud. "
            "It requires the load balancer ID and allows updating the description, "
            "protocol, port number, maximum concurrent connections, and maximum connections per second."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("load balancer id"), "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": _("load balancer description"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-protocol"],
                    {
                        "metavar": "PROTOCOL",
                        "help": _("protocol for connections to load balancer: {protocols}").format(protocols=protocols),
                        "action": "store",
                        "type": str,
                        "choices": protocols,
                    },
                ),
                (["-port"], {"help": _("port number"), "action": "store", "type": int}),
                (
                    ["-max_conn"],
                    {
                        "help": _("maximum concurrent connections"),
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-max_conn_rate"],
                    {
                        "help": _("maximum connections per second"),
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

        uri = f"{self.baseuri}/networkservices/loadbalancer/modifyloadbalancer"
        res = self.cmp_put(uri, data={"load_balancer": data}, timeout=600)
        uuid = dict_get(res, "ModifyLoadBalancerResponse.LoadBalancer.loadBalancerId")
        self.wait_for_service(uuid)
        self.app.render({"msg": f"Update load balancer {oid}"})

    @ex(
        help=_("delete load balancer"),
        description=_(
            "This command deletes a load balancer from Nivola Cloud. "
            "It requires the ID of the load balancer to delete as a required argument. "
            "The load balancer ID uniquely identifies the load balancer instance."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("load balancer id"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        uuid = self.app.pargs.id
        data = {"loadBalancerId": uuid}
        uri = f"{self.baseuri}/networkservices/loadbalancer/deleteloadbalancer"
        entity = f"Load balancer {uuid}"
        res = self.cmp_delete(uri, data=data, timeout=600, entity=entity, output=False)
        if res is not None:
            state = self.wait_for_service(uuid, accepted_state="DELETED")
            if state == "DELETED":
                print(f"{entity} deleted")

    @ex(
        help=_("enable load balancer"),
        description=_(
            "This command enables a load balancer that was previously created. "
            "It requires the ID of the load balancer to start as a required argument. "
            "The load balancer ID uniquely identifies the load balancer instance. "
            "Enabling the load balancer allows it to start distributing traffic to the backend servers."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("load balancer id"), "action": "store", "type": str}),
            ]
        ),
    )
    def start(self):
        uuid = self.app.pargs.id
        data = {"loadBalancerId": uuid}
        uri = f"{self.baseuri}/networkservices/loadbalancer/enableloadbalancer"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": f"Load balancer {uuid} enabled"})

    @ex(
        help=_("disable load balancer"),
        description=_(
            "This command stops or disables the specified load balancer. "
            "It takes the load balancer ID as the only required argument. "
            "Disabling a load balancer will stop forwarding traffic to the backend servers and "
            "the health check will stop. "
            "The load balancer can be re-enabled using the 'beehive bu netaas load-balancers start' command."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("load balancer id"), "action": "store", "type": str}),
            ]
        ),
    )
    def stop(self):
        uuid = self.app.pargs.id
        data = {"loadBalancerId": uuid}
        uri = f"{self.baseuri}/networkservices/loadbalancer/disableloadbalancer"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": f"Load balancer {uuid} disabled"})

    @ex(
        help=_("delete load balancer generic services"),
        description=_(
            "This command deletes predefined load balancer services for a given account id. "
            "The account id argument is required to identify the account "
            "whose predefined services need to be deleted from the load balancer. "
            "Deleting predefined services removes the preconfigured load balancing rules "
            "for applications like HTTP, HTTPS etc for the specified account."
        ),
        arguments=ARGS(
            [
                (
                    ["account"],
                    {"help": _("account id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete_predefined_service(self):
        account = self.app.pargs.account

        plugintypes = ["NetworkHealthMonitor", "NetworkListener"]
        for plugintype in plugintypes:
            version = "v2.0"
            uri = f"/{version}/nws/serviceinsts"

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
                ser_plugintype = serviceinst["plugintype"]
                if ser_plugintype == plugintype:
                    print(f"deleting {name} ...")

                    value = uuid
                    force = False
                    propagate = False
                    data = {"force": force, "propagate": propagate}
                    uri = f"/v2.0/nws/serviceinsts/{value}"
                    self.cmp_delete(uri, data=data, timeout=180, entity=f"service instance {value}")


class SshGatewayNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = CURRENT
        stacked_type = "nested"
        label = "sshgw"
        description = _("ssh gateway service management")
        help = _("ssh gateway service management")

    @ex(
        help=_("get ssh gateway configurations"),
        description=_(
            "This command is used to retrieve the list of configured SSH gateway configurations "
            "on the Nivola CMP platform. "
            "SSH gateways allow clients to connect to internal resources through a secure tunnel "
            "without exposing those resources directly to the internet. "
            "The conf-list subcommand displays all existing SSH gateway configurations by name "
            "so they can be easily identified and referred to by other commands."
        ),
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": _("list of account id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": _("list of ssh gateway configurations id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-names"],
                    {
                        "help": _("list of ssh gateway configurations names comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("list of tag comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": _("list page [default=0]"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": _("list page size [default=20]"),
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
        uri = f"{self.baseuri}/networkservices/ssh_gateway/configuration/list"
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
            maxsize=45,
        )

    @ex(
        help=_("get ssh gateway configuration"),
        description=_(
            "This command is used to retrieve the configuration of a specific SSH gateway from "
            "the Nivola CMP platform. "
            "The 'id' argument is required and should contain the unique identifier of "
            "the SSH gateway configuration to fetch. This command will return the full "
            "configuration details of the specified SSH gateway as a JSON object."
        ),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("ssh gateway configuration id"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def conf_get(self):
        data = {"size": 2}
        l_id = self.app.pargs.id
        if self.is_uuid(id):
            data["sshgwconf-id.N"] = [l_id]
        elif self.is_name(id):
            data["sshgwconf-name.N"] = [l_id]

        uri = f"{self.baseuri}/networkservices/ssh_gateway/configuration/list"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeSshGatewaysConfResponse.sshGatewaySet", default={})

        if len(res) == 0:
            raise Exception(f"ssh gateway configuration {id} does not exist")
        if len(res) > 1:
            raise Exception("found more than one ssh gateway configuration. Specify id or uuid instead of name.")
        res = res[0]
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("add ssh gateway configuration"),
        description=_(
            "This CLI command is used to add SSH gateway configuration to a beehive device. "
            "The conf-add subcommand of the beehive bu netaas sshgw command allows "
            "administrators to configure SSH tunnels and gateways on Cisco "
            "SD-WAN devices for site-to-site or client VPN access. "
            "No arguments are required for this command as the configuration values can be "
            "passed interactively. "
            "The command connects to the designated device and prompts for inputs "
            "to define the SSH gateway settings that should be added."
        ),
        arguments=ARGS(
            [
                (
                    ["-name"],
                    {
                        "help": _("configuration name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["gw_type"],
                    {
                        "metavar": "gw_type",
                        "help": _("ssh gateway type (gw_dbaas,gw_cpaas)"),
                        "choices": ["gw_dbaas", "gw_cpaas"],
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("configuration description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["dest_uuid"],
                    {
                        "help": _("destination service instance uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-allowed_ports"],
                    {
                        "help": _("comma separated list of ranges (start-end) or single ports. e.g. 8000-9000,22"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-forbidden_ports"],
                    {
                        "help": _("comma separated list of ranges (start-end) or single ports. e.g. 8000-9000,22"),
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
            self.app.pargs.allowed_ports = "DB_PORT"  # optional placeholder value
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
        help=_("delete a ssh gateway configuration"),
        description=_(
            "This command deletes a specific SSH gateway configuration from the beehive database by its unique ID. "
            "The ID of the configuration to delete must be provided as an argument to this command. "
            "Upon successful deletion, a confirmation message will be displayed."
        ),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("ssh gateway conf id"), "action": "store", "type": str},
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
        help=_("activate ssh gw configuration"),
        description=_(
            "This command activates an existing SSH gateway configuration on Nivola Cloud. "
            "It requires the SSH gateway configuration ID and destination port number "
            "as required arguments to identify and activate the specific configuration."
        ),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("ssh gateway conf id"), "action": "store", "type": str},
                ),
                (["port"], {"help": _("destination port"), "action": "store", "type": str}),
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


CFGEXAMPLE = """
configuration:
  - alias: applicazione01
    backends:
      - ip: 10.0.0.0
        name: primo
        port: 8080
        protocol: http
    certificate: |
      -----BEGIN CERTIFICATE-----
      ................................................................
      ................................................................
      ................................................................
      ................................................................
      ................................................................
      -----END CERTIFICATE-----
    fqdn: pippo.pluto.csi.it
    redirectHttp": false
    stickySessions: true
    whiteList:
      - 10.0.0.0/8
      - 158.0.0.0/8
      - 0.0.0.0/0
"""


class LbaasController(BusinessControllerChild, AdminChildController):
    class Meta:
        stacked_on = CURRENT
        stacked_type = "nested"
        label = "lbaas"
        description = _("load balancer service management")
        help = _("load balancer service management")

    protocols = ["http", "https"]
    deployment_envs = ["prod", "preprod", "stage", "test"]

    @ex(
        help=_("get load balancer flavours"),
        description=_("This command is used to retrieve the load balancer flavours  available for accounts."),
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": _("template id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def flavours_definitions(self):
        self.get_service_definitions("NetworkLbaasInstance")

    @ex(
        help=_("get load balancer templates"),
        description=_(
            "This command is used to retrieve the available load balancer templates for the account. "
            "Load balancer templates define the configuration for load balancers that can be created. "
            "This command lists the available options without creating any resources."
        ),
        arguments=ARGS([]),
    )
    def templates(self):
        # self.get_service_definitions("VirtualServiceSync")
        # TODO
        uri = f"{self.baseuri}/networkservices/lbaas/templates"
        res: dict = self.cmp_get(uri)
        lb: dict = res.get("templates")
        if self.is_output_text():
            headers = [
                "name",
                "description",
            ]
            fields = [
                "name",
                "description",
            ]
            self.app.render(lb, headers=headers, fields=fields, maxsize=80)
        else:
            self.app.render(res, details=True, maxsize=100)

    @ex(
        help=_("get load balancer templates"),
        description=_(
            "This command is used to retrieve the available load balancer templates for the account. "
            "Load balancer templates define the configuration for load balancers that can be created. "
            "This command lists the available options without creating any resources."
        ),
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def account_templates(self):
        # self.get_service_definitions("VirtualServiceSync")
        # TODO
        account = self.app.pargs.account

        uri = f"{self.baseuri}/account/{account}/network/lbaas_templates"
        res: dict = self.cmp_get(uri)
        lb: dict = res.get("templates")
        if self.is_output_text():
            headers = [
                "name",
                "description",
            ]
            fields = [
                "name",
                "description",
            ]
            self.app.render(lb, headers=headers, fields=fields, maxsize=80)
        else:
            self.app.render(res, details=True, maxsize=100)

    @ex(
        help=_("get load balancer templates"),
        description=_(
            "This command is used to retrieve the available load balancer templates for the account. "
            "Load balancer templates define the configuration for load balancers that can be created. "
            "This command lists the available options without creating any resources."
        ),
        arguments=ARGS([]),
    )
    def flavours(self):
        uri = f"{self.baseuri}/networkservices/lbaas/flavours"
        res: dict = self.cmp_get(uri)
        lb: dict = res.get("flavours")
        if self.is_output_text():
            headers = [
                "name",
                "description",
            ]
            fields = [
                "name",
                "description",
            ]
            self.app.render(lb, headers=headers, fields=fields, maxsize=80)
        else:
            self.app.render(res, details=True, maxsize=100)

    @ex(
        help=_("get load balancer templates"),
        description=_(
            "This command is used to retrieve the available load balancer templates for the account. "
            "Load balancer templates define the configuration for load balancers that can be created. "
            "This command lists the available options without creating any resources."
        ),
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def account_flavours(self):
        # self.get_service_definitions("VirtualServiceSync")
        # TODO
        # GET {{endpoint}}/v1.0/nws/networkservices/lbaas/templates
        account = self.app.pargs.account

        # GET {{endpoint}}/v1.0/nws/account/{{account}}/lbaas_templates
        uri = f"{self.baseuri}/account/{account}/network/lbaas_flavours"
        # uri = f"{self.baseuri}/networkservices/lbaas/templates"
        res: dict = self.cmp_get(uri)
        lb: dict = res.get("flavours")
        if self.is_output_text():
            headers = [
                "name",
                "description",
            ]
            fields = [
                "name",
                "description",
            ]
            self.app.render(lb, headers=headers, fields=fields, maxsize=80)
        else:
            self.app.render(res, details=True, maxsize=100)

    @ex(
        help=_("list load balancers"),
        description=_(
            "This command lists all the load balancers in the accounts specified or "
            "in the default account if no account is specified. "
            "Load balancers are networking components that distribute "
            "incoming application traffic across multiple backend servers."
        ),
        example="beehive bu netaas load-balancers list -accounts dmabla",
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": _("list of comma separated account ids"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": _("list of comma separated load balancer ids"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("list of comma separated tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": _("list page [default=0]"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": _("list page size [default=20]"),
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
        uri = f"{self.baseuri}/networkservices/lbaas"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            # res = res.get("Lbaas", {})

            resp = {
                "count": res.get("Count"),
                "page": page,
                "total": res.get("Total"),
                "sort": {"field": "id", "order": "asc"},
                "instances": res.get("Lbaas"),
            }

            headers = [
                "Lb uuid",
                "Lb name",
                "Account uuid",
                "Account name",
                "Lb state",
                "Lb template",
                "Address",
                "AZ",
                "resource uuid",
            ]
            fields = [
                "loadBalancerId",
                "name",
                "ownerId",
                "nvl-ownerAlias",
                "state",
                "template",
                "address",
                "availability_zone",
                "nvl-resourceId",
            ]
            self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=45)

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="Total",
            key_list_name="Lbaas",
            fn_render=render,
        )

    @ex(
        help=_("get load balancer"),
        description=_(
            "This command is used to retrieve information about a specific load balancer configured in Nivola Cloud. "
            "It requires the unique identifier (UUID) or name of the load balancer as the only required argument. "
            "The command will return details like the load balancer type, port, protocol, backend servers and "
            "health check configuration."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("load balancer uuid or name"), "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        # TODO
        oid = self.app.pargs.id
        if not is_uuid(oid) and not is_name(oid):
            raise Exception("Provide a valid uuid or name")
        uri = f"{self.baseuri}/networkservices/lbaas/{oid}"
        res: dict = self.cmp_get(uri)
        lb: dict = res.get("Lbaas")
        if self.is_output_text():
            headers = [
                "Lb uuid",
                "Lb name",
                "Account uuid",
                "Account name",
                "Lb state",
                "Lb template",
                "resource uuid",
            ]
            fields = [
                "loadBalancerId",
                "name",
                "ownerId",
                "nvl-ownerAlias",
                "state",
                "template",
                "nvl-resourceId",
            ]
            self.app.render(lb, headers=headers, fields=fields, maxsize=80)
        else:
            self.app.render(res, details=True, maxsize=100)

    @ex(
        help=_("test load balancer configuration"),
        description=_("get the inner configuration generated from user configutration"),
        arguments=ARGS(
            [
                (["id"], {"help": _("load balancer uuid or name"), "action": "store", "type": str}),
            ]
        ),
    )
    def test(self):
        # TODO
        oid = self.app.pargs.id
        if is_uuid(oid):
            pass
        elif is_name(oid):
            pass
        else:
            raise Exception("Provide a valid uuid or name")
        uri = f"{self.baseuri}/networkservices/lbaas/{oid}/test"
        res: dict = self.cmp_get(uri)
        lb: dict = res.get("Lbaas")
        if self.is_output_text():
            headers = [
                "Lb uuid",
                "Lb name",
                "Account uuid",
                "Account name",
                "Lb state",
                "Lb template",
                "resource uuid",
            ]
            fields = [
                "loadBalancerId",
                "name",
                "ownerId",
                "nvl-ownerAlias",
                "state",
                "template",
                "nvl-resourceId",
            ]
            self.app.render(lb, headers=headers, fields=fields, maxsize=80)
        else:
            self.app.render(res, details=True, maxsize=100)

    @ex(
        help=_("create load balancer"),
        description=_("create load balancer ") + CFGEXAMPLE,
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("load balancer name"), "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (
                    ["flavour"],
                    {
                        "help": _("load balancer  flavour service definition"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["template"],
                    {
                        "help": _("load balancer service definition"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["configuration"],
                    {
                        "help": _("path to yaml containg load balacer configurations "),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("load balancer description"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-subnet"],
                    {"help": _("lbaas instance subnet id"), "action": "store", "type": str},
                ),
                (
                    ["-sg"],
                    {
                        "help": _("lbaas instance security group id"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get("uuid")
        if self.app.pargs.sg is not None:
            sg = self.get_service_instance(self.app.pargs.sg, account_id=account)
        else:
            sg = None

        data = {
            "account_id": account,
            "flavour": self.app.pargs.flavour,
            "instance_identifier": self.app.pargs.name,
            "template": self.app.pargs.template,
        }
        if data.get("flavour") is None:
            raise Exception("flavour is mandatory")
        if data.get("instance_identifier") is None:
            raise Exception("name is mandatory")
        if data.get("flavour") is None:
            raise Exception("flavour is mandatory")
        params = [
            {
                "key": "security_group_id",
                "value": sg,
            },
        ]
        if self.app.pargs.subnet is not None:
            params.append(
                {"key": "subnet", "value": self.get_service_instance(self.app.pargs.subnet, account_id=account)}
            )

        for param in params:
            if param.get("value") is not None:
                data[param.get("key")] = param.get("value")
        if os.path.exists(self.app.pargs.configuration):
            with open(self.app.pargs.configuration, "r", encoding="utf-8") as cfgstream:
                configuration: dict = yaml_load(cfgstream)
                data["lbaasconfig"] = configuration.get("configuration", [])
        uri = "/v1.0/nws/networkservices/lbaas"
        res = self.cmp_post(uri, data={"Lbaas": data}, timeout=600)
        uuid = dict_get(res, "lbaasIdentifier")
        self.wait_for_service(uuid)
        self.app.render({"msg": f"Add load balancer {uuid}"})

    @ex(
        help=_("update load balancer"),
        description=_("This CLI command updates a lnìbaas balancer on Nivola Cloud. A configiration has this form:")
        + CFGEXAMPLE,
        arguments=ARGS(
            [
                (["id"], {"help": _("load balancer id"), "action": "store", "type": str}),
                (
                    ["-cfg"],
                    {
                        "help": _("yaml file path containing new configuration"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-passwd"],
                    {
                        "help": _("new password for staistics"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.id
        passwd = self.app.pargs.passwd
        cfg = self.app.pargs.cfg

        data: UpdateLbaasDict = {}
        if passwd is not None:
            data["user_password"] = passwd
        if cfg is not None:
            if os.path.exists(cfg):
                with open(cfg, "r", encoding="utf-8") as cfgstream:
                    configuration: dict = yaml_load(cfgstream)
                    data["lbaasconfig"] = configuration.get("configuration", [])

        uri = f"{self.baseuri}/networkservices/lbaas/{oid}"
        res = self.cmp_put(uri, data={"Lbaas": data}, timeout=600)
        uuid = res.get("lbaasIdentifier")
        self.wait_for_service(uuid)
        self.app.render({"msg": f"Update load balancer {oid}"})

    @ex(
        help=_("Patch load balancer"),
        description=_("This CLI command patch a lbaas forcing it to update some attributes from provided resources."),
        arguments=ARGS( [ (["id"], {"help": _("load balancer id"), "action": "store", "type": str}), ]
        ),
    )
    def patch(self):
        oid = self.app.pargs.id

        uri = f"{self.baseuri}/networkservices/lbaas/{oid}"
        res = self.cmp_patch(uri, timeout=600)
        msg = res.get("msg")
        self.app.render({"msg": f"patch {oid}: {msg}"})

    @ex(
        help=_("delete load balancer"),
        description=_(
            "This command deletes a load balancer from Nivola Cloud. "
            "It requires the ID of the load balancer to delete as a required argument. "
            "The load balancer ID uniquely identifies the load balancer instance."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("load balancer id"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        uuid = self.app.pargs.id

        uri = f"/v1.0/nws/networkservices/lbaas/{uuid}"
        entity = f"Load balancer {uuid}"
        res = self.cmp_delete(uri, timeout=600, entity=entity, output=False)
        if res is not None:
            state = self.wait_for_service(uuid, accepted_state="DELETED")
            if state == "DELETED":
                print(f"{entity} deleted")

    @ex(
        help=_("create or modify lbaas"),
        description=_(
            "This interactive command create and modify lbaas configuration. "
            "Once you reach the desired configuration, the command let you save  it, "
            "or applay to an axisting lbaas or create a new lbaas for it"
        ),
        arguments=ARGS(
            [
                (["-a","--account"], {"help": _("account id"), "action": "store", "type": str}),
            ]
        ),
    )

    def wizard(self):
        account :str = self.app.pargs.account
        account_uuid: str = None
        if account is not None:
            acc_info : dict = self.get_account(account)
            if acc_info is not None:
                account_uuid = acc_info.get("uuid")
                account = acc_info.get("name")
        # account: str = None
        lbaas: str = None
        lbaas_uuid: str = None
        lbaasconfig: List[LbConfigurationDict] = []
        working: bool = True
        aprompt = PromptTool(controller=self, account=account, account_uuid=account_uuid)
        def checkport():
            nonlocal lbaasconfig
            for config in lbaasconfig:
                if config.get("protocol") == "http":
                    config["port"]=80
                elif config.get("protocol") == "https":
                    config["port"]=443

        def update():
            nonlocal lbaasconfig
            data: UpdateLbaasDict = {}
            data["lbaasconfig"] = lbaasconfig
            __, lbaas_uuid = aprompt.get_lbaas(_("Destination lbaas"))

            uri = f"{self.baseuri}/networkservices/lbaas/{lbaas_uuid}"
            res = self.cmp_put(uri, data={"Lbaas": data}, timeout=600)
            uuid = res.get("lbaasIdentifier")
            self.wait_for_service(uuid)

        def create():
            nonlocal lbaasconfig
            lbaas_name = aprompt.get_name(_("Lbaas name"))
            __, account_uuid = aprompt.get_account()

            flavour = aprompt.get_lbaas_flavours(_("Lbaas falvour"))
            template = aprompt.get_lbaas_templates(_("Lbaas template"))

            data = {
                "account_id": account_uuid,
                "flavour": flavour,
                "instance_identifier": lbaas_name,
                "template": template,
            }

            sg_name = aprompt.get_security_group(_("Lbaas SG"))
            sg = self.get_service_instance(sg_name, account_id=account_uuid)

            params = [
                {
                    "key": "security_group_id",
                    "value": sg,
                },
            ]
            todo = choice(
                message=_("overide templat subnet?"),
                options=[
                    (1, _("Yes")),
                    (2, _("No")),
                ],
                default=1,
                show_frame=~is_done,
            )
            if todo == 1:
                subnet = aprompt.get_subnet("")
                params.append({"key": "subnet", "value": self.get_service_instance(subnet, account_id=account_uuid)})

            for param in params:
                if param.get("value") is not None:
                    data[param.get("key")] = param.get("value")

            data["lbaasconfig"] = lbaasconfig

            uri = "/v1.0/nws/networkservices/lbaas"
            res = self.cmp_post(uri, data={"Lbaas": data}, timeout=600)
            uuid = dict_get(res, "lbaasIdentifier")
            self.wait_for_service(uuid)

        def backend_ip_by_vm() -> str:
            nonlocal aprompt
            _, _, detail = aprompt.get_vm("back-end")
            return detail.get("privateIpAddress")

        def load_lbaas():
            nonlocal aprompt, lbaas, lbaas_uuid, lbaasconfig, working

            lbaas, lbaas_uuid = aprompt.get_lbaas(_("lbaas"))
            if lbaas_uuid is not None:
                uri = f"{self.baseuri}/networkservices/lbaas/{lbaas_uuid}"
                lbaasconfig = self.cmp_get(uri).get("Lbaas", {}).get("lbaas_config", [])
                working = False

        def load_file():
            nonlocal aprompt, lbaas, lbaas_uuid, lbaasconfig, working
            fname = aprompt.get_filename(prompt_prefix=_("File to load "), patterns=["*.yml", "*.yaml", "*.json"])
            if fname.endswith(".yml") or fname.endswith(".yaml"):
                with open(fname, "r", encoding="utf-8") as s:
                    lbaasconfig = yaml_load(s).get("configuration", [])
                working = False
            if fname.endswith(".json"):
                with open(fname, "r", encoding="utf-8") as s:
                    lbaasconfig = json_load(s).get("configuration", [])
                working = False

        def show_sections(cfg: List[LbConfigurationDict]):
            headers = [
                ("alias"),
                ("fqdn"),
                # ("port"),
                ("protocol"),
                ("stickySessions"),
                ("redirectHttp"),
                # ("backends"),
                # ("whiteList"),
                # ("certificate"),
            ]
            fields = [
                "alias",
                "fqdn",
                # "port",
                "protocol",
                "stickySessions",
                "redirectHttp",
                # "backends",
                # "whiteList",
                # "certificate",
            ]
            self.app.render({"lbaas": cfg}, key="lbaas", headers=headers, fields=fields, maxsize=45)

        def edit_backend(backend_data: LbBackendDict, cfg: LbConfigurationDict, todelete=False):
            nonlocal aprompt, self
            while True:
                self.app.render(backend_data, details=True, maxsize=45)
                todo = choice(
                    message=_("BackEnd Edit: Please select an option:"),
                    options=[
                        (1, _("modify ip")),
                        (2, _("set ip by vm")),
                        (3, _("set port")),
                        (4, _("set protocol")),
                        (5, _("back to section")),
                    ],
                    default=1,
                    show_frame=~is_done,
                )
                if todo == 1:
                    backend_data["ip"] = aprompt.get_ipv4(default=backend_data["ip"])
                elif todo == 2:
                    backend_data["ip"] = backend_ip_by_vm()
                elif todo == 3:
                    backend_data["port"] = aprompt.get_number("port ")
                elif todo == 4:
                    backend_data["protocol"] = aprompt.get_word(
                        ["http", "https"],
                        prompt_prefix=_("choose protocol"),
                        default=backend_data.get("protocol", "https"),
                    )
                elif todo == 5:
                    return backend_data

        def edit_section(cfg: LbConfigurationDict) -> Optional[LbConfigurationDict]:

            def fqdn():
                nonlocal cfg, aprompt
                cfg["fqdn"] = aprompt.get_fqdn(prompt_prefix=_("Insert fqdn"), default=cfg.get("fqdn", ""))

            def proto():
                nonlocal cfg
                cfg["protocol"] = aprompt.get_word(
                    ["http", "https"], prompt_prefix=_("choose protocol"), default=cfg.get("protocol", "https")
                )

            def stickysession():
                nonlocal cfg
                cfg["stickySessions"] = choice(
                    message=_("do you need sticky Sessions?"),
                    options=[
                        (True, _("Yes")),
                        (False, _("No")),
                    ],
                    default=cfg.get("stickySessions", False),
                    show_frame=~is_done,
                )

            def redirect():
                nonlocal cfg
                cfg["redirectHttp"] = choice(
                    message=_("Do you need http rediretion to https?"),
                    options=[
                        (True, _("Yes")),
                        (False, _("No")),
                    ],
                    default=cfg.get("redirectHttp", False),
                    show_frame=~is_done,
                )

            def backend():
                nonlocal cfg
                if "backends" not in cfg:
                    cfg["backends"] = []
                while True:
                    todo = choice(
                        message=_("Section Edit: Please select an action ?:"),
                        options=[
                            (1, _("add new Back-end")),
                            (2, _("edit Back-end")),
                            (3, _("remove Back-end")),
                            (4, _("leave unchanged")),
                        ],
                        default=3,
                        show_frame=~is_done,
                    )
                    if todo == 1:
                        backend_dict: LbBackendDict = {}
                        backend_dict["name"] = aprompt.get_alfanum(
                            "name", not_in=[i["name"] for i in cfg.get("backends", [])]
                        )
                        backend_dict = edit_backend(backend_data=backend_dict, cfg=cfg, todelete=False)
                        cfg["backends"].append(backend_dict)

                    elif todo == 2:
                        msg = _("review")
                        l = len(cfg["backends"])
                        toedit = choice(
                            message=_("choose backend to edit?"),
                            options=[(i, f"{msg} {cfg['backends'][i]['name']}") for i in range(l)],
                            show_frame=~is_done,
                        )
                        backend_dict = cfg["backends"][toedit]
                        backend_dict = edit_backend(backend_data=backend_dict, cfg=cfg)
                        cfg["backends"][toedit] = backend_dict
                    elif todo == 3:
                        msg = _("delete")
                        l = len(cfg["backends"])
                        todel = choice(
                            message=_("choose backend to delete?"),
                            options=[(i, f"{msg} {cfg['backends'][i]['name']}") for i in range(l)],
                            show_frame=~is_done,
                        )
                        cfg["backends"].pop(todel)
                    else:
                        return

            def whitelist():
                nonlocal cfg, aprompt
                if cfg.get("whiteList") is None:
                    cfg["whiteList"] = []
                wl = ",".join(cfg["whiteList"])
                wl = aprompt.get_ipv4_cidr_list(_("White list"), default=wl)

                cfg["whiteList"] = wl.replace(" ", "").split(",")

            def certificate():
                nonlocal cfg
                #key = "certificate"
                todo = choice(
                    message=_("Do you change certificate?"),
                    options=[(1, "load new"), (2, "remove"), (3, "leave unchamged")],
                    default=3,
                    show_frame=~is_done,
                )
                if todo == 1:
                    fname = aprompt.get_filename(patterns=["*.pem", "*.crt"])
                    if os.path.exists(fname):
                        with open(fname, "r", encoding="utf-8") as s:
                            cfg["certificate"] = s.read()
                elif todo == 2:
                    cfg.pop("certificate", None)
                    # if "certificate" in cfg.keys():
                    #     delete(cfg["certificate"])

            # fqdn()
            # proto()
            # stickysession()
            # redirect()
            # backend()
            # whitelist()
            # certificate()
            while True:
                # self.app.render(cfg, details=True, fields=fields, headers=fields,  maxsize=45)
                self.app.render(cfg, details=True, maxsize=45)
                result = choice(
                    message=_("Please select an option"),
                    options=[
                        ("delete", _("Delete section")),
                        ("fqdn", _("Set fqdn")),
                        ("proto", _("Set protocol")),
                        ("sticky", _("Set stickySessions")),
                        ("redire", _("Set redirectHttp")),
                        ("backen", _("Set backends")),
                        ("whitel", _("Set whiteList")),
                        ("certif", _("Set certificate")),
                        ("exit", _("Exit")),
                    ],
                    default="exit",
                    show_frame=~is_done,
                )
                if result == "delete":
                    return None
                if result == "fqdn":
                    fqdn()
                elif result == "proto":
                    proto()
                elif result == "sticky":
                    stickysession()
                elif result == "redire":
                    redirect()
                elif result == "backen":
                    backend()
                elif result == "whitel":
                    whitelist()
                elif result == "certif":
                    certificate()
                elif result == "exit":
                    return cfg
                else:
                    pass

        ### Load Configuration
        while working:
            result = choice(
                message=_("Please select an option"),
                options=[
                    (1, _("Load configuration from file")),
                    (2, _("Load configuration from existing lbaas")),
                    (3, _("Start from scratch")),
                    (4, _("Exit")),
                ],
                default="file",
                show_frame=~is_done,
            )
            if result == 1:
                load_file()
            elif result == 2:
                load_lbaas()
            elif result == 3:
                working = False
            elif result == 4:
                os._exit(0)
            else:
                pass
        working = True
        ## Edit Configuration
        while working:
            show_sections(lbaasconfig)
            options = [(-1, _("Add new section"))]
            for i in [
                (item, f"{_('Edit ')} {lbaasconfig[item].get('alias', f'item{item}')}")
                for item in range(len(lbaasconfig))
            ]:
                options.append(i)
            options.append(
                (-99, _("Stop Editing")),
            )
            result = choice(
                message=_("Configuration Edit: Please select an option."),
                options=options,
                default="exit",
                show_frame=~is_done,
            )
            if result >= 0:
                sec = lbaasconfig[result]
                sec = edit_section(sec)
                if sec is None:
                    lbaasconfig.pop(result)
            elif result == -1:
                new: LbConfigurationDict = {}
                new["alias"] = aprompt.get_alfanum(
                    prompt_prefix=_("New section alias"), not_in=[i["alias"] for i in lbaasconfig]
                )
                new = edit_section(new)
                if new is not None:
                    lbaasconfig.append(new)

            elif result == -99:
                working = False
            else:
                pass

        working = True
        ## Save Configuration
        while working:
            result = choice(
                message=_("Use Configuration: Please select an option"),
                options=[
                    ("new", _("Apply to new lbaas")),
                    ("apply", _("Apply to existing lbaas")),
                    ("save", _("Save to file")),
                    ("exit", _("Exit")),
                ],
                default="exit",
                show_frame=~is_done,
            )
            if result == "new":
                checkport()
                create()
            elif result == "apply":
                checkport()
                update()
            elif result == "save":
                checkport()
                name = aprompt.get_alfanum(prompt_prefix=_("File name"))
                with open(f"{name}.yml", "w", encoding="utf-8") as wf:
                    yaml_dump({"configuration": lbaasconfig}, wf)
                with open(f"{name}.json", "w", encoding="utf-8") as wf:
                    json_dump({"configuration": lbaasconfig}, wf)
            elif result == "exit":
                working = False
