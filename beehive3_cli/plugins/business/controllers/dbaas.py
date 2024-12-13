# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beecell.types.type_dict import dict_get, dict_set
from beehive3_cli.core.controller import ARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


class DBaaServiceController(BusinessControllerChild):
    class Meta:
        label = "dbaas"
        description = "database service management"
        help = "database service management"

    @ex(
        help="get database service info",
        description="This command retrieves information about a database service instance. It requires the account ID of the service as the only required argument.",
        example="beehive bu dbaas info <uuid>;beehive bu dbaas info <uuid> -e <env>",
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
        description="This command is used to get database service quotas for a given account id. It requires the account id as the only required argument to retrieve the quotas allocated to that account for database services.",
        example="beehive bu dbaas quotas Acc_demo1_nmsflike -k;beehive bu dbaas quotas Acc_demo1_nmsflike -e <env>",
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
        description="This command is used to retrieve the available database instance types from the Nivola CMP Database as a Service (DBaaS). Database instance types determine the hardware specifications like CPU, memory, storage etc. of the database instance. The command does not require any arguments. The output will list all supported database instance types that can be used while provisioning a new database instance.",
        example="beehive bu dbaas db-instances types -e <env>;beehive bu dbaas db-instances types AIA",
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
        description="This command is used to get database instance engines. It retrieves the engines of database instances from the Nivola CMP Database as a Service (DBaaS). No required arguments.",
        example="beehive bu dbaas db-instances engines sige-preprod;beehive bu dbaas db-instances engines buke",
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
            headers=["engine", "version", "fullVersion", "definition", "description"],
            fields=["engine", "engineVersion", "fullVersion", "definition", "description"],
            key="engineTypesSet",
        )

    @ex(
        help="get database instances",
        description="This command retrieves database instances from the Nivola CMP Database as a Service (DBaaS). It lists out existing database instances without requiring any arguments. The -size and -accounts options allow filtering the results by page size or associated account respectively.",
        example="beehive bu dbaas db-instances list -size 5;beehive bu dbaas db-instances list -accounts MOODLE",
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

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="DescribeDBInstancesResponse.DescribeDBInstancesResult.nvl-DBInstancesTotal",
            key_list_name="DescribeDBInstancesResponse.DescribeDBInstancesResult.DBInstances",
            fn_render=render,
        )

    @ex(
        help="list all db-instance",
        description="This command lists all database instances within a specified range. It requires the 'start' and 'end' arguments to define the lower and upper bounds of the instance IDs range to list instances from.",
        arguments=ARGS(
            [
                (
                    ["start"],
                    {
                        "help": "instances range lower bound",
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["end"],
                    {
                        "help": "instances range upper bound",
                        "action": "store",
                        "type": int,
                    },
                ),
            ]
        ),
    )
    def list_all(self):
        account_d = dict()

        def get_account(account_uuid):
            uri = "%s/accounts/%s" % (self.baseuri, account_uuid)
            res = self.cmp_get(uri)
            res = res.get("account")
            account_name = res.get("name")
            div_uuid = res.get("division_id")
            return account_name, div_uuid

        def get_division(div_uuid):
            uri = "/v1.0/nws/divisions/%s" % div_uuid
            res = self.cmp_get(uri)
            res = res.get("division")
            div_name = res.get("name")
            org_uuid = res.get("organization_id")
            return div_name, org_uuid

        def get_organization(org_uuid):
            uri = "/v1.0/nws/organizations/%s" % org_uuid
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
            uri = "%s/databaseservices/instance/describedbinstances" % self.baseuri
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
                    account_triplet = "%s.%s.%s" % (org_name, div_name, account_name)
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
            "DBInstance.%s" % self.__get_field_id_key(),
            "DBInstance.%s" % self.__get_field_id_name(),
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
        format = self.format
        for page in range(first_page, last_page):
            print("getting db-instances from %s to %s ..." % (page * size + 1, (page + 1) * size))
            try:
                chunk_resp = get_instance(page, size)[0]
                if format == "text":
                    self.app.render(chunk_resp, headers=headers, fields=fields)
                else:
                    resp += chunk_resp
                print("got db-instances from %s to %s" % (page * size + 1, (page + 1) * size))
                # time.sleep(secs)
            except Exception as exc:
                print(exc)
                break
        if format == "json":
            self.app.render(resp, headers=headers, fields=fields)

    @ex(
        help="get database instance",
        description="This command retrieves details of a specific database instance from the Nivola CMP Database as a Service (DBaaS) platform. The 'id' argument is required to identify the database instance being retrieved.",
        example="beehive bu dbaas db-instances get <uuid>;beehive bu dbaas db-instances get <id_Dbinstance>",
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
        description="This command creates a MySQL database instance. It requires the name, account id, type, subnet id, security group id and database engine version as required arguments to uniquely identify and provision the database instance.",
        example="beehive bu dbaas db-instances add-mysql dbs-cmrc-proto-prd-001m cmrc-proto db.m8.xlarge Subnet-Rupar62-torino02 SG-DBAAS 8.0.25-vs;beehive bu dbaas db-instances add-mysql dbs-cmrc-proto-prd-001m cmrc-proto db.m8.xlarge Subnet-Rupar62-torino02 SG-DBAAS 8.0.25-vs",
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
        help="create MariaDB db instance",
        description="This command creates a MariaDB database instance on Nivola Cloud. It requires the name, account ID, type, subnet ID, security group ID and version of the database to be specified as required arguments.",
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
    def add_mariadb(self):
        data = self.__add_common()
        data.update({"Engine": "mariadb"})
        data.update({"AllocatedStorage": self.app.pargs.storage})

        self.__cmp_post(data)

    # @ex(
    #     help="create postgresql db instance",
    #     description="This command creates a PostgreSQL database instance. It requires the name, account id, type, subnet id, security group id and version of the database as required arguments to uniquely identify and provision the instance.",
    #     example="beehive bu dbaas db-instances add-postgresql dbs-cloudera-prd-002p cloudera db.m4.large <uuid> SG-DBAAS-PROD 12.4 -storage 50 -e <env>;beehive bu dbaas db-instances add-postgresql pg154-01 Felice db.m2.medium SubnetBE-torino01 SG-BE-CB 15.4-vs",
    #     arguments=ARGS(
    #         [
    #             (
    #                 ["name"],
    #                 {"help": "db instance name", "action": "store", "type": str},
    #             ),
    #             (
    #                 ["account"],
    #                 {"help": "parent account id", "action": "store", "type": str},
    #             ),
    #             (
    #                 ["type"],
    #                 {"help": "db instance type", "action": "store", "type": str},
    #             ),
    #             (
    #                 ["subnet"],
    #                 {"help": "db instance subnet id", "action": "store", "type": str},
    #             ),
    #             (
    #                 ["sg"],
    #                 {
    #                     "help": "db instance security group id",
    #                     "action": "store",
    #                     "type": str,
    #                 },
    #             ),
    #             (
    #                 ["version"],
    #                 {"help": "database engine version", "action": "store", "type": str},
    #             ),
    #             (
    #                 ["-storage"],
    #                 {
    #                     "help": "amount of storage [GB] to allocate for the DB instance",
    #                     "action": "store",
    #                     "type": int,
    #                     "default": 30,
    #                 },
    #             ),
    #             (
    #                 ["-pwd"],
    #                 {
    #                     "help": "db root password",
    #                     "action": "store",
    #                     "type": str,
    #                     "default": None,
    #                 },
    #             ),
    #             (
    #                 ["-keyname"],
    #                 {
    #                     "help": "ssh key name",
    #                     "action": "store",
    #                     "type": str,
    #                     "default": None,
    #                 },
    #             ),
    #             (
    #                 ["-postgis"],
    #                 {
    #                     "help": "spatial database extension",
    #                     "action": "store",
    #                     "type": str,
    #                     "default": None,
    #                 },
    #             ),
    #         ]
    #     ),
    # )
    # def add_postgresql(self):
    #     data = self.__add_common()
    #     data.update({"Engine": "postgresql"})
    #     data.update({"AllocatedStorage": self.app.pargs.storage})

    #     d = {}
    #     self.add_field_from_pargs_to_data("postgis", d, "Postgresql.GeoExtension")
    #     if d:
    #         data["Nvl_Postgresql_Options"] = {}
    #         data["Nvl_Postgresql_Options"].update(d)

    #     self.__cmp_post(data)

    @ex(
        help="create postgresql db instance",
        description="This command creates a PostgreSQL database instance. It requires the name, account id, type, subnet id, security group id and version of the database as required arguments to uniquely identify and provision the instance.",
        example="beehive bu dbaas db-instances add-postgresql dbs-cloudera-prd-002p cloudera db.m4.large <uuid> SG-DBAAS-PROD 12.4 -storage 50 -e <env>;beehive bu dbaas db-instances add-postgresql pg154-01 Felice db.m2.medium SubnetBE-torino01 SG-BE-CB 15.4-vs",
        arguments=ARGS(
            [
                # (
                #     ["-postgis"],
                #     {
                #         "help": "spatial database extension",
                #         "action": "store",
                #         "type": str,
                #         "default": None,
                #     },
                # ),
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
                    ["-db-name"],
                    {
                        "type": str,
                        "action": "store",
                        "dest": "db_name",
                        "default": None,
                        "required": False,
                        "help": "Database name",
                    },
                ),
                (["-encoding"], {"type": str, "action": "store", "default": "UTF-8", "help": "Database Encoding"}),
                (
                    ["-lc-collate"],
                    {
                        "type": str,
                        "action": "store",
                        "default": "en_US.UTF-8",
                        "help": "Database Collate",
                    },
                ),
                (
                    ["-lc-ctype"],
                    {
                        "type": str,
                        "action": "store",
                        "default": "en_US.UTF-8",
                        "required": False,
                        "help": "Database Ctype",
                    },
                ),
                (
                    ["-user-name"],
                    {"type": str, "dest": "role_name", "action": "store", "required": False, "help": "Role name"},
                ),
                (
                    ["-user-password"],
                    {
                        "type": str,
                        "action": "store",
                        "dest": "role_password",
                        "required": False,
                        "help": "Role password",
                    },
                ),
                (
                    ["-schema-name"],
                    {"type": str, "action": "store", "dest": "schema_name", "required": False, "help": "Schema name"},
                ),
                (
                    ["--pgcrypto"],
                    {
                        "help": "activate pgcrypto Postgresql extension",
                        "action": "append_const",
                        "dest": "pg_extensions",
                        "const": "pgcrypto",
                    },
                ),
                (
                    ["--orafce"],
                    {
                        "help": "activate orafce Postgresql extension",
                        "action": "append_const",
                        "dest": "pg_extensions",
                        "const": "orafce",
                    },
                ),
                (
                    ["--tablefunc"],
                    {
                        "help": "activate tablefunc Postgresql extension",
                        "action": "append_const",
                        "dest": "pg_extensions",
                        "const": "tablefunc",
                    },
                ),
                (
                    ["--uuid-ossp"],
                    {
                        "help": "activate uuid Postgresql extension",
                        "action": "append_const",
                        "dest": "pg_extensions",
                        "const": "uuid-ossp",
                    },
                ),
                (
                    ["--postgis"],
                    {
                        "help": "activate postgis Postgresql extension",
                        "action": "append_const",
                        "dest": "pg_extensions",
                        "const": "postgis",
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
        help="create oracle db instance",
        description="This CLI command creates an Oracle database instance on Nivola Cloud. It requires the name, account id, type, subnet id, security group id and version of the database as required arguments. The database instance type can be db.m2.2xlarge for example. It creates the instance in the specified subnet and associates the provided security group to it. The database version could be 12EE for Oracle 12c Enterprise Edition for instance.",
        example="beehive bu dbaas db-instances add-oracle;beehive bu dbaas db-instances add-oracle dbs-screen-prd-001o screen db.m2.2xlarge SubnetBE-torino01 SG-DBaaS 12EE -dbname SCREEN -charset WE8ISO8859P1 -dbfdisksize 500 -recodisksize 500 -e <env>",
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
        description="This command creates a SQL Server database instance on Nivola Cloud. It requires the name, account, type, subnet, security group and version of the instance to be provided as required arguments.",
        example="beehive bu dbaas db-instances add-sqlserver dbs-datal-c-1s datalineage db.l16.xlarge Subnet-Rupar36-torino02 SG-DBaaS-COLL 2017 -storage 300 -e <env>;beehive bu dbaas db-instances add-sqlserver dbs-ires-p01s zucchetti db.m4.large Subnet-Rupar71-torino01 SG-ZUCCHETTI-DBAAS 2017-vs -storage 100",
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
        data.update({"AllocatedStorage": self.app.pargs.storage})
        self.__cmp_post(data)

    @ex(
        help="update a db instance",
        description="This command updates a db instance on the Nivola CMP platform. It requires the db instance id as the first argument to identify which instance to update.",
        example="beehive bu dbaas db-instances update -dbi_class db.m4.2xlarge <uuid>;beehive bu dbaas db-instances update <uuid> -dbi_class db.m4.2xlarge",
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
        description="This command deletes a db instance from the Nivola CMP Database as a Service (DBaaS). It requires the database instance id as the only required argument to identify the instance to delete.",
        example="beehive bu dbaas db-instances delete <uuid> -e <env>;beehive bu dbaas db-instances delete <uuid> -y",
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
        description="This command starts a db instance that was previously stopped or created. The required database argument specifies the id of the db instance to start. Starting a db instance provisions the underlying infrastructure and makes the database available.",
        example="beehive bu dbaas db-instances start dbs-posc-prd-077p -e <env>",
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
        description="This command stops a database instance by its id. The required database argument specifies the id of the db instance to stop.",
        example="beehive bu dbaas db-instances stop dbs-posc-prd-077p -e <env>;beehive bu dbaas db-instances stop dbs-posc-tst-075p -e <env>",
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
        description="This command reboots a database instance in the Nivola CMP Database as a Service (DBaaS). The required 'database' argument specifies the unique identifier of the database instance to reboot. Rebooting a database instance will restart the underlying database server, causing a brief interruption of service during the reboot process.",
        example="beehive bu dbaas db-instances reboot <uuid>;beehive bu dbaas db-instances reboot <uuid>",
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
        description="This command gets the databases/schemas of a given db instance. It requires the db instance id as the only required argument.",
        example="beehive bu dbaas db-instances database-get <uuid> -e <env>;beehive bu dbaas db-instances database-get <uuid> -e <env>",
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
        description="This command creates a database/schema within a db instance on the Nivola CMP DBaaS platform. It requires the db instance id, database name and charset as required arguments to uniquely identify and create the new database.",
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
        description="This command deletes a database/schema from a Db instance. It requires the Db instance id and the name of the database to delete as required arguments.",
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
        description="This command gets the users for a specific database instance. The 'instance' argument is required and specifies the ID of the database instance to retrieve users for.",
        example="beehive bu dbaas db-instances user-get <uuid>",
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
        description="This command creates a database instance user. It requires the database instance id, the user name and the user password as required arguments to add a new user to the specified database instance.",
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
        description="This command deletes a database instance user. It requires the database instance id and the name of the user to delete as required arguments. The instance id identifies the database the user belongs to and the name specifies which user to delete from that instance.",
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
        description="This command grants privileges to a database user on a specific database instance and database. The required arguments are the instance ID, user name and database name to grant privileges to.",
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
        description="This command revokes privileges of a database user on a specific database instance. The required arguments are the instance id, user name and database name to identify the user and database uniquely and revoke the privileges.",
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
        description="This command changes the password for a database user in a specific database instance. It requires the instance id, username and new password as arguments to identify the user and update the password.",
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
        description="This command enables monitoring on a specific database instance. The required 'instance' argument specifies the ID of the database instance to enable monitoring on. Monitoring collects metrics on database performance and resource usage to help with troubleshooting and capacity planning.",
        example="beehive bu dbaas db-instances enable-monitoring $NODE",
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
        description="This command disables monitoring for the specified database instance. Monitoring collects metrics about your database instance's performance and availability and makes this available in the Nivola CMP console. Disabling monitoring stops collecting these metrics but can improve performance for low usage instances.",
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
        description="This command enables logging for the specified database instance. The 'instance' argument is required and specifies the ID of the virtual machine instance for which logging needs to be enabled. Enabling logging allows monitoring and troubleshooting of database operations and queries.",
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

    @ex(
        help="import a dbaas",
        description="This command imports the dbaas vm into a specified container. It requires the container ID, VM name, physical VM ID from the provider, provider image ID, and VM password as required arguments.",
        example="beehive bu dbaas db-instances load Podto1Vsphere esva-procn vm-##### Ubuntu20 esva-procn procn;beehive bu cpaas vms load Podto1Vsphere esva-procn vm-##### Ubuntu20 esva-procn procn",
        arguments=ARGS(
            [
                (
                    ["container"],
                    {
                        "help": "container id where import virtual machine. e.g. Podto1Vsphere",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["name"],
                    {"help": "dbaas name. e.g. dbs-01p", "action": "store", "type": str},
                ),
                (
                    ["vm"],
                    {
                        "help": "physical id of the dbaas virtual machine to import",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["vm_pwd"],
                    {
                        "help": "associated virtual machine password",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["vm_image_id"],
                    {
                        "help": "name of the vm image of the dbaas. e.g. Postegresql-14.7-vs",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["engine"],
                    {"help": "dbaas engine", "action": "store", "type": str},
                ),
                (
                    ["version"],
                    {"help": "dbaas engine version", "action": "store", "type": str},
                ),
                # (
                #    ["sql_admin_pwd"],
                #    {
                #        "help": "",
                #        "action":"store",
                #        "type": str,
                #    },
                # ),
                (
                    ["account"],
                    {
                        "help": "parent account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                # (['-type'], {'help': 'virtual machine type', 'action': 'store', 'type': str, 'default': None}),
                # (['-subnet'], {'help': 'virtual machine subnet id', 'action': 'store', 'type': str, 'default': None}),
                # (['-sg'], {'help': 'virtual machine security group id', 'action': 'store', 'type': str, 'default': None}),
                #
                # (['-pwd'], {'help': 'virtual machine admin/root password', 'action': 'store', 'type': str,
                #             'default': None}),
                # (['-multi-avz'], {'help': 'if set to False create vm to work only in the selected availability zone '
                #                           '[default=True]. Use when subnet cidr is public', 'action': 'store', 'type': str,
                #                   'default': True}),
                # (['-meta'], {'help': 'virtual machine custom metadata', 'action': 'store', 'type': str, 'default': None}),
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
            print("importing physical entity %s as resource..." % resclass)
            self.api.resource.container.synchronize(
                container_id,
                resclass,
                new=True,
                died=False,
                changed=False,
                ext_id=ext_id,
            )
            print("imported physical entity %s as resource" % resclass)

        resclasses = {"Openstack": "Openstack.Domain.Project.Volume", "Vsphere": None}
        resclass = resclasses.get(ctype, None)
        if resclass is not None:
            print("importing physical entity %s as resource..." % resclass)
            self.api.resource.container.synchronize(container_id, resclass, new=True, died=False, changed=False)
            print("imported physical entity %s as resource" % resclass)

        # import physical resource ad provider resource
        # - get resource by ext_id
        physical_resource = self.api.resource.entity.list(ext_id=ext_id).get("resources")[0]["uuid"]

        # - patch resource
        print("patch resource %s" % physical_resource)
        self.api.resource.entity.patch(physical_resource)

        # - import physical resource as provider resource
        from beecell.types.type_id import id_gen

        res_name = "%s-%s" % (name, id_gen())
        print("load resource instance res_name: %s" % res_name)
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
        print("stack create from vm: %s" % stack_name)
        stack_uuid = self.api.resource.provider.instance.stack_create_from_vm(
            stack_name, provider_vm_id, " ", engine, version
        )

        # - import service instance
        print("load service instance res_name: %s" % stack_name)
        res = self.api.business.service.instance.load(
            name,
            account_id,
            "DatabaseInstance",
            "DatabaseService",
            stack_uuid,
            service_definition_id=db_flavor,
        )
        print("import provider resource as database instance %s" % res)
