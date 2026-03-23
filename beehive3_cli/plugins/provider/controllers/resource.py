# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from datetime import datetime
from time import time
from typing import Dict
from urllib.parse import urlencode
from cement.ext.ext_argparse import ex
from beecell.file import read_file
from beecell.types.type_string import truncate, bool2str, str2bool
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import BaseController, PARGS, ARGS
from beehive3_cli.core.util import load_config
from beehive3_cli.translate import _


class ResourceProviderController(BaseController):
    class Meta:
        label = "res_provider"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("provider management")
        help = _("provider management")

        cmp = {"baseuri": "/v1.0/nrs/provider", "subsystem": "resource"}

        headers = ["id", "uuid", "name", "parent", "state", "creation", "modified"]
        fields = [
            "id",
            "uuid",
            "name",
            "parent",
            "state",
            "date.creation",
            "date.modified",
        ]
        region_headers = [
            "id",
            "uuid",
            "name",
            "parent",
            "state",
            "creation",
            "modified",
        ]
        region_fields = [
            "id",
            "uuid",
            "name",
            "parent",
            "state",
            "date.creation",
            "date.modified",
        ]
        site_headers = [
            "id",
            "uuid",
            "name",
            "parent",
            "state",
            "creation",
            "modified",
            "orchestrators     ping",
        ]
        site_fields = [
            "id",
            "uuid",
            "name",
            "parent",
            "state",
            "date.creation",
            "date.modified",
            "orchestrators",
        ]
        site_network_headers = [
            "uuid",
            "name",
            "desc",
            "state",
            "creation",
            "vlan",
            "subnets",
            "zabbix_proxy",
        ]
        site_network_fields = [
            "uuid",
            "name",
            "desc",
            "state",
            "date.creation",
            "attributes.configs.vlan",
            "attributes.configs.subnets",
            "attributes.configs.zabbix_proxy",
        ]
        compute_zones_headers = [
            "id",
            "name",
            "desc",
            "state",
            "availability_zones",
            "creation",
            "modified",
        ]
        compute_zones_fields = [
            "uuid",
            "name",
            "desc",
            "state",
            "availability_zones",
            "date.creation",
            "date.modified",
        ]
        vpc_headers = [
            "id",
            "uuid",
            "name",
            "parent",
            "state",
            "type",
            "cidr",
            "creation",
            "modified",
        ]
        vpc_fields = [
            "id",
            "uuid",
            "name",
            "parent",
            "state",
            "attributes.configs.type",
            "attributes.configs.cidr",
            "date.creation",
            "date.modified",
        ]
        security_group_headers = [
            "id",
            "uuid",
            "name",
            "parent",
            "compute_zone",
            "state",
            "creation",
            "modified",
            "rules",
        ]
        security_group_fields = [
            "id",
            "uuid",
            "name",
            "parent",
            "compute_zone",
            "state",
            "date.creation",
            "date.modified",
            "rules",
        ]
        rule_headers = ["id", "uuid", "name", "parent", "state", "creation", "modified"]
        rule_fields = [
            "id",
            "uuid",
            "name",
            "parent",
            "state",
            "date.creation",
            "date.modified",
        ]
        instance_fields = [
            "id",
            "parent",
            "name",
            "availability_zone.name",
            "hypervisor",
            "attributes.host",
            "state",
            "runstate",
            "os",
            "vpcs.0.name",
            "security_groups.0.name",
            "flavor.vcpus",
            "flavor.memory",
            "volume.size",
            "volume.num",
            "vpcs.0.fixed_ip.ip",
            "attributes.backup_enabled",
            "attributes.monitoring_enabled",
            "attributes.logging_enabled",
        ]
        instance_headers = [
            "id",
            "parent",
            "name",
            "av_zone",
            "type",
            "host",
            "state",
            "runstate",
            "os",
            "vpc",
            "sg",
            "cpu",
            "ram",
            "disk",
            "disk #",
            "ip",
            "bck",
            "monit",
            "logfw",
        ]
        flavor_headers = [
            "id",
            "uuid",
            "name",
            "parent",
            "state",
            "creation",
            "vcpus",
            "memory",
            "disk",
        ]
        flavor_fields = [
            "id",
            "uuid",
            "name",
            "parent",
            "state",
            "date.creation",
            "attributes.configs.vcpus",
            "attributes.configs.memory",
            "attributes.configs.disk",
        ]
        image_headers = [
            "id",
            "name",
            "parent",
            "state",
            "os",
            "os-ver",
            "min-disk-size",
            "modified",
            "hypervisors",
        ]
        image_fields = [
            "uuid",
            "name",
            "parent",
            "state",
            "attributes.configs.os",
            "attributes.configs.os_ver",
            "attributes.configs.min_disk_size",
            "date.modified",
            "availability_zones.0.hypervisors",
        ]
        share_headers = [
            "id",
            "name",
            "parent",
            "state",
            "type",
            "proto",
            "size",
            "vpc",
            "export",
            "creation",
        ]
        share_headers_v2 = [
            "id",
            "name",
            "export",
            "parent",
            "state",
            "type",
            "proto",
            "size",
            "site",
            "creation",
        ]
        share_fields_v2 = [
            "uuid",
            "name",
            "details.exports",
            "parent",
            "state",
            "details.type",
            "details.proto",
            "details.size",
            "availability_zone.name",
            "date.creation",
        ]
        share_fields = [
            "uuid",
            "name",
            "parent",
            "state",
            "details.type",
            "details.proto",
            "details.size",
            "vpcs.0.name",
            "details.exports.0.mounts",
            "date.creation",
        ]
        volume_fields = [
            "id",
            "name",
            "parent",
            "availability_zone.name",
            "flavor.name",
            "hypervisor",
            "bootable",
            "encrypted",
            "state",
            "size",
            "used",
            "instance.uuid",
        ]
        volume_headers = [
            "id",
            "name",
            "parent",
            "av_zone",
            "flavor",
            "hypervisor",
            "bootable",
            "encrypted",
            "state",
            "size",
            "used",
            "instance",
        ]
        volumeflavor_fields = [
            "id",
            "name",
            "desc",
            "parent",
            "state",
            "attributes.configs.disk_iops",
        ]
        volumeflavor_headers = ["id", "name", "desc", "parent", "state", "disk_iops"]
        customization_headers = [
            "id",
            "name",
            "parent",
            "state",
            "creation",
            "modified",
            "orchestrators",
        ]
        customization_fields = [
            "id",
            "name",
            "parent",
            "state",
            "date.creation",
            "date.modified",
        ]
        gateway_headers = [
            "id",
            "name",
            "parent",
            "state",
            "type",
            "flavor",
            "external_ip_address",
            "vpcs",
            "bastion",
            "creation",
        ]
        gateway_fields = [
            "id",
            "name",
            "parent_desc",
            "state",
            "attributes.type",
            "attributes.flavor",
            "external_ip_address",
            "vpcs",
            "bastion",
            "date.creation",
        ]
        load_balancer_headers = [
            "uuid",
            "name",
            "parent_desc",
            "state",
            "runstate",
            "type",
            "network_appliance",
            "ext_ip_addr",
            "creation",
        ]
        load_balancer_fields = [
            "uuid",
            "name",
            "parent_desc",
            "state",
            "runstate",
            "attributes.orchestrator_type",
            "attributes.network_appliance.name",
            "attributes.vip",
            "date.creation",
        ]

    def get_container(self):
        """Get container provider"""
        data = urlencode({"container_type": "Provider"})
        uri = "/v1.0/nrs/containers"
        res = self.cmp_get(uri, data=data)["resourcecontainers"][0]["id"]
        self.app.log.info(f"Get resource container: {truncate(res)}")
        return str(res)

    def pre_command_run(self):
        super().pre_command_run()

        self.configure_cmp_api_client()

    #
    # Region
    #
    @ex(
        help=_("get region(s)"),
        description=_("get region(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("region id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def region_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = self.baseuri + f"/regions/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("region")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            uri = f"{self.baseuri}/regions"
            res = self.cmp_get(uri)
            self.app.render(
                res,
                key="regions",
                headers=self._meta.region_headers,  # pylint: disable=E1101
                fields=self._meta.region_fields,  # pylint: disable=E1101
            )

    @ex(
        help=_("add region"),
        description=_("add region"),
        arguments=ARGS(
            [
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def region_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + "/regions"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add region {res['uuid']}"})

    @ex(
        help=_("delete region"),
        description=_("delete region"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("region id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def region_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = self.baseuri + f"/regions/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"region {oid}")

    @ex(
        help=_("update region"),
        description=_("update region"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("region id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def region_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + f"/regions/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.log.info(f"Update {self._meta.alias}: {truncate(res)}")  # pylint: disable=E1101
        self.app.render({"msg": f"update region {res['uuid']}"})

    #
    # site
    #
    @ex(
        help=_("get site(s)"),
        description=_("get site(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("site id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def site_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/sites/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("site")
                attributes = res.pop("attributes")
                orchestrators = res.pop("orchestrators")  # (non aggiornato) # pylint: disable=W0612
                limits = attributes.pop("limits")

                attributes_orchestrators = attributes.pop("orchestrators")
                self.app.render(res, details=True)

                self.c("\n\nattributes", "underline")
                self.app.render(attributes, details=True)

                self.c("\n\norchestrators", "underline")
                transform = {"config.colortext": False}
                self.app.render(
                    attributes_orchestrators,
                    headers=["id", "name", "type", "tag", "ping", "config"],
                    maxsize=100,
                    transform=transform,
                )

                self.c("\n\nlimits", "underline")
                self.app.render(limits, details=True)
            else:
                self.app.render(res, details=True)
        else:
            uri = f"{self.baseuri}/sites"
            res = self.cmp_get(uri)

            # sostituisco "orchestrators" (non aggiornato) con "orchestrators" sotto "attributes" (completo)
            for site in res["sites"]:
                attributes = site.get("attributes")
                attributes_orchestrators = attributes.pop("orchestrators")

                for orchestrator in attributes_orchestrators:
                    # se name non è presente, prendo il type
                    name = orchestrator.get("name", orchestrator.get("type"))
                    orchestrator["name"] = name

                    # se ping non è presente, metto trattino
                    ping = orchestrator.get("ping", "-")
                    orchestrator["ping"] = ping

                site["orchestrators"] = attributes_orchestrators

            transform = {"orchestrators": lambda x: "\n".join([f"{o['name']:18}{o['ping']}" for o in x])}
            self.app.render(
                res,
                key="sites",
                headers=self._meta.site_headers,  # pylint: disable=E1101
                fields=self._meta.site_fields,  # pylint: disable=E1101
                transform=transform,
                maxsize=400,
            )

    @ex(
        help=_("add site"),
        description=_("add site"),
        arguments=ARGS(
            [
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def site_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + "/sites"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add site {res['uuid']}"})

    @ex(
        help=_("delete site"),
        description=_("delete site"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("site id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def site_delete(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = self.baseuri + f"/sites/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"site {oid}")

    @ex(
        help=_("update site"),
        description=_("update site"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("site id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def site_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + f"/sites/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update site {res['uuid']}"})

    @ex(
        help=_("get site orchestrators"),
        description=_("get site orchestrators"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("site id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def site_orchestrator_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/sites/{oid}"
        res = self.cmp_get(uri)
        res = res.get("site")
        attributes = res.pop("attributes")
        orchestrators = attributes.pop("orchestrators")

        if self.is_output_text():
            for orchestrator in orchestrators:
                self.c("\n\n" + orchestrator["id"], "underline")
                self.app.render(orchestrator, details=True)
        else:
            self.app.render(res, details=True)

    @ex(
        help=_("add site orchestrator"),
        description=_("add site orchestrator"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("site id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def site_orchestrator_add(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = f"{self.baseuri}/sites/{oid}/orchestrators"
        self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add orchestrator to site {oid}"})

    @ex(
        help=_("delete site orchestrator"),
        description=_("delete site orchestrator"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("site id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["orchestrator"],
                    {
                        "help": _("orchestrator id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def site_orchestrator_del(self):
        oid = self.app.pargs.id
        orchestrator = self.app.pargs.orchestrator
        data = {"orchestrator": {"id": orchestrator}}
        uri = f"{self.baseuri}/sites/{oid}/orchestrators"
        self.cmp_delete(uri, data=data)
        self.app.render({"msg": f"delete orchestrator from site {oid}"})

    #
    # site network
    #
    @ex(
        help=_("get site network(s)"),
        description=_("get site network(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("site network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-allocation-pools-details"],
                    {
                        "help": _("show the allocation pools details"),
                        "action": "store_true",
                        "default": False,
                    },
                ),

            ]
        ),
    )
    def site_network_get(self):
        oid = getattr(self.app.pargs, "id", None)
        allocation_pools_details = str2bool(getattr(self.app.pargs, "allocation_pools_details", False))

        if oid is not None:
            data = {}
            if allocation_pools_details:
                data['allocation_pools_details'] = True
            uri = f"/v2.0/nrs/provider/site_networks/{oid}"
            res = self.cmp_get(uri, data=data)

            if self.is_output_text():
                res = res.get("site_network")
                attributes = res.pop("attributes").pop("configs")
                subnets = attributes.pop("subnets")
                self.app.render(res, details=True)
                self.c("\n\nattributes", "underline")
                self.app.render(attributes, details=True)
                self.c("\n\nsubnets", "underline")

                transform = {"allocation_pools.colortext": False}
                self.app.render(
                    subnets,
                    headers=[
                        "cidr",
                        "allocable",
                        "enable_dhcp",
                        "gateway",
                        "dns_nameservers",
                        "allocation_pools",
                        "vsphere_id",
                        "openstack_id",
                    ],
                    transform=transform,
                )
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            if allocation_pools_details:
                data += "&allocation_pools_details=true"
            uri = "/v2.0/nrs/provider/site_networks"

            def render(self, res, **kwargs):
                transform = {
                    "attributes.configs.subnets": lambda x: ",".join([s["cidr"] for s in x if x is not None]),
                    "attributes.configs.subnets.colortext": True,
                }
                self.app.render(
                    res,
                    key="site_networks",
                    headers=self._meta.site_network_headers,  # pylint: disable=E1101
                    fields=self._meta.site_network_fields,  # pylint: disable=E1101
                    transform=transform,
                    maxsize=100,
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render, pagesize=50)

    @ex(
        help=_("add site network"),
        description=_("add site network"),
        arguments=ARGS(
            [
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def site_network_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = "/v2.0/nrs/provider/site_networks"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add site network {res['uuid']}"})

    @ex(
        help=_("delete site network"),
        description=_("delete site network"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("site network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def site_network_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = f"/v2.0/nrs/provider/site_networks/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"site network {oid}")

    @ex(
        help=_("update site network"),
        description=_("update site network"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("site network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def site_network_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = f"/v2.0/nrs/provider/site_networks/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update site network {res['uuid']}"})

    @ex(
        help=_("add site network subnet"),
        description=_("add site network subnet"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("site network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["cidr"],
                    {
                        "help": _("subnet cidr"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pools"],
                    {
                        "help": _(
                            "allocation pools. Syntax: openstack:<start-ip>:<stop-ip>,vmware:<start-ip>:<stop-ip>"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-gw"],
                    {
                        "help": _("default gateway"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-enable_dhcp"],
                    {
                        "help": _("if true enable dhcp"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
                (
                    ["-allocable"],
                    {
                        "help": _("if true subnet is allocable"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
            ]
        ),
    )
    def site_network_subnet_add(self):
        oid = self.app.pargs.id
        cidr = self.app.pargs.cidr
        pools = self.app.pargs.pools
        gw = self.app.pargs.gw
        enable_dhcp = str2bool(self.app.pargs.enable_dhcp)
        allocable = str2bool(self.app.pargs.allocable)
        uri = f"/v2.0/nrs/provider/site_networks/{oid}/subnets"
        allocation_pools = {}
        for pool in pools.split(","):
            pool = pool.split(":")
            allocation_pools[pool[0]] = [{"start": pool[1], "end": pool[2]}]
        data = {
            "cidr": cidr,
            "allocation_pools": allocation_pools,
            "enable_dhcp": enable_dhcp,
            "allocable": allocable,
        }
        if gw is not None:
            data["gateway"] = gw

        """
              - cidr: ###.###.###.###/24
                allocation_pools:
                  openstack:
                    - start: ###.###.###.###
                      end: ###.###.###.###
                enable_dhcp: false
                allocable: false
        """

        self.cmp_post(uri, data={"subnets": [data]})
        self.app.render({"msg": f"delete subnet {cidr}"})

    @ex(
        help=_("delete site network subnet"),
        description=_("delete site network subnet"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("site network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["cidr"],
                    {
                        "help": _("subnet cidr"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def site_network_subnet_del(self):
        oid = self.app.pargs.id
        cidr = self.app.pargs.cidr
        uri = f"/v2.0/nrs/provider/site_networks/{oid}/subnets"
        data = {"subnets": [{"cidr": cidr}]}
        self.cmp_delete(uri, data=data, entity=f"subnet {cidr}")

    #
    # compute zone
    #
    def __is_managed(self, oid):
        # get ssh management status
        uri = self.baseuri + f"/compute_zones/{oid}/manage"
        mgt = self.cmp_get(uri, "GET").get("is_managed", [])
        res = {
            "is-managed": bool2str(mgt),
            "has-backup": "false",
            "has-monitor": "false",
        }
        return res

    def __get_availability_zones(self, oid):
        # get ssh management status
        uri = self.baseuri + f"/compute_zones/{oid}/availability_zones"
        res = self.cmp_get(uri, "GET").get("availability_zones", [])
        return res

    @ex(
        help=_("get provider computes zone"),
        description=_("get provider computes zone(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("compute zone name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("compute zone description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def compute_zone_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = self.baseuri + f"/compute_zones/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("compute_zone")
                res.pop("availability_zones", None)
                self.app.render(res, details=True)
                avz = self.__get_availability_zones(oid)
                self.c("\n\navailability_zones", "underline")
                self.app.render(
                    avz,
                    fields=["id", "name", "state", "site.id", "site.name"],
                    headers=["id", "name", "state", "site-id", "site-name"],
                )
                self.c("\n\nconfigs", "underline")
                config = self.__is_managed(oid)
                self.app.render(config, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "tags"]
            mappings = {
                "name": lambda n: "%" + n + "%",
                "desc": lambda n: "%" + n + "%",
            }
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/compute_zones"

            def render(self, res, **kwargs):
                self.app.render(
                    res,
                    key="compute_zones",
                    headers=self._meta.compute_zones_headers,  # pylint: disable=E1101
                    fields=self._meta.compute_zones_fields,  # pylint: disable=E1101
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render)

    @ex(
        help=_("add compute zone"),
        description=_("add compute zone"),
        arguments=ARGS(
            [
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def compute_zone_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + "/compute_zones"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add compute zone {res['uuid']}"})

    @ex(
        help=_("delete compute zone"),
        description=_("delete compute zone"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def compute_zone_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = self.baseuri + f"/compute_zones/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"compute zone {oid}")

    @ex(
        help=_("update compute zone"),
        description=_("update compute zone"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def compute_zone_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + f"/compute_zones/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update compute zone {res['uuid']}"})

    @ex(
        help=_("enable provider computes zone management by ssh module"),
        description=_("enable provider computes zone management by ssh module"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def compute_zone_manage(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = self.baseuri + f"/compute_zones/{oid}/manage"
        res = self.cmp_post(uri).get("manage", [])
        msg = f"Enable compute zone {oid} management with ssh group: {res}"
        self.app.log.info(msg)
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("disable provider computes zone management by ssh module"),
        description=_("disable provider computes zone management by ssh module"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def compute_zone_unmanage(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = self.baseuri + f"/compute_zones/{oid}/manage"
        res = self.cmp_delete(uri)
        msg = f"Disable compute zone {oid} management with ssh group: {res}"
        self.app.log.info(msg)
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("list compute zone ssh keys available"),
        description=_("list compute zone ssh keys available"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def compute_zone_sshkeys(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = self.baseuri + f"/compute_zones/{oid}/sshkeys"
        res = self.cmp_get(uri).get("sshkeys", [])
        self.app.log.info(f"Get compute zone {oid} sshkeys: {truncate(res)}")
        self.app.render(
            res,
            key="compute_zones",
            headers=["id", "name", "desc", "date"],
            fields=["uuid", "name", "desc", "date.creation"],
        )

    @ex(
        help=_("get compute zone metrics"),
        description=_("get compute zone metrics"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def compute_zone_metric_get(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = self.baseuri + f"/compute_zones/{oid}/metrics"
        res = self.cmp_get(uri).get("compute_zone")
        resp = []
        for item in res:
            for m in item.get("metrics"):
                resp.append(
                    {
                        "id": item.get("uuid"),
                        "type": item.get("type"),
                        "extraction-date": item.get("extraction_date"),
                        "metric": m.get("key"),
                        "metric-value": m.get("value"),
                        "metric-type": m.get("type"),
                        "metric-unit": m.get("unit"),
                    }
                )
        self.app.render(
            resp,
            headers=[
                "id",
                "type",
                "extraction-date",
                "metric",
                "metric-value",
                "metric-unit",
                "metric-type",
            ],
        )

    @ex(
        help=_("delete compute zone metrics cache"),
        description=_("delete compute zone metrics cache"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def compute_zone_metric_cache_delete(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = self.baseuri + f"/compute_zones/{oid}/metrics/cache"
        res = self.cmp_delete(uri)
        self.app.render({"msg": f"delete compute zone metric cache {res}"})

    @ex(
        help=_("pre load compute zones metrics"),
        description=_("pre load compute zones metrics"),
        arguments=ARGS(),
    )
    def compute_zone_metric_preload(self):
        uri = self.baseuri + "/compute_zones"
        css = self.cmp_get(uri, data={"size": -1}).get("compute_zones")
        for cs in css:
            start = time()
            uri = self.baseuri + f"/compute_zones/{cs['id']}/metrics"
            self.cmp_get(uri).get("compute_zone")
            elapsed = time() - start
            print(cs["name"], elapsed)

    @ex(
        help=_("get provider childs"),
        description=_("get provider childs"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def compute_zone_child_get(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = self.baseuri + f"/compute_zones/{oid}/childs"
        res = self.cmp_get(uri).get("resources")
        s = sorted(res, key=lambda i: i["name"])
        resp = sorted(s, key=lambda i: i["__meta__"]["definition"])
        headers = ["id", "uuid", "type", "name", "state", "runstate", "date"]
        fields = [
            "id",
            "uuid",
            "__meta__.definition",
            "name",
            "state",
            "runstate",
            "date.creation",
        ]
        self.app.render(resp, headers=headers, fields=fields)

    @ex(
        help=_("add compute zone availability zone"),
        description=_("add compute zone availability zone"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def compute_zone_availability_zone_add(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = f"{self.baseuri}/compute_zones/{oid}/availability_zones"
        self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add availability zone to compute zone {oid}"})

    @ex(
        help=_("delete compute zone availability zone"),
        description=_("delete compute zone availability zone"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["zone"],
                    {
                        "help": _("site name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def compute_zone_availability_zone_del(self):
        oid = self.app.pargs.id
        zone = self.app.pargs.zone
        data = {"availability_zone": {"id": zone}}
        uri = f"{self.baseuri}/compute_zones/{oid}/availability_zones"
        self.cmp_delete(
            uri,
            data=data,
            entity=f"availability zone {zone} from compute zone {oid}",
        )

    @ex(
        help=_("disable compute zone availability zone"),
        description=_("disable compute zone availability zone"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("availability zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def compute_zone_availability_zone_disable(self):
        oid = self.app.pargs.id
        data = {"state": "DISABLED"}
        uri = f"/v1.0/nrs/entities/{oid}/state"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"disable availability zone {oid}"})

    @ex(
        help=_("enable compute zone availability zone"),
        description=_("enable compute zone availability zone"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("availability zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def compute_zone_availability_zone_enable(self):
        oid = self.app.pargs.id
        data = {"state": "ACTIVE"}
        uri = f"/v1.0/nrs/entities/{oid}/state"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"enable availability zone {oid}"})

    @ex(
        help=_("get compute zone quotas"),
        description=_("get compute zone quotas"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def compute_zone_quota_get(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = self.baseuri + f"/compute_zones/{oid}/quotas"
        res = self.cmp_get(uri, timeout=500).get("quotas")
        self.app.render(res, headers=["quota", "value", "allocated", "unit"])

    @ex(
        help=_("get compute zone quotas classes"),
        description=_("get compute zone quotas classes"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def compute_zone_default_quota_get(self):
        oid = self.app.pargs.id
        uri = self.baseuri + f"/compute_zones/{oid}/quotas/classes"
        res = self.cmp_get(uri, "GET").get("quota_classes", [])
        self.app.render(res, headers=["quota", "default", "unit"])

    @ex(
        help=_("check provider computes zone quota"),
        description=_(
            """
        check provider computes zone quota.
        The command will check whether it is possible to allocate 'value' amount of quota 'quota'
        without reaching the currently set maximum value in cmp for that quota.
        e.g. share.blocks set in cmp with max: 1024, current: 1000
        if you try to check whether you can allocate 20, if will work, but if you try to allocate
        30, you get a 'quota share.blocks exceeded' exception.
        More in detail quota_to_allocate = cli command 'value' parameter + currently allocated
        if quota_to_allocate > max -> exception.
        """
        ),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["quotas"],
                    {
                        "help": _("compute zone quota ex. database.instances"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["value"],
                    {
                        "help": _("compute zone quota value ex. 3"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-check_all"],
                    {
                        "help": _("check all quotas, not just the given one"),
                        "action": "store_true",
                    },
                ),
            ]
        ),
    )
    def compute_zone_quota_check(self):
        oid = self.app.pargs.id
        quota = self.app.pargs.quotas
        value = self.app.pargs.value
        uri = self.baseuri + f"/compute_zones/{oid}/quotas/check"
        res = self.cmp_put(uri, {"quotas": {quota: int(value)}, "check_all": self.app.pargs.check_all}).get(
            "quotas", []
        )
        self.app.render(res, headers=["quota", "default", "unit"], details=True)

    @ex(
        help=_("set provider computes zone quota"),
        description=_("set provider computes zone quota"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["quota"],
                    {
                        "help": _("compute zone quota ex. database.instances"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["value"],
                    {
                        "help": _("compute zone quota value ex. 3"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def compute_zone_quota_set(self):
        oid = self.app.pargs.id
        quota = self.app.pargs.quota
        value = self.app.pargs.value
        try:
            value = int(value)
        except:
            pass
        uri = self.baseuri + f"/compute_zones/{oid}/quotas"
        self.cmp_put(uri, {"quotas": {quota: value}}).get("quotas", [])
        self.app.render(
            {"msg": f"set compute zone {oid} quota {quota}: {value}"},
            maxsize=200,
        )

    @ex(
        help=_("get compute zone configured backup jobs"),
        description=_("get compute zone configured backup jobs"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-hypervisor"],
                    {
                        "help": _("hypervisor name: vsphere, openstack, all"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-job"],
                    {
                        "help": _("backup job id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def compute_zone_backup_job_get(self):
        oid = self.app.pargs.id
        hypervisor = self.app.pargs.hypervisor
        job_id = self.app.pargs.job
        if job_id is not None:
            uri = f"{self.baseuri}/compute_zones/{oid}/backup/jobs/{job_id}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("job")
                instances = res.pop("instances", [])
                self.app.render(res, details=True)
                #avz = self.__get_availability_zones(oid)
                self.c("\ninstances", "underline")
                self.app.render(
                    instances,
                    fields=["id", "name", "state"],
                    headers=["id", "name", "state"],
                )
            else:
                self.app.render(res, details=True)
        else:
            uri = f"{self.baseuri}/compute_zones/{oid}/backup/jobs"
            data = {"hypervisor": hypervisor}
            res = self.cmp_get(uri, data)
            jobs = res.get("jobs")
            headers = [
                "id",
                "name",
                "site",
                "hypervisor",
                "resource_type",
                "created",
                "updated",
                "instances",
                "usage",
                "status",
                "schedule",
            ]
            fields = [
                "id",
                "name",
                "site",
                "hypervisor",
                "resource_type",
                "created",
                "updated",
                "instances",
                "usage",
                "status",
                "schedule.enabled",
            ]
            self.app.render(jobs, headers=headers, fields=fields)

    @ex(
        help=_("add compute zone backup job"),
        description=_("add compute zone backup job"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("job name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["site"],
                    {
                        "help": _("availability zone name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["instances"],
                    {
                        "help": _("comma separated list of instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-hypervisor"],
                    {
                        "help": _("hypervisor like openstack or vsphere [openstack]"),
                        "action": "store",
                        "type": str,
                        "default": "openstack",
                    },
                ),
                (
                    ["-hypervisor_tag"],
                    {
                        "help": _("hypervisor tag [default]"),
                        "action": "store",
                        "type": str,
                        "default": "default",
                    },
                ),
                (
                    ["-resource_type"],
                    {
                        "help": _("type of resource managed by job. Can be: ComputeInstance [ComputeInstance]"),
                        "action": "store",
                        "type": str,
                        "default": "ComputeInstance",
                    },
                ),
                (
                    ["-fullbackup_interval"],
                    {
                        "help": _("interval between full backup [2]"),
                        "action": "store",
                        "type": int,
                        "default": 2,
                    },
                ),
                (
                    ["-restore_points"],
                    {
                        "help": _("number of restore points to retain [4]"),
                        "action": "store",
                        "type": int,
                        "default": 4,
                    },
                ),
                (
                    ["-start_date"],
                    {
                        "help": _("start date like dd/mm/yyyy [now]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-end_date"],
                    {
                        "help": _("end date like dd/mm/yyyy [empty]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-start_time"],
                    {
                        "help": _("start time like 0:00 AM [00:00 AM]"),
                        "action": "store",
                        "type": str,
                        "default": "0:00 AM",
                    },
                ),
                (
                    ["-interval"],
                    {
                        "help": _("job interval like 24hrs [24hrs]"),
                        "action": "store",
                        "type": str,
                        "default": "24hrs",
                    },
                ),
                (
                    ["-timezone"],
                    {
                        "help": _("job timezone [Europe/Rome]"),
                        "action": "store",
                        "type": str,
                        "default": "Europe/Rome",
                    },
                ),
                (
                    ["-job_type"],
                    {
                        "help": _("job type. Can be: Parallel or Serial [Parallel]"),
                        "action": "store",
                        "type": str,
                        "default": "Parallel",
                    },
                ),
            ]
        ),
    )
    def compute_zone_backup_job_add(self):
        oid = self.app.pargs.id
        start_date = self.app.pargs.start_date
        uri = f"{self.baseuri}/compute_zones/{oid}/backup/jobs"
        if start_date is None:
            now = datetime.today()
            start_date = f"{now.day}/{now.month}/{now.year}"
        data = {
            "name": self.app.pargs.name,
            "site": self.app.pargs.site,
            "hypervisor": self.app.pargs.hypervisor,
            "hypervisor_tag": self.app.pargs.hypervisor_tag,
            "resource_type": self.app.pargs.resource_type,
            "fullbackup_interval": self.app.pargs.fullbackup_interval,
            "restore_points": self.app.pargs.restore_points,
            "start_date": start_date,
            "end_date": self.app.pargs.end_date,
            "start_time": self.app.pargs.start_time,
            "interval": self.app.pargs.interval,
            "timezone": self.app.pargs.timezone,
            "job_type": self.app.pargs.job_type,
            "instances": self.app.pargs.instances.split(","),
        }
        res = self.cmp_post(uri, data=data)
        job = res.get("job")
        self.app.render({"msg": f"add backup job {job}"})

    @ex(
        help=_("update compute zone backup job"),
        description=_("update compute zone backup job"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["job"],
                    {"help": _("job id"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-name"],
                    {
                        "help": _("job name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-instances"],
                    {
                        "help": _("comma separated list of <instance id>:<add/del>"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-fullbackup_interval"],
                    {
                        "help": _("interval between full backup"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-restore_points"],
                    {
                        "help": _("number of restore points to retain"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-start_date"],
                    {
                        "help": _("start date like dd/mm/yyyy"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-end_date"],
                    {
                        "help": _("end date like dd/mm/yyyy"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-start_time"],
                    {
                        "help": _("start time like 0:00 AM"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-interval"],
                    {
                        "help": _("job interval like 24hrs"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-timezone"],
                    {
                        "help": _("job timezone"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-job_type"],
                    {
                        "help": _("job type. Can be: Parallel or Serial"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": _("if true enable job"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def compute_zone_backup_job_update(self):
        oid = self.app.pargs.id
        job = self.app.pargs.job
        uri = f"{self.baseuri}/compute_zones/{oid}/backup/jobs/{job}"
        data = {}
        keys = [
            "name",
            "fullbackup_interval",
            "restore_points",
            "start_date",
            "end_date",
            "start_time",
            "interval",
            "timezone",
            "job_type",
            "enabled",
        ]
        for key in keys:
            self.add_field_from_pargs_to_data(key, data, key, reject_value=None, format=None)
        instances = self.app.pargs.instances
        if instances is not None:
            inst = []
            instances = instances.split(",")
            for instance in instances:
                instance_id, action = instance.split(":")
                if action not in ["add", "del"]:
                    raise Exception(f"action {action} is not permitted")
                inst.append({"instance": instance_id, "action": action})
            data["instances"] = inst

        res = self.cmp_put(uri, data=data)
        job = res.get("job")
        self.app.render({"msg": f"update backup job {job}"})

    @ex(
        help=_("delete compute zone backup job"),
        description=_("delete compute zone backup job"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["job"],
                    {"help": _("job id"), "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def compute_zone_backup_job_del(self):
        oid = self.app.pargs.id
        job = self.app.pargs.job
        uri = f"{self.baseuri}/compute_zones/{oid}/backup/jobs/{job}"
        self.cmp_delete(uri, entity=f"backup job {job}")

    @ex(
        help=_("get compute zone backup job restore points"),
        description=_("get compute zone backup job restore points"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["job"],
                    {
                        "help": _("backup job id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-restore_point"],
                    {
                        "help": _("backup restore point id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def compute_zone_backup_restore_point_get(self):
        oid = self.app.pargs.id
        job_id = self.app.pargs.job
        restore_point_id = self.app.pargs.restore_point
        if restore_point_id is not None:
            uri = f"{self.baseuri}/compute_zones/{oid}/backup/restore_points"
            res = self.cmp_get(uri, data={"job_id": job_id, "restore_point_id": restore_point_id})

            if self.is_output_text():
                res = res.get("restore_points")
                if len(res) > 0:
                    res = res[0]
                    metadata = res.pop("metadata", [])
                    instances = res.pop("instances", [])
                    self.app.render(res, details=True)

                    self.c("\nmetadata", "underline")
                    fields = ["id", "created", "key", "value"]
                    headers = ["id", "created", "key", "value"]
                    self.app.render(metadata, fields=fields, headers=headers)

                    self.c("\ninstances", "underline")
                    self.app.render(
                        instances,
                        fields=["id", "name", "state"],
                        headers=["id", "name", "state"],
                    )
            else:
                self.app.render(res, details=True)
        else:
            uri = f"{self.baseuri}/compute_zones/{oid}/backup/restore_points"
            res = self.cmp_get(uri, data={"job_id": job_id})
            restore_points = res.get("restore_points")
            headers = [
                "id",
                "name",
                "site",
                "hypervisor",
                "resource_type",
                "created",
                "type",
                "status",
            ]
            fields = [
                "id",
                "name",
                "site",
                "hypervisor",
                "resource_type",
                "created",
                "type",
                "status",
            ]
            self.app.render(restore_points, headers=headers, fields=fields)

    @ex(
        help=_("add compute zone backup job restore point"),
        description=_("add compute zone backup job restore point"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["job"],
                    {
                        "help": _("backup job id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("restore point name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("restore point description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-full"],
                    {
                        "help": _("if true create a full restore point, otherwise make an incremental"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
    )
    def compute_zone_backup_restore_point_add(self):
        oid = self.app.pargs.id
        job_id = self.app.pargs.job
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        full = str2bool(self.app.pargs.full)
        if desc is None:
            desc = name
        uri = f"{self.baseuri}/compute_zones/{oid}/backup/restore_points"
        data = {"job_id": job_id, "name": name, "desc": desc, "full": full}
        self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add backup job {job_id} restore point"})

    @ex(
        help=_("delete compute zone backup job restore point"),
        description=_("delete compute zone backup job restore point"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["job"],
                    {
                        "help": _("backup job id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["restore_point"],
                    {
                        "help": _("restore point id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def compute_zone_backup_restore_point_del(self):
        oid = self.app.pargs.id
        job_id = self.app.pargs.job
        restore_point_id = self.app.pargs.restore_point
        uri = f"{self.baseuri}/compute_zones/{oid}/backup/restore_points"
        data = {"job_id": job_id, "restore_point_id": restore_point_id}
        self.cmp_delete(uri, data=data)
        self.app.render({"msg": f"delete backup job {job_id} restore point"})

    #
    # vpc
    #
    @ex(
        help=_("get provider vpc"),
        description=_("get provider vpc(s)"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {"help": _("vpc id"), "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def vpc_interpod_next_subnet(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = f"/v2.0/nrs/provider/vpcs/{oid}/subnet/next"
        res = self.cmp_get(uri)
        self.app.render(res, details=True)

    @ex(
        help=_("get provider vpc"),
        description=_("get provider vpc(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {"help": _("vpc id"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("entity attributes"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-allocation-pools-details"],
                    {
                        "help": _("show the allocation pools details"),
                        "action": "store_true",
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def vpc_get(self):
        oid = getattr(self.app.pargs, "id", None)
        allocation_pools_details = str2bool(getattr(self.app.pargs, "allocation_pools_details", False))
        if oid is not None:
            uri = "/v2.0/nrs/provider/vpcs/" + oid
            data = {}
            if allocation_pools_details:
                data['allocation_pools_details'] = True
            res = self.cmp_get(uri, data)

            if self.is_output_text():
                res = res.get("vpc")
                networks = res.pop("networks", [])
                self.app.render(res, details=True)

                for i in networks:
                    i["subnets"] = []
                    configs = i.get("attributes").get("configs")
                    subnets = configs.get("subnets", None)
                    i["subnets"] = ""
                    for s in subnets:
                        allocable = s.get("allocable", False)
                        i["subnets"] += f"- cidr={s.get('cidr')}\n"
                        i["subnets"] += f" allocable={allocable}\n"
                        i["subnets"] += "  hypervisor\n"
                        for h in s.get("hypervisor", []):
                            vlanx = h.get('vxlan')
                            pool = h.get('pool')
                            i["subnets"] +=  f"  - {h.get('type')}: "
                            if vlanx is not None:
                                i["subnets"] += f"vxlan={h.get('vxlan')}, "
                            i["subnets"] += (
                                f"cidr={h.get('cidr')}, "
                                f"gateway={h.get('gateway')}"
                            )
                            if pool != "":
                                i["subnets"] += f", pool={pool}"
                                if allocation_pools_details and allocable:
                                    i["subnets"] += f", available_ips={h.get('available_ips')}"
                            i["subnets"] += "\n"

                self.c("\n\nnetworks", "underline")
                headers = ["id", "name", "avz", "vlan", "reuse", "state", "subnets"]
                fields = [
                    "id",
                    "name",
                    "availabilty_zone.name",
                    "attributes.configs.vlan",
                    "reuse",
                    "state",
                    "subnets",
                ]
                self.app.render(networks, headers=headers, fields=fields, maxsize=1000)
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            if allocation_pools_details:
                data += "&allocation_pools_details=true"

            uri = "/v2.0/nrs/provider/vpcs"

            def render(self, res, **kwargs):
                self.app.render(
                    res,
                    key="vpcs",
                    headers=self._meta.vpc_headers,  # pylint: disable=E1101
                    fields=self._meta.vpc_fields,  # pylint: disable=E1101
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render, pagesize=50)

    @ex(
        help=_("add vpc"),
        description=_("add vpc"),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("vpc name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["container"],
                    {
                        "help": _("vpc container id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["compute_zone"],
                    {
                        "help": _("vpc compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["cidr"],
                    {
                        "help": _("vpc cidr"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("vpc type. Can shared or private"),
                        "action": "store",
                        "type": str,
                        "default": "shared",
                    },
                ),
            ]
        ),
    )
    def vpc_add(self):
        name = self.app.pargs.name
        data = {
            "name": name,
            "desc": name,
            "container": self.app.pargs.container,
            "compute_zone": self.app.pargs.compute_zone,
            "cidr": self.app.pargs.cidr,
            "type": self.app.pargs.type,
        }

        uri = "/v2.0/nrs/provider/vpcs"
        res = self.cmp_post(uri, data={"vpc": data})
        self.app.render({"msg": f"add vpc {res['uuid']}"})

    @ex(
        help=_("delete vpc"),
        description=_("delete vpc"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("vpc id"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def vpc_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = f"/v2.0/nrs/provider/vpcs/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"vpc {oid}")

    @ex(
        help=_("update vpc"),
        description=_("update vpc"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("vpc id"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def vpc_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = f"/v2.0/nrs/provider/vpcs/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update vpc {res['uuid']}"})

    @ex(
        help=_("add vpc network"),
        description=_("add vpc network"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("vpc id"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["type"],
                    {
                        "help": _("network type. Can be private or site"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-networks"],
                    {
                        "help": _("comma separated list of site network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-cidr"],
                    {
                        "help": _("private network cidr"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-avz"],
                    {
                        "help": _("private network availability zone"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-zone"],
                    {
                        "help": _("dns zone"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dns"],
                    {
                        "help": _("dns list"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def vpc_network_add(self):
        oid = self.app.pargs.id
        net_type = self.app.pargs.type
        if net_type == "site":
            networks = self.app.pargs.networks.split(",")
            data = {"site": [{"network": n} for n in networks]}
        elif net_type == "private":
            cidr = self.app.pargs.cidr
            avz = self.app.pargs.avz
            dns = self.app.pargs.dns
            zone = self.app.pargs.zone
            data = {
                "private": [
                    {
                        "cidr": cidr,
                        "availability_zone": avz,
                        "dns_search": zone,
                        "dns_nameservers": dns.split(","),
                    }
                ]
            }
        else:
            raise Exception(f"Invalid net type: {net_type}. Valid values are 'site' or 'private'")
        uri = f"/v2.0/nrs/provider/vpcs/{oid}/network"
        self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add {net_type} networks to vpc {oid}"})

    @ex(
        help=_("delete vpc network"),
        description=_("delete vpc network"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("vpc id"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["type"],
                    {
                        "help": _("network type. Can be private or site"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-networks"],
                    {
                        "help": _("comma separated list of site network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-cidr"],
                    {
                        "help": _("private network cidr"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-avz"],
                    {
                        "help": _("private network availability zone"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def vpc_network_del(self):
        oid = self.app.pargs.id
        net_type = self.app.pargs.type
        if net_type == "site":
            networks = self.app.pargs.networks.split(",")
            data = {"site": [{"network": n} for n in networks]}
        elif net_type == "private":
            cidr = self.app.pargs.cidr
            avz = self.app.pargs.avz
            data = {"private": [{"cidr": cidr, "availability_zone": avz}]}
        else:
            raise Exception("network type can be only private or site")
        uri = f"/v2.0/nrs/provider/vpcs/{oid}/network"
        self.cmp_delete(uri, data=data, entity=f"{net_type} network")
        self.app.render({"msg": f"delete {net_type} networks to vpc {oid}"})

    #
    # security group
    #
    @ex(
        help=_("get provider security group"),
        description=_("get provider security group(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("security_group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vpc"],
                    {"help": _("vpc id"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-instance"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("entity attributes"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def sg_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = self.baseuri + f"/security_groups/{oid}"
            res = self.cmp_get(uri).get("security_group")

            if self.is_output_text():
                rules = res.pop("rules", [])
                instances = res.pop("instances", [])
                self.app.render(res, details=True)

                self.c("\nrules", "underline")
                headers = [
                    "id",
                    "name",
                    "proto",
                    "subproto",
                    "port",
                    "src-type",
                    "src",
                    "dst-type",
                    "dst",
                    "state",
                    "reserved",
                ]
                fields = [
                    "uuid",
                    "name",
                    "attributes.configs.service.protocol",
                    "attributes.configs.service.subprotocol",
                    "attributes.configs.service.port",
                    "attributes.configs.source.type",
                    "attributes.configs.source.value",
                    "attributes.configs.destination.type",
                    "attributes.configs.destination.value",
                    "state",
                    "attributes.reserved",
                ]
                self.app.render(rules, headers=headers, fields=fields, maxsize=400)

                self.c("\ninstances", "underline")
                self.app.render(
                    instances,
                    headers=self._meta.instance_headers,  # pylint: disable=E1101
                    fields=self._meta.instance_fields,  # pylint: disable=E1101
                    maxsize=400,
                )
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags", "instance", "vpc"]
            mappings = {"name": lambda n: "%" + n + "%"}
            aliases = {"parent": "parent_list"}
            data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
            uri = f"{self.baseuri}/security_groups"

            def render(self, res, **kwargs):
                transform = {"rules": len}
                self.app.render(
                    res,
                    key="security_groups",
                    headers=self._meta.security_group_headers,  # pylint: disable=E1101
                    fields=self._meta.security_group_fields,  # pylint: disable=E1101
                    transform=transform,
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render, pagesize=20)

    @ex(
        help=_("check security groups contain ingress rule from zabbix proxy"),
        description=_("check security groups contain ingress rule from zabbix proxy"),
        arguments=PARGS(
            [
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def sg_zabbix_is_enabled(self):
        params = ["name", "desc", "parent", "state", "tags", "instance", "vpc"]
        mappings = {"name": lambda n: "%" + n + "%"}
        aliases = {"parent": "parent_list"}
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = f"{self.baseuri}/security_groups"
        res = self.cmp_get(uri, data=data)
        transform = {"rules": len}
        headers = [
            "id",
            "uuid",
            "name",
            "state",
            "SiteTorino01",
            "SiteTorino02",
            "SiteVercelli01",
        ]
        fields = [
            "id",
            "uuid",
            "name",
            "state",
            "zabbix_rules.SiteTorino01",
            "zabbix_rules.SiteTorino02",
            "zabbix_rules.SiteVercelli01",
        ]
        self.app.render(
            res,
            key="security_groups",
            headers=headers,
            fields=fields,
            transform=transform,
        )

    @ex(
        help=_("enable security group ingress from zabbix proxy"),
        description=_("enable security group ingress from zabbix proxy"),
        arguments=PARGS(
            [
                (["id"], {"help": _("security group id"), "action": "store", "type": str}),
                (
                    ["availability_zone"],
                    {
                        "help": _("availability zone name. Es. SiteTorino01"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def sg_zabbix_enable(self):
        oid = self.app.pargs.id
        availability_zone = self.app.pargs.availability_zone
        data = {"availability_zone": availability_zone}
        uri = f"{self.baseuri}/security_groups/{oid}/zabbix"
        self.cmp_post(uri, data=data)

    @ex(
        help=_("disable security group ingress from zabbix proxy"),
        description=_("disable security group ingress from zabbix proxy"),
        arguments=PARGS(
            [
                (["id"], {"help": _("security group id"), "action": "store", "type": str}),
                (
                    ["availability_zone"],
                    {
                        "help": _("availability zone name. Es. SiteTorino01"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def sg_zabbix_disable(self):
        oid = self.app.pargs.id
        availability_zone = self.app.pargs.availability_zone
        data = {"availability_zone": availability_zone}
        uri = f"{self.baseuri}/security_groups/{oid}/zabbix"
        self.cmp_delete(
            uri,
            data=data,
            entity=f"sg zabbix rule for availability zone {availability_zone}",
        )

    @ex(
        help=_("check provider security group"),
        description=_("check provider security group(s)"),
        arguments=PARGS(),
    )
    def sg_check(self):
        # get rules
        data = {"parent": "f2716a97-97a1-4cb8-bce3-7a411326bcf6", "size": -1}
        uri = f"{self.baseuri}/rules"
        res = self.cmp_get(uri, data=data).get("rules")
        rule_idx = {r["id"]: r for r in res}
        # print(rule_list)

        # self.app.render(res, key='rules', headers=self._meta.rule_headers, fields=self._meta.rule_fields)

        sg_rule_idx = {}
        oids = [
            146984,
            145866,
            143148,
            143138,
            143056,
            142853,
            142758,
            142702,
            142075,
            141988,
            141393,
            141300,
        ]
        for oid in oids:
            uri = self.baseuri + f"/security_groups/{oid}"
            res = self.cmp_get(uri).get("security_group")
            rules = res.pop("rules", [])
            for rule in rules:
                sg_rule_idx[rule["id"]] = None
        # print(list(rule_idx.keys()))

        old_rules = set(list(rule_idx.keys())) - set(list(sg_rule_idx.keys()))

        check_sgs = {}
        for old_rule_id in old_rules:
            old_rule = rule_idx.get(old_rule_id)
            # print(rule_idx.get(old_rule))
            source = dict_get(old_rule, "attributes.configs.source")
            destination = dict_get(old_rule, "attributes.configs.destination")
            if source.get("type") == "SecurityGroup":
                check_sgs[source.get("value")] = None
            if destination.get("type") == "SecurityGroup":
                check_sgs[destination.get("value")] = None
        print(list(check_sgs.keys()))

    @ex(
        help=_("add security group"),
        description=_("add security group"),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("security group name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["vpc"],
                    {
                        "help": _("parent vpc id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def sg_add(self):
        name = self.app.pargs.name
        vpc = self.app.pargs.vpc
        data = {
            "security_group": {
                "container": self.get_container(),
                "name": name,
                "desc": name,
                "vpc": vpc,
            }
        }
        uri = self.baseuri + "/security_groups"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add security_group {res['uuid']}"})

    @ex(
        help=_("delete security group"),
        description=_("delete security group"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("security_group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def sg_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = self.baseuri + f"/security_groups/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"security_group {oid}")

    #
    # rule
    #
    @ex(
        help=_("get provider rule"),
        description=_("get provider rule(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("rule id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-source"],
                    {
                        "help": _("rule source"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-destination"],
                    {
                        "help": _("rule destination"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-security_groups"],
                    {
                        "help": _("search rule by security group"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-service"],
                    {
                        "help": _("service"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def rule_get(self):
        if self.app.pargs.security_groups and (
            self.app.pargs.source is not None
            or self.app.pargs.destination is not None
            or self.app.pargs.service is not None
        ):
            self.app.warning("Security group filter will override source, destination and service filters")

        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = self.baseuri + f"/rules/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("rule")
                attributes = res.get("attributes", [])
                configs = attributes.pop("configs", [])
                source = configs.pop("source", [])
                dest = configs.pop("destination", [])
                service = configs.pop("service", [])
                self.app.render(res, details=True)

                fromto = []
                if not isinstance(source, list):
                    source = [source]
                for i in source:
                    i["fromto"] = "source"
                fromto.extend(source)
                if not isinstance(dest, list):
                    dest = [dest]
                for i in dest:
                    i["fromto"] = "destination"
                fromto.extend(dest)
                self.c("\n\nsource - destination", "underline")
                self.app.render(fromto, headers=["fromto", "type", "value"], maxsize=200)
                self.c("\n\nservice", "underline")
                self.app.render(service, headers=["protocol", "subprotocol", "port"], maxsize=200)
            else:
                self.app.render(res, details=True)
        else:
            params = [
                "name",
                "desc",
                "parent",
                "source",
                "destination",
                "state",
                "security_groups",
                "service",
            ]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/rules"

            def render(self, res, **kwargs):
                self.app.render(
                    res,
                    key="rules",
                    headers=self._meta.rule_headers,  # pylint: disable=E1101
                    fields=self._meta.rule_fields,  # pylint: disable=E1101
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render)

    @ex(
        help=_("add rule"),
        description=_("add rule"),
        example=(
            "beehive res-provider rule-add SG-test-xxx <uuid compute zone> "
            "Cidr:xx.xx.xx.xx/32 SecurityGroup:<uuid sg resource> "
            "-reserved True -orchestrators openstack"
        ),
        arguments=ARGS(
            [
                (["name"], {"help": _("rule id"), "action": "store", "type": str}),
                (
                    ["compute_zone"],
                    {"help": _("compute zone id"), "action": "store", "type": str},
                ),
                (
                    ["source"],
                    {
                        "help": _(
                            "rule source. Syntax <type>:<value>. type can be SecurityGroup, Cidr. value can be "
                            "security group id, cidr like ###.###.###.###/24"
                        ),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["dest"],
                    {
                        "help": _(
                            "rule destination. Syntax <type>:<value>. type can be SecurityGroup, Cidr. value can be"
                            " security group id, cidr like ###.###.###.###/24"
                        ),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-proto"],
                    {
                        "help": _(
                            "can be  6 [tcp], 17 [udp], 1 [icmp], * [all]. "
                            "If use icmp specify also subprotocol. [default=*]"
                        ),
                        "action": "store",
                        "type": str,
                        "default": "*",
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": _(
                            "can be an integer between 0 and 65535 or a range with start and end in the same "
                            "interval. Range format is <start>-<end>. Use * for all ports. [default=*]"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subproto"],
                    {
                        "help": _("icmp subprotocol. ex. 8 for echo request"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-reserved"],
                    {
                        "help": _("reserved: True/False"),
                        "action": "store",
                        "type": bool,
                        "default": None,
                    },
                ),
                (
                    ["-log"],
                    {
                        "help": _("True/False to enable/disable rule logging"),
                        "action": "store",
                        "type": bool,
                        "default": None,
                    },
                ),
                (
                    ["-orchestrators"],
                    {
                        "help": _("orchestrators comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def rule_add(self):
        name = self.app.pargs.name
        zone = self.app.pargs.compute_zone
        source = self.app.pargs.source.split(":")
        dest = self.app.pargs.dest.split(":")
        port = self.app.pargs.port
        proto = self.app.pargs.proto
        subproto = self.app.pargs.subproto
        if proto == "*":
            port = "*"

        rule = {
            "container": self.get_container(),
            "name": name,
            "desc": name,
            "compute_zone": zone,
            "source": {"type": source[0], "value": source[1]},
            "destination": {"type": dest[0], "value": dest[1]},
            "service": {"protocol": proto},
        }

        reserved = self.app.pargs.reserved
        if reserved is not None:
            rule.update({"reserved": reserved})

        orchestrators: str = self.app.pargs.orchestrators
        if orchestrators is not None:
            rule_orchestrator_types = orchestrators.split(",")
            rule.update({"rule_orchestrator_types": rule_orchestrator_types})

        logging = self.app.pargs.log
        if logging is not None:
            rule.update({"logging": logging})

        data = {"rule": rule}
        if port is not None:
            data["rule"]["service"]["port"] = port
        if proto == "1" and subproto is not None:
            data["rule"]["service"]["subprotocol"] = subproto

        uri = f"{self.baseuri}/rules"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add rule {res['uuid']}"})

    @ex(
        help=_("delete rule"),
        description=_("delete rule"),
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("rule id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def rule_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        parent = self.app.pargs.parent

        if parent is not None:
            data = urlencode({"parent": parent, "size": -1}, doseq=True)
            uri = f"{self.baseuri}/rules"
            res = self.cmp_get(uri, data=data)
            # self.app.render(res, key='rules', headers=self._meta.rule_headers, fields=self._meta.rule_fields)

            for item in res.get("rules"):
                uri = self.baseuri + f"/rules/{item['id']}"
                if force is True:
                    uri += "?force=true"
                self.cmp_delete(uri, entity=f"rule {item['id']}")
        elif oid is not None:
            uri = self.baseuri + f"/rules/{oid}"
            if force is True:
                uri += "?force=true"
            self.cmp_delete(uri, entity=f"rule {oid}")

    #
    # bastion
    #
    @ex(
        help=_("get provider bastion host(s)"),
        description=_("get provider bastion host(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("bastion id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("bastion name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("bastion description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-compute_zone"],
                    {
                        "help": _("bastion zone"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                # (['-state'], {'help': 'instance state', 'action': 'store', 'type': str, 'default': None}),
                # (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
                # (['-hypervisor'], {'help': 'instance hypervisor', 'action': 'store', 'type': str, 'default': None}),
                # (['-tags'], {'help': 'instance tags', 'action': 'store', 'type': str, 'default': None})
            ]
        ),
    )
    def bastion_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = self.baseuri + f"/bastions/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                data = res.get("bastion")
                avz = data.pop("availability_zone", None)
                flavor = data.pop("flavor", {})
                image = data.pop("image", {})
                vpcs = data.pop("vpcs", [])
                sgs = data.pop("security_groups", [])
                storage = data.pop("block_device_mapping", [])
                self.app.render(data, details=True)

                self.c("\nAvailability zone", "underline")
                self.app.render(avz, headers=["uuid", "name", "state"])
                self.c("\nFlavor", "underline")
                self.app.render(
                    flavor,
                    headers=["vcpus", "memory", "disk", "disk_iops", "bandwidth"],
                )
                self.c("\nImage", "underline")
                self.app.render(image, headers=["os", "os_ver"])
                self.c("\nSecurity groups", "underline")
                self.app.render(sgs, headers=["uuid", "name"])
                self.c("\nNetworks", "underline")
                self.app.render(vpcs, headers=["uuid", "name", "fixed_ip.ip"])
                self.c("\nBlock device mapping", "underline")
                self.app.render(
                    storage,
                    headers=[
                        "id",
                        "name",
                        "boot_index",
                        "bootable",
                        "encrypted",
                        "volume_size",
                    ],
                )
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "compute_zone"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/bastions"
            res = self.cmp_get(uri, data=data)
            if self.is_output_text():
                for item in res.get("bastions"):
                    image = item.get("image", {})
                    item["os"] = f"{image.get('os', '')} {image.get('os_ver', '')}"
                    block_device_mapping = item.get("block_device_mapping", [])
                    item["volume"] = {"num": len(block_device_mapping)}
                    if item["volume"]["num"] > 0:
                        item["volume"]["size"] = sum([i.get("volume_size", None) for i in block_device_mapping])

            self.app.render(
                res,
                key="bastions",
                headers=self._meta.instance_headers,  # pylint: disable=E1101
                fields=self._meta.instance_fields,  # pylint: disable=E1101
            )

    @ex(
        help=_("add provider bastion host"),
        description=_("add provider bastion host"),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("bastion name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["compute_zone"],
                    {
                        "help": _("bastion name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-availability_zone"],
                    {
                        "help": _("bastion name"),
                        "action": "store",
                        "type": str,
                        "default": "SiteVercelli01",
                    },
                ),
                (
                    ["-pwd"],
                    {
                        "help": _("bastion admin password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-key_name"],
                    {
                        "help": _("bastion admin ssh key"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-flavor"],
                    {
                        "help": _("bastion flavor"),
                        "action": "store",
                        "type": str,
                        "default": "vm.s1.micro",
                    },
                ),
                (
                    ["-volume_flavor"],
                    {
                        "help": _("bastion volume flavor"),
                        "action": "store",
                        "type": str,
                        "default": "vol.default",
                    },
                ),
                (
                    ["-image"],
                    {
                        "help": _("bastion image"),
                        "action": "store",
                        "type": str,
                        "default": "Centos7",
                    },
                ),
                (
                    ["-acl"],
                    {
                        "help": _("comma separated list of network acl"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
            ]
        ),
    )
    def bastion_add(self):
        name = self.app.pargs.name
        compute_zone = self.app.pargs.compute_zone
        availability_zone = self.app.pargs.availability_zone
        flavor = self.app.pargs.flavor
        volume_flavor = self.app.pargs.volume_flavor
        image = self.app.pargs.image
        pwd = self.app.pargs.pwd
        key_name = self.app.pargs.key_name
        acl = self.app.pargs.acl.split(",")
        data = {
            "container": "ResourceProvider01",
            "name": name,
            "desc": name,
            "compute_zone": compute_zone,
            "availability_zone": availability_zone,
            "flavor": flavor,
            "volume_flavor": volume_flavor,
            "image": image,
        }
        if pwd is not None:
            data["admin_pass"] = pwd
        if key_name is not None:
            data["key_name"] = key_name
        if acl is not None:
            data["acl"] = [{"subnet": a} for a in acl]

        uri = self.baseuri + "/bastions"
        res = self.cmp_post(uri, data={"bastion": data})
        self.app.render({"msg": f"add bastion {res['uuid']}"})

    @ex(
        help=_("patch bastion"),
        description=_("patch bastion"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("bastion id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def bastion_patch(self):
        oid = self.app.pargs.id
        uri = self.baseuri + f"/bastions/{oid}"
        res = self.cmp_patch(uri, data="")
        self.app.render({"msg": f"patch bastion {res['uuid']}"})

    @ex(
        help=_("delete bastion"),
        description=_("delete bastion"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("bastion id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def bastion_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = self.baseuri + f"/bastions/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"bastion {oid}")

    @ex(
        help=_("start bastion"),
        description=_("start bastion"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("bastion id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def bastion_start(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/bastions/{oid}/actions"
        data = {"action": {"start": True}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"start bastion {oid}"})

    @ex(
        help=_("stop bastion"),
        description=_("stop bastion"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("bastion id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def bastion_stop(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/bastions/{oid}/actions"
        data = {"action": {"stop": True}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"stop bastion {oid}"})

    @ex(
        help=_("set bastion flavor"),
        description=_("set bastion flavor"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("bastion id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["flavor"],
                    {
                        "help": _("flavor id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def bastion_flavor_set(self):
        oid = self.app.pargs.id
        flavor = self.app.pargs.flavor
        uri = f"{self.baseuri}/bastions/{oid}/actions"
        data = {"action": {"set_flavor": {"flavor": flavor}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"set bastion {oid} flavor {flavor}"})

    @ex(
        help=_("add bastion security group"),
        description=_("add bastion security group"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("bastion id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["security_group"],
                    {
                        "help": _("security group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def bastion_sg_add(self):
        oid = self.app.pargs.id
        security_group = self.app.pargs.security_group
        uri = f"{self.baseuri}/bastions/{oid}/actions"
        data = {"action": {"add_security_group": {"security_group": security_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add bastion {oid} security group {security_group}"})

    @ex(
        help=_("remove bastion security group"),
        description=_("remove bastion security group"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("bastion id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["security_group"],
                    {
                        "help": _("security group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def bastion_sg_del(self):
        oid = self.app.pargs.id
        security_group = self.app.pargs.security_group
        uri = f"{self.baseuri}/bastions/{oid}/actions"
        data = {"action": {"del_security_group": {"security_group": security_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"remove bastion {oid} security group {security_group}"})

    @ex(
        help=_("install bastion zabbix proxy"),
        description=_("install bastion zabbix proxy"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("bastion id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def bastion_zabbix_proxy_install(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/bastions/{oid}/actions"
        data = {"action": {"install_zabbix_proxy": True}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"install zabbix proxy on bastion {oid}"})

    @ex(
        help=_("register bastion zabbix proxy"),
        description=_("register bastion zabbix proxy"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("bastion id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def bastion_zabbix_proxy_register(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/bastions/{oid}/actions"
        data = {"action": {"register_zabbix_proxy": True}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"register zabbix proxy on bastion {oid}"})

    @ex(
        help=_("install shipper on bastion to enable resource monitoring"),
        description=_("install shipper on bastion to enable resource monitoring"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("bastion id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-hostgroup"],
                    {
                        "help": _("account hostgroup written as Org.Div.Acc"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def bastion_monit_enable(self):
        oid = self.app.pargs.id
        host_group = self.app.pargs.hostgroup
        uri = f"{self.baseuri}/bastions/{oid}/actions"
        data = {"action": {"enable_monitoring": {"host_group": host_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"shipper installed, resource monitoring enabled on bastion {oid}"})

    @ex(
        help=_("install shipper on bastion to forward and centralize log data"),
        description=_("install shipper on bastion to forward and centralize log data"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("bastion id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def bastion_log_enable(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/bastions/{oid}/actions"
        data = {"action": {"enable_logging": True}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"shipper installed, log forwarding enabled on bastion {oid}"})

    #
    # instance
    #
    @ex(
        help=_("get provider instance"),
        description=_("get provider instance(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("instance name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("instance description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("instance parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("instance state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                # (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
                (
                    ["-hypervisor"],
                    {
                        "help": _("instance hypervisor"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("instance tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-image"],
                    {
                        "help": _("instance image"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-flavor"],
                    {
                        "help": _("instance flavor"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vpc"],
                    {
                        "help": _("instance vpc"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-security_group"],
                    {
                        "help": _("instance security group"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-hostinfo"],
                    {
                        "help": _("print list with hypervisor info"),
                        "action": "store",
                        "type": str,
                        "default": False,
                    },
                ),
                (
                    ["-availability_zone"],
                    {
                        "help": _("instance availability zone"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = self.baseuri + f"/instances/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                data: Dict = res.get("instance")
                avz = data.pop("availability_zone", [])
                flavor = data.pop("flavor", {})
                image = data.pop("image", {})
                vpcs = data.pop("vpcs", [])
                sgs = data.pop("security_groups", [])
                storage = data.pop("block_device_mapping", [])
                attributes = data.pop("attributes", [])
                self.app.render(data, details=True)

                self.c("\nConfig", "underline")
                uri = f"{self.baseuri}/instances/{data.get('uuid')}/manage"
                mgt = self.cmp_get(uri).get("is_managed", [])
                config = {
                    "is-managed": bool2str(mgt),
                    "backup-enabled": attributes.get("backup_enabled", False),
                    "monitoring-enabled": attributes.get("monitoring_enabled", False),
                    "logging-enabled": attributes.get("logging_enabled", False),
                }
                self.app.render(
                    config,
                    headers=[
                        "is-managed",
                        "backup-enabled",
                        "monitoring-enabled",
                        "logging-enabled",
                    ],
                )

                self.c("\nAvailability zone", "underline")
                self.app.render(avz, headers=["uuid", "name", "state"])

                self.c("\nFlavor", "underline")
                self.app.render(
                    flavor,
                    headers=[
                        "name",
                        "vcpus",
                        "memory",
                        "disk",
                        "disk_iops",
                        "bandwidth",
                    ],
                )
                self.c("\nImage", "underline")
                self.app.render(image, headers=["os", "os_ver"])
                self.c("\nSecurity groups", "underline")
                self.app.render(sgs, headers=["uuid", "name"])
                self.c("\nNetworks", "underline")
                self.app.render(vpcs, headers=["uuid", "name", "fixed_ip.ip"])
                self.c("\nBlock device mapping", "underline")
                self.app.render(
                    storage,
                    headers=[
                        "id",
                        "name",
                        "boot_index",
                        "bootable",
                        "encrypted",
                        "volume_size",
                    ],
                )
            else:
                self.app.render(res, details=True)
        else:
            hostinfo = str2bool(self.app.pargs.hostinfo)
            params = [
                "name",
                "desc",
                "parent",
                "state",
                "tags",
                "hypervisor",
                "image",
                "flavor",
                "vpc",
                "security_group",
                "availability_zone",
            ]
            mappings = {
                "name": lambda n: "%" + n + "%",
                "desc": lambda n: "%" + n + "%",
            }
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/instances"

            def render(self: 'BaseController', res, **kwargs):
                if self.is_output_text():
                    for item in res.get("instances"):
                        image = item.get("image", {})
                        item["os"] = f"{image.get('os', '')} {image.get('os_ver', '')}"
                        block_device_mapping = item.get("block_device_mapping", [])
                        item["volume"] = {"num": len(block_device_mapping)}
                        if item["volume"]["num"] > 0:
                            item["volume"]["size"] = sum(i.get("volume_size", None) for i in block_device_mapping)

                headers = self._meta.instance_headers  # pylint: disable=E1101
                fields = self._meta.instance_fields  # pylint: disable=E1101
                if hostinfo is True:
                    fields = [
                        "id",
                        "parent",
                        "name",
                        "availability_zone.name",
                        "hypervisor",
                        "attributes.host",
                        "attributes.host_group",
                        "runstate",
                        "os",
                        "vpcs.0.fixed_ip.ip",
                    ]
                    headers = [
                        "id",
                        "parent",
                        "name",
                        "av_zone",
                        "type",
                        "host",
                        "host_group",
                        "runstate",
                        "os",
                        "ip",
                    ]
                self.app.render(res, key="instances", headers=headers, fields=fields)

            res = self.cmp_get_pages(uri, data=data, fn_render=render, pagesize=10)

    @ex(
        help=_("add instance"),
        description=_("add instance"),
        arguments=ARGS(
            [
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def instance_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + "/instances"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add instance {res['uuid']}"})

    @ex(
        help=_("import instance"),
        description=_("import instance"),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("instance name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["physical_id"],
                    {
                        "help": _("physical resource id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": _("instance password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["image"],
                    {
                        "help": _("image id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["key_name"],
                    {
                        "help": _("ssh key name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-resolve"],
                    {
                        "help": _("if true add hostname in dns"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
                (
                    ["-manage"],
                    {
                        "help": _("if true add node in ssh"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
            ]
        ),
    )
    def instance_import(self):
        name = self.app.pargs.name
        physical_id = self.app.pargs.physical_id
        pwd = self.app.pargs.pwd
        image = self.app.pargs.image
        key_name = self.app.pargs.key_name
        resolve = str2bool(self.app.pargs.resolve)
        manage = str2bool(self.app.pargs.manage)

        config = {
            "container": "ResourceProvider01",
            "name": name,
            "desc": name,
            "physical_id": physical_id,
            "attribute": {},
            "resclass": "beehive_resource.plugins.provider.entity.instance.ComputeInstance",
            "configs": {
                "multi_avz": True,
                "admin_pass": pwd,
                "image": image,
                "key_name": key_name,
                "resolve": resolve,
                "manage": manage,
            },
        }
        uri = "/v1.0/nrs/entities/import"
        self.cmp_post(uri, data={"resource": config})
        self.app.render({"msg": f"import instance {name}"})

    @ex(
        help=_("patch instance"),
        description=_("patch instance"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def instance_patch(self):
        oid = self.app.pargs.id
        uri = self.baseuri + f"/instances/{oid}"
        res = self.cmp_patch(uri, data="")
        self.app.render({"msg": f"patch instance {res['uuid']}"})

    @ex(
        help=_("delete instance"),
        description=_("delete instance"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def instance_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = self.baseuri + f"/instances/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"instance {oid}")

    @ex(
        help=_("update instance"),
        description=_("update instance"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + f"/instances/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update instance {res['uuid']}"})

    @ex(
        help=_("check provider computes instance is managed by ssh module, has backup active, has monitor active"),
        description=_(
            "check provider computes instance is managed by ssh module, has backup active, has monitor active"
        ),
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def instance_config(self):
        oid = self.app.pargs.id

        if oid is None:
            # TODO possibly dead code. remove if unused
            data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
            uri = self.baseuri + "/instances"
            czs = self.cmp_get(uri, data=data)
        else:
            uri = self.baseuri + f"/instances/{oid}"
            czs = self.cmp_get(uri).get("instance", None)
            if czs is not None:
                czs = {
                    "instances": [czs],
                    "page": 0,
                    "count": 1,
                    "total": 1,
                    "sort": {"field": "id", "order": "DESC"},
                }
            print(czs)

        def query_item(cz):
            # get ssh management status
            uri = f"{self.baseuri}/instances/{cz.get('id')}/manage"
            mgt = self.cmp_get(uri).get("is_managed", [])
            res = {
                "is-managed": bool2str(mgt),
                "has-backup": "false",
                "has-monitor": "false",
            }
            return res

        tmpl = "{uuid:36.36} {name:40.40} {desc:40.40} {is-managed:20.20} {has-backup:20.20} {has-monitor:20.20}"
        headers = {
            "uuid": "id",
            "name": "name",
            "desc": "desc",
            "is-managed": "is-managed",
            "has-backup": "has-backup",
            "has-monitor": "has-monitor",
        }
        self.app.render(czs, "instances", query_item, tmpl=tmpl, headers=headers)

    @ex(
        help=_("enable provider computes instance management by ssh module"),
        description=_("enable provider computes instance management by ssh module"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ssh_key"],
                    {
                        "help": _("instance ssh key"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_manage(self):
        oid = self.app.pargs.id
        key = self.app.pargs.ssh_key

        data = {"manage": {"key": key}}
        uri = f"{self.baseuri}/instances/{oid}/manage"
        res = self.cmp_post(uri, data=data).get("manage", [])
        self.app.render({"msg": f"enable compute instance {oid} management with ssh node: {res}"})

    @ex(
        help=_("disable provider computes instance management by ssh module"),
        description=_("disable provider computes instance management by ssh module"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def instance_unmanage(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/instances/{oid}/manage"
        self.cmp_delete(uri)
        self.app.render({"msg": f"disable compute instance {oid} management"})

    @ex(
        help=_("run command on provider instance"),
        description=_("run command on provider instance(s)"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["command"],
                    {
                        "help": _("file name where is saved the command to run"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_command_run(self):
        oid = self.app.pargs.id
        command = self.app.pargs.command
        command = load_config(command)
        data = {"command": command}
        uri = self.baseuri + f"/instances/{oid}/command"
        res = self.cmp_put(uri, data=data)
        res = dict_get(res, "output")
        self.app.render(res, details=True)

    @ex(
        help=_("get compute instance console"),
        description=_("get compute instance console"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def instance_console_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/instances/{oid}/console"
        res = self.cmp_get(uri).get("console", {})
        self.app.render(res, details=True)
        # sh.firefox(res.get('url'))

    @ex(
        help=_("get compute instance backup info"),
        description=_("get compute instance backup info"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def instance_backup_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/instances/{oid}/backup/restore_points"
        res = self.cmp_get(uri)
        restore_points = res.pop("restore_points")
        self.app.render(res, details=True)
        self.c("\nrestore points", "underline")
        self.app.render(restore_points, headers=["id", "name", "desc", "type", "status", "created"])

    @ex(
        help=_("get compute instance backup restores"),
        description=_("get compute instance backup restores"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["restore_point"],
                    {
                        "help": _("restore point id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_backup_restore_get(self):
        oid = self.app.pargs.id
        sid = self.app.pargs.restore_point
        uri = f"{self.baseuri}/instances/{oid}/backup/restore_points/{sid}/restores"
        res = self.cmp_get(uri).get("restores", [])
        self.app.render(
            res,
            headers=[
                "id",
                "name",
                "time_taken",
                "size",
                "uploaded_size",
                "status",
                "progress_percent",
                "created",
            ],
        )

    @ex(
        help=_("restore compute instance from backup restore point"),
        description=_("restore compute instance from backup restore point"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["restore_point"],
                    {
                        "help": _("restore point id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("restored instance name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_backup_restore(self):
        oid = self.app.pargs.id
        restore_point = self.app.pargs.restore_point
        name = self.app.pargs.name
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {
            "action": {
                "restore_from_backup": {
                    "restore_point": restore_point,
                    "instance_name": name,
                }
            }
        }
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"restore compute instance {oid} from backup restore point {restore_point}"})

    @ex(
        help=_("add user to instance"),
        description=_("add user to instance"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": _("user password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ssh_key"],
                    {
                        "help": _("ssh key id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_user_add(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        pwd = self.app.pargs.pwd
        key = self.app.pargs.ssh_key
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"add_user": {"user_name": name, "user_pwd": pwd, "user_ssh_key": key}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add user {name} to instance {oid}"})

    @ex(
        help=_("delete user to instance"),
        description=_("delete user to instance"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_user_del(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"del_user": {"user_name": name}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"delete user {name} to instance {oid}"})

    @ex(
        help=_("delete user to instance"),
        description=_("delete user to instance"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": _("user password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_user_password_set(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        pwd = self.app.pargs.pwd
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"set_user_pwd": {"user_name": name, "user_pwd": pwd}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"set user {name} password to instance {oid}"})

    @ex(
        help=_("start instance"),
        description=_("start instance"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-schedule"],
                    {
                        "help": _(
                            "schedule definition. Pass as json file using crontab or timedelta syntax. "
                            'Ex. {"type": "timedelta", "minutes": 1}'
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_start(self):
        oid = self.app.pargs.id
        schedule = self.app.pargs.schedule
        uri = f"{self.baseuri}/instances/{oid}/actions"
        if schedule is None:
            data = {"action": {"start": True}}
            self.cmp_put(uri, data=data)
            self.app.render({"msg": f"start instance {oid}"})
        else:
            schedule = load_config(schedule)
            data = {"action": {"start": True}, "schedule": schedule}
            self.cmp_put(uri, data=data)
            self.app.render({"msg": f"schedule start instance {oid}"})

    @ex(
        help=_("stop instance"),
        description=_("stop instance"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-schedule"],
                    {
                        "help": _(
                            "schedule definition. Pass as json file using crontab or timedelta syntax. "
                            'Ex. {"type": "timedelta", "minutes": 1}'
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_stop(self):
        oid = self.app.pargs.id
        schedule = self.app.pargs.schedule
        uri = f"{self.baseuri}/instances/{oid}/actions"
        if schedule is None:
            data = {"action": {"stop": True}}
            self.cmp_put(uri, data=data)
            self.app.render({"msg": f"stop instance {oid}"})
        else:
            schedule = load_config(schedule)
            data = {"action": {"stop": True}, "schedule": schedule}
            self.cmp_put(uri, data=data)
            self.app.render({"msg": f"schedule stop instance {oid}"})

    @ex(
        help=_("reboot instance"),
        description=_("reboot instance"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-schedule"],
                    {
                        "help": _(
                            "schedule definition. Pass as json file using crontab or timedelta syntax. "
                            'Ex. {"type": "timedelta", "minutes": 1}'
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_reboot(self):
        oid = self.app.pargs.id
        schedule = self.app.pargs.schedule
        uri = f"{self.baseuri}/instances/{oid}/actions"
        if schedule is None:
            data = {"action": {"reboot": True}}
            self.cmp_put(uri, data=data)
            self.app.render({"msg": f"reboot instance {oid}"})
        else:
            schedule = load_config(schedule)
            data = {"action": {"reboot": True}, "schedule": schedule}
            self.cmp_put(uri, data=data)
            self.app.render({"msg": f"schedule reboot instance {oid}"})

    @ex(
        help=_("migrate instance"),
        description=_("migrate instance"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def instance_migrate(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"migrate": {"live": True}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"migrate instance {oid}"})

    @ex(
        help=_("set instance flavor"),
        description=_("set instance flavor"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["flavor"],
                    {
                        "help": _("flavor id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_flavor_set(self):
        oid = self.app.pargs.id
        flavor = self.app.pargs.flavor
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"set_flavor": {"flavor": flavor}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"set instance {oid} flavor {flavor}"})

    @ex(
        help=_("set instance volume flavor"),
        description=_("set instance volume flavor"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-volume"],
                    {
                        "help": _("volume id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-flavor"],
                    {
                        "help": _("flavor id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_volume_flavor_set(self):
        oid = self.app.pargs.id
        flavor = self.app.pargs.flavor
        volume = self.app.pargs.volume

        # list volumes
        uri = self.baseuri + f"/instances/{oid}"
        res = self.cmp_get(uri)
        data = res.get("instance")
        storage = data.pop("block_device_mapping", [])
        #resp = []
        for block in storage:
            uri = self.baseuri + f"/volumes/{block['id']}"
            res = self.cmp_get(uri).get("volume", {})
            block["flavor"] = dict_get(res, "flavor.name")
            block["state"] = dict_get(res, "state")
        self.app.render(
            storage,
            headers=[
                "id",
                "name",
                "flavor",
                "state",
                "boot_index",
                "volume_size",
                "bootable",
            ],
        )

        if volume is not None and flavor is not None:
            uri = f"{self.baseuri}/volumes/{volume}/actions"
            data = {"action": {"set_flavor": {"flavor": flavor}}}
            res = self.cmp_put(uri, data=data)
            self.app.render({"msg": f"set volume {volume} flavor {flavor}"})

    @ex(
        help=_("add instance volume"),
        description=_("add instance volume"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["volume"],
                    {
                        "help": _("volume id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_volume_add(self):
        oid = self.app.pargs.id
        volume = self.app.pargs.volume
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"add_volume": {"volume": volume}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add instance {oid} volume {volume}"})

    @ex(
        help=_("remove instance volume"),
        description=_("remove instance volume"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["volume"],
                    {
                        "help": _("volume id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_volume_del(self):
        oid = self.app.pargs.id
        volume = self.app.pargs.volume
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"del_volume": {"volume": volume}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"remove instance {oid} volume {volume}"})

    @ex(
        help=_("extend instance volume"),
        description=_("extend instance volume"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["volume"],
                    {
                        "help": _("volume id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (["size"], {"help": _("volume size"), "action": "store", "type": str}),
            ]
        ),
    )
    def instance_volume_extend(self):
        oid = self.app.pargs.id
        volume = self.app.pargs.volume
        volume_size = self.app.pargs.size

        instance = self.cmp_get(self.baseuri + f"/instances/{oid}").get("instance", {})
        if instance.get("hypervisor") == "openstack" and instance.get("runstate") != "poweredOff":
            self.app.render({"msg": f"To extend the volume you must poweroff the compute instance {oid}"})
            return

        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"extend_volume": {"volume": volume, "volume_size": volume_size}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"extend instance {oid} volume {volume} to size {volume_size} GiB"})

    @ex(
        help=_("get compute instance dns resolution"),
        description=_("get compute instance dns resolution"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def instance_dns_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/instances/{oid}/dns"
        res = self.cmp_get(uri).get("dns", [])
        headers = ["id", "name", "ip_address", "zone", "container", "fqdn"]
        fields = ["id", "name", "ip_address", "parent", "container", "fqdn"]
        self.app.render(res, headers=headers, fields=fields, maxsize=200)

    @ex(
        help=_("add compute instance dns resolution"),
        description=_("add compute instance dns resolution"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def instance_dns_add(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/instances/{oid}/dns"
        res = self.cmp_post(uri)
        self.app.render({"msg": f"add instance {oid} dns resolution {res.get('uuid')}"})

    @ex(
        help=_("delete compute instance dns resolution"),
        description=_("selete compute instance dns resolution"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def instance_dns_del(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/instances/{oid}/dns"
        res = self.cmp_delete(uri)
        self.app.render({"msg": f"delete instance {oid} dns resolution {res.get('uuid')}"})

    @ex(
        help=_("add instance security group"),
        description=_("add instance security group"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["security_group"],
                    {
                        "help": _("security group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_sg_add(self):
        oid = self.app.pargs.id
        security_group = self.app.pargs.security_group
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"add_security_group": {"security_group": security_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add instance {oid} security group {security_group}"})

    @ex(
        help=_("remove instance security group"),
        description=_("remove instance security group"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["security_group"],
                    {
                        "help": _("security group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_sg_del(self):
        oid = self.app.pargs.id
        security_group = self.app.pargs.security_group
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"del_security_group": {"security_group": security_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"remove instance {oid} security group {security_group}"})

    @ex(
        help=_("get instance snapshot"),
        description=_("get instance snapshot"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def instance_snapshot_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/instances/{oid}/snapshots"
        res = self.cmp_get(uri).get("snapshots")
        self.app.render(res, headers=["id", "name", "status", "created_at"])

    @ex(
        help=_("add instance snapshot"),
        description=_("add instance snapshot"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["snapshot"],
                    {
                        "help": _("snapshot name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_snapshot_add(self):
        oid = self.app.pargs.id
        snapshot = self.app.pargs.snapshot
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"add_snapshot": {"snapshot": snapshot}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add instance {oid} snapshot {snapshot}"})

    @ex(
        help=_("remove instance snapshot"),
        description=_("remove instance snapshot"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["snapshot"],
                    {
                        "help": _("snapshot id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_snapshot_del(self):
        oid = self.app.pargs.id
        snapshot = self.app.pargs.snapshot
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"del_snapshot": {"snapshot": snapshot}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"remove instance {oid} snapshot {snapshot}"})

    @ex(
        help=_("revert instance to snapshot"),
        description=_("revert instance to snapshot"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["snapshot"],
                    {
                        "help": _("snapshot id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_snapshot_revert(self):
        oid = self.app.pargs.id
        snapshot = self.app.pargs.snapshot
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"revert_snapshot": {"snapshot": snapshot}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"revert instance {oid} to snapshot {snapshot}"})

    @ex(
        help=_("install shipper on instance to enable resource monitoring"),
        description=_("install shipper on instance to enable resource monitoring"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-hostgroup"],
                    {
                        "help": _("account hostgroup written as Org.Div.Acc"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_monit_enable(self):
        oid = self.app.pargs.id
        host_group = self.app.pargs.hostgroup
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"enable_monitoring": {"host_group": host_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"shipper installed, resource monitoring enabled on instance {oid}"})

    @ex(
        help=_("remove shipper on instance to disable resource monitoring"),
        description=_("remove shipper on instance to disable resource monitoring"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-hostgroup"],
                    {
                        "help": _("account hostgroup written as Org.Div.Acc"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_monit_disable(self):
        oid = self.app.pargs.id
        host_group = self.app.pargs.hostgroup
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"enable_monitoring": {"host_group": host_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"shipper installed, resource monitoring enabled on instance {oid}"})

    @ex(
        help=_("install shipper on instance to forward and centralize log data"),
        description=_("install shipper on instance to forward and centralize log data"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def instance_log_enable(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/instances/{oid}/actions"
        data = {"action": {"enable_logging": True}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"shipper installed, log forwarding enabled on instance {oid}"})

    @ex(
        help=_("get compute instance quotas"),
        description=_("get compute instance quotas"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("compute instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def instance_quota_get(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = self.baseuri + f"/instances/{oid}/quotas"
        res = self.cmp_get(uri, timeout=500).get("quotas")
        # self.app.render(res, headers=['quota', 'value', 'allocated', 'unit'])
        self.app.render(res, details=True)

    #
    # flavor
    #
    @ex(
        help=_("get provider flavor"),
        description=_("get provider flavor(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("flavor id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("entity attributes"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def flavor_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v1.0/nrs/provider/flavors/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                data = res.get("flavor")
                attributes = data.get("attributes", [])
                configs = attributes.pop("configs", [])
                data.pop("flavors", [])
                self.app.render(data, details=True)

                self.c("\nconfigs", "underline")
                self.app.render(configs, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v1.0/nrs/provider/flavors"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="flavors",
                headers=self._meta.flavor_headers,  # pylint: disable=E1101
                fields=self._meta.flavor_fields,  # pylint: disable=E1101
            )

    @ex(
        help=_("add flavor"),
        description=_("add flavor"),
        arguments=ARGS(
            [
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def flavor_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = "/v1.0/nrs/provider/flavors"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add flavor {res['uuid']}"})

    @ex(
        help=_("delete flavor"),
        description=_("delete flavor"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("flavor id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def flavor_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = f"/v1.0/nrs/provider/flavors/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"flavor {oid}")

    @ex(
        help=_("update flavor"),
        description=_("update flavor"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("flavor id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def flavor_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = f"/v1.0/nrs/provider/flavors/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update flavor {res['uuid']}"})

    #
    # image
    #
    @ex(
        help=_("get provider image"),
        description=_("get provider image(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("image id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("entity attributes"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def image_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v1.0/nrs/provider/images/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                data = res.get("image")
                attributes = data.get("attributes", [])
                configs = attributes.pop("configs", [])
                #images = data.pop("images", [])
                self.app.render(data, details=True)

                self.c("\nconfigs", "underline")
                self.app.render(configs, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v1.0/nrs/provider/images"

            def render(self, res, **kwargs):
                self.app.render(
                    res,
                    key="images",
                    headers=self._meta.image_headers,  # pylint: disable=E1101
                    fields=self._meta.image_fields,  # pylint: disable=E1101
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render)

    @ex(
        help=_("add image"),
        description=_("add image"),
        arguments=ARGS(
            [
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def image_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = "/v1.0/nrs/provider/images"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add image {res['uuid']}"})

    @ex(
        help=_("delete image"),
        description=_("delete image"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("image id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def image_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = f"/v1.0/nrs/provider/images/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"image {oid}")

    @ex(
        help=_(
            "prune image branches (Provider.Region.Site.AvailabilityZone.Image, "
            "Vsphere.DataCenter.Folder.Server, Openstack.Image)"
        ),
        description=_(
            "prune image branches (Provider.Region.Site.AvailabilityZone.Image, "
            "Vsphere.DataCenter.Folder.Server, Openstack.Image)"
        ),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("image id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def image_avz_del(self):
        oid = self.app.pargs.id
        custom_baseuri = "/v1.0/nrs"
        data = {}
        uri = f"{custom_baseuri}/entities/{oid}/tree"
        res = self.cmp_get(uri, data=data).get("resourcetree", {})
        # print("res: %s" % res)

        for child in res.get("children", []):
            #l_type = child.get("type")
            uuid = child.get("uuid")
            #l_id = child.get("id")
            name = child.get("name")
            if type == "Provider.Region.Site.AvailabilityZone.Image":
                # print(uuid)

                b_manually = False
                for leaf in child.get("children", []):
                    reuse = leaf.get("reuse")
                    if reuse == "reuse=False":
                        b_manually = True

                if not b_manually:
                    # print("delete %s - uuid: %s - id: %s" % (l_type, uuid, l_id))
                    uri = f"{custom_baseuri}/entities/{uuid}?"
                    self.cmp_delete(uri, entity=f"AvailabilityZone.Image {name}")
                else:
                    print("delete tree image manually. Attention to links reuse=False")

    @ex(
        help=_("update image"),
        description=_("update image"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("image id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def image_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = f"/v1.0/nrs/provider/images/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update image {res['uuid']}"})

    #
    # share
    #
    @ex(
        help=_("get provider shares v1"),
        description=_("get provider shares v1"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("entity attributes"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_get_legacy(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v1.0/nrs/provider/shares/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("share")
                grants = res.get("details").pop("grants")
                self.app.render(res, details=True)

                self.c("\ngrants", "underline")
                self.app.render(
                    grants,
                    headers=["id", "access_level", "access_superuser", "protocols", "clients"],
                    transform={"protocols": ", ".join, "clients": ", ".join},
                )
                """
                for site, grants in grants.items():
                    self.c("\ngrants site: %s" % site, "underline")
                    self.app.render(
                        grants,
                        headers=[
                            "id",
                            "access_type",
                            "access_level",
                            "access_to",
                            "state",
                        ],
                    )
                """
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v1.0/nrs/provider/shares"

            def render(self, res, **kwargs):
                transform = {"details.exports.0.mounts": "\n".join}
                self.app.render(
                    res,
                    key="shares",
                    headers=self._meta.share_headers,  # pylint: disable=E1101
                    fields=self._meta.share_fields,  # pylint: disable=E1101
                    transform=transform,
                    maxsize=200,
                )

            self.cmp_get_pages(uri, data=data, fn_render=render)

    @ex(
        help=_("get provider shares v2"),
        description=_("get provider shares v2"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("entity attributes"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v2.0/nrs/provider/shares/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("share")
                snaplock = res.get("details").pop("snaplock", None)
                snapmirrors = res.get("details").pop("snapmirrors")
                grants = res.get("details").pop("grants")
                self.app.render(res, details=True)

                role = res.get("attributes", {}).get("share_role")
                if role == "main":
                    if not snaplock:
                        snaplock = []
                    self.c("\nsnaplock", "underline")
                    self.app.render(
                        snaplock,
                        headers=["snaplock_phy_id", "snaplock_phy_name", "site", "dest_path", "state", "healthy"],
                    )

                    self.c("\nsnapmirrors", "underline")
                    self.app.render(
                        snapmirrors, headers=["replica_id", "replica_name", "site", "dest_path", "state", "healthy"]
                    )
                elif role == "replica":
                    self.c("\nrelationship with source", "underline")
                    self.app.render(
                        snapmirrors, headers=["source_id", "source_name", "site", "source_path", "state", "healthy"]
                    )
                else:
                    self.c("\nsnapmirrors", "underline")
                    self.app.error(f"Invalid role {role}")

                self.c("\ngrants", "underline")
                self.app.render(
                    grants,
                    headers=["id", "access_level", "access_superuser", "protocols", "clients"],
                    transform={"protocols": ", ".join, "clients": ", ".join},
                )
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v2.0/nrs/provider/shares"

            def render(self, res, **kwargs):
                transform = {
                    "name": lambda x: truncate(x, size=30),
                    "details.exports": lambda x: "\n".join("\n".join(y.get("mounts", [])) for y in x),
                }
                self.app.render(
                    res,
                    key="shares",
                    headers=self._meta.share_headers_v2,  # pylint: disable=E1101
                    fields=self._meta.share_fields_v2,  # pylint: disable=E1101
                    transform=transform,
                    maxsize=200,
                )

            self.cmp_get_pages(uri, data=data, fn_render=render)

    @ex(
        help=_("add provider share v1"),
        description=_("add provider share v1"),
        arguments=ARGS(
            [
                (["name"], {"help": _("share name"), "action": "store", "type": str}),
                (
                    ["container"],
                    {"help": _("resource container id"), "action": "store", "type": str},
                ),
                (
                    ["compute_zone"],
                    {"help": _("compute zone id"), "action": "store", "type": str},
                ),
                (
                    ["availability_zone"],
                    {"help": _("share availability zone"), "action": "store", "type": str},
                ),
                (["vpc"], {"help": _("share vpc"), "action": "store", "type": str}),
                (
                    ["size"],
                    {
                        "help": _("share size"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-proto"],
                    {
                        "help": _("share proto like nfs, cifs"),
                        "action": "store",
                        "type": str,
                        "default": "nfs",
                    },
                ),
                (
                    ["-subnet"],
                    {
                        "help": _("share subnet cidr"),
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
            ]
        ),
    )
    def share_add_legacy(self):
        data = {
            "name": self.app.pargs.name,
            "desc": self.app.pargs.name,
            "container": self.app.pargs.container,
            "compute_zone": self.app.pargs.compute_zone,
            "network": self.app.pargs.vpc,
            "availability_zone": self.app.pargs.availability_zone,
            "size": self.app.pargs.size,
            "share_proto": self.app.pargs.proto,
            "subnet": self.app.pargs.subnet,
        }
        label = self.app.pargs.label
        if label is not None:
            data["share_label"] = label
        uri = "/v1.0/nrs/provider/shares"
        res = self.cmp_post(uri, data={"share": data})
        self.app.render({"msg": f"add share {res['uuid']}"})

    @ex(
        help=_("add provider share v2"),
        description=_("add provider share v2"),
        arguments=ARGS(
            [
                (["name"], {"help": _("share name"), "action": "store", "type": str}),
                (
                    ["container"],
                    {
                        "help": _("resource container id"),
                        # "example": "ResourceProvider01",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["compute_zone"],
                    {"help": _("compute zone id"), "action": "store", "type": str},
                ),
                (
                    ["site"],
                    {
                        "help": _("site name"),
                        # "example": "SiteTorino01",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["size"],
                    {"help": _("share size"), "action": "store", "type": int},
                ),
                (
                    ["proto"],
                    {"help": _("share proto like nfs, cifs"), "action": "store", "type": str},
                ),
                (
                    ["-awx_orchestrator_tag"],
                    {
                        "help": _("the awx orchestrator tag"),
                        # "example": "02",
                        "action": "store",
                        "type": str,
                    },
                ),
                (["-not_compliance"], {"action": "store_true", "default": False}),
                (
                    ["-compliance_rpo"],
                    {"help": _("compliance rpo"), "choices": ["12h", "24h"], "action": "store", "type": str},
                ),
            ]
        ),
    )
    def share_add(self): # TODO check all
        data = {
            "name": self.app.pargs.name,
            "desc": self.app.pargs.name,
            "container": self.app.pargs.container,
            "compute_zone": self.app.pargs.compute_zone,
            "orchestrator_type": "ontap",
            "orchestrator_tag": "legacyfas",
            "site": self.app.pargs.site,
            "share_params": {
                "size": int(self.app.pargs.size),
                "share_proto": self.app.pargs.proto,
                "encrypted": False
            },
            "compliance": not self.app.pargs.not_compliance,
        }

        if not self.app.pargs.not_compliance:
            rpo = self.app.pargs.compliance_rpo
            if not rpo:
                raise Exception("must specify compliance rpo if compliance is True")
            data["compliance_rpo"] = rpo

        if self.app.pargs.awx_orchestrator_tag:
            data["awx_orchestrator_tag"] = self.app.pargs.awx_orchestrator_tag

        uri = "/v2.0/nrs/provider/shares"
        res = self.cmp_post(uri, data={"share": data})
        self.app.render({"msg": f"add share {res['uuid']}"})  # TODO wrong uuid field

    @ex(
        help=_("import provider share v2"),
        description="import provider share v2",
        arguments=ARGS(
            [
                (
                    ["remote_name"],
                    {
                        "help": _("remote ontap volume name"),
                        "action": "store",
                        "type": str,
                    }
                ),
                (
                    ["-name"],
                    {
                        "help": _("share name"),
                        "action": "store",
                        "type": str
                    }
                ),
                (
                    ["-container"],
                    {
                        "help": _("resource container id"),
                        "action": "store",
                        "type": str,
                        "default": "ResourceProvider01"
                    },
                ),
                (
                    ["compute_zone"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str
                    },
                ),
                (
                    ["site"],
                    {
                        "help": "site name",
                        #"example": "SiteTorino01",
                        "action": "store",
                        "type": str
                    }
                ),
                (
                    ["-awx_orchestrator_tag"],
                    {
                        "help": _("awx orchestrator tag"),
                        #"example": "02",
                        "action":"store",
                        "type": str
                    }
                ),
                (
                    ["-force_import_as_main"],
                    {
                        "help": _(
                            "import as main even if it's currently a replica. "
                            "WARNING: do not use if you don't know what you're doing"
                        ),
                        "action": "store_true",
                        "default": False
                    }
                ),
            ]
        ),
    )
    def share_import(self): # TODO check all
        name = self.app.pargs.name
        if not name:
            # real name will be generated
            name = "placeholder"
        remote_name = self.app.pargs.remote_name
        data = {
            "name": name,
            "desc": "imported share",
            "container": self.app.pargs.container,
            "compute_zone": self.app.pargs.compute_zone,
            "orchestrator_type":"ontap",
            "orchestrator_tag":"legacyfas",
            "site": self.app.pargs.site,
            "remote_name": remote_name
        }

        if self.app.pargs.awx_orchestrator_tag:
            data["awx_orchestrator_tag"] = self.app.pargs.awx_orchestrator_tag
        else:
            data["awx_orchestrator_tag"] = "02"

        if self.app.pargs.force_import_as_main:
            # set if volume is a main volume but currently
            # shows as a replica since it's been synced with
            # another volume due to a migration
            if self._ct.prompt_choice(_("Are you sure you want to force import as main volume?"))!="y":
                self.app.error(_("Aborting"))
                return
            data["force_import_as_main"] = self.app.pargs.force_import_as_main

        uri = "/v2.0/nrs/provider/shares/import"
        res = self.cmp_post(uri, data={"share": data})
        self.app.render({"msg": _("add share {share_uuid}").format(share_uuid=res["uuid"])})

    @ex(
        help=_("update share v2 physical resource attributes with aws params"),
        description="update share v2 physical resource attributes with aws params",
        arguments=ARGS(
            [
                (
                    ["share"],
                    {
                        "help": _("provider compute share id"),
                        "action": "store",
                        "type": str,
                    }
                ),
            ]
        ),
    )
    def share_awx_params_update(self):
        share_id = self.app.pargs.share
        share = self.api.resource.provider.share_v2.get(share_id)
        share_attribs = share.get("attributes", {})

        # get site
        site_id = share_attribs.get("availability_zone")
        site = self.api.resource.provider.site.get(site_id)

        # get zone resource
        zn_shares = self.api.resource.entity.get_linked_entities(share_id, link_type=f"relation.{site_id}")
        zn_shares = zn_shares.get("resources")
        zn_share = zn_shares[0]
        zn_share_id = zn_share.get("id")

        # get physical resource
        phy_shares = self.api.resource.entity.get_linked_entities(zn_share_id, link_type="relation")
        phy_shares = phy_shares.get("resources")
        phy_share = phy_shares[0]
        phy_share_id = phy_share.get("id")

        # get awx params from physical resource attributes
        curr_awx_params = phy_share.get("attributes").get("awx_params", {})
        print(_("Current physical resource awx params:") + f"\n{curr_awx_params}")

        # get awx v2 orchestrator
        orchestrators = site.get("orchestrators")
        awx_orchestrators = [o for o in orchestrators if o.get("type") == "awx" and o.get("tag") == "02"]
        if not awx_orchestrators or len(awx_orchestrators) > 1:
            raise Exception(_("Orchestrator Awx02 not found in site")+ f" {site_id}")
        awx_orchestrator = awx_orchestrators[0]

        # determine awx params
        awx_orchestrator_id = awx_orchestrator.get("id")
        awx_organization_id = awx_orchestrator.get("config", {}).get("organization")
        awx_vault_cred_id = awx_orchestrator.get("config", {}).get("vault_cred_id")
        awx_projects = self.api.resource.awx.project.list(container=awx_orchestrator_id, name="staas")
        awx_projects = awx_projects.get("projects", [])
        if not awx_projects or len(awx_projects) > 1:
            raise Exception(_("Staas project not found in orchestrator") + f" {awx_orchestrator_id}")
        awx_project = awx_projects[0]
        awx_project_id = awx_project.get("id")

        calc_awx_params = {
            "awx_orchestrator_id": awx_orchestrator_id,
            "awx_organization_id": awx_organization_id,
            "awx_vault_cred_id": awx_vault_cred_id,
            "awx_project_id": awx_project_id,
        }
        print(_("Calculated awx params:") + f"\n{calc_awx_params}")

        msg = _("If current params and calculated ones differ, you are advised to update current params")
        yes = self.app.pargs.assumeyes
        if yes or self.confirm(msg=msg, suffix=_(". Proceed with update? [y/N]")):
            # update physical resource attributes with awx params
            self.api.resource.entity.set_config(phy_share_id, key="awx_params.awx_orchestrator_id",
                                                value=awx_orchestrator_id)
            self.api.resource.entity.set_config(phy_share_id, key="awx_params.awx_organization_id",
                                                value=awx_organization_id)
            self.api.resource.entity.set_config(phy_share_id, key="awx_params.awx_project_id",
                                                value=str(awx_project_id))
            self.api.resource.entity.set_config(phy_share_id, key="awx_params.awx_vault_cred_id",
                                                value=awx_vault_cred_id)
            print(_("Awx params updated"))

    @ex(
        help=_("add share replica"),
        description=_("add share replica"),
        arguments=ARGS(
            [
                (["source_id"], {"help": _("source volume id"), "action": "store", "type": str}),
                (["dest_site_name"], {"help": _("destination site name"), "action": "store", "type": str}),
                (["replica_rpo"], {"help": _("replica rpo"), "action": "store", "type": str}),
                (["-awx_orchestrator_tag"], {"help": _("awx orchestrator tag"), "action": "store", "type": str})
                # ( TODO uncomment only when needed
                #    ["-custom_service_name"],
                #    {
                #        "help": _("specify custom name for cmp service"),
                #        "action": "store",
                #        "type":str
                #    }
                # )
            ]
        ),
    )
    def share_add_replica(self):
        try:
            source = self.cmp_get(f"/v2.0/nrs/provider/shares/{self.app.pargs.source_id}")
        except Exception as exc:
            raise Exception(f"Source volume not found: {ex!s}") from exc
        data = {
            "container": "ResourceProvider01",
            "compute_zone": str(source.get("share").get("parent")),  # TODO remove?
            "site": self.app.pargs.dest_site_name,
            "rpo": self.app.pargs.replica_rpo,
        }
        if self.app.pargs.awx_orchestrator_tag:
            data["awx_orchestrator_tag"] = self.app.pargs.awx_orchestrator_tag
        uri = f"/v2.0/nrs/provider/shares/{self.app.pargs.source_id}/replica"
        res = self.cmp_post(uri, data={"share": data})
        self.app.render({"msg": f"add share {res['uuid']}"})

    @ex(
        help=_("delete share"),
        description=_("delete share"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
                (
                    ["-version"],
                    {
                        "help": _("share api version. default='v2.0'"),
                        "action": "store",
                        "type": str,
                        "default": "v2.0",
                    },
                ),
            ]
        ),
    )
    def share_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = f"/{self.app.pargs.version}/nrs/provider/shares/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"share {oid}")

    @ex(
        help=_("update share"),
        description=_("update share"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = f"/v1.0/nrs/provider/shares/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": _("update share {share_uuid}").format(share_uuid=res["uuid"])})

    @ex(
        help=_("extend share size"),
        description=_("extend share size"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["size"],
                    {
                        "help": _("new size to assign"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_size_extend(self):
        oid = self.app.pargs.id
        size = self.app.pargs.size
        params = {"new_size": size, "extend_shrink": "extend"}
        self.cmp_put(uri=f"/v2.0/nrs/provider/shares/{oid}/resize", data={"share": params})
        self.app.render({"msg": f"extend share {oid} size: {size}"})

    @ex(
        help=_("shrink share size"),
        description=_("shrink share size"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["size"],
                    {
                        "help": _("new size to assign"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_size_shrink(self):
        oid = self.app.pargs.id
        size = self.app.pargs.size
        params = {"new_size": size, "extend_shrink": "shrink"}
        self.cmp_put(uri=f"/v2.0/nrs/provider/shares/{oid}/resize", data={"share": params})
        self.app.render({"msg": f"shrink share {oid} size: {size}"})

    @ex(
        help=_("set share status"),
        description=_("set remote share status"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["status"],
                    {
                        "metavar": "status",
                        "help": _("share status to set"),
                        "action": "store",
                        "type": str,
                        "choices": ["online", "offline"],
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_set_status(self):
        oid = self.app.pargs.id
        status = self.app.pargs.status
        params = {
            "status": status,
        }
        self.cmp_put(uri=f"/v2.0/nrs/provider/shares/{oid}/setstatus", data={"share": params})
        self.app.render({"msg": f"set share {oid} status: {status}"})

    @ex(
        help=_("list share grants"),
        description=_("list share grants"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def share_grant_get(self):
        data = {}
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/{oid}/grants"
        res = self.cmp_get(uri, data=data).get("shares")
        for item in res:
            # self.app.render(item, headers=self.headers, fields=self.fields)
            self.c("\ngrants", "underline")
            self.app.render(
                item.get("grants", []),
                headers=["id", "state", "level", "type", "to"],
                fields=["uuid", "state", "access_level", "access_type", "access_to"],
                maxsize=200,
                table_style="simple",
            )

    @ex(
        help=_("add share grant"),
        description=_("add share grant"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-access_level"],
                    {
                        "help": _("RW or RO"),
                        "action": "store",
                        "type": str,
                        "default": "RW",
                    },
                ),
                (
                    ["-access_type"],
                    {
                        "help": _("access type like IP or USER or CERT"),
                        "action": "store",
                        "type": str,
                        "default": "IP",
                    },
                ),
                (
                    ["access_to"],
                    {
                        "help": _("access to like ###.###.###.###/24 or admin/user or TLS identity"),
                        "action": "store",
                        "type": str,
                        "default": "RW",
                    },
                ),
            ]
        ),
    )
    def share_grant_add(self):
        oid = self.app.pargs.id
        access_level = self.app.pargs.access_level
        access_type = self.app.pargs.access_type
        access_to = self.app.pargs.access_to

        data = {
            "share_grant": {
                "access_level": access_level,
                "access_type": access_type,
                "access_to": access_to,
            }
        }
        uri = f"{self.baseuri}/{oid}/grants"
        self.cmp_post(uri, data=data)
        self.app.render({"msg": "add share grant"})

    @ex(
        help=_("delete file share grant"),
        description=_("delete file share grant"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["access_id"],
                    {
                        "help": _("access grant id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_grant_del(self):
        oid = self.app.pargs.id
        access_id = self.app.pargs.access_id
        uri = self.baseuri + f"/{oid}/grants"
        self.cmp_delete(uri, data={"share_grant": {"access_id": access_id}})

    @ex(
        help=_("suspend share replica"),
        description=_("suspend share replica"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_replica_suspend(self):
        oid = self.app.pargs.id
        params = {"subaction": "suspend"}
        self.cmp_put(uri=f"/v2.0/nrs/provider/shares/{oid}/replication", data={"share": params})
        self.app.render({"msg": f"suspend share {oid} replica process"})

    @ex(
        help=_("resume share replica"),
        description=_("resume share replica"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_replica_resume(self):
        oid = self.app.pargs.id
        params = {"subaction": "resume"}
        self.cmp_put(uri=f"/v2.0/nrs/provider/shares/{oid}/replication", data={"share": params})
        self.app.render({"msg": f"resume share {oid} replica process"})

    @ex(
        help=_("eliminate share replica relationship"),
        description=_("eliminate share replica relationship"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["new_name"],
                    {
                        "help": _("new share name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_replica_unlink(self):
        oid = self.app.pargs.id
        params = {"subaction": "unlink", "new_name": self.app.pargs.new_name}
        self.cmp_put(uri=f"/v2.0/nrs/provider/shares/{oid}/replication", data={"share": params})
        self.app.render({"msg": f"unlink replica share {oid}"})

    #
    # volume
    #
    @ex(
        help=_("get provider volume"),
        description=_("get provider volume(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("volume id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("entity attributes"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v1.0/nrs/provider/volumes/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("volume")
                attribs = res.pop("attributes", [])
                flavor = res.pop("flavor", [])
                instance = res.pop("instance", [])
                self.app.render(res, details=True)

                self.c("\nattributes", "underline")
                self.app.render(attribs, details=True)
                self.c("\nflavor", "underline")
                self.app.render(flavor, details=True)
                self.c("\ninstance", "underline")
                self.app.render(instance, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v1.0/nrs/provider/volumes"

            def render(self, res, **kwargs):
                self.app.render(
                    res,
                    key="volumes",
                    headers=self._meta.volume_headers,  # pylint: disable=E1101
                    fields=self._meta.volume_fields,  # pylint: disable=E1101
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render, pagesize=20)

    @ex(
        help=_("add volume"),
        description=_("add volume"),
        arguments=ARGS(
            [
                (
                    ["file"],
                    {
                        "help": _(
                            "data file. Ex. volume: container: ResourceProvider01  name: provettina-volume01 "
                            "desc: provettina-volume01 compute_zone: ComputeService-44ff4cf3 "
                            "availability_zone: SiteVercelli01 size: 5 type: openstack "
                            "flavor: vol.default"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def volume_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = "/v1.0/nrs/provider/volumes"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add volume {res['uuid']}"})

    @ex(
        help=_("import volume"),
        description=_("import volume"),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("instance name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["physical_id"],
                    {
                        "help": _("physical resource id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_import(self):
        name = self.app.pargs.name
        physical_id = self.app.pargs.physical_id

        config = {
            "container": "ResourceProvider01",
            "name": name,
            "desc": name,
            "physical_id": physical_id,
            "attribute": {},
            "resclass": "beehive_resource.plugins.provider.entity.instance.ComputeVolume",
            "configs": {},
        }
        uri = "/v1.0/nrs/entities/import"
        self.cmp_post(uri, data={"resource": config})
        self.app.render({"msg": f"import volume {name}"})

    @ex(
        help=_("delete volume"),
        description=_("delete volume"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("volume id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def volume_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = f"/v1.0/nrs/provider/volumes/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"volume {oid}")

    @ex(
        help=_("update volume"),
        description=_("update volume"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("volume id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = f"/v1.0/nrs/provider/volumes/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update volume {res['uuid']}"})

    @ex(
        help=_("set volume flavor"),
        description=_("set volume flavor"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("volume id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["flavor"],
                    {
                        "help": _("volume flavor id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_flavor_set(self):
        oid = self.app.pargs.id
        flavor = self.app.pargs.flavor
        uri = f"{self.baseuri}/volumes/{oid}/actions"
        data = {"action": {"set_flavor": {"flavor": flavor}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"set volume {oid} flavor {flavor}"})

    #
    # volumeflavor
    #
    @ex(
        help=_("get provider volumeflavor"),
        description=_("get provider volumeflavor(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("volumeflavor id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("entity attributes"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volumeflavor_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v1.0/nrs/provider/volumeflavors/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("volumeflavor")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v1.0/nrs/provider/volumeflavors"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="volumeflavors",
                headers=self._meta.volumeflavor_headers,  # pylint: disable=E1101
                fields=self._meta.volumeflavor_fields,  # pylint: disable=E1101
            )

    @ex(
        help=_("add volumeflavor"),
        description=_("add volumeflavor"),
        arguments=ARGS(
            [
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def volumeflavor_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = "/v1.0/nrs/provider/volumeflavors"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add volumeflavor {res['uuid']}"})

    @ex(
        help=_("delete volumeflavor"),
        description=_("delete volumeflavor"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("volumeflavor id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def volumeflavor_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = f"/v1.0/nrs/provider/volumeflavors/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"volumeflavor {oid}")

    @ex(
        help=_("update volumeflavor"),
        description=_("update volumeflavor"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("volumeflavor id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volumeflavor_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = f"/v1.0/nrs/provider/volumeflavors/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update volumeflavor {res['uuid']}"})

    #
    # customization
    #
    @ex(
        help=_("get customization(s)"),
        description=_("get customization(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("customization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def customization_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v1.0/nrs/provider/customizations/{oid}"
            res = self.cmp_get(uri).get("customization")
            if self.is_output_text():
                applied_customs = res.pop("applied", [])
                self.app.render(res, details=True)
                self.c("\n\napplied customizations", "underline")
                headers = ["id", "uuid", "name", "state"]
                fields = ["id", "uuid", "name", "state"]
                self.app.render(applied_customs, headers=headers, fields=fields, maxsize=400)
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v1.0/nrs/provider/customizations"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="customizations",
                headers=self._meta.customization_headers,  # pylint: disable=E1101
                fields=self._meta.customization_fields,  # pylint: disable=E1101
            )

    @ex(
        help=_("add customization"),
        description=_("add customization"),
        arguments=ARGS(
            [
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
                #
                # As a data file example, see beehive-mgmt/configs/test/example/provider_customization_add.yml
                #
            ]
        ),
    )
    def customization_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = "/v1.0/nrs/provider/customizations"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add customization {res['uuid']}"})

    @ex(
        help=_("delete customization"),
        description=_("delete customization"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("customization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def customization_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = f"/v1.0/nrs/provider/customizations/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"customization {oid}")

    #
    # applied customization
    #
    @ex(
        help=_("get applied customizations"),
        description=_("get applied customizations"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("applied customization uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-uuids"],
                    {
                        "help": _("comma separated list of applied customization uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-instance"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def applied_customization_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            uri = f"/v1.0/nrs/provider/applied_customizations/{oid}"
            res = self.cmp_get(uri).get("applied_customization")
            if self.is_output_text():
                job_template = res.pop("job_template", {})
                last_job = job_template.pop("last_job", {})
                #related = last_job.pop("related", {})
                #summary_fields = last_job.pop("summary_fields", {})
                #job_env = last_job.pop("job_env", {})
                stdout = last_job.pop("stdout", {}).get("content")
                self.app.render(res, details=True)
                self.c("\njob template", "underline")
                self.app.render(job_template, details=True)
                self.c(f"\njob {last_job['id']} stdout", "underline")
                print(stdout)
            else:
                self.app.render(res, details=True)
        else:
            uri = "/v1.0/nrs/provider/applied_customizations"
            params = ["instance", "uuids"]
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="applied_customizations",
                headers=self._meta.customization_headers,  # pylint: disable=E1101
                fields=self._meta.customization_fields,  # pylint: disable=E1101
            )

    @ex(
        help=_("add applied customization"),
        description=_("add applied customization"),
        arguments=ARGS(
            [
                (
                    ["container"],
                    {
                        "help": _("container id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["compute_zone"],
                    {
                        "help": _("compute zone id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {"help": _("name"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-desc"],
                    {
                        "help": _("description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["customization"],
                    {
                        "help": _("customization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["instance"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-extra_vars"],
                    {
                        "help": _("extra vars passed as json file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-playbook"],
                    {
                        "help": _("container id"),
                        "action": "store",
                        "type": str,
                        "default": "main.yml",
                    },
                ),
                (
                    ["-verbosity"],
                    {
                        "help": _("container id"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
            ]
        ),
    )
    def applied_customization_add(self):
        container = self.app.pargs.container
        compute_zone = self.app.pargs.compute_zone
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        customization = self.app.pargs.customization
        extra_vars = self.app.pargs.extra_vars
        if desc is None:
            desc = name
        if extra_vars is not None:
            extra_vars = load_config(extra_vars)
        else:
            extra_vars = {}
        data = {
            "container": container,
            "compute_zone": compute_zone,
            "name": name,
            "desc": desc,
            "customization": customization,
            "instances": [{"id": self.app.pargs.instance}],
            "extra_vars": extra_vars,
            "playbook": self.app.pargs.playbook,
            "verbosity": self.app.pargs.verbosity,
        }
        uri = "/v1.0/nrs/provider/applied_customizations"
        res = self.cmp_post(uri, data={"applied_customization": data})
        self.app.render({"msg": f"add applied customization {res['uuid']}"})

    @ex(
        help=_(
            "delete applied customization. It removes customization entities from CMP and AWX platforms but do not "
            "uninstall software from hosts where customization was applied"
        ),
        description=_(
            "delete applied customization. It removes customization entities from CMP and AWX platforms but do "
            "not uninstall software from hosts where customization was applied"
        ),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("applied customization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def applied_customization_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = f"/v1.0/nrs/provider/applied_customizations/{oid}"
        if force is True:
            uri += "?force=true"
        self.cmp_delete(uri, entity=f"applied customization {oid}")

    #
    # stack
    #
    @ex(
        help=_("get stack"),
        description=_("get stack"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def stack_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v2.0/nrs/provider/stacks/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("stack")
                actions = res.pop("actions")
                resources = res.pop("resources")
                inputs = res.pop("inputs", {})
                outputs = res.pop("outputs")
                self.app.render(res, details=True)

                self.c("\ninputs", "underline")
                self.app.render(inputs, details=True)
                self.c("\nactions", "underline")
                headers = ["id", "name", "state", "creation", "modified"]
                fields = ["uuid", "name", "state", "date.creation", "date.modified"]
                self.app.render(actions, headers=headers, fields=fields, showindex="always")
                self.c("\nresources", "underline")
                headers = ["id", "name", "state", "active"]
                fields = ["uuid", "name", "state", "active"]
                self.app.render(resources, headers=headers, fields=fields)
                self.c("\noutputs", "underline")
                self.app.render(outputs, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v2.0/nrs/provider/stacks"

            def render(self, res, **kwargs):
                headers = [
                    "id",
                    "name",
                    "parent",
                    "state",
                    "type",
                    "actions",
                    "resources",
                    "creation",
                ]
                fields = [
                    "uuid",
                    "name",
                    "parent",
                    "state",
                    "attributes.stack_type",
                    "actions",
                    "resources",
                    "date.creation",
                ]
                self.app.render(res, key="stacks", headers=headers, fields=fields)

            res = self.cmp_get_pages(uri, data=data, fn_render=render)

    @ex(
        help=_("get stack action"),
        description=_("get stack action"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["action"],
                    {
                        "help": _("action index"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def stack_action_get(self):
        oid = self.app.pargs.id
        action_index = self.app.pargs.action
        uri = f"/v2.0/nrs/provider/stacks/{oid}"
        res = self.cmp_get(uri)
        actions = dict_get(res, "stack.actions")
        try:
            action = actions[action_index]
        except Exception as exc:
            raise Exception(f'action {action_index} with index does note exist') from exc

        if self.is_output_text():
            attributes = action.pop("attributes")
            resource = attributes.pop("resource")
            params = attributes.pop("params")
            self.app.render(action, details=True)
            self.c("\nresource", "underline")
            self.app.render(resource, details=True)
            self.c("\nparams", "underline")
            self.app.render(params, details=True)
        else:
            self.app.render(res, details=True)

    #
    # sql stack
    #
    @ex(
        help=_("get stack sql"),
        description=_("get stack sql"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def stack_sql_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v2.0/nrs/provider/sql_stacks/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("sql_stack")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v2.0/nrs/provider/sql_stacks"

            def render(self, res, **kwargs):
                headers = [
                    "id",
                    "name",
                    "parent",
                    "state",
                    "runstate",
                    "engine",
                    "version",
                    "storage",
                    "charset",
                    "timezone",
                    "license",
                    "listener",
                    "vpc",
                    "security_groups",
                    "date",
                ]
                fields = [
                    "id",
                    "name",
                    "parent",
                    "state",
                    "runstate",
                    "attributes.engine",
                    "attributes.version",
                    "allocated_storage",
                    "attributes.charset",
                    "attributes.timezone",
                    "attributes.license",
                    "listener",
                    "vpc.name",
                    "security_groups.0.name",
                    "date.creation",
                ]
                transform = {"listener.colortext": False, "listener.address.colortext": False}
                self.app.render(res, key="sql_stacks", headers=headers, fields=fields, transform=transform)

            res = self.cmp_get_pages(uri, data=data, fn_render=render, pagesize=20)

    @ex(
        help=_("import stack sql"),
        description=_("import stack sql"),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("sql stack name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["physical_id"],
                    {
                        "help": _("compute instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["engine"],
                    {
                        "help": _("sql stack engine"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["version"],
                    {
                        "help": _("sql stack engine version"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": _("sql stack admin password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-charset"],
                    {
                        "help": _("sql stack charset"),
                        "action": "store",
                        "type": str,
                        "default": "latin1",
                    },
                ),
                (
                    ["-timezone"],
                    {
                        "help": _("sql stack charset"),
                        "action": "store",
                        "type": str,
                        "default": "Europe/Rome",
                    },
                ),
            ]
        ),
    )
    def stack_sql_import(self):
        name = self.app.pargs.name
        physical_id = self.app.pargs.physical_id
        engine = self.app.pargs.engine
        version = self.app.pargs.version
        pwd = self.app.pargs.pwd
        charset = self.app.pargs.charset
        timezone = self.app.pargs.timezone

        config = {
            "container": "ResourceProvider01",
            "name": name,
            "desc": name,
            "physical_id": physical_id,
            "attribute": {},
            "resclass": "beehive_resource.plugins.provider.entity.sql_stack_v2.SqlComputeStackV2",
            "configs": {
                "charset": charset,
                "timezone": timezone,
                "engine": engine,
                "version": version,
                "pwd": {"admin": pwd, "db_superuser": "", "db_appuser_pwd": ""},
                "user": {"db_superuser": "system", "db_appuser_pwd": "test"},
            },
        }
        uri = "/v1.0/nrs/entities/import"
        self.cmp_post(uri, data={"resource": config})
        self.app.render({"msg": f"import sql stack {name}"})

    @ex(
        help=_("get stack sql engines"),
        description=_("get stack sql engines"),
        arguments=ARGS([]),
    )
    def stack_sql_engine_get(self):
        uri = "/v2.0/nrs/provider/sql_stacks/engines"
        res = self.cmp_get(uri, data="")
        self.app.render(res, headers=["engine", "version"], key="engines")

    @ex(
        help=_("get database credentials"),
        description=_("get database credentials"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("sql stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def stack_sql_credential_get(self):
        oid = self.app.pargs.id
        uri = f"/v2.0/nrs/provider/sql_stacks/{oid}/credentials"
        res = self.cmp_get(uri, data="")
        self.app.render(res, headers=["name", "password"], key="sql_stack_credentials")

    @ex(
        help=_("set database credentials. Only root support for the moment"),
        description=_("set database credentials. Only root support for the moment"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("sql stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["user"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": _(
                            "user password. If pwd start with @ pwd is the name of a file that contains password"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def stack_sql_credential_set(self):
        oid = self.app.pargs.id
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        if pwd.find("@") == 0:
            pwd = read_file(pwd.lstrip("@"))
        uri = f"/v2.0/nrs/provider/sql_stacks/{oid}/credentials"
        self.cmp_put(uri, data={"user": user, "password": pwd})
        self.app.render({"msg": f"set {user} password"})

    @ex(
        help=_("get stack sql dbs"),
        description=_("get stack sql dbs"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def stack_sql_db_get(self):
        oid = self.app.pargs.id
        uri = f"/v2.0/nrs/provider/sql_stacks/{oid}/action"
        data = {"action": {"get_dbs": True}}
        res = self.cmp_put(uri, data=data)
        res = res.get("dbs")
        self.app.render(res, headers=["db_name", "charset", "collation"])

    @ex(
        help=_("get stack sql dbs"),
        description=_("get stack sql dbs"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def stack_sql_user_get(self):
        oid = self.app.pargs.id
        uri = f"/v2.0/nrs/provider/sql_stacks/{oid}/action"
        data = {"action": {"get_users": True}}
        res = self.cmp_put(uri, data=data)
        res = res.get("users")
        self.app.render(res, headers=["user", "host", "account_locked", "max_connections", "plugin"])

    @ex(
        help=_("enable mailx"),
        description=_("enable mailx"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-relayhost"],
                    {
                        "help": _("remote relay mail server, default is xxx.csi.it"),
                        "action": "store",
                        "type": str,
                        "default": "xxx.csi.it",
                    },
                ),
            ]
        ),
    )
    def stack_sql_mailx_enable(self):
        oid = self.app.pargs.id
        relayhost = self.app.pargs.relayhost
        uri = f"/v2.0/nrs/provider/sql_stacks/{oid}/action"
        data = {"action": {"enable_mailx": {"relayhost": relayhost}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "enable mailx"})

    @ex(
        help=_("register db server on haproxy"),
        description=_("register db server on haproxy"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ports"],
                    {
                        "help": _("range of haproxy ports that clients can connect to [default=10100:10999]"),
                        "action": "store",
                        "type": str,
                        "default": "10100:10999",
                    },
                ),
            ]
        ),
    )
    def stack_sql_haproxy_register(self):
        oid = self.app.pargs.id
        ports = self.app.pargs.ports
        ports = ports.strip().split(":")
        port_ini = ports[0]
        port_fin = ports[1]
        uri = f"/v2.0/nrs/provider/sql_stacks/{oid}/action"
        data = {"action": {"haproxy_register": {"port_ini": port_ini, "port_fin": port_fin}}}
        self.cmp_put(uri, data=data)
        msg = f"register db server {oid} on haproxy"
        self.app.render({"msg": msg})

    @ex(
        help=_("deregister db server from haproxy"),
        description=_("deregister db server from haproxy"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def stack_sql_haproxy_deregister(self):
        oid = self.app.pargs.id
        uri = f"/v2.0/nrs/provider/sql_stacks/{oid}/action"
        data = {"action": {"haproxy_deregister": True}}
        self.cmp_put(uri, data=data)
        msg = f"deregister db server {oid} from haproxy"
        self.app.render({"msg": msg})

    @ex(
        help=_("delete sqlstack v2"),
        description=_(
            "Attention! \nThis command shall never be used! "
            "Databases shuold be deleted always from service interface. \n"
            "This command is intended for debugging and for advanced administrative tasks."
        ),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("sql stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def stack_sql_delete(self):
        oid = self.app.pargs.id
        uri = f"/v2.0/nrs/provider/sql_stacks/{oid}"
        self.cmp_delete(uri, entity=f"Sql Stack {oid}")


    #
    # oldstack
    #
    @ex(
        help=_("get provider old stack"),
        description=_("get provider old stack"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("old stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def oldstack_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v1.0/nrs/provider/stacks/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("stack")
                self.app.render(res, details=True)

                # get ssh management status
                self.c("\nmanagement status", "underline")
                uri = f"/v1.0/nrs/provider/stacks/{oid}/manage"
                mgt = self.cmp_get(uri).get("is_managed", [])
                res = {
                    "is-managed": bool2str(mgt),
                    "has-backup": "false",
                    "has-monitor": "false",
                }
                self.app.render(res, details=True)

                # get dns
                self.c("\ndns resolution", "underline")
                uri = f"/v1.0/nrs/provider/stacks/{oid}/dns"
                res = self.cmp_get(uri).get("dns", {})
                headers = ["id", "name", "ip_address", "zone", "container", "fqdn"]
                fields = ["id", "name", "ip_address", "parent", "container", "fqdn"]
                self.app.render(res, headers=headers, fields=fields)

                # get resources
                uri = f"/v1.0/nrs/provider/stacks/{oid}/resources"
                res = self.cmp_get(uri, data="").get("stack_resources")
                for item in res:
                    self.c(
                        f"\nAvailability zone: {item.get('availability_zone')}",
                        "underline",
                    )
                    self.c("resources", "underline")
                    self.app.render(
                        item.get("resources", []),
                        headers=["id", "name", "type"],
                        fields=["uuid", "name", "__meta__.definition"],
                        maxsize=200,
                        table_style="simple",
                    )
                    self.c("internal resources", "underline")
                    headers = [
                        "id",
                        "logical_id",
                        "name",
                        "type",
                        "creation",
                        "status",
                        "reason",
                        "required",
                    ]
                    fields = [
                        "physical_resource_id",
                        "logical_resource_id",
                        "resource_name",
                        "resource_type",
                        "creation_time",
                        "resource_status",
                        "resource_status_reason",
                        "required_by",
                    ]
                    self.app.render(
                        item.get("internal_resources", []),
                        headers=headers,
                        fields=fields,
                        maxsize=40,
                        table_style="simple",
                    )

                # get inputs
                self.c("\ninputs", "underline")
                uri = f"/v1.0/nrs/provider/stacks/{oid}/inputs"
                res = self.cmp_get(uri, data="").get("stack_inputs")
                for item in res:
                    self.c(
                        f"availability zone: {item.get('availability_zone')}",
                        "underline",
                    )
                    resp = []
                    for k, v in item.get("inputs").items():
                        resp.append({"key": k, "value": v})
                    self.app.render(resp, headers=["key", "value"], maxsize=200)

                # get outputs
                self.c("\noutputs", "underline")
                uri = f"/v1.0/nrs/provider/stacks/{oid}/outputs"
                res = self.cmp_get(uri, data="").get("stack_outputs")
                for item in res:
                    self.c(
                        f"availability zone: {item.get('availability_zone')}",
                        "underline",
                    )
                    for out in item.get("outputs"):
                        print("----------------------------------------------------------")
                        print("output_key:")
                        print(out.get("output_key", None))
                        print("description:")
                        print(out.get("description", None))
                        print("output_value:")
                        print(out.get("output_value", None))
                        print("output_error:")
                        print(out.get("output_error", None))
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v1.0/nrs/provider/stacks"

            def render(self, res, **kwargs):
                headers = [
                    "id",
                    "name",
                    "parent",
                    "state",
                    "runstate",
                    "type",
                    "engine",
                    "creation",
                ]
                fields = [
                    "uuid",
                    "name",
                    "parent",
                    "state",
                    "runstate",
                    "attributes.stack_type",
                    "attributes.engine",
                    "date.creation",
                ]
                self.app.render(res, key="stacks", headers=headers, fields=fields)

            res = self.cmp_get_pages(uri, data=data, fn_render=render)

    @ex(
        help=_("enable provider old stack management by ssh module"),
        description=_("enable provider old stack management by ssh module"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("old stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ssh_key"],
                    {
                        "help": _("server stack ssh key"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def oldstack_manage(self):
        """Enable provider computes instance management by ssh module"""
        oid = self.app.pargs.id
        key = self.app.pargs.ssh_key

        data = {"manage": {"key": key}}
        uri = f"/v1.0/nrs/provider/stacks/{oid}/manage"
        res = self.cmp_post(uri, data=data).get("manage", [])
        self.app.render({"msg": f"enable old stack {oid} management with ssh node: {res}"})

    @ex(
        help=_("disable provider old stack management by ssh module"),
        description=_("disable provider old stack management by ssh module"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("old stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def oldstack_unmanage(self):
        oid = self.app.pargs.id
        uri = f"/v1.0/nrs/provider/stacks/{oid}/manage"
        self.cmp_delete(uri, entity=f"compute old stack {oid}")

    @ex(
        help=_("add compute old stack dns resolution"),
        description=_("add compute old stack dns resolution"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("old sql stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def oldstack_dns_add(self):
        oid = self.app.pargs.id
        uri = f"/v1.0/nrs/provider/stacks/{oid}/dns"
        self.cmp_post(uri)
        self.app.render({"msg": f"add old stack {oid} dns resolution"})

    @ex(
        help=_("delete compute old stack dns resolution"),
        description=_("delete compute old stack dns resolution"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("old sql stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def oldstack_dns_del(self):
        oid = self.app.pargs.id
        uri = f"/v1.0/nrs/provider/stacks/{oid}/dns"
        self.cmp_delete(uri, entity=f"old stack {oid} dns resolution")

    #
    # old sql stack
    #
    @ex(
        help=_("get provider old stack sql"),
        description=_("get provider old stack sql"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("old stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def oldstack_sql_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v1.0/nrs/provider/sql_stacks/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("sql_stack")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v1.0/nrs/provider/sql_stacks"
            res = self.cmp_get(uri, data=data)
            headers = [
                "id",
                "name",
                "parent",
                "state",
                "listener",
                "vpc",
                "security_group",
                "creation",
                "modified",
            ]
            fields = [
                "uuid",
                "name",
                "parent",
                "state",
                "stacks.0.listener",
                "vpcs.0.name",
                "security_groups.0.name",
                "date.creation",
                "date.modified",
            ]
            self.app.render(res, key="sql_stacks", headers=headers, fields=fields)

    @ex(
        help=_("get provider old stack sql engines"),
        description=_("get provider old stack sql engines"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("old sql stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def oldstack_sql_engine_get(self):
        uri = "/v1.0/nrs/provider/sql_stacks/engines"
        res = self.cmp_get(uri, data="")
        self.app.render(res, headers=["engine", "version"], key="engines")

    @ex(
        help=_("get database credentials"),
        description=_("get database credentials"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("old sql stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def oldstack_sql_credential_get(self):
        oid = self.app.pargs.id
        uri = f"/v1.0/nrs/provider/sql_stacks/{oid}/credentials"
        res = self.cmp_get(uri, data="")
        self.app.render(res, headers=["name", "pwd"], key="sql_stack_credentials")

    @ex(
        help=_("set database credentials. Only root support for the moment"),
        description=_("set database credentials. Only root support for the moment"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("old sql stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": _("old sql stack password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def oldstack_sql_credential_set(self):
        oid = self.app.pargs.id
        pwd = self.app.pargs.pwd
        uri = f"/v1.0/nrs/provider/sql_stacks/{oid}/credentials"
        self.cmp_put(uri, data={"sql_stack_credentials": [{"user": "root", "pwd": pwd}]})
        self.app.render({"msg": "set root password"})

    #
    # old app stack
    #
    @ex(
        help=_("get provider old stack app"),
        description=_("get provider old stack app"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("old stack id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def oldstack_app_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v1.0/nrs/provider/app_stacks/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("app_stack")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v1.0/nrs/provider/app_stacks"
            res = self.cmp_get(uri, data=data)
            headers = [
                "id",
                "name",
                "parent",
                "state",
                "listener",
                "vpc",
                "security_group",
                "creation",
                "modified",
            ]
            fields = [
                "uuid",
                "name",
                "parent",
                "state",
                "stacks.0.listener",
                "vpcs.0.name",
                "security_groups.0.name",
                "date.creation",
                "date.modified",
            ]
            self.app.render(res, key="app_stacks", headers=headers, fields=fields)

    #
    # gateway
    #
    @ex(
        help=_("get provider gateway"),
        description=_("get provider gateway(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("gateway id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("entity attributes"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def gateway_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v1.0/nrs/provider/gateways/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("gateway")
                vpc = res.pop("vpc", {})
                internal_routers = res.pop("details", {}).get("internal_router", [])
                self.app.render(res, details=True)

                uplinks = vpc.get("uplinks", [])
                for uplink in uplinks:
                    uplink["type"] = "uplink"
                internals = vpc.get("internals", [])
                for internal in internals:
                    internal["type"] = "internal"
                transport = vpc.get("transport", [])
                transport["type"] = "transport"
                vpcs = [transport]
                vpcs.extend(uplinks)
                vpcs.extend(internals)

                self.c("\n\nvpcs", "underline")
                headers = ["id", "uuid", "name", "parent", "cidr", "type"]
                fields = ["id", "uuid", "name", "parent", "cidr", "type"]
                self.app.render(vpcs, headers=headers, fields=fields, maxsize=100)

                self.c("\n\nnat rules", "underline")
                uri = f"/v1.0/nrs/provider/gateways/{oid}/nat"
                nats = self.cmp_get(uri).get("nat_rules")
                headers = [
                    "role",
                    "id",
                    "action",
                    "desc",
                    "vnic",
                    "orig-address",
                    "orig-port",
                    "translate-address",
                    "translate-port",
                    "proto",
                ]
                fields = [
                    "role",
                    "ruleId",
                    "action",
                    "description",
                    "vnic",
                    "originalAddress",
                    "originalPort",
                    "translatedAddress",
                    "translatedPort",
                    "protocol",
                ]
                self.app.render(nats, headers=headers, fields=fields, maxsize=100)

                self.c("\n\nfirewall rules", "underline")
                uri = f"/v1.0/nrs/provider/gateways/{oid}/firewall"
                fws = self.cmp_get(uri).get("firewall_rules")
                for r in fws:
                    source = r.get("source", {})
                    new_source = []
                    for k, v in source.items():
                        if isinstance(v, list):
                            for v1 in v:
                                new_source.append(f"{k}:{v1}")
                        else:
                            new_source.append(f"{k}:{v}")
                    r["source"] = "\n".join(new_source)

                    dest = r.get("destination", {})
                    new_dest = []
                    for k, v in dest.items():
                        if isinstance(v, list):
                            for v1 in v:
                                new_dest.append(f"{k}:{v1}")
                        else:
                            new_dest.append(f"{k}:{v}")
                    r["destination"] = "\n".join(new_dest)

                    application = r.get("application", {})
                    new_application = []
                    for k, v in application.items():
                        if isinstance(v, list):
                            for v1 in v:
                                new_application.append(f"{k}:{v1}")
                        if isinstance(v, dict):
                            new_application.append(f"{k}:")
                            for k1, v1 in v.items():
                                new_application.append(f"  {k1}:{v1}")
                        else:
                            new_application.append(f"{k}:{v}")
                    r["application"] = "\n".join(new_application)
                headers = [
                    "role",
                    "id",
                    "name",
                    "type",
                    "action",
                    "enabled",
                    "source",
                    "destination",
                    "application",
                ]
                fields = [
                    "role",
                    "id",
                    "name",
                    "ruleType",
                    "action",
                    "enabled",
                    "source",
                    "destination",
                    "application",
                ]
                self.app.render(fws, headers=headers, fields=fields, maxsize=100)

                self.c("\n\ninternal routers", "underline")
                headers = [
                    "id",
                    "name",
                    "container",
                    "parent",
                    "state",
                    "role",
                    "type",
                    "vnics",
                    "routes",
                ]
                fields = [
                    "id",
                    "name",
                    "container",
                    "parent",
                    "state",
                    "role",
                    "__meta__.definition",
                    "attributes.vnics",
                    "attributes.routes",
                ]
                transform = {
                    "attributes.vnics": lambda ii: "\n".join(
                        [
                            f"{i.get('name', '')}:{i.get('type', '')}:{i.get('primary_address', '')}"
                            for i in ii
                            if isinstance(i, dict)
                        ]
                    ),
                    "attributes.routes": lambda ii: "\n".join(
                        [f"{i.get('network', '')}:{i.get('next_hop', '')}" for i in ii if isinstance(i, dict)]
                    ),
                }
                self.app.render(
                    internal_routers,
                    headers=headers,
                    fields=fields,
                    maxsize=300,
                    transform=transform,
                )
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v1.0/nrs/provider/gateways"
            res = self.cmp_get(uri, data=data)
            for item in res.get("gateways"):
                item["vpcs"] = "\n".join(
                    [
                        f"uplink:    {dict_get(item, 'vpc.uplinks.0.cidr')}",
                        f"transport: {dict_get(item, 'vpc.transport.cidr')}",
                        f"internal:  {dict_get(item, 'vpc.internals.0.cidr')}",
                    ]
                )
                item["external_ip_address"] = "\n".join(
                    [f"{k}:{v}" for k, v in item.get("external_ip_address", {}).items()]
                )

            self.app.render(
                res,
                key="gateways",
                headers=self._meta.gateway_headers,  # pylint: disable=E1101
                fields=self._meta.gateway_fields,  # pylint: disable=E1101
                maxsize=200,
            )

    @ex(
        help=_("get provider gateway credentials"),
        description=_("get provider gateway credentials"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("gateway id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def gateway_credentials_get(self):
        oid = self.app.pargs.id
        uri = f"/v1.0/nrs/provider/gateways/{oid}/credentials"
        res = self.cmp_get(uri)
        res = res.get("credentials")
        self.app.render(res, headers=["user", "password"])

    @ex(
        help=_("set provider gateway default route"),
        description=_("set provider gateway default route"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("gateway id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": _("gateway role. Can be default [default], primary or secondary"),
                        "action": "store",
                        "type": str,
                        "default": "default",
                    },
                ),
            ]
        ),
    )
    def gateway_default_route_set(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        uri = f"/v1.0/nrs/provider/gateways/{oid}/route/default"
        self.cmp_put(uri, data={"role": role})
        self.app.render({"msg": f"set gateway {oid} deafult route with role {role}"})

    @ex(
        help=_("add provider gateway firewall rule"),
        description=_("add provider gateway firewall rule"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("gateway id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": _("gateway role. Can be default [default], primary or secondary"),
                        "action": "store",
                        "type": str,
                        "default": "default",
                    },
                ),
                (
                    ["-action"],
                    {
                        "help": _("firewall rule action. Can be accept [default], deny"),
                        "action": "store",
                        "type": str,
                        "default": "accept",
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": _("firewall rule status"),
                        "action": "store",
                        "type": bool,
                        "default": True,
                    },
                ),
                (
                    ["-logged"],
                    {
                        "help": _("firewall rule logged"),
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
                (
                    ["-direction"],
                    {
                        "help": _("firewall rule direction. Can be: in, out, inout [deafult]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-source"],
                    {
                        "help": _(
                            "rule source. list of comma separated item like: ip:<ipAddress>, "
                            "grp:<groupingObjectId>, vnic:<vnicGroupId>"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dest"],
                    {
                        "help": _(
                            "rule destination. list of comma separated item like: ip:<ipAddress>, "
                            "grp:<groupingObjectId>, vnic:<vnicGroupId>"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-appl"],
                    {
                        "help": _(
                            "rule application. list of comma separated item like: app:<applicationId>, "
                            "ser:proto+port+source_port"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def gateway_firewall_rule_add(self):
        oid = self.app.pargs.id
        data = {
            "role": self.app.pargs.role,
            "action": self.app.pargs.action,
            "enabled": self.app.pargs.enabled,
            "logged": self.app.pargs.logged,
            "direction": self.app.pargs.direction,
            "source": self.app.pargs.source,
            "dest": self.app.pargs.dest,
            "appl": self.app.pargs.appl,
        }
        uri = f"/v1.0/nrs/provider/gateways/{oid}/firewall"
        self.cmp_post(uri, data={"firewall_rule": data})
        self.app.render({"msg": f"add gateway {oid} firewall rule"})

    @ex(
        help=_("delete provider gateway firewall rule"),
        description=_("delete provider gateway firewall rule"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("gateway id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": _("gateway role. Can be default [default], primary or secondary"),
                        "action": "store",
                        "type": str,
                        "default": "default",
                    },
                ),
                (
                    ["-action"],
                    {
                        "help": _("firewall rule action. Can be accept [default], deny"),
                        "action": "store",
                        "type": str,
                        "default": "accept",
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": _("firewall rule status"),
                        "action": "store",
                        "type": bool,
                        "default": True,
                    },
                ),
                (
                    ["-logged"],
                    {
                        "help": _("firewall rule logged"),
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
                (
                    ["-direction"],
                    {
                        "help": _("firewall rule direction. Can be: in, out, inout [deafult]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-source"],
                    {
                        "help": _(
                            "rule source. list of comma separated item like: ip:<ipAddress>, "
                            "grp:<groupingObjectId>, vnic:<vnicGroupId>"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dest"],
                    {
                        "help": _(
                            "rule destination. list of comma separated item like: ip:<ipAddress>, "
                            "grp:<groupingObjectId>, vnic:<vnicGroupId>"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-appl"],
                    {
                        "help": _(
                            "rule application. list of comma separated item like: app:<applicationId>, "
                            "ser:proto+port+source_port"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def gateway_firewall_rule_del(self):
        oid = self.app.pargs.id
        data = {
            "role": self.app.pargs.role,
            "action": self.app.pargs.action,
            "direction": self.app.pargs.direction,
            "source": self.app.pargs.source,
            "dest": self.app.pargs.dest,
            "appl": self.app.pargs.appl,
        }
        uri = f"/v1.0/nrs/provider/gateways/{oid}/firewall"
        self.cmp_delete(uri, data={"firewall_rule": data}, entity=f"gateway {oid} firewall rule")

    @ex(
        help=_("add provider gateway nat rule"),
        description=_("add provider gateway nat rule"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("gateway id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": _("gateway role. Can be default [default], primary or secondary"),
                        "action": "store",
                        "type": str,
                        "default": "default",
                    },
                ),
                (
                    ["action"],
                    {
                        "help": _("nat rule action. Can be snat e dnat"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": _("nat rule status"),
                        "action": "store",
                        "type": bool,
                        "default": True,
                    },
                ),
                (
                    ["-logged"],
                    {
                        "help": _("nat rule logged"),
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
                (
                    ["-original_address"],
                    {
                        "help": _("original address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-translated_address"],
                    {
                        "help": _("translated address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-original_port"],
                    {
                        "help": _("original port"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-translated_port"],
                    {
                        "help": _("translated port"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-protocol"],
                    {
                        "help": _("nat protocol. Ex. tcp"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vnic"],
                    {
                        "help": _("nat vnic index. Ex. 0"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def gateway_nat_rule_add(self):
        oid = self.app.pargs.id
        data = {
            "role": self.app.pargs.role,
            "action": self.app.pargs.action,
            "enabled": self.app.pargs.enabled,
            "logged": self.app.pargs.logged,
            "original_address": self.app.pargs.original_address,
            "translated_address": self.app.pargs.translated_address,
            "original_port": self.app.pargs.original_port,
            "translated_port": self.app.pargs.translated_port,
            "protocol": self.app.pargs.protocol,
            "vnic": self.app.pargs.vnic,
        }
        uri = f"/v1.0/nrs/provider/gateways/{oid}/nat"
        self.cmp_post(uri, data={"nat_rule": data})
        self.app.render({"msg": f"add gateway {oid} nat rule"})

    @ex(
        help=_("delete provider gateway nat rule"),
        description=_("delete provider gateway nat rule"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("gateway id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": _("gateway role. Can be default [default], primary or secondary"),
                        "action": "store",
                        "type": str,
                        "default": "default",
                    },
                ),
                (
                    ["action"],
                    {
                        "help": _("nat rule action. Can be snat e dnat"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-original_address"],
                    {
                        "help": _("original address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-translated_address"],
                    {
                        "help": _("translated address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-original_port"],
                    {
                        "help": _("original port"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-translated_port"],
                    {
                        "help": _("translated port"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-protocol"],
                    {
                        "help": _("nat protocol. Ex. tcp"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vnic"],
                    {
                        "help": _("nat vnic. eEx. vinc0"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def gateway_nat_rule_del(self):
        oid = self.app.pargs.id
        data = {
            "role": self.app.pargs.role,
            "action": self.app.pargs.action,
            "original_address": self.app.pargs.original_address,
            "translated_address": self.app.pargs.translated_address,
            "original_port": self.app.pargs.original_port,
            "translated_port": self.app.pargs.translated_port,
            "protocol": self.app.pargs.protocol,
            "vnic": self.app.pargs.vnic,
        }
        uri = f"/v1.0/nrs/provider/gateways/{oid}/nat"
        self.cmp_delete(uri, data={"nat_rule": data}, entity=f"gateway {oid} nat rule")

    #
    # load balancer
    #
    @ex(
        help=_("get provider load balancer(s)"),
        description=_("get provider load balancer(s)"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("load balancer id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("load balancer name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def load_balancer_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"/v1.0/nrs/provider/loadbalancers/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("load_balancer")
            self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "/v1.0/nrs/provider/loadbalancers"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="load_balancers",
                headers=self._meta.load_balancer_headers,  # pylint: disable=E1101
                fields=self._meta.load_balancer_fields,  # pylint: disable=E1101
                maxsize=200,
            )
