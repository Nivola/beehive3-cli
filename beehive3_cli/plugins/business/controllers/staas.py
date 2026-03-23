# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


from typing import Union, Optional
from urllib.parse import urlencode

from cement import ex

from beecell.types.type_dict import dict_get
from beecell.types.type_id import is_uuid

from beehive3_cli.core.controller import ARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild
from beehive3_cli.translate import _


class STaaServiceController(BusinessControllerChild):
    class Meta:
        label = "staas"
        description = _("storage service management")
        help = _("storage service management")

    @ex(
        help=_("get storage service info"),
        description=_(
            "This command retrieves information about a storage service instance. "
            "It requires the account ID as a required argument to identify "
            "the specific storage service instance. "
            "The command displays details like the account ID, name, status and other metadata."
        ),
        example="beehive bu staas info <uuid> -e <env>; beehive bu staas info <uuid> -e <env>",
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
        uri = f"{self.baseuri}/storageservices"
        res = self.cmp_get(uri, data=urlencode(data))
        res = dict_get(res, "DescribeStorageResponse.storageSet.0")
        self.app.render(res, details=True, maxsize=100)

    @ex(
        help=_("get storage service quotas"),
        description=_(
            "This command gets the storage service quotas for a given account id. "
            "The required 'account' argument specifies the account id to retrieve quotas for."
        ),
        example="beehive bu staas quotas get account <uuid>",
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
        uri = f"{self.baseuri}/storageservices/describeaccountattributes"
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
        description = _("file share service management")
        help = _("file share service management")

    snapshot_policies_c = ["default", "4h_1d", "4h_7d_2w", "8h_7d_14w", "8h_21d_14w_6m", "8h_21d_14w_12m", "14d"]
    replica_rpos = ["30m", "1h", "3h", "6h", "12h", "24h"]

    def _get_instance_staas_version(self, oid: Union[str,int]):
        uri = f"/v2.0/nws/serviceinsts/{oid}"
        return self.cmp_get(uri).get("serviceinst").get("instance-version", None)

    @ex(
        help=_("get share types"),
        description=_(
            "This command is used to retrieve the available share types for Nivola CMP "
            "Storage as a Service (STaaS) Elastic File System (EFS). "
            "Share types determine things like performance and storage capacity. "
            "By listing the available types, you can choose the appropriate one for your needs "
            "when creating a new EFS."
        ),
        example="beehive bu staas efs types",
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
    def types(self):
        self.get_service_definitions("StorageEFS")

    @ex(
        help=_("list share"),
        description=_(
            "This command lists all the shares in the EFS file system. "
            "The EFS (Elastic File System) is a file storage service for "
            "Amazon Web Services (AWS) that provides simple, scalable file storage "
            "for use with AWS Cloud services and on-premises resources. "
            "This command retrieves a list of all the shares in the EFS file system "
            "without needing any additional parameters."
        ),
        example="beehive bu staas efs list -accounts cmrc-proto",
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
                    ["-name"],
                    {
                        "help": _("list of share id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-version"],
                    {
                        "metavar": "VERSION",
                        "help": _("storage instance version, allowed values: 1.0, 2.0"),
                        "action": "store",
                        "type": str,
                        "choices": ["1.0", "2.0"],
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
        params = ["accounts", "name", "tags", "version"]
        mappings = {"accounts": self.get_account_ids, "tags": lambda x: x.split(",")}
        aliases = {
            "accounts": "owner-id.N",
            "name": "CreationToken",
            "tags": "tag-key.N",
            "size": "MaxItems",
            "page": "Marker",
            "version": "InstanceVersion",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "/v2.0/nws/storageservices/efs/file-systems"

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
                "srv-status",
                "account",
                "version",
                "avz",
                # "targets",
                # "ip-addr",
                "mount-target",
                "proto",
                # "size(B)",
                "size(GB)",
                "encrypted",
                "vol-status",
                "compliant",
                "creation",
            ]
            fields = [
                "FileSystemId",
                "CreationToken",
                "LifeCycleState",
                "nvl-OwnerAlias",
                "InstanceVersion",
                "nvl-AvailabilityZone",
                # "NumberOfMountTargets",
                # "IpAddress",
                "MountTargets",
                "nvl_shareProto",
                # "SizeInBytes.Value",
                "Size",
                "Encrypted",
                "FileSystemState",
                "nvl-complianceMode",
                "CreationTime",
            ]

            def mount_targets_as_string(input_list):
                ret = ""
                for item in input_list:
                    mounts = item.get("mounts")
                    if not mounts:
                        continue
                    if ret != "":
                        ret += "\n"
                        ret += "\n".join(mounts)
                    else:
                        ret = "\n".join(mounts)
                return ret

            def color_compliance(value: Optional[bool]) -> str:
                if value is False:
                    return self.app.colored_text.output(str(value), "YELLOW")
                if value is True:
                    return self.app.colored_text.output(str(value), "GREEN")
                return str(value)

            transform = {
                "LifeCycleState": self.color_error,
                "InstanceVersion": lambda x: f"v{x}",
                "SizeInBytes.Value": lambda x: f"{int(x)}" if x else 0,
                "MountTargets": mount_targets_as_string,
                "nvl-complianceMode": (
                    lambda x: color_compliance(x)
                    if self.app.config.get("beehive", "colored")
                    else x
                ),
            }
            self.app.render(
                resp,
                key="instances",
                headers=headers,
                fields=fields,
                maxsize=25,
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

    def _get(self, oid):
        data = {"FileSystemId": oid}
        uri = "/v1.0/nws/storageservices/efs/file-systems"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = res.get("FileSystems", [])
        if len(res) == 0:
            raise Exception(f"share {oid} does not exists")

        if self.is_output_text():
            self.app.render(res[0], details=True, maxsize=200)

            self.c("\nmount targets", "underline")
            headers = ["protocol", "mounts"]
            transform = {"mounts": "\n".join}
            self.app.render(res[0], key="MountTargets", headers=headers, transform=transform, maxsize=200)

            self.c("\ngrants", "underline")
            self._grant_list(oid, version="1.0")  # manila only 1.0, the rest should be ok with 2.0
        else:
            self.app.render(res, details=True, maxsize=100)

    def _get_v2(self, oid):
        data = {"FileSystemId": oid}
        uri = "/v2.0/nws/storageservices/efs/file-systems"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = res.get("FileSystems", [])
        if len(res) == 0:
            raise Exception(f"share {oid} does not exists")
        res = res[0]

        if self.is_output_text():
            self.app.render(res, details=True, maxsize=200)

            if res.get("Replicas"):
                self.c("\nreplicas", "underline")
                headers = ["replica_id", "replica_name", "site", "rpo", "healthy", "state"]
                self.app.render(res, key="Replicas", headers=headers, maxsize=200)

            if res.get("Source"):
                self.c("\nsource", "underline")
                headers = ["source_id", "source_name", "site", "healthy", "state"]
                self.app.render(res, key="Source", headers=headers, maxsize=200)

            self.c("\nmount targets", "underline")
            headers = ["id", "protocol", "mounts"]
            transform = {"mounts": "\n".join}
            self.app.render(res, key="MountTargets", headers=headers, transform=transform, maxsize=200)

            self.c("\ngrants", "underline")
            self._grant_list(oid, version="2.0")
        else:
            self.app.render(res, details=True, maxsize=100)

    @ex(
        help=_("get share"),
        description=_(
            "This command retrieves information about a specific file share by its unique identifier (ID). "
            "The required 'share' argument specifies the ID of the share to retrieve details for."
        ),
        example="beehive bu staas efs get 245d5e90-2b67-4d16-917f-66a2105c9714",
        arguments=ARGS(
            [
                (["share"], {"help": _("share id"), "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        uuid = self.app.pargs.share
        staas_version = self._get_instance_staas_version(uuid)
        if staas_version == "2.0":
            self._get_v2(uuid)
        elif staas_version in [None, "", "1.0"]:
            self._get(uuid)
        else:
            raise Exception(f"Unknown staas version: {staas_version}")

    @ex(
        help=_("create a share"),
        description=_(
            "This command creates a share with the specified name, parent account id and size. "
            "Name, account, size and type arguments are required to uniquely identify and "
            "provision the storage for the new share being created."
        ),
        example="beehive bu staas efs add ts-repo-data1 Csi.SSA242.DOIT-preprod 5000 store.ontap.m1",
        arguments=ARGS(
            [
                (["name"], {"help": _("share name"), "action": "store", "type": str}),
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (["size"], {"help": _("share size"), "action": "store", "type": int}),
                (
                    ["-mode"],
                    {
                        "help": _("share performance mode. Can be generalPurpose or localPurpose"),
                        "action": "store",
                        "type": str,
                        "default": "generalPurpose",
                    },
                ),
            ]
        ),
    )
    def add_legacy(self):
        data = {
            "CreationToken": self.app.pargs.name,
            "owner_id": self.get_account(self.app.pargs.account).get("uuid"),
            "Nvl_FileSystem_Size": self.app.pargs.size,
            "Nvl_FileSystem_Type": "store.ontap.m1",
            "PerformanceMode": self.app.pargs.mode,
        }
        uri = f"{self.baseuri}/storageservices/efs/file-systems"
        res = self.cmp_post(uri, data=data, timeout=600)
        uuid = dict_get(
            res,
            "FileSystemId",
        )
        self.wait_for_service(uuid)
        self.app.render({"msg": f"add storage efs instance share {res.get('FileSystemId', None)}"})

    @ex(
        help=_("create a share V2"),
        description=_(
            "This command creates a share with the specified name, parent account id and size. "
            "Name, account, size and type arguments are required to uniquely identify and provision "
            "the storage for the new share being created."
        ),
        arguments=ARGS(
            [
                (["name"], {"help": _("share name"), "action": "store", "type": str}),
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (
                    ["zone"],
                    {
                        "help": _("site where to create share. e.g. SiteTorino05"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (["size"], {"help": _("share size"), "action": "store", "type": int}),
                (
                    ["protocol"],
                    {
                        "metavar": "protocol",
                        "help": _("one of [nfs, cifs]"),
                        "choices": ["nfs", "cifs"],
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-nocompliance"],
                    {
                        "help": _("not compliant with ACN requirements i.e. without snaplock volume"),
                        "action": "store_true",
                    },
                ),
                (
                    ["-rpo"],
                    {
                        "help": _("compliance rpo, one of [12h, 24h]"),
                        "choices": ["12h","24h"],
                        "action":"store",
                        "type": str
                    }
                ),
                (
                    ["-snapshot_policy"],
                    {
                        "help": _("snapshot policy value"),
                        "action": "store",
                        "type": str,
                        "choices": snapshot_policies_c,
                        "default": None
                    }
                ),
                (["-encrypted"], {"help": _("encrypt volume"), "action": "store_true"}),
            ]
        ),
    )
    def add(self):
        compliance = not self.app.pargs.nocompliance
        rpo = self.app.pargs.rpo
        encrypted = self.app.pargs.encrypted
        snapshot_policy = self.app.pargs.snapshot_policy

        data = {
            "CreationToken": self.app.pargs.name,
            "owner_id": self.get_account(self.app.pargs.account).get("uuid"),
            "SiteName": self.app.pargs.zone,
            "Nvl_FileSystem_Size": self.app.pargs.size,
            "Nvl_FileSystem_Type": "store.ontap.m1",
            "Nvl_shareProto": self.app.pargs.protocol.upper(),
            "ComplianceMode": compliance,
        }

        if compliance and rpo:
            data["Rpo"] = rpo
        elif compliance and not rpo:
            raise Exception("Must provide rpo when compliance is enabled")
        elif not compliance and rpo:
            self.app.warning("Rpo parameter will not be used since compliance is set to False")

        if encrypted:
            data["Encrypted"] = encrypted
        if snapshot_policy:
            data["SnapshotPolicy"] = snapshot_policy

        uri = "/v2.0/nws/storageservices/efs/file-systems"
        res = self.cmp_post(uri, data=data, timeout=600).get("FileSystem")
        share_uuid = res.get("FileSystemId")
        self.wait_for_service_v2(share_uuid)
        self.app.render({"msg": f"add storage efs instance share {share_uuid} ({res.get('CreationToken')})"})

    @ex(
        help=_("update a share"),
        description=_("update a share"),
        example="beehive bu staas efs update <share> [option]",
        arguments=ARGS(
            [
                (
                    ["share"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str
                    }
                ),
                (
                    ["-size"],
                    {
                        "help": _("new share size in GB"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-set_online"],
                    {
                        "help": _("set status to online"),
                        "action": "store_true",
                    },
                ),
                (
                    ["-set_offline"],
                    {
                        "help": _("set status to offline"),
                        "action": "store_true",
                    },
                ),
                (
                    ["-snapshot_policy"],
                    {
                        "help": _("snapshot policy value"),
                        "action": "store",
                        "type": str,
                        "choices": snapshot_policies_c,
                        "default": None,
                    },
                ),
                (
                    ["-enable_compliance"],
                    {
                        "help": _(
                            "be compliant with ACN requirements, "
                            "i.e. create snaplock volume; rpo value must be passed"
                        ),
                        "choices": ["12h", "24h"],
                        "action": "store",
                        "type": str
                    },
                ),
                (
                    ["-disable_compliance"],
                    {
                        "help": _("be non-compliant with ACN requirements, i.e. remove snaplock volume"),
                        "action": "store_true",
                    },
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.share
        size = self.app.pargs.size
        online = self.app.pargs.set_online
        offline = self.app.pargs.set_offline
        snapshot_policy = self.app.pargs.snapshot_policy
        enable_compliance_rpo = self.app.pargs.enable_compliance
        disable_compliance = self.app.pargs.disable_compliance

        # check
        l = [x for x in [
                            size,
                            online,
                            offline,
                            snapshot_policy,
                            enable_compliance_rpo,
                            disable_compliance
                        ] if x not in [None, False]]
        if len(l) > 1:
            raise Exception("Only one parameter can be updated at a time")

        if size:
            data = {"Nvl_FileSystem_Size": size}
        elif online:
            data = {"Nvl_MountTarget_Status": "online"}
        elif offline:
            data = {"Nvl_MountTarget_Status": "offline"}
        elif snapshot_policy:
            data = {"Nvl_SnapshotPolicy": snapshot_policy}
        elif enable_compliance_rpo:
            data = {
                "Nvl_ComplianceMode": True,
                "Rpo": enable_compliance_rpo
            }
        elif disable_compliance:
            data = {"Nvl_ComplianceMode": False}
        else:
            raise Exception("Unknown action")

        uri = f"/v2.0/nws/storageservices/efs/file-systems/{oid}"
        self.cmp_put(uri, data=data, timeout=600)

        if size:
            self.app.render({"msg": f"share {oid} resized"})
        elif online:
            self.app.render({"msg": f"share {oid} is online"})
        elif offline:
            self.app.render({"msg": f"share {oid} is offline"})
        elif snapshot_policy:
            self.app.render({"msg": f"applied snapshot policy {snapshot_policy} to share {oid}"})
        elif enable_compliance_rpo:
            self.app.render({"msg": f"enabled compliance for share {oid}"})
        elif disable_compliance:
            self.app.render({"msg": f"disabled compliance for share {oid}"})

    @ex(
        help=_("add share replica"),
        description=_("add share replica"),
        arguments=ARGS(
            [
                (
                    ["source_id"],
                    {
                        "help": _("source share id"),
                        "action":"store",
                        "type": str
                    }
                ),
                (
                    ["dest_site_name"],
                    {
                        "help": _("destination site name"),
                        "action": "store",
                        "type":str
                    }
                ),
                (
                    ["replica_rpo"],
                    {
                        "help": _("replica rpo"),
                        "action": "store",
                        "type": str,
                        "choices": replica_rpos
                    }
                ),
            ]
        ),
    )
    def replica_add(self):
        data = {
            "SiteName": self.app.pargs.dest_site_name,
            "Rpo": self.app.pargs.replica_rpo,
        }

        uri = f"/v2.0/nws/storageservices/efs/file-systems/{self.app.pargs.source_id}/replica"
        res = self.cmp_post(uri, data=data, timeout=600).get("FileSystem")
        share_uuid = res.get("FileSystemId")
        self.wait_for_service_v2(share_uuid)
        self.app.render({"msg": f"add storage efs instance share {share_uuid} ({res.get('CreationToken')})"})

    @ex(
        help=_("update a share replica"),
        description=_("update a share replica"),
        example="beehive bu staas efs replica-update <replica> [option]",
        arguments=ARGS(
            [
                (
                    ["replica"],
                    {
                        "help": _("replica id"),
                        "action": "store",
                        "type": str
                    }
                ),
                (
                    ["-rpo"],
                    {
                        "help": _("replica rpo"),
                        "action": "store",
                        "type": str,
                        "choices": replica_rpos,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def replica_update(self):
        oid = self.app.pargs.replica
        rpo = self.app.pargs.rpo

        if rpo:
            data = {"rpo": rpo}
        else:
            raise Exception("Unknown action")

        uri = f"/v2.0/nws/storageservices/efs/file-systems/{oid}/updatereplica"
        self.cmp_put(uri, data={"replica": data}, timeout=600)

        if rpo:
            self.app.render({"msg": f"apply rpo {rpo} to replica share {oid}"})

    @ex(
        help=_("delete a share"),
        description=_(
            "This command deletes a share by specifying its id. "
            "The share id is a required argument for this command to identify the share to be deleted."
        ),
        example="beehive bu staas efs delete <uuid> -e <env>; beehive bu staas efs delete <uuid> -e <env>",
        arguments=ARGS([(["share"], {"help": _("share id"), "action": "store", "type": str})]),
    )
    def delete(self):
        uuid = self.app.pargs.share
        uri = f"{self.baseuri}/storageservices/efs/file-systems/{uuid}"
        self.cmp_delete(uri, timeout=300, entity=f"share {uuid}")

    @ex(
        help=_("delete replica relationship"),
        description=_("Delete the relationship between a replica and its source storage efs filesystem"),
        example="beehive bu staas efs replica-unlink e8c943b9-1a2b-4d90-b655-efcb213d32e6",
        arguments=ARGS(
            [
                (["replica"], {"help": _("replica uuid"), "action": "store", "type": str}),
                (
                    ["name"],
                    {
                        "help": _("the name to assign to the volume after the replica relationship was deleted"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def replica_unlink(self):
        oid = self.app.pargs.replica
        name = self.app.pargs.name
        if not is_uuid(oid):
            raise Exception("Provide a valid uuid.")
        data = {"new_name": name}
        uri = f"/v2.0/nws/storageservices/efs/file-systems/{oid}/unlinkreplica"
        self.cmp_put(uri, data={"replica": data}, timeout=600)
        self.app.render({"msg": f"Delete replica relationship for efs instance {oid}"})

    @ex(
        help=_("suspend/pause replica relationship"),
        description=_("Suspend/pause the relationship between a replica and its source storage efs filesystem"),
        example="beehive bu staas efs replica-suspend e8c943b9-1a2b-4d90-b655-efcb213d32e6",
        arguments=ARGS(
            [
                (["replica"], {"help": _("replica uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def replica_suspend(self):
        oid = self.app.pargs.replica
        if not is_uuid(oid):
            raise Exception("Provide a valid uuid.")
        uri = f"/v2.0/nws/storageservices/efs/file-systems/{oid}/suspendreplica"
        self.cmp_put(uri, timeout=600)
        self.app.render({"msg": f"Suspend replica relationship for efs instance {oid}"})

    @ex(
        help=_("resume replica relationship"),
        description=_("Resume the relationship between a replica and its source storage efs filesystem"),
        example="beehive bu staas efs replica-resume e8c943b9-1a2b-4d90-b655-efcb213d32e6",
        arguments=ARGS(
            [
                (["replica"], {"help": _("replica uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def replica_resume(self):
        oid = self.app.pargs.replica
        if not is_uuid(oid):
            raise Exception("Provide a valid uuid.")
        uri = f"/v2.0/nws/storageservices/efs/file-systems/{oid}/resumereplica"
        self.cmp_put(uri, timeout=600)
        self.app.render({"msg": f"Resume replica relationship for efs instance {oid}"})

    @ex(
        help=_("mount efs"),
        description=_("Mount efs"),
        example="beehive bu staas efs mount e8c943b9-1a2b-4d90-b655-efcb213d32e6",
        arguments=ARGS(
            [
                (["id"], {"help": _("efs uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def mount(self):
        oid = self.app.pargs.id
        if not is_uuid(oid):
            raise Exception("Provide a valid uuid.")
        uri = f"/v2.0/nws/storageservices/efs/file-systems/{oid}/mount"
        self.cmp_put(uri, timeout=600)
        self.app.render({"msg": f"Mount efs instance {oid}"})

    @ex(
        help=_("list share mount target"),
        description=_(
            "This command lists all the mount targets that are associated with the specified EFS file system. "
            "An EFS mount target represents a gateway that clients use to access an EFS file system. "
            "This command returns information about each mount target such as the IP address and NFSv4 ID. "
            "The -size and --notruncate options can be used to control the output."
        ),
        example="beehive bu staas efs target-list",
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
                    ["-name"],
                    {
                        "help": _("list of share id comma separated"),
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
    def target_list(self):
        params = ["accounts"]
        mappings = {"accounts": self.get_account_ids}
        aliases = {"accounts": "owner-id.N", "size": "MaxItems", "page": "Marker"}
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        page = self.app.pargs.page
        uri = f"{self.baseuri}/storageservices/efs/mount-targets"
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
        help=_("create share mount target"),
        description=_(
            "This command creates a mount target for the specified EFS file system share. "
            "A mount target represents an IP address within a specific Availability Zone "
            "on which the file system may be mounted. "
            "It requires the share ID as the first argument and optionally takes the subnet ID "
            "as the second argument and environment as third argument."
        ),
        example="beehive bu staas efs target-add <uuid> <uuid> nfs -e <env>",
        arguments=ARGS(
            [
                (["share"], {"help": _("share id"), "action": "store", "type": str}),
                (
                    ["subnet"],
                    {
                        "help": _("share subnet"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["protocol"],
                    {
                        "help": _("protocol should be  nfs|cifs"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-label"],
                    {
                        "help": _("custom label to be used when you want to use a labelled share type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ontap_volume"],
                    {
                        "help": _("ontap netapp volume id"),
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

        uri = f"{self.baseuri}/storageservices/efs/mount-targets"
        self.cmp_post(uri, data=data, timeout=600)
        self.app.render({"msg": f"add share {share} mount target"})

    @ex(
        help=_("delete share mount target"),
        description=_(
            "This CLI command deletes a specific share mount target from the Nivola CMP EFS service. "
            "It requires the share ID as the only required argument to identify the target to delete."
        ),
        example="beehive bu staas efs target-delete <uuid>",
        arguments=ARGS([(["share"], {"help": _("share id"), "action": "store", "type": str})]),
    )
    def target_delete(self):
        share = self.app.pargs.share
        uri = f"{self.baseuri}/storageservices/efs/mount-targets"
        self.cmp_delete(
            uri,
            data={"Nvl_FileSystemId": share},
            entity=f"share {share} mount target",
        )

    def _grant_list(self, oid, version="2.0"):
        uri = f"/v{version}/nws/storageservices/efs/mount-targets/{oid}/grants"
        res = self.cmp_get(uri, timeout=200)
        headers_v1 = ["id", "access-level", "access-type", "clients"]
        headers_v2 = ["id", "access-level", "su-access", "protocols", "clients"]
        fields_v1 = ["id", "access_level", "access_type", "access_to"]
        fields_v2 = ["id", "access_level", "access_superuser", "protocols", "clients"]

        is_manila_format = False
        if version == "1.0":
            grants = res.get("grants")
            if grants and isinstance(grants, list) and "access_to" in grants[0].keys():
                is_manila_format = True

        if version == "2.0" or not is_manila_format:
            headers = headers_v2
            fields = fields_v2
            transform = {
                "protocols": ", ".join,
                "clients": ", ".join,
            }
        else:
            headers = headers_v1
            fields = fields_v1
            transform = {
                "clients": ", ".join,
            }
        self.app.render(res, key="grants", headers=headers, fields=fields, transform=transform, maxsize=200)

    @ex(
        help=_("get share access grants"),
        description=_("Get share grants."),
        example="beehive bu staas efs grant-list e8c943b9-1a2b-4d90-b655-efcb213d32e6",
        arguments=ARGS(
            [
                (["share"], {"help": _("share id"), "action": "store", "type": str}),
            ]
        ),
    )
    def grant_list(self):
        oid = self.app.pargs.share
        staas_version = self._get_instance_staas_version(oid)
        self._grant_list(oid, version=staas_version)

    def _grant_add(self, oid, access_level, client_type: str, clients: str):
        # grant-add API v1.0 manages a target at a time, so loop from list items
        clients = clients.split(",")
        for client in clients:
            data = {
                "access_level": access_level,
                "access_type": "ip",
                "access_to": client,
            }
            uri = f"/v1.0/nws/storageservices/efs/mount-targets/{oid}/grants"
            self.cmp_post(uri, data={"grant": data}, timeout=600)
            self.app.render({"msg": f"add grant to share {oid}"})

    def _grant_add_v2(self, oid, access_level, superuser, client_type: str, clients: str, protocol: str):
        data = {
            "access_level": access_level,
            "access_superuser": superuser,
            "client_type": client_type,
            "client.N": clients.split(","),
            "protocol": protocol,
        }
        uri = f"/v2.0/nws/storageservices/efs/mount-targets/{oid}/grants"
        self.cmp_post(uri, data={"grant": data}, timeout=600)
        self.app.render({"msg": f"add grant to share {oid}"})

    @ex(
        help="create a share access grant",
        description="This CLI command creates a share grant by specifying the required arguments.",
        example=(
            "beehive bu staas efs grant-add TODEL-DAVIDE-NC-1 rw ID:vmPP311024 nfs3,test-filebeat-to2-02 "
            "ro CIDR:10.20.30.0/24 nfs3 -superuser"
        ),
        arguments=ARGS(
            [
                (["share"], {"help": _("share id"), "action": "store", "type": str}),
                (
                    ["access_level"],
                    {
                        "help": _("access level to grant, should be 'ro' or 'rw'"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["clients"],
                    {
                        "help": _(
                            """list of clients to enable on share.
                            Syntax <type>:<value>.
                            <type> can be ID, CIDR or USER.
                            For ID, <value> should be a comma separated list of vms id, uuid or name.
                            For CIDR, <value> should be a valid CIDR block like 10.138.144.0/24.
                            For USER, <value> should be a valid domain user.
                            Please note that type USER is used for CIFS shares only."""
                        ),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["protocol"],
                    {
                        "help": _("protocol (nfs, nfs3, cifs). defaults to share protocol if unspecified"),
                        "action": "store",
                        "choices": ["nfs", "nfs3", "cifs"],
                        "type": str,
                    }
                ),
                (
                    ["-superuser"],
                    {
                        "help": _("allow superuser access"),
                        "action": "store_true",
                    },
                ),
            ]
        ),
    )
    def grant_add(self):
        uuid = self.app.pargs.share

        access_level = self.app.pargs.access_level
        access_level = access_level.lower()

        clients = self.app.pargs.clients
        client_type, clients = clients.split(":")

        protocol = self.app.pargs.protocol
        superuser = self.app.pargs.superuser

        if access_level not in ["ro", "rw"]:
            raise Exception(f'Allowed access level values are: {["ro", "rw"]}')

        # force RW access in case superuser access is allowed
        if superuser and access_level == "ro":
            raise Exception("Access level must be RW when superuser access is allowed.")

        staas_version = self._get_instance_staas_version(uuid)

        if staas_version == "2.0":
            if client_type not in ["ID", "CIDR", "USER"]:
                raise Exception(f'Allowed clients types for STAAS v2.0 are: {["ID", "CIDR", "USER"]}')
            self._grant_add_v2(uuid, access_level, superuser, client_type, clients, protocol)
        elif staas_version in [None, "", "1.0"]:
            if client_type not in ["CIDR"]:
                raise Exception(f'Allowed clients types for STAAS v1.0 are: {["CIDR"]}')
            self._grant_add(uuid, access_level, client_type, clients)
        else:
            raise Exception(f"Unknown staas version: {staas_version}")

    @ex(
        help=_("delete share access grants"),
        description=_(
            "This command deletes one o more share grants for the specified share ID. "
            "Both the share ID and the grants ids are required arguments for this command "
            "to identify the share whose grants needs to be deleted."
        ),
        example="beehive bu staas efs grant-delete 7a25f93c-523f-4fef-98bf-b82bb36b36b0 2,4,5",
        arguments=ARGS(
            [
                (
                    ["share"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str
                    }
                ),
                (
                    ["grants"],
                    {
                        "help": _("comma separated list of grant ids"),
                        "action": "store",
                        "type": str,
                        "default": None
                    }
                ),
            ]
        ),
    )
    def grant_delete(self):
        oid = self.app.pargs.share
        grants = self.app.pargs.grants
        grant_ids = [int(x) for x in grants.split(",")]
        staas_version = self._get_instance_staas_version(oid)
        if staas_version == "2.0":
            uri = f"/v2.0/nws/storageservices/efs/mount-targets/{oid}/grants"
        elif staas_version in [None, "", "1.0"]:
            uri = f"/v1.0/nws/storageservices/efs/mount-targets/{oid}/grants"
        else:
            raise Exception(f"Unknown staas version: {staas_version}")
        self.cmp_delete(
            uri,
            data={"grant": {"access_ids": grant_ids}},
            timeout=600,
            entity=f"share {oid} grants {grant_ids}",
        )

    @ex(
        help=_("get snapshot policies"),
        description=_("get snapshot policies"),
        example="beehive bu staas efs snapshot-policies <account>",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("account id, uuid or name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def snapshot_policies(self):
        params = ["account"]
        mappings = {
            "account": lambda x: self.get_account(x)["uuid"],
        }
        aliases = {"account": "owner-id"}
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "/v2.0/nws/storageservices/efs/file-systems/describesnapshotpolicies"
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeSnapshotPoliciesResponse", {}).get("snapshotPoliciesSet", [])
        # add key 'policy' in each dictionary of 'res' list
        resp = [dict(item, **{"policy": item["name"].removeprefix("staas_snap_")}) for item in res]
        headers = ["policy", "definition", "scheduled snapshots"]
        fields = ["policy", "name", "description"]
        self.app.render(resp, headers=headers, fields=fields, maxsize=200)

    @ex(
        help="get replica policies",
        description="get replica policies",
        example="beehive bu staas efs replica-policies <account>",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("account id, uuid or name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def replica_policies(self):
        params = ["account"]
        mappings = {
            "account": lambda x: self.get_account(x)["uuid"],
        }
        aliases = {"account": "owner-id"}
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "/v2.0/nws/storageservices/efs/file-systems/describereplicapolicies"
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeReplicaPoliciesResponse", {}).get("replicaPoliciesSet", [])
        # add key 'policy' in each dictionary of 'res' list
        resp = [dict(item, **{"policy": item["name"].removeprefix("staas_mirror_")}) for item in res]
        headers = ["rpo", "definition", "transfer schedule"]
        fields = ["policy", "name", "description"]
        self.app.render(resp, headers=headers, fields=fields, maxsize=200)
