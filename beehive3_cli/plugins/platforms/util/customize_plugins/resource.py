# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from urllib.parse import urlencode
from beecell.types.type_dict import dict_get
from beehive3_cli.plugins.platforms.util.customize_plugins import CustomizePlugin


class ResourceCustomizePlugin(CustomizePlugin):
    def __init__(self, manager):
        super().__init__(manager)

        manager.controller._meta.cmp = {"baseuri": "/v1.0/nrs", "subsystem": "resource"}
        manager.controller.configure_cmp_api_client()

    def __create_tags(self, configs):
        if self.has_config(configs, "resource.tags") is False:
            return

        self.write("##### RESOURCE TAGS")
        base_uri = "/v1.0/nrs/tags"

        for obj in dict_get(configs, "resource.tags"):
            group_uri = f"{base_uri}/{obj['value']}"

            name = obj["value"]

            exists = self.cmp_exists(group_uri, f"Resource tag {name} already exists")

            if exists is False:
                self.cmp_post(base_uri, {"resourcetag": obj}, f"Add resource tag: {name}")

    def __create_containers(self, configs):
        if self.has_config(configs, "resource.containers") is False:
            return

        self.write("##### RESOURCE CONTAINERS")
        base_uri = "/v1.0/nrs/containers"

        for obj in dict_get(configs, "resource.containers"):
            group_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            exists = self.cmp_exists(group_uri, f"Resource container {name} already exists")

            if exists is False:
                self.cmp_post(
                    base_uri,
                    {"resourcecontainer": obj},
                    f"Add resource containers: {name}",
                )

    def __sync_containers(self, configs):
        if self.has_config(configs, "resource.containers-sync") is False:
            return

        self.write("##### RESOURCE CONTAINERS SYNC")
        base_uri = "/v1.0/nrs/containers"

        for obj in dict_get(configs, "resource.containers-sync"):
            group_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            container_types = obj["types"]
            exists = self.cmp_exists(group_uri, f"Resource container {name} exists")

            if exists is False:
                self.write(f"container {name} does not exist")
                continue

            for rtype in container_types:
                data = {
                    "synchronize": {
                        "types": rtype,
                        "new": True,
                        "died": False,
                        "changed": False,
                    }
                }
                self.cmp_put(
                    base_uri + f"/{name}/discover",
                    data,
                    f"Sync resource container {name} for type {rtype}",
                )

    def __create_vsphere_flavors(self, configs):
        if self.has_config(configs, "resource.vsphere.flavors") is False:
            return

        self.write("##### RESOURCE VSPHERE FLAVOR")
        base_uri = "/v1.0/nrs/vsphere/flavors"

        for obj in dict_get(configs, "resource.vsphere.flavors"):
            #obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            # exists = self.cmp_exists(obj_uri, 'Vsphere flavor %s already exists' % name)

            # if exists is False:
            self.cmp_post(base_uri, {"flavor": obj}, f"Add vsphere flavor: {name}")

    def __create_vsphere_volumetypes(self, configs):
        if self.has_config(configs, "resource.vsphere.volumetypes") is False:
            return

        self.write("##### RESOURCE VSPHERE VOLUMETYPE")
        base_uri = "/v1.0/nrs/vsphere/volumetypes"

        for obj in dict_get(configs, "resource.vsphere.volumetypes"):
            name = obj["name"]
            datastores = obj.pop("datastores", [])
            volumetype = self.cmp_exists2(
                base_uri,
                f"Vsphere volumetype {name} already exists",
                data={"container": obj.get("container"), "name": name},
            )

            if volumetype is None:
                volumetype = self.cmp_post(base_uri, {"volumetype": obj}, f"Add vsphere volumetype: {name}").get(
                    "uuid"
                )

            for datastore in datastores:
                obj_uri = f"{base_uri}/{volumetype}"
                uri = obj_uri + "/datastores"
                msg = f"Add vsphere volumetype {volumetype} datastores: {datastore['uuid']}"
                self.cmp_post(uri, {"datastore": datastore}, msg)

    def __create_openstack_flavors(self, configs):
        if self.has_config(configs, "resource.openstack.flavors") is False:
            return

        self.write("##### RESOURCE OPENSTACK FLAVOR")
        base_uri = "/v1.0/nrs/openstack/flavors"

        for obj in dict_get(configs, "resource.openstack.flavors"):
            # obj_uri = '%s/%s' % (base_uri, obj['name'])
            name = obj["name"]
            extra_specs = obj.pop("extra_specs", None)
            data = {"name": name, "container": obj["container"]}
            exists = self.cmp_exists2(
                base_uri,
                f"Openstack flavor {name} already exists",
                data=data,
                key="flavors.0.id",
            )
            if exists is None:
                flavor = self.cmp_post(base_uri, {"flavor": obj}, f"Add openstack flavor: {name}")
                if extra_specs is not None:
                    obj_uri = f"{base_uri}/{flavor['uuid']}"
                    self.cmp_put(
                        obj_uri,
                        {"flavor": {"extra_specs": extra_specs}},
                        f"set openstack flavor {name} extra_specs: {extra_specs}",
                    )

    def __create_dns_zones(self, configs):
        if self.has_config(configs, "resource.dns.zones") is False:
            return

        self.write("##### RESOURCE DNS ZONE")
        base_uri = "/v1.0/nrs/dns/zones"

        for obj in dict_get(configs, "resource.dns.zones"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            #obj_records = obj.pop("records", "")
            exists = self.cmp_exists(obj_uri, f"Dns zone {name} already exists")

            if exists is False:
                self.cmp_post(base_uri, {"zone": obj}, f"Add dns zone: {name}")

    def __create_provider_regions(self, configs):
        if self.has_config(configs, "resource.provider.regions") is False:
            return

        self.write("##### RESOURCE PROVIDER REGION")
        base_uri = "/v1.0/nrs/provider/regions"

        for obj in dict_get(configs, "resource.provider.regions"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            exists = self.cmp_exists(obj_uri, f"Provider region {name} already exists")

            if exists is False:
                self.cmp_post(base_uri, {"region": obj}, f"Add provider region: {name}")

    def __create_provider_sites(self, configs):
        if self.has_config(configs, "resource.provider.sites") is False:
            return

        self.write("##### RESOURCE PROVIDER SITES")
        base_uri = "/v1.0/nrs/provider/sites"

        for obj in dict_get(configs, "resource.provider.sites"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            orchestrators = obj.pop("orchestrators", [])
            exists = self.cmp_exists(obj_uri, f"Provider site {name} already exists")

            if exists is False:
                self.cmp_post(base_uri, {"site": obj}, f"Add provider site: {name}")

            for orchestrator in orchestrators:
                if orchestrator["type"] == "openstack":
                    # get domain
                    data = urlencode({"container": orchestrator["id"], "name": "Default"})
                    domain = self.cmp_get("/v1.0/nrs/openstack/domains", data=data)
                    orchestrator["config"]["domain"] = domain["domains"][0]["id"]
                uri = obj_uri + "/orchestrators"
                msg = f"Add site {name} orchestrator: {orchestrator['id']}"
                self.cmp_post(uri, {"orchestrator": orchestrator}, msg)

    def __create_provider_compute_zones(self, configs):
        if self.has_config(configs, "resource.provider.compute_zones") is False:
            return

        self.write("##### RESOURCE PROVIDER COMPUTE ZONES")
        base_uri = "/v1.0/nrs/provider/compute_zones"

        for obj in dict_get(configs, "resource.provider.compute_zones"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            quota = obj.get("quota", {})
            sites = obj.pop("sites", [])
            exists = self.cmp_exists(obj_uri, f"Provider compute_zone {name} already exists")

            if exists is False:
                self.cmp_post(
                    base_uri,
                    {"compute_zone": obj},
                    f"Add provider compute_zone: {name}",
                )

            for site in sites:
                data = {
                    "availability_zone": {
                        "id": site,
                        "orchestrator_tag": "default",
                        "quota": quota,
                    }
                }
                uri = obj_uri + "/availability_zones"
                msg = f"Add compute_zone {name} availability_zones: {site}"
                self.cmp_post(uri, data, msg)

    def __create_provider_site_networks(self, configs):
        # patch to maintains compatibility with old file syntax
        if (
            self.has_config(configs, "resource.provider.site_networks") is False
            and self.has_config(configs, "resource.entities.site_networks") is False
        ):
            return

        self.write("##### RESOURCE PROVIDER SITE NETWORK")
        base_uri = "/v2.0/nrs/provider/site_networks"

        nets = dict_get(configs, "resource.provider.site_networks", default=[])
        nets.extend(dict_get(configs, "resource.entities.site_networks", default=[]))

        for obj in nets:
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            subnets = obj.pop("subnets", [])
            exists = self.cmp_exists(obj_uri, f"Provider site_network {name} already exists")

            if exists is False:
                self.cmp_post(
                    base_uri,
                    {"site_network": obj},
                    f"Add provider site_network: {name}",
                )

            data = {"subnets": subnets}
            uri = obj_uri + "/subnets"
            msg = f"Add site_network {name} subnets: {subnets}"
            self.cmp_post(uri, data, msg)

    def __create_provider_flavors(self, configs):
        if self.has_config(configs, "resource.provider.flavors") is False:
            return

        self.write("##### RESOURCE PROVIDER FLAVORS")
        base_uri = "/v1.0/nrs/provider/flavors"

        for obj in dict_get(configs, "resource.provider.flavors"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            exists = self.cmp_exists(obj_uri, f"Provider flavor {name} already exists")

            if exists is False:
                self.cmp_post(
                    base_uri + "/import",
                    {"flavor": obj},
                    f"Add provider flavor: {name}",
                )
            else:
                flavors = list(obj.get('flavors', []))
                self.cmp_put(
                    obj_uri,
                    {"flavor": {"flavors": flavors}},
                    f"Update provider flavor: {name}",
                )

    def __create_provider_volumeflavors(self, configs):
        if self.has_config(configs, "resource.provider.volumeflavors") is False:
            return

        self.write("##### RESOURCE PROVIDER VOLUME FLAVORS")
        base_uri = "/v1.0/nrs/provider/volumeflavors"

        for obj in dict_get(configs, "resource.provider.volumeflavors"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            exists = self.cmp_exists(obj_uri, f"Provider volumeflavor {name} already exists")

            if exists is False:
                self.cmp_post(
                    base_uri + "/import",
                    {"volumeflavor": obj},
                    f"Update provider volumeflavor: {name}",
                )
            else:
                obj = {"volume_types": obj.get("volume_types", [])}
                self.cmp_put(
                    obj_uri,
                    {"volumeflavor": obj},
                    f"Update provider volumeflavor: {name}",
                )

    def __create_provider_images(self, configs):
        if not self.has_config(configs, "resource.provider.images"):
            return

        self.write("##### RESOURCE PROVIDER IMAGES")
        base_uri = "/v1.0/nrs/provider/images"

        for obj in dict_get(configs, "resource.provider.images"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            exists = self.cmp_exists(obj_uri, f"Provider image {name} already exists")

            if exists is False:
                self.cmp_post(
                    base_uri + "/import",
                    {"image": obj},
                    f"Add provider image: {name}",
                )
            else:
                # update only image templates
                data = {"templates": obj.get("templates", [])}
                self.cmp_put(obj_uri, {"image": data}, msg=f"Update image {name}")
            print("---")

    def __create_provider_customizations(self, configs):
        if self.has_config(configs, "resource.provider.customizations") is False:
            return

        self.write("##### RESOURCE PROVIDER CUSTOMIZATIONS")
        base_uri = "/v1.0/nrs/provider/customizations"

        for obj in dict_get(configs, "resource.provider.customizations"):
            name = obj["name"]
            print(f"customization name: {name}")
            obj_uri = f"{base_uri}/{name}"
            exists = self.cmp_exists(obj_uri, f"Provider customization {name} already exists")

            if exists is False:
                self.cmp_post(
                    base_uri,
                    {"customization": obj},
                    f"Add provider customization: {name}",
                )
            else:
                data = {"awx_project": obj.get("awx_project", {})}
                self.cmp_put(obj_uri, {"customization": data}, msg=f"Update customization {name}")
            print("---")

    def run(self, configs, dry=False):
        if dry:
            return

        self.__create_tags(configs)
        self.__create_containers(configs)
        self.__sync_containers(configs)
        self.__create_vsphere_flavors(configs)
        self.__create_vsphere_volumetypes(configs)
        self.__create_openstack_flavors(configs)
        self.__create_dns_zones(configs)
        self.__create_provider_regions(configs)
        self.__create_provider_sites(configs)
        self.__create_provider_compute_zones(configs)
        self.__create_provider_site_networks(configs)
        self.__create_provider_flavors(configs)
        self.__create_provider_volumeflavors(configs)
        self.__create_provider_images(configs)
        self.__create_provider_customizations(configs)
