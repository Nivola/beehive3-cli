# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import ARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


class DBaaServiceController(BusinessControllerChild):
    class Meta:
        label = "dbaas"
        description = "database service management"
        help = "database service management"

    @ex(
        help="get database service info",
        description="get database service info",
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
        uri = "%s/databaseservices" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, "DescribeDatabaseResponse.databaseSet.0")
        self.app.render(res, details=True, maxsize=100)

    @ex(
        help="get database service quotas",
        description="get database service quotas",
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
        uri = "%s/databaseservices/describeaccountattributes" % self.baseuri
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
        description = "database instance service management"
        help = "database instance service management"

        cmp = {"baseuri": "/v2.0/nws", "subsystem": "service"}
        # cmp = {'baseuri': '/v1.0/nws', 'subsystem': 'service'}

    def __get_instance_id_key(self):
        if self._meta.cmp["baseuri"].find("v1.0") > 0:
            return "db-instance-id"
        elif self._meta.cmp["baseuri"].find("v2.0") > 0:
            return "db-instance-id"

    def __get_field_id_key(self):
        if self._meta.cmp["baseuri"].find("v1.0") > 0:
            return "DBInstanceIdentifier"
        elif self._meta.cmp["baseuri"].find("v2.0") > 0:
            return "DbiResourceId"

    def __get_field_id_name(self):
        if self._meta.cmp["baseuri"].find("v1.0") > 0:
            return "nvl-name"
        elif self._meta.cmp["baseuri"].find("v2.0") > 0:
            return "DBInstanceIdentifier"

    def __exist(self, instance):
        data = {"%s.N" % self.__get_instance_id_key(): instance}
        uri = "%s/databaseservices/instance/describedbinstances" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = res.get("DescribeDBInstancesResponse").get("DescribeDBInstancesResult")
        if len(res.get("DBInstances")) > 0:
            resp = res.get("DBInstances")[0]
            return True
        return False

    @ex(
        help="get database instance types",
        description="get database instance types",
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
        help="get database instance engines",
        description="get database instance engines",
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
    def engines(self):
        data = {"owner-id": self.get_account(self.app.pargs.account)["uuid"]}
        uri = "/v2.0/nws/databaseservices/instance/enginetypes"
        res = self.cmp_get(uri, data=data).get("DescribeDBInstanceEngineTypesResponse")
        self.app.render(
            res,
            headers=["engine", "version"],
            fields=["engine", "engineVersion"],
            key="engineTypesSet",
        )

    @ex(
        help="get database instances",
        description="get database instances",
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
                        "help": "list of db instance id comma separated",
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
            "ids": "%s.N" % self.__get_instance_id_key(),
            "tags": "Nvl-tag-key.N",
            "size": "MaxRecords",
            "page": "Marker",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/databaseservices/instance/describedbinstances" % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeDBInstancesResponse").get("DescribeDBInstancesResult")
        page = self.app.pargs.page
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
        ]
        fields = [
            "DBInstance.%s" % self.__get_field_id_key(),
            "DBInstance.%s" % self.__get_field_id_name(),
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

    @ex(
        help="get database instance",
        description="get database instance",
        arguments=ARGS(
            [
                (["id"], {"help": "database id", "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {"%s.N" % self.__get_instance_id_key(): [oid]}
        elif self.is_name(oid):
            data = {"DBInstanceIdentifier": oid}
        uri = "%s/databaseservices/instance/describedbinstances" % self.baseuri
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
                network["subnet"] = "%s - %s" % (
                    dict_get(subnet, "Subnets.0.SubnetIdentifier"),
                    subnet.get("DBSubnetGroupName", None),
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
            raise Exception("db-instance %s was not found" % oid)

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

        self.add_field_from_pargs_to_data("pwd", data, "MasterUserPassword")
        self.add_field_from_pargs_to_data("keyname", data, "Nvl_KeyName")

        return data

    def __cmp_post(self, data):
        uri = "%s/databaseservices/instance/createdbinstance" % self.baseuri
        res = self.cmp_post(uri, data={"dbinstance": data}, timeout=600)
        uuid = dict_get(
            res,
            "CreateDBInstanceResponse.CreateDBInstanceResult.DBInstance.DBInstanceIdentifier",
        )
        self.wait_for_service(uuid)
        self.app.render({"msg": "Add database instance %s" % uuid})

    @ex(
        help="create mysql db instance",
        description="create mysql db instance",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "db instance name", "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["type"],
                    {"help": "db instance type", "action": "store", "type": str},
                ),
                (
                    ["subnet"],
                    {"help": "db instance subnet id", "action": "store", "type": str},
                ),
                (
                    ["sg"],
                    {
                        "help": "db instance security group id",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["version"],
                    {"help": "database engine version", "action": "store", "type": str},
                ),
                (
                    ["-pwd"],
                    {
                        "help": "db root password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-storage"],
                    {
                        "help": "data storage capacity in GB",
                        "action": "store",
                        "type": int,
                        "default": 30,
                    },
                ),
                (
                    ["-keyname"],
                    {
                        "help": "ssh key name",
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
        help="create postgresql db instance",
        description="create postgresql db instance",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "db instance name", "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["type"],
                    {"help": "db instance type", "action": "store", "type": str},
                ),
                (
                    ["subnet"],
                    {"help": "db instance subnet id", "action": "store", "type": str},
                ),
                (
                    ["sg"],
                    {
                        "help": "db instance security group id",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["version"],
                    {"help": "database engine version", "action": "store", "type": str},
                ),
                (
                    ["-storage"],
                    {
                        "help": "amount of storage [GB] to allocate for the DB instance",
                        "action": "store",
                        "type": int,
                        "default": 30,
                    },
                ),
                (
                    ["-pwd"],
                    {
                        "help": "db root password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-keyname"],
                    {
                        "help": "ssh key name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-postgis"],
                    {
                        "help": "spatial database extension",
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

        d = {}
        self.add_field_from_pargs_to_data("postgis", d, "Postgresql.GeoExtension")
        if d:
            data["Nvl_Postgresql_Options"] = {}
            data["Nvl_Postgresql_Options"].update(d)

        self.__cmp_post(data)

    @ex(
        help="create oracle db instance",
        description="create oracle db instance",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "db instance name", "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["type"],
                    {"help": "db instance type", "action": "store", "type": str},
                ),
                (
                    ["subnet"],
                    {"help": "db instance subnet id", "action": "store", "type": str},
                ),
                (
                    ["sg"],
                    {
                        "help": "db instance security group id",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["version"],
                    {"help": "database engine version", "action": "store", "type": str},
                ),
                (
                    ["-pwd"],
                    {
                        "help": "db root password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-keyname"],
                    {
                        "help": "ssh key name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dbname"],
                    {
                        "help": "db name [default: ORCL0]",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-lsnport"],
                    {
                        "help": "listener port [default: 1521]",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-archmode"],
                    {
                        "help": "archivelog mode Y/N [default: Y]",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-partopt"],
                    {
                        "help": "partitioning option Y/N [default: Y]",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-charset"],
                    {
                        "help": "character set [default: WE8ISO8859P1]",
                        "action": "store",
                        "type": str,
                        "default": "WE8ISO8859P1",
                    },
                ),
                (
                    ["-natcharset"],
                    {
                        "help": "national charset [default: AL16UTF16]",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dbfdisksize"],
                    {
                        "help": "datafiles disk size in GB [default: 30]",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-recodisksize"],
                    {
                        "help": "recovery disk size in GB [default: 20]",
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

        self.__cmp_post(data)

    @ex(
        help="create sqlserver db instance",
        description="create sqlserver db instance",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "db instance name", "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["type"],
                    {"help": "db instance type", "action": "store", "type": str},
                ),
                (
                    ["subnet"],
                    {"help": "db instance subnet id", "action": "store", "type": str},
                ),
                (
                    ["sg"],
                    {
                        "help": "db instance security group id",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["version"],
                    {"help": "database engine version", "action": "store", "type": str},
                ),
                (
                    ["-pwd"],
                    {
                        "help": "db root password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-storage"],
                    {
                        "help": "data storage capacity in GB",
                        "action": "store",
                        "type": int,
                        "default": 30,
                    },
                ),
                (
                    ["-keyname"],
                    {
                        "help": "ssh key name",
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
        self.__cmp_post(data)

    @ex(
        help="update a db instance",
        description="update a db instance",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
                (
                    ["-dbi_class"],
                    {
                        "help": "db instance class to set up",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sg_add"],
                    {
                        "help": "db instance security group id to add",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sg_del"],
                    {
                        "help": "db instance security group id to remove",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-resize"],
                    {
                        "help": "new amount of storage (in GiB) to allocate for the db instance",
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-extensions_add"],
                    {
                        "help": "db extensions to install, e.g. name1:type1,name2:type2,... where type can "
                        "be plugin or component",
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
            sg = "%s:ADD" % sg_add
            data.update({"VpcSecurityGroupIds": {"VpcSecurityGroupId": [sg]}})
        elif sg_del is not None:
            sg = "%s:DEL" % sg_del
            data.update({"VpcSecurityGroupIds": {"VpcSecurityGroupId": [sg]}})
        if allocated_storage is not None:
            data.update({"AllocatedStorage": allocated_storage})
        if extensions is not None:
            res = []
            for extension in extensions.split(","):
                extension = extension.strip()
                name, type = extension.split(":")
                res.append({"Name": name, "Type": type})
            data.update({"Extensions": res})
        uri = "%s/databaseservices/instance/modifydbinstance" % self.baseuri
        self.cmp_put(uri, data=data, timeout=600).get("ModifyDBInstanceResponse")
        self.wait_for_service(dbi_id)
        self.app.render({"msg": "update db instance: %s" % dbi_id})

    @ex(
        help="delete a db instance",
        description="delete a db instance",
        arguments=ARGS(
            [
                (
                    ["database"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete(self):
        uuid = self.app.pargs.database
        uri = "%s/databaseservices/instance/deletedbinstance" % self.baseuri

        entity = "db instance %s" % uuid
        self.cmp_delete(uri, data={"DBInstanceIdentifier": uuid}, entity=entity, output=False)
        state = self.wait_for_service(uuid, accepted_state="DELETED")
        if state == "DELETED":
            print("%s deleted" % entity)

    #
    # action
    #
    @ex(
        help="start a db instance",
        description="stop a db instance",
        arguments=ARGS(
            [
                (
                    ["database"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def start(self):
        uuid = self.app.pargs.database
        uri = "%s/databaseservices/instance/startdbinstance" % self.baseuri
        self.cmp_put(uri, data={"DBInstanceIdentifier": uuid})
        self.wait_for_service(uuid)
        self.app.render({"msg": "start database instance %s" % uuid})

    @ex(
        help="stop a db instance",
        description="stop a db instance",
        arguments=ARGS(
            [
                (
                    ["database"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def stop(self):
        uuid = self.app.pargs.database
        uri = "%s/databaseservices/instance/stopdbinstance" % self.baseuri
        self.cmp_put(uri, data={"DBInstanceIdentifier": uuid})
        self.wait_for_service(uuid)
        self.app.render({"msg": "stop database instance %s" % uuid})

    @ex(
        help="reboot a db instance",
        description="reboot a db instance",
        arguments=ARGS(
            [
                (
                    ["database"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def reboot(self):
        uuid = self.app.pargs.database
        uri = "%s/databaseservices/instance/rebootdbinstance" % self.baseuri
        self.cmp_put(uri, data={"DBInstanceIdentifier": uuid})
        self.wait_for_service(uuid)
        self.app.render({"msg": "reboot database instance %s" % uuid})

    #
    # database
    #
    @ex(
        help="get db instance databases/schemas",
        description="get db instance databases/schemas",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def database_get(self):
        uuid = self.app.pargs.instance

        data = {"DBInstanceIdentifier": uuid}
        uri = "%s/databaseservices/instance/describedbinstanceschema" % self.baseuri
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
            transform={"schemas": lambda x: ",".join(x)},
        )

    @ex(
        help="create a db instance database/schema",
        description="create a db instance database/schema",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
                (["name"], {"help": "database name", "action": "store", "type": str}),
                (
                    ["charset"],
                    {"help": "database charset", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def database_add(self):
        uuid = self.app.pargs.instance
        name = self.app.pargs.name
        charset = self.app.pargs.charset

        data = {"DBInstanceIdentifier": uuid, "Name": name, "Charset": charset}

        uri = "%s/databaseservices/instance/createdbinstanceschema" % self.baseuri
        self.cmp_post(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": "add database instance %s db %s" % (uuid, name)})

    @ex(
        help="delete a db instance database/schema",
        description="delete a db instance database/schema",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
                (["name"], {"help": "database name", "action": "store", "type": str}),
            ]
        ),
    )
    def database_del(self):
        uuid = self.app.pargs.instance
        name = self.app.pargs.name

        data = {"DBInstanceIdentifier": uuid, "Name": name}

        uri = "%s/databaseservices/instance/deletedbinstanceschema" % self.baseuri
        self.cmp_delete(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": "delete database instance %s db %s" % (uuid, name)})

    #
    # user
    #
    @ex(
        help="get db instance users",
        description="get db instance users",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_get(self):
        uuid = self.app.pargs.instance

        data = {"DBInstanceIdentifier": uuid}
        uri = "%s/databaseservices/instance/describedbinstanceuser" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True), timeout=60)
        res = dict_get(res, "DescribeDBInstanceUserResponse.DescribeDBInstanceUserResult.Users")
        self.app.render(res, headers=["user", "host", "account_locked", "max_connections", "plugin"])

    @ex(
        help="create a db instance user",
        description="create a db instance user",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
                (["name"], {"help": "user name", "action": "store", "type": str}),
                (["pwd"], {"help": "user password", "action": "store", "type": str}),
            ]
        ),
    )
    def user_add(self):
        uuid = self.app.pargs.instance
        name = self.app.pargs.name
        pwd = self.app.pargs.pwd

        data = {"DBInstanceIdentifier": uuid, "Name": name, "Password": pwd}

        uri = "%s/databaseservices/instance/createdbinstanceuser" % self.baseuri
        self.cmp_post(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": "add db instance %s user %s" % (uuid, name)})

    @ex(
        help="delete a db instance user",
        description="delete a db instance user",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
                (["name"], {"help": "user name", "action": "store", "type": str}),
                (
                    ["-force"],
                    {
                        "help": "force deletion",
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

        uri = "%s/databaseservices/instance/deletedbinstanceuser" % self.baseuri
        self.cmp_delete(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": "delete db instance %s user %s" % (uuid, name)})

    @ex(
        help="grant db instance user privileges",
        description="grant db instance user privileges",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
                (["name"], {"help": "user name", "action": "store", "type": str}),
                (
                    ["db_name"],
                    {
                        "help": "database name. For postgres use db1 to select a database e db1.schema1 to select "
                        "schema schema1 in database db1",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["privileges"],
                    {
                        "help": "privileges admitted: mysql - SELECT,INSERT,DELETE,UPDATE,ALL, "
                        "postgres db - CONNECT, postgres schema - USAGE,CREATE,ALL",
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

        uri = "%s/databaseservices/instance/grantdbinstanceuserprivileges" % self.baseuri
        self.cmp_post(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render(
            {"msg": "grant db instance %s user %s privileges %s to database %s" % (uuid, name, privileges, db_name)}
        )

    @ex(
        help="revoke db instance user privileges",
        description="revoke db instance user privileges",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
                (["name"], {"help": "user name", "action": "store", "type": str}),
                (
                    ["db_name"],
                    {
                        "help": "database name. For postgres use db1 to select a database e db1.schema1 to select "
                        "schema schema1 in database db1",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["privileges"],
                    {
                        "help": "privileges admitted: mysql - SELECT,INSERT,DELETE,UPDATE,ALL, "
                        "postgres db - CONNECT, postgres schema - USAGE,CREATE,ALL",
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

        uri = "%s/databaseservices/instance/revokedbinstanceuserprivileges" % self.baseuri
        self.cmp_delete(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render(
            {"msg": "revoke db instance %s user %s privileges %s from database %s" % (uuid, name, privileges, db_name)}
        )

    @ex(
        help="change db instance user password",
        description="change db instance user password",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
                (["name"], {"help": "user name", "action": "store", "type": str}),
                (["pwd"], {"help": "user password", "action": "store", "type": str}),
            ]
        ),
    )
    def user_password_set(self):
        uuid = self.app.pargs.instance
        name = self.app.pargs.name
        pwd = self.app.pargs.pwd

        data = {"DBInstanceIdentifier": uuid, "Name": name, "Password": pwd}

        uri = "%s/databaseservices/instance/changedbinstanceuserpassword" % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(uuid)
        self.app.render({"msg": "change db instance %s user %s password" % (uuid, name)})

    @ex(
        help="enable db instance monitoring",
        description="enable db instance monitoring",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
                (
                    ["-templates"],
                    {
                        "help": "templates list",
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
        uri = "%s/databaseservices/instance/monitordbinstances" % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(dbi_id)
        self.app.render({"msg": "enable db instance %s monitoring" % dbi_id})

    @ex(
        help="disable db instance monitoring",
        description="disable db instance monitoring",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": "db instance id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def disable_monitoring(self):
        dbi_id = self.app.pargs.instance
        data = {"DBInstanceId.N": [dbi_id]}
        uri = "%s/databaseservices/instance/unmonitordbinstances" % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(dbi_id)
        self.app.render({"msg": "disable db instance %s monitoring" % dbi_id})

    @ex(
        help="enable db instance logging",
        description="enable db instance logging",
        arguments=ARGS(
            [
                (
                    ["instance"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["-files"],
                    {
                        "help": "files list",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-pipeline"],
                    {
                        "help": "log collector pipeline port",
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
        uri = "%s/databaseservices/instance/forwardlogdbinstances" % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(dbi_id)
        self.app.render({"msg": "enable db instance %s logging" % dbi_id})
