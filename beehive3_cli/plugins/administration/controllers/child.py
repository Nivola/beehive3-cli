# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


from json import dumps as jdumps
from textwrap import dedent
from typing import Iterable, List, Optional, Union, Dict
from urllib.parse import urlencode
from beecell.types.type_id import is_name
from beecell.types.type_dict import dict_get
from beehive3_cli.translate import _
from beehive3_cli.core.controller import BaseController
from beehive3_cli.core.util import CmpUtils

VOL_SUCCESS = _("Updated cmp metadata volume {meta_vol_num} with hypervisor volume {hyp_vol_num}. ")

OPENSTACK_ALIGN_VOL_NOT_SUPPORTED = _("""\
Openstack update is not implemented, if some ext_id are wrong please open an issue this should never happen!\
""")

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
        """
        Ask which option desire the user.
        """
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

    def init_container(self, container: Dict):
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
            server_volumes: List[Dict] = res["os-extended-volumes:volumes_attached"]
            flavor_id = dict_get(res, "flavor.id")
            res["flavor"]["name"] = osclient.flavor.get(flavor_id).get("name")

            for item in server_volumes:
                volume = osclient.volume_v3.get(item["id"])
                item.update(volume)
            return res
        raise AdminError(f"container {self.container_type} not implemented")

    def get_cmp_container(self, identifier: str) -> Dict:
        """
        Get container by identifier id or uuid.
        """
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/containers/{identifier}"
        return self.cmp_get(uri).get("resourcecontainer", {})

    def get_res_provider_compute_instance(self, identifier: str) -> Dict:
        """
        Get resource.
        """
        if identifier is None:
            return None
        self.app.subsystem = "resource"
        uri: str = f"/v1.0/nrs/provider/instances/{identifier}"
        result: dict = self.cmp_get(uri)
        return result.get("instance")

    def get_cmp_resource(self, identifier: str) -> Dict:
        """
        Get resource.
        """
        if identifier is None:
            return None
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

    def reset_cmp_cache_resource(self, identifier: str) -> Dict:
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

    def set_cmp_resource(self, identifier: str, **kwargs) -> Dict:
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

    def get_cmp_restree(self, identifier: str) -> Dict:
        """
        Get resource entity tree.
        """
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{identifier}/tree"
        tree = self.cmp_get(uri)
        return tree

    def get_cmp_linkedres(self, identifier: str, **kvargs) -> List[dict]:
        """
        Get linked resource.
        """
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{identifier}/linked"
        data = ""
        link_type = kvargs.get("link_type")
        if link_type:
            data = {"link_type": link_type}
        return self.cmp_get(uri, data=data).get("resources", [])

    def get_cmp_service_instance(self, oid: str, plugin: str = "DatabaseInstance") -> Dict:
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

    def find_cmp_service_instance(self,**kwargs) -> Dict:
        if kwargs.get("oid"):
            plugin = kwargs.get("plugintype", "DatabaseInstance") # same default as other function
            return self.get_cmp_service_instance(kwargs.get("oid"), plugin=plugin)
        filtered_params = {k: v for k, v in kwargs.items() if v is not None}
        query_string = urlencode(filtered_params)
        self.app.subsystem = "service"
        uri = "/v2.0/nws/serviceinsts"
        res = self.cmp_get(uri,data=query_string).get("serviceinsts")
        if not res:
            raise AdminError(_("no service instance found"))
        if len(res) > 1:
            raise AdminError(_("found more than one service instance"))
        return res[0]

    def get_cmp_service_definition(self, oid: str) -> Dict:
        """
        get cmp service definition
        """
        self.app.subsystem = "service"
        uri = f"/v1.0/nws/servicedefs/{oid}"
        return self.cmp_get(uri).get("servicedef")

    def set_cmp_resource_ext_id(self, res_uuid: str, ext_id: Optional[str] = None):
        """
        Set low resource ext_id (link to platform)
        """
        msg =  _("Setting ext_id {ext_id} on resource {res_uuid}").format(
            ext_id=ext_id,
            res_uuid=res_uuid,
        )

        print(self.styler.clear_line() + msg, end="",)
        uri = f"/v1.0/nrs/entities/{res_uuid}"
        status = self.cmp_put(uri, data={"resource": {"ext_id": ext_id}})
        formatted_message = _("Set ext_id {ext_id} on resource {res_uuid} with status {status}").format(
            ext_id=ext_id,
            res_uuid=res_uuid,
            status=status
        )
        print(self.styler.clear_line() + formatted_message, end="")

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

    def get_cmp_account(self, identifier: str, div_uuid: str = None) -> Dict:
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
                raise AdminError(_("Multiple accounts with the given name. Select one using its uuid instead."))
            if count == 0:
                raise AdminError(_("The account {identifier} does not exist.").format(identifier=identifier))
            return res.get("accounts")[0]
        uri = uri + f"/{identifier}"
        res = self.cmp_get(uri)
        return res.get("account")

    def get_cmp_division(self, identifier: str, org_uuid: str = None) -> Dict:
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
                raise AdminError(_("Multiple divisions with the given name. Select one using its uuid instead."))
            if count == 0:
                raise AdminError(_("The division {identifier} does not exist.").format(identifier=identifier))
            return res.get("divisions")[0]
        uri = uri + f"/{identifier}"
        res = self.cmp_get(uri)
        return res.get("division")

    def get_cmp_sites(self) -> Dict:
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
            raise AdminError(_("Container resclass and name are mandatory parameters."))

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
        attribute: Dict = None,
        tags: List[str] = None,
    ) -> str:
        """
        Add resource.
        """
        if container is None or resclass is None or name is None:
            raise AdminError(_("Container resclass and name are mandatory parameters."))
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
                    raise Exception(_("Account is wrong"))
            else:
                raise Exception(_("Account is wrong"))

            count = res.get("count")
            if count > 1:
                error_message = _("There are some account with name {account_id}. Select one using uuid")
                raise Exception(error_message.format(account_id=account_id))
            if count == 0:
                error_message = _("The account {account_id} does not exist.").format(account_id=account_id)
                raise Exception(error_message)

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
        yn = " [y/n] "
        pr1_vol_changevolume = _("Do you want to Update cmp metadata volume with hypervisor volume?") + yn
        pr1_vol_new_changevolume = _("Do you want to Update another cmp metadata volume with hypervisor volume?") + yn
        pr2_vol_choosecmp = _("Which cmp metadata volume do you want to change?") + " [#/-1 " + _("for all") + "] "
        pr3_vol_choosehyp = _(
            "Which hypervisor volume do you want to map to cmp metadata volume {meta_vol_num}?"
        ) + " [#] "
        pr4_vol_check = _(
            "Do you want to Update cmp metadata volume {meta_vol_num} with hypervisor volume {hyp_vol_num}?"
        ) + yn
        pr4_vol_check_all = _("Do you want to Update ALL cmp metadata volume with hypervisor volumes?") + yn
        pr4_vol_check_err = _(
            "You can not Update ALL cmp metadata; the number of volumes reported by hypervisor does not match the volumes in metadata! "
        )
        print()
        hypervisor = dict_get(metadata, "provider_compute_instance.attributes.type")
        if hypervisor == "openstack":
            print(self.styler.red(OPENSTACK_ALIGN_VOL_NOT_SUPPORTED))
            return

        # change volume metadata using hypervisor data
        check = self.ask(pr1_vol_changevolume, yn=True)
        while check == "Y":
            cmpindex = None
            while cmpindex is None:
                indata = self.ask(pr2_vol_choosecmp, yn=False)
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
                    indata = self.ask(pr3_vol_choosehyp.format(meta_vol_num=cmpindex), yn=False)
                try:
                    hypindex = int(indata)
                    if hypindex < -1 or cmpindex > len(tab_hyp) - 1:
                        hypindex = None
                except Exception:
                    hypindex = None
            if cmpindex != -1:
                check = self.ask(pr4_vol_check.format(meta_vol_num=hypindex, hyp_vol_num=hypindex), yn=True)
            elif len(tab_hyp) == len(tab_cmp):
                check = self.ask(pr4_vol_check_all, yn=True)
            else:
                check = False
                print(self.styler.clear_line() + self.styler.red(pr4_vol_check_err), flush=True)
                return
            print()
            if check == "Y":
                print("", end="", flush=True)
                if cmpindex != -1:
                    self.update_volume(cmpindex, hypindex, metadata)
                    msg = VOL_SUCCESS.format(meta_vol_num=cmpindex, hyp_vol_num=hypindex)
                    print(self.styler.clear_line() + self.styler.green(msg), flush=True)
                else:
                    self.update_volumes(metadata)

            if cmpindex != -1:
                check = self.ask(pr1_vol_new_changevolume, yn=True)
            else:
                check = False
        compute_instance = metadata['provider_compute_instance']['uuid']
        self.reset_cmp_cache_resource(compute_instance)

    def remove_volume_metadata(self, volc: int, metadata: Dict):
        """
        Remove volume metadata.
        """
        stok = _("SUCCESS removing volume {volc}").format(volc=volc)
        try:
            vol_meta: Dict = metadata["provider_compute_instance"]["block_device_mapping"][volc]
        except Exception as exc:
            raise AdminError(f"Nivola volume {volc} not found") from exc
        try:
            r_id = vol_meta["resource_hypervisor_volume"]["uuid"]
            msg = _("Setting physical {r_id} volume size to null").format(r_id=r_id)
            print(self.styler.clear_line(), msg, end="", sep="")
            self.set_cmp_resource_ext_id(r_id, "")
            self.set_cmp_resource_ext_id(r_id, None)

            r_id = vol_meta["id"]
            msg = _("deleting Provider Volume {r_id} volume").format(r_id=r_id)
            print(self.styler.clear_line(), msg, end="", sep="")
            self.delete_resource(r_id, force=True, deep=False)

            msg = _("deleted Provider Volume {r_id} volume").format(r_id=r_id)
            print(self.styler.clear_line(), msg, end="", sep="")

            self.reset_cmp_cache_resource(dict_get(metadata, "provider_compute_instance.id", default=r_id))

            print(self.styler.clear_line() + stok, self.styler.cur_up(1), end="", sep="")

            return r_id
        except Exception as exc:
            sterr = _("ERROR removing volume {volc} : {stacktrace}").format(volc=volc, stacktrace=f"{exc}")
            print(self.styler.clear_line(), sterr, self.styler.cur_up(1), end="", sep="")
            return None

    def update_volume(self, volc: int, volh: int, metadata: Dict):
        """
        Update volume.
        """
        stok = _("SUCCESS filled metadata {volc} with hypervisor volume {volh}").format(volc=volc, volh=volh)

        try:
            vol_meta: Dict = metadata["provider_compute_instance"]["block_device_mapping"][volc]
        except Exception as exc:
            raise AdminError(f"Nivola volume {volc} not found") from exc
        try:
            vol_hyp: Dict = metadata["hypervisor_serverserver_det"]["volumes"][volh]
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
            msg = _("Setting physical {r_id} volume size to {val}").format(r_id=r_id, val=val)
            print(self.styler.clear_line(), msg, end="", sep="")
            self.set_cmp_resource_config(r_id, "size", str(val))
            self.reset_cmp_cache_resource(r_id)

            # Setting physical volume ext_id to
            val = vol_hyp["disk_object_id"]
            msg = _("Setting physical {r_id} volume ext_id to {val}").format(r_id=r_id, val=val)
            print(self.styler.clear_line(), msg, end="", sep="")
            self.set_cmp_resource_ext_id(r_id, val)
            self.reset_cmp_cache_resource(r_id)

            print(self.styler.clear_line(), stok, self.styler.cur_up(1), end="", sep="")
        except Exception as e:
            sterr = _(
                "ERROR filling metadata {volc} with hypervisor volume {volh} : {stack_det}"
            ).format(volc=volc, volh=volh, stack_det=f"{e}")
            print(self.styler.clear_line(), sterr, self.styler.cur_up(1), end="", sep="")

    def update_volumes(self, metadata):
        """
        Update volumes.
        """
        hypervisor = dict_get(metadata, "provider_compute_instance.attributes.type")
        if hypervisor == "openstack":
            print(self.styler.red(OPENSTACK_ALIGN_VOL_NOT_SUPPORTED))
            return
        cmp_vols: list = dict_get(metadata, "provider_compute_instance.block_device_mapping")
        hyp_vols: list = self.get_hypervisor_volumes(metadata)
        if len(hyp_vols) != len(cmp_vols):
            raise AdminError(_("Hypervisor and Cmp has not the same numer of volumes"))

        for index in range(len(cmp_vols)):
            self.update_volume(index, index, metadata)
            msg = VOL_SUCCESS.format(meta_vol_num=index, hyp_vol_num=index)
            print(self.styler.clear_line() + self.styler.green(msg), flush=True)

    def get_hypervisor_volumes(self, metadata: Dict):
        """
        Get hypervisor volumes.
        """
        hypervisor = dict_get(metadata, "provider_compute_instance.attributes.type")
        if hypervisor == "vsphere":
            vol_hyp = metadata["hypervisor_serverserver_det"]["volumes"]
        elif hypervisor == "openstack":
            vol_hyp = metadata["hypervisor_serverserver_det"]["os-extended-volumes:volumes_attached"]
        else:
            raise Exception(_("unsupported hypervisor: {hypervisor}").format(hypervisor=hypervisor))
        return vol_hyp

    def import_volume(self, volh: int, metadata: Dict):
        """
        Import volume.
        """

        print("\n", self.styler.clear_line(), _("Gathering info"), sep="", end="")
        container: str = dict_get(metadata, "provider_compute_instance.attributes.type", default="").lower()
        container_name: str = dict_get(metadata, "hypervisor_container.name")
        template_id = dict_get(
            metadata, "provider_compute_instance.block_device_mapping.0.resource_hypervisor_volume.uuid"
        )
        print(self.styler.clear_line(), _("Using first volume as template"), sep="", end="")
        physical_vol_template: dict = self.get_cmp_resource(template_id)
        if container_name is None:
            raise AdminError(_("Container Name not found"))
        try:
            vol_hyp = self.get_hypervisor_volumes(metadata)[volh]
        except Exception as exc:
            raise AdminError(_("Hypervisor volume {volh} not found").format(volh=volh)) from exc
        try:
            if container == "openstack":
                vol_hyp["unit_number"] = volh
            self._import_volume_resource(container_name, vol_hyp, physical_vol_template, metadata, container)
            stok = _("SUCCESS importing volume {volh}").format(volh=volh)
            print(self.styler.clear_line() + stok + self.styler.cur_up(1), end="", sep="")
        except Exception as exc:
            sterr = _("ERROR importing volume {volh} : {stack_det}").format(volh=volh, stack_det=f"{exc}")
            print(self.styler.clear_line(), sterr, self.styler.cur_up(1), end="", sep="")

    def _import_volume_resource(
        self, container_name, vol_hyp, physical_vol_template, metadata, container, has_quotas=True
    ):
        print(self.styler.clear_line(), _("vSphere {container_name}"), sep="", end="")
        # import resource describing physical volume
        volume_type = dict_get(physical_vol_template, "attributes.volume_type")
        attribute = {
            "size": int(vol_hyp["size"]),
            "volume_type": volume_type,
            "source_volume": None,
            "source_image": None,
            "bootable": False,
            "encrypted": False,
            "has_quotas": has_quotas,
            "status": "in-use",
        }
        provider_vm_name = dict_get(metadata, "service_servinst.name")
        name = provider_vm_name + "-" + vol_hyp.get("name", "imported_volume")
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
        # parent = str(1611515)
        print(self.styler.clear_line(), _("Adding physical volume metadata. "), sep="", end="")
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
        print(self.styler.clear_line(), _("Ensure physical volume metadata end status. "), sep="", end="")
        volph_uuid = volph["uuid"]
        serph_uuid = dict_get(metadata, "resource_hypervisor_server.uuid")
        self.set_cmp_resource(volph_uuid, ext_id=physical_resource_id)
        self.set_cmp_resource_active(volph_uuid)
        print(self.styler.clear_line(), _("Linking physical Server metadata with volume metadata. "), sep="", end="")
        # add link from resource physical server
        self.add_cmp_resource_link(
            name=f"{serph_uuid}-{volph_uuid}-volume-link",
            linktype="volume",
            attrib={"boot": False},
            start_resource=serph_uuid,
            end_resource=volph_uuid,
        )
        # add  provider volume
        unit_number = vol_hyp["unit_number"]
        print(self.styler.clear_line(), _("Adding provider volume metadata. "), sep="", end="")
        volpr = self.cmp_volume_import(
            physical_resource_id=volph["uuid"], name=f"{provider_vm_name}-volume-{unit_number}"
        )
        # add link from provider compute instance
        print(self.styler.clear_line(), _("Linking provider server with provider volume metadata."), sep="", end="")
        volpr_uuid = volpr["uuid"]
        serpr_uuid = dict_get(metadata, "provider_compute_instance.uuid")
        self.add_cmp_resource_link(
            name=f"{serpr_uuid}-{volpr_uuid}-volume-link",
            linktype=f"volume.{unit_number}",
            start_resource=serpr_uuid,
            end_resource=volpr_uuid,
        )
        self.set_cmp_resource_enable_quotas(volpr_uuid, value=has_quotas)
        # clear cache
        print(self.styler.clear_line(), _("Clear provider server cache."), sep="", end="")
        self.reset_cmp_cache_resource(serpr_uuid)
        self.reset_cmp_cache_resource(dict_get(metadata, "provider_compute_instance.id", default=serpr_uuid))
        return serpr_uuid

    def manage_interactive_import(self, metadata):
        """
        Manage interactive import.
        """
        yn = " [y/n] "
        pr1_load_change = _("Do you want to Add an existing hypervisor volume on cmp metadata volumes?") + yn
        pr2_load_choose = _("Which hypervisor volume do you want to Add?") + " [#] "
        pr3_load_check = _(
            "Are you sure you want to Add hypervisor volume # {hyp_vol_num} in cmp metadata volumes?"
        ) + yn
        load_success = _("Added hypervisor volume {hyp_vol_num} in cmp metadata volumes {cmp_vol_num}. ")
        # change t backup tag interaction
        print()
        check = self.ask(pr1_load_change, yn=True)
        if check == "Y":
            valid = False
            while not valid:
                indata = self.ask(pr2_load_choose, yn=False)
                try:
                    volumenumbers = [int(i) for i in indata.split(",")]
                    valid = True
                except Exception:
                    valid = False

            check = self.ask(pr3_load_check.format(hyp_vol_num=indata), yn=True)
            print()
            if check == "Y":
                for volumenumber in volumenumbers:
                    self.import_volume(volumenumber, metadata)
                    msg = load_success.format(hyp_vol_num=volumenumber, cmp_vol_num=volumenumber)
                    msg = self.styler.clear_line() + self.styler.green(msg)
                    print(msg, flush=True)

    def manage_interactive_delete(self, metadata: Dict):
        """
        Manage interactive delete.
        """
        yn = " [y/n] "
        pr1_remove_prompt = _("Do you want to Delete a non existing volume described by cmp metadata?") + yn
        pr2_remove_choose = _("Which cmp metadata volume do you want to Delete?") + " [#] "
        pr3_remove_check = _("Are you sure you want to Delete metadata volume # {cmp_vol_num}?") + yn
        remove_success = _("Deleted cmp metadata volume {cmp_vol_num}.")
        # change t backup tag interaction
        print()
        check = self.ask(pr1_remove_prompt, yn=True)
        if check == "Y":
            volumenumber = -1
            while volumenumber == -1:
                indata = self.ask(pr2_remove_choose, yn=False)
                try:
                    volumenumber = int(indata)
                    if volumenumber < 0:
                        volumenumber = -1
                except Exception:
                    volumenumber = -1
            check = self.ask(pr3_remove_check.format(cmp_vol_num=volumenumber), yn=True)
            print()
            if check == "Y":
                self.remove_volume_metadata(volumenumber, metadata)
                msg = self.styler.green(remove_success.format(cmp_vol_num=volumenumber))
                print(self.styler.clear_line() + msg, flush=True)

    def toggle_backup_tags(self, tab_cmp):
        """
        Toggle backup tags on volume.
        """
        yn = " [y/n] "
        pr1_tag_change = _("Do you want to add/remove backup a tag from volume?") + yn
        pr2_tag_choosecmp = _("Which cmp metadata volume's tag do you want to change?") + " [#] "
        pr3_tag_check = _(
            "Are you sure you want to {action} the {tag_name} tag from cmp metadata volume {cmp_vol_num}?"
        ) + yn
        tag_success = _("Tagged cmp metadata volume {cmp_vol_num}.")
        tag = "nws$volume_bck"
        # change tag interaction
        print()
        check = self.ask(pr1_tag_change, yn=True)
        while check == "Y":
            cmpindex = -1
            action = ""
            while cmpindex == -1:
                indata = self.ask(pr2_tag_choosecmp, yn=False)
                try:
                    cmpindex = int(indata)
                    if cmpindex < 0 or cmpindex > len(tab_cmp) - 1:
                        cmpindex = -1
                    else:
                        if tag in tab_cmp[cmpindex]["tags"]:
                            action = _("delete")
                        else:
                            action = _("add")
                except Exception:
                    cmpindex = -1
            msg = pr3_tag_check.format(action=action, tag_name=tag, cmp_vol_num=cmpindex)
            check = self.ask(msg, yn=True)
            print()
            if check == "Y":
                print("", end="", flush=True)
                r_id = tab_cmp[cmpindex]["id"]
                if action == "delete":
                    self.del_cmp_entity_tags(r_id, tag)
                else:
                    self.set_cmp_entity_tags(r_id, tag)
                msg = tag_success.format(cmp_vol_num=cmpindex)
                print(self.styler.clear_line() + self.styler.green(msg), flush=True)

            check = self.ask(pr1_tag_change, yn=True)

    def data_bulk_tags(self, tab_cmp):
        """
        Bulk tag volumes as backup.
        """
        tag = "nws$volume_bck"
        input_prompt = _("Please enter the indexes (#) of the CMP data volumes, separated by commas (e.g., 1,2,5).")
        indata = self.ask(input_prompt, yn=False)
        cmpindexes = []
        try:
            cmpindexes = [int(n) for n in indata.split(",")]
        except:
            msg = _("Invalid input {indata}").format(indata=indata)
            print(self.styler.clear_line() + self.styler.red(msg), flush=True)
        for cmpindex in cmpindexes:
            if cmpindex < 0 or cmpindex > len(tab_cmp) - 1:
                msg = _("Invalid index {cmpindex}").format(cmpindex=cmpindex)
                print(self.styler.clear_line() + self.styler.red(msg), flush=True)
        for item in tab_cmp:
            index = item["#"]
            if index == 0:
                if 0 in cmpindexes:
                    msg = _("Skip boot index {index}").format(index=index)
                    print(self.styler.clear_line() + self.styler.red(msg), flush=True)
                continue
            r_id = item["id"]
            if index in cmpindexes:
                # This is a data volume, I remove the backup tag if it has one.
                if tag in item["tags"]:
                    self.del_cmp_entity_tags(r_id, tag)
            else:
                # This is a backup volume, I add the backup tag if it doesn't have one.
                if tag not in item["tags"]:
                    self.set_cmp_entity_tags(r_id, tag)

    def manage_interactive_tags(self, tab_cmp):
        """
        Manage tags, including the backup one.
        """
        prompt = (
            "\n" + _("You can press: ") + "\n"
            + self.styler.underline("D") + "; "
            + _("to tag Data volumes in bulk") + ",\n"
            + self.styler.underline("B") + "; "
            + _("to toggle the Backup tag on a specific volume") + ",\n"
            + self.styler.underline("H") + "; "
            + _("to return to Home") + ".\n"
        )
        print(prompt)

        allowed = ("D", "B", "H")
        prompt_choose = f"Data, Backup, or Home [{'/'.join(allowed)}]? "

        check = self.ask(prompt_choose, yn=False, allowed=allowed)
        if check == "B":
            self.toggle_backup_tags(tab_cmp)
        if check == "D":
            self.data_bulk_tags(tab_cmp)
        if check == "H":
            return

    def suggestion_print(self, action, text):
        """
        Print menu suggestion
        """
        red = self.styler.red
        msg = red(_("Press")) + " " + red(self.styler.underline(action)) + red("; " +text)
        print(msg)

    def print_warning(self):
        """
        Print warning.
        """
        print("\n" + self.styler.red(self.styler.format(_("Warning! "), self.styler.BLINK)))

    def print_success(self):
        """
        Print success.
        """
        print("\n" + self.styler.green(self.styler.format(_("Success! "), self.styler.BLINK)))

    def print_info(self):
        """
        Print info.
        """
        print("\n" + self.styler.red(self.styler.format(_("Info! "), self.styler.BLINK)))

    def print_looking_for(self, msg):
        """
        Print looking for msg.
        """
        sentence = self.styler.green(self.styler.clear_line() + _("I'm looking for ") + msg)
        print(sentence, end="...", flush=True)

    def make_suggestions(self, tab_cmp, tab_hyp):
        """
        Make suggestions to solve discrepancies between the cmp metadata and the vm information on hypervisor.
        """
        ext_cmp = {a["ext_id"]: a["size"] for a in tab_cmp}
        hyp_cmp = {a["ext_id"]: a["size"] for a in tab_hyp}
        cmp_vol_index = set(a for a, v in enumerate(ext_cmp))
        hyp_vol_index = set(a for a, v in enumerate(hyp_cmp))
        if len(tab_cmp) != len(tab_hyp):
            warn = self.styler.format("\n" + _("Warning! ") + "\n", self.styler.BLINK)
            msg = _("The number of volumes reported by hypervisor does not match the volumes in metadata!")
            print(self.styler.red(warn) + self.styler.red(msg))
            missing_cmp_vol = hyp_vol_index - cmp_vol_index
            for a in missing_cmp_vol:
                msg = _("Add the cmp volume metadata # {a} this exists in hypervisor but not in cmp.").format(a=a)
                self.suggestion_print("A", msg)
            cmp_vol_no_hyp = cmp_vol_index - hyp_vol_index
            for a in cmp_vol_no_hyp:
                msg = _("Delete the cmp volume metadata # {a} this does not exist in hypervisor.").format(a=a)
                self.suggestion_print("D", msg)
        else:
            same_keys = cmp_vol_index == hyp_vol_index
            same_values = None
            if same_keys:
                same_values = all(ext_cmp.get(k) == hyp_cmp.get(k) for k in hyp_cmp)
            else:
                self.print_warning()
                self.suggestion_print("U", _("to Update cmp metadata volumes, detected some problems on indices."))
            if same_keys and not same_values:
                self.print_warning()
                self.suggestion_print(
                    "U", _("to Update cmp metadata volumes, some ext_id are not aligned to hypervisor data volumes.")
                )
            else:
                self.print_success()
                msg = _("Cmp metadata volumes match with hypervisor data volumes.")
                print(self.styler.green(msg))
                return True
        return False

    def exit_suggestion(self):
        """
        All is ok, suggest to exit.
        """
        self.print_info()
        red = self.styler.red
        green = self.styler.green
        exit_msg = _("Press") + " " + self.styler.underline("X")
        msg = red(exit_msg) + " " + red(_("to eXit")) + ", " + green(_("everything is ok!"))
        print(msg)
