# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


from typing import TypedDict, Optional, List
from urllib.parse import urlencode
from cement import ex

from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.completion import WordCompleter

from beecell.db.db_name import DatabaseConstants, get_db_name
from beecell.password import random_password
from beecell.types.type_dict import dict_get, dict_set

from beehive3_cli.core.controller import ARGS
from beehive3_cli.core.prompt_utils import (
    CmpValidator,
    MandatoryValidator,
    NumberValidator,
    PromptAccount,
    PromptNetaas,
    PromptUtil,
    start_progress,
)

from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild
from beehive3_cli.translate import _


class DBaaServiceController(BusinessControllerChild):
    class Meta:  # type: ignore
        label = "dbaas"
        description = _("database service management")
        help = _("database service management")

    @ex(
        help=_("get database service info"),
        description=_(
            "This command retrieves information about a database service instance. "
            "It requires the account ID of the service as the only required argument."
        ),
        example="beehive bu dbaas info <uuid>; beehive bu dbaas info <uuid> -e <env>",
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
        uri = f"{self.baseuri}/databaseservices"
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, "DescribeDatabaseResponse.databaseSet.0")
        self.app.render(res, details=True, maxsize=100)

    @ex(
        help=_("get database service quotas"),
        description=_(
            "This command is used to get database service quotas for a given account id. "
            "It requires the account id as the only required argument to retrieve the quotas "
            "allocated to that account for database services."
        ),
        example="beehive bu dbaas quotas Acc_demo1_nmsflike -e <env>",
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
        uri = f"{self.baseuri}/databaseservices/describeaccountattributes"
        res = self.cmp_get(uri, data=urlencode(data))
        res = dict_get(res, "DescribeAccountAttributesResponse.accountAttributeSet")
        headers = ["name", "value", "used"]
        fields = [
            "attributeName",
            "attributeValueSet.0.item.attributeValue",
            "attributeValueSet.0.item.nvl-attributeUsed",
        ]
        self.app.render(res, headers=headers, fields=fields)


class DBServiceInstanceController(BusinessControllerChild):
    class Meta:
        stacked_on = "dbaas"
        stacked_type = "nested"
        label = "db_instances"
        description = _("database instance service management")
        help = _("database instance service management")

        cmp = {"baseuri": "/v2.0/nws", "subsystem": "service"}
        # cmp = {'baseuri': '/v1.0/nws', 'subsystem': 'service'}

    def __get_instance_id_key(self):
        if self._meta.cmp["baseuri"].find("v1.0") > 0:
            return "db-instance-id"
        if self._meta.cmp["baseuri"].find("v2.0") > 0:
            return "db-instance-id"
        return None

    def __get_field_id_key(self):
        if self._meta.cmp["baseuri"].find("v1.0") > 0:
            return "DBInstanceIdentifier"
        if self._meta.cmp["baseuri"].find("v2.0") > 0:
            return "DbiResourceId"
        return None

    def __get_field_id_name(self):
        if self._meta.cmp["baseuri"].find("v1.0") > 0:
            return "nvl-name"
        if self._meta.cmp["baseuri"].find("v2.0") > 0:
            return "DBInstanceIdentifier"
        return None

    # def __exist(self, instance):
    #    data = {"%s.N" % self.__get_instance_id_key(): instance}
    #    uri = "%s/databaseservices/instance/describedbinstances" % self.baseuri
    #    res = self.cmp_get(uri, data=urlencode(data, doseq=True))
    #    res = res.get("DescribeDBInstancesResponse").get("DescribeDBInstancesResult")
    #    if len(res.get("DBInstances")) > 0:
    #        #resp = res.get("DBInstances")[0]
    #        return True
    #    return False

    @ex(
        help=_("get database instance types"),
        description=_(
            "This command is used to retrieve the available database instance types "
            "from the Nivola CMP Database as a Service (DBaaS). "
            "Database instance types determine the hardware specifications like CPU, "
            "memory, storage etc. of the database instance. "
            "The command does not require any arguments. "
            "The output will list all supported database instance types that "
            "can be used while provisioning a new database instance."
        ),
        example="beehive bu dbaas db-instances types -e <env>",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("parent account id"),
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
    def types(self):
        params = ["account"]
        mappings = {
            "account": lambda x: self.get_account(x)["uuid"],
        }
        aliases = {"account": "owner-id", "size": "MaxResults", "page": "NextToken"}
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "/v2.0/nws/databaseservices/instance/describedbinstancetypes"
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeDBInstanceTypesResponse")
        page = self.app.pargs.page
        resp = {
            "count": len(res.get("instanceTypesSet")),
            "page": page,
            "total": res.get("instanceTypesTotal"),
            "sort": {"field": "id", "order": "asc"},
            "types": res.get("instanceTypesSet"),
        }
        headers = ["id", "instance_type", "desc", "vcpus", "disk", "ram"]
        fields = [
            "uuid",
            "name",
            "description",
            "features.vcpus",
            "features.disk",
            "features.ram",
        ]
        self.app.render(resp, key="types", headers=headers, fields=fields)

    @ex(
        help=_("get database instance engines"),
        description=_(
            "This command is used to get database instance engines. "
            "It retrieves the engines of database instances from the "
            "Nivola CMP Database as a Service (DBaaS). No required arguments."
        ),
        example="beehive bu dbaas db-instances engines sige-preprod",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("parent account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def engines(self):
        data = {"owner-id": self.get_account(self.app.pargs.account)["uuid"]}
        uri = "/v2.0/nws/databaseservices/instance/enginetypes"
        res = self.cmp_get(uri, data=data).get("DescribeDBInstanceEngineTypesResponse")
        self.app.render(
            res,
            headers=["engine", "version", "fullVersion", "definition", "description"],
            fields=["engine", "engineVersion", "fullVersion", "definition", "description"],
            key="engineTypesSet",
        )

    @ex(
        help=_("get database instances"),
        description=_(
            "This command retrieves database instances from the Nivola CMP Database as a Service (DBaaS). "
            "It lists out existing database instances without requiring any arguments. "
            "The -size and -accounts options allow filtering the results by page size or associated "
            "account respectively."
        ),
        example="beehive bu dbaas db-instances list -accounts MOODLE",
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
                        "help": _("list of db instance id comma separated"),
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
            "ids": f"{self.__get_instance_id_key()}.N",
            "tags": "Nvl-tag-key.N",
            "size": "MaxRecords",
            "page": "Marker",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = f"{self.baseuri}/databaseservices/instance/describedbinstances"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeDBInstancesResponse").get("DescribeDBInstancesResult")
            resp = {
                "count": len(res.get("DBInstances")),
                "page": page,
                "total": res.get("nvl-DBInstancesTotal"),
                "sort": {"field": "id", "order": "asc"},
                "instances": res.get("DBInstances", []),
            }
            headers = [
                "id",
                "name",
                "status",
                "account",
                "Engine",
                "EngineVersion",
                "AllocatedStorage",
                "AvailabilityZone",
                "DBInstanceClass",
                "Subnet",
                "Listen",
                "Port",
                "Date",
                # "MasterUsername",
            ]
            fields = [
                f"DBInstance.{self.__get_field_id_key()}",
                f"DBInstance.{self.__get_field_id_name()}",
                "DBInstance.DBInstanceStatus",
                "DBInstance.nvl-ownerAlias",
                "DBInstance.Engine",
                "DBInstance.EngineVersion",
                "DBInstance.AllocatedStorage",
                "DBInstance.AvailabilityZone",
                "DBInstance.DBInstanceClass",
                "DBInstance.DBSubnetGroup.DBSubnetGroupName",
                "DBInstance.Endpoint.Address",
                "DBInstance.Endpoint.Port",
                "DBInstance.InstanceCreateTime",
                # "DBInstance.MasterUsername",
            ]
            transform = {"DBInstance.DBInstanceStatus": self.color_error}
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
            pagesize=20,
            key_total_name="DescribeDBInstancesResponse.DescribeDBInstancesResult.nvl-DBInstancesTotal",
            key_list_name="DescribeDBInstancesResponse.DescribeDBInstancesResult.DBInstances",
            fn_render=render,
        )

    @ex(
        help=_("get database instances"),
        description=_(
            "This command retrieves database instances from the Nivola CMP Database as a Service (DBaaS). "
            "The -size and -accounts options allow filtering the results by page size or associated "
            "account respectively."
        ),
        example="beehive bu dbaas db-instances simple-list -accounts MOODLE",
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
                        "help": _("list of db instance id comma separated"),
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
    def simple_list(self):
        params = ["accounts", "ids", "tags"]
        mappings = {
            "accounts": self.get_account_ids,
            "tags": lambda x: x.split(","),
            "ids": lambda x: x.split(","),
        }
        aliases = {
            "accounts": "owner-id.N",
            "ids": f"{self.__get_instance_id_key()}.N",
            "tags": "Nvl-tag-key.N",
            "size": "MaxRecords",
            "page": "Marker",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = f"{self.baseuri}/databaseservices/instance/describesimpledbinstances"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeDBInstancesResponse").get("DescribeDBInstancesResult")
            resp = {
                "count": len(res.get("DBInstances")),
                "page": page,
                "total": res.get("nvl-DBInstancesTotal"),
                "sort": {"field": "id", "order": "asc"},
                "instances": res.get("DBInstances", []),
            }
            headers = [
                "id",
                "name",
                "status",
                "account",
                "Engine",
                "EngineVersion",
                "AllocatedStorage",
                "AvailabilityZone",
                "DBInstanceClass",
                "Subnet",
                "Listen",
                "Port",
                "Date",
                # "MasterUsername",
            ]
            fields = [
                f"DBInstance.{self.__get_field_id_key()}",
                f"DBInstance.{self.__get_field_id_name()}",
                "DBInstance.DBInstanceStatus",
                "DBInstance.nvl-ownerAlias",
                "DBInstance.Engine",
                "DBInstance.EngineVersion",
                "DBInstance.AllocatedStorage",
                "DBInstance.AvailabilityZone",
                "DBInstance.DBInstanceClass",
                "DBInstance.DBSubnetGroup.DBSubnetGroupName",
                "DBInstance.Endpoint.Address",
                "DBInstance.Endpoint.Port",
                "DBInstance.InstanceCreateTime",
                # "DBInstance.MasterUsername",
            ]
            transform = {"DBInstance.DBInstanceStatus": self.color_error}
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
            pagesize=20,
            key_total_name="DescribeDBInstancesResponse.DescribeDBInstancesResult.nvl-DBInstancesTotal",
            key_list_name="DescribeDBInstancesResponse.DescribeDBInstancesResult.DBInstances",
            fn_render=render,
        )

    @ex(
        help=_("list all db-instance"),
        description=_(
            "This command lists all database instances within a specified range. "
            "It requires the 'start' and 'end' arguments to define the lower and "
            "upper bounds of the instance IDs range to list instances from."
        ),
        arguments=ARGS(
            [
                (
                    ["start"],
                    {
                        "help": _("instances range lower bound"),
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["end"],
                    {
                        "help": _("instances range upper bound"),
                        "action": "store",
                        "type": int,
                    },
                ),
            ]
        ),
    )
    def list_all(self):
        account_d = {}

        def get_account(account_uuid):
            uri = f"{self.baseuri}/accounts/{account_uuid}"
            res = self.cmp_get(uri)
            res = res.get("account")
            account_name = res.get("name")
            div_uuid = res.get("division_id")
            return account_name, div_uuid

        def get_division(div_uuid):
            uri = f"/v1.0/nws/divisions/{div_uuid}"
            res = self.cmp_get(uri)
            res = res.get("division")
            div_name = res.get("name")
            org_uuid = res.get("organization_id")
            return div_name, org_uuid

        def get_organization(org_uuid):
            uri = f"/v1.0/nws/organizations/{org_uuid}"
            res = self.cmp_get(uri)
            res = res.get("organization")
            org_name = res.get("name")
            return org_name

        def get_node_name(ip_addr):
            if ip_addr:
                data = {"ip_address": ip_addr}
                uri = "/v1.0/gas/nodes"
                res = self.cmp_get(uri, data=urlencode(data, doseq=True))
                nodes = res.get("nodes")
                if not nodes:
                    return None
                node = nodes[0]
                name = node.get("name")
                return name
            return None

        def get_instance(page, size):
            data = {"MaxRecords": size, "Marker": page}
            uri = f"{self.baseuri}/databaseservices/instance/describedbinstances"
            res = self.cmp_get(uri, data=urlencode(data, doseq=True))
            res = res.get("DescribeDBInstancesResponse").get("DescribeDBInstancesResult")
            total = res.get("nvl-DBInstancesTotal")
            db_instances = res.get("DBInstances")
            for db_instance in db_instances:
                # get fqdn of database server
                ip_addr = dict_get(db_instance, "DBInstance.Endpoint.Address")
                fqdn = get_node_name(ip_addr)
                dict_set(db_instance, "DBInstance.Endpoint.Fqdn", fqdn)
                # get account triplet, i.e. org.div.account
                account_uuid = dict_get(db_instance, "DBInstance.nvl-ownerId")
                if account_uuid in account_d:
                    account_triplet = account_d[account_uuid]
                else:
                    account_name, div_uuid = get_account(account_uuid)
                    div_name, org_uuid = get_division(div_uuid)
                    org_name = get_organization(org_uuid)
                    account_triplet = f"{org_name}.{div_name}.{account_name}"
                    account_d[account_uuid] = account_triplet
                dict_set(db_instance, "DBInstance.nvl-ownerAlias", account_triplet)

            return db_instances, total

        # secs = 0
        size = 20
        start = self.app.pargs.start
        end = self.app.pargs.end
        if not isinstance(start, int):
            start = int(start)
        if not isinstance(end, int):
            end = int(end)
        if start < 0 or end < 0:
            raise Exception("Upper and/or lower bounds cannot be negative")
        if start > end:
            raise Exception("Lower bound cannot be greater that upper bound")
        if start == 0:
            start = 1
        first_page = start // size
        last_page = end // size + (end % size > 0)
        headers = [
            "id",
            "name",
            "status",
            "account",
            "engine",
            "engine_ver",
            "type",
            "allocated_storage",
            "avz",
            "subnet",
            "ip_addr",
            "port",
            "fqdn",
            "creation_date",
        ]
        fields = [
            f"DBInstance.{self.__get_field_id_key()}",
            f"DBInstance.{self.__get_field_id_name()}",
            "DBInstance.DBInstanceStatus",
            "DBInstance.nvl-ownerAlias",
            "DBInstance.Engine",
            "DBInstance.EngineVersion",
            "DBInstance.DBInstanceClass",
            "DBInstance.AllocatedStorage",
            "DBInstance.AvailabilityZone",
            "DBInstance.DBSubnetGroup.DBSubnetGroupName",
            "DBInstance.Endpoint.Address",
            "DBInstance.Endpoint.Port",
            "DBInstance.Endpoint.Fqdn",
            "DBInstance.InstanceCreateTime",
        ]
        resp = []
        lformat = self.format
        for page in range(first_page, last_page):
            print(f"getting db-instances from {page * size + 1} to {(page + 1) * size} ...")
            try:
                chunk_resp = get_instance(page, size)[0]
                if lformat == "text":
                    self.app.render(chunk_resp, headers=headers, fields=fields)
                else:
                    resp += chunk_resp
                print(f"got db-instances from {page * size + 1} to {(page + 1) * size}")
                # time.sleep(secs)
            except Exception as exc:
                print(exc)
                break
        if lformat == "json":
            self.app.render(resp, headers=headers, fields=fields)

    @ex(
        help=_("get database instance"),
        description=_(
            "This command retrieves details of a specific database instance from "
            "the Nivola CMP Database as a Service (DBaaS) platform. "
            "The 'id' argument is required to identify the database instance being retrieved."
        ),
        example="beehive bu dbaas db-instances get <id_Dbinstance>",
        arguments=ARGS(
            [
                (["id"], {"help": _("database id"), "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {f"{self.__get_instance_id_key()}.N": [oid]}
        elif self.is_name(oid):
            data = {"DBInstanceIdentifier": oid}
        uri = f"{self.baseuri}/databaseservices/instance/describedbinstances"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeDBInstancesResponse.DescribeDBInstancesResult", default={})

        if len(res.get("DBInstances")) > 0:
            res = dict_get(res, "DBInstances.0.DBInstance")
            if self.is_output_text():
                network = {}
                instance_type = res.pop("DBInstanceClass", None)
                endpoint = res.pop("Endpoint", {})
                network["ip_address"] = endpoint.get("Address")
                network["port"] = endpoint.get("Port")
                subnet = res.pop("DBSubnetGroup")
                network["subnet"] = (
                    f"{dict_get(subnet, 'Subnets.0.SubnetIdentifier')} - " f"{subnet.get('DBSubnetGroupName', None)}"
                )
                sgs = res.pop("VpcSecurityGroups", [])
                self.app.render(res, details=True, maxsize=100)
                self.c("\ninstance type", "underline")
                self.app.render({"DBInstanceClass": instance_type}, headers=["DBInstanceClass"])
                self.c("\nnetwork", "underline")
                self.app.render(network, details=True)
                print()
                self.app.render(
                    sgs,
                    headers=["groupId", "groupName"],
                    fields=[
                        "VpcSecurityGroupMembership.VpcSecurityGroupId",
                        "VpcSecurityGroupMembership.nvl-vpcSecurityGroupName",
                    ],
                )
            else:
                self.app.render(res, details=True, maxsize=400)
        else:
            raise Exception(f"db-instance {oid} was not found")

    def __add_common(self):
        name = self.app.pargs.name
        account = self.get_account(self.app.pargs.account).get("uuid")
        template = self.get_service_definition(self.app.pargs.type)
        subnet = self.get_service_instance(self.app.pargs.subnet, account_id=account)
        engine_version = self.app.pargs.version
        sg = self.get_service_instance(self.app.pargs.sg, account_id=account)

        data = {
            "AccountId": account,
            "DBInstanceIdentifier": name,
            "DBInstanceClass": template,
            "DBSubnetGroupName": subnet,
            "EngineVersion": engine_version,
            "VpcSecurityGroupIds": {"VpcSecurityGroupId": sg.split(",")},
        }
        kms_domain = self.app.pargs.kms_domain
        if type(kms_domain) == str:
            data["KmsDomain"] = kms_domain

        self.add_field_from_pargs_to_data("pwd", data, "MasterUserPassword")
        self.add_field_from_pargs_to_data("keyname", data, "Nvl_KeyName")

        return data

    def __cmp_post(self, data):
        uri = f"{self.baseuri}/databaseservices/instance/createdbinstance"
        res = self.cmp_post(uri, data={"dbinstance": data}, timeout=600)
        uuid = dict_get(
            res,
            "CreateDBInstanceResponse.CreateDBInstanceResult.DBInstance.DBInstanceIdentifier",
        )
        self.wait_for_service(uuid)
        self.app.render({"msg": f"Add database instance {uuid}"})

    @ex(
        help=_("wizard to create a db instance"),
        description=_("wizard to create a db instance"),
        example="beehive bu dbaas db-instances add_wizard",
        arguments=ARGS([]),
    )
    def add_wizard(self):
        db_account, db_account_uuid = PromptAccount.get_account(self, "db")

        # engine
        control_thread = start_progress("types")

        uri = "/v2.0/nws/databaseservices/instance/enginetypes"
        data = {
            "owner-id": db_account_uuid,
        }
        res = self.cmp_get(uri, data=data)
        control_thread.stop()
        res = dict_get(res, "DescribeDBInstanceEngineTypesResponse")
        engines = res.get("engineTypesSet")
        engine_names = [f"{engine.get('engine')} {engine.get('fullVersion')}" for engine in engines]
        engine_names.sort()
        engine_completer = WordCompleter(engine_names, ignore_case=True, match_middle=True)
        engine_session = PromptSession(completer=engine_completer)
        PromptUtil.start_completer(engine_session)
        db_full_engine = engine_session.prompt(
            "db engine > ",
            search_ignore_case=True,
            key_bindings=PromptUtil.kb,
            validator=CmpValidator(self.app, engine_names),
        )

        db_engine = None
        db_engine_full_version = None
        for engine in engines:
            full_engine = f"{engine.get('engine')} {engine.get('fullVersion')}"
            if full_engine == db_full_engine:
                db_engine = engine.get("engine")
                db_engine_full_version = engine.get("fullVersion")

        # environment
        environment_names = [f"{environment.get('name')}" for environment in DatabaseConstants.ENVIRONMENTS]
        environment_completer = WordCompleter(environment_names, ignore_case=True, match_middle=True)
        environment_session = PromptSession(completer=environment_completer)
        PromptUtil.start_completer(environment_session)

        vm_environment = environment_session.prompt(
            "db environment > ",
            search_ignore_case=True,
            key_bindings=PromptUtil.kb,
            validator=CmpValidator(self.app, environment_names),
        )

        environment_prefix = None
        for environment in DatabaseConstants.ENVIRONMENTS:
            if environment.get("name") == vm_environment:
                environment_prefix = environment.get("prefix")

        # digit
        digit_len = 3
        digit_msg = "Enter a three-digit using 001,002 format"
        if db_engine == "sqlserver" and db_engine_full_version == "2017":
            digit_len = 2
            digit_msg = "Enter a two-digit using 01,02 format"

        db_digit = prompt("db digit > ", validator=NumberValidator(self.app, length=digit_len), placeholder=digit_msg)

        # acronym
        default: str = db_account
        acronym_length = -1
        if db_engine == "sqlserver":
            default = db_account[0:6]
            acronym_length = 6

        db_acronym = prompt(
            "db acronym > ", validator=MandatoryValidator(self.app, length=acronym_length), default=default.lower()
        )

        db_name = get_db_name(db_engine, db_acronym, environment_prefix, db_digit)

        # type
        control_thread = start_progress("types")

        uri = "/v2.0/nws/databaseservices/instance/describedbinstancetypes"
        data = {
            "owner-id": db_account_uuid,
            "NextToken": 0,
            "MaxResults": -1,
        }
        res = self.cmp_get(uri, data=data)
        control_thread.stop()
        res = dict_get(res, "DescribeDBInstanceTypesResponse")
        types = res.get("instanceTypesSet")
        type_names = [type.get("name") for type in types]
        type_names.sort()
        type_completer = WordCompleter(type_names, ignore_case=True, match_middle=True)
        type_session = PromptSession(completer=type_completer)
        PromptUtil.start_completer(type_session)

        db_type = type_session.prompt(
            "db type > ",
            search_ignore_case=True,
            key_bindings=PromptUtil.kb,
            validator=CmpValidator(self.app, type_names),
        )

        # subnet
        db_subnet = PromptNetaas.get_subnet(self, db_account_uuid, "db")

        # securitygroup
        db_securitygroup = PromptNetaas.get_security_group(self, db_account_uuid, "db")

        # show command - name account type subnet sg version
        command = (
            f"beehive bu dbaas db-instances add-{db_engine} {db_name} {db_account_uuid} "
            f"{db_type} {db_subnet} {db_securitygroup} {db_engine_full_version} -h"
        )

        print("")
        print(_("Run the following command, possibly specifying the parameters for the db engine (-h show help): "))
        print(command)

    @ex(
        help=_("create mysql db instance"),
        description=_(
            "This command creates a MySQL database instance. "
            "It requires the name, account id, type, subnet id, security group id and "
            "database engine version as required arguments to uniquely identify and provision the database instance."
        ),
        example=(
            "beehive bu dbaas db-instances add-mysql dbs-cmrc-proto-prd-001m cmrc-proto db.m8.xlarge "
            "Subnet-Rupar62-torino02 SG-DBAAS 8.0.25-vs"
        ),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("db instance name"), "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (
                    ["type"],
                    {"help": _("db instance type"), "action": "store", "type": str},
                ),
                (
                    ["subnet"],
                    {"help": _("db instance subnet id"), "action": "store", "type": str},
                ),
                (
                    ["sg"],
                    {
                        "help": _("db instance security group id"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["version"],
                    {"help": _("database engine version"), "action": "store", "type": str},
                ),
                (
                    ["-pwd"],
                    {
                        "help": _("db root password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-storage"],
                    {
                        "help": _("data storage capacity in GB"),
                        "action": "store",
                        "type": int,
                        "default": 30,
                    },
                ),
                (
                    ["-keyname"],
                    {
                        "help": _("ssh key name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-kms-domain"],
                    {
                        "help": _("kms domain only if TDE  available"),
                        "dest": "kms_domain",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add_mysql(self):
        data = self.__add_common()
        data.update({"Engine": "mysql"})
        data.update({"AllocatedStorage": self.app.pargs.storage})

        self.__cmp_post(data)

    @ex(
        help=_("create MariaDB db instance"),
        description=_(
            "This command creates a MariaDB database instance on Nivola Cloud. "
            "It requires the name, account ID, type, subnet ID, security group "
            "ID and version of the database to be specified as required arguments."
        ),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("db instance name"), "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (
                    ["type"],
                    {"help": _("db instance type"), "action": "store", "type": str},
                ),
                (
                    ["subnet"],
                    {"help": _("db instance subnet id"), "action": "store", "type": str},
                ),
                (
                    ["sg"],
                    {
                        "help": _("db instance security group id"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["version"],
                    {"help": _("database engine version"), "action": "store", "type": str},
                ),
                (
                    ["-pwd"],
                    {
                        "help": _("db root password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-storage"],
                    {
                        "help": _("data storage capacity in GB"),
                        "action": "store",
                        "type": int,
                        "default": 30,
                    },
                ),
                (
                    ["-keyname"],
                    {
                        "help": _("ssh key name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-kms-domain"],
                    {
                        "help": _("kms domain only if TDE  available"),
                        "dest": "kms_domain",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add_mariadb(self):
        data = self.__add_common()
        data.update({"Engine": "mariadb"})
        data.update({"AllocatedStorage": self.app.pargs.storage})

        self.__cmp_post(data)

    @ex(
        help=_("create postgresql db instance"),
        description=_(
            "This command creates a PostgreSQL database instance. "
            "It requires the name, account id, type, subnet id, "
            "security group id and version of the database as required "
            "arguments to uniquely identify and provision the instance."
        ),
        example=(
            "beehive bu dbaas db-instances add-postgresql dbs-cloudera-prd-002p cloudera db.m4.large "
            "<uuid> SG-DBAAS-PROD 12.4 -storage 50 -e <env>"
        ),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("db instance name"), "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (
                    ["type"],
                    {"help": _("db instance type"), "action": "store", "type": str},
                ),
                (
                    ["subnet"],
                    {"help": _("db instance subnet id"), "action": "store", "type": str},
                ),
                (
                    ["sg"],
                    {
                        "help": _("db instance security group id"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["version"],
                    {"help": _("database engine version"), "action": "store", "type": str},
                ),
                (
                    ["-storage"],
                    {
                        "help": _("amount of storage [GB] to allocate for the DB instance"),
                        "action": "store",
                        "type": int,
                        "default": 30,
                    },
                ),
                (
                    ["-pwd"],
                    {
                        "help": _("db root password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-keyname"],
                    {
                        "help": _("ssh key name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-db-name"],
                    {
                        "type": str,
                        "action": "store",
                        "dest": "db_name",
                        "default": None,
                        "required": False,
                        "help": _("Database name"),
                    },
                ),
                (["-encoding"], {"type": str, "action": "store", "default": "UTF-8", "help": _("Database Encoding")}),
                (
                    ["-lc-collate"],
                    {
                        "type": str,
                        "action": "store",
                        "default": "en_US.UTF-8",
                        "help": _("Database Collate"),
                    },
                ),
                (
                    ["-lc-ctype"],
                    {
                        "type": str,
                        "action": "store",
                        "default": "en_US.UTF-8",
                        "required": False,
                        "help": _("Database Ctype"),
                    },
                ),
                (
                    ["-user-name"],
                    {"type": str, "dest": "role_name", "action": "store", "required": False, "help": _("Role name")},
                ),
                (
                    ["-user-password"],
                    {
                        "type": str,
                        "action": "store",
                        "dest": "role_password",
                        "required": False,
                        "help": _("Role password"),
                    },
                ),
                (
                    ["-schema-name"],
                    {
                        "type": str,
                        "action": "store",
                        "dest": "schema_name",
                        "required": False,
                        "help": _("Schema name"),
                    },
                ),
                (
                    ["--pgcrypto"],
                    {
                        "help": _("activate pgcrypto Postgresql extension"),
                        "action": "append_const",
                        "dest": "pg_extensions",
                        "const": "pgcrypto",
                    },
                ),
                (
                    ["--orafce"],
                    {
                        "help": _("activate orafce Postgresql extension"),
                        "action": "append_const",
                        "dest": "pg_extensions",
                        "const": "orafce",
                    },
                ),
                (
                    ["--tablefunc"],
                    {
                        "help": _("activate tablefunc Postgresql extension"),
                        "action": "append_const",
                        "dest": "pg_extensions",
                        "const": "tablefunc",
                    },
                ),
                (
                    ["--uuid-ossp"],
                    {
                        "help": _("activate uuid Postgresql extension"),
                        "action": "append_const",
                        "dest": "pg_extensions",
                        "const": "uuid-ossp",
                    },
                ),
                (
                    ["--postgis"],
                    {
                        "help": _("activate postgis Postgresql extension"),
                        "action": "append_const",
                        "dest": "pg_extensions",
                        "const": "postgis",
                    },
                ),
                (
                    ["-kms-domain"],
                    {
                        "help": _("kms domain only if TDE  available"),
                        "dest": "kms_domain",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add_postgresql(self):
        data = self.__add_common()

        data.update({"Engine": "postgresql"})
        data.update({"AllocatedStorage": self.app.pargs.storage})

        data["Nvl_Postgresql_Options"] = {
            "Postgresql.GeoExtension": "True",
            "pg_encoding": "UTF-8",
            "pg_lc_collate": "en_US.UTF-8",
            "pg_lc_ctype": "en_US.UTF-8",
        }

        if self.app.pargs.db_name:
            data["Nvl_Postgresql_Options"]["pg_db_name"] = self.app.pargs.db_name
        if self.app.pargs.pg_extensions:
            data["Nvl_Postgresql_Options"]["pg_extensions"] = self.app.pargs.pg_extensions
        if self.app.pargs.role_password:
            data["Nvl_Postgresql_Options"]["pg_password"] = self.app.pargs.role_password
        if self.app.pargs.role_name:
            data["Nvl_Postgresql_Options"]["pg_role_name"] = self.app.pargs.role_name
        if self.app.pargs.schema_name:
            data["Nvl_Postgresql_Options"]["pg_schema_name"] = self.app.pargs.schema_name

        # if self.confirm("This command shall be used only in order to test new postgresql parameters"):
        self.__cmp_post(data)

    @ex(
        help=_("create oracle db instance"),
        description=_(
            "This CLI command creates an Oracle database instance on Nivola Cloud. "
            "It requires the name, account id, type, subnet id, security group id and "
            "version of the database as required arguments. "
            "The database instance type can be db.m2.2xlarge for example. "
            "It creates the instance in the specified subnet and associates "
            "the provided security group to it. "
            "The database version could be 12EE for Oracle 12c Enterprise Edition for instance."
        ),
        example=(
            "beehive bu dbaas db-instances add-oracle dbs-screen-prd-001o screen "
            "db.m2.2xlarge SubnetBE-torino01 SG-DBaaS 12EE -dbname SCREEN "
            "-charset WE8ISO8859P1 -dbfdisksize 500 -recodisksize 500 -e <env>"
        ),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("db instance name"), "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (
                    ["type"],
                    {"help": _("db instance type"), "action": "store", "type": str},
                ),
                (
                    ["subnet"],
                    {"help": _("db instance subnet id"), "action": "store", "type": str},
                ),
                (
                    ["sg"],
                    {
                        "help": _("db instance security group id"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["version"],
                    {"help": _("database engine version"), "action": "store", "type": str},
                ),
                (
                    ["-pwd"],
                    {
                        "help": _("db root password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-keyname"],
                    {
                        "help": _("ssh key name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dbname"],
                    {
                        "help": _("db name [default: ORCL0]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-lsnport"],
                    {
                        "help": _("listener port [default: 1521]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-archmode"],
                    {
                        "help": _("archivelog mode Y/N [default: Y]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-partopt"],
                    {
                        "help": _("partitioning option Y/N [default: Y]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-charset"],
                    {
                        "help": _("character set [default: WE8ISO8859P1]"),
                        "action": "store",
                        "type": str,
                        "default": "WE8ISO8859P1",
                    },
                ),
                (
                    ["-natcharset"],
                    {
                        "help": _("national charset [default: AL16UTF16]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dbfdisksize"],
                    {
                        "help": _("datafiles disk size in GB [default: 30]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-recodisksize"],
                    {
                        "help": _("recovery disk size in GB [default: 20]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-user_name"],
                    {
                        "action": "store",
                        "type": str,
                        "help": _("schema and user name minimum lenght 9, max length 30 "),
                    },
                ),
                (
                    ["-user_pwd"],
                    {"action": "store", "type": str, "help": _("user password minimum lenght 9, max length 30")},
                ),
                (
                    ["--data_tbs_name", "-dtbs_n"],
                    {
                        "action": "store",
                        "dest": "dtbs_n",
                        "type": str,
                        "help": _(
                            "default tablespace name, minimum lenght 9, max length 30. "
                            "It will be converted in upper case"
                        ),
                    },
                ),
                (
                    ["--data_tbs_size", "-dtbs_s"],
                    {
                        "action": "store",
                        "dest": "dtbs_s",
                        "type": str,
                        "help": _("default tablespace initial size (Mega). eg 2048M "),
                    },
                ),
                (
                    ["--data_tbs_nextl", "-dtbs_x"],
                    {
                        "action": "store",
                        "dest": "dtbs_x",
                        "type": str,
                        "help": _("default tablespace next extent size (Mega). eg 32M"),
                    },
                ),
                (
                    ["--idx_tbs_name", "-itbs_n"],
                    {
                        "action": "store",
                        "dest": "itbs_n",
                        "type": str,
                        "help": _(
                            "index tablespace name, minimum lenght 9, max length 30. It will be converted in upper case"
                        ),
                    },
                ),
                (
                    ["--idx_tbs_size", "-itbs_"],
                    {
                        "action": "store",
                        "type": str,
                        "dest": "itbs_s",
                        "help": _("index tablespace intial size (Mega). eg 1024M"),
                    },
                ),
                (
                    ["--idx_tbs_next", "-itbs_x"],
                    {
                        "action": "store",
                        "type": str,
                        "dest": "itbs_x",
                        "help": _("index tablespece next extent size (Mega). eg 16M"),
                    },
                ),
                (
                    ["--lob_tbs_name", "-ltbs_n"],
                    {
                        "action": "store",
                        "type": str,
                        "dest": "ltbs_n",
                        "help": _(
                            "LOB tablespace name, minimum lenght 9, max length 30. It will be converted in upper case"
                        ),
                    },
                ),
                (
                    ["--lob_tbs_size", "-ltbs_s"],
                    {
                        "action": "store",
                        "type": str,
                        "dest": "ltbs_s",
                        "help": _("LOB tablespace intial size (Mega). eg 2048M"),
                    },
                ),
                (
                    ["--lob_tbs_next", "-ltbs_x"],
                    {
                        "action": "store",
                        "type": str,
                        "dest": "ltbs_x",
                        "help": _("LOB tablespace next extente size (Mega). eg32M"),
                    },
                ),
                (
                    ["--batch", "-B"],
                    {"action": "store_true", "dest": "batch", "help": _("Batch mode non interactive")},
                ),
                (
                    ["--no_starter_pack", "--no_sp"],
                    {"action": "store_true", "dest": "no_sp", "help": _("no starter pack")},
                ),
                (
                    ["-kms-domain"],
                    {
                        "help": _("kms domain only if TDE  available"),
                        "dest": "kms_domain",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add_oracle(self):
        data = self.__add_common()
        data.update({"Engine": "oracle"})
        self.add_field_from_pargs_to_data("pwd", data, "MasterUserPassword")
        self.add_field_from_pargs_to_data("keyname", data, "Nvl_KeyName")

        d = {}
        self.add_field_from_pargs_to_data("dbname", d, "Oracle.DBName")
        self.add_field_from_pargs_to_data("lsnport", d, "Oracle.LsnPort")
        self.add_field_from_pargs_to_data("archmode", d, "Oracle.ArchMode")
        self.add_field_from_pargs_to_data("partopt", d, "Oracle.PartOption")
        self.add_field_from_pargs_to_data("charset", d, "Oracle.CharSet")
        self.add_field_from_pargs_to_data("natcharset", d, "Oracle.NatCharSet")
        self.add_field_from_pargs_to_data("dbfdisksize", d, "Oracle.DbfDiskSize")
        self.add_field_from_pargs_to_data("recodisksize", d, "Oracle.RecoDiskSize")
        if d:
            data["Nvl_Oracle_Options"] = {}
            data["Nvl_Oracle_Options"].update(d)

        batch = self.app.pargs.batch or self.app.pargs.assumeyes
        no_sp = self.app.pargs.no_sp

        def upperformat(a: str) -> str:
            if len(a) <= 30:
                return str(a).upper()
            raise Exception(f"{a} is too long")

        if batch:
            # batch mode
            if not no_sp:
                sp = {}
                # -user_name # -user_pwd # -data_tbs # -data_tb_sizes # -data_tb_nexts
                self.add_field_from_pargs_to_data("user_name", sp, "Oracle.UserName", format=upperformat)
                self.add_field_from_pargs_to_data("user_pwd", sp, "Oracle.UserPwd", format=upperformat)
                if sp.get("Oracle.UserName") is not None:
                    if sp.get("Oracle.UserPwd") is None:
                        raise Exception("User password is mandatory when creating schema")
                    # when strater pack use default value for manadatory tablespace when data is missing
                    self.add_field_from_pargs_to_data(
                        "dtbs_n",
                        sp,
                        "Oracle.DataTablespaceName",
                        default_value=sp["Oracle.UserName"] + "_TBL",
                        format=upperformat,
                    )
                    self.add_field_from_pargs_to_data("dtbs_s", sp, "Oracle.DataTablespaceSize", default_value="2048M")
                    self.add_field_from_pargs_to_data("dtbs_x", sp, "Oracle.DataTablespaceNext", default_value="32M")

                    # non mandatory tablespace -idx_tbs # -idx_tbs_size # -idx_tbs_next
                    self.add_field_from_pargs_to_data("itbs_n", sp, "Oracle.IdxTablespaceName", format=upperformat)
                    if sp.get("Oracle.IdxTablespaceName") is not None:
                        self.add_field_from_pargs_to_data(
                            "itbs_s", sp, "Oracle.IdxTablespaceSize", default_value="1024M"
                        )
                        self.add_field_from_pargs_to_data("itbs_x", sp, "Oracle.IdxTablespaceNext", default_value="32M")

                    # non mandatory tablespace  -lob_tbs # -lob_tbs_size # -lob_tbs_next
                    self.add_field_from_pargs_to_data("ltbs_n", sp, "Oracle.LobTablespaceName", format=upperformat)
                    if sp.get("Oracle.LobTablespaceName") is not None:
                        self.add_field_from_pargs_to_data(
                            "ltbs_s", sp, "Oracle.LobTablespaceSize", default_value="2048M"
                        )
                        self.add_field_from_pargs_to_data("ltbs_x", sp, "Oracle.LobTablespaceNext", default_value="32M")
                data["Nvl_Oracle_Options"].update(sp)
            # self.print_dict(data)
            self.__cmp_post(data)

        else:
            # interactive mode
            if not no_sp:
                # if self.confirm(msg="do you want configure schema"):
                if not self.confirm(msg="skip schema creation?", suffix="[y/n]"):
                    sp = {}
                    # -user_name # -user_pwd # -data_tbs # -data_tb_sizes # -data_tb_nexts
                    self.interactive_add_field_from_pargs_to_data(
                        "user_name", sp, "Oracle.UserName", default_value="SCHEMA", format=upperformat
                    )
                    self.interactive_add_field_from_pargs_to_data(
                        "user_pwd", sp, "Oracle.UserPwd", default_value=random_password()
                    )
                    self.interactive_add_field_from_pargs_to_data(
                        "dtbs_n",
                        sp,
                        "Oracle.DataTablespaceName",
                        default_value=sp["Oracle.UserName"] + "_TBL",
                        format=upperformat,
                    )
                    self.interactive_add_field_from_pargs_to_data(
                        "dtbs_s", sp, "Oracle.DataTablespaceSize", default_value="2048M"
                    )
                    self.interactive_add_field_from_pargs_to_data(
                        "dtbs_x", sp, "Oracle.DataTablespaceNext", default_value="32M"
                    )

                    # -idx_tbs # -idx_tbs_size # -idx_tbs_next
                    # if self.confirm(msg="do you want configure an index tablaspace"):
                    if self.confirm(msg="Will you create index tablaspace?", suffix="[y/n]"):
                        self.interactive_add_field_from_pargs_to_data(
                            "itbs_n",
                            sp,
                            "Oracle.IdxTablespaceName",
                            default_value=sp["Oracle.UserName"] + "_IDX",
                            format=upperformat,
                        )
                        self.interactive_add_field_from_pargs_to_data(
                            "itbs_s", sp, "Oracle.IdxTablespaceSize", default_value="1024M"
                        )
                        self.interactive_add_field_from_pargs_to_data(
                            "itbs_x", sp, "Oracle.IdxTablespaceNext", default_value="32M"
                        )

                    # -lob_tbs # -lob_tbs_size # -lob_tbs_next
                    if self.confirm(msg="Will you create a LOB tablaspace", suffix="[y/n]"):
                        self.interactive_add_field_from_pargs_to_data(
                            "ltbs_n",
                            sp,
                            "Oracle.LobTablespaceName",
                            default_value=sp["Oracle.UserName"] + "_LOB",
                            format=lambda a: str(a).upper(),
                        )
                        self.interactive_add_field_from_pargs_to_data(
                            "ltbs_s", sp, "Oracle.LobTablespaceSize", default_value="2048M"
                        )
                        self.interactive_add_field_from_pargs_to_data(
                            "ltbs_x", sp, "Oracle.LobTablespaceNext", default_value="32M"
                        )
                    data["Nvl_Oracle_Options"].update(sp)

            msg = ""
            keys = [
                "Engine",
                "pwd",
                "keyname",
                "AccountId",
                "DBInstanceIdentifier",
                "DBInstanceClass",
                "DBSubnetGroupName",
                "EngineVersion",
            ]
            for k in keys:
                value = data.get(k)
                if value is not None:
                    msg = msg + "\n" + k + ":\t" + value

            msg = msg + "\n"

            keys = [
                "Oracle.DBName",
                "Oracle.LsnPort",
                "Oracle.ArchMode",
                "Oracle.PartOption",
                "Oracle.CharSet",
                "Oracle.NatCharSet",
                "Oracle.DbfDiskSize",
                "Oracle.RecoDiskSize",
                "Oracle.UserName",
                "Oracle.UserPwd",
                "Oracle.DataTablespaceName",
                "Oracle.DataTablespaceSize",
                "Oracle.DataTablespaceNext",
                "Oracle.IdxTablespaceName",
                "Oracle.IdxTablespaceSize",
                "Oracle.IdxTablespaceNext",
                "Oracle.LobTablespaceName",
                "Oracle.LobTablespaceSize",
                "Oracle.LobTablespaceNext",
            ]
            for k in keys:
                value = data["Nvl_Oracle_Options"].get(k)
                if value is not None:
                    msg = msg + "\n" + k + ":\t" + value
            msg = msg + "\n" + " do you want to confirm current setting and create the dbaas?"
            if self.confirm(msg=msg):
                # self.print_dict(data)
                self.__cmp_post(data)

    @ex(
        help=_("create sqlserver db instance"),
        description=_(
            "This command creates a SQL Server database instance on Nivola Cloud. "
            "It requires the name, account, type, subnet, security group and version "
            "of the instance to be provided as required arguments."
        ),
        example=(
            "beehive bu dbaas db-instances add-sqlserver dbs-datal-c-1s datalineage db.l16.xlarge "
            "Subnet-Rupar36-torino02 SG-DBaaS-COLL 2017 -storage 300 -e <env>"
        ),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("db instance name"), "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (
                    ["type"],
                    {"help": _("db instance type"), "action": "store", "type": str},
                ),
                (
                    ["subnet"],
                    {"help": _("db instance subnet id"), "action": "store", "type": str},
                ),
                (
                    ["sg"],
                    {
                        "help": _("db instance security group id"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["version"],
                    {"help": _("database engine version"), "action": "store", "type": str},
                ),
                (
                    ["-pwd"],
                    {
                        "help": _("db root password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-storage"],
                    {
                        "help": _("data storage capacity in GB"),
                        "action": "store",
                        "type": int,
                        "default": 30,
                    },
                ),
                (
                    ["-keyname"],
                    {
                        "help": _("ssh key name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-kms-domain"],
                    {
                        "help": _("kms domain only if TDE  available"),
                        "dest": "kms_domain",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add_sqlserver(self):
        data = self.__add_common()
        data.update({"Engine": "sqlserver"})
        data.update({"AllocatedStorage": self.app.pargs.storage})
        self.__cmp_post(data)

    @ex(
        help=_("update a db instance"),
        description=_(
            "This command updates a db instance on the Nivola CMP platform. "
            "It requires the db instance id as the first argument to identify which instance to update."
        ),
        example="beehive bu dbaas db-instances update <uuid> -dbi_class db.m4.2xlarge",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
                (
                    ["-dbi_class"],
                    {
                        "help": _("db instance class to set up"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sg_add"],
                    {
                        "help": _("db instance security group id to add"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sg_del"],
                    {
                        "help": _("db instance security group id to remove"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-resize"],
                    {
                        "help": _("new amount of storage (in GiB) to allocate for the db instance"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-extensions_add"],
                    {
                        "help": _(
                            "db extensions to install, e.g. name1:type1,name2:type2,... where type can "
                            "be plugin or component"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def update(self):
        dbi_id = self.app.pargs.instance
        dbi_class = self.app.pargs.dbi_class
        sg_add = self.app.pargs.sg_add
        sg_del = self.app.pargs.sg_del
        allocated_storage = self.app.pargs.resize
        extensions = self.app.pargs.extensions_add
        data = {"DBInstanceIdentifier": dbi_id}
        if dbi_class is not None:
            data.update({"DBInstanceClass": dbi_class})
        if sg_add is not None:
            sg = f"{sg_add}:ADD"
            data.update({"VpcSecurityGroupIds": {"VpcSecurityGroupId": [sg]}})
        elif sg_del is not None:
            sg = f"{sg_del}:DEL"
            data.update({"VpcSecurityGroupIds": {"VpcSecurityGroupId": [sg]}})
        if allocated_storage is not None:
            data.update({"AllocatedStorage": allocated_storage})
        if extensions is not None:
            res = []
            for extension in extensions.split(","):
                extension = extension.strip()
                name, etype = extension.split(":")
                res.append({"Name": name, "Type": etype})
            data.update({"Extensions": res})
        uri = f"{self.baseuri}/databaseservices/instance/modifydbinstance"
        self.cmp_put(uri, data=data, timeout=600).get("ModifyDBInstanceResponse")
        self.wait_for_service(dbi_id)
        self.app.render({"msg": f"update db instance: {dbi_id}"})

    @ex(
        help=_("delete a db instance"),
        description=_(
            "This command deletes a db instance from the Nivola CMP Database as a Service (DBaaS). "
            "It requires the database instance id as the only required argument to identify the instance to delete."
        ),
        example="beehive bu dbaas db-instances delete <uuid> -y",
        arguments=ARGS(
            [
                (
                    ["database"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete(self):
        uuid = self.app.pargs.database
        uri = f"{self.baseuri}/databaseservices/instance/deletedbinstance"

        entity = f"db instance {uuid}"
        self.cmp_delete(uri, data={"DBInstanceIdentifier": uuid}, entity=entity, output=False)
        state = self.wait_for_service(uuid, accepted_state="DELETED")
        if state == "DELETED":
            print(f"{entity} deleted")

    #
    # action
    #
    @ex(
        help=_("start a db instance"),
        description=_(
            "This command starts a db instance that was previously stopped or created. "
            "The required database argument specifies the id of the db instance to start. "
            "Starting a db instance provisions the underlying infrastructure and makes the database available."
        ),
        example="beehive bu dbaas db-instances start dbs-posc-prd-077p -e <env>",
        arguments=ARGS(
            [
                (
                    ["database"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def start(self):
        uuid = self.app.pargs.database
        uri = f"{self.baseuri}/databaseservices/instance/startdbinstance"
        self.cmp_put(uri, data={"DBInstanceIdentifier": uuid})
        self.wait_for_service(uuid)
        self.app.render({"msg": f"start database instance {uuid}"})

    @ex(
        help=_("stop a db instance"),
        description=_(
            "This command stops a database instance by its id. "
            "The required database argument specifies the id of the db instance to stop."
        ),
        example="beehive bu dbaas db-instances stop dbs-posc-tst-075p -e <env>",
        arguments=ARGS(
            [
                (
                    ["database"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def stop(self):
        uuid = self.app.pargs.database
        uri = f"{self.baseuri}/databaseservices/instance/stopdbinstance"
        self.cmp_put(uri, data={"DBInstanceIdentifier": uuid})
        self.wait_for_service(uuid)
        self.app.render({"msg": f"stop database instance {uuid}"})

    @ex(
        help=_("reboot a db instance"),
        description=_(
            "This command reboots a database instance in the Nivola CMP Database as a Service (DBaaS). "
            "The required 'database' argument specifies the unique identifier of the database instance to reboot. "
            "Rebooting a database instance will restart the underlying database server, causing a brief interruption "
            "of service during the reboot process."
        ),
        example="beehive bu dbaas db-instances reboot <uuid>",
        arguments=ARGS(
            [
                (
                    ["database"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def reboot(self):
        uuid = self.app.pargs.database
        uri = f"{self.baseuri}/databaseservices/instance/rebootdbinstance"
        self.cmp_put(uri, data={"DBInstanceIdentifier": uuid})
        self.wait_for_service(uuid)
        self.app.render({"msg": f"reboot database instance {uuid}"})

    #
    # database
    #
    @ex(
        help=_("get db instance databases/schemas"),
        description=_(
            "This command gets the databases/schemas of a given db instance. "
            "It requires the db instance id as the only required argument."
        ),
        example="beehive bu dbaas db-instances database-get <uuid> -e <env>",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def database_get(self):
        uuid = self.app.pargs.instance

        data = {"DBInstanceIdentifier": uuid}
        uri = f"{self.baseuri}/databaseservices/instance/describedbinstanceschema"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True), timeout=60)
        res = dict_get(
            res,
            "DescribeDBInstanceSchemaResponse.DescribeDBInstanceSchemaResult.Schemas",
        )
        self.app.render(
            res,
            headers=[
                "db_name",
                "size",
                "charset",
                "collation",
                "schemas",
                "access_privileges",
            ],
            maxsize=200,
            transform={"schemas": ",".join},
        )

    @ex(
        help=_("create a db instance database/schema"),
        description=_(
            "This command creates a database/schema within a db instance on the Nivola CMP DBaaS platform. "
            "It requires the db instance id, database name and charset as required arguments to "
            "uniquely identify and create the new database."
        ),
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
                (["name"], {"help": _("database name"), "action": "store", "type": str}),
                (
                    ["charset"],
                    {"help": _("database charset"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def database_add(self):
        uuid = self.app.pargs.instance
        name = self.app.pargs.name
        charset = self.app.pargs.charset

        data = {"DBInstanceIdentifier": uuid, "Name": name, "Charset": charset}

        uri = f"{self.baseuri}/databaseservices/instance/createdbinstanceschema"
        self.cmp_post(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": f"add database instance {uuid} db {name}"})

    @ex(
        help=_("delete a db instance database/schema"),
        description=_(
            "This command deletes a database/schema from a Db instance. "
            "It requires the Db instance id and the name of the database "
            "to delete as required arguments."
        ),
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
                (["name"], {"help": _("database name"), "action": "store", "type": str}),
            ]
        ),
    )
    def database_del(self):
        uuid = self.app.pargs.instance
        name = self.app.pargs.name

        data = {"DBInstanceIdentifier": uuid, "Name": name}

        uri = f"{self.baseuri}/databaseservices/instance/deletedbinstanceschema"
        self.cmp_delete(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": f"delete database instance {uuid} db {name}"})

    #
    # user
    #
    @ex(
        help=_("get db instance users"),
        description=_(
            "This command gets the users for a specific database instance. "
            "The 'instance' argument is required and specifies the ID of "
            "the database instance to retrieve users for."
        ),
        example="beehive bu dbaas db-instances user-get <uuid>",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_get(self):
        uuid = self.app.pargs.instance

        data = {"DBInstanceIdentifier": uuid}
        uri = f"{self.baseuri}/databaseservices/instance/describedbinstanceuser"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True), timeout=60)
        res = dict_get(res, "DescribeDBInstanceUserResponse.DescribeDBInstanceUserResult.Users")
        self.app.render(res, headers=["user", "host", "account_locked", "max_connections", "plugin"])

    @ex(
        help=_("create a db instance user"),
        description=_(
            "This command creates a database instance user. "
            "It requires the database instance id, the user name and the user password "
            "as required arguments to add a new user to the specified database instance."
        ),
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
                (["name"], {"help": _("user name"), "action": "store", "type": str}),
                (["pwd"], {"help": _("user password"), "action": "store", "type": str}),
            ]
        ),
    )
    def user_add(self):
        uuid = self.app.pargs.instance
        name = self.app.pargs.name
        pwd = self.app.pargs.pwd

        data = {"DBInstanceIdentifier": uuid, "Name": name, "Password": pwd}

        uri = f"{self.baseuri}/databaseservices/instance/createdbinstanceuser"
        self.cmp_post(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": f"add db instance {uuid} user {name}"})

    @ex(
        help=_("delete a db instance user"),
        description=_(
            "This command deletes a database instance user. "
            "It requires the database instance id and the name "
            "of the user to delete as required arguments. "
            "The instance id identifies the database the user belongs to "
            "and the name specifies which user to delete from that instance."
        ),
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
                (["name"], {"help": _("user name"), "action": "store", "type": str}),
                (
                    ["-force"],
                    {
                        "help": _("force deletion"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
            ]
        ),
    )
    def user_del(self):
        uuid = self.app.pargs.instance
        name = self.app.pargs.name
        force = self.app.pargs.force

        data = {"DBInstanceIdentifier": uuid, "Name": name, "Force": force}

        uri = f"{self.baseuri}/databaseservices/instance/deletedbinstanceuser"
        self.cmp_delete(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": f"delete db instance {uuid} user {name}"})

    @ex(
        help=_("grant db instance user privileges"),
        description=_(
            "This command grants privileges to a database user on a specific "
            "database instance and database. "
            "The required arguments are the instance ID, user name and database name to grant privileges to."
        ),
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
                (["name"], {"help": _("user name"), "action": "store", "type": str}),
                (
                    ["db_name"],
                    {
                        "help": _(
                            "database name. For postgres use db1 to select a database e db1.schema1 to select "
                            "schema schema1 in database db1"
                        ),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["privileges"],
                    {
                        "help": _(
                            "privileges admitted: mysql - SELECT,INSERT,DELETE,UPDATE,ALL, "
                            "postgres db - CONNECT, postgres schema - USAGE,CREATE,ALL"
                        ),
                        "action": "store",
                        "type": str,
                        "default": "ALL",
                    },
                ),
            ]
        ),
    )
    def user_priv_grant(self):
        uuid = self.app.pargs.instance
        name = self.app.pargs.name
        db_name = self.app.pargs.db_name
        privileges = self.app.pargs.privileges

        data = {
            "DBInstanceIdentifier": uuid,
            "UserName": name,
            "DbName": db_name,
            "Privileges": privileges,
        }

        uri = f"{self.baseuri}/databaseservices/instance/grantdbinstanceuserprivileges"
        self.cmp_post(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": f"grant db instance {uuid} user {name} privileges {privileges} to database {db_name}"})

    @ex(
        help=_("revoke db instance user privileges"),
        description=_(
            "This command revokes privileges of a database user on a specific database instance. "
            "The required arguments are the instance id, user name and database name to identify "
            "the user and database uniquely and revoke the privileges."
        ),
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
                (["name"], {"help": _("user name"), "action": "store", "type": str}),
                (
                    ["db_name"],
                    {
                        "help": _(
                            "database name. For postgres use db1 to select a database e db1.schema1 to select "
                            "schema schema1 in database db1"
                        ),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["privileges"],
                    {
                        "help": _(
                            "privileges admitted: mysql - SELECT,INSERT,DELETE,UPDATE,ALL, "
                            "postgres db - CONNECT, postgres schema - USAGE,CREATE,ALL"
                        ),
                        "action": "store",
                        "type": str,
                        "default": "ALL",
                    },
                ),
            ]
        ),
    )
    def user_priv_revoke(self):
        uuid = self.app.pargs.instance
        name = self.app.pargs.name
        db_name = self.app.pargs.db_name
        privileges = self.app.pargs.privileges

        data = {
            "DBInstanceIdentifier": uuid,
            "UserName": name,
            "DbName": db_name,
            "Privileges": privileges,
        }

        uri = f"{self.baseuri}/databaseservices/instance/revokedbinstanceuserprivileges"
        self.cmp_delete(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render(
            {"msg": f"revoke db instance {uuid} user {name} privileges {privileges} from database {db_name}"}
        )

    @ex(
        help=_("change db instance user password"),
        description=_(
            "This command changes the password for a database user in a specific database instance. "
            "It requires the instance id, username and new password as arguments to identify "
            "the user and update the password."
        ),
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
                (["name"], {"help": _("user name"), "action": "store", "type": str}),
                (["pwd"], {"help": _("user password"), "action": "store", "type": str}),
            ]
        ),
    )
    def user_password_set(self):
        uuid = self.app.pargs.instance
        name = self.app.pargs.name
        pwd = self.app.pargs.pwd

        data = {"DBInstanceIdentifier": uuid, "Name": name, "Password": pwd}

        uri = f"{self.baseuri}/databaseservices/instance/changedbinstanceuserpassword"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": f"change db instance {uuid} user {name} password"})

    @ex(
        help=_("enable db instance monitoring"),
        description=_(
            "This command enables monitoring on a specific database instance. "
            "The required 'instance' argument specifies the ID of the database "
            "instance to enable monitoring on. Monitoring collects metrics on "
            "database performance and resource usage to help with troubleshooting and capacity planning."
        ),
        example="beehive bu dbaas db-instances enable-monitoring $NODE",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
                (
                    ["-templates"],
                    {
                        "help": _("templates list"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def enable_monitoring(self):
        dbi_id = self.app.pargs.instance
        templates = self.app.pargs.templates
        data = {"DBInstanceId.N": [dbi_id], "Nvl_Templates": templates}
        uri = f"{self.baseuri}/databaseservices/instance/monitordbinstances"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(dbi_id)
        self.app.render({"msg": f"enable db instance {dbi_id} monitoring"})

    @ex(
        help=_("disable db instance monitoring"),
        description=_(
            "This command disables monitoring for the specified database instance. "
            "Monitoring collects metrics about your database instance's performance "
            "and availability and makes this available in the Nivola CMP console. "
            "Disabling monitoring stops collecting these metrics but can improve "
            "performance for low usage instances."
        ),
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": _("db instance id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def disable_monitoring(self):
        dbi_id = self.app.pargs.instance
        data = {"DBInstanceId.N": [dbi_id]}
        uri = f"{self.baseuri}/databaseservices/instance/unmonitordbinstances"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(dbi_id)
        self.app.render({"msg": f"disable db instance {dbi_id} monitoring"})

    @ex(
        help=_("enable db instance logging"),
        description=_(
            "This command enables logging for the specified database instance. "
            "The 'instance' argument is required and specifies the ID of "
            "the virtual machine instance for which logging needs to be enabled. "
            "Enabling logging allows monitoring and troubleshooting of database operations and queries."
        ),
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": _("virtual machine id"), "action": "store", "type": str},
                ),
                (
                    ["-files"],
                    {
                        "help": _("files list"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-pipeline"],
                    {
                        "help": _("log collector pipeline port"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def enable_logging(self):
        dbi_id = self.app.pargs.instance
        files = self.app.pargs.files
        pipeline = self.app.pargs.pipeline
        data = {"DBInstanceId.N": [dbi_id], "Files": files, "Pipeline": pipeline}
        uri = f"{self.baseuri}/databaseservices/instance/forwardlogdbinstances"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(dbi_id)
        self.app.render({"msg": f"enable db instance {dbi_id} logging"})

    @ex(
        help=_("import a dbaas"),
        description=_(
            "This command imports the dbaas vm into a specified container. "
            "It requires the container ID, VM name, physical VM ID from the provider, "
            " provider image ID, and VM password as required arguments."
        ),
        example="beehive bu dbaas db-instances load Podto1Vsphere esva-procn vm-##### Ubuntu20 esva-procn procn",
        arguments=ARGS(
            [
                (
                    ["container"],
                    {
                        "help": _("container id where import virtual machine. e.g. Podto1Vsphere"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["name"],
                    {"help": _("dbaas name. e.g. dbs-01p"), "action": "store", "type": str},
                ),
                (
                    ["vm"],
                    {
                        "help": _("physical id of the dbaas virtual machine to import"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["vm_pwd"],
                    {
                        "help": _("associated virtual machine password"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["vm_image_id"],
                    {
                        "help": _("name of the vm image of the dbaas. e.g. Postegresql-14.7-vs"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["engine"],
                    {"help": _("dbaas engine"), "action": "store", "type": str},
                ),
                (
                    ["version"],
                    {"help": _("dbaas engine version"), "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {
                        "help": _("parent account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def load(self):
        container_id = self.app.pargs.container
        name = self.app.pargs.name
        ext_id = self.app.pargs.vm
        vm_image_id = self.app.pargs.vm_image_id
        engine = self.app.pargs.engine
        version = self.app.pargs.version
        vm_pwd = self.app.pargs.vm_pwd
        account_id = self.get_account(self.app.pargs.account).get("uuid")

        # register server as resource
        # - get container type
        container = self.api.resource.container.get(container_id).get("resourcecontainer")
        ctype = dict_get(container, "__meta__.definition")

        # - synchronize container
        resclasses = {
            "Openstack": "Openstack.Domain.Project.Server",
            "Vsphere": "Vsphere.DataCenter.Folder.Server",
        }
        resclass = resclasses.get(ctype, None)
        if resclass is not None:
            print(f"importing physical entity {resclass} as resource...")
            self.api.resource.container.synchronize(
                container_id,
                resclass,
                new=True,
                died=False,
                changed=False,
                ext_id=ext_id,
            )
            print(f"imported physical entity {resclass} as resource")

        resclasses = {"Openstack": "Openstack.Domain.Project.Volume", "Vsphere": None}
        resclass = resclasses.get(ctype, None)
        if resclass is not None:
            print(f"importing physical entity {resclass} as resource...")
            self.api.resource.container.synchronize(container_id, resclass, new=True, died=False, changed=False)
            print(f"imported physical entity {resclass} as resource")

        # import physical resource ad provider resource
        # - get resource by ext_id
        physical_resource = self.api.resource.entity.list(ext_id=ext_id).get("resources")[0]["uuid"]

        # - patch resource
        print(f"patch resource {physical_resource}")
        self.api.resource.entity.patch(physical_resource)

        # - import physical resource as provider resource
        from beecell.types.type_id import id_gen

        res_name = f"{name}-{id_gen()}"
        print(f"load resource instance res_name: {res_name}")
        self.api.resource.provider.instance.load(
            "ResourceProvider01",
            res_name,
            physical_resource,
            vm_pwd,
            vm_image_id,
            hostname=name,
        )

        # res_name = "dbs-01p-7be2eec7a4"
        # - get resource
        res = self.api.resource.provider.instance.get(res_name)
        vm_flavor = dict_get(res, "flavor.name")
        provider_vm_id = res["uuid"]

        db_flavor = vm_flavor.replace("vm.", "db.")

        stack_name = f"{name}-stackV2"
        print(f"stack create from vm: {stack_name}")
        stack_uuid = self.api.resource.provider.instance.stack_create_from_vm(
            stack_name, provider_vm_id, " ", engine, version
        )

        # - import service instance
        print(f"load service instance res_name: {stack_name}")
        res = self.api.business.service.instance.load(
            name,
            account_id,
            "DatabaseInstance",
            "DatabaseService",
            stack_uuid,
            service_definition_id=db_flavor,
        )
        print(f"import provider resource as database instance {res}")

    @ex(
        help=_("dev: import a dbaas from vm"),
        description=_("This command imports a standarad vm created on Nivola as a dbaas."),
        example="beehive bu dbaas db-instances vm2dbaas Podto1Vsphere esva-procn vm-##### Ubuntu20 esva-procn procn",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {
                        "help": _("cpaas vm uuid"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["engine"],
                    {"help": _("dbaas engine"), "action": "store", "type": str},
                ),
                (
                    ["version"],
                    {"help": _("dbaas engine version"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def vm2dbaas(self):
        class AccountDict(TypedDict):
            id: int
            uuid: str
            name: str

        class DateDict(TypedDict):
            creation: Optional[str]
            modified: Optional[str]
            expiry: Optional[str]

        class ParentDict(TypedDict):
            uuid: str
            name: str

        class ServInstDict(TypedDict):
            id: int
            uuid: str
            name: str
            desc: str
            active: bool
            date: DateDict
            version: str
            account: AccountDict
            definition_id: str
            definition_name: str
            bpmn_process_id: Optional[str]
            resource_uuid: str
            status: str
            parent: ParentDict
            is_container: bool
            config: dict
            last_error: str
            plugintype: str
            tags: List[str]

        class SgDict(TypedDict):
            uuid: str
            name: str

        class InstFlavorDict(TypedDict):
            disk_iops: int
            vcpus: int
            disk: float
            bandwidth: float
            memory: float
            name: str
            uuid: str

        class InstanceDict(TypedDict):
            id: int
            uuid: str
            name: str
            desc: str
            active: bool
            date: DateDict
            base_state: str
            state: str
            runstate: str
            parent: int
            details: dict
            attributes: dict
            ext_id: Optional[str]
            reuse: bool
            reason: Optional[str]
            childs: int
            container: int
            hypervisor: str
            vpcs: List[dict]
            image: dict
            flavor: InstFlavorDict
            availability_zone: dict
            block_device_mapping: List[dict]
            security_groups: List[SgDict]

        # class InstanceResponse(TypedDict):
        #    instance: InstanceDict

        engine: str = self.app.pargs.engine
        version: str = self.app.pargs.version

        engine_definition: dict = self.api.business.service.definition.get(f"db-engine-{engine}-{version}")
        if engine_definition is None:
            print(f"db-engine-{engine}-{version} do not exist!\n aborting!")
            return
        print(engine_definition)
        print("OK")
        if self.app.pargs.vm is None:
            print("Vm is required!\n aborting!")
            return
        uri = f"/v2.0/nws/serviceinsts/{self.app.pargs.vm}"
        srvinst: ServInstDict = self.cmp_get(uri).get("serviceinst")
        if not srvinst.get("plugintype") == "ComputeInstance":
            print(srvinst.get("plugintype"))
            print("not a ComputeInstance!\n aborting!")
            return
        # vm = srvinst.get("uuid")
        cpinst = srvinst.get("resource_uuid")
        account = srvinst.get("account", {})

        # res_name = "dbs-01p-7be2eec7a4"
        # - get resource
        res_inst: InstanceDict = self.api.resource.provider.instance.get(cpinst)
        vm_flavor = res_inst.get("flavor").get("name")
        # provider_vm_id = res_inst.get("uuid"]
        db_flavor = vm_flavor.replace("vm.", "db.")

        stack_name = f"{srvinst.get('name')}-stackV2"
        print(f"stack create from vm: {stack_name}")
        stack_uuid = self.api.resource.provider.instance.stack_create_from_vm(stack_name, cpinst, " ", engine, version)

        # - import service instance
        print(f"load service instance res_name: {stack_name}")
        res = self.api.business.service.instance.load(
            "imp-" + srvinst.get("name"),
            account.get("uuid"),
            "DatabaseInstance",
            "DatabaseService",
            stack_uuid,
            service_definition_id=db_flavor,
        )
        print(f"import provider resource as database instance {res}")
