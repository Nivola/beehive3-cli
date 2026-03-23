# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex
from beecell.types.type_string import truncate
from beehive3_cli.core.controller import BaseController, PARGS, ARGS
from beehive3_cli.translate import _


class OpenstackController(BaseController):
    class Meta:
        label = "res_openstack"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("openstack orchestrator")
        help = _("openstack orchestrator")

        cmp = {"baseuri": "/v1.0/nrs/openstack", "subsystem": "resource"}

        headers = ["id", "ext_id", "name", "desc", "parent", "container", "state"]
        fields = ["id", "ext_id", "name", "desc", "parent", "container", "state"]
        project_headers = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "level",
        ]
        project_fields = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "details.level",
        ]
        network_headers = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "segmentation_id",
            "external",
            "shared",
            "provider_type",
        ]
        network_fields = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "details.segmentation_id",
            "details.external",
            "details.shared",
            "details.provider_network_type",
        ]
        subnet_headers = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "cidr",
            "gateway_ip",
            "subnet_types",
            "enable_dhcp",
        ]
        subnet_fields = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "details.cidr",
            "details.gateway_ip",
            "details.subnet_types",
            "details.enable_dhcp",
        ]
        port_headers = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "device_owner",
            "mac_address",
            "ip_address",
        ]
        port_fields = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "details.device_owner",
            "details.mac_address",
            "details.fixed_ips.0.ip_address",
        ]
        router_headers = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "enable_snat",
            "external_network",
            "external_ip",
        ]
        router_fields = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "details.enable_snat",
            "details.external_network.name",
            "details.external_ips.0.ip_address",
        ]
        image_headers = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "size",
            "minDisk",
            "minRam",
            "status",
        ]
        image_fields = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "details.size",
            "details.minDisk",
            "details.minRam",
            "details.status",
        ]
        flavor_headers = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "vcpus",
            "ram",
            "disk",
        ]
        flavor_fields = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "details.vcpus",
            "details.ram",
            "details.disk",
        ]
        server_headers = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "runstate",
            "ip-address",
            "hostname",
            "cpu",
            "ram",
            "disk",
            "disknum",
            "is-template",
        ]
        server_fields = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "details.state",
            "details.ip_address.0",
            "details.hostname",
            "details.cpu",
            "details.memory",
            "details.disk",
        ]
        volume_headers = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "status",
            "size",
            "bootable",
            "encrypted",
            "volume_type",
        ]
        volume_fields = [
            "id",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "details.status",
            "details.size",
            "details.bootable",
            "details.encrypted",
            "details.volume_type",
        ]
        stack_headers = ["id", "ext_id", "name", "desc", "parent", "container", "state"]
        stack_fields = ["id", "ext_id", "name", "desc", "parent", "container", "state"]
        share_headers = [
            "id",
            "ext_id",
            "name",
            "parent",
            "container",
            "state",
            "share_type",
            "share_proto",
            "size",
            "host",
            "date",
        ]
        share_fields = [
            "id",
            "ext_id",
            "name",
            "parent",
            "container",
            "state",
            "details.share_type",
            "details.share_proto",
            "details.size",
            "details.host",
            "date.creation",
        ]

    def pre_command_run(self):
        super().pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help=_("get domains"),
        description=_("get domains"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("domain id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def domain_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/domains/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("domain")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/domains"
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="domains", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("get projects"),
        description=_("get projects"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/projects/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("project")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/projects"

            def render(self, res, **kwargs):
                self.app.render(
                    res,
                    key="projects",
                    headers=self._meta.project_headers,
                    fields=self._meta.project_fields,
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render, pagesize=20)

    @ex(
        help=_("get project quotas"),
        description=_("get project quotas"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_quota_get(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = f"{self.baseuri}/projects/{oid}/quotas"
        res = self.cmp_get(uri)
        res = res.get("quotas")
        resp = []
        resp = res
        # for k, v in res.items():
        #     for k1, v1 in v.items():
        #         if isinstance(v1, int):
        #             v1 = {'limit': v1}
        #         resp.append({'module': k, 'quota': k1, 'value': v1})
        # headers = ['module', 'quota', 'limit', 'reserved', 'in_use', 'allocated']
        # fields = ['module', 'quota', 'value.limit', 'value.reserved', 'value.in_use', 'value.allocated']
        # self.app.render(resp, headers=headers, fields=fields, maxsize=45)
        self.app.render(resp, details=True, maxsize=45)

    @ex(
        help=_("get project default quotas"),
        description=_("get project default quotas"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_default_quota_get(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = f"{self.baseuri}/projects/{oid}/system/project/quotas"
        res = self.cmp_get(uri)
        res = res.get("default_quotas")
        resp = []
        for k, v in res.items():
            for k1, v1 in v.items():
                if isinstance(v1, int):
                    v1 = {"limit": v1}
                resp.append({"module": k, "quota": k1, "value": v1})
        headers = ["module", "quota", "limit", "reserved", "in_use", "allocated"]
        fields = [
            "module",
            "quota",
            "value.limit",
            "value.reserved",
            "value.in_use",
            "value.allocated",
        ]
        self.app.render(resp, headers=headers, fields=fields, maxsize=45)

    @ex(
        help=_("set project quotas"),
        description=_("set project quotas"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["type"],
                    {
                        "help": _("quota type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["quota"],
                    {
                        "help": _("quota name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["value"],
                    {
                        "help": _("quota value"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_quota_set(self):
        oid = getattr(self.app.pargs, "id", None)
        data = {
            "quotas": [
                {
                    "type": self.app.pargs.type,
                    "quota": self.app.pargs.quota,
                    "value": self.app.pargs.value,
                }
            ]
        }
        uri = f"{self.baseuri}/projects/{oid}/quotas"
        self.cmp_post(uri, data=data)
        self.app.render(msg={"msg": f"set project {oid} quota {data['quotas']}"})

    @ex(
        help=_("get project members"),
        description=_("get project members"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_member_get(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = f"{self.baseuri}/projects/{oid}/members"
        res = self.cmp_get(uri)
        res = res.get("members")
        headers = ["user_id", "user_name", "role_id", "role_name"]
        fields = ["user_id", "user_name", "role_id", "role_name"]
        self.app.render(res, headers=headers, fields=fields, maxsize=45)

    @ex(
        help=_("set project member TODO"),
        description=_("set project member TODO"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["type"],
                    {
                        "help": _("quota type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["quota"],
                    {
                        "help": _("quota name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["value"],
                    {
                        "help": _("quota value"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_member_set(self):
        oid = getattr(self.app.pargs, "id", None)
        data = {
            "member": [
                {
                    "type": self.app.pargs.type,
                    "quota": self.app.pargs.quota,
                    "value": self.app.pargs.value,
                }
            ]
        }
        uri = f"{self.baseuri}/projects/{oid}/members"
        self.cmp_post(uri, data=data)
        self.app.render(msg={"msg": f"set project {oid} quota {data['quotas']}"})

    @ex(
        help=_("get networks"),
        description=_("get networks"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def network_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/networks/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("network")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/networks"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="networks",
                headers=self._meta.network_headers,
                fields=self._meta.network_fields,
            )

    @ex(
        help=_("get subnets"),
        description=_("get subnets"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("subnet id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def subnet_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/subnets/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("subnet")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/subnets"
            res = self.cmp_get(uri, data=data)
            transform = {"desc": lambda x: truncate(x, 20)}
            self.app.render(
                res,
                key="subnets",
                headers=self._meta.subnet_headers,
                fields=self._meta.subnet_fields,
                transform=transform,
            )

    @ex(
        help=_("get ports"),
        description=_("get ports"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("port id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def port_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/ports/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("port")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/ports"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="ports",
                headers=self._meta.port_headers,
                fields=self._meta.port_fields,
            )

    @ex(
        help=_("get security groups"),
        description=_("get security groups"),
        arguments=PARGS(
            [
                (
                    ["-id"],
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
    def security_group_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/security_groups/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("security_group")
                rules = res.get("details").pop("rules")
                headers = [
                    "id",
                    "direction",
                    "protocol",
                    "ethertype",
                    "remote_ip_prefix",
                    "remote_group.name",
                    "remote_group.id",
                    "port_range_min",
                    "port_range_max",
                ]
                fields = [
                    "id",
                    "direction",
                    "protocol",
                    "ethertype",
                    "remote_ip_prefix",
                    "remote_group.name",
                    "remote_group.id",
                    "port_range_min",
                    "port_range_max",
                ]
                self.app.render(res, details=True)
                self.c("\nrules", "underline")
                self.app.render(rules, headers=headers, fields=fields)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/security_groups"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="security_groups",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    @ex(
        help=_("delete security group rule"),
        description=_("delete security group rule"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("security group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["rule"],
                    {
                        "help": _("security group rule id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def security_group_del_rule(self):
        oid = self.app.pargs.id
        ruleid = self.app.pargs.rule
        data = {"security_group_rule": {"rule_id": ruleid}}
        uri = f"{self.baseuri}/security_groups/{oid}/rules"
        self.cmp_delete(uri, data=data, entity=f"security group {oid} rule {ruleid}")

    @ex(
        help=_("get routers"),
        description=_("get routers"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("router id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def router_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/routers/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("router")
                details = res.get("details")
                external_net = details.pop("external_network", [])
                external_ips = details.pop("external_ips", [])
                routes = details.pop("routes")

                if external_net is None:
                    external_net = []
                if external_ips is None:
                    external_ips = []

                # get internal ports
                uri = uri + "/ports"
                ports = self.cmp_get(uri).get("router_ports", [])
                self.app.render(res, details=True)

                self.c("\nroutes", "underline")
                self.app.render(routes, headers=["nexthop", "destination"])
                self.c("\nexternal network", "underline")
                self.app.render(external_net, headers=["name", "state"])
                self.c("\nexternal ip", "underline")
                self.app.render(external_ips, headers=["subnet_id", "ip_address"])
                self.c("\ninternal ports", "underline")
                headers = [
                    "id",
                    "name",
                    "state",
                    "network",
                    "device_owner",
                    "mac_address",
                    "subnet",
                    "ip_address",
                ]
                fields = [
                    "id",
                    "name",
                    "state",
                    "details.network.id",
                    "details.device_owner",
                    "details.mac_address",
                    "details.fixed_ips.0.subnet_id",
                    "details.fixed_ips.0.ip_address",
                ]
                self.app.render(ports, headers=headers, fields=fields, maxsize=50)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/routers"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="routers",
                headers=self._meta.router_headers,
                fields=self._meta.router_fields,
            )

    @ex(
        help=_("delete router port"),
        description=_("delete router port"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("router id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["subnet"],
                    {
                        "help": _("subnet id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def router_port_del(self):
        oid = self.app.pargs.id
        subnet = self.app.pargs.subnet
        uri = f"{self.baseuri}/routers/{oid}/ports"
        self.cmp_delete(
            uri,
            data={"router_port": {"subnet_id": subnet}},
            entity=f"router {oid} port on subnet {subnet}",
        )

    @ex(
        help=_("get images"),
        description=_("get images"),
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
            ]
        ),
    )
    def image_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/images/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("image")
                self.app.render(res, details=True)

                uri = uri + "/metadata"
                res = self.cmp_get(uri).get("image_metadata", {})
                self.c("\nmetadata", "underline")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/images"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="images",
                headers=self._meta.image_headers,
                fields=self._meta.image_fields,
            )

    @ex(
        help=_("get flavors"),
        description=_("get flavors"),
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
            ]
        ),
    )
    def flavor_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/flavors/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("flavor")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/flavors"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="flavors",
                headers=self._meta.flavor_headers,
                fields=self._meta.flavor_fields,
            )

    @ex(
        help=_("get servers"),
        description=_("get servers"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("server id"),
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
                    ["-container"],
                    {
                        "help": _("container uuid or name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/servers/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("server")
                detail = res.get("details")
                volumes = detail.pop("volumes", [])
                networks = detail.pop("networks", [])
                flavor = detail.pop("flavor", [])
                security_groups = detail.pop("security_groups", [])
                self.app.render(res, details=True)
                self.c("\nflavor", "underline")
                self.app.render(flavor, headers=["id", "name", "memory", "cpu"])
                self.c("\nvolumes", "underline")
                headers = [
                    "id",
                    "name",
                    "format",
                    "bootable",
                    "storage",
                    "mode",
                    "type",
                    "size",
                ]
                self.app.render(volumes, headers=headers, maxsize=200)
                self.c("\nnetworks", "underline")
                headers = [
                    "net_id",
                    "name",
                    "port_id",
                    "mac_addr",
                    "port_state",
                    "fixed_ips.0.ip_address",
                ]
                self.app.render(networks, headers=headers)
                self.c("\nsecurity_groups", "underline")
                self.app.render(security_groups, headers=["name"])

            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "desc", "parent", "state", "tags", "container"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/servers"
            res = self.cmp_get(uri, data=data)
            transform = {"desc": lambda x: truncate(x, 20)}
            self.app.render(
                res,
                key="servers",
                headers=self._meta.server_headers,
                fields=self._meta.server_fields,
                transform=transform,
            )

    @ex(
        help=_("patch server"),
        description=_("patch server"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_patch(self):
        oid = self.app.pargs.id
        uri = f"/v1.0/nrs/entities/{oid}"
        self.cmp_patch(uri, data={"resource": {}})
        self.app.render({"msg": f"patch server {oid}"}, details=True)

    @ex(
        help=_("delete server"),
        description=_("delete server"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_del(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/servers/{oid}"
        self.cmp_delete(uri, f"server {oid}")

    @ex(
        help=_("get server console"),
        description=_("get server console"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_console(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/servers/{oid}/console"
        res = self.cmp_get(uri)
        self.app.render(res, details=True)

    @ex(
        help=_("get server console"),
        description=_("get server console"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_runtime(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/servers/{oid}/runtime"
        res = self.cmp_get(uri)
        self.app.render(res, details=True)

    @ex(
        help=_("get server stats"),
        description=_("get server stats"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_stats(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/servers/{oid}/stats"
        res = self.cmp_get(uri)

        if self.is_output_text():
            res = res.get("server_stats")
            self.app.render(res, details=True)
        else:
            self.app.render(res, details=True)

    @ex(
        help=_("get server actions"),
        description=_("get server actions"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_actions(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/servers/{oid}/actions"
        res = self.cmp_get(uri)
        self.app.render(res, headers=["action", "request_id", "message"])

    @ex(
        help=_("get server metadata"),
        description=_("get server metadata"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_metadata(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/servers/{oid}/metadata"
        res = self.cmp_get(uri)
        self.app.render(res, details=True)

    @ex(
        help=_("get openstack server snapshots"),
        description=_("get openstack server snapshots"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def server_snapshot_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/servers/{oid}/snapshots"
        res = self.cmp_get(uri).get("server_snapshots")
        self.app.render(res, headers=["id", "name", "status", "created_at"])

    @ex(
        help=_("add openstack server snapshot"),
        description=_("add openstack server snapshot"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
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
    def server_snapshot_add(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"add_snapshot": {"snapshot": name}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add server {oid} snapshot {name}"})

    @ex(
        help=_("delete openstack server snapshot"),
        description=_("delete openstack server snapshot"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
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
    def server_snapshot_del(self):
        oid = self.app.pargs.id
        snapshot = self.app.pargs.snapshot
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"del_snapshot": {"snapshot": snapshot}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"del server {oid} snapshot {snapshot}"})

    @ex(
        help=_("revert openstack server to snapshot"),
        description=_("revert openstack server to snapshot"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
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
    def server_snapshot_revert(self):
        oid = self.app.pargs.id
        snapshot = self.app.pargs.snapshot
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"revert_snapshot": {"snapshot": snapshot}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"revert server {oid} to snapshot {snapshot}"})

    @ex(
        help=_("add openstack server security group"),
        description=_("add openstack server security group"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["sg"],
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
    def server_sg_add(self):
        oid = self.app.pargs.id
        security_group = self.app.pargs.sg
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"add_security_group": {"security_group": security_group}}}
        self.cmp_put(uri, data=data)

    @ex(
        help=_("delete openstack server security group"),
        description=_("delete openstack server security group"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["sg"],
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
    def server_sg_del(self):
        oid = self.app.pargs.id
        security_group = self.app.pargs.sg
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"del_security_group": {"security_group": security_group}}}
        self.cmp_put(uri, data=data)

    @ex(
        help=_("add volume to server"),
        description=_("add volume to server"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
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
    def server_volume_add(self):
        oid = self.app.pargs.id
        volume = self.app.pargs.volume
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"add_volume": {"volume": volume}}}
        self.cmp_put(uri, data=data)

    @ex(
        help=_("get server security groups"),
        description=_("get server security groups"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
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
    def server_volume_del(self):
        oid = self.app.pargs.id
        volume = self.app.pargs.volume
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"del_volume": {"volume": volume}}}
        self.cmp_put(uri, data=data)

    @ex(
        help=_("stop server"),
        description=_("stop server"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_stop(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"stop": True}}
        self.cmp_put(uri, data=data)

    @ex(
        help=_("get server security groups"),
        description=_("get server security groups"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_start(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"start": True}}
        self.cmp_put(uri, data=data)

    @ex(
        help=_("get server security groups"),
        description=_("get server security groups"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server id"),
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
    def server_resize(self):
        oid = self.app.pargs.id
        flavor = self.app.pargs.flavor
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"set_flavor": {"flavor": flavor}}}
        self.cmp_put(uri, data=data)

    @ex(
        help=_("get volumes"),
        description=_("get volumes"),
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
            ]
        ),
    )
    def volume_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/volumes/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("volume")
                uri = uri + "/metadata"
                meta = self.cmp_get(uri)

                self.app.render(res, details=True)
                self.c("\nbase", "underline")
                self.app.render(meta.get("volume_metadata", {}), details=True)
                self.c("\nimage", "underline")
                self.app.render(meta.get("image_metadata", {}), details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/volumes"
            res = self.cmp_get(uri, data=data)
            transform = {
                "desc": lambda x: truncate(x, 20),
                "name": lambda x: truncate(x, 100),
            }
            self.app.render(
                res,
                key="volumes",
                headers=self._meta.volume_headers,
                fields=self._meta.volume_fields,
                transform=transform,
            )

    @ex(
        help=_("get volume snapshots"),
        description=_("get volume snapshots"),
        arguments=PARGS(
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
            ]
        ),
    )
    def volume_snapshot_get(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = f"{self.baseuri}/volumes/{oid}/snapshots"
        res = self.cmp_get(uri).get("snapshots")
        headers = ["id", "name", "status", "size", "created", "progress"]
        fields = [
            "id",
            "name",
            "status",
            "size",
            "created_at",
            "os-extended-snapshot-attributes:progress",
        ]
        self.app.render(res, headers=headers, fields=fields, maxsize=45)

    @ex(
        help=_("add volume snapshot"),
        description=_("add volume snapshot"),
        arguments=PARGS(
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
                    ["name"],
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
    def volume_snapshot_add(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        uri = f"{self.baseuri}/volumes/{oid}/snapshots"
        data = {"snapshot": {"name": name}}
        self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add volume {oid} snapshot: {name}"})

    @ex(
        help=_("delete volume snapshot"),
        description=_("delete volume snapshot"),
        arguments=PARGS(
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
                    ["name"],
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
    def volume_snapshot_del(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        uri = f"{self.baseuri}/volumes/{oid}/snapshots"
        data = {"snapshot": {"name": name}}
        self.cmp_delete(uri, data=data, entity=f"volume {oid} snapshot: {name}")

    @ex(
        help=_("revert volume to snapshot"),
        description=_("revert volume to snapshot"),
        arguments=PARGS(
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
    def volume_snapshot_revert(self):
        oid = self.app.pargs.id
        snapshot = self.app.pargs.snapshot
        uri = f"{self.baseuri}/volumes/{oid}/snapshots/{snapshot}/revert"
        self.cmp_put(uri, {})
        self.app.render({"msg": f"revert volume {oid} to snapshot {snapshot}"})

    @ex(
        help=_("get volumetypes"),
        description=_("get volumetypes"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("volumetype id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volumetype_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/volumetypes/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("volumetype")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/volumetypes"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="volumetypes",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    @ex(
        help=_("get stacks"),
        description=_("get stacks"),
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
            ]
        ),
    )
    def stack_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/stacks/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("stack")
                details = res.pop("details")
                parameters = [{"parameter": item, "value": val} for item, val in details.pop("parameters").items()]
                files = details.pop("files", {})
                outputs = details.pop("outputs", [])
                self.app.render(res, details=True, maxsize=800)
                self.app.render(details, details=True, maxsize=800)
                self.c("\nparameters", "underline")
                self.app.render(parameters, headers=["parameter", "value"], maxsize=800)
                self.c("\nfiles", "underline")
                self.app.render(files, headers=["file", "content"], maxsize=800)
                self.c("\noutputs", "underline")
                self.app.render(
                    outputs,
                    headers=["key", "value", "desc"],
                    fields=["output_key", "output_value", "description"],
                    maxsize=100,
                )

                self.c("\nevents", "underline")
                uri1 = uri + "/events"
                res = self.cmp_get(uri1).get("stack_events", [])
                headers = [
                    "id",
                    "name",
                    "resource_id",
                    "status",
                    "status_reason",
                    "event_time",
                ]
                fields = [
                    "id",
                    "resource_name",
                    "physical_resource_id",
                    "resource_status",
                    "resource_status_reason",
                    "event_time",
                ]
                self.app.render(res, headers=headers, fields=fields, maxsize=45)

                self.c("\ninternal resources", "underline")
                uri1 = uri + "/internal_resources"
                res = self.cmp_get(uri1).get("stack_resources", [])
                headers = ["id", "name", "status", "type", "creation", "required_by"]
                fields = [
                    "physical_resource_id",
                    "resource_name",
                    "resource_status",
                    "resource_type",
                    "creation_time",
                    "required_by",
                ]
                self.app.render(res, headers=headers, fields=fields, maxsize=45)

                self.c("\nresources", "underline")
                uri1 = uri + "/resources"
                res = self.cmp_get(uri1).get("resources", [])
                headers = [
                    "id",
                    "definition",
                    "name",
                    "container",
                    "parent",
                    "state",
                    "creation",
                    "ext_id",
                ]
                fields = [
                    "id",
                    "__meta__.definition",
                    "name",
                    "container",
                    "parent",
                    "state",
                    "date.creation",
                    "ext_id",
                ]
                self.app.render(res, headers=headers, fields=fields, maxsize=45)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/stacks"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="stacks",
                headers=self._meta.stack_headers,
                fields=self._meta.stack_fields,
            )

    @ex(
        help=_("get stack template"),
        description=_("get stack template"),
        arguments=ARGS(
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
    def stack_template_get(self):
        oid = getattr(self.app.pargs, "id", None)
        uri = f"{self.baseuri}/stacks/{oid}/template"
        res = self.cmp_get(uri).get("stack_template", {})
        self.app.render(res, details=True)

    @ex(
        help=_("get orchestrator heat template versions"),
        description=_("get orchestrator heat template versions"),
        arguments=ARGS(
            [
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
    def stack_template_versions(self):
        orchestrator = self.app.pargs.orchestrator
        uri = self.uri
        res = self.cmp_get(uri, data=f"container={orchestrator}").get("template_versions", {})
        self.app.render(res, headers=["version", "type", "aliases"])

    @ex(
        help=_("get stack template functions"),
        description=_("get stack template functions"),
        arguments=ARGS(
            [
                (
                    ["orchestrator"],
                    {
                        "help": _("orchestrator id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["template"],
                    {
                        "help": _("template"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def stack_template_functions(self):
        orchestrator = self.app.pargs.orchestrator
        template = self.app.pargs.template
        uri = "/v1.0/nrs/openstack/stack-template-functions"
        res = self.cmp_get(uri, data=f"container={orchestrator}&template={template}").get(
            "template_functions", {}
        )
        self.app.render(res, headers=["functions", "description"], maxsize=200)

    @ex(
        help=_("validate stack template"),
        description=_("validate stack template"),
        arguments=PARGS(
            [
                (
                    ["orchestrator"],
                    {
                        "help": _("orchestrator id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["template_uri"],
                    {
                        "help": _("template uri"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def stack_template_validate(self):
        orchestrator = self.app.pargs.orchestrator
        template = self.app.pargs.template_uri
        data = {"stack_template": {"container": orchestrator, "template_uri": template}}
        uri = "/v1.0/nrs/openstack/stack-template-validate"
        res = self.cmp_post(uri, data=data)
        if res:
            res["uri"] = template
        self.app.render(res, headers=["uri", "validate"], maxsize=200)

    #
    # share
    #
    @ex(
        help=_("get shares"),
        description=_("get shares"),
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
            ]
        ),
    )
    def share_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/shares/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("share")
                details = res.get("details")
                share_network = details.pop("share_network", {})
                if share_network is None:
                    share_network = {}
                share_server = details.pop("share_server", {})
                if share_server is None:
                    share_server = {}
                export_locations = details.pop("export_locations", [])
                self.app.render(res, details=True)

                self.c("\nshare network", "underline")
                self.app.render(share_network, details=True)
                self.c("\nshare server", "underline")
                self.app.render(share_server, details=True)
                self.c("\nexport locations", "underline")
                self.app.render(
                    export_locations,
                    headers=["id", "preferred", "path", "share_instance_id"],
                    maxsize=100,
                )

                self.c("\ngrants", "underline")
                uri = f"{self.baseuri}/shares/{oid}/grant"
                try:
                    res = self.cmp_get(uri).get("share_grant", [])
                    self.app.render(
                        res,
                        headers=[
                            "id",
                            "state",
                            "access_level",
                            "access_type",
                            "access_to",
                        ],
                        maxsize=80,
                    )
                except:
                    pass
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/shares"
            res = self.cmp_get(uri, data=data)
            transform = {"details.host": lambda x: truncate(x, 25)}
            self.app.render(
                res,
                key="shares",
                headers=self._meta.share_headers,
                fields=self._meta.share_fields,
                transform=transform,
            )

    @ex(
        help=_("add share"),
        description=_("add share"),
        arguments=PARGS(
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
                    ["name"],
                    {
                        "help": _("share name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("share description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["project"],
                    {
                        "help": _("share project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("comma separated list of tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["share_proto"],
                    {
                        "help": _("share protocol. A valid value is NFS, CIFS, GlusterFS, HDFS, or CephFS"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["size"],
                    {
                        "help": _("the share size, in GBs"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["share_type"],
                    {
                        "help": _("The share type id."),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-snapshot_id"],
                    {
                        "help": _("The id of the share's base snapshot."),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-share_group_id"],
                    {
                        "help": _("The id of the share group."),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": _("id of the network to use"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subnet"],
                    {
                        "help": _("id of the subnet to use"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-metadata"],
                    {
                        "help": _("One or more metadata key and value pairs as a dictionary of strings."),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-availability_zone"],
                    {
                        "help": _("The availability zone."),
                        "action": "store",
                        "type": str,
                        "default": "nova",
                    },
                ),
            ]
        ),
    )
    def share_add(self):
        container = self.app.pargs.container
        name = self.app.pargs.name
        project = self.app.pargs.project
        share_proto = self.app.pargs.share_proto
        size = self.app.pargs.size
        share_type = self.app.pargs.share_type
        data = {
            "container": container,
            "name": name,
            "project": project,
            "share_proto": share_proto,
            "size": size,
            "share_type": share_type,
        }
        self.add_field_from_pargs_to_data("desc", data, "desc")
        self.add_field_from_pargs_to_data("tags", data, "tags")
        self.add_field_from_pargs_to_data("snapshot_id", data, "snapshot_id")
        self.add_field_from_pargs_to_data("share_group_id", data, "share_group_id")
        self.add_field_from_pargs_to_data("network", data, "network")
        self.add_field_from_pargs_to_data("subnet", data, "subnet")
        self.add_field_from_pargs_to_data("metadata", data, "metadata")
        self.add_field_from_pargs_to_data("availability_zone", data, "availability_zone")
        uri = f"{self.baseuri}/shares"
        res = self.cmp_post(uri, data={"share": data})
        self.app.render({"msg": f"add share {res['uuid']}"})

    @ex(
        help=_("delete share"),
        description=_("delete share"),
        arguments=PARGS(
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
    def share_del(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/shares/{oid}"
        self.cmp_delete(uri, data="", entity=f"share {oid}")

    @ex(
        help=_("get share types"),
        description=_("get share types"),
        arguments=PARGS(
            [
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
    def share_type_get(self):
        orchestrator = self.app.pargs.orchestrator
        uri = f"{self.baseuri}/shares/types"
        res = self.cmp_get(uri, data=f"container={orchestrator}")
        headers = ["id", "name", "snapshot_support", "backend"]
        fields = [
            "id",
            "name",
            "extra_specs.snapshot_support",
            "extra_specs.share_backend_name",
        ]
        self.app.render(res, key="share_types", headers=headers, fields=fields)

    #
    # share grant
    #
    @ex(
        help=_("add share grant"),
        description=_("add share grant"),
        arguments=PARGS(
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
                    ["access_level"],
                    {"help": _("rw, ro"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["access_type"],
                    {
                        "help": _("access type like ip or user"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["access_to"],
                    {
                        "help": _("access to like ###.###.###.###/24 or admin/user"),
                        "action": "store",
                        "type": str,
                        "default": None,
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
        uri = f"{self.baseuri}/shares/{oid}/grant"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"Add grant to share {oid}: {res['uuid']}"})

    @ex(
        help=_("delete share grant"),
        description=_("delete share grant"),
        arguments=PARGS(
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
        data = {"share_grant": {"access_id": access_id}}
        uri = f"{self.baseuri}/shares/{oid}/grant"
        self.cmp_delete(uri, data=data, entity=f"share {oid} grant {access_id}")

    #
    # share network
    #
    @ex(
        help=_("get share networks"),
        description=_("get share networks"),
        arguments=ARGS(
            [
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
    def share_network_get(self):
        orchestrator = self.app.pargs.orchestrator
        uri = f"{self.baseuri}/shares/networks"
        res = self.cmp_get(uri, data=f"container={orchestrator}").get("share_networks")
        headers = [
            "id",
            "name",
            "project_id",
            "created_at",
            "neutron_net_id",
            "neutron_subnet_id",
        ]
        fields = [
            "id",
            "name",
            "project_id",
            "created_at",
            "neutron_net_id",
            "neutron_subnet_id",
        ]
        self.app.render(res, headers=headers, fields=fields)
