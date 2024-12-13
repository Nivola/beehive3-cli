# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import ARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


class STaaServiceController(BusinessControllerChild):
    class Meta:
        label = "staas"
        description = "storage service management"
        help = "storage service management"

    @ex(
        help="get storage service info",
        description="This command retrieves information about a storage service instance. It requires the account ID as a required argument to identify the specific storage service instance. The command displays details like the account ID, name, status and other metadata.",
        example="beehive bu staas info <uuid> -e <env>;beehive bu staas info <uuid> -e <env>",
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
        uri = "%s/storageservices" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data))
        res = dict_get(res, "DescribeStorageResponse.storageSet.0")
        self.app.render(res, details=True, maxsize=100)

    @ex(
        help="get storage service quotas",
        description="This command gets the storage service quotas for a given account id. The required 'account' argument specifies the account id to retrieve quotas for.",
        example="beehive bu staas quotas account <uuid>;beehive bu staas quotas get account <uuid>",
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
        uri = "%s/storageservices/describeaccountattributes" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data))
        res = dict_get(res, "DescribeAccountAttributesResponse.accountAttributeSet")
        headers = ["name", "value", "used"]
        fields = [
            "attributeName",
            "attributeValueSet.0.item.attributeValue",
            "attributeValueSet.0.item.nvl-attributeUsed",
        ]
        self.app.render(res, headers=headers, fields=fields)


class STaaServiceEfsController(BusinessControllerChild):
    class Meta:
        stacked_on = "staas"
        stacked_type = "nested"
        label = "efs"
        description = "file share service management"
        help = "file share service management"

    @ex(
        help="get share types",
        description="This command is used to retrieve the available share types for Nivola CMP Storage as a Service (STaaS) Elastic File System (EFS). Share types determine things like performance and storage capacity. By listing the available types, you can choose the appropriate one for your needs when creating a new EFS.",
        example="beehive bu staas efs types",
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
    def types(self):
        self.get_service_definitions("StorageEFS")

    @ex(
        help="list share",
        description="This command lists all the shares in the EFS file system. The EFS (Elastic File System) is a file storage service for Amazon Web Services (AWS) that provides simple, scalable file storage for use with AWS Cloud services and on-premises resources. This command retrieves a list of all the shares in the EFS file system without needing any additional parameters.",
        example="beehive bu staas efs list -accounts cmrc-proto;beehive bu staas efs list -account Csi.SSA242.DOIT-preprod",
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
                        "help": "list of share id comma separated",
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
            "name": "CreationToken",
            "tags": "tag-key.N",
            "size": "MaxItems",
            "page": "Marker",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "%s/storageservices/efs/file-systems" % self.baseuri

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            total = res.get("nvl-fileSystemTotal")
            res = res.get("FileSystems", [])
            resp = {
                "count": len(res),
                "page": page,
                "total": total,
                "sort": {"field": "date.creation", "order": "desc"},
                "instances": res,
            }

            headers = [
                "id",
                "name",
                "status",
                "creation",
                "account",
                "targets",
                "size(bytes)",
                "mode",
            ]
            fields = [
                "FileSystemId",
                "CreationToken",
                "LifeCycleState",
                "CreationTime",
                "OwnerId",
                "NumberOfMountTargets",
                "SizeInBytes.Value",
                "PerformanceMode",
            ]
            transform = {"LifeCycleState": self.color_error}
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
            key_total_name="nvl-fileSystemTotal",
            key_list_name="FileSystems",
            fn_render=render,
        )

    @ex(
        help="get share",
        description="This command retrieves information about a specific file share by its unique identifier (ID). The required 'share' argument specifies the ID of the share to retrieve details for.",
        example="beehive bu staas efs get <uuid>;beehive bu staas efs get <uuid>",
        arguments=ARGS(
            [
                (["share"], {"help": "share id", "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        uuid = self.app.pargs.share
        data = {"FileSystemId": uuid}
        uri = "%s/storageservices/efs/file-systems" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = res.get("FileSystems", [])
        if len(res) == 0:
            raise Exception("share %s does not exists" % uuid)

        if self.is_output_text():
            self.app.render(res[0], details=True, maxsize=200)

            self.c("\nmount targets", "underline")
            data = {}
            # data['owner-id.N'] = self.split_arg('owner-id.N')
            data["FileSystemId"] = uuid
            data["MaxItems"] = 10
            data["Marker"] = 0
            uri = "%s/storageservices/efs/mount-targets" % self.baseuri
            res = self.cmp_get(uri, data=urlencode(data, doseq=True))
            res = res.get("MountTargets", [])
            headers = [
                "status",
                "target",
                "availability-zone",
                "subnet",
                "ipaddress",
                "proto",
            ]
            fields = [
                "LifeCycleState",
                "MountTargetId",
                "nvl-AvailabilityZone",
                "SubnetId",
                "IpAddress",
                "nvl-ShareProto",
            ]
            self.app.render(res, headers=headers, fields=fields, maxsize=200)

            self.c("\ngrants", "underline")
            uri = "%s/storageservices/efs/mount-targets/%s/grants" % (
                self.baseuri,
                uuid,
            )
            res = self.cmp_get(uri, timeout=600)
            resp = []
            for grant in res.get("grants"):
                resp.append(
                    {
                        "id": res.get("FileSystemId"),
                        "grant-id": grant.get("id"),
                        "access-level": grant.get("access_level"),
                        "state": grant.get("state"),
                        "access-type": grant.get("access_type"),
                        "access-to": grant.get("access_to"),
                    }
                )
            self.app.render(
                resp,
                headers=[
                    "grant-id",
                    "state",
                    "access-level",
                    "access-type",
                    "access-to",
                ],
                maxsize=200,
            )
        else:
            self.app.render(res, details=True, maxsize=100)

    @ex(
        help="create a share",
        description="This command creates a share with the specified name, parent account id and size. Name, account, size and type arguments are required to uniquely identify and provision the storage for the new share being created.",
        example="beehive bu staas efs add greg-tutorial1 Csi.Welfare-sociale.greg-preprod 20 store.m1;beehive bu staas efs add ts-repo-data1 Csi.SSA242.DOIT-preprod 5000 store.ontap.m1",
        arguments=ARGS(
            [
                (["name"], {"help": "share name", "action": "store", "type": str}),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (["size"], {"help": "share size", "action": "store", "type": int}),
                (
                    ["type"],
                    {
                        "help": "share type: use store.m1 for shares managed by manila; use store.ontap.m1 for shares created on netapp directly to import in cmp",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-mode"],
                    {
                        "help": "share performance mode. Can be generalPurpose or localPurpose",
                        "action": "store",
                        "type": str,
                        "default": "generalPurpose",
                    },
                ),
            ]
        ),
    )
    def add(self):
        type = self.app.pargs.type
        if type not in ["store.ontap.m1"]:
            raise Exception(
                "This command is DEPRECATED. Please use RUNDECK procedure to create the share. "
                "Once the volume was created, import it in CMP using the script efs.sh."
            )
        data = {
            "CreationToken": self.app.pargs.name,
            "owner_id": self.get_account(self.app.pargs.account).get("uuid"),
            "Nvl_FileSystem_Size": self.app.pargs.size,
            "Nvl_FileSystem_Type": self.app.pargs.type,
            "PerformanceMode": self.app.pargs.mode,
        }
        uri = "%s/storageservices/efs/file-systems" % self.baseuri
        res = self.cmp_post(uri, data=data, timeout=600)

        self.app.render({"msg": "add storage efs instance share %s" % res.get("FileSystemId", None)})

    @ex(
        help="resize a share",
        description="Resize a share. Resize a share by specifying the share id and new size in bytes.",
        example="beehive bu staas efs resize <uuid> 8192;beehive bu staas efs resize <uuid> 4000",
        arguments=ARGS(
            [
                (["share"], {"help": "share id", "action": "store", "type": str}),
                (
                    ["size"],
                    {
                        "help": "new share size in GB",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def resize(self):
        oid = self.app.pargs.share
        params = {"Nvl_FileSystem_Size": self.app.pargs.size}
        uri = "%s/storageservices/efs/file-systems/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data=params)
        self.app.render({"msg": "resize share %s" % oid})

    @ex(
        help="delete a share",
        description="This command deletes a share by specifying its id. The share id is a required argument for this command to identify the share to be deleted.",
        example="beehive bu staas efs delete <uuid> -e <env>;beehive bu staas efs delete <uuid> -e <env>",
        arguments=ARGS([(["share"], {"help": "share id", "action": "store", "type": str})]),
    )
    def delete(self):
        uuid = self.app.pargs.share
        uri = "%s/storageservices/efs/file-systems/%s" % (self.baseuri, uuid)
        self.cmp_delete(uri, timeout=300, entity="share %s" % uuid)

    @ex(
        help="list share mount target",
        description="This command lists all the mount targets that are associated with the specified EFS file system. An EFS mount target represents a gateway that clients use to access an EFS file system. This command returns information about each mount target such as the IP address and NFSv4 ID. The -size and --notruncate options can be used to control the output.",
        example="beehive bu staas efs target-list;beehive bu staas efs target-list -size -1 --notruncate",
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
                        "help": "list of share id comma separated",
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
    def target_list(self):
        params = ["accounts"]
        mappings = {"accounts": self.get_account_ids}
        aliases = {"accounts": "owner-id.N", "size": "MaxItems", "page": "Marker"}
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        page = self.app.pargs.page
        uri = "%s/storageservices/efs/mount-targets" % self.baseuri
        res = self.cmp_get(uri, data=data, timeout=600)
        total = res.get("nvl_fileSystemTargetTotal")
        res = dict_get(res, "MountTargets", default=[])
        resp = {
            "count": len(res),
            "page": page,
            "total": total,
            "sort": {"field": "date.creation", "order": "desc"},
            "instances": res,
        }

        headers = [
            "file-system",
            "ipaddress",
            "target",
            "account",
            "availability-zone",
            "subnet",
            "proto",
            "status",
        ]
        fields = [
            "FileSystemId",
            "IpAddress",
            "MountTargetId",
            "OwnerId",
            "nvl-AvailabilityZone",
            "SubnetId",
            "nvl-ShareProto",
            "LifeCycleState",
        ]
        self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=200)

    @ex(
        help="create share mount target",
        description="This command creates a mount target for the specified EFS file system share. A mount target represents an IP address within a specific Availability Zone on which the file system may be mounted. It requires the share ID as the first argument and optionally takes the subnet ID as the second argument and environment as third argument.",
        example="beehive bu staas efs target-add <uuid> <uuid> nfs;beehive bu staas efs target-add <uuid> <uuid> nfs -e <env>",
        arguments=ARGS(
            [
                (["share"], {"help": "share id", "action": "store", "type": str}),
                (
                    ["subnet"],
                    {
                        "help": "share subnet",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["protocol"],
                    {
                        "help": "protocol should be  nfs|cifs",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-label"],
                    {
                        "help": "custom label to be used when you want to use a labelled share type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ontap_volume"],
                    {
                        "help": "ontap netapp volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def target_add(self):
        share = self.app.pargs.share
        label = self.app.pargs.label
        ontap_volume = self.app.pargs.ontap_volume
        data = {
            "Nvl_FileSystemId": share,
            "SubnetId": self.app.pargs.subnet,
            "Nvl_shareProto": self.app.pargs.protocol,
        }
        if label is not None:
            data["Nvl_shareLabel"] = label
        if ontap_volume is None:
            raise Exception(
                "This command is DEPRECATED. Please use RUNDECK procedure to create the share. "
                "Once the volume was created, import it in CMP using the script efs.sh."
            )
        if ontap_volume is not None:
            data["Nvl_shareVolume"] = ontap_volume

        uri = "%s/storageservices/efs/mount-targets" % self.baseuri
        self.cmp_post(uri, data=data, timeout=600)
        self.app.render({"msg": "add share %s mount target" % share})

    @ex(
        help="delete share mount target",
        description="This CLI command deletes a specific share mount target from the Nivola CMP EFS service. It requires the share ID as the only required argument to identify the target to delete.",
        example="beehive bu staas efs target-delete <uuid>;beehive bu staas efs target-delete <uuid>",
        arguments=ARGS([(["share"], {"help": "share id", "action": "store", "type": str})]),
    )
    def target_delete(self):
        share = self.app.pargs.share
        uri = "%s/storageservices/efs/mount-targets" % self.baseuri
        self.cmp_delete(
            uri,
            data={"Nvl_FileSystemId": share},
            entity="share %s mount target" % share,
        )

    @ex(
        help="create a share grant",
        description="This CLI command creates a share grant by specifying the required arguments - share id, access level which can be either read-write (rw) or read-only (r), access type which should be ip, and the access to expression specifying the ip address or cidr block to grant access to for the specified share id.",
        example="beehive bu staas efs grant-add <uuid> rw ip ###.###.###.###/32;beehive bu staas efs grant-add <uuid> rw ip ###.###.###.###/32",
        arguments=ARGS(
            [
                (["share"], {"help": "share id", "action": "store", "type": str}),
                (
                    ["access_level"],
                    {
                        "help": "access to grant shld be rw | r",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["access_type"],
                    {
                        "help": "access type should be ip",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["access_to"],
                    {"help": "access to expression", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def grant_add(self):
        uuid = self.app.pargs.share
        data = {
            "access_level": self.app.pargs.access_level,
            "access_type": self.app.pargs.access_type,
            "access_to": self.app.pargs.access_to,
        }
        uri = "%s/storageservices/efs/mount-targets/%s/grants" % (self.baseuri, uuid)
        res = self.cmp_post(uri, data={"grant": data}, timeout=600)
        self.app.render({"msg": "add grant share %s" % res})

    @ex(
        help="delete share grant",
        description="This command deletes a share grant for the specified share ID. The share ID is a required argument for this command to identify the share whose grant needs to be deleted.",
        example="beehive bu staas efs grant-delete <uuid> <uuid> -y;beehive bu staas efs grant-delete <uuid> <uuid> -y",
        arguments=ARGS(
            [
                (["share"], {"help": "share id", "action": "store", "type": str}),
                (
                    ["grant"],
                    {
                        "help": "grant id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def grant_delete(self):
        uuid = self.app.pargs.share
        grant = self.app.pargs.grant
        data = {"access_id": grant}
        uri = "%s/storageservices/efs/mount-targets/%s/grants" % (self.baseuri, uuid)
        self.cmp_delete(
            uri,
            data={"grant": data},
            timeout=600,
            entity="share %s grant %s" % (uuid, grant),
        )
