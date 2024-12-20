# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from typing import List, Callable, Union
import json
import yaml

from cement.ext.ext_argparse import ex
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import ARGS
from .child import AdminChildController, AdminError


class DatabaseAdminController(AdminChildController):
    """
    DatabaseAdminController: This contains commands to manage and adjust metadata of dbaas stackv2.
    """

    class Meta:
        label = "database"
        description = "database administration commands"
        help = "database administration commands"

    @ex(
        help="check database storage",
        description="""
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
""",
        arguments=ARGS(
            [
                (
                    ["database"],
                    {
                        "help": "database service id uuid or name; this is one of the service identifiers",
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
        Sanity check for dbaas metadata stackv2 against platform.
        """
        self.cmp_fernet = self.app.pargs.cmp_key
        if self.cmp_fernet is None or self.cmp_fernet == "":
            print("Warning: You have no specified fernet key", end="\n")
        else:
            print(f"Info: Using Fernet key {self.cmp_fernet}", end="\n")
        database = self.app.pargs.database
        metadata = None
        try:
            print()
            print(self.styler.clear_line() + "Collecting Metadata", end="...", flush=True)
            metadata = self.get_metadata(database)
        except AdminError as e:
            print(self.styler.error(data=str(e)))

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

    def get_metadata(self, database: str) -> dict:
        """
        Get database from service down to hypervisor in order
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

        self.print_looking_for("Servervice Instance")
        bu_servinst = self.get_cmp_service_instance(database)
        resource_uuid = bu_servinst.get("resource_uuid")
        provider_sqlstack = {
            "id": resource_uuid,
            "config": self.get_cmp_resource_config(resource_uuid),
        }
        # get of the unuseful resource uri = f"/v1.0/nrs/entities/{resource_uuid}"
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
            raise AdminError(
                f" Could not find any ComputeInstance in the ComputeStack {resource_uuid} "
                + f"which implements the database {database}"
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
                + f"which implements the database {database}"
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
        result["provider_sqlstack"] = provider_sqlstack
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
        compute_res = self.make_suggestions(tab_cmp, tab_hyp)
        db_stack_res = self.storage_suggestion(metadata)
        if compute_res and db_stack_res:
            self.print_info()
            msg = self.styler.red("Please e" + self.styler.underline("X")) + self.styler.red("it, all is fine!")
            print(msg)
        return general_instance, tab_cmp, tab_hyp

    def manage_interactive_quotas(self, tab_cmp):
        """
        Manage quotas. For dbaas only data volumes must be set with enable_quotas to True.
        Usually only the first volume, the boot one must have enable_quotas to False.
        """
        PR1_QT_CHANGE = "Do you want to disable quotas for some volumes? [y/n] "
        PR2_QT_CHOOSECMP = "Which volume's quotas do you want disable? [#/-1 for all] "
        PR3_QT_CHECK = "Are you sure you want disable quotas for volume %s? [y/n] "
        PR3_QT_CHECK_ALL = "Are you sure you want disable quotas for ALL volumes? [y/n] "
        PR1_QT_ANOTHER_CHANGE = "Do you want to disable quotas for another volume? [y/n] "
        print()
        check = self.ask(PR1_QT_CHANGE, yn=True)
        while check == "Y":
            cmpindex = None
            while cmpindex is None:
                indata = self.ask(PR2_QT_CHOOSECMP, yn=False)
                try:
                    cmpindex = int(indata)
                    if cmpindex < -1 or cmpindex > len(tab_cmp) - 1:
                        cmpindex = None
                except Exception:
                    cmpindex = None
            if cmpindex != -1:
                check = self.ask(PR3_QT_CHECK % cmpindex, yn=True)
            else:
                check = self.ask(PR3_QT_CHECK_ALL, yn=True)
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
                check = self.ask(PR1_QT_ANOTHER_CHANGE, yn=True)
            else:
                check = False

    def storage_suggestion(self, metadata):
        ret = False
        msg = ""
        block_devices = metadata["provider_compute_instance"]["block_device_mapping"]
        has_quotas = any(a["config"]["has_quotas"] for a in block_devices)
        if has_quotas:
            quotas_msg = "Usually the dbaas storage 'has_quotas' field is set to False for all volumes! Please disable"
            msg += (
                self.styler.red(quotas_msg)
                + " "
                + self.styler.red(self.styler.underline("Q"))
                + self.styler.red("uotas.")
            )
        current_storage = metadata["provider_sqlstack"]["config"]["allocated_storage"]
        extimated_storage = sum(a["volume_size"] for a in block_devices[1:] if a["tags"] == "")
        if current_storage == extimated_storage:
            self.print_success()
            success_msg = "Overall storage is coherent with volumes and tags."
            print(self.styler.green(success_msg))
        else:
            PR_STO_EXPLAIN = self.styler.red(
                "Usually the allocated overall storage for dbaas is set as the sum of the size of "
                "all volumes except the first one and those with a tag."
            )
            post_msg = (
                self.styler.red(f"Please " + self.styler.underline("T"))
                + self.styler.red("ag the cmp metadata volumes before set overall " + self.styler.underline("S"))
                + self.styler.red("torage!")
            )
            msg += "\n" + PR_STO_EXPLAIN + " " + post_msg
            current_storage_msg = (
                f"Current overall storage is {current_storage} GiB, "
                + f"Extimated overall storage is {extimated_storage} GiB. "
                + "Please set overall "
                + self.styler.underline("S")
            )
            msg += "\n" + self.styler.red(current_storage_msg) + self.styler.red("torage.")
        if msg != "":
            self.print_warning()
            print(msg, flush=True)
        else:
            ret = True
        return ret

    def manage_interactive_storage(self, metadata):
        """
        Manage interactive storage; change the metadata volume size.
        """
        PR1_STO_CHANGE = "Do you want change the database allocated storage? [y/n] "
        PR2_STO_CHOOSE = "Which value do you want to set for allocated storage (in GiB)? [#] "
        PR3_STO_CHECK = "Are you sure you want to set allocated storage to %s ? [y/n] "
        # change t backup tag interaction
        print()
        check = self.ask(PR1_STO_CHANGE, yn=True)
        if check == "Y":
            storage_value = -1
            while storage_value == -1:
                self.storage_suggestion(metadata)
                indata = self.ask(PR2_STO_CHOOSE, yn=False)
                try:
                    storage_value = int(indata)
                    if storage_value < 0:
                        storage_value = -1
                except Exception:
                    storage_value = -1
            check = self.ask(PR3_STO_CHECK % (storage_value), yn=True)
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
            + "ag cmp metadata volumes, disable "
            + self.styler.underline("Q")
            + "uotas, set overall "
            + self.styler.underline("S")
            + "torage, or e"
            + self.styler.underline("X")
            + "it"
        )
        allowed = ("R", "U", "D", "A", "T", "Q", "S", "X")
        PROMPT_1 = f"Reload, Update, Delete, Add, Tags, Quotas, Storage, or eXit [{'/'.join(allowed)}]? "
        _, tab_cmp, tab_hyp = self.show_metadata(metadata)
        # change volume metadata using hypervisor data
        check = ""
        while check != "X":
            print("\n" + PROMPT_0)
            check = self.ask(PROMPT_1, yn=False, allowed=allowed)
            if check == "R":
                try:
                    print()
                    print(self.styler.clear_line() + "Collecting Metadata", end="...", flush=True)
                    metadata = self.get_metadata(database)
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
            elif check == "Q":
                self.manage_interactive_quotas(tab_cmp)
            elif check == "S":
                self.manage_interactive_storage(metadata)
            elif check == "X":
                print("\n\n", "Bye", sep="")

    def _import_volume_resource(self, container_name, vol_hyp, physical_vol_template, metadata, container):
        serpr_uuid = super()._import_volume_resource(
            container_name, vol_hyp, physical_vol_template, metadata, container
        )
        self.reset_cmp_cache_resource(dict_get(metadata, "provider_sqlstack.id", default=serpr_uuid))

    def remove_volume_metadata(self, volc: int, metadata: dict):
        """
        Remove volume metadata.
        """
        r_id = super().remove_volume_metadata(volc, metadata)
        self.reset_cmp_cache_resource(dict_get(metadata, "provider_sqlstack.id", default=r_id))
