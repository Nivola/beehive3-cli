# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from typing import List, Callable, Union
from urllib.parse import urlencode
import json
import yaml

from cement.ext.ext_argparse import ex
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import ARGS
from .child import AdminChildController, AdminError


class ComputeAdminController(AdminChildController):

    """
    ComputeAdminController: This contains commands to manage and adjust metadata of compute.
    """

    class Meta:
        label = "compute"
        description = "compute service administration commands"
        help = "compute administration commands"

    @ex(
        help="check compute service storage",
        description="""
compute management, the holistic way :)
The compute parameters must be a service identifier.
It should be an uuid, id or name of a compute service.
You can get it listing the services of the account using commands like "bu account get" or "bu compute vms get".
The procedure checks compute storage consistency between Nivola and hypervisors.
The procedure query both Nivola and the hypervisor on which the compute service is running.
Then display details about volumes.
Pay attention to the column "ext_id" of the volumes that should uniquely identify the hypervisor's volume.
You may change Nivola's volumes information by matching with hypervisor volumes.
You will be asked for which match has to be established.
""",
        arguments=ARGS(
            [
                (
                    ["compute"],
                    {
                        "help": "compute service id uuid or name; this is one of the service identifiers",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["--tofile"],
                    {
                        "help": "store to file only when format is json or yaml",
                        "dest": "to file",
                        "action": "store_true",
                        "default": False,
                    },
                ),
                (
                    ["--cmp_key"],
                    {"help": "cmp fernet encription key ", "dest": "cmp_key", "type": str},
                ),
            ]
        ),
    )
    def check(self):
        """
        Sanity check for compute metadata against platform.
        """
        self.cmp_fernet = self.app.pargs.cmp_key
        if self.cmp_fernet is None or self.cmp_fernet == "":
            print("Warning: You have no specified fernet key", end="\n")
        else:
            print(f"Info: Using Fernet key {self.cmp_fernet}", end="\n")
        compute = self.app.pargs.compute
        metadata = None
        try:
            print()
            print(self.styler.clear_line() + "Collecting Metadata", end="...", flush=True)
            metadata = self.get_metadata(compute)
        except AdminError as e:
            print(self.styler.error(data=str(e)))

        if self.is_output_text():
            self.manage_interactions(compute, metadata)
            print()
        else:
            metadata = None
            with open(f"{compute}.{self.format}", mode="+tw", encoding="utf-8") as outfile:
                if self.format == "json":
                    outfile.write(json.dumps(metadata))
                elif self.format == "yaml":
                    yaml.dump(metadata, outfile)
            self.app.render(metadata, key="object", details=True)

    def align_service_to_resource(self, metadata):
        """
        Align resource information to service.
        """
        bu_servinst_uuid = metadata["service_servinst"]["uuid"]
        compute_instance_id = metadata["provider_compute_instance"]["uuid"]
        compute_instance = self.get_cmp_resource(compute_instance_id)
        service_baseuri = "/v2.0/nws"
        uri = f"{service_baseuri}/computeservices/instance/describeinstances"
        data = {"instance-id.N": [bu_servinst_uuid]}
        bu_servinst = self.cmp_get(uri, data=urlencode(data, doseq=True))
        instance_item = bu_servinst["DescribeInstancesResponse"]["reservationSet"][0]["instancesSet"][0]
        account_id = instance_item["nvl-ownerId"]
        service_inst_name = instance_item["nvl-name"]
        data = {"force": True, "propagate": False}
        for block_device_item in instance_item["blockDeviceMapping"]:
            service_volume_id = block_device_item["ebs"]["volumeId"]
            if service_volume_id is None:
                continue
            uri = f"{service_baseuri}/serviceinsts/{service_volume_id}"
            self.cmp_delete(
                uri, data=data, timeout=180, entity=f"service instance {service_volume_id}", confirm=False, output=False
            )

        compute_instance_block_device_mapping = compute_instance.get("block_device_mapping", [])
        for compute_instance_block_device_item in compute_instance_block_device_mapping:
            resource_id = compute_instance_block_device_item["id"]
            boot_index = compute_instance_block_device_item["boot_index"]
            service_volume_name = f"{service_inst_name}-volume-{boot_index}"
            data = {
                "serviceinst": {
                    "name": service_volume_name,
                    "account_id": account_id,
                    "plugintype": "ComputeVolume",
                    "container_plugintype": "ComputeService",
                    "resource_id": resource_id,
                }
            }
            uri = f"{service_baseuri}/serviceinsts/import"
            self.cmp_post(uri, data=data)
        print(self.styler.clear_line() + self.styler.green("Aligned volume service instance."), flush=True)

    def get_metadata(self, compute: str) -> dict:
        """
        Get compute from service down to hypervisor in order
        to get all information about volumes mapped and available.
        """

        def tree_search(children: List[dict], check: Callable[[dict], bool]) -> Union[dict, None]:
            for child in children:
                if check(child):
                    return child
                rec = tree_search(child.get("children", []), check)
                if isinstance(rec, dict):
                    return rec
            return None

        def get_server(node: dict) -> bool:
            tp = node.get("type")
            return tp in ("Vsphere.DataCenter.Folder.Server", "Openstack.Domain.Project.Server")

        def get_volume(node: dict) -> bool:
            tp = node.get("type")
            return tp in ("Vsphere.DataCenter.Folder.volume", "Openstack.Domain.Project.Volume")

        self.print_looking_for("Service Instance")
        bu_servinst = self.get_cmp_service_instance(compute, "ComputeInstance")
        resource_uuid = bu_servinst.get("resource_uuid")
        # self.reset_cmp_cache_resource(resource_uuid)
        resource_config = self.get_cmp_resource_config(resource_uuid)
        # get of the unuseful resource uri = f"/v1.0/nrs/entities/{resource_uuid}"
        # get of the linked entities to search for the ComputeInstance
        self.print_looking_for("resource linked entities")
        provider_config = {
            "id": resource_uuid,
            "config": resource_config,
        }
        compute_instance = None

        # get of the ComputeInstance between the linked entities
        self.print_looking_for("Provider.ComputeZone.ComputeInstance")
        compute_instance = self.get_cmp_resource(resource_uuid)

        if compute_instance is None:
            raise AdminError(
                f" Could not find any ComputeInstance for resource {resource_uuid} "
                + f"which implements the compute {compute}"
            )
        for vol in compute_instance.get("block_device_mapping", []):
            tags = self.get_cmp_entity_tags(vol["id"])
            vol["tags"] = tags
            config = self.get_cmp_resource_config(vol["id"])
            vol["config"] = config
        # get server openstack o vsphere
        self.print_looking_for("hypervisor Server in ComputeInstance tree")
        compute_tree = self.get_cmp_restree(compute_instance.get("id"))
        hypervisor_server = tree_search(dict_get(compute_tree, "resourcetree.children", default=[]), get_server)
        if hypervisor_server is None:
            raise AdminError(
                f" Could not find any Server in ComputeInstance in the ComputeStack {resource_uuid}"
                + f"which implements the compute {compute}"
            )

        # get hypervisor info in order to connect from resource containers
        self.print_looking_for("hypervisor container")
        hypervisor_container = self.get_cmp_container(hypervisor_server.get("container"))
        self.print_looking_for("hypervisor Server and volumes")
        self.init_container(hypervisor_container)
        hypervisor_server_detail = self.get_hypervisor_server(hypervisor_server.get("ext_id"))
        devices = compute_instance.get("block_device_mapping", [])
        for device in devices:
            devtree = self.get_cmp_restree(device["id"])
            device["resource_hypervisor_volume"] = tree_search(
                dict_get(devtree, "resourcetree.children", default=[]), get_volume
            )

        result = {}
        result["service_servinst"] = bu_servinst
        result["provider_compute_instance"] = compute_instance
        result["provider_config"] = provider_config
        result["resource_hypervisor_server"] = hypervisor_server
        result["hypervisor_serverserver_det"] = hypervisor_server_detail
        result["hypervisor_container"] = hypervisor_container
        return result

    def show_metadata(self, metadata) -> tuple[dict, List[dict], List[dict]]:
        """
        Volumes  display.
        """
        cmp: list = dict_get(metadata, "provider_compute_instance.block_device_mapping")
        tab_cmp = []
        tab_hyp = []
        i = 0
        general_instance = {
            "service name": dict_get(metadata, "service_servinst.name"),
            "service uuid": dict_get(metadata, "service_servinst.uuid"),
            "account name": dict_get(metadata, "service_servinst.account.name"),
            "account uuid": dict_get(metadata, "service_servinst.account.uuid"),
            "provider instance fqdn": dict_get(metadata, "provider_compute_instance.attributes.fqdn"),
            "provider instance type": dict_get(metadata, "provider_compute_instance.attributes.type"),
            "provider instance has quotas": dict_get(metadata, "provider_compute_instance.attributes.has_quotas"),
        }

        for v in cmp:
            tab_cmp.append(
                {
                    "#": i,
                    "name": v.get("name"),
                    "index": v.get("boot_index"),
                    "ext_id": dict_get(v, "resource_hypervisor_volume.ext_id"),
                    "size": v.get("volume_size"),
                    "id": v.get("id"),
                    "bootable": dict_get(v, "config.bootable"),
                    # "encrypted": dict_get(v, "config.encrypted"),
                    "has_quotas": dict_get(v, "config.has_quotas"),
                    "tags": v.get("tags"),
                }
            )
            i += 1
        i = 0
        hypervisor = general_instance["provider instance type"]
        if hypervisor == "vsphere":
            hypv: list = dict_get(metadata, "hypervisor_serverserver_det.volumes")
        elif hypervisor == "openstack":
            hypv: list = dict_get(metadata, "hypervisor_serverserver_det.os-extended-volumes:volumes_attached")
        else:
            raise AdminError(f"hypervisor {hypervisor} not known")
        for v in hypv:
            if hypervisor == "vsphere":
                index = v.get("unit_number")
                ext_id = v.get("disk_object_id")
            elif hypervisor == "openstack":
                index = dict_get(v, "attachments.0.device")
                ext_id = dict_get(v, "id")
            tab_hyp.append(
                {
                    "#": i,
                    "name": v.get("name"),
                    "index": index,
                    "ext_id": ext_id,
                    "size": v.get("size"),
                    "id": v.get("id"),
                    "has_quotas": dict_get(v, "config.has_quotas"),
                }
            )
            i += 1
        print(self.styler.clear_line() + self.styler.underline("Object"))
        self.app.render(general_instance, details=True)
        print(self.styler.underline("Cmp Metadata volumes"))
        cmp_fields = ["#", "name", "index", "ext_id", "size", "id", "has_quotas", "tags"]
        cmp_headers = ["#", "name", "index", "ext_id", "size (GiB)", "id", "has_quotas", "tags"]
        self.app.render(tab_cmp, headers=cmp_headers, fields=cmp_fields)
        print(self.styler.underline("Hypervisor volumes"))
        hyp_headers = ["#", "name", "index", "ext_id", "size (GiB)", "id"]
        hyp_fields = ["#", "name", "index", "ext_id", "size", "id"]
        self.app.render(tab_hyp, headers=hyp_headers, fields=hyp_fields, maxsize=2000)
        res = self.make_suggestions(tab_cmp, tab_hyp)
        if res:
            self.print_info()
            msg = self.styler.red("Please e" + self.styler.underline("X")) + self.styler.red("it, all is fine!")
            print(msg)

        return general_instance, tab_cmp, tab_hyp

    def manage_interactions(self, compute, metadata):
        """
        Manage user interactions in order to force volume mapping.
        """
        PROMPT_0 = (
            "You can: "
            + self.styler.underline("R")
            + "eload menu with cmp metadata volumes and hypervisor volumes, "
            + self.styler.underline("U")
            + "pdate cmp metadata volumes, "
            + self.styler.underline("D")
            + "elete cmp metadata volumes, "
            + self.styler.underline("A")
            + "dd cmp metadata volumes, change "
            + self.styler.underline("T")
            + "ag cmp metadata volumes or e"
            + self.styler.underline("X")
            + "it"
        )
        allowed = ("R", "U", "D", "A", "T", "X")
        PROMPT_1 = f"Reload, Update, Delete, Add, Tags, or eXit [{'/'.join(allowed)}]? "
        _, tab_cmp, tab_hyp = self.show_metadata(metadata)
        # change volume metadata using hypervisor data
        check = ""
        while check != "X":
            print(PROMPT_0)
            check = self.ask(PROMPT_1, yn=False, allowed=allowed)
            if check == "R":
                try:
                    print()
                    print(self.styler.clear_line() + "Collecting Metadata", end="...", flush=True)
                    metadata = self.get_metadata(compute)
                except AdminError as e:
                    print(self.styler.error(data=str(e)))
                _, tab_cmp, tab_hyp = self.show_metadata(metadata)
            elif check == "U":
                self.manage_interactive_mapping(tab_cmp, tab_hyp, metadata)
            elif check == "D":
                self.manage_interactive_delete(metadata)
            elif check == "A":
                self.manage_interactive_import(metadata)
            elif check == "T":
                self.manage_interactive_tags(tab_cmp)
            elif check == "X":
                print("\n\n", "Bye", sep="")
            if check in ("D", "L"):
                self.align_service_to_resource(metadata)
