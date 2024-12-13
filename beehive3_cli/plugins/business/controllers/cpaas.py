# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beecell.password import random_password
from beecell.types.type_dict import dict_get
from beecell.types.type_id import id_gen
from beecell.types.type_string import str2bool
from beehive3_cli.core.controller import ARGS
from beehive3_cli.core.util import load_config
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


CONTINUE_NOTICE = "to continue use this command specify --continues argument"


class CPaaServiceController(BusinessControllerChild):
    class Meta:
        label = "cpaas"
        description = "compute service management"
        help = "compute service management"

    @ex(
        help="get compute service info",
        description="""\
This CLI command retrieves compute service information for the specified account id. \
The account id argument is required to identify which account's compute service info should be retrieved. \
This command will display basic info about the compute service configuration and resources for the given account.\
""",
        example="beehive bu cpaas info ####;beehive bu cpaas info <uuid>",
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
        uri = f"{self.baseuri}/computeservices"
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, "DescribeComputeResponse.computeSet.0")
        self.app.render(res, details=True, maxsize=100)
        # limits = res.pop('limits')
        # self.output('Limits:')
        # self.app.render(limits, headers=['quota', 'value', 'allocated', 'unit'], maxsize=40)

    @ex(
        help="get compute service quotas",
        description="""\
This command is used to retrieve compute service quotas for a given account id. \
The account id is a required argument that must be provided to get the quotas information. \
This command will return the quotas configured for the specified account for compute services.\
""",
        example="beehive bu cpaas quotas <uuid>",
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
        uri = f"{self.baseuri}/computeservices/describeaccountattributes"
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
        help="get compute service availibility zones",
        description="""\
This command retrieves the available compute service availability zones for a given account. \
The account ID is required as it will return the availability zones accessible to that specific account.\
""",
        example="beehive bu cpaas availability-zones xxxxx;beehive bu cpaas availability-zones xxxxx",
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
        uri = f"{self.baseuri}/computeservices/describeavailabilityzones"
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, "DescribeAvailabilityZonesResponse.availabilityZoneInfo")
        headers = ["name", "state", "region", "message"]
        fields = ["zoneName", "zoneState", "regionName", "messageSet.0.message"]
        self.app.render(res, headers=headers, fields=fields)


class ImageServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = "cpaas"
        stacked_type = "nested"
        label = "images"
        description = "image service management"
        help = "image service management"

    @ex(
        help="list images",
        description="""\
This command lists all the available images in the Cement Platform as a Service (CPaaS) image registry. \
Images are templates that can be used to deploy applications and workloads on CPaaS. \
Listing images allows a user to see what options are available to choose from when deploying or launching new instances.\
""",
        example="beehive bu cpaas images list 16 -e <env>;beehive bu cpaas images list -account xxxxx",
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
                    ["-images"],
                    {
                        "help": "list of image id comma separated",
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
        params = ["accounts", "images"]
        mappings = {
            "accounts": self.get_account_ids,
            "tags": lambda x: x.split(","),
            "images": lambda x: x.split(","),
        }
        aliases = {
            "accounts": "owner-id.N",
            "images": "image-id.N",
            "tags": "tag-key.N",
            "size": "Nvl-MaxResults",
            "page": "Nvl-NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)

        uri = f"{self.baseuri}/computeservices/image/describeimages"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeImagesResponse")
            resp = {
                "count": len(res.get("imagesSet")),
                "page": page,
                "total": res.get("nvl-imageTotal"),
                "sort": {"field": "id", "order": "asc"},
                "instances": res.get("imagesSet"),
            }

            headers = ["id", "name", "state", "type", "account", "platform", "hypervisor"]
            fields = [
                "imageId",
                "name",
                "imageState",
                "imageType",
                "imageOwnerAlias",
                "platform",
                "hypervisor",
            ]
            self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=45)

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=100,
            key_total_name="DescribeImagesResponse.nvl-imageTotal",
            key_list_name="DescribeImagesResponse.imagesSet",
            fn_render=render,
        )

    @ex(
        help="get image",
        description="""\
This command retrieves the details of a specific image by providing its image id as an argument. \
The image id is a required argument for this command to work. \
It helps the user to get details of a particular image stored in the system by its unique identifier.\
""",
        example="beehive bu cpaas images get <uuid>",
        arguments=ARGS(
            [
                (["image"], {"help": "image id", "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        image_id = self.app.pargs.image
        if self.is_uuid(image_id):
            data = {"ImageId.N": [image_id]}
        elif self.is_name(image_id):
            data = {"name.N": [image_id]}

        uri = f"{self.baseuri}/computeservices/image/describeimages"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeImagesResponse.imagesSet", default={})
        if len(res) > 0:
            res = res[0]
            # if self.is_output_text():
            #     self.app.render(res, details=True, maxsize=100)
            # else:
            self.app.render(res, details=True, maxsize=100)
        else:
            raise Exception(f"image {image_id} was not found")

    @ex(
        help="get image templates",
        description="""\
This command retrieves the available image templates that can be used to deploy applications on Nivola CMP CPAAS. \
Image templates define the base operating system, runtime and dependencies required by applications. \
They help standardize application deployments and ensure consistency across environments like development, test and production.\
""",
        example="beehive bu cpaas images types <uuid>",
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
        self.get_service_definitions("ComputeImage")

    @ex(
        help="create an image",
        description="""\
This command creates an image in the Nivola CMP CPAAS platform. \
It requires the image name, parent account id, description and type as required arguments to \
uniquely identify and describe the new image being created.\
""",
        example="beehive bu cpaas images addImgname <uuid> name name",
        arguments=ARGS(
            [
                (["name"], {"help": "image name", "action": "store", "type": str}),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["desc"],
                    {"help": "image description", "action": "store", "type": str},
                ),
                (["type"], {"help": "image type (definition)", "action": "store", "type": str}),
            ]
        ),
    )
    def add(self):
        name = self.app.pargs.name
        account = self.get_account(self.app.pargs.account).get("uuid")
        itype = self.get_service_definition(self.app.pargs.type)
        desc = self.app.pargs.desc

        data = {
            "ImageName": name,
            "owner_id": account,
            "ImageDescription": desc,
            "ImageType": itype,
        }
        uri = f"{self.baseuri}/computeservices/image/createimage"
        res = self.cmp_post(uri, data={"image": data}, timeout=600)
        res = dict_get(res, "CreateImageResponse.imageId")
        self.app.render({"msg": f"add image: {res}"})

    @ex(
        help="delete an image",
        description="""\
This command deletes an image with the provided image id from the Nivola CMP CPAAS. \
The image id is a required argument for this command to identify the image to delete. \
An environment can also be optionally specified with the -e <env> to target a non-default environment.\
""",
        example="beehive bu cpaas images delete <uuid> -e <env>",
        arguments=ARGS(
            [
                (["image"], {"help": "image id", "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.image

        # check type
        version = "v2.0"
        uri = f"/{version}/nws/serviceinsts/{oid}"
        res = self.cmp_get(uri).get("serviceinst")
        plugintype = res["plugintype"]
        if plugintype != "ComputeImage":
            print("Instance is not a ComputeImage")
        else:
            data = {"force": False, "propagate": True}
            uri = f"/v2.0/nws/serviceinsts/{oid}"
            self.cmp_delete(uri, data=data, timeout=180, entity=f"image {oid}")


class VolumeServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = "cpaas"
        stacked_type = "nested"
        label = "volumes"
        description = "volume service management"
        help = "volume service management"

        cmp = {"baseuri": "/v1.0/nws", "subsystem": "service"}

    @ex(
        help="load volumes from resources",
        description="""\
This CLI command loads volumes from resources. \
It retrieves volume information from the configured resources and loads them into the platform \
so they can be used to provision applications and services. \
No required arguments as the volumes will be loaded based on the configured resources.\
""",
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
                    ["volume_name"],
                    {
                        "help": "name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["volume_resource_id"],
                    {
                        "help": "resource volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def load(self):
        name = self.app.pargs.volume_name
        account_id = self.get_account(self.app.pargs.account).get("uuid")
        resource_id = self.app.pargs.volume_resource_id
        data = {
            "serviceinst": {
                "name": name,
                "account_id": account_id,
                "plugintype": "ComputeVolume",
                "container_plugintype": "ComputeService",
                "resource_id": resource_id,
            }
        }
        uri = "/v2.0/nws/serviceinsts/import"
        self.cmp_post(uri, data=data)
        self.app.render({"msg": f"import service plugin instance {name}"})

    @ex(
        help="list volumes",
        description="""\
This command lists all the volumes for the specified account. \
If no account is specified, it will list volumes for the current account.\
""",
        example="beehive bu cpaas volumes list -accounts xxxx",
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
                    ["-volumes"],
                    {
                        "help": "list of volume id comma separated",
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
        params = ["accounts", "volumes"]
        mappings = {
            "accounts": self.get_account_ids,
            "tags": lambda x: x.split(","),
            "volumes": lambda x: x.split(","),
        }
        aliases = {
            "accounts": "owner-id.N",
            "volumes": "volume-id.N",
            "tags": "tag-key.N",
            "size": "MaxResults",
            "page": "NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)

        uri = f"{self.baseuri}/computeservices/volume/describevolumes"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeVolumesResponse")
            resp = {
                "count": len(res.get("volumesSet")),
                "page": page,
                "total": res.get("nvl-volumeTotal"),
                "sort": {"field": "id", "order": "asc"},
                "volumes": res.get("volumesSet"),
            }

            headers = [
                "id",
                "name",
                "state",
                "size",
                "type",
                "account",
                "platform",
                "creation",
                "instance",
            ]
            fields = [
                "volumeId",
                "nvl-name",
                "status",
                "size",
                "volumeType",
                "nvl-volumeOwnerAlias",
                "nvl-hypervisor",
                "createTime",
                "attachmentSet.0.instanceId",
            ]
            self.app.render(resp, key="volumes", headers=headers, fields=fields, maxsize=45)

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="DescribeVolumesResponse.nvl-volumeTotal",
            key_list_name="DescribeVolumesResponse.volumesSet",
            fn_render=render,
        )

    @ex(
        help="get volume",
        description="""\
This command retrieves information about a specific volume by specifying its ID. \
It requires the volume ID as the only required argument. \
The command will return details of the requested volume such as its ID, name, size, etc.\
""",
        example="beehive bu cpaas volumes get <uuid>",
        arguments=ARGS(
            [
                (["volume"], {"help": "volume id", "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        volume_id = self.app.pargs.volume
        if self.is_uuid(volume_id):
            data = {"VolumeId.N": [volume_id]}
        elif self.is_name(volume_id):
            data = {"Nvl_Name.N": [volume_id]}

        uri = f"{self.baseuri}/computeservices/volume/describevolumes"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeVolumesResponse.volumesSet", default={})
        if len(res) > 0:
            res = res[0]
            # if self.is_output_text():
            #     self.app.render(res, details=True, maxsize=100)
            # else:
            self.app.render(res, details=True, maxsize=100)
        else:
            raise Exception(f"volume {volume_id} was not found")

    @ex(
        help="get volumes types",
        description="""\
This command is used to retrieve the available volume types that can be used when provisioning volumes on the Nivola \
CMP CPAAS platform. Volume types determine things like the size of the volume, the type of storage (SSD, HDD etc.), \
and other performance characteristics. \
The command does not require any arguments as it simply lists out the available volume types without filtering or \
operating on a specific volume.\
""",
        example="beehive bu cpaas volumes types <uuid>",
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
        uri = "/v2.0/nws/computeservices/volume/describevolumetypes"
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeVolumeTypesResponse")
        page = self.app.pargs.page
        resp = {
            "count": len(res.get("volumeTypesSet")),
            "page": page,
            "total": res.get("volumeTypesTotal"),
            "sort": {"field": "id", "order": "asc"},
            "types": res.get("volumeTypesSet"),
        }
        headers = ["id", "volume_type", "desc"]
        fields = ["uuid", "name", "description"]
        self.app.render(resp, key="types", headers=headers, fields=fields)

    @ex(
        help="create a volume",
        description="""
This command creates a volume with the specified name, account id, availability zone, type and size. \
The required arguments are the volume name, parent account id, availability zone, type and size.\
""",
        example="beehive bu cpaas volumes add xxxxx aaaaa azazZ <vol_type> ##",
        arguments=ARGS(
            [
                (["name"], {"help": "volume name", "action": "store", "type": str}),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["availability_zone"],
                    {
                        "help": "volume availability_zone",
                        "action": "store",
                        "type": str,
                    },
                ),
                (["type"], {"help": "volume type", "action": "store", "type": str}),
                (["size"], {"help": "volume size", "action": "store", "type": str}),
                (
                    ["-iops"],
                    {
                        "help": "volume iops",
                        "action": "store",
                        "type": int,
                        "default": -1,
                    },
                ),
                (
                    ["-hypervisor"],
                    {
                        "help": "volume hypervisor. Can be: openstack or vsphere [default=vsphere]",
                        "action": "store",
                        "type": str,
                        "default": "vsphere",
                    },
                ),
            ]
        ),
    )
    def add(self):
        name = self.app.pargs.name
        account = self.get_account(self.app.pargs.account).get("uuid")
        itype = self.get_service_definition(self.app.pargs.type)
        size = self.app.pargs.size
        iops = self.app.pargs.iops
        zone = self.app.pargs.availability_zone
        hypervisor = self.app.pargs.hypervisor

        data = {
            "Nvl_Name": name,
            "owner-id": account,
            "VolumeType": itype,
            "Size": size,
            "Iops": iops,
            "AvailabilityZone": zone,
            "MultiAttachEnabled": False,
            "Encrypted": False,
            "Nvl_Hypervisor": hypervisor,
        }
        uri = f"{self.baseuri}/computeservices/volume/createvolume"
        res = self.cmp_post(uri, data={"volume": data}, timeout=600)
        res = dict_get(res, "CreateVolumeResponse.volumeId")
        self.wait_for_service(res)
        self.app.render({"msg": f"add volume: {res}"})

    @ex(
        help="delete a volume",
        description="""\
This command deletes a volume by specifying its id. The volume id is a required argument for this command to identify \
the volume to be deleted. An optional -y flag can also be provided to skip confirmation prompt for deleting the volume.\
""",
        example="beehive bu cpaas volumes delete <uuid>",
        arguments=ARGS(
            [
                (["volume"], {"help": "volume id", "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        volume_id = self.app.pargs.volume
        if self.is_name(volume_id):
            raise Exception("only volume id is supported")
        data = {"VolumeId": volume_id}
        uri = f"{self.baseuri}/computeservices/volume/deletevolume"
        self.cmp_delete(uri, data=data, timeout=600, entity=f"volume {volume_id}")
        self.wait_for_service(volume_id, accepted_state="DELETED")

    @ex(
        help="attach a volume to an instance",
        description="""\
This command attaches a volume to an instance. \
It requires the volume ID and instance ID as arguments to identify the specific volume and instance to attach.\
""",
        example="""\
beehive bu cpaas volumes attach <uuid> <uuid>\
""",
        arguments=ARGS(
            [
                (["volume"], {"help": "volume id", "action": "store", "type": str}),
                (["instance"], {"help": "instance id", "action": "store", "type": str}),
            ]
        ),
    )
    def attach(self):
        volume = self.app.pargs.volume
        instance = self.app.pargs.instance
        data = {"InstanceId": instance, "VolumeId": volume, "Device": "/dev/sda"}
        uri = f"{self.baseuri}/computeservices/volume/attachvolume"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(volume)
        self.app.render({"msg": f"attach volume {volume} to instance {instance}"})

    @ex(
        help="detach a volume to an instance",
        description="""
This command detaches a volume from an instance. \
It requires the volume ID and instance ID as arguments to identify the specific volume and instance to detach.\
""",
        example="""\
beehive bu cpaas volumes detach <uuid> <uuid>\
""",
        arguments=ARGS(
            [
                (["volume"], {"help": "volume id", "action": "store", "type": str}),
                (["instance"], {"help": "instance id", "action": "store", "type": str}),
            ]
        ),
    )
    def detach(self):
        volume = self.app.pargs.volume
        instance = self.app.pargs.instance
        data = {"InstanceId": instance, "VolumeId": volume, "Device": "/dev/sda"}
        uri = f"{self.baseuri}/computeservices/volume/detachvolume"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(volume)
        self.app.render({"msg": f"detach volume {volume} to instance {instance}"})


class VmServiceController(BusinessControllerChild):
    host_groups = ["oracle", "amco", "sirmet"]

    class Meta:
        stacked_on = "cpaas"
        stacked_type = "nested"
        label = "vms"
        description = "virtual machine service management"
        help = "virtual machine service management"

        cmp = {"baseuri": "/v2.0/nws", "subsystem": "service"}

    @ex(
        help="List virtual machine",
        description="""\
This command lists the virtual machines under the specified account. No arguments are required. \
The -accounts flag can be used to filter the VMs by a specific account. \
The -e <env> filters VMs by environment like pod, region etc.\
""",
        example="beehive bu cpaas vms list -accounts xxxxx",
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
                        "help": "list of vm id comma separated",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "vm name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-names"],
                    {
                        "help": "vm name pattern",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-types"],
                    {
                        "help": "list of type comma separated",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-launch_time"],
                    {
                        "help": "launch time interval e.g. 2021-01-30T:2021-01-31T",
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
                    ["-states"],
                    {
                        "help": "list of instance state comma separated",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sg"],
                    {
                        "help": "list of security group id comma separated e.g. pending, running, error",
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
                    ["-services"],
                    {
                        "help": "print instance service enabling e.g. backup, monitoring",
                        "action": "store_true",
                    },
                ),
            ]
        ),
    )
    def list(self):
        services = self.app.pargs.services
        params = [
            "accounts",
            "ids",
            "types",
            "tags",
            "sg",
            "name",
            "names",
            "launch_time",
            "states",
        ]
        mappings = {
            "accounts": self.get_account_ids,
            "tags": lambda x: x.split(","),
            "types": lambda x: x.split(","),
            "ids": lambda x: x.split(","),
            "name": lambda x: x.split(","),
            "names": lambda x: "%" + x + "%",
            "sg": lambda x: x.split(","),
            "launch_time": lambda x: x.split(","),
            "states": lambda x: x.split(","),
        }
        aliases = {
            "accounts": "owner-id.N",
            "ids": "instance-id.N",
            "types": "instance-type.N",
            "name": "name.N",
            "names": "name-pattern",
            "tags": "tag-key.N",
            "sg": "instance.group-id.N",
            "launch_time": "launch-time.N",
            "states": "instance-state-name.N",
            "size": "MaxResults",
            "page": "NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = f"{self.baseuri}/computeservices/instance/describeinstances"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeInstancesResponse")
            res = res.get("reservationSet")[0]
            resp = {
                "count": len(res.get("instancesSet")),
                "page": page,
                "total": res.get("nvl-instanceTotal"),
                "sort": {"field": "id", "order": "asc"},
                "instances": res.get("instancesSet"),
            }

            headers = [
                "id",
                "name",
                "account",
                "type",
                "state",
                "availabilityZone",
                "privateIp",
                "image",
                "subnet",
                "sg",
                "hypervisor",
                "launchTime",
            ]
            fields = [
                "instanceId",
                "nvl-name",
                "nvl-ownerAlias",
                "instanceType",
                "instanceState.name",
                "placement.availabilityZone",
                "privateIpAddress",
                "nvl-imageName",
                "nvl-subnetName",
                "groupSet.0.groupId",
                "hypervisor",
                "launchTime",
            ]
            if services is True:
                headers = [
                    "id",
                    "name",
                    "account",
                    "state",
                    "availabilityZone",
                    "privateIp",
                    "backup",
                    "monitoring",
                    "logging",
                    "target_groups",
                ]
                fields = [
                    "instanceId",
                    "nvl-name",
                    "nvl-ownerAlias",
                    "instanceState.name",
                    "placement.availabilityZone",
                    "privateIpAddress",
                    "nvl-BackupEnabled",
                    "nvl-MonitoringEnabled",
                    "nvl-LoggingEnabled",
                    "nvl-targetGroups",
                ]

            transform = {"instanceState.name": self.color_error}
            self.app.render(
                resp,
                key="instances",
                headers=headers,
                fields=fields,
                transform=transform,
                maxsize=40,
            )

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="DescribeInstancesResponse.reservationSet.0.nvl-instanceTotal",
            key_list_name="DescribeInstancesResponse.reservationSet.0.instancesSet",
            fn_render=render,
        )

    @ex(
        help="list all virtual machines",
        description="""\
This command lists all virtual machines between the start and end range provided as required arguments. \
The start and end arguments specify the lower and upper bounds of the vm range to list respectively.\
""",
        example="beehive bu cpaas vms list-all",
        arguments=ARGS(
            [
                (
                    ["start"],
                    {
                        "help": "vms range lower bound",
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["end"],
                    {
                        "help": "vms range upper bound",
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

        def get_instance(page, size):
            data = {"MaxResults": size, "NextToken": page}
            uri = f"{self.baseuri}/computeservices/instance/describeinstances"
            res = self.cmp_get(uri, data=urlencode(data, doseq=True))
            res = res.get("DescribeInstancesResponse").get("reservationSet")[0]
            total = res.get("nvl-instanceTotal")
            res = res.get("instancesSet")
            for item in res:
                block_devices = item.pop("blockDeviceMapping", [])
                instance_type = item.pop("nvl-InstanceTypeExt", {})
                item["vcpus"] = instance_type.get("vcpus")
                item["memory"] = instance_type.get("memory")
                item["disk"] = sum(dict_get(b, "ebs.volumeSize") for b in block_devices)
                # get account triplet, i.e. org.div.account
                account_uuid = item.get("nvl-ownerId")
                if account_uuid in account_d:
                    account_triplet = account_d[account_uuid]
                else:
                    account_name, div_uuid = get_account(account_uuid)
                    div_name, org_uuid = get_division(div_uuid)
                    org_name = get_organization(org_uuid)
                    account_triplet = f"{org_name}.{div_name}.{account_name}"
                    account_d[account_uuid] = account_triplet
                item["nvl-ownerAlias"] = account_triplet

            return res, total

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
            "account",
            "state",
            "privateIp",
            "fqdn",
            "image",
            "avz",
            "subnet",
            "type",
            "vcpus",
            "memory",
            "disk",
            "hypervisor",
            "creation",
        ]
        fields = [
            "instanceId",
            "nvl-name",
            "nvl-ownerAlias",
            "instanceState.name",
            "privateIpAddress",
            "dnsName",
            "nvl-imageName",
            "placement.availabilityZone",
            "nvl-subnetName",
            "instanceType",
            "vcpus",
            "memory",
            "disk",
            "hypervisor",
            "launchTime",
        ]
        resp = []
        out_format = self.format
        for page in range(first_page, last_page):
            print(f"getting vms from {page * size + 1} to {(page + 1) * size} ...")
            try:
                chunk_resp = get_instance(page, size)[0]
                if out_format == "text":
                    self.app.render(chunk_resp, headers=headers, fields=fields)
                else:
                    resp += chunk_resp
                print(f"got vms from {page * size + 1} to {(page + 1) * size}")
                # time.sleep(secs)
            except Exception as exc:
                print(exc)
                break
        if out_format == "json":
            self.app.render(resp, headers=headers, fields=fields)

    @ex(
        help="get virtual machine",
        description="""\
This command retrieves information about a specific virtual machine instance from the Nivola CMP CPAAS VMS service \
by its ID. The 'vm' argument is required and should contain the ID of the virtual machine to fetch details for.\
""",
        example="beehive bu cpaas vms get <uuid>",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def get(self):
        vm_id = self.app.pargs.vm
        if self.is_uuid(vm_id):
            data = {"instance-id.N": [vm_id]}
        elif self.is_name(vm_id):
            data = {"name.N": [vm_id]}

        uri = f"{self.baseuri}/computeservices/instance/describeinstances"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeInstancesResponse.reservationSet.0.instancesSet", default={})
        if len(res) > 0:
            res = res[0]
            if self.is_output_text():
                network = {}
                block_devices = res.pop("blockDeviceMapping", [])
                instance_type = res.pop("nvl-InstanceTypeExt", {})
                image = {
                    "id": res.pop("imageId", None),
                    "name": res.pop("nvl-imageName", None),
                }
                network["ip_address"] = res.pop("privateIpAddress", None)
                network["subnet"] = f'{res.pop("subnetId", None)} - {res.pop("nvl-subnetName", None)}'
                network["vpc"] = f'{res.pop("vpcId", None)} - {res.pop("nvl-vpcName", None)}'
                network["dns_name"] = res.pop("dnsName", None)
                network["dns_name"] = res.pop("dnsName", None)
                network["private_dns_name"] = res.pop("privateDnsName", None)
                sgs = res.pop("groupSet", [])
                self.app.render(res, details=True, maxsize=100)
                self.c("\ninstance type", "underline")
                headers = ["vcpus", "bandwidth", "memory", "disk_iops", "disk"]
                self.app.render(instance_type, headers=headers)
                self.c("\nimage", "underline")
                self.app.render(image, details=True)
                self.c("\nnetwork", "underline")
                self.app.render(network, details=True)
                print()
                self.app.render(sgs, headers=["groupId", "groupName"])
                self.c("\nblock device", "underline")
                headers = [
                    "deviceName",
                    "ebs.status",
                    "ebs.volumeSize",
                    "ebs.deleteOnTermination",
                    "ebs.volumeId",
                    "ebs.attachTime",
                ]
                self.app.render(block_devices, headers=headers)
            else:
                self.app.render(res, details=True, maxsize=100)
        else:
            raise Exception(f"virtual machine {vm_id} was not found")

    @ex(
        help="get virtual machine console",
        description="""\
This command gets the virtual machine console details by specifying the virtual machine id as an argument. \
It retrieves the console details like console type, port etc of the specified virtual machine.\
""",
        example="beehive bu cpaas vms console-get <uuid>",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def console_get(self):
        vm_id = self.app.pargs.vm
        data = {"InstanceId": vm_id}
        uri = "/v2.0/nws/computeservices/instance/getconsole"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "GetConsoleResponse.console", default={})
        self.app.render(res, details=True, maxsize=100)

    def __populate_block(self, disk_opt, e, hypervisor):
        ebs = {}
        if disk_opt is None:
            return {"Ebs": ebs}
        # Format <size>:<volume_type> (for all) or <volume_id>:<volume_type> (for boot only)
        disk_s = disk_opt.split(":")
        if len(disk_s) > 2:
            raise Exception(f"Disk invalid value {disk_opt}")
        if len(disk_s) > 1:
            # This might contain  <volume_type>
            second_part_disk_opt = disk_s[1]
            ebs = {"VolumeType": second_part_disk_opt}
        # This must contain <size> or <volume_id>
        first_part_disk_opt = disk_s[0]
        if first_part_disk_opt.isdigit():
            # Size
            ebs["VolumeSize"] = int(first_part_disk_opt)
        elif self.is_uuid(first_part_disk_opt):
            # Uuid is valid for boot disk only
            if e != 0:
                raise Exception(f"Disk invalid value {disk_opt}; volume_id is allow for boot disk only.")
            if hypervisor == "vsphere":
                raise Exception(f"Disk invalid value {disk_opt}; volume_id is not supported by vsphere.")
            # Volume Id
            ebs["Nvl_VolumeId"] = first_part_disk_opt
        else:
            msg = f"Disk invalid value {disk_opt}; firts part must be a <size>"
            if e == 0:
                msg += " or <volume_id>"
            raise Exception(msg)
        return {"Ebs": ebs}

    def __populate_blocks(self, boot_disk, disks, hypervisor):
        all_disks_opt = [boot_disk] + (disks.split(",") if disks is not None else [])
        return [self.__populate_block(disk_opt, e, hypervisor) for e, disk_opt in enumerate(all_disks_opt)]

    @ex(
        help="create a virtual machine",
        description="""\
This command creates a virtual machine with the specified name, account, type, subnet, image and security group.\
""",
        example=" beehive bu cpaas vms add ap1 digifert vm.m1.medium SubnetWEB-xxxxx Ubuntu22 SG-xxxx -sshkey xxxx",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "virtual machine name", "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["type"],
                    {"help": "virtual machine type", "action": "store", "type": str},
                ),
                (
                    ["subnet"],
                    {
                        "help": "virtual machine subnet id",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["image"],
                    {
                        "help": "virtual machine image id",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["sg"],
                    {
                        "help": "virtual machine security group id",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-sshkey"],
                    {
                        "help": "virtual machine ssh key name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-pwd"],
                    {
                        "help": "virtual machine admin/root password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-main-disk"],
                    {
                        "help": """\
optional main disk size configuration. \
Use <size> to set e default volume type e.g. "40". \
Use <size>:<volume_type> to set a non default volume type e.g. "5:vol.oracle". \
Use <volume_id>:<volume_type> to set a volume to clone e.g. "<uuid>:vol.gold".
""",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-other-disk"],
                    {
                        "help": """\
list of additional disk sizes comma separated. \
Use <size> to set the default volume type e.g. "40". \
Use <size>:<volume_type> to set a non default volume type e.g. "5:10" or "5:vol.oracle,10"\
""",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-hypervisor"],
                    {
                        "help": "virtual machine hypervisor. Can be: openstack or vsphere [default=vsphere]",
                        "action": "store",
                        "type": str,
                        "default": "vsphere",
                    },
                ),
                (
                    ["-host-group"],
                    {
                        "help": "virtual machine host group e.g. oracle",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-multi-avz"],
                    {
                        "help": "if set to False create vm to work only in the selected availability zone "
                        "[default=True]. Use when subnet cidr is public",
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
                (
                    ["-meta"],
                    {
                        "help": "virtual machine custom metadata",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-skip-main-vol-size-check"],
                    {
                        "help": "Skips checking if the main volume size is smaller than the template’s main volume.",
                        "action": "store_true",
                        "dest": "skip_main_vol_size_check",
                    },
                ),
                (
                    ["-private-ip"],
                    {
                        "help": "use to specify a value from the IPv4 address range of the subnet, ex. ###.###.###.###",
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
        account = self.get_account(self.app.pargs.account).get("uuid")
        itype = self.get_service_definition(self.app.pargs.type)
        subnet = self.get_service_instance(self.app.pargs.subnet, account_id=account)
        image = self.get_service_instance(self.app.pargs.image, account_id=account)
        sg = self.get_service_instance(self.app.pargs.sg, account_id=account)
        sshkey = self.app.pargs.sshkey
        pwd = self.app.pargs.pwd
        boot_disk = self.app.pargs.main_disk
        disks = self.app.pargs.other_disk
        hypervisor = self.app.pargs.hypervisor
        host_group = self.app.pargs.host_group
        multi_avz = self.app.pargs.multi_avz
        meta = self.app.pargs.meta
        check_main_vol_size = not self.app.pargs.skip_main_vol_size_check
        private_ip = self.app.pargs.private_ip

        if pwd is None:
            pwd = random_password(10)

        data = {
            "Name": name,
            "owner-id": account,
            "AdditionalInfo": "",
            "SubnetId": subnet,
            "InstanceType": itype,
            "AdminPassword": pwd,
            "ImageId": image,
            "SecurityGroupId.N": [sg],
            "Nvl_MultiAvz": multi_avz,
            "CheckMainVolSize": check_main_vol_size,
        }

        # set hypervisor
        if hypervisor is not None:
            if hypervisor not in ("openstack", "vsphere"):
                raise Exception("Supported hypervisor are openstack and vsphere")
            data["Nvl_Hypervisor"] = hypervisor

        # set blocks
        blocks = self.__populate_blocks(boot_disk, disks, hypervisor)
        data["BlockDeviceMapping.N"] = blocks

        # set sshkey
        if sshkey is not None:
            data["KeyName"] = sshkey

        # set host_group
        if host_group is not None:
            if hypervisor == "vsphere" and host_group not in VmServiceController.host_groups:
                raise Exception(f"Supported vsphere host groups are {VmServiceController.host_groups}")
            if hypervisor == "openstack" and host_group not in ["bck", "nobck"]:
                raise Exception('Supported openstack host group are "bck" and "nobck"')
            data["Nvl_HostGroup"] = host_group

        # set meta
        if meta is not None:
            data["Nvl_Metadata"] = {}
            kvs = meta.split(",")
            for kv in kvs:
                k, v = kv.split(":")
                data["Nvl_Metadata"][k] = v

        if private_ip is not None:
            data["PrivateIpAddress"] = private_ip

        uri = f"{self.baseuri}/computeservices/instance/runinstances"
        res = self.cmp_post(uri, data={"instance": data}, timeout=600)
        uuid = dict_get(res, "RunInstanceResponse.instancesSet.0.instanceId")
        self.wait_for_service(uuid)
        self.app.render({"msg": f"add virtual machine: {uuid}"})

    def _get_instance(self, vm_id):
        if self.is_uuid(vm_id):
            data = {"instance-id.N": [vm_id]}
        elif self.is_name(vm_id):
            data = {"name.N": [vm_id]}

        uri = f"{self.baseuri}/computeservices/instance/describeinstances"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeInstancesResponse.reservationSet.0.instancesSet", default={})
        if len(res) != 1:
            raise Exception(f"no valid vm found for id {vm_id}")
        return res[0]

    @ex(
        help="clone a virtual machine",
        description="""\
This command is used to clone an existing virtual machine. \
It requires the name of the new cloned virtual machine and the ID of the virtual machine to clone. \
Optional arguments can also be provided like the account, subnet, SSH key, password, security group and environment \
to use for the cloned virtual machine.\
""",
        example="""\
beehive bu cpaas vms clone new-cloned-vm <uuid> -e <env>; \
beehive bu cpaas vms clone new-cloned-vm <uuid>  -account <uuid> -subnet <uuid> -sg <uuid> -e <env>\
""",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "virtual machine name", "action": "store", "type": str},
                ),
                (
                    ["id"],
                    {
                        "help": "id of the virtual machine to clone",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-account"],
                    {
                        "help": "target account id for cloning (default is the same account of the vm to clone)",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "virtual machine type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subnet"],
                    {
                        "help": "virtual machine subnet id (this must exist in the target account)",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sg"],
                    {
                        "help": "virtual machine security group id (this must exist in the target account)",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sshkey"],
                    {
                        "help": "virtual machine ssh key name (this must exist in the target account)",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-pwd"],
                    {
                        "help": "admin/root password of the virtual machine to clone (required for unmanaged accounts)",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-multi-avz"],
                    {
                        "help": "if set to False create vm to work only in the selected availability zone "
                        "[default=True]. Use when subnet cidr is public",
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
                (
                    ["-meta"],
                    {
                        "help": "virtual machine custom metadata",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def clone(self):
        pargs = self.app.pargs
        vm_id = pargs.id
        account = pargs.account
        itype = pargs.type
        subnet = pargs.subnet
        sg = pargs.sg
        sshkey = pargs.sshkey
        meta = pargs.meta

        # get original vm
        vm = self._get_instance(vm_id)
        image_name = dict_get(vm, "nvl-imageName")
        hypervisor = dict_get(vm, "hypervisor")

        if account is None:
            account = dict_get(vm, "nvl-ownerId")
        else:
            account = self.get_account(self.app.pargs.account).get("uuid")

        image = self.get_service_instance(image_name, account_id=account)
        if itype is None:
            itype = dict_get(vm, "instanceType")
        itype = self.get_service_definition(itype)
        if subnet is None:
            subnet = dict_get(vm, "subnetId")
        else:
            subnet = self.get_service_instance(subnet, account_id=account)

        sgg = None
        if sg is None:
            sgg = [a["groupId"] for a in vm.get("groupSet", [])]
        else:
            sgg = [self.get_service_instance(sg, account_id=account)]
        if sshkey is None:
            sshkey = dict_get(vm, "keyName")

        # set disks
        blocks = []
        for disk in vm.get("blockDeviceMapping", []):
            block = {
                "VolumeSize": dict_get(disk, "ebs.volumeSize"),
            }
            if hypervisor == "openstack":
                # must be passed because openstack clones the volume
                block["Nvl_VolumeId"] = dict_get(disk, "ebs.volumeId")
            blocks.append({"Ebs": block})
        data = {
            "Name": self.app.pargs.name,
            "InstanceId": vm_id,
            "owner-id": account,
            "SubnetId": subnet,
            "InstanceType": itype,
            "AdminPassword": self.app.pargs.pwd,
            "ImageId": image,
            "SecurityGroupId.N": sgg,
            "Nvl_MultiAvz": pargs.multi_avz,
            "Nvl_Hypervisor": hypervisor,
            "BlockDeviceMapping.N": blocks,
        }

        if sshkey is not None:
            data["KeyName"] = sshkey

        # set meta
        if meta is not None:
            data["Nvl_Metadata"] = {}
            kvs = meta.split(",")
            for kv in kvs:
                k, v = kv.split(":")
                data["Nvl_Metadata"][k] = v

        uri = f"{self.baseuri}/computeservices/instance/cloneinstances"
        res = self.cmp_post(uri, data={"instance": data}, timeout=600)
        uuid = dict_get(res, "CloneInstanceResponse.instancesSet.0.instanceId")
        self.wait_for_service(uuid)
        self.app.render({"msg": f"add virtual machine: {uuid}"})

    @ex(
        help="import a virtual machine",
        description="""\
This command imports a virtual machine into a specified container. \
It requires the container ID, VM name, physical VM ID from the provider, provider image ID, \
and VM password as required arguments.\
""",
        example="""\
beehive bu cpaas vms load xxxxxx xxxxx vm-#### Ubuntu20 -sshkey xxxxx xxxxx xxxx\
""",
        arguments=ARGS(
            [
                (
                    ["container"],
                    {
                        "help": "container id where import virtual machine",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["name"],
                    {"help": "virtual machine name", "action": "store", "type": str},
                ),
                (
                    ["vm"],
                    {
                        "help": "physical id of the virtual machine to import",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["os"],
                    {
                        "metavar": "os",
                        "help": "operative system of the virtual machine to import: win, linux",
                        "action": "store",
                        "type": str,
                        "choices": ["win", "linux"],
                    },
                ),
                (
                    ["image"],
                    {"help": "provider image id", "action": "store", "type": str},
                ),
                (
                    ["pwd"],
                    {
                        "help": "virtual machine password",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["account"],
                    {
                        "help": "parent account id",
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
        os = self.app.pargs.os
        image_id = self.app.pargs.image
        pwd = self.app.pargs.pwd
        account = self.get_account(self.app.pargs.account)
        account_id = account.get("uuid")
        acronym = account.get("acronym")
        if os == "linux" and acronym is not None and acronym != "":
            hostname = f"{name}-{acronym}"
        else:
            hostname = name

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
        res_name = f"{name}-{id_gen()}"
        print(f"load resource instance res_name: {res_name}")
        self.api.resource.provider.instance.load(
            "ResourceProvider01",
            res_name,
            physical_resource,
            pwd,
            image_id,
            hostname=hostname,
        )
        # - get resource
        res = self.api.resource.provider.instance.get(res_name)
        flavor = dict_get(res, "flavor.name")
        resource_uuid = res["uuid"]

        # print('import physical resource %s as provider resource %s' % (physical_resource, resource))

        # import provider resource as compute instance
        # - get compute service
        # res = self.api.business.service.instance.list(account_id=account_id, flag_container=True,
        #                                               plugintype='ComputeService')
        # cs = res.get('serviceinsts')[0]['uuid']

        # - import service instance
        print(f"load service instance res_name: {res_name}")
        res = self.api.business.service.instance.load(
            name,
            account_id,
            "ComputeInstance",
            "ComputeService",
            resource_uuid,
            service_definition_id=flavor,
        )
        print(f"import provider resource as compute instance {res}")

    @ex(
        help="update a virtual machine",
        description="""\
This CLI command updates a virtual machine on the Nivola Cloud platform. \
The 'vm' argument is required and specifies the ID of the virtual machine to update.\
""",
        example="""\
beehive bu cpaas vms update <uuid> vm.m4.2xlarge;beehive bu cpaas vms update\
""",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["-type"],
                    {
                        "help": "virtual machine type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sg_add"],
                    {
                        "help": "virtual machine security group id to add",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sg_del"],
                    {
                        "help": "virtual machine security group id to remove",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def update(self):
        uuid = self.app.pargs.vm
        vmtype = self.app.pargs.type
        sg_add = self.app.pargs.sg_add
        sg_del = self.app.pargs.sg_del
        sg = None
        data = {"InstanceId": uuid, "InstanceType": vmtype}
        if sg_add is not None:
            sg = f"{sg_add}:ADD"
            data["GroupId.N"] = [sg]
        elif sg_del is not None:
            sg = f"{sg_del}:DEL"
            data["GroupId.N"] = [sg]
        data = {"instance": data}
        uri = f"{self.baseuri}/computeservices/instance/modifyinstanceattribute"
        self.cmp_put(uri, data=data, timeout=600).get("ModifyInstanceAttributeResponse")
        self.wait_for_service(uuid)
        self.app.render({"msg": f"update virtual machine: {uuid}"})

    @ex(
        help="refresh virtual machine state",
        description="""\
This command refreshes the state of a virtual machine managed by Nivola CMP CPaaS. \
It requires the ID, UUID or name of the virtual machine as the only required argument. \
By refreshing the state, it updates the VM's reported state in Nivola CMP CPaaS to match \
the actual state on the hypervisor.\
""",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "virtual machine id, uuid or name",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def refresh_state(self):
        oid = self.app.pargs.id
        res = self.api.business.cpaas.instance.get(oid)
        resource_uuid = res.get("nvl-resourceId")
        self.api.resource.provider.instance.del_cache(resource_uuid)
        print(f"state refreshed for virtual machine {oid}")

    @ex(
        help="delete a virtual machine",
        description="""\
This command deletes a virtual machine. It requires the virtual machine id as the only required argument. \
The virtual machine id uniquely identifies the vm to delete from the cpaas environment.\
""",
        example="beehive bu cpaas vms delete <uuid> -e <env>",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete(self):
        vm_id = self.app.pargs.vm
        if self.is_uuid(vm_id):
            data = {"instance-id.N": [vm_id]}
        elif self.is_name(vm_id):
            data = {"name.N": [vm_id]}
        uri = f"{self.baseuri}/computeservices/instance/describeinstances"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeInstancesResponse.reservationSet.0.instancesSet")
        if len(res) == 0:
            raise Exception(f"virtual machine {vm_id} was not found")
        uuid = res[0].get("instanceId")

        data = {"InstanceId.N": [uuid]}
        uri = f"{self.baseuri}/computeservices/instance/terminateinstances"
        entity = f"instance {vm_id}"
        self.cmp_delete(uri, data=data, timeout=600, entity=entity, output=False)
        state = self.wait_for_service(uuid, accepted_state="DELETED")
        if state == "DELETED":
            print(f"{entity} deleted")

    @ex(
        help="start a virtual machine",
        description="""\
This command starts a virtual machine that is currently stopped. \
It requires the virtual machine ID as the only required argument to identify the specific virtual machine to start. \
Starting a stopped virtual machine will allocate necessary resources like CPU, memory, disk, and network to power \
it on and make it available.\
""",
        example="beehive bu cpaas vms start <uuid> -e <env>",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["-schedule"],
                    {
                        "help": "schedule definition. Pass as json file using crontab or timedelta syntax. "
                        'e.g. {"type": "timedelta", "minutes": 1}',
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def start(self):
        vm_id = self.app.pargs.vm
        schedule = self.app.pargs.schedule
        data = {"InstanceId.N": [vm_id]}
        if schedule is not None:
            schedule = load_config(schedule)
            data["Schedule"] = schedule
        uri = f"{self.baseuri}/computeservices/instance/startinstances"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({"msg": f"start virtual machine {vm_id}"})

    @ex(
        help="stop a virtual machine",
        description="""\
This command stops a running virtual machine instance on the Nivola CMP Cloud Platform. \
It requires the virtual machine ID as the only required argument. \
Upon execution, it sends a signal to the hypervisor managing the specified VM to power it off \
or shut it down gracefully.\
""",
        example="beehive bu cpaas vms stop <uuid>",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["-schedule"],
                    {
                        "help": "schedule definition. Pass as json file using crontab or timedelta syntax. "
                        'e.g. {"type": "timedelta", "minutes": 1}',
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def stop(self):
        vm_id = self.app.pargs.vm
        schedule = self.app.pargs.schedule
        data = {"InstanceId.N": [vm_id]}
        if schedule is not None:
            schedule = load_config(schedule)
            data["Schedule"] = schedule
        uri = f"{self.baseuri}/computeservices/instance/stopinstances"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({"msg": f"stop virtual machine {vm_id}"})

    @ex(
        help="reboot a virtual machine",
        description="""\
This command reboots a virtual machine. \
It requires the virtual machine ID as the only required argument to identify the virtual machine to reboot.\
""",
        example="beehive bu cpaas vms reboot <uuid>",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["-schedule"],
                    {
                        "help": "schedule definition. Pass as json file using crontab or timedelta syntax. "
                        'e.g. {"type": "timedelta", "minutes": 1}',
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def reboot(self):
        vm_id = self.app.pargs.vm
        schedule = self.app.pargs.schedule
        data = {"InstanceId.N": [vm_id]}
        if schedule is not None:
            schedule = load_config(schedule)
            data["Schedule"] = schedule
        uri = f"{self.baseuri}/computeservices/instance/rebootinstances"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({"msg": f"reboot virtual machine {vm_id}"})

    @ex(
        help="enable virtual machine monitoring",
        description="""\
This command enables monitoring on the specified virtual machine. \
It requires the virtual machine ID as the only required argument to identify the target virtual machine \
for which monitoring needs to be enabled.\
""",
        example="beehive bu cpaas vms enable-monitoring <uuid>",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
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
                (
                    ["--continues"],
                    {
                        "help": "continue use command",
                        "action": "store_true",
                        "dest": "continues",
                    },
                ),
            ]
        ),
    )
    def enable_monitoring(self):
        vm_id = self.app.pargs.vm
        templates = self.app.pargs.templates
        if getattr(self.app.pargs, "continues", False) is False:
            self.app.render(
                {"msg": f'deprecated command - use "beehive bu maas monitor-instances add" ({CONTINUE_NOTICE})'}
            )
        else:
            data = {"InstanceId.N": [vm_id], "Nvl_Templates": templates}
            uri = f"{self.baseuri}/computeservices/instance/monitorinstances"
            self.cmp_put(uri, data=data, timeout=600)
            self.wait_for_service(vm_id)
            self.app.render({"msg": f"enable virtual machine {vm_id} monitoring"})

    @ex(
        help="disable virtual machine monitoring",
        description="""\
This command disables monitoring for the specified virtual machine. \
Monitoring collects metrics like CPU and memory usage from the VM which are useful for troubleshooting \
performance issues. By disabling monitoring, these metrics will no longer be collected for the VM.\
""",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["--continues"],
                    {
                        "help": "continue use command",
                        "action": "store_true",
                        "dest": "continues",
                    },
                ),
            ]
        ),
    )
    def disable_monitoring(self):
        vm_id = self.app.pargs.vm
        if getattr(self.app.pargs, "continues", False) is False:
            self.app.render(
                {"msg": f'deprecated command - use "beehive bu maas monitor-instances delete" ({CONTINUE_NOTICE}) '}
            )
        else:
            data = {"InstanceId.N": [vm_id]}
            uri = f"{self.baseuri}/computeservices/instance/unmonitorinstances"
            self.cmp_put(uri, data=data, timeout=600)
            self.wait_for_service(vm_id)
            self.app.render({"msg": f"disable virtual machine {vm_id} monitoring"})

    @ex(
        help="enable virtual machine logging",
        description="""\
This command enables logging for the specified virtual machine. \
It requires the virtual machine ID as the only required argument to identify the target virtual machine \
for which logging needs to be enabled.\
""",
        example="beehive bu cpaas vms enable-logging xxxxx",
        arguments=ARGS(
            [
                (
                    ["vm"],
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
                (
                    ["--continues"],
                    {
                        "help": "continue use command",
                        "action": "store_true",
                        "dest": "continues",
                    },
                ),
            ]
        ),
    )
    def enable_logging(self):
        vm_id = self.app.pargs.vm
        files = self.app.pargs.files
        pipeline = self.app.pargs.pipeline
        if getattr(self.app.pargs, "continues", False) is False:
            self.app.render({"msg": f'deprecated command - use "beehive bu logaas instances add" ({CONTINUE_NOTICE}) '})
        else:
            data = {"InstanceId.N": [vm_id], "Files": files, "Pipeline": pipeline}
            uri = f"{self.baseuri}/computeservices/instance/forwardloginstances"
            self.cmp_put(uri, data=data, timeout=600)
            self.wait_for_service(vm_id)
            self.app.render({"msg": f"enable virtual machine {vm_id} logging"})

    @ex(
        help="list virtual machine snapshots",
        description="""\
This command lists the snapshots of a virtual machine by its ID. \
Snapshots capture the state of the virtual machine at a point in time and allow restoring the machine to that state. \
The snapshots are listed with their ID, name, creation time and other metadata by default. \
The --notruncate option prevents truncating of long values in the output for a more complete listing.\
""",
        example="beehive bu cpaas vms snapshot-get <uuid> -e <env>",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def snapshot_get(self):
        vm_id = self.app.pargs.vm
        data = {"InstanceId.N": [vm_id]}
        uri = f"{self.baseuri}/computeservices/instance/describeinstancesnapshots"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True), timeout=600)
        res = res.get("DescribeInstanceSnapshotsResponse")
        res = res.get("instancesSet")
        resp = []
        for item in res:
            for snapshot in item["snapshots"]:
                snapshot["id"] = item["instanceId"]
                resp.append(snapshot)
        headers = ["id", "name", "status", "creation_date"]
        fields = ["snapshotId", "snapshotName", "snapshotStatus", "createTime"]
        self.app.render(resp, headers=headers, fields=fields, maxsize=45)

    @ex(
        help="add virtual machine snapshot",
        description="""\
This command adds a snapshot of a virtual machine. \
It requires the virtual machine ID as an argument to identify which VM to snapshot. \
Additional optional arguments like the snapshot name and external parameters can also be provided. \
Taking snapshots allows restoring VMs to previous points in time for backup/restore or testing purposes.\
""",
        example="beehive bu cpaas vms snapshot-add <uuid> xxxx -e <env>",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["snapshot"],
                    {
                        "help": "snapshot name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def snapshot_add(self):
        vm_id = self.app.pargs.vm
        snapshot = self.app.pargs.snapshot
        data = {"InstanceId.N": [vm_id], "SnapshotName": snapshot}
        uri = f"{self.baseuri}/computeservices/instance/createinstancesnapshots"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({"msg": f"add snapshot {snapshot} of virtual machine {vm_id}"})

    @ex(
        help="add virtual machine snapshot",
        description="""\
This command deletes a snapshot of a virtual machine. \
It requires the virtual machine ID as an argument to identify which machine's snapshot should be deleted.\
""",
        example="beehive bu cpaas vms snapshot-del <uuid>",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["snapshot"],
                    {
                        "help": "snapshot id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def snapshot_del(self):
        vm_id = self.app.pargs.vm
        snapshot = self.app.pargs.snapshot
        data = {"InstanceId.N": [vm_id], "SnapshotId": snapshot}
        uri = f"{self.baseuri}/computeservices/instance/deleteinstancesnapshots"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({"msg": f"delete snapshot {snapshot} of virtual machine {vm_id}"})

    @ex(
        help="revert virtual machine snapshot",
        description="""\
This command reverts a virtual machine to a previous snapshot state by ID. \
It requires the virtual machine ID as an argument.\
""",
        example="""\
beehive bu cpaas vms snapshot-revert <uuid> <uuid>\
""",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["snapshot"],
                    {
                        "help": "snapshot id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def snapshot_revert(self):
        vm_id = self.app.pargs.vm
        snapshot = self.app.pargs.snapshot
        data = {"InstanceId.N": [vm_id], "SnapshotId": snapshot}
        uri = f"{self.baseuri}/computeservices/instance/revertinstancesnapshots"
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({"msg": f"revert virtual machine {vm_id} to snapshot {snapshot}"})

    def __user_action(self, uuid, action, **user_params):
        params = {"Nvl_Action": action}
        params.update(user_params)
        data = {"InstanceId": uuid, "Nvl_User": params}
        data = {"instance": data}
        uri = f"{self.baseuri}/computeservices/instance/modifyinstanceattribute"
        self.cmp_put(uri, data=data, timeout=600).get("ModifyInstanceAttributeResponse")
        self.wait_for_service(uuid)
        self.app.render({"msg": f"update virtual machine: {uuid}"})

    @ex(
        help="add virtual machine user",
        description="""\
This command adds a new user to a virtual machine. \
It requires the virtual machine ID as an argument to specify which virtual machine the user will be added to. \
Adding a user allows that user to login to the virtual machine via SSH and access it remotely.\
""",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["name"],
                    {
                        "help": "user name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": "user password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ssh_key"],
                    {
                        "help": "ssh key id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def user_add(self):
        uuid = self.app.pargs.vm
        name = self.app.pargs.name
        pwd = self.app.pargs.pwd
        key = self.app.pargs.ssh_key
        self.__user_action(uuid, "add", Nvl_Name=name, Nvl_Password=pwd, Nvl_SshKey=key)

    @ex(
        help="delete virtual machine user",
        description="""\
This command deletes a user from a virtual machine. \
It requires the virtual machine ID as an argument to identify which virtual machine's user should be deleted.\
""",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["name"],
                    {
                        "help": "user name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def user_del(self):
        uuid = self.app.pargs.vm
        name = self.app.pargs.name
        self.__user_action(uuid, "delete", Nvl_Name=name)

    @ex(
        help="set virtual machine user password",
        description="""\
This command sets the password for the user on the specified virtual machine. \
It requires the virtual machine ID as the only required argument to identify the target virtual machine. \
The password will be set for the default user on that virtual machine.\
""",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["name"],
                    {
                        "help": "user name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": "user password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def user_password_set(self):
        uuid = self.app.pargs.vm
        name = self.app.pargs.name
        pwd = self.app.pargs.pwd
        self.__user_action(uuid, "set-password", Nvl_Name=name, Nvl_Password=pwd)

    @ex(
        help="get virtual machine types (flavor)",
        description="""\
This command is used to get virtual machine types (flavor) available in the cloud platform. \
It lists out the different types of virtual machines that can be provisioned with varying configurations like \
CPU, memory, storage etc. This helps the user to select the right type of VM depending on their workload requirements.\
""",
        example="beehive bu cpaas vms types get account -size -1;beehive bu cpaas vms types 16 -e <env>",
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
        uri = "/v2.0/nws/computeservices/instance/describeinstancetypes"
        res = self.cmp_get(uri, data=data)
        res = res.get("DescribeInstanceTypesResponse")
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
        help="get backup job restore points",
        description="""\
This command is used to get backup job restore points. \
It requires the virtual machine id and backup job id as required arguments to retrieve the restore points \
for a specific backup job of a virtual machine.\
""",
        example="""\
beehive bu cpaas vms backup-restore-point-get <uuid> \
-job <uuid> \
""",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["-vm"],
                    {
                        "help": "virtual machine id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-job"],
                    {"help": "job id", "action": "store", "type": str, "default": None},
                ),
                (
                    ["-restore_point"],
                    {
                        "help": "restore point id",
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
    def backup_restore_point_get(self):
        params = ["account", "vm", "job", "restore_point"]
        mappings = {
            "account": lambda x: self.get_account(x)["uuid"],
        }
        aliases = {
            "account": "owner-id",
            "vm": "InstanceId",
            "job": "JobId",
            "restore_point": "RestorePointId",
            "size": "MaxItems",
            "page": "Marker",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = "/v1.0/nws/computeservices/instancebackup/describebackuprestorepoints"
        res = self.cmp_get(uri, data=data, timeout=600)
        if self.is_output_text():
            restore_points = dict_get(res, "DescribeBackupRestorePointsResponse.restorePointSet")
            restore_point_total = dict_get(res, "DescribeBackupRestorePointsResponse.restorePointTotal")

            if self.app.pargs.restore_point is not None:
                if len(restore_points) > 0:
                    res = restore_points[0]
                    res.pop("metadata", [])
                    instances = res.pop("instanceSet", [])
                    self.app.render(res, details=True)

                    self.c("\ninstanceSet", "underline")
                    self.app.render(instances, fields=["uuid", "name"], headers=["id", "name"])
            else:
                # self.app.render(
                #     restore_points,
                #     headers=["id", "name", "desc", "type", "status", "created"],
                # )
                resp = {
                    "count": len(restore_points),
                    "page": 0,
                    "total": restore_point_total,
                    "sort": {"field": "creationDate", "order": "desc"},
                    "restore_points": restore_points,
                }

                headers = ["id", "name", "desc", "type", "status", "created"]
                fields = ["id", "name", "desc", "type", "status", "created"]
                transform = {}
                self.app.render(
                    resp,
                    key="restore_points",
                    headers=headers,
                    fields=fields,
                    maxsize=100,
                    transform=transform,
                )

        else:
            self.app.render(res, details=True)

    @ex(
        help="add backup job restore point",
        description="""\
This command adds a restore point for a backup job. \
A restore point represents a specific backup snapshot that can be used to restore data from. \
The account ID is required to identify the backup job account.\
""",
        example="beehive bu cpaas vms backup-restore-point-add ",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["job"],
                    {"help": "job id", "action": "store", "type": str, "default": None},
                ),
                (
                    ["name"],
                    {
                        "help": "restore point name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "restore point description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-full"],
                    {
                        "help": "backup type. If true make a full backup otherwise make an incremental backup",
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
            ]
        ),
    )
    def backup_restore_point_add(self):
        account = self.get_account(self.app.pargs.account).get("uuid")
        job_id = self.app.pargs.job
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        full = str2bool(self.app.pargs.full)

        data = {
            "owner-id": account,
            "JobId": job_id,
            "Name": name,
            "Desc": desc if desc is not None else name,
            "BackupFull": full,
        }

        uri = "/v1.0/nws/computeservices/instancebackup/createbackuprestorepoints"
        self.cmp_post(uri, data=data, timeout=600)
        # uuid = dict_get(res, 'CreateBackupRestorePoints.instanceBackupSet.0.instanceId')
        # self.wait_for_service(uuid)
        self.app.render({"msg": f"create new backup job {job_id} restore point"})

    @ex(
        help="delete backup job restore point",
        description="""\
This command deletes a specific restore point for a backup job. \
It requires the account ID and restore point ID as required arguments to identify the restore point to delete.\
""",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["job"],
                    {"help": "job id", "action": "store", "type": str, "default": None},
                ),
                (
                    ["restore_point"],
                    {"help": "restore point id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def backup_restore_point_del(self):
        account = self.get_account(self.app.pargs.account).get("uuid")
        job_id = self.app.pargs.job
        restore_point_id = self.app.pargs.restore_point

        data = {
            "owner-id": account,
            "JobId": job_id,
            "RestorePointId": restore_point_id,
        }

        uri = "/v1.0/nws/computeservices/instancebackup/deletebackuprestorepoints"
        self.cmp_delete(
            uri, data=data, timeout=600, entity=f"remove backup job {job_id} restore point {restore_point_id}"
        )
        # uuid = dict_get(res, vm_id)
        # self.wait_for_service(uuid)

    @ex(
        help="get virtual machine backup restores",
        description="""\
This command is used to get the details of a specific virtual machine backup restore point. \
It requires the virtual machine id and restore point id as required arguments to retrieve the restore details for \
that particular VM and restore point.\
""",
        arguments=ARGS(
            [
                (
                    ["vm"],
                    {"help": "virtual machine id", "action": "store", "type": str},
                ),
                (
                    ["restore_point"],
                    {"help": "restore point id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def backup_restore_get(self):
        vm_id = self.app.pargs.vm
        restore_point_id = self.app.pargs.restore_point
        data = {"InstanceId.N": [vm_id], "RestorePoint": restore_point_id}
        uri = "/v1.0/nws/computeservices/instancebackup/describebackuprestores"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True), timeout=600)
        res = dict_get(res, "DescribeBackupRestoresResponse.restoreSet")
        if len(res) > 0:
            res = res[0]["restores"]
            headers = [
                "id",
                "name",
                "desc",
                "time_taken",
                "size",
                "uploaded_size",
                "status",
                "progress_percent",
                "created",
            ]
            self.app.render(res, headers=headers)

    @ex(
        help="restore a virtual machine from backup",
        description="""\
This command restores a virtual machine from backup. \
It requires the restored virtual machine name, id of the virtual machine to clone from backup, \
and id of the restore point to use for restoring the virtual machine state.\
""",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "restored virtual machine name",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["id"],
                    {
                        "help": "id of the virtual machine to clone",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["restore_point"],
                    {"help": "id of restore point", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def backup_restore_add(self):
        name = self.app.pargs.name
        vm_id = self.app.pargs.id
        restore_point_id = self.app.pargs.restore_point

        data = {
            "InstanceId": vm_id,
            "RestorePointId": restore_point_id,
            "InstanceName": name,
        }

        uri = "/v1.0/nws/computeservices/instancebackup/createbackuprestores"
        res = self.cmp_post(uri, data={"instance": data}, timeout=600)
        uuid = dict_get(res, "CreateBackupRestoreResponse.instancesSet.0.instanceId")
        self.wait_for_service(uuid)
        self.app.render({"msg": f"restore virtual machine from backup: {uuid}"})

    @ex(
        help="get backup job name using naming convention",
        description="""\
This command gets the backup job name using the naming convention for a given account id. \
The account id is a required argument to identify the account whose backup job name needs to be retrieved.\
""",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
            ]
        ),
    )
    def backup_job_name_get(self):
        account_id = self.app.pargs.account
        account = self.get_account(account_id)
        account_uuid = account.get("uuid")
        account_name = account.get("name")

        data = {"account_id": account_uuid, "size": -1, "flag_container": True}
        serviceinsts = self.cmp_get("/v2.0/nws/serviceinsts", data=data).get("serviceinsts")

        core_service = serviceinsts[0]
        resource_uuid = core_service["resource_uuid"]

        uri = f"/v1.0/nrs/entities/{resource_uuid}"
        resource = self.cmp_get(uri).get("resource")
        compute_zone_name: str = resource["name"]
        compute_zone_code = compute_zone_name.replace("ComputeService-", "")

        job_name = f"BCK-{compute_zone_code}-{account_name}"
        print(job_name)

    @ex(
        help="from backup job name get related account (using naming convention)",
        description="""\
This command checks the provided backup job name and retrieves the related account using a naming convention. \
The backup job name is a required argument for this command to work.\
""",
        arguments=ARGS(
            [
                (["backup_job_name"], {"help": "backup job name", "action": "store", "type": str}),
            ]
        ),
    )
    def backup_job_name_check(self):
        backup_job_name = self.app.pargs.backup_job_name
        job_name = f"{backup_job_name}"

        if job_name.find("BCK") == 0:
            # replace "punto"
            job_name = job_name.replace(".", "-")
            # replace "spazio"
            job_name = job_name.replace(" ", "-")
            # replace "doppio trattino"
            job_name = job_name.replace("--", "-")
            # replace "BCK-ComputeService"
            job_name = job_name.replace("BCK-ComputeService-", "BCK-")
            # replace "BK-"
            job_name = job_name.replace("BK-", "BCK-")

            if job_name != backup_job_name:
                print("job name does not respect naming convention. Trying to retrieve information...")

            cz_id = job_name.split("-")[1]
            compute_zone_name = f"ComputeService-{cz_id}"
            uri = f"/v1.0/nrs/entities/{compute_zone_name}"
            resource = self.cmp_get(uri).get("resource")
            compute_zone_uuid: str = resource["uuid"]

            data = {"resource_uuid": compute_zone_uuid, "size": -1, "flag_container": True}
            serviceinsts = self.cmp_get("/v2.0/nws/serviceinsts", data=data).get("serviceinsts")
            # print("serviceinsts: %s" % serviceinsts)

            core_service = serviceinsts[0]
            account = core_service["account"]
            # print("account: %s" % account)
            account_name = account["name"]
            account_uuid = account["uuid"]
            print(f"job name related to account {account_name} ({account_uuid})")

            # get account
            data = ""
            uri_account = f"/v1.0/nws/accounts/{account_uuid}"
            account = self.cmp_get(uri_account, data).get("account")
            # account_name = account["name"]
            division_id = account["division_id"]

            # get division
            uri_division = f"/v1.0/nws/divisions/{division_id}"
            division = self.cmp_get(uri_division, data).get("division")
            division_name = division["name"]
            organization_id = division["organization_id"]

            # get organization
            uri_organization = f"/v1.0/nws/organizations/{organization_id}"
            organization = self.cmp_get(uri_organization, data).get("organization")
            organization_name = organization["name"]

            print(f"full account name {organization_name}.{division_name}.{account_name}")

        else:
            print("job name is not related to an account")

    @ex(
        help="get account virtual machine backup jobs",
        description="""\
This command is used to retrieve the list of backup jobs for virtual machines associated with a given account on \
the Nivola CMP CPAAS platform. \
It requires the account ID as a required argument. \
An optional '-hypervisor' argument can be provided to filter the results by a specific hypervisor like \
OpenStack, vSphere, or return all hypervisor types.\
""",
        example="beehive bu cpaas vms backup-job-list sdo3liv",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["-hypervisor"],
                    {
                        "help": "virtual machine hypervisor. Can be: openstack, vsphere, all (default)",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def backup_job_list(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get("uuid")
        data = {
            "owner-id.N": [account_id],
        }

        hypervisor = self.app.pargs.hypervisor

        if hypervisor is not None:
            data.update({"hypervisor": hypervisor})
        else:
            data.update({"hypervisor": "all"})

        uri = "/v1.0/nws/computeservices/instancebackup/describebackupjobs"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True), timeout=600)
        res = dict_get(res, "DescribeBackupJobsResponse.jobSet")
        headers = [
            "id",
            "name",
            "account",
            "hypervisor",
            "availabilityZone",
            "state",
            "enabled",
            "instances",
        ]
        fields = [
            "jobId",
            "name",
            "owner_id",
            "hypervisor",
            "availabilityZone",
            "jobState",
            "enabled",
            "instanceNum",
        ]
        self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="get account virtual machine backup job",
        description="""\
This command is used to retrieve details of a specific backup job for a virtual machine backup. \
It requires the account id and job id of the backup job as required arguments to uniquely identify \
and get information of the particular backup job.\
""",
        example="beehive bu cpaas vms backup-job-get cloudcmmi trilio_710_<uuid>",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (["job"], {"help": "job id", "action": "store", "type": str}),
            ]
        ),
    )
    def backup_job_get(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get("uuid")
        job_id = self.app.pargs.job
        data = {"owner-id.N": [account_id], "JobId": job_id}
        uri = "/v1.0/nws/computeservices/instancebackup/describebackupjobs"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True), timeout=600)
        res = dict_get(res, "DescribeBackupJobsResponse.jobSet.0")
        instances = res.pop("instanceSet", [])
        self.app.render(res, details=True)
        self.c("\ninstances", "underline")
        self.app.render(instances, headers=["uuid", "name"])

    @ex(
        help="add account virtual machine backup job",
        description="""\
Add account virtual machine backup job. \
This CLI command adds a backup job for virtual machines under a specific account. \
It requires the job name, account id, availability zone where the job runs and a comma separated list of instance ids \
to backup as required arguments. An optional description of the job can also be provided with the -desc argument.\
""",
        example="beehive bu cpaas vms backup-job-add provatrilio Acc_demo_nmsflike SiteTorino01  prova",
        arguments=ARGS(
            [
                (["name"], {"help": "job name", "action": "store", "type": str}),
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["zone"],
                    {"help": "job availability zone", "action": "store", "type": str},
                ),
                (
                    ["instance"],
                    {
                        "help": "comma separated list of instance id to add",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-hypervisor"],
                    {
                        "help": "job hypervisor [openstack]",
                        "action": "store",
                        "type": str,
                        "default": "openstack",
                    },
                ),
                (
                    ["-policy"],
                    {
                        "help": "job hypervisor [bk-job-policy-7-7-retention]",
                        "action": "store",
                        "type": str,
                        "default": "bk-job-policy-7-7-retention",
                    },
                ),
                (
                    ["-desc"],
                    {"help": "job description", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def backup_job_add(self):
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        account = self.app.pargs.account
        account_id = self.get_account(account).get("uuid")
        zone = self.app.pargs.zone
        instance = self.app.pargs.instance
        policy = self.app.pargs.policy
        hypervisor = self.app.pargs.hypervisor

        data = {
            "owner-id": account_id,
            "InstanceId.N": instance.split(","),
            "Name": name,
            "Desc": desc,
            "AvailabilityZone": zone,
            "Policy": policy,
            "Hypervisor": hypervisor,
        }
        uri = "/v1.0/nws/computeservices/instancebackup/createbackupjob"
        res = self.cmp_post(uri, data=data, timeout=600)
        res = dict_get(res, "CreateBackupJob.jobsSet.0.jobId")
        self.app.render({"msg": f"add backup job {res}"}, details=True)

    @ex(
        help="update account virtual machine backup job",
        description="""\
This command updates an existing virtual machine backup job for the specified account. \
It requires the account ID and job ID as required arguments. \
The job can then be updated by passing additional arguments like -enabled to enable/disable the job.\
""",
        example="beehive bu cpaas vms backup-job-update elcap <uuid> -enabled=false",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (["job"], {"help": "job id", "action": "store", "type": str}),
                (
                    ["-name"],
                    {
                        "help": "job name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": "enable or disable job",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-policy"],
                    {
                        "help": "job policy ",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def backup_job_update(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get("uuid")
        job_id = self.app.pargs.job
        data = {"owner-id": account_id, "JobId": job_id}
        data = self.add_field_from_pargs_to_data("name", data, "Name", reject_value=None, format=None)
        data = self.add_field_from_pargs_to_data("enabled", data, "Enabled", reject_value=None, format=None)
        data = self.add_field_from_pargs_to_data("policy", data, "Policy", reject_value=None, format=str2bool)
        uri = "/v1.0/nws/computeservices/instancebackup/modifybackupjob"
        res = self.cmp_put(uri, data=data, timeout=600)
        res = dict_get(res, "ModifyBackupJob.jobsSet.0.jobId")
        self.app.render({"msg": f"update backup job {res}"}, details=True)

    @ex(
        help="delete account virtual machine backup job",
        description="""\
This command deletes a backup job for a virtual machine belonging to an account. \
It requires the account ID and job ID as required arguments to identify the specific backup job to delete.\
""",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (["job"], {"help": "job id", "action": "store", "type": str}),
            ]
        ),
    )
    def backup_job_del(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get("uuid")
        job_id = self.app.pargs.job
        data = {"owner-id": account_id, "JobId": job_id}
        uri = "/v1.0/nws/computeservices/instancebackup/deletebackupjob"
        self.cmp_delete(uri, data=data, timeout=600, entity=f"delete backup job {job_id}")

    @ex(
        help="add virtual machine to backup job",
        description="""\
This command adds a virtual machine instance to an existing backup job. \
It requires the account id, job id and the instance id as required arguments to identify the backup job \
and the instance to add to it.\
""",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (["job"], {"help": "job id", "action": "store", "type": str}),
                (
                    ["instance"],
                    {"help": "instance id to add", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def backup_job_instance_add(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get("uuid")
        job_id = self.app.pargs.job
        instance = self.app.pargs.instance
        data = {
            "owner-id": account_id,
            "InstanceId": instance,
            "JobId": job_id,
        }
        uri = "/v1.0/nws/computeservices/instancebackup/addbackupjobinstance"
        res = self.cmp_post(uri, data=data, timeout=600)
        res = dict_get(res, "AddBackupJobInstance.jobsSet.0.jobId")
        self.app.render(
            {"msg": f"add virtual machine {instance} to backup job {job_id}"},
            details=True,
        )

    @ex(
        help="delete virtual machine from backup job",
        description="""\
This command deletes a virtual machine instance from an existing backup job. \
It requires the account id, job id and instance id as required arguments to identify the backup job and \
virtual machine instance to remove from the job.\
""",
        example="""\
beehive bu cpaas vms backup-job-instance-del notify 8c750fce-5400-47cf-adae-f7e5c1e83e1 dbs-notify-prd-002p\
""",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (["job"], {"help": "job id", "action": "store", "type": str}),
                (
                    ["instance"],
                    {"help": "instance id to add", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def backup_job_instance_del(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get("uuid")
        job_id = self.app.pargs.job
        instance = self.app.pargs.instance
        data = {
            "owner-id": account_id,
            "InstanceId": instance,
            "JobId": job_id,
        }
        uri = "/v1.0/nws/computeservices/instancebackup/delbackupjobinstance"
        res = self.cmp_delete(
            uri,
            data=data,
            timeout=600,
            entity=f"virtual machine {instance} from backup job {job_id}",
        )
        res = dict_get(res, "DelBackupJobInstance.jobsSet.0.jobId")

    @ex(
        help="get account virtual machine backup job policies",
        description="""\
This command is used to retrieve the backup job policies for virtual machines associated with a given account. \
The 'account' argument is required and specifies the account id to get the backup job policies for. \
The policies define how backups of the virtual machines are configured for that account.\
""",
        example="beehive bu cpaas vms backup-job-policies animm;beehive bu cpaas vms backup-job-policies ivar",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
            ]
        ),
    )
    def backup_job_policies(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get("uuid")
        data = {"owner-id": account_id}
        uri = "/v1.0/nws/computeservices/instancebackup/describebackupjobpolicies"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True), timeout=600)
        res = dict_get(res, "DescribeBackupJobPoliciesResponse.jobPoliciesSet")
        headers = [
            "id",
            "uuid",
            "name",
            "fullbackup_interval",
            "restore_points",
            "start_time_window",
            "interval",
            "timezone",
        ]
        fields = [
            "id",
            "uuid",
            "name",
            "fullbackup_interval",
            "restore_points",
            "start_time_window",
            "interval",
            "timezone",
        ]
        self.app.render(res, headers=headers, fields=fields)


class KeyPairServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = "cpaas"
        stacked_type = "nested"
        label = "keypairs"
        description = "key pair management"
        help = "key pair management"

    @ex(
        help="list key pairs",
        description="""\
This command retrieves the list of key pairs associated with the current Nivola CMP Cloud account. \
Key pairs are used for SSH access to virtual machines and need to be created before launching instances \
that require SSH access. The list operation returns basic information about each key pair such as name and fingerprint.\
""",
        example="beehive bu cpaas keypairs list -accounts CSI.Datacenter.test -e <env>",
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
                        "help": "list of keypair name comma separated",
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
        params = ["accounts", "name", "tags", "sg"]
        mappings = {"accounts": self.get_account_ids, "name": lambda x: x.split(",")}
        aliases = {
            "accounts": "owner-id.N",
            "name": "key-name.N",
            "size": "Nvl-MaxResults",
            "page": "Nvl-NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = f"{self.baseuri}/computeservices/keypair/describekeypairs"
        self.cmp_get(uri, data=data)

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeKeyPairsResponse")
            resp = {
                "count": len(res.get("keySet")),
                "page": page,
                "total": res.get("nvl-keyTotal"),
                "sort": {"field": "id", "order": "asc"},
                "instances": res.get("keySet"),
            }

            headers = ["id", "name", "account", "keyFingerprint", "type", "bits"]
            fields = ["nvl-keyId", "keyName", "nvl-ownerAlias", "keyFingerprint", "type", "bits"]
            self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=75)

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=100,
            key_total_name="DescribeKeyPairsResponse.nvl-keyTotal",
            key_list_name="DescribeKeyPairsResponse.keySet",
            fn_render=render,
        )

    @ex(
        help="get key pair",
        description="""\
This command retrieves the details of an existing key pair in your account. \
You need to provide the name of the key pair as the required argument. \
The key pair name uniquely identifies the key pair resource.\
""",
        example="beehive bu cpaas keypairs get davidino-key -e <env>",
        arguments=ARGS(
            [
                (["name"], {"help": "keypair name", "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        data = {"key-name.N": self.app.pargs.name}
        uri = f"{self.baseuri}/computeservices/keypair/describekeypairs"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeKeyPairsResponse.keySet.0", default={})
        self.app.render(res, details=True, maxsize=100)

    # @ex(
    #     help='export key pair',
    #     description='export key pair',
    #     arguments=ARGS([
    #         (['name'], {'help': 'keypair name', 'action': 'store', 'type': str}),
    #     ])
    # )
    # def export(self):
    #     data = {'key-name.N': self.app.pargs.name}
    #     uri = '%s/computeservices/keypair/exportkeypairs' % self.baseuri
    #     res = self.cmp_get(uri, data=urlencode(data, doseq=True))
    #     res = dict_get(res, 'ExportKeyPairsResponse.instance', default={})
    #     self.app.render(res, details=True, maxsize=100)

    @ex(
        help="delete a key pair",
        description="""\
This command deletes a key pair from your Nivola CMP account. \
You need to provide the name of the key pair as an argument to identify which key pair to delete from your account. \
Deleting a key pair will remove the public/private key permanently.\
""",
        arguments=ARGS(
            [
                (["name"], {"help": "keypair name", "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        name = self.app.pargs.name
        data = {"KeyName": name}
        uri = f"{self.baseuri}/computeservices/keypair/deletekeypair"
        self.cmp_delete(uri, data=data, timeout=600, entity=f"keypair {name}")

    @ex(
        help="add new RSA key pair",
        description="""\
This command adds a new RSA key pair to the specified account. \
It requires the account ID, key pair name and key type (-type) as required arguments.\
""",
        example="beehive bu cpaas keypairs add -accounts felice",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (["name"], {"help": "key pair name", "action": "store", "type": str}),
                (["-type"], {"help": "key type", "action": "store", "type": str}),
            ]
        ),
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get("uuid")
        name = self.app.pargs.name
        key_type = self.app.pargs.type
        data = {
            "owner-id": account,
            "KeyName": name,
            "Nvl-KeyPairType": key_type,
        }
        uri = f"{self.baseuri}/computeservices/keypair/createkeypair"
        res = self.cmp_post(uri, data={"keypair": data})
        res = res.get("CreateKeyPairResponse")
        headers = ["name", "fingerprint SHA1", "material PEM"]
        fields = ["keyName", "keyFingerprint", "keyMaterial"]
        self.app.render(res, key=None, headers=headers, fields=fields)

        res = {"msg": f"Add key pair {name}"}
        self.app.render(res)

    @ex(
        help="import public RSA key",
        description="""\
This command imports a public RSA key into an account's key pair store. \
It requires the account ID, key pair name, file containing the base64 encoded public key, \
and key type (-type) as required arguments. \
The public key will be associated with the specified key pair name in the given account.\
""",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (["name"], {"help": "key pair name", "action": "store", "type": str}),
                (
                    ["publickey"],
                    {
                        "help": "file containing public key base64 encoded",
                        "action": "store",
                        "type": str,
                    },
                ),
                (["-type"], {"help": "key type", "action": "store", "type": str}),
            ]
        ),
    )
    def import_public_key(self):
        account = self.get_account(self.app.pargs.account).get("uuid")
        name = self.app.pargs.name
        file_name = self.app.pargs.publickey
        key_type = self.app.pargs.type
        file = load_config(file_name)

        data = {
            "owner-id": account,
            "KeyName": name,
            "PublicKeyMaterial": file,
            "Nvl-KeyPairType": key_type,
        }
        uri = f"{self.baseuri}/computeservices/keypair/importkeypair"
        res = self.cmp_post(uri, data={"keypair": data})
        res = res.get("ImportKeyPairResponse")

        headers = ["name", "fingerprint MD5"]
        fields = ["keyName", "keyFingerprint"]
        self.app.render(res, key=None, headers=headers, fields=fields)

        res = {"msg": f"Import key pair {name}"}
        self.app.render(res)


class TagServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = "cpaas"
        stacked_type = "nested"
        label = "compute_tags"
        description = "tags service management"
        help = "tags service management"

    @ex(
        help="list resource by tags",
        description="""\
This command lists resources that are tagged with specific tags. \
Tags are key-value pairs that are attached to supported cloud resources. \
This allows you to categorize and search for these resources. \
The list command will display the tagged resources without any additional parameters. \
You can also filter the results by specifying tag keys or values using optional parameters like -key, -value etc.\
""",
        example="beehive bu cpaas compute-tags list -accounts CSI.Datacenter.test",
        arguments=ARGS(
            [
                (
                    ["-account"],
                    {
                        "help": "account id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-services"],
                    {
                        "help": "comma separated list of service instance id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": "comma separated list of tag key",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-types"],
                    {
                        "help": "comma separated list of service instance types",
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
        params = ["account", "services", "tags", "types"]
        mappings = {
            "account": lambda x: x,
            "services": lambda x: x.split(","),
            "tags": lambda x: x.split(","),
            "types": lambda x: x.split(","),
        }
        aliases = {
            "account": "owner-id.N",
            "services": "resource-id.N",
            "types": "resource-type.N",
            "tags": "key.N",
            "size": "MaxResults",
            "page": "NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = f"{self.baseuri}/computeservices/tag/describetags"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeTagsResponse")
            resp = {
                "count": len(res.get("tagSet")),
                "page": page,
                "total": res.get("nvl-tagTotal", 0),
                "sort": {"field": "id", "order": "asc"},
                "instances": res.get("tagSet"),
            }
            headers = ["service-instance", "type", "tag"]
            fields = ["resourceId", "resourceType", "key"]
            self.app.render(resp, key="instances", headers=headers, fields=fields, maxsize=45)

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=100,
            key_total_name="DescribeTagsResponse.nvl-tagTotal",
            key_list_name="DescribeTagsResponse.tagSet",
            fn_render=render,
        )

    @ex(
        help="add tag to service instance",
        description="""\
This command adds a tag to a service instance. \
The required arguments are the account id, service instance id and the tag key to add.\
""",
        arguments=ARGS(
            [
                (["account"], {"help": "account id", "action": "store", "type": str}),
                (
                    ["service"],
                    {"help": "service instance id", "action": "store", "type": str},
                ),
                (["tag"], {"help": "tag key", "action": "store", "type": str}),
            ]
        ),
    )
    def add(self):
        account = self.app.pargs.account
        account = self.get_account(account).get("uuid")
        service = self.app.pargs.service
        tag = self.app.pargs.tag
        data = {
            "owner-id": account,
            "ResourceId.N": [service],
            "Tag.N": [{"Key": tag}],
        }
        uri = f"{self.baseuri}/computeservices/tag/createtags"
        res = self.cmp_post(uri, data={"tags": data}, timeout=600)
        dict_get(res, "CreateTagsResponse.return")
        res = {"msg": f"add tag {tag} to {service}"}
        self.app.render(res)

    @ex(
        help="delete tag from service instance",
        description="""\
This command deletes a tag from a CPAAS compute service instance. \
The 'service' argument specifies the service instance ID and the 'tag' argument specifies the tag key to delete.\
""",
        arguments=ARGS(
            [
                (
                    ["service"],
                    {"help": "service instance id", "action": "store", "type": str},
                ),
                (["tag"], {"help": "tag key", "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        service = self.app.pargs.service
        tag = self.app.pargs.tag
        data = {
            "ResourceId.N": [service],
            "Tag.N": [{"Key": tag}],
        }
        uri = f"{self.baseuri}/computeservices/tag/deletetags"
        self.cmp_delete(uri, data={"tags": data}, timeout=600, entity=f"service {service} tag {tag}")


class CustomizationServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = "cpaas"
        stacked_type = "nested"
        label = "customizations"
        description = "customization service management"
        help = "customization service management"

    @ex(
        help="get customizations types",
        description="""\
This CLI command is used to get customizations types from Nivola CMP CPAAS. \
It retrieves the available customization types without requiring any arguments. \
The types returned can then be used as a reference for other CPAAS customization commands.\
""",
        example="beehive bu cpaas customizations types <uuid>",
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
                    ["-id"],
                    {
                        "help": "customization type id",
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
        oid = self.app.pargs.id
        if oid is not None:
            account = self.get_account(self.app.pargs.account)["uuid"]
            data = urlencode({"CustomizationType": oid, "owner-id": account}, doseq=True)
            uri = f"{self.baseuri}/computeservices/customization/describecustomizationtypes"
            res = self.cmp_get(uri, data=data)
            res = dict_get(res, "DescribeCustomizationTypesResponse.customizationTypesSet.0")
            params = res.pop("args")
            self.app.render(res, details=True)
            self.c("\nparams", "underline")
            self.app.render(
                params,
                headers=["name", "desc", "required", "type", "default", "allowed"],
            )
        else:
            params = ["account"]
            mappings = {
                "account": lambda x: self.get_account(x)["uuid"],
            }
            aliases = {"account": "owner-id", "size": "MaxResults", "page": "NextToken"}
            data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
            uri = f"{self.baseuri}/computeservices/customization/describecustomizationtypes"
            res = self.cmp_get(uri, data=data)
            res = res.get("DescribeCustomizationTypesResponse")
            page = self.app.pargs.page
            resp = {
                "count": len(res.get("customizationTypesSet")),
                "page": page,
                "total": res.get("customizationTypesTotal"),
                "sort": {"field": "id", "order": "asc"},
                "types": res.get("customizationTypesSet"),
            }
            headers = ["id", "customization_type", "desc"]
            fields = ["uuid", "name", "description"]
            self.app.render(resp, key="types", headers=headers, fields=fields)

    @ex(
        help="list customizations",
        description="""\
This command lists all the customizations that have been applied to the Nivola CMP CPAAS platform. \
The customizations modify and extend the standard Nivola CMP platform functionality for a particular environment \
like test, stage or production. No arguments are required to just get a list of all the customizations.\
""",
        example="beehive bu cpaas customizations list -env test;beehive bu cpaas customizations list -e <env>",
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
                    ["-customizations"],
                    {
                        "help": "list of customization id comma separated",
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
        params = ["accounts", "customizations"]
        mappings = {
            "accounts": self.get_account_ids,
            "tags": lambda x: x.split(","),
            "customizations": lambda x: x.split(","),
        }
        aliases = {
            "accounts": "owner-id.N",
            "customizations": "customization-id.N",
            "tags": "tag-key.N",
            "size": "MaxResults",
            "page": "NextToken",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)

        uri = f"{self.baseuri}/computeservices/customization/describecustomizations"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeCustomizationsResponse")
            resp = {
                "count": len(res.get("customizationsSet")),
                "page": page,
                "total": res.get("customizationTotal"),
                "sort": {"field": "id", "order": "asc"},
                "customizations": res.get("customizationsSet"),
            }

            headers = ["id", "name", "state", "type", "account", "creation"]
            fields = [
                "customizationId",
                "customizationName",
                "customizationState.name",
                "customizationType",
                "ownerAlias",
                "launchTime",
            ]
            self.app.render(resp, key="customizations", headers=headers, fields=fields, maxsize=45)

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=20,
            key_total_name="DescribeCustomizationsResponse.customizationTotal",
            key_list_name="DescribeCustomizationsResponse.customizationsSet",
            fn_render=render,
        )

    @ex(
        help="get customization",
        description="""\
This CLI command is used to retrieve a specific customization configuration from Nivola CMP CPAAS platform. \
The required 'customization' argument expects the customization id as input to fetch the details of \
that particular customization.\
""",
        example="beehive bu cpaas customizations get serv-custom-01 -e <env>",
        arguments=ARGS(
            [
                (
                    ["customization"],
                    {"help": "customization id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def get(self):
        customization_id = self.app.pargs.customization
        if self.is_uuid(customization_id):
            data = {"customization-id.N": [customization_id]}
        elif self.is_name(customization_id):
            data = {"customization-name.N": [customization_id]}

        uri = f"{self.baseuri}/computeservices/customization/describecustomizations"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeCustomizationsResponse.customizationsSet", default={})
        if len(res) > 0:
            res = res[0]
            # if self.is_output_text():
            #     self.app.render(res, details=True, maxsize=100)
            # else:
            self.app.render(res, details=True, maxsize=100)
        else:
            raise Exception(f"customization {customization_id} was not found")

    @ex(
        help="create a customization",
        description="""\
This command creates a customization with the given name, account, type and instances. \
It takes the customization name, parent account id, type and comma separated list of compute instance ids \
as required arguments. \
It also takes an optional args argument to pass customization params in key-value pair format separated by commas.\
""",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "customization name", "action": "store", "type": str},
                ),
                (
                    ["account"],
                    {"help": "parent account id", "action": "store", "type": str},
                ),
                (
                    ["type"],
                    {"help": "customization type", "action": "store", "type": str},
                ),
                (
                    ["instances"],
                    {
                        "help": "comma separated list of compute instance id",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["args"],
                    {
                        "help": "customization params. Use syntax arg1:val1,arg2:val2",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def add(self):
        name = self.app.pargs.name
        account = self.get_account(self.app.pargs.account).get("uuid")
        itype = self.get_service_definition(self.app.pargs.type)
        instances = self.app.pargs.instances.split(",")
        args = self.app.pargs.args.split(",")

        params = []
        for arg in args:
            arg = arg.split(":")
            params.append({"Name": arg[0], "Value": arg[1]})

        data = {
            "Name": name,
            "owner-id": account,
            "CustomizationType": itype,
            "Instances": instances,
            "Args": params,
        }
        uri = f"{self.baseuri}/computeservices/customization/runcustomizations"
        res = self.cmp_post(uri, data={"customization": data}, timeout=600)
        uuid = dict_get(res, "RunCustomizationResponse.customizationId")
        self.wait_for_service(uuid)
        self.app.render({"msg": f"add customization: {uuid}"})

    @ex(
        help="delete a customization",
        description="""\
This command deletes a customization from the Nivola CMP CPAAS platform. \
It requires the customization ID as a required argument to identify which customization to delete from the system.\
""",
        arguments=ARGS(
            [
                (
                    ["customization"],
                    {"help": "customization id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete(self):
        customization_id = self.app.pargs.customization
        if self.is_name(customization_id):
            raise Exception("only customization id is supported")
        data = {"CustomizationId": customization_id}
        uri = f"{self.baseuri}/computeservices/customization/terminatecustomizations"
        self.cmp_delete(
            uri,
            data=data,
            timeout=600,
            output=False,
            entity=f"customization {customization_id}",
        )
        self.wait_for_service(customization_id, accepted_state="DELETED")
        self.app.render({"msg": f"delete customization: {customization_id}"})

    @ex(
        help="update a customization",
        description="""\
This command updates an existing customization in Nivola CMP CPaaS. \
It requires the customization ID as the only required argument to identify which customization to update. \
The customization object with the updated values is then sent to the Nivola CMP API to update the existing customization record.\
""",
        arguments=ARGS(
            [
                (
                    ["customization"],
                    {"help": "customization id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def update(self):
        customization_id = self.app.pargs.customization
        if self.is_name(customization_id):
            raise Exception("only customization id is supported")
        data = {"CustomizationId": customization_id}
        uri = f"{self.baseuri}/computeservices/customization/updatecustomizations"
        self.cmp_put(uri, data=data, timeout=600).get("UpdateCustomizationResponse")
        self.wait_for_service(customization_id)
        self.app.render({"msg": f"update customization: {customization_id}"})
