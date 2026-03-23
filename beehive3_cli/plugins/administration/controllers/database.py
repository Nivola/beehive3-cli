# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


import sys
from typing import List, Callable, Union, Dict
from collections import OrderedDict
import json
import yaml
from cement.ext.ext_argparse import ex
from beecell.types.type_dict import dict_get
from beecell.types.type_string import str2bool
from beehive3_cli.translate import _
from beehive3_cli.core.controller import ARGS
from beehive3_cli.core.connect import SshConnectionManager
from .child import AdminChildController, AdminError
from .database_disk_info import DbVolumeInfo


class DatabaseAdminController(AdminChildController):
    """
    DatabaseAdminController: This contains commands to manage and adjust metadata of dbaas stackv2.
    """

    class Meta:
        label = "database"
        description = _("database administration commands")
        help = _("database administration commands")

    @ex(
        help=_("check database storage"),
        description=_(
            """
Database management, the holistic way :)
The database parameters must be a service identifier.
It should be an uuid, id or name of a db instance.
You can get it listing the services of the account using commands like "bu account get" or "bu dbaas db-instance get".
The procedure checks database storage consistency between Nivola and hypervisors.
The procedure query both Nivola and the hypervisor on which the database server is running.
Then display details about volumes.
Pay attention to the column "ext_id" of the volumes that should uniquely identify the hypervisor's volume.
You may change Nivola's volumes information by matching with hypervisor volumes.
You will be asked for which match has to be established.
Then you will be asked for change backup tags on the database volume.
Remember that volume tagged as backup will generates ad hoc metrics distinct from allocated storage.
Then you will be asked to disable volume quotas.
Database's volumes should always have quotas disabled otherwise they will generate compute metrics in addition to
database metrics.
After that you will be asked to change the allocated storage for the databases.
The allocated storage is displayed by the service portal and some beehive commands, it should be the sum of database
volumes used for database data.
As a matter of fact, Nivola calculates data storage as the sum of attached volumes that are neither the boot volume or
tagged as backup.
"""
        ),
        arguments=ARGS(
            [
                (
                    ["database"],
                    {
                        "help": _("database service id uuid or name; this is one of the service identifiers"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["--tofile"],
                    {
                        "help": _("store to file only when format is json or yaml"),
                        "dest": "to file",
                        "action": "store_true",
                        "default": False,
                    },
                ),
                (
                    ["--cmp_key"],
                    {"help": _("cmp fernet encription key "), "dest": "cmp_key", "type": str},
                ),
                (
                    ["--auto_align"],
                    {"help": _("align ext id"), "action": "store", "type": str, "default": "false"},
                ),

            ]
        ),
    )
    def check(self):
        """
        Sanity check for dbaas metadata stackv2 against platform.
        """
        self.cmp_fernet = self.app.pargs.cmp_key
        if self.cmp_fernet is None or self.cmp_fernet == "":
            self.cmp_fernet = self.api.cmpkey

        database = self.app.pargs.database
        metadata = None
        auto_align = str2bool(self.app.pargs.auto_align)
        try:
            print()
            print(self.styler.clear_line() + _("Collecting Metadata"), end="...", flush=True)
            metadata = self.get_metadata(database)

        except AdminError as e:
            print(self.styler.error(data=str(e)))

        if auto_align:
            fine, _tab_cmp, _tab_hyp = self.show_metadata(metadata)
            if not fine:
                self.update_volumes(metadata)
            sys.exit()

        if self.is_output_text():
            self.manage_interactions(database, metadata)
            print()
        else:
            metadata = None
            with open(f"{database}.{self.format}", mode="+tw", encoding="utf-8") as outfile:
                if self.format == "json":
                    outfile.write(json.dumps(metadata))
                elif self.format == "yaml":
                    yaml.dump(metadata, outfile)
            self.app.render(metadata, key="object", details=True)


    def _res_provider_failure_info(self, resource_uuid: str, dbaas_uuid: str):
        provider_res = self.get_res_provider_compute_instance(resource_uuid)
        if provider_res is None:
            raise AdminError(_("Resource {resource_uuid} not found.").format(resource_uuid=resource_uuid))
        provider_res_definition = provider_res['__meta__']['definition']
        implements_dbaas = _("the resource implements the database {dbaas_uuid}").format(dbaas_uuid=dbaas_uuid)
        with_def = _("has as its definition {provider_res_definition}").format(
            provider_res_definition=provider_res_definition
        )
        if provider_res_definition == "Provider.ComputeZone.ComputeStackV2":
            compute_instance_not_found = _("""\
ComputeInstance not found in the ComputeStack {resource_uuid}, this {with_def}; {implements_dbaas}\
""").format(
    resource_uuid=resource_uuid, with_def=with_def, implements_dbaas=implements_dbaas
)
            raise AdminError(compute_instance_not_found)
        msg = _("Resource {resource_uuid} {with_def} that is not supported; {implements_dbaas}").format(
            resource_uuid=resource_uuid, with_def=with_def, implements_dbaas=implements_dbaas
        )
        raise AdminError(msg)


    def find_compute_instance(self, resource_uuid: str, dbaas_uuid: str):
        """
        Find compute instance.
        """
        # get of the linked entities to search for the ComputeInstance that implements the db
        self.print_looking_for("resource linked entities")
        linked_resources = self.get_cmp_linkedres(resource_uuid)
        compute_instance = None

        # get of the ComputeInstance between the linked entities
        self.print_looking_for("Provider.ComputeZone.ComputeInstance")
        for resource in linked_resources:
            definition = dict_get(resource, "__meta__.definition")
            if definition == "Provider.ComputeZone.ComputeInstance":
                compute_instance = resource
                break
        if compute_instance is None:
            self._res_provider_failure_info(resource_uuid, dbaas_uuid)
        return compute_instance

    def get_metadata(self, database: str) -> Dict: #-> DbMetadata:
        """
        Get database from service down to hypervisor in order
        to get all information about volumes mapped and available.
        """

        def tree_search(children: List[Dict], check: Callable[[Dict], bool]) -> Union[Dict, None]:
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

        self.print_looking_for(_("Service Instance"))
        bu_servinst = self.get_cmp_service_instance(database)
        resource_uuid = bu_servinst.get("resource_uuid")
        provider_sqlstack = {
            "id": resource_uuid,
            "config": self.get_cmp_resource_config(resource_uuid),
        }
        compute_instance = self.find_compute_instance(resource_uuid, database)
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
            msg = _("""\
Server not found in ComputeInstance in the ComputeStack {resource_uuid} which implements the database {database}\
""").format(resource_uuid=resource_uuid, database=database)
            raise AdminError(msg)

        # get hypervisor info in order to connect from resource containers
        self.print_looking_for(_("hypervisor container"))
        hypervisor_container = self.get_cmp_container(hypervisor_server.get("container"))
        self.print_looking_for(_("hypervisor Server and volumes"))
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
        result["provider_sqlstack"] = provider_sqlstack
        result["resource_hypervisor_server"] = hypervisor_server
        result["hypervisor_serverserver_det"] = hypervisor_server_detail
        result["hypervisor_container"] = hypervisor_container
        return result

    def _align_service_allocated_storage(self, metadata):
        """
        Align service allocated storage if need it.
        """
        service_allocated_storage = dict_get(metadata, "service_servinst.config.dbinstance.AllocatedStorage")
        provider_allocated_storage = dict_get(metadata, "provider_sqlstack.config.allocated_storage")
        if provider_allocated_storage != service_allocated_storage:
            self.set_cmp_service_config(
                dict_get(metadata, "service_servinst.uuid"),
                "dbinstance.AllocatedStorage",
                str(provider_allocated_storage),
            )
            msg = _("Autoaligned service instance allocated storage to sqlstack allocated storage")
            print("\n" + self.styler.yellow(msg))

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
            "service allocated storage": dict_get(metadata, "service_servinst.config.dbinstance.AllocatedStorage"),
            "provider allocated storage": dict_get(metadata, "provider_sqlstack.config.allocated_storage"),
            "account name": dict_get(metadata, "service_servinst.account.name"),
            "account uuid": dict_get(metadata, "service_servinst.account.uuid"),
            "engine": dict_get(metadata, "provider_compute_instance.config.dbinstance.Engine"),
            "engine version": dict_get(metadata, "provider_compute_instance.config.dbinstance.EngineVersion"),
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
            raise AdminError(_("unknown hypervisor {hypervisor}").format(hypervisor=hypervisor))
        for v in hypv:
            if hypervisor == "vsphere":
                index = v.get("unit_number")
                ext_id = v.get("disk_object_id")
            elif hypervisor == "openstack":
                index = dict_get(v, "attachments.0.device")
                ext_id = dict_get(v, "id")
            else:
                raise AdminError(_("unknown hypervisor {hypervisor}").format(hypervisor=hypervisor))
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
        print(self.styler.underline(_("Cmp Metadata volumes")))
        cmp_fields = ["#", "name", "index", "ext_id", "size", "id", "has_quotas", "tags"]
        cmp_headers = ["#", "name", "index", "ext_id", "size (GB)", "id", "has_quotas", "tags"]
        self.app.render(tab_cmp, headers=cmp_headers, fields=cmp_fields)
        print(self.styler.underline(_("Hypervisor volumes")))
        hyp_headers = ["#", "name", "index", "ext_id", "size (GB)", "id"]
        hyp_fields = ["#", "name", "index", "ext_id", "size", "id"]
        self.app.render(tab_hyp, headers=hyp_headers, fields=hyp_fields, maxsize=2000)
        compute_res = self.make_suggestions(tab_cmp, tab_hyp)
        db_stack_res = self._storage_suggestion(metadata, command_memo=True)
        estimated_storage = self._estimate_data_storage(metadata)
        msg = _("Extimated overall data storage reading tags is {estimated_storage} GB").format(
            estimated_storage=estimated_storage
        )
        print("\n" + self.styler.yellow(msg))
        fine = compute_res and db_stack_res
        if db_stack_res:
            self._align_service_allocated_storage(metadata)
        if fine:
            self.exit_suggestion()
        return fine, tab_cmp, tab_hyp

    def manage_interactive_quotas(self, tab_cmp):
        """
        Manage quotas. For dbaas only data volumes must be set with enable_quotas to True.
        Usually only the first volume, the boot one must have enable_quotas to False.
        """
        yn = " [y/n] "
        pr1_qt_change = _("Do you want to disable quotas for some volumes?") + yn
        pr1_qt_another_change = _("Do you want to disable quotas for another volume?") + yn
        pr2_qt_choosecmp = _("Which volume's quotas do you want disable?") + " [#/-1 " + _("for all") + "] "
        pr3_qt_check = _("Are you sure you want disable quotas for volume {cmp_vol_num}?") + yn
        pr3_qt_check_all = _("Are you sure you want disable quotas for ALL volumes?") + yn
        print()
        check = self.ask(pr1_qt_change, yn=True)
        while check == "Y":
            cmpindex = None
            while cmpindex is None:
                indata = self.ask(pr2_qt_choosecmp, yn=False)
                try:
                    cmpindex = int(indata)
                    if cmpindex < -1 or cmpindex > len(tab_cmp) - 1:
                        cmpindex = None
                except Exception:
                    cmpindex = None
            if cmpindex != -1:
                check = self.ask(pr3_qt_check.format(cmp_vol_num=cmpindex), yn=True)
            else:
                check = self.ask(pr3_qt_check_all, yn=True)
            print()
            if check == "Y":
                print("", end="", flush=True)
                if cmpindex == -1:
                    for tab_cmp_item in tab_cmp:
                        self.set_cmp_resource_enable_quotas(tab_cmp_item["id"], False)
                else:
                    r_id = tab_cmp[cmpindex]["id"]
                    self.set_cmp_resource_enable_quotas(r_id, False)
            if cmpindex != -1:
                check = self.ask(pr1_qt_another_change, yn=True)
            else:
                check = False

    def print_lvm_section(self, lvm, partitions, volumes):
        """
        Print lvm section info.
        """
        print("\n " + self.styler.underline(_("Volume Groups")))
        size_s = _("size")
        total_size_s = _("total_size")
        for lvm_name in lvm:
            lvm_item = lvm[lvm_name]
            total_lvm_item_size = 0
            lvm_infos = ["\t" + _("logical volumes:")]
            for lv_device, lv in lvm_item.items():
                slaves = lv["slaves"]
                lv_infos = []
                total_lv_size = 0
                for storage_key in sorted(slaves):
                    if storage_key in partitions:
                        storage_size = partitions[storage_key]
                    elif storage_key in volumes:
                        storage_size = volumes[storage_key]["size"]
                    else:
                        storage_size = 0
                    total_lvm_item_size += storage_size
                    total_lv_size += storage_size
                    lv_infos.append(f"\t  |_{storage_key} ({size_s} ≈ {self.bytes_to_human(storage_size)})")
                total_size = self.bytes_to_human(total_lv_size)
                lvm_infos.append(f"\t|_{lv['lv']} (device = {lv_device}, {total_size_s} ≈ {total_size})")
                lvm_infos.append("\t  " + _("slaves block devices:"))
                lvm_infos += lv_infos
            lvm_info = "\n".join(lvm_infos)
            print(f"\n\t{lvm_name} ({total_size_s} ≈ {self.bytes_to_human(total_lvm_item_size)}):\n{lvm_info}")

    def bytes_to_human(self, nbytes):
        """
        Convert bytes to human readable format with measurement unit.
        """
        if nbytes >= 1024**3:
            return f"{round(nbytes / (1024**3))} GB"
        if nbytes >= 1024**2:
            return f"{round(nbytes / (1024**2))} MB"
        if nbytes >= 1024:
            return f"{round(nbytes / 1024)} KB"
        return f"{nbytes} B"

    def print_partitions_section(self, partitions):
        """
        Print partitions section.
        """
        print("\n " + self.styler.underline(_("Partitions")))
        s_partitions = sorted(partitions)
        size_s = _("size")
        print("\t" + "\n\t".join(f"{p} ({size_s} ≈ {self.bytes_to_human(partitions[p])})" for p in s_partitions))

    def _integrate_details_into_volume_section(self, volumes):
        def extract_final_digits(device):
            return device[7:]

        def sd_letter_to_index(name):
            index = 0
            for char in name:
                index = index * 26 + (ord(char) - ord("a") + 1)
            return index - 1

        def compute_index(device):
            return sd_letter_to_index(extract_final_digits(device))

        def detail(device):
            res = {}
            if "/dev/dm-" in device:
                return {"type": "logical volume"}
            if "/dev/sr" in device:
                return {"type": "optical device"}
            try:
                return {"type": "block device", "index": compute_index(device)}
            except:
                pass
            return res

        e_volumes = {}
        for v in volumes:
            item = {"size": volumes[v]}
            item.update(detail(v))
            e_volumes[v] = item
        return e_volumes

    def print_volumes_section(self, volumes):
        """
        Print volumes section.
        """
        def detail(device):
            return ", " + ", ".join(f'{k} = "{device[k]}"' for k in device if k != "size")

        print("\n " + self.styler.underline(_("Volumes")))
        s_volumes = OrderedDict(sorted(volumes.items(), key=lambda item: item[1].get("index", float("inf"))))
        print(
            "\t"
            + "\n\t".join(f"{k} (size ≈ {self.bytes_to_human(v['size'])}{detail(v)})" for k, v in s_volumes.items())
        )

    def print_mount_points_section(self, mount_points):
        """
        Print mount points section.
        """
        print("\n " + self.styler.underline(_("Mount Points")))
        s_mount_points = sorted(mount_points)
        on_s = _("on")
        print("\t" + "\n\t".join(f"{v} {on_s} {mount_points[v]}" for v in s_mount_points))

    def print_estimated_volumes(self, label, devices, id_name):
        """
        Print the estimated volumes size.
        """
        estimated_volume_size = self.bytes_to_human(sum(v["size"] for v in devices.values()))
        estimated_s = _("Estimated")
        total_size_s = _("total_size")
        size_s = _("size")
        msg = self.styler.yellow(f"{estimated_s} {label} ({total_size_s} = {estimated_volume_size})")
        if len(devices) < 1:
            return
        msg += ":\n"
        msg += "\n".join(
            f"Device {a} ({id_name} = {v['volume'][id_name]}, "
            + f"{size_s} ≈ {self.bytes_to_human(v['size'])}, cmp_metadata_volumes_index (#) = {v['cmp_index']})"
            for a, v in devices.items()
        )
        print(msg)

    def print_estimated_vsphere_volumes(self, label, devices):
        """
        Print the estimated volumes size for vSphere.
        """
        self.print_estimated_volumes(label, devices, 'disk_object_id')

    def print_estimated_openstack_volumes(self, label, devices):
        """
        Print the estimated volumes size for Openstack.
        """
        self.print_estimated_volumes(label, devices, 'volume_id')

    def _hypervisor_devices_to_cmp_indexes(self, cmp_vols):
        return {v["resource_hypervisor_volume"]["ext_id"]: i for i, v in enumerate(cmp_vols)}

    def _print_no_tag_suggestion(self):
        no_tag_suggestion = _("No tag suggestions, ")
        update_before = no_tag_suggestion + _("update cmp volumes and retry. ")
        print(self.styler.red(update_before + _("Not all volumes imported in cmp!")))

    def _discriminate_devices(self, lvm, all_block_devices, mount_points):
        fail = _("Tag suggestion is not reliable because dbaas out of standard")
        action = _("Tag it manually!")
        data_lv_dev = next((a for a in mount_points if "data" in mount_points[a]), None)
        if data_lv_dev is None:
            reason = _("could not find data mount point")
            print(self.styler.red(f"{fail}; {reason}. {action}"))
        data_partitions = next((l[a]["slaves"] for l in lvm.values() for a in l if a == data_lv_dev), None)
        if data_partitions is None:
            reason = _("could not find data logical volume")
            print(self.styler.red(f"{fail}; {reason}. {action}"))

        data_devices_s = self._partitions_to_devices(data_partitions)
        data_devices = {}
        backup_devices = {}
        boot_devices = {}
        for device_name, block_device in all_block_devices.items():
            if any(device_name in d for d in data_devices_s):
                data_devices[device_name] = block_device
            else:
                if block_device["index"] != 0:
                    backup_devices[device_name] = block_device
                else:
                    boot_devices[device_name] = block_device
        return boot_devices, data_devices, backup_devices

    def _suggest_tags_for_vsphere_volumes(self, cmp_vols, lvm, volumes, hypervisor_volumes, mount_points):
        """
        Suggest how to apply tags on what was detected on the vSphere vm.
        The volumes will be classified as boot, data or backup.
        """
        all_block_devices = {k: v for k, v in volumes.items() if v["type"] == "block device"}
        if len(hypervisor_volumes) != len(all_block_devices):
            self._print_no_tag_suggestion()
            return
        hypervisor_to_cmp = self._hypervisor_devices_to_cmp_indexes(cmp_vols)
        hypervisor_sorted_volumes = sorted(hypervisor_volumes, key=lambda d: d["unit_number"])
        for e, block_device in enumerate(all_block_devices):
            block_device_item = all_block_devices[block_device]
            hypervisor_volume = hypervisor_sorted_volumes[e]
            disk_object_id = hypervisor_volume["disk_object_id"]
            cmp_index = hypervisor_to_cmp.get(disk_object_id)
            if cmp_index is None:
                self._print_no_tag_suggestion()
                return
            block_device_item.update({"cmp_index": cmp_index, "volume": hypervisor_volume})
        boot_devices, data_devices, backup_devices = self._discriminate_devices(lvm, all_block_devices, mount_points)
        self.print_estimated_vsphere_volumes(_("boot volumes"), boot_devices)
        self.print_estimated_vsphere_volumes(_("data volumes"), data_devices)
        self.print_estimated_vsphere_volumes(_("backup volumes"), backup_devices)

    def _suggest_tags_for_openstack_volumes(self, cmp_vols, lvm, volumes, hypervisor_volumes, mount_points):
        """
        Suggest how to apply tags on what was detected on the Openstack vm.
        The volumes will be classified as boot, data or backup.
        """
        all_block_devices = {k: v for k, v in volumes.items() if v["type"] == "block device"}
        if len(hypervisor_volumes) != len(all_block_devices):
            self._print_no_tag_suggestion()
            return
        hypervisor_to_cmp = self._hypervisor_devices_to_cmp_indexes(cmp_vols)
        n_hypervisor_volumes = {v["attachments"][0]["device"]: v["attachments"][0] for v in hypervisor_volumes}
        for block_device in all_block_devices:
            block_device_item = all_block_devices[block_device]
            hypervisor_volume = n_hypervisor_volumes[block_device]
            cmp_index = hypervisor_to_cmp[hypervisor_volume["volume_id"]]
            block_device_item.update({"cmp_index": cmp_index, "volume": hypervisor_volume})
        boot_devices, data_devices, backup_devices = self._discriminate_devices(lvm, all_block_devices, mount_points)
        self.print_estimated_openstack_volumes(_("boot volumes"), boot_devices)
        self.print_estimated_openstack_volumes(_("data volumes"), data_devices)
        self.print_estimated_openstack_volumes(_("backup volumes"), backup_devices)

    def _partitions_to_devices(self, partitions):
        return {"".join(d for d in device if d.isalpha() or d == "/") for device in partitions}

    def storage_volume_db_suggestion(self, metadata):
        """
        Suggest how to apply tags on what was detected on the vm.
        The volumes will be classified as boot, data or backup.
        """
        fqdn = metadata["provider_compute_instance"]["attributes"]["fqdn"]
        uri = "/v1.0/gas/nodes/" + fqdn
        node = self.cmp_get(uri).get("node", {})
        scm = SshConnectionManager(self)
        db_volume_info = DbVolumeInfo(scm, node)
        res = db_volume_info.get_disk_info()
        print("\n" + self.styler.underline(_("Operating system volumes")))
        lvm = res["lvm"]
        partitions = res["partitions"]
        volumes = res["volumes"]
        volumes = self._integrate_details_into_volume_section(volumes)
        mount_points = res["mount_points"]
        self.print_lvm_section(lvm, partitions, volumes)
        self.print_volumes_section(volumes)
        self.print_partitions_section(partitions)
        self.print_mount_points_section(mount_points)
        hypervisor_volumes = self.get_hypervisor_volumes(metadata)
        hypervisor = dict_get(metadata, "provider_compute_instance.attributes.type")
        cmp_vols: list = dict_get(metadata, "provider_compute_instance.block_device_mapping")
        print("\n" + self.styler.underline("\n" + _("Tags suggestions") + "\n"))
        if hypervisor == "vsphere":
            self._suggest_tags_for_vsphere_volumes(cmp_vols, lvm, volumes, hypervisor_volumes, mount_points)
        elif hypervisor == "openstack":
            self._suggest_tags_for_openstack_volumes(cmp_vols, lvm, volumes, hypervisor_volumes, mount_points)

    def _estimate_storage_by_tag(self, metadata, tag):
        block_devices = metadata["provider_compute_instance"]["block_device_mapping"]
        return sum(a["volume_size"] for a in block_devices[1:] if a["tags"] == tag)

    def _estimate_data_storage(self, metadata):
        return self._estimate_storage_by_tag(metadata, "")

    def _storage_suggestion(self, metadata, command_memo=False):
        ret = False
        block_devices = metadata["provider_compute_instance"]["block_device_mapping"]
        has_quotas = any(a["config"].get("has_quotas", True) for a in block_devices)
        if has_quotas:
            quotas_msg = _("Usually the dbaas storage 'has_quotas' field is set to False for all volumes.")
            self.suggestion_print("Q", _("to disable Quotas.") + " " + quotas_msg)

        current_storage = metadata["provider_sqlstack"]["config"]["allocated_storage"]
        estimated_data_storage = self._estimate_data_storage(metadata)

        if current_storage == estimated_data_storage:
            self.print_success()
            success_msg = _("Overall data storage is coherent with volumes and tags.")
            print(self.styler.green(success_msg))
            ret = True
        else:
            pr_sto_explain = _(
                "Usually the allocated overall data storage for dbaas is set as the sum of the size of "
                "all volumes except the first one and those with a tag."
            )
            current_storage_msg = (
                _(
                    "Current overall data storage is {current_storage} GB, Extimated overall data storage reading tags is {estimated_data_storage} GB."
                ).format(current_storage=current_storage, estimated_data_storage=estimated_data_storage)
            )
            print(self.styler.red("\n" + pr_sto_explain + "\n" + current_storage_msg))
            if command_memo:
                self.suggestion_print("V", _("to have a Volume picture."))
                self.suggestion_print("T", _("to Tag the cmp metadata volumes."))
                self.suggestion_print("S", _("to set overall Storage."))
        return ret

    def manage_interactive_storage(self, metadata):
        """
        Manage interactive storage; change the metadata volume size.
        """
        yn = " [y/n] "
        pr1_sto_change = _("Do you want change the database allocated storage?") + yn
        pr2_sto_choose = _("Which value do you want to set for allocated storage (in GB)?") + " [#] "
        pr3_sto_check = _("Are you sure you want to set allocated storage to {storage_value} ?") + yn
        # change t backup tag interaction
        print()
        check = self.ask(pr1_sto_change, yn=True)
        if check == "Y":
            storage_value = -1
            while storage_value == -1:
                self._storage_suggestion(metadata)
                indata = self.ask(pr2_sto_choose, yn=False)
                try:
                    storage_value = int(indata)
                    if storage_value < 0:
                        storage_value = -1
                except Exception:
                    storage_value = -1
            check = self.ask(pr3_sto_check.format(storage_value=storage_value), yn=True)
            print()
            if check == "Y":
                self.set_cmp_service_config(
                    dict_get(metadata, "service_servinst.uuid"),
                    "dbinstance.AllocatedStorage",
                    str(storage_value),
                )
                self.set_cmp_resource_config(
                    dict_get(metadata, "provider_sqlstack.id"),
                    "allocated_storage",
                    str(storage_value),
                )

    def manage_interactions(self, database, metadata):
        """
        Manage user interactions in order to force volume mapping.
        """
        prompt_0 = (
            _("You can press: ") + "\n"
            + self.styler.underline("R") + "eload; "
            + _("to Reload menu with cmp metadata volumes and hypervisor volumes") + ",\n"
            + self.styler.underline("U") + "pdate; "
            + _("to Update cmp metadata volumes") + ",\n"
            + self.styler.underline("D") + "elete; "
            + _("to Delete cmp metadata volumes") + ",\n"
            + self.styler.underline("A") + "dd; "
            + _("to Add cmp metadata volumes") + ",\n"
            + self.styler.underline("V") + "olumes; "
            + _("to see Volumes details") + ",\n"
            + self.styler.underline("T") + "ags; "
            + _("to Tag cmp metadata volumes") + ",\n"
            + self.styler.underline("Q") + "uotas; "
            + _("to disable Quotas") + ",\n"
            + self.styler.underline("S") + "torage; "
            + _("to set overall data Storage") + ",\n"
            + "e" + self.styler.underline("X") + "it; "
            + _("to eXit") + ".\n"
        )
        allowed = ("R", "U", "D", "A", "V", "T", "Q", "S", "X")
        prompt_1 = f"Reload, Update, Delete, Add, Volumes, Tags, Quotas, Storage, eXit [{'/'.join(allowed)}]? "
        _x, tab_cmp, tab_hyp = self.show_metadata(metadata)
        # change volume metadata using hypervisor data
        check = ""
        while check != "X":
            print("\n" + prompt_0)
            check = self.ask(prompt_1, yn=False, allowed=allowed)
            if check == "R":
                try:
                    print()
                    print(self.styler.clear_line() + _("Collecting Metadata"), end="...", flush=True)
                    metadata = self.get_metadata(database)
                except AdminError as e:
                    print(self.styler.error(data=str(e)))
                _x, tab_cmp, tab_hyp = self.show_metadata(metadata)
            elif check == "U":
                self.manage_interactive_mapping(tab_cmp, tab_hyp, metadata)
            elif check == "D":
                self.manage_interactive_delete(metadata)
            elif check == "A":
                self.manage_interactive_import(metadata)
            elif check == "V":
                self.storage_volume_db_suggestion(metadata)
            elif check == "T":
                self.manage_interactive_tags(tab_cmp)
            elif check == "Q":
                self.manage_interactive_quotas(tab_cmp)
            elif check == "S":
                self.manage_interactive_storage(metadata)
            elif check == "X":
                print("\n\n", _("Bye"), sep="")

    def _import_volume_resource(
        self, container_name, vol_hyp, physical_vol_template, metadata, container, has_quotas=False
    ):
        serpr_uuid = super()._import_volume_resource(
            container_name, vol_hyp, physical_vol_template, metadata, container, has_quotas=has_quotas
        )
        self.reset_cmp_cache_resource(dict_get(metadata, "provider_sqlstack.id", default=serpr_uuid))

    def remove_volume_metadata(self, volc: int, metadata: dict):
        """
        Remove volume metadata.
        """
        r_id = super().remove_volume_metadata(volc, metadata)
        self.reset_cmp_cache_resource(dict_get(metadata, "provider_sqlstack.id", default=r_id))
