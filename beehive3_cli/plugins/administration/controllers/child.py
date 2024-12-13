# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from json import dumps as jdumps
from textwrap import dedent
from typing import Iterable, List, Optional, Union
from beecell.types.type_id import is_name
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import BaseController
from beehive3_cli.core.util import CmpUtils


class AdminError(Exception):
    """
    Custom admin error.
    """

    def __init__(self, message, *args):
        # remove starting common whitespace to non-empty lines in the case of multiline strings
        dd_message = dedent(message)
        if args:
            super().__init__(dd_message, args)
        else:
            super().__init__(dd_message)


class AdminChildController(BaseController):
    """
    Admin child controller.
    """

    container_info = None
    container_type = None
    hypervisor_client = None

    class Meta:
        stacked_on = "mgmt"
        stacked_type = "nested"
        cmp = {"baseuri": "/v1.0/nrs", "subsystem": "resource"}

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.cmp_fernet: str = ""

    def ask(self, prompt: str, style: int = None, yn: bool = True, allowed: Iterable = None) -> str:
        if style is None:
            style = self.styler.YELLOW
        test = ""
        # define allowed response if any
        if yn:
            allowed = ("Y", "N")

        if allowed is None:
            test = self.styler.prompt(prompt, style)
        else:
            # make a case-insensitive check
            calow = [str(x).upper() for x in allowed]
            while test not in calow:
                test = self.styler.prompt(prompt, style).upper()
        return test

    def pre_command_run(self):
        super().pre_command_run()
        self.configure_cmp_api_client()

    def init_container(self, container: dict):
        """
        Initialize  the container info.

        container is the hypervisor which is running the database server
        self.container_info : contains container description e connection info
        self.container_type: contains hypervisor type for easy check hypervisor may be Vsphere or Openstack
        self.hypervisor_client:  is the client from Beedrones library
        """
        from beedrones.vsphere.client import VsphereManager
        from beedrones.openstack.client import OpenstackManager

        self.container_info = container
        self.container_type: str = dict_get(container, "__meta__.definition").upper()
        conn: dict = container.get("conn", {})
        # for item in conn.keys():
        #     print(f"for item {item}")
        #     self.decrypt_pwd( self.container_info["conn"][item])

        if self.container_type == "VSPHERE":
            self.hypervisor_client = VsphereManager(conn.get("vcenter"), conn.get("nsx"), key=self.cmp_fernet)
        elif self.container_type == "OPENSTACK":
            api = conn.get("api")
            self.hypervisor_client = OpenstackManager(api.get("uri"), default_region=api.get("region"))
            self.hypervisor_client.authorize(
                user=api.get("user"),
                pwd=api.get("pwd"),
                project=api.get("project"),
                domain=api.get("domain"),
                key=self.cmp_fernet,
            )
        else:
            raise AdminError(f"container {self.container_type} not implemented")

    def set_vsphere_container(self):
        """
        Set vsphere container.
        """
        self.container_type = "VSPHERE"

    def set_openstack_container(self):
        """
        Set openstack container.
        """
        self.container_type = "OPENSTACK"

    def set_container(self, conttype: str):
        """
        Set container with conttype
        """
        self.container_type = conttype

    def get_hypervisor_server(self, server_id: str):
        """
        Get server detail from hypervisor.
        """
        from beedrones.vsphere.client import VsphereManager
        from beedrones.openstack.client import OpenstackManager

        # according to implementing technologies openstack or vsphere
        if self.container_type == "VSPHERE":
            client: VsphereManager = self.hypervisor_client
            res = client.server.get(server_id)
            data = client.server.detail(res)
            return data
        if self.container_type == "OPENSTACK":
            osclient: OpenstackManager = self.hypervisor_client

            res = osclient.server.get(server_id)
            server_volumes: List[dict] = res["os-extended-volumes:volumes_attached"]
            flavor_id = dict_get(res, "flavor.id")
            res["flavor"]["name"] = osclient.flavor.get(flavor_id).get("name")

            for item in server_volumes:
                volume = osclient.volume_v3.get(item["id"])
                item.update(volume)
            return res
        raise AdminError(f"container {self.container_type} not implemented")

    def get_cmp_container(self, identifier: str) -> dict:
        """
        Get container by identifier id or uuid.
        """
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/containers/{identifier}"
        return self.cmp_get(uri).get("resourcecontainer", {})

    def get_cmp_resource(self, identifier: str) -> dict:
        """
        Get resource.
        """
        self.app.subsystem = "resource"
        uri: str = f"/v1.0/nrs/entities/{identifier}"
        result: dict = self.cmp_get(uri)
        return result.get("resource")

    def get_cmp_entity_tags(self, identifier: str) -> str:
        """
        Get entity tags.
        """
        try:
            self.app.subsystem = "resource"
            data = {"resource": identifier}
            uri = "/v1.0/nrs/tags"
            taglist = self.cmp_get(uri, data=data).get("resourcetags", [])
            tags = ""
            for tag in taglist:
                tags += tag.get("name", "") + " "

        except Exception as ex:
            tags = "error " + str(ex)
        return tags

    def set_cmp_entity_tags(self, identifier: str, *tags: List[str]):
        """
        add tag to resource
        """
        try:
            self.app.subsystem = "resource"
            data = {"resource": identifier}
            data = {"resource": {"tags": {"cmd": "add", "values": tags}}}
            uri = f"/v1.0/nrs/entities/{identifier}"
            res = self.cmp_put(uri, data=data)
        except Exception as ex:
            res = "error  " + str(ex)
        return res

    def del_cmp_entity_tags(self, identifier: str, *tags: str):
        """
        Remove tag from resource.
        """
        try:
            self.app.subsystem = "resource"
            data = {"resource": {"tags": {"cmd": "remove", "values": tags}}}
            uri = f"/v1.0/nrs/entities/{identifier}"
            res = self.cmp_put(uri, data=data)
        except Exception as ex:
            res = "error " + str(ex)
        return res

    def reset_cmp_cache_resource(self, identifier: str) -> dict:
        """
        Reset cache for resource.
        """
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{identifier}/cache"
        res = self.cmp_put(uri)
        return res

    def set_cmp_resource_active(self, identifier: str):
        """
        Force entity state at ACTIVE.
        """
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{identifier}/state"
        res = self.cmp_put(uri, data={"state": "ACTIVE"})
        return res

    def set_cmp_resource(self, identifier: str, **kwargs) -> dict:
        """
        Set reosource attribute using force in order to not trigger any management logic in the resource layer.
        """
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{identifier}"
        data = {"force": True}
        for key in ("name", "desc", "ext_id", "active"):  # ,"disable_quotas", "enable_quotas"):
            val = kwargs.get(key, None)
            if not val is None:
                data[key] = val

        result = self.cmp_put(uri, data={"resource": data})
        return result

    def get_cmp_resource_config(self, res_ident: Union[str, int]):
        """
        Get resource configuration attribute.
        """
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{res_ident}/config"
        result = self.cmp_get(uri).get("config")
        return result

    def set_cmp_resource_config(self, res_ident: Union[str, int], key: str, value):
        """
        Set resource configuration attribute.
        """
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{res_ident}/config"
        result = self.cmp_put(uri, data={"config": {"key": key, "value": str(value)}})
        return result

    def set_cmp_service_config(self, ideintifier: Union[str, int], key: str, value: str):
        """
        Set service configuration attribute.
        """
        uri = f"/v2.0/nws/serviceinsts/{ideintifier}/config"
        res = self.cmp_put(uri, data={"config": {"key": key, "value": value}})
        return res

    def get_cmp_restree(self, identifier: str) -> dict:
        """
        Get resource entity tree.
        """
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{identifier}/tree"
        tree = self.cmp_get(uri)
        return tree

    def get_cmp_linkedres(self, identifier: str) -> List[dict]:
        """
        Get linked resource.
        """
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{identifier}/linked"
        return self.cmp_get(uri).get("resources", [])

    def get_cmp_service_instance(self, oid: str, plugin: str = "DatabaseInstance") -> dict:
        """
        Get cmp service instance.
        """
        self.app.subsystem = "service"
        uri = f"/v2.0/nws/serviceinsts/{oid}"
        bu_servinst = self.cmp_get(uri).get("serviceinst")
        plugintype = bu_servinst.get("plugintype")

        if plugintype != plugin:
            raise AdminError(f" {oid} not found")
        return bu_servinst

    def set_cmp_resource_ext_id(self, res_uuid: str, ext_id: Optional[str] = None):
        """
        Set low resource ext_id (link to platform)
        """
        print(
            self.styler.clear_line() + f"Setting ext_id {ext_id} on resource {res_uuid}",
            end="",
        )
        uri = f"/v1.0/nrs/entities/{res_uuid}"
        status = self.cmp_put(uri, data={"resource": {"ext_id": ext_id}})
        print(
            self.styler.clear_line() + f"Set ext_id {ext_id} on resource {res_uuid} with status {status}",
            end="",
        )

    def set_cmp_resource_enable_quotas(self, identifier: str, value: bool = False):
        """
        Set enable quotas to resource.
        """
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{identifier}"
        if value:
            res = self.cmp_put(uri, data={"resource": {"enable_quotas": True}})
        else:
            res = self.cmp_put(uri, data={"resource": {"disable_quotas": True}})
        return res

    def get_cmp_account(self, identifier: str, div_uuid: str = None) -> dict:
        """
        Get cmp account.

        - identifier: can be in the following formats:
            1) organization.division.account
            2) division.account
            3) account
          or:
            4) it can be an id or a uuid
        - div_uuid: used only when only an account name is given (case 3)
        """
        uri = "/v1.0/nws/accounts"

        if not CmpUtils.is_valid_id(identifier) and not CmpUtils.is_valid_uuid(identifier):
            # treat it as a name or org.div.acc string
            org_div_acc = identifier.split(".")
            num_fields = len(org_div_acc)
            if num_fields == 3:
                # get division
                div = self.get_cmp_division(org_div_acc[1], org_div_acc[0])
                division_uuid = div["uuid"]
                data = f"name={org_div_acc[2]}&division_id={division_uuid}"
            elif num_fields == 2:
                data = f"name={org_div_acc[1]}&division_id={org_div_acc[0]}"
            elif num_fields == 1:
                data = f"name={org_div_acc[0]}"
                if div_uuid and CmpUtils.is_valid_uuid(div_uuid):
                    data = data + f"&division_id={div_uuid}"
            else:
                raise AdminError(f"Invalid account format: {identifier}")
            res = self.cmp_get(uri, data)
            count = res.get("count")
            if count > 1:
                raise AdminError("""Multiple accounts with the given name. Select one using its uuid instead.""")
            if count == 0:
                raise AdminError(f"The account {identifier} does not exist")
            return res.get("accounts")[0]
        uri = uri + f"/{identifier}"
        res = self.cmp_get(uri)
        return res.get("account")

    def get_cmp_division(self, identifier: str, org_uuid: str = None) -> dict:
        """
        Get cmp division.

        - identifier: can be in the following formats:
            1) organization.division
            2) division
          or:
            3) it can be an id or a uuid
        - org_id: used only when only a division name is given (case 2)
        """
        uri = "/v1.0/nws/divisions"

        if not CmpUtils.is_valid_id(identifier) and not CmpUtils.is_valid_uuid(identifier):
            # treat it as a name or org.div string
            org_div = identifier.split(".")
            num_fields = len(org_div)
            if num_fields == 2:
                data = f"name={org_div[1]}&organization_id={org_div[0]}"
            elif num_fields == 1:
                data = f"name={org_div[0]}"
                if org_uuid and CmpUtils.is_valid_uuid(org_uuid):
                    data = data + f"&organization_id={org_uuid}"
            else:
                raise AdminError(f"Invalid division format: {identifier}")
            res = self.cmp_get(uri, data)
            count = res.get("count")
            if count > 1:
                raise AdminError("""Multiple divisions with the given name. Select one using its uuid instead.""")
            if count == 0:
                raise AdminError(f"The division {identifier} does not exist")
            return res.get("divisions")[0]
        uri = uri + f"/{identifier}"
        res = self.cmp_get(uri)
        return res.get("division")

    def get_cmp_sites(self) -> dict:
        """
        Get cmp sites.
        """
        uri = "/v1.0/nrs/provider/sites"
        return self.cmp_get(uri).get("sites", {})

    def cmp_resource_import(
        self,
        container: str = "ResourceProvider01",
        resclass: str = None,
        name: str = None,
        desc: str = None,
        physical_resource_id: str = None,
        parent: str = None,
        attribute: dict = None,
        tags: List[str] = None,
    ):
        """
        Import resource.
        """
        if container is None or resclass is None or name is None:
            raise AdminError("container resclass and name are mandatory parameters")

        config = {
            "container": container,
            "name": name,
            "desc": name,
            "attribute": {},
            "resclass": resclass,
            "configs": {},
        }
        if not desc is None:
            config["desc"] = desc
        if not physical_resource_id is None:
            config["physical_id"] = physical_resource_id
        if not parent is None:
            config["parent"] = parent
        if not attribute is None:
            config["attribute"] = attribute
        if not tags is None:
            config["tags"] = ",".join(tags)

        self.app.subsystem = "resource"
        uri = "/v1.0/nrs/entities/import"
        res = self.cmp_post(uri, data={"resource": config})
        return res

    def cmp_volume_import(self, name: str, physical_resource_id: str):
        """
        Import volume.
        """
        res = self.cmp_resource_import(
            name=name,
            container="ResourceProvider01",
            physical_resource_id=physical_resource_id,
            resclass="beehive_resource.plugins.provider.entity.instance.ComputeVolume",
        )
        return res

    def add_cmp_resource_link(
        self,
        name: str = "link",
        linktype: str = "relation",
        start_resource: str = None,
        end_resource: str = None,
        attrib: dict = None,
    ):
        """
        Add resource link.
        """
        if attrib is None:
            attrib = {}

        data = {
            "type": linktype,
            "name": name,
            "attributes": attrib,
            "start_resource": start_resource,
            "end_resource": end_resource,
        }
        uri = "/v1.0/nrs/links"
        res = self.cmp_post(uri, data={"resourcelink": data})
        return res

    def add_resource(
        self,
        container: str = None,
        resclass: str = None,
        name: str = None,
        desc: str = None,
        parent: str = None,
        attribute: dict = None,
        tags: List[str] = None,
    ) -> str:
        """
        Add resource.
        """
        if container is None or resclass is None or name is None:
            raise AdminError("container resclass and name are mandatory parameters")
        data = {
            "container": container,
            "resclass": resclass,
            "name": name,
        }
        if desc is not None:
            data["desc"] = desc
        if parent is not None:
            data["parent"] = parent
        if attribute is not None:
            data["attribute"] = jdumps(attribute)
        if tags is not None:
            data["tags"] = ",".join(tags)

        self.app.subsystem = "resource"
        uri = "/v1.0/nrs/entities/"

        res = self.cmp_post(uri, data={"resource": data})
        return res["uuid"]

    def delete_resource(self, identifier: str, force: bool = False, deep: bool = False):
        """
        Delete resource.
        """
        fv = "false"
        dv = "false"
        if force:
            fv = "true"
        if deep:
            dv = "true"
        uri = f"/v1.0/nrs/entities/{identifier}?force={fv}&deep={dv}"
        self.cmp_delete(uri, confirm=False)

    def get_account(self, account_id):
        """
        Get account by id.

        :param account_id: account id
        :return: account object
        """
        check = is_name(account_id)
        uri = "/v1.0/nws/accounts"
        if check is True:
            oid = account_id.split(".")
            if len(oid) == 1:
                data = "name=" + oid[0]
                res = self.cmp_get(uri, data=data)
            elif len(oid) == 2:
                data = "name={oid[1]}&division_id={oid[0]}"
                res = self.cmp_get(uri, data=data)
            elif len(oid) == 3:
                # get division
                data = f"name={oid[1]}&organization_id={oid[0]}"
                uri2 = "/v1.0/nws/divisions"
                divs = self.cmp_get(uri2, data=data)
                # get account
                if divs.get("count") > 0:
                    data = f"name={oid[2]}&division_id={divs['divisions'][0]['uuid']}"
                    res = self.cmp_get(uri, data=data)
                else:
                    raise Exception("Account is wrong")
            else:
                raise Exception("Account is wrong")

            count = res.get("count")
            if count > 1:
                raise Exception(f"There are some account with name {account_id}. Select one using uuid")
            if count == 0:
                raise Exception(f"The account {account_id} does not exist")

            account = res.get("accounts")[0]
            self.app.log.info(f"get account by name: {account}")
            return account

        uri += "/" + account_id
        account = self.cmp_get(uri).get("account")
        self.app.log.info(f"get account by id: {account}")
        return account

    def manage_interactive_mapping(self, tab_cmp, tab_hyp, metadata):
        """
        User interaction in order to force volume mapping.
        """
        PR1_VOL_CHANGEVOLUME = "Do you want to Update cmp metadata volume with hypervisor volume? [y/n] "
        PR1_VOL_NEW_CHANGEVOLUME = "Do you want to Update another cmp metadata volume with hypervisor volume? [y/n] "
        PR2_VOL_CHOOSECMP = "Which cmp metadata volume do you want to change? [#/-1 for all] "
        PR3_VOL_CHOOSEHYP = "Which hypervisor volume do you want to map to cmp metadata volume %s? [#] "
        PR4_VOL_CHECK = "Do you want to Update cmp metadata volume %s with hypervisor volume %s? [y/n] "
        VOL_SUCCESS = "Updated cmp metadata volume %s with hypervisor volume %s. "
        PR4_VOL_CHECK_ALL = "Do you want to Update ALL cmp metadata volume with hypervisor volumes? [y/n] "
        PR4_VOL_CHECK_ERR = (
            "You can not Update ALL cmp metadata; "
            + "the number of volumes reported by hypervisor does not match the volumes in metadata! "
        )

        print()
        # change volume metadata using hypervisor data
        check = self.ask(PR1_VOL_CHANGEVOLUME, yn=True)
        while check == "Y":
            cmpindex = None
            while cmpindex is None:
                indata = self.ask(PR2_VOL_CHOOSECMP, yn=False)
                try:
                    cmpindex = int(indata)
                    if cmpindex < -1 or cmpindex > len(tab_cmp) - 1:
                        cmpindex = None
                except Exception:
                    cmpindex = None
            hypindex = None
            while hypindex is None:
                if cmpindex == -1:
                    indata = "-1"
                else:
                    indata = self.ask(PR3_VOL_CHOOSEHYP % (cmpindex), yn=False)
                try:
                    hypindex = int(indata)
                    if hypindex < -1 or cmpindex > len(tab_hyp) - 1:
                        hypindex = None
                except Exception:
                    hypindex = None
            if cmpindex != -1:
                check = self.ask(PR4_VOL_CHECK % (cmpindex, hypindex), yn=True)
            elif len(tab_hyp) == len(tab_cmp):
                check = self.ask(PR4_VOL_CHECK_ALL, yn=True)
            else:
                check = False
                print(self.styler.clear_line() + self.styler.red(PR4_VOL_CHECK_ERR), flush=True)
                return
            print()
            if check == "Y":
                print("", end="", flush=True)
                if cmpindex != -1:
                    self.update_volume(cmpindex, hypindex, metadata)
                    print(self.styler.clear_line() + self.styler.green(VOL_SUCCESS % (cmpindex, hypindex)), flush=True)
                else:
                    for index in range(len(tab_cmp)):
                        self.update_volume(index, index, metadata)
                        print(self.styler.clear_line() + self.styler.green(VOL_SUCCESS % (index, index)), flush=True)

            if cmpindex != -1:
                check = self.ask(PR1_VOL_NEW_CHANGEVOLUME, yn=True)
            else:
                check = False

        def update_volume(self, volc: int, volh: int, metadata: dict):
            """
            Update volume.
            """
            STOK = f"SUCCESS filled metadata {volc} with hypervisor volume {volh}"
            STERR = f"ERROR filling metadata {volc} with hypervisor volume {volh} : %s"

            try:
                vol_meta: dict = metadata["provider_compute_instance"]["block_device_mapping"][volc]
            except Exception as exc:
                raise AdminError(f"Nivola volume {volc} not found") from exc
            try:
                vol_hyp: dict = metadata["hypervisor_serverserver_det"]["volumes"][volh]
            except Exception as exc:
                raise AdminError(f"Hypervisor volume {volh} not found") from exc

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
            except Exception as e:
                print(self.styler.clear_line(), STERR % str(e), self.styler.cur_up(1), end="", sep="")

    def remove_volume_metadata(self, volc: int, metadata: dict):
        """
        Remove volume metadata.
        """
        STOK = f"SUCCESS removing volume {volc}"
        STERR = f"ERROR removing volume {volc} : %s"
        try:
            vol_meta: dict = metadata["provider_compute_instance"]["block_device_mapping"][volc]
        except Exception as exc:
            raise AdminError(f"Nivola volume {volc} not found") from exc
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

            print(self.styler.clear_line() + STOK, self.styler.cur_up(1), end="", sep="")

            return r_id
        except Exception as exc:
            print(self.styler.clear_line(), STERR % str(exc), self.styler.cur_up(1), end="", sep="")
            return None

    def update_volume(self, volc: int, volh: int, metadata: dict):
        """
        Update volume.
        """
        STOK = f"SUCCESS filled metadata {volc} with hypervisor volume {volh}"
        STERR = f"ERROR filling metadata {volc} with hypervisor volume {volh} : %s"

        try:
            vol_meta: dict = metadata["provider_compute_instance"]["block_device_mapping"][volc]
        except Exception as exc:
            raise AdminError(f"Nivola volume {volc} not found") from exc
        try:
            vol_hyp: dict = metadata["hypervisor_serverserver_det"]["volumes"][volh]
        except Exception as exc:
            raise AdminError(f"Hypervisor volume {volh} not found") from exc

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
        except Exception as e:
            print(self.styler.clear_line(), STERR % str(e), self.styler.cur_up(1), end="", sep="")

    def import_volume(self, volh: int, metadata: dict):
        """
        Import volume.
        """
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
            hypervisor = dict_get(metadata, "provider_compute_instance.attributes.type")
            vol_hyp: dict = {}
            if hypervisor == "vsphere":
                vol_hyp = metadata["hypervisor_serverserver_det"]["volumes"][volh]
            elif hypervisor == "openstack":
                vol_hyp = metadata["hypervisor_serverserver_det"]["os-extended-volumes:volumes_attached"][volh]
        except Exception as exc:
            raise AdminError(f"Hypervisor volume {volh} not found") from exc
        try:
            if container == "openstack":
                vol_hyp["unit_number"] = volh
            self._import_volume_resource(container_name, vol_hyp, physical_vol_template, metadata, container)
            print(self.styler.clear_line() + STOK + self.styler.cur_up(1), end="", sep="")
        except Exception as exc:
            print(self.styler.clear_line(), STERR % str(exc), self.styler.cur_up(1), end="", sep="")

    def _import_volume_resource(self, container_name, vol_hyp, physical_vol_template, metadata, container):
        print(self.styler.clear_line(), f"vSphere {container_name}", sep="", end="")
        # import resource describing physical volume
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
        resclass = None
        desc = ""
        physical_resource_id = None
        if container == "vsphere":
            resclass = "beehive_resource.plugins.vsphere.entity.vs_volume.VsphereVolume"
            desc = vol_hyp.get("id", "imported_volume")
            physical_resource_id = vol_hyp.get("disk_object_id", None)
        if container == "openstack":
            resclass = "beehive_resource.plugins.openstack.entity.ops_volume.OpenstackVolume"
            desc = vol_hyp.get("description")
            physical_resource_id = vol_hyp.get("id")

        parent = str(physical_vol_template["parent"])
        print(self.styler.clear_line(), "Adding physical volume metadata. ", sep="", end="")
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
        print(self.styler.clear_line(), "Ensure physical volume metadata end status. ", sep="", end="")
        volph_uuid = volph["uuid"]
        serph_uuid = dict_get(metadata, "resource_hypervisor_server.uuid")
        self.set_cmp_resource(volph_uuid, ext_id=physical_resource_id)
        self.set_cmp_resource_active(volph_uuid)
        print(self.styler.clear_line(), "Linking physical Server metadata with volume metadata. ", sep="", end="")
        # add link from resource physical server
        self.add_cmp_resource_link(
            name=f"{serph_uuid}-{volph_uuid}volume-link",
            linktype="volume",
            attrib={"boot": False},
            start_resource=serph_uuid,
            end_resource=volph_uuid,
        )
        # add  provider volume
        print(self.styler.clear_line(), "Adding provider volume metadata. ", sep="", end="")
        volpr = self.cmp_volume_import(physical_resource_id=volph["uuid"], name=name)
        # add link from provider compute instance
        print(self.styler.clear_line(), "Linking provider server with provider volume metadata.", sep="", end="")
        volpr_uuid = volpr["uuid"]
        unit_number = vol_hyp["unit_number"]
        serpr_uuid = dict_get(metadata, "provider_compute_instance.uuid")
        self.add_cmp_resource_link(
            name=f"{serpr_uuid}-{volpr_uuid}volume-link",
            linktype=f"volume.{unit_number}",
            start_resource=serpr_uuid,
            end_resource=volpr_uuid,
        )
        self.set_cmp_resource_enable_quotas(volpr_uuid, value=True)
        # clear cache
        print(self.styler.clear_line(), "Clear provider server cache.", sep="", end="")
        self.reset_cmp_cache_resource(serpr_uuid)
        self.reset_cmp_cache_resource(dict_get(metadata, "provider_compute_instance.id", default=serpr_uuid))
        return serpr_uuid

    def manage_interactive_import(self, metadata):
        """
        Manage interactive import.
        """
        PR1_LOAD_CHANGE = "Do you want to Add an existing hypervisor volume on cmp metadata volumes? [y/n] "
        PR2_LOAD_CHOOSE = "Which hypervisor volume do you want to Add? [#] "
        PR3_LOAD_CHECK = "Are you sure you want to Add hypervisor volume # %s in cmp metadata volumes? [y/n] "
        LOAD_SUCCESS = "Added hypervisor volume %s in cmp metadata volumes %s. "
        # change t backup tag interaction
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
                self.import_volume(volumenumber, metadata)
                msg = self.styler.clear_line() + self.styler.green(LOAD_SUCCESS % (volumenumber, volumenumber))
                print(msg, flush=True)

    def manage_interactive_delete(self, metadata: dict):
        """
        Manage interactive delete.
        """
        PR1_REMOVE_PROMPT = "Do you want to Delete a non existing volume described by cmp metadata? [y/n] "
        PR2_REMOVE_CHOOSE = "Which cmp metadata volume do you want to Delete? [#] "
        PR3_REMOVE_CHECK = "Are you sure you want to Delete metadata volume # %s? [y/n] "
        REMOVE_SUCCESS = "Deleted cmp metadata volume %s."
        # change t backup tag interaction
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
                self.remove_volume_metadata(volumenumber, metadata)
                print(self.styler.clear_line() + self.styler.green(REMOVE_SUCCESS % volumenumber), flush=True)

    def manage_interactive_tags(self, tab_cmp):
        """
        Manage tags, including the backup one.
        """
        PR1_TAG_CHANGE = "Do you want to add/remove backup a tag from volume? [y/n] "
        PR2_TAG_CHOOSECMP = "Which cmp metadata volume's tag do you want to change? [#] "
        PR3_TAG_CHECK = "Are you sure you want to %s the '%s' tag from cmp metadata volume %s? [y/n] "
        TAG_SUCCESS = "Tagged cmp metadata volume %s."
        TAG = "nws$volume_bck"
        # change tag interaction
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
                print(self.styler.clear_line() + self.styler.green(TAG_SUCCESS % cmpindex), flush=True)

            check = self.ask(PR1_TAG_CHANGE, yn=True)

    def suggestion_print(self, action, text):
        msg = self.styler.red("Please " + self.styler.underline(action)) + self.styler.red(text)
        print(msg)

    def print_warning(self):
        print("\n" + self.styler.red(self.styler.format("Warning! ", self.styler.BLINK)))

    def print_success(self):
        print("\n" + self.styler.green(self.styler.format("Success! ", self.styler.BLINK)))

    def print_info(self):
        print("\n" + self.styler.red(self.styler.format("Info! ", self.styler.BLINK)))

    def print_looking_for(self, msg):
        sentence = self.styler.green(self.styler.clear_line() + "I'm looking for " + msg)
        print(sentence, end="...", flush=True)

    def make_suggestions(self, tab_cmp, tab_hyp):
        ext_cmp = {i: a["ext_id"] for i, a in enumerate(tab_cmp)}
        hyp_cmp = {i: a["ext_id"] for i, a in enumerate(tab_hyp)}
        cmp_vol_index = set(ext_cmp.keys())
        hyp_vol_index = set(hyp_cmp.keys())
        if len(tab_cmp) != len(tab_hyp):
            msg = "The number of volumes reported by hypervisor does not match the volumes in metadata!"
            print("\n" + self.styler.format("Warning! ", self.styler.BLINK) + self.styler.red(msg))
            missing_cmp_vol = hyp_vol_index - cmp_vol_index
            for a in missing_cmp_vol:
                self.suggestion_print(
                    "A", f"dd the cmp volume metadata # {a} this exists in hypervisor but not in cmp."
                )
            cmp_vol_no_hyp = cmp_vol_index - hyp_vol_index
            for a in cmp_vol_no_hyp:
                self.suggestion_print("D", f"elete the cmp volume metadata # {a} this does not exist in hypervisor.")
        else:
            same_keys = cmp_vol_index == hyp_vol_index
            if same_keys:
                same_values = [a for a in ext_cmp.values()] == [a for a in hyp_cmp.values()]
            else:
                self.print_warning()
                self.suggestion_print("U", "pdate cmp metadata volumes, detected some problems on indices.")
            if same_keys and not same_values:
                self.print_warning()
                self.suggestion_print(
                    "U", "pdate cmp metadata volumes, some ext_id are not aligned to hypervisor data volumes."
                )
            else:
                self.print_success()
                msg = "Cmp metadata volumes match with hypervisor data volumes."
                print(self.styler.green(msg))
                return True
        return False
