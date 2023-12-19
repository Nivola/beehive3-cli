# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from json import dumps as jdumps
from textwrap import dedent
from typing import List, Union, Iterable
from beecell.types.type_id import is_name
from beecell.types.type_dict import dict_get
from beedrones.vsphere.client import VsphereManager
from beedrones.openstack.client import OpenstackManager
from beehive3_cli.core.controller import BaseController
from beehive3_cli.core.util import CmpUtils


class AdminError(Exception):
    """custom admin error"""

    def __init__(self, message, *args):
        # remove starting common whitespace
        # to non-empty lines in the case
        # of multiline strings
        dd_message = dedent(message)
        if args:
            super().__init__(dd_message, args)
        else:
            super().__init__(dd_message)


class AdminChildController(BaseController):
    """admin child controller"""

    # key = ""

    class Meta:
        stacked_on = "mgmt"
        stacked_type = "nested"
        cmp = {"baseuri": "/v1.0/nrs", "subsystem": "resource"}

        # cmp = {"baseuri": "", "subsystem": ""}

    def ask(self, prompt: str, style: int = None, yn: bool = True, alowed: Iterable = None) -> str:
        if style is None:
            style = self.styler.YELLOW
        test = ""
        ## define alowed response if any
        if yn:
            alowed = ("Y", "N")

        if alowed is None:
            test = self.styler.prompt(prompt, style)
        else:
            ## make check case insensitive
            calow = [str(x).upper() for x in alowed]
            while test not in calow:
                test = self.styler.prompt(prompt, style)[0].upper()
        return test

    def pre_command_run(self):
        super().pre_command_run()
        self.configure_cmp_api_client()

    def init_container(self, container: dict):
        """initialize  the container info
        container is the hypervisor which is running the database server

        self.container_info : contains container description e connection info
        self.container_type: contians hyprdvisor type for easy check hypervisere may be Vspher or openstack
        self.hypervisor_client  is the client from bedrones library

        """
        self.container_info = container
        self.container_type: str = dict_get(container, "__meta__.definition").upper()
        conn: dict = container.get("conn", {})
        # for item in conn.keys():
        #     print(f"for item {item}")
        #     self.decrypt_pwd( self.container_info["conn"][item])

        if self.container_type == "VSPHERE":
            self.hypervisor_client = VsphereManager(conn.get("vcenter"), conn.get("nsx"), key=self.key)
        elif self.container_type == "OPENSTACK":
            api = conn.get("api")
            self.hypervisor_client = OpenstackManager(api.get("uri"), default_region=api.get("region"))
            self.hypervisor_client.authorize(
                user=api.get("user"),
                pwd=api.get("pwd"),
                project=api.get("project"),
                domain=api.get("domain"),
                key=self.key,
            )
        else:
            raise AdminError(f"container {self.container_type} not implemented")

    def set_vsphere_container(self):
        self.container_type = "VSPHERE"

    def set_openstack_container(self):
        self.container_type = "OPENSTACK"

    def set_container(self, conttype: str):
        self.container_type = conttype

    def get_hypervisor_server(self, server_id: str):
        """get servier detail from hypervior"""
        # acording to implemeting tecnologies openstack or vsphere
        if self.container_type == "VSPHERE":
            client: VsphereManager = self.hypervisor_client
            res = client.server.get(server_id)
            data = client.server.detail(res)
            pass
            return data
        elif self.container_type == "OPENSTACK":
            osclient = OpenstackManager = self.hypervisor_client

            res = osclient.server.get(server_id)
            server_volumes: List[dict] = res["os-extended-volumes:volumes_attached"]
            flavor_id = dict_get(res, "flavor.id")
            res["flavor"]["name"] = osclient.flavor.get(flavor_id).get("name")

            for item in server_volumes:
                volume = osclient.volume_v3.get(item["id"])
                item.update(volume)
            return res
        else:
            raise AdminError(f"container {self.container_type} not implemented")

    def get_cmp_container(self, identifier: str) -> dict:
        """getcontainer by identifyer id or uuid"""
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/containers/{identifier}"
        return self.cmp_get(uri).get("resourcecontainer", {})

    def get_cmp_resource(self, identifier: str) -> dict:
        """get resource"""
        self.app.subsystem = "resource"
        uri: str = f"/v1.0/nrs/entities/{identifier}"
        result: dict = self.cmp_get(uri)
        return result.get("resource")

    def get_cmp_entity_tags(self, identifier: str) -> str:
        """
        get entity tags
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
        remove tag dìfrom resource
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
        """reset cache for resource"""
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{identifier}/cache"
        res = self.cmp_put(uri)
        return res

    def set_cmp_resource_active(self, identifier: str):
        """force entity state at ACTIVE"""
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{identifier}/state"
        res = self.cmp_put(uri, data={"state": "ACTIVE"})
        return res

    def set_cmp_resource(self, identifier: str, **kwargs) -> dict:
        """Set reosoruce attribute usingi force in order to not
        trigger any managment logic in the resource layer"""
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
        """get resource configuration attribute"""
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{res_ident}/config"
        result = self.cmp_get(uri).get("config")
        return result

    def set_cmp_resource_config(self, res_ident: Union[str, int], key: str, value):
        """set resource configuration attribute"""
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{res_ident}/config"
        result = self.cmp_put(uri, data={"config": {"key": key, "value": str(value)}})
        return result

    def set_cmp_service_config(self, ideintifier: Union[str, int], key: str, value: str):
        uri = f"/v2.0/nws/serviceinsts/{ideintifier}/config"
        res = self.cmp_put(uri, data={"config": {"key": key, "value": value}})
        return res

    def get_cmp_restree(self, identifier: str) -> dict:
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{identifier}/tree"
        tree = self.cmp_get(uri)
        return tree

    def get_cmp_linkedres(self, identifier: str) -> List[dict]:
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{identifier}/linked"
        return self.cmp_get(uri).get("resources", [])

    def get_cmp_service_instance(self, oid: str, plugin: str = "DatabaseInstance") -> dict:
        self.app.subsystem = "service"
        uri = f"/v2.0/nws/serviceinsts/{oid}"
        bu_servinst = self.cmp_get(uri).get("serviceinst")
        plugintype = bu_servinst.get("plugintype")

        if plugintype != plugin:
            raise AdminError(f" {oid} not found")
        return bu_servinst

    def set_cmp_resource_ext_id(self, res_uuid: str, ext_id: str):
        print(
            self.styler.clear_line() + "Setting ext_id %s on resource %s" % (ext_id, res_uuid),
            end="",
        )
        uri = "/v1.0/nrs/entities/%s" % (res_uuid)
        status = self.cmp_put(uri, data={"resource": {"ext_id": ext_id}})
        print(
            self.styler.clear_line() + "Set ext_id %s on resource %s with status %s" % (ext_id, res_uuid, str(status)),
            end="",
        )

    def set_cmp_resource_enable_quotas(self, identifier: str, value: bool = False):
        self.app.subsystem = "resource"
        uri = f"/v1.0/nrs/entities/{identifier}"
        if value:
            res = self.cmp_put(uri, data={"resource": {"enable_quotas": True}})
        else:
            res = self.cmp_put(uri, data={"resource": {"disable_quotas": True}})
        return res

    def get_cmp_account(self, identifier: str, div_uuid: str = None) -> dict:
        """
        get cmp account
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
                raise AdminError(
                    """\
                                 Multiple accounts with the given name.
                                 Select one using its uuid instead.
                                 """
                )
            if count == 0:
                raise AdminError(f"The account {identifier} does not exist")
            return res.get("accounts")[0]
        else:
            uri = uri + f"/{identifier}"
            res = self.cmp_get(uri)
            return res.get("account")

    def get_cmp_division(self, identifier: str, org_uuid: str = None) -> dict:
        """
        get cmp division
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
                raise AdminError(
                    """\
                                 Multiple divisions with the given name.
                                 Select one using its uuid instead.
                                 """
                )
            if count == 0:
                raise AdminError(f"The division {identifier} does not exist")
            return res.get("divisions")[0]
        else:
            uri = uri + f"/{identifier}"
            res = self.cmp_get(uri)
            return res.get("division")

    def get_cmp_sites(self) -> dict:
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
        if container is None or resclass is None or name is None:
            raise AdminError("parametri necessari")

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
        if container is None or resclass is None or name is None:
            raise AdminError("parametri necessari")
        data = {
            "container": container,
            "resclass": resclass,
            "name": name,
        }
        if not desc is None:
            data["desc"] = desc
        if not parent is None:
            data["parent"] = parent
        if not attribute is None:
            data["attribute"] = jdumps(attribute)
        if not tags is None:
            data["tags"] = ",".join(tags)

        self.app.subsystem = "resource"
        uri = "/v1.0/nrs/entities/"

        res = self.cmp_post(uri, data={"resource": data})
        return res["uuid"]

    def delete_resource(self, ideintifier: str, force: bool = False, deep: bool = False):
        fv = "false"
        dv = "false"
        if force:
            fv = "true"
        if deep:
            dv = "true"
        uri = f"/v1.0/nrs/entities/{ideintifier}?force={fv}&deep={dv}"
        self.cmp_delete(uri, confirm=False)

    def get_account(self, account_id):
        """Get account by id

        :param account_id: account id
        :return: account object
        """
        check = is_name(account_id)
        uri = "/v1.0/nws/accounts"
        if check is True:
            oid = account_id.split(".")
            if len(oid) == 1:
                data = "name=%s" % oid[0]
                res = self.cmp_get(uri, data=data)
            elif len(oid) == 2:
                data = "name=%s&division_id=%s" % (oid[1], oid[0])
                res = self.cmp_get(uri, data=data)
            elif len(oid) == 3:
                # get division
                data = "name=%s&organization_id=%s" % (oid[1], oid[0])
                uri2 = "/v1.0/nws/divisions"
                divs = self.cmp_get(uri2, data=data)
                # get account
                if divs.get("count") > 0:
                    data = "name=%s&division_id=%s" % (
                        oid[2],
                        divs["divisions"][0]["uuid"],
                    )
                    res = self.cmp_get(uri, data=data)
                else:
                    raise Exception("Account is wrong")
            else:
                raise Exception("Account is wrong")

            count = res.get("count")
            if count > 1:
                raise Exception("There are some account with name %s. Select one using uuid" % account_id)
            if count == 0:
                raise Exception("The account %s does not exist" % account_id)

            account = res.get("accounts")[0]
            self.app.log.info("get account by name: %s" % account)
            return account

        uri += "/" + account_id
        account = self.cmp_get(uri).get("account")
        self.app.log.info("get account by id: %s" % account)
        return account
