# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from sys import stdout
from typing import List, Callable, Union
from cement.ext.ext_argparse import ex
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import ARGS
from .child import AdminChildController, AdminError


def myprint(*args, **kwargs):
    data = ""
    for d in args:
        data += str(d)
    data += kwargs.get("end", "\n")
    flush = kwargs.get("flush", True)
    stdout.write(data)
    if flush:
        stdout.flush()


class DatabaseAdminController(AdminChildController):
    class Meta:
        label = "database"
        description = "database administartion commands"
        help = "database administartion commands"

    @ex(
        help="check database storage",
        description="""Database management, the holistic way :)
        The database parameters must be a service identifier.
        It should be an uuid, id or name  of a db instance.
        You can get it listing the services of the account using commands like "bu account get" or  "bu dbaas db-instance get"..
        The porcedure checks database storage consistency beetween nivola and hypervisors.
        The procedure query both Nivola and the hypervisor on which the database server is runing.
        Then diplay details about volumes.
        Pay attention to the column "ext_id" of the volumes that should uniquely identify the hypervisor's volume.
        You may change Nivola's volumes information by matching with hypervisor volumes.
        You will be asked for which match has to be established.
        Then you will be asked for change backup tags on the database volume.
        Remeber that volume tagged as backup will generates ad hoc metrics distinct from alocated storage.
        Then you will be asked to disable volume quotas.
        Database's volumes should always have qutas disbled otheways they will generate compute metrics in adition to database matrics.
        Afterall you will be asked to change the allocated storage for the databases.
        The allocated storage is displayed by the service portal and some beehive commands, it should be the sum of database volumes used for database data.
        As a matter of fact, Nivola calculates data storage as the sum of attached volumes that are neither the boot volume or marked as backup.


        """,
        arguments=ARGS(
            [
                (
                    ["database"],
                    {
                        "help": "database service id uuid or name  this is one of the serivce identifiers",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["--tofile"],
                    {
                        "help": "store to file only when format is json or yaml",
                        "dest": "tofile",
                        "action": "store_true",
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def check(self):
        if self.key is None or self.key == "":
            print("Warning: Using no decription key", end="\n")
        else:
            print("Warning: Using %s" % self.key, end="\n")
        database = self.app.pargs.database
        try:
            print()
            print(self.styler.clear_line() + "Collecting Metadata", end="...", flush=True)
            result = self.get_metadata(database)
        except AdminError as ex:
            print(self.styler.error(data=str(ex)))

        if self.is_output_text():
            self.manage_interactions(database, result)
            # al_instance, tab_cmp, tab_hyp = self.show_metadata(result)
            # self.manage_interactive_mapping(al_instance, tab_cmp, tab_hyp, result)
            # self.manage_interactive_tags(al_instance, tab_cmp, tab_hyp, result)
            # self.manage_interactive_quotas(al_instance, tab_cmp, tab_hyp, result)
            # self.manage_interactive_storage(al_instance, tab_cmp, tab_hyp, result)
            print()
        else:
            outfile = open(f"{database}.{self.format}", mode="+tw")
            if self.format == "json":
                import json

                outfile.write(json.dumps(result))
                outfile.close()
            elif self.format == "yaml":
                import yaml

                yaml.dump(result, outfile)
            self.app.render(result, key="object", details=True)

    def get_metadata(self, database: str) -> dict:
        """
        get database from service down to hypervisor in order
        to get all information about volumes mapped and available
        """

        def tree_search(children: List[dict], check: Callable[[dict], bool]) -> Union[dict, None]:
            for child in children:
                if check(child):
                    return child
                else:
                    child.get("chldren", [])
                    rec = tree_search(child.get("children", []), check)
                    if isinstance(rec, dict):
                        return rec
            return None

        def get_server(node: dict) -> bool:
            tp = node.get("type")
            if tp == "Vsphere.DataCenter.Folder.Server":
                return True
            elif tp == "Openstack.Domain.Project.Server":
                return True
            else:
                return False

        def get_volume(node: dict) -> bool:
            tp = node.get("type")
            if tp == "Vsphere.DataCenter.Folder.volume":
                return True
            elif tp == "Openstack.Domain.Project.Volume":
                return True
            else:
                return False

        # res = self.cmp_get(uri, data=data).get("resourcetree", {})
        print(
            self.styler.clear_line() + "Now sarchinfg for Service Instance",
            end="...",
            flush=True,
        )
        bu_servinst = self.get_cmp_service_instance(database)

        resource_uuid = bu_servinst.get("resource_uuid")
        provider_sqlstack = {
            "id": resource_uuid,
            "config": self.get_cmp_resource_config(resource_uuid),
        }
        # get della risorsa non utile uri = f"/v1.0/nrs/entities/{resource_uuid}"
        # get delle linked enities per cercare la ComputeInstance che implementa il db
        print(
            self.styler.clear_line() + "Now serching for resource linked entities",
            end="...",
            flush=True,
        )
        linked_resurces = self.get_cmp_linkedres(resource_uuid)
        compute_instance = None

        # get della ComputeInstance tra le linked entities
        print(
            self.styler.clear_line() + "Now serching for Provider.ComputeZone.ComputeInstance",
            end="...",
            flush=True,
        )
        for resource in linked_resurces:
            definition = dict_get(resource, "__meta__.definition")
            if definition == "Provider.ComputeZone.ComputeInstance":
                compute_instance = resource
                break
        if compute_instance is None:
            raise AdminError(
                f" Could not find any ComputeInstance in the ComputeStack {resource_uuid} which implements the database {database}"
            )
        for vol in compute_instance.get("block_device_mapping", []):
            tags = self.get_cmp_entity_tags(vol["id"])
            vol["tags"] = tags
            config = self.get_cmp_resource_config(vol["id"])
            vol["config"] = config
        # get server openstack o vsphere
        print(
            self.styler.clear_line() + "Now serching for hypervisor Server in ComputeInstance tree",
            end="...",
            flush=True,
        )
        compute_tree = self.get_cmp_restree(compute_instance.get("id"))
        hypervisor_server = tree_search(dict_get(compute_tree, "resourcetree.children", default=[]), get_server)
        if hypervisor_server is None:
            raise AdminError(
                f" Could not find any Server in CmputeInstance in the ComputeStack {resource_uuid} which implements the database {database}"
            )

        # get hypervisor info in order to connect from resource containers
        print(
            self.styler.clear_line() + "Now serching for hypervisor container",
            end="...",
            flush=True,
        )
        hypervisor_container = self.get_cmp_container(hypervisor_server.get("container"))
        print(
            self.styler.clear_line() + "Now serching for hypervisor Server and volumes",
            end="...",
            flush=True,
        )
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
        """volumes  display"""
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
            "engine versione": dict_get(metadata, "provider_compute_instance.config.dbinstance.EngineVersion"),
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

            for v in hypv:
                tab_hyp.append(
                    {
                        "#": i,
                        "name": v.get("name"),
                        "index": v.get("unit_number"),
                        "ext_id": v.get("disk_object_id"),
                        "size": v.get("size"),
                        "id": v.get("id"),
                    }
                )
                i += 1
        elif hypervisor == "openstack":
            hypv: list = dict_get(metadata, "hypervisor_serverserver_det.os-extended-volumes:volumes_attached")
            for v in hypv:
                tab_hyp.append(
                    {
                        "name": dict_get(v, "name"),
                        "index": dict_get(v, "attachments.0.device"),
                        "ext_id": dict_get(v, "id"),
                        "size": dict_get(v, "size"),
                        "id": dict_get(v, "description"),
                    }
                )
                i += 1
        else:
            raise AdminError(f"hypervisor {hypervisor} not known")
        print(self.styler.clear_line() + self.styler.underline("Object"))
        self.app.render(general_instance, details=True)
        print(self.styler.underline("Current Metadata"))
        self.app.render(
            tab_cmp,
            headers=[
                "#",
                "name",
                "index",
                "ext_id",
                "size",
                "id",
                "has_quotas",
                "tags",
            ],
        )
        print(self.styler.underline("Hypervisor Metadata"))
        self.app.render(tab_hyp, headers=["#", "name", "index", "ext_id", "size", "id"])
        if len(tab_cmp) != len(tab_hyp):
            print(
                self.styler.format("Warning! ", self.styler.BLINK)
                + self.styler.green(
                    "The number of volumes reported by hypervisor does not match the volumes in metadata!"
                )
            )

        return general_instance, tab_cmp, tab_hyp

    def manage_interactions(self, database, result):
        """user interaction in ordere to force volume mapping"""
        PROMPT_0 = (
            "Yuo can: "
            + self.styler.underline("R")
            + "eload metadata, "
            + self.styler.underline("U")
            + "pdate volume info, "
            + self.styler.underline("D")
            + "elete volume, "
            + self.styler.underline("L")
            + "oad volume, change "
            + self.styler.underline("T")
            + "ags, diasble "
            + self.styler.underline("Q")
            + "uotas, set overall "
            + self.styler.underline("S")
            + "torage, or e"
            + self.styler.underline("X")
            + "it"
        )
        PROMPT_1 = "Reload, Update, Delete, Load , Tags, Quotas, Storage, or eXit [r/u/d/l/t/q/s/x] ?"
        al_instance, tab_cmp, tab_hyp = self.show_metadata(result)
        print(PROMPT_0)
        # change volume metadata using hypervisor data
        check = ""
        while check != "X":
            check = self.ask(PROMPT_1, yn=False, alowed=("R", "U", "D", "L", "T", "Q", "S", "X"))
            if check == "R":
                try:
                    print()
                    print(self.styler.clear_line() + "Collecting Metadata", end="...", flush=True)
                    result = self.get_metadata(database)
                except AdminError as ex:
                    print(self.styler.error(data=str(ex)))
                al_instance, tab_cmp, tab_hyp = self.show_metadata(result)
                print(PROMPT_0)
            elif check == "U":
                self.manage_interactive_mapping(al_instance, tab_cmp, tab_hyp, result)
            elif check == "D":
                self.manage_interactive_delete(al_instance, tab_cmp, tab_hyp, result)
            elif check == "L":
                self.manage_interactive_import(al_instance, tab_cmp, tab_hyp, result)
            elif check == "T":
                self.manage_interactive_tags(al_instance, tab_cmp, tab_hyp, result)
            elif check == "Q":
                self.manage_interactive_quotas(al_instance, tab_cmp, tab_hyp, result)
            elif check == "S":
                self.manage_interactive_storage(al_instance, tab_cmp, tab_hyp, result)
            elif check == "X":
                print("\n\n", "Bye", sep="")

    def manage_interactive_mapping(self, general_instance, tab_cmp, tab_hyp, metadata):
        """user interaction in ordere to force volume mapping"""
        PR1_VOL_CHANGEVAOLUME = "Do you want to change current metadata with hypervisor data? [y/n] "
        PR2_VOL_CHOOSECMP = "Which volume do you want to change? [#] "
        PR3_VOL_CHOOSEHYP = "Which hypervisor volume do you want to map to volume %s ? [#] "
        PR4_VOL_CHECK = "Do you want ti fill matadata %s with hypervisor volume %s ? [y/n] "

        print()
        # change volume metadata using hypervisor data
        check = self.ask(PR1_VOL_CHANGEVAOLUME, yn=True)
        while check == "Y":
            cmpindex = -1
            while cmpindex == -1:
                indata = self.ask(PR2_VOL_CHOOSECMP, yn=False)
                try:
                    cmpindex = int(indata)
                    if cmpindex < 0 or cmpindex > len(tab_cmp) - 1:
                        cmpindex: -1
                except Exception:
                    cmpindex: -1
            hypindex = -1
            while hypindex == -1:
                indata = self.ask(PR3_VOL_CHOOSEHYP % (cmpindex), yn=False)
                try:
                    hypindex = int(indata)
                    if hypindex < 0 or hypindex > len(tab_hyp) - 1:
                        hypindex: -1
                except Exception:
                    hypindex: -1
            check = self.ask(PR4_VOL_CHECK % (cmpindex, hypindex), yn=True)
            print()
            if check == "Y":
                print("", end="", flush=True)
                self.update_volume(cmpindex, hypindex, tab_cmp, tab_hyp, metadata)

            check = self.ask(PR1_VOL_CHANGEVAOLUME, yn=True)

    def manage_interactive_tags(self, general_instance, tab_cmp, tab_hyp, metadata):
        PR1_TAG_CHANGE = "Do you want to add/remove backup a tag from volume [y/n]"
        PR2_TAG_CHOOSECMP = "Which volume's tag do you want to change? [#] "
        PR3_TAG_CHECK = "Are you sure you want to %s the '%s' tag from volume %s ? [y/n] "
        TAG = "nws$volume_bck"
        ## change tag interaction
        print()
        check = self.ask(PR1_TAG_CHANGE, yn=True)
        while check == "Y":
            cmpindex = -1
            action = ""
            while cmpindex == -1:
                indata = self.ask(PR2_TAG_CHOOSECMP, yn=False)
                try:
                    cmpindex = int(indata)
                    if cmpindex < 0 or cmpindex > len(tab_cmp) - 1:
                        cmpindex = -1
                    else:
                        if TAG in tab_cmp[cmpindex]["tags"]:
                            action = "delete"
                        else:
                            action = "add"
                except Exception:
                    cmpindex = -1
            check = self.ask(PR3_TAG_CHECK % (action, TAG, cmpindex), yn=True)
            print()
            if check == "Y":
                print("", end="", flush=True)
                r_id = tab_cmp[cmpindex]["id"]
                if action == "delete":
                    self.del_cmp_entity_tags(r_id, TAG)
                else:
                    self.set_cmp_entity_tags(r_id, TAG)

            check = self.ask(PR1_TAG_CHANGE, yn=True)

    def manage_interactive_quotas(self, general_instance, tab_cmp, tab_hyp, metadata):
        PR1_QT_CHANGE = "Do you want to disable quotas for any volumes [y/n]"
        PR2_QT_CHOOSECMP = "Which volume's quotas do you want disable? [#/-1 for all] "
        PR3_QT_CHECK = "Are you sure you want disable  quotas for volume  %s ? [y/n] "
        print()
        check = self.ask(PR1_QT_CHANGE, yn=True)
        while check == "Y":
            cmpindex = -999
            while cmpindex == -999:
                indata = self.ask(PR2_QT_CHOOSECMP, yn=False)
                try:
                    cmpindex = int(indata)
                    if cmpindex < -1 or cmpindex > len(tab_cmp) - 1:
                        cmpindex = -999
                except Exception:
                    cmpindex = -999
            check = self.ask(PR3_QT_CHECK % cmpindex, yn=True)
            print()
            if check == "Y":
                print("", end="", flush=True)
                if cmpindex == -1:
                    for i in range(0, len(tab_cmp)):
                        r_id = tab_cmp[i]["id"]
                        self.set_cmp_resource_enable_quotas(r_id, False)
                else:
                    r_id = tab_cmp[cmpindex]["id"]
                    self.set_cmp_resource_enable_quotas(r_id, False)

            check = self.ask(PR1_QT_CHANGE, yn=True)

    def manage_interactive_storage(self, general_instance, tab_cmp, tab_hyp, metadata):
        PR1_STO_CHANGE = "Do you want change the database allocated storage? [y/n]"
        PR2_STO_CHOOSE = "Which value do you want to set for allocated storage? [#] "
        PR3_STO_CHECK = "Are you sure you want to set allocated storage to %s ? [y/n] "
        TAG = "nws$volume_bck"
        ## change t backup tag interaction
        print()
        check = self.ask(PR1_STO_CHANGE, yn=True)
        if check == "Y":
            storage_value = -1
            while storage_value == -1:
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

    def manage_interactive_import(self, general_instance, tab_cmp, tab_hyp, metadata):
        PR1_LOAD_CHANGE = "Do you want load an existing hypervisor volume ? [y/n]"
        PR2_LOAD_CHOOSE = "Which hypervisor volume do you want to load? [#] "
        PR3_LOAD_CHECK = "Are you sure you want to load hypervisor volume # %s ? [y/n] "
        ## change t backup tag interaction
        print()
        check = self.ask(PR1_LOAD_CHANGE, yn=True)
        if check == "Y":
            volumenumber = -1
            while volumenumber == -1:
                indata = self.ask(PR2_LOAD_CHOOSE, yn=False)
                try:
                    volumenumber = int(indata)
                    if volumenumber < 0:
                        volumenumber = -1
                except Exception:
                    volumenumber = -1
            check = self.ask(PR3_LOAD_CHECK % (volumenumber), yn=True)
            print()
            if check == "Y":
                self.import_volume(volumenumber, tab_cmp, tab_hyp, metadata)

    def manage_interactive_delete(self, general_instance: dict, tab_cmp: dict, tab_hyp: dict, metadata: dict):
        PR1_REMOVE_PROMPT = "Do you want to delete a non existing volume described by current metadata ? [y/n]"
        PR2_REMOVE_CHOOSE = "Which current metadata volume do you want to remove? [#] "
        PR3_REMOVE_CHECK = "Are you sure you want to remove metadata volume # %s ? [y/n] "
        ## change t backup tag interaction
        print()
        check = self.ask(PR1_REMOVE_PROMPT, yn=True)
        if check == "Y":
            volumenumber = -1
            while volumenumber == -1:
                indata = self.ask(PR2_REMOVE_CHOOSE, yn=False)
                try:
                    volumenumber = int(indata)
                    if volumenumber < 0:
                        volumenumber = -1
                except Exception:
                    volumenumber = -1
            check = self.ask(PR3_REMOVE_CHECK % (volumenumber), yn=True)
            print()
            if check == "Y":
                self.remove_volume_metadata(volumenumber, tab_cmp, tab_hyp, metadata)

    def import_volume(self, volh: int, tab_cmp: List[dict], tab_hyp: List[dict], metadata: dict):
        STOK = f"SUCCESS importing volume {volh}"
        STERR = f"ERROR importing volume {volh} : %s"

        print("\n", self.styler.clear_line(), "Gathering info", sep="", end="")
        container: str = dict_get(metadata, "provider_compute_instance.attributes.type", default="").lower()
        container_name: str = dict_get(metadata, "hypervisor_container.name")
        template_id = dict_get(
            metadata, "provider_compute_instance.block_device_mapping.0.resource_hypervisor_volume.uuid"
        )
        print(self.styler.clear_line(), "Using first volume as template", sep="", end="")
        physical_vol_template: dict = self.get_cmp_resource(template_id)
        if container_name is None:
            raise AdminError("Container Name not found")
        try:
            vol_hyp: dict = metadata["hypervisor_serverserver_det"]["volumes"][volh]
        except Exception:
            raise AdminError(f"Hypervisor volume {volh} not found")
        try:
            if container == "vsphere":
                self._import_vspherevolume(container_name, vol_hyp, physical_vol_template, metadata)
                print(self.styler.clear_line() + STOK + self.styler.cur_up(1), end="", sep="")
            if container == "openstack":
                raise AdminError("Import volume from openstack not implemented")
            pass
        except Exception as ex:
            print(self.styler.clear_line(), STERR % str(ex), self.styler.cur_up(1), end="", sep="")

    def _import_vspherevolume(self, container_name, vol_hyp, physical_vol_template, metadata):
        print(self.styler.clear_line(), f"vSphere {container_name}", sep="", end="")
        ## import resurce describing physical volume
        volume_type = dict_get(physical_vol_template, "attributes.volume_type")
        attribute = {
            "size": int(vol_hyp["size"]),
            "volume_type": volume_type,
            "source_volume": None,
            "source_image": None,
            "bootable": False,
            "encrypted": False,
            "has_quotas": True,
            "status": "in-use",
        }
        name = dict_get(metadata, "service_servinst.name") + "-" + vol_hyp.get("name", "imported_volume")
        # "Vsphere.DataCenter.Folder.volume"
        resclass = "beehive_resource.plugins.vsphere.entity.vs_volume.VsphereVolume"
        desc = vol_hyp.get("id", "imported_volume")
        physical_resource_id = vol_hyp.get("disk_object_id", None)
        parent = str(physical_vol_template["parent"])
        # attribute: dict = None,
        # tags: List[str] = None
        print(self.styler.clear_line(), f"Adding physical volume metadata. ", sep="", end="")
        volph = self.cmp_resource_import(
            container=container_name,
            resclass=resclass,
            attribute=attribute,
            name=name,
            desc=desc,
            physical_resource_id=physical_resource_id,
            parent=parent,
        )

        # set state and ext_id
        print(self.styler.clear_line(), f"Ensure physical volume metadata end status. ", sep="", end="")
        volph_uuid = volph["uuid"]
        serph_uuid = dict_get(metadata, "resource_hypervisor_server.uuid")
        self.set_cmp_resource(volph_uuid, ext_id=physical_resource_id)
        self.set_cmp_resource_active(volph_uuid)

        print(self.styler.clear_line(), f"Linking physical Server metadata with volume metadata. ", sep="", end="")
        ## add link from resource physical server
        self.add_cmp_resource_link(
            name=f"{serph_uuid}-{volph_uuid}volume-link",
            linktype="volume",
            attrib={"boot": False},
            start_resource=serph_uuid,
            end_resource=volph_uuid,
        )
        ## add  provider vvolume
        print(self.styler.clear_line(), f"Adding provider volume metadata. ", sep="", end="")
        volpr = self.cmp_volume_import(physical_resource_id=volph["uuid"], name=name)

        ## add link from provider compute instace
        print(self.styler.clear_line(), f"Linking provider server with provider volume metadata.", sep="", end="")
        volpr_uuid = volpr["uuid"]
        unit_number = vol_hyp["unit_number"]
        serpr_uuid = dict_get(metadata, "provider_compute_instance.uuid")
        self.add_cmp_resource_link(
            name=f"{serpr_uuid}-{volpr_uuid}volume-link",
            linktype=f"volume.{unit_number}",
            start_resource=serpr_uuid,
            end_resource=volpr_uuid,
        )
        # clear cache
        print(self.styler.clear_line(), f"Clear provider server cache.", sep="", end="")
        self.reset_cmp_cache_resource(serpr_uuid)
        self.reset_cmp_cache_resource(dict_get(metadata, "provider_compute_instance.id", default=serpr_uuid))
        self.reset_cmp_cache_resource(dict_get(metadata, "provider_sqlstack.id", default=serpr_uuid))

    def remove_volume_metadata(self, volc: int, tab_cmp: List[dict], tab_hyp: List[dict], metadata: dict):
        STOK = f"SUCCESS removing volume {volc}"
        STERR = f"ERROR removing volume {volc} : %s"
        try:
            vol_meta: dict = metadata["provider_compute_instance"]["block_device_mapping"][volc]
        except Exception:
            raise AdminError(f"Nivola volume {volc} not found")
        pass
        try:
            r_id = vol_meta["resource_hypervisor_volume"]["uuid"]
            print(self.styler.clear_line(), f"Setting physical {r_id} volume size to null", end="", sep="")
            self.set_cmp_resource_ext_id(r_id, "")
            self.set_cmp_resource_ext_id(r_id, None)

            r_id = vol_meta["id"]
            print(self.styler.clear_line(), f"deleting Provider Volume {r_id} volume", end="", sep="")
            self.delete_resource(r_id, force=True, deep=False)

            print(self.styler.clear_line(), f"deleting Provider Volume {r_id} volume", end="", sep="")

            self.reset_cmp_cache_resource(dict_get(metadata, "provider_compute_instance.id", default=r_id))
            self.reset_cmp_cache_resource(dict_get(metadata, "provider_sqlstack.id", default=r_id))

            print(self.styler.clear_line() + STOK, self.styler.cur_up(1), end="", sep="")

        except Exception as ex:
            print(self.styler.clear_line(), STERR % str(ex), self.styler.cur_up(1), end="", sep="")

    def update_volume(self, volc: int, volh: int, tab_cmp: List[dict], tab_hyp: List[dict], metadata: dict):
        STOK = f"SUCCESS filled matadata {volc} with hypervisor volume {volh}"
        STERR = f"ERROR filling matadata {volc} with hypervisor volume {volh} : %s"

        try:
            vol_meta: dict = metadata["provider_compute_instance"]["block_device_mapping"][volc]
        except Exception:
            raise AdminError(f"Nivola volume {volc} not found")
        try:
            vol_hyp: dict = metadata["hypervisor_serverserver_det"]["volumes"][volh]
        except Exception:
            raise AdminError(f"Hyoervisor volume {volh} not found")

        try:
            # Setting Provider volume size
            r_id = vol_meta["id"]
            val = int(vol_hyp["size"])
            print(self.styler.clear_line(), f"Setting Provider {r_id} volume size to {val}", end="", sep="")
            self.set_cmp_resource_config(r_id, "configs.size", str(val))
            self.reset_cmp_cache_resource(r_id)

            # Setting physical volume size
            r_id = vol_meta["resource_hypervisor_volume"]["uuid"]
            print(self.styler.clear_line(), f"Setting physical {r_id} volume size to {val}", end="", sep="")
            self.set_cmp_resource_config(r_id, "size", str(val))
            self.reset_cmp_cache_resource(r_id)

            # Setting physical volume ext_id to
            val = vol_hyp["disk_object_id"]
            print(self.styler.clear_line(), "Setting physical {r_id} volume ext_id to {val}", end="", sep="")
            self.set_cmp_resource_ext_id(r_id, val)
            self.reset_cmp_cache_resource(r_id)

            print(self.styler.clear_line(), STOK, self.styler.cur_up(1), end="", sep="")
        except Exception as ex:
            print(self.styler.clear_line(), STERR % str(ex), self.styler.cur_up(1), end="", sep="")
