# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex

from beecell.types.type_string import truncate, str2bool
from beecell.types.type_dict import dict_get
from beecell.types.type_id import id_gen

from beehive3_cli.core.controller import BASE_ARGS, BaseController, PARGS, ARGS
from beehive3_cli.plugins.vsphere.controllers.manage_datasource.app import ManageDatasourceApp
from beehive3_cli.translate import _


class VsphereController(BaseController):
    class Meta:
        label = "res_vsphere"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("vsphere orchestrator")
        help = _("vsphere orchestrator")

        cmp = {"baseuri": "/v1.0/nrs/vsphere", "subsystem": "resource"}

        headers = [
            "id",
            "uuid",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
        ]
        fields = [
            "id",
            "uuid",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
        ]

        ds_headers = [
            "id",
            "uuid",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "accessible",
            "maintenanceMode",
            "freespace",
            "type",
        ]
        ds_fields = [
            "id",
            "uuid",
            "ext_id",
            "name",
            "desc",
            "parent",
            "container",
            "state",
            "details.accessible",
            "details.maintenanceMode",
            "details.freespace",
            "details.type",
        ]

        server_headers = [
            "id",
            "uuid",
            "ext_id",
            "name",
            "parent",
            "container",
            "state",
            "runstate",
            "ip-address",
            "hostname",
            "cp",
            "ram",
            "disk",
            "is-template",
        ]
        server_fields = [
            "id",
            "uuid",
            "ext_id",
            "name",
            "parent",
            "container",
            "state",
            "details.state",
            "details.ip_address",
            "details.hostname",
            "details.cpu",
            "details.ram",
            "details.disk",
            "details.template",
        ]

        flavor_headers = [
            "id",
            "uuid",
            "ext_id",
            "name",
            "parent",
            "container",
            "state",
            "vcpus",
            "ram",
            "disk",
            "version",
            "guest_id",
        ]
        flavor_fields = [
            "id",
            "uuid",
            "ext_id",
            "name",
            "parent",
            "container",
            "state",
            "details.vcpus",
            "details.ram",
            "details.disk",
            "details.version",
            "details.guest_id",
        ]

        vt_headers = [
            "id",
            "uuid",
            "ext_id",
            "name",
            "parent",
            "container",
            "state",
            "disk_iops",
            "tag",
        ]
        vt_fields = [
            "id",
            "uuid",
            "ext_id",
            "name",
            "parent",
            "container",
            "state",
            "details.disk_iops",
            "tag",
        ]

        vol_headers = [
            "id",
            "uuid",
            "ext_id",
            "name",
            "parent",
            "container",
            "state",
            "status",
            "size",
            "bootable",
            "encrypted",
            "volume_type",
        ]
        vol_fields = [
            "id",
            "uuid",
            "ext_id",
            "name",
            "parent",
            "container",
            "state",
            "details.status",
            "details.size",
            "details.bootable",
            "details.encrypted",
            "details.volume_type",
        ]

    def pre_command_run(self):
        super().pre_command_run()

        self.configure_cmp_api_client()

    def get_containers(self):
        uri = "/v1.0/nrs/containers"
        containers = self.cmp_get(uri).get("resourcecontainers", [])
        c_idx = {str(c["id"]): c["name"] for c in containers}
        return c_idx

    @ex(
        help=_("get datacenters"),
        description=_("get datacenters"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("datacenter id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def datacenter_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/datacenters/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("datacenter")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/datacenters"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="datacenters",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    @ex(
        help=_("get folders"),
        description=_("get folders"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("folder id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def folder_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/folders/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("folder")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/folders"
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="folders", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("get datastores"),
        description=_("get datastores"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("datastore id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-container"],
                    {
                        "help": _("container id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def datastore_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/datastores/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("datastore")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "container"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/datastores"

            def render(self, res, **kwargs):
                self.app.render(
                    res,
                    key="datastores",
                    headers=self._meta.ds_headers,
                    fields=self._meta.ds_fields,
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render)

    @ex(
        help=_("get clusters"),
        description=_("get clusters"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("cluster id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def cluster_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/clusters/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("cluster")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/clusters"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="clusters",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    @ex(
        help=_("get distributed virtual switches"),
        description=_("get distributed virtual switches"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("distributed virtual switch id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dvs_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/network/dvss/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("dvs")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/network/dvss"
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="dvss", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("get distributed virtual port groups"),
        description=_("get distributed virtual port groups"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("distributed virtual port group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dvpg_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/network/dvpgs/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("dvpg")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/network/dvpgs"
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="dvpgs", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("get nsx managers"),
        description=_("get nsx managers"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("nsx manager id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def nsx_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/network/nsxs/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("nsx")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/network/nsxs"
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="nsxs", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("get nsx security groups"),
        description=_("get nsx security groups"),
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
    def nsx_security_group_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/network/nsx_security_groups/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("nsx_security_group")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/network/nsx_security_groups"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="nsx_security_groups",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    def __edge_fw_config(self, features):
        firewall = features.get("firewall", {})
        global_config = firewall.pop("globalConfig", {})
        default_policy = firewall.pop("defaultPolicy", {})
        rules = firewall.pop("firewallRules", {}).get("firewallRule", {})
        if isinstance(rules, dict):
            rules = [rules]

        for r in rules:
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

        self.c("\nFIREWALL", "bold")
        self.c("\nglobal config", "underline")
        self.app.render(global_config, details=True)
        self.c("\ndefault policy", "underline")
        self.app.render(default_policy, details=True)
        self.c("\nrules", "underline")
        headers = [
            "id",
            "name",
            "type",
            "action",
            "enabled",
            "tag",
            "loggingEnabled",
            "source",
            "destination",
            "application",
        ]
        fields = [
            "id",
            "name",
            "ruleType",
            "action",
            "enabled",
            "ruleTag",
            "loggingEnabled",
            "source",
            "destination",
            "application",
        ]
        self.app.render(rules, table_style="grid", headers=headers, fields=fields, maxsize=200)

    def __edge_nat_config(self, features):
        rules = []
        nat = features.get("nat", {})
        natrules = nat.pop("natRules", {})
        if natrules is not None:
            natrule = natrules.get("natRule", {})
            if not isinstance(natrule, list):
                natrule = [natrule]
            rules = natrule

        self.c("\nNAT", "bold")
        self.c("\nrules", "underline")
        headers = [
            "id",
            "desc",
            "type",
            "action",
            "vnic",
            "enabled",
            "origAddr",
            "origPort",
            "transAddress",
            "transPort",
            "dnatMatchSourceAddr",
            "dnatMatchSourcePort",
            "isLogged",
            "enabled",
            "protocol",
        ]
        fields = [
            "ruleId",
            "description",
            "ruleType",
            "action",
            "vnic",
            "enabled",
            "originalAddress",
            "originalPort",
            "translatedAddress",
            "translatedPort",
            "dnatMatchSourceAddress",
            "dnatMatchSourcePort",
            "loggingEnabled",
            "enabled",
            "protocol",
        ]
        self.app.render(rules, table_style="grid", headers=headers, fields=fields, maxsize=30)

    def __edge_vpn_config(self, l2vpn, ipsec, sslvpn_config):
        advanced_config = sslvpn_config.pop("advancedConfig", {})
        server_settings = sslvpn_config.pop("serverSettings", {})
        client_configuration = sslvpn_config.pop("clientConfiguration", {})
        layout_configuration = sslvpn_config.pop("layoutConfiguration", {})
        ip_address_pools = sslvpn_config.pop("ipAddressPools", {}).get("ipAddressPool", [])
        private_networks = sslvpn_config.pop("privateNetworks", {}).get("privateNetwork", [])
        users = sslvpn_config.pop("users", {}).get("user", [])
        client_install_packages = sslvpn_config.pop("clientInstallPackages", {}).get("clientInstallPackage", {})
        authentication_configuration = sslvpn_config.pop("authenticationConfiguration", {})
        self.c("\nL2VPN", "bold")
        self.app.render(l2vpn, details=True)
        self.c("\nIPSEC", "bold")
        self.app.render(ipsec, details=True)
        self.c("\nSSL VPN", "bold")
        self.app.render(sslvpn_config, details=True)
        self.c("\nserver settings", "underline")
        self.app.render(server_settings, details=True)
        self.c("\nadvanced config", "underline")
        self.app.render(advanced_config, details=True)
        self.c("\nclient configuration", "underline")
        self.app.render(client_configuration, details=True)
        self.c("\nlayout configuration", "underline")
        self.app.render(layout_configuration, details=True)
        self.c("\nclient install packages", "underline")
        self.app.render(client_install_packages, details=True)
        self.c("\nauthentication configuration", "underline")
        self.app.render(authentication_configuration, details=True)
        self.c("\nip address pools", "underline")
        headers = [
            "objectId",
            "ipRange",
            "netmask",
            "gateway",
            "primaryDns",
            "secondaryDns",
            "dnsSuffix",
            "winsServer",
            "description",
            "description",
            "enabled",
        ]
        self.app.render(ip_address_pools, headers=headers)
        self.c("\nprivate networks", "underline")
        headers = [
            "objectId",
            "network",
            "sendOverTunnel.optimize",
            "description",
            "enabled",
        ]
        self.app.render(private_networks, headers=headers)
        self.c("\nusers", "underline")
        headers = [
            "objectId",
            "userId",
            "firstName",
            "lastName",
            "description",
            "disableUserAccount",
            "passwordNeverExpires",
            "allowChangePassword.changePasswordOnNextLogin",
        ]
        self.app.render(users, headers=headers)

    def __edge_lb_config(self, load_balancer):
        monitor = load_balancer.pop("monitor", {})
        application_profile = load_balancer.pop("applicationProfile", {})
        pools = load_balancer.pop("pool", {})
        virtual_server = load_balancer.pop("virtualServer", {})

        self.c("\nLOAD BALANCER", "bold")
        self.app.render(load_balancer, details=True)
        self.c("\nmonitor", "underline")
        headers = ["monitorId", "type", "interval", "timeout", "maxRetries", "name"]
        self.app.render(monitor, table_style="grid", headers=headers, maxsize=50)
        self.c("\napplication profile", "underline")
        headers = [
            "applicationProfileId",
            "name",
            "insertXForwardedFor",
            "sslPassthrough",
            "template",
            "serverSslEnabled",
            "persistence.method",
        ]
        self.app.render(application_profile, table_style="grid", headers=headers, maxsize=50)

        self.c("\npool", "underline")
        headers = ["poolId", "name", "algorithm", "transparent", "member"]
        if not pools:
            self.app.render(pools, headers=headers)
        else:

            def print_members(members):
                if isinstance(members, str):
                    members = []
                if isinstance(members, dict):
                    members = [members]
                res = []
                for m in members:
                    m["port"] = m.get("port", m.get("monitorPort"))
                    res.append(
                        f"id:{m['memberId']}, name:{m['name']}, ip:{m['ipAddress']}, "
                        f"weight:{m['weight']}, monitorPort:{m['monitorPort']}, "
                        f"port:{m['port']}, maxConn:{m['maxConn']}, "
                        f"minConn:{m['minConn']}, condition:{m['condition']}"
                    )
                return "\n".join(res)

            transform = {"member": print_members}
            self.app.render(
                pools,
                table_style="grid",
                headers=headers,
                transform=transform,
                maxsize=1000,
            )

        self.c("\nvirtual server", "underline")
        headers = [
            "virtualServerId",
            "name",
            "description",
            "enabled",
            "ipAddress",
            "protocol",
            "port",
            "connectionLimit",
            "connectionRateLimit",
            "defaultPoolId",
            "applicationProfileId",
            "enableServiceInsertion",
            "accelerationEnabled",
        ]
        self.app.render(virtual_server, table_style="grid", headers=headers, maxsize=50)

    def __edge_routing_config(self, routing, ospf_useless):
        config = routing.pop("routingGlobalConfig", {})
        default_route = dict_get(routing, "staticRouting.defaultRoute")
        static_routes = dict_get(routing, "staticRouting.staticRoutes.route", default={})
        ospf = routing.pop("ospf", {})
        ospf_areas = ospf.pop("ospfAreas", {}).get("ospfArea", [])
        self.c("\nROUTING", "bold")
        self.app.render(config, details=True)
        self.c("\ndefault routes", "underline")
        headers = ["vnic", "mtu", "description", "gatewayAddress", "adminDistance"]
        self.app.render(default_route, headers=headers, maxsize=50)
        self.c("\nstatic routes", "underline")
        headers = ["mtu", "description", "type", "network", "nextHop", "adminDistance"]
        self.app.render(static_routes, headers=headers, maxsize=50)
        self.c("\nospf", "underline")
        self.app.render(ospf, details=True)
        self.c("\nospf areas", "underline")
        headers = ["areaId", "type", "authentication.type"]
        self.app.render(ospf_areas, headers=headers, maxsize=50)

    @ex(
        help=_("get nsx edges"),
        description=_("get nsx edges"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def nsx_edge_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/network/nsx_edges/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("nsx_edge")
                details = res.pop("details", {})
                settings = details.pop("cliSettings", {})
                autoconfiguration = details.pop("autoConfiguration", {})
                querydaemon = details.pop("queryDaemon", {})
                dnsclient = details.pop("dnsClient", {})
                features = details.pop("features", {})
                appliances = details.pop("appliances", {}).get("appliance", [])
                syslog = features.get("syslog", {})
                l2vpn = features.get("l2Vpn", {})
                sslvpn_config = features.get("sslvpnConfig", {})
                ipsec = features.get("ipsec", {})
                load_balancer = features.get("loadBalancer", {})
                routing = features.get("routing", {})
                ospf = features.get("ospf", {})
                high_availability = features.get("highAvailability", {})
                dns = features.get("dns", {})
                dhcp = features.get("dhcp", {})
                gslb = features.get("gslb", {})
                vnics = details.pop("vnics", {}).get("vnic", [])
                feature_list = [
                    {"feature": k, "version": v["version"], "enabled": v["enabled"]}
                    for k, v in features.items()
                    if isinstance(v, dict) is True
                ]

                self.app.render(res, details=True)
                self.c("\nbase configuration", "underline")
                self.app.render(details, details=True)
                self.c("\nsyslog", "underline")
                self.app.render(
                    syslog,
                    headers=["ipAddress", "protocol"],
                    fields=["serverAddresses.ipAddress", "protocol"],
                )
                self.c("\nautoConfiguration", "underline")
                self.app.render(autoconfiguration, headers=["enabled", "rulePriority"])
                self.c("\nqueryDaemon", "underline")
                self.app.render(querydaemon, headers=["enabled", "port"])
                self.c("\ndnsClient", "underline")
                self.app.render(dnsclient, headers=["primaryDns", "secondaryDns", "domainName"])
                self.c("\ncliSettings", "underline")
                self.app.render(settings, details=True)
                self.c("\nappliances", "underline")
                headers = [
                    "vmId",
                    "vmHostname",
                    "vmName",
                    "hostName",
                    "deployed",
                    "haAdminState",
                ]
                self.app.render(appliances, headers=headers)
                self.c("\nvnics", "underline")
                headers = [
                    "index",
                    "name",
                    "label",
                    "type",
                    "mtu",
                    "isConnected",
                    "portgroupId",
                    "primaryAddress",
                    "enableProxyArp",
                    "enableSendRedirects",
                ]
                fields = [
                    "index",
                    "name",
                    "label",
                    "type",
                    "mtu",
                    "isConnected",
                    "portgroupId",
                    "addressGroups.addressGroup.primaryAddress",
                    "enableProxyArp",
                    "enableSendRedirects",
                ]
                self.app.render(vnics, headers=headers, fields=fields)

                self.c("\nFEATURES", "bold")
                self.app.render(feature_list, headers=["feature", "enabled", "version"])

                self.c("\nHIGH AVAILABILITY", "bold")
                self.app.render(high_availability, details=True)
                self.c("\nDNS", "bold")
                self.app.render(dns, details=True)
                self.c("\nDHCP", "bold")
                self.app.render(dhcp, details=True)
                self.c("\nGSLB", "bold")
                self.app.render(gslb, details=True)

                self.__edge_routing_config(routing, ospf)
                self.__edge_vpn_config(l2vpn, ipsec, sslvpn_config)
                self.__edge_lb_config(load_balancer)
                self.__edge_fw_config(features)
                self.__edge_nat_config(features)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/network/nsx_edges"

            def render(self, res, **kwargs):
                self.app.render(
                    res,
                    key="nsx_edges",
                    headers=self._meta.headers,
                    fields=self._meta.fields,
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render, pagesize=20)

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
                details = res.pop("details")
                volumes = details.pop("volumes")
                networks = details.pop("networks")
                flavor = details.pop("flavor")
                tools = details.pop("vsphere:tools")
                sgs = details.pop("security_groups")
                self.app.render(res, details=True)
                self.c("\ndetails", "underline")
                self.app.render(details, details=True)
                self.c("\nguest Tools", "underline")
                self.app.render(tools, headers=["status", "version"])
                self.c("\nflavor", "underline")
                self.app.render(flavor, headers=["id", "cpu", "memory"])
                self.c("\nnetworks", "underline")
                self.app.render(
                    networks,
                    headers=[
                        "name",
                        "mac_addr",
                        "dns",
                        "fixed_ips",
                        "net_id",
                        "port_state",
                    ],
                )
                self.c("\nsecurity groups", "underline")
                self.app.render(sgs, headers=["id", "uuid", "name"])
                self.c("\nvolumes", "underline")
                headers = [
                    "uuid",
                    "name",
                    "name",
                    "disk_object_id",
                    "storage",
                    "size",
                    "unit_number",
                    "bootable",
                    "thin",
                    "mode",
                ]
                headers = [
                    "uuid",
                    "name",
                    "vsphere:name",
                    "disk_object_id",
                    "storage",
                    "size",
                    "unit_number",
                    "bootable",
                    "thin",
                    "mode",
                ]
                self.app.render(volumes, headers=headers, maxsize=100)

            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/servers"

            def render(self, res, **kwargs):
                self.app.render(
                    res,
                    key="servers",
                    headers=self._meta.server_headers,
                    fields=self._meta.server_fields,
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render, pagesize=20)

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
        help=_("get server hardware"),
        description=_("get server hardware"),
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
    def server_hw(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/servers/{oid}/hw"
        res = self.cmp_get(uri)

        if self.is_output_text():
            res = res.get("server_hardware")
            file_layout = res.pop("file_layout")
            files = file_layout.pop("files")
            other = res.pop("other")
            network = res.pop("network")
            storage = res.pop("storage")
            controllers = other.pop("controllers")
            pci = other.pop("pci")
            input_devices = other.pop("input_devices")
            self.app.render(res, details=True)
            self.c("\nnetwork", "underline")
            self.app.render(
                network,
                headers=[
                    "type",
                    "name",
                    "key",
                    "connected",
                    "network.name",
                    "network.dvs",
                    "network.vlan",
                    "macaddress",
                ],
            )
            self.c("\nstorage", "underline")
            self.app.render(
                storage,
                headers=[
                    "type",
                    "name",
                    "size",
                    "datastore.file_name",
                    "datastore.disk_mode",
                    "datastore.write_through",
                ],
                maxsize=200,
            )
            self.c("\nfile layout", "underline")
            self.app.render(file_layout, details=True)
            self.app.render(
                files,
                headers=["accessible", "name", "uniqueSize", "key", "type", "size"],
                maxsize=200,
            )
            self.c("\ncontrollers", "underline")
            self.app.render(controllers, headers=["type", "name", "key"])
            self.c("\npci", "underline")
            self.app.render(pci, headers=["type", "name", "key"])
            self.c("\ninput devices", "underline")
            self.app.render(input_devices, headers=["type", "name", "key"])
        else:
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
        self.app.render(res, details=True)

    @ex(
        help=_("get server guest"),
        description=_("get server guest"),
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
    def server_guest(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/servers/{oid}/guest"
        res = self.cmp_get(uri)

        if self.is_output_text():
            res = res.get("server_guest")

            guest = res.pop("guest")
            tools = res.pop("tools")
            disk = res.pop("disk")
            nics = res.pop("nics")
            ip_stack = res.pop("ip_stack")
            self.app.render(res, details=True)
            self.c("\nGuest", "underline")
            self.app.render(guest, details=True)
            self.c("\ntools", "underline")
            self.app.render(tools, details=True)
            self.c("\ndisks", "underline")
            self.app.render(disk, headers=["diskPath", "capacity", "free_space"], maxsize=100)
            self.c("\nnics", "underline")
            self.app.render(
                nics,
                headers=[
                    "netbios_config",
                    "network",
                    "dnsConfig",
                    "connected",
                    "ip_config",
                    "mac_address",
                    "device_config_id",
                ],
            )
            self.c("\nip_stacks", "underline")
            for item in ip_stack:
                self.app.render(
                    item.get("dns_config"),
                    headers=[
                        "dhcp",
                        "search_domain",
                        "hostname",
                        "ip_address",
                        "domainname",
                    ],
                )
                self.app.render(item.get("ip_route_config"), headers=["network", "gateway"])
        else:
            self.app.render(res, details=True)

    @ex(
        help=_("get vsphere server snapshots"),
        description=_("get vsphere server snapshots"),
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
        help=_("add vsphere server snapshot"),
        description=_("add vsphere server snapshot"),
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
        snapshot = self.app.pargs.snapshot
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"add_snapshot": {"snapshot": snapshot}}}
        self.cmp_put(uri, data=data)

    @ex(
        help=_("delete vsphere server snapshot"),
        description=_("delete vsphere server snapshot"),
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

    @ex(
        help=_("revert vsphere server to snapshot"),
        description=_("revert vsphere server to snapshot"),
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

    @ex(
        help=_("add vsphere server security group"),
        description=_("add vsphere server security group"),
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
    def server_sg_add(self):
        oid = self.app.pargs.id
        security_group = self.app.pargs.sg
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"add_security_group": {"security_group": security_group}}}
        self.cmp_put(uri, data=data)

    @ex(
        help=_("delete vsphere server security group"),
        description=_("delete vsphere server security group"),
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
        help=_("add some volumes to server"),
        description=_("add some volumes to server"),
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
                    ["volume_type"],
                    {
                        "help": _("volume type id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-volume_num"],
                    {
                        "help": _("volume number"),
                        "action": "store",
                        "type": int,
                        "default": 2,
                    },
                ),
            ]
        ),
    )
    def server_volume_adds(self):
        oid = self.app.pargs.id
        volume_type = self.app.pargs.volume_type
        vol_num = self.app.pargs.volume_num

        # get server
        uri = f"{self.baseuri}/servers/{oid}"
        server = self.cmp_get(uri).get("server")

        container = server.get("container")
        folder = server.get("parent")
        size = 1
        for __ in vol_num:
            name = server.get("name") + "-volume-" + id_gen()

            uri = f"{self.baseuri}/volumes"
            data = {
                "volume": {
                    "container": str(container),
                    "name": name,
                    "desc": name,
                    "folder": str(folder),
                    "size": size,
                    "volume_type": volume_type,
                }
            }
            res = self.cmp_post(uri, data)
            self.app.render({"msg": f"add volume {res.get('uuid')}"})

            uri = f"{self.baseuri}/servers/{oid}/action"
            data = {"server_action": {"add_volume": {"volume": res.get("uuid")}}}
            self.cmp_put(uri, data=data)
            self.app.render({"msg": f"add volume {res.get('uuid')} to server {oid}"})

    @ex(
        help=_("del volume from server"),
        description=_("del volume from server"),
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
                (
                    ["-propagate"],
                    {
                        "help": _("if true detach and delete volume"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
    )
    def server_volume_del(self):
        oid = self.app.pargs.id
        volume = self.app.pargs.volume
        propagate = str2bool(self.app.pargs.propagate)
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"del_volume": {"volume": volume}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"del volume {volume} from server {oid}"})

        if propagate is True:
            uri = f"{self.baseuri}/volumes/{volume}"
            self.cmp_delete(uri, entity=f"del volume {volume}", confirm=False)

    @ex(
        help=_("extend server volume"),
        description=_("extend server volume"),
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
                (["size"], {"help": _("volume size"), "action": "store", "type": str}),
            ]
        ),
    )
    def server_volume_extend(self):
        oid = self.app.pargs.id
        volume = self.app.pargs.volume
        size = self.app.pargs.size
        uri = f"{self.baseuri}/servers/{oid}/action"
        data = {"server_action": {"extend_volume": {"volume": volume, "volume_size": size}}}
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"extend volume {volume} of server {oid} to size {size} GiB"})

    @ex(
        help=_("del volumes from server"),
        description=_("del volumes from server"),
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
    def server_volume_dels(self):
        oid = self.app.pargs.id

        # get server
        uri = f"{self.baseuri}/servers/{oid}"
        server = self.cmp_get(uri).get("server")

        for v in dict_get(server, "details.volumes"):
            if v["bootable"] is True:
                continue

            volume = v["uuid"]
            uri = f"{self.baseuri}/servers/{oid}/action"
            data = {"server_action": {"del_volume": {"volume": volume}}}
            self.cmp_put(uri, data=data)
            self.app.render({"msg": f"del volume {volume} from server {oid}"})

            uri = f"{self.baseuri}/volumes/{volume}"
            self.cmp_delete(uri, entity=f"del volume {volume}", confirm=False)

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
        help=_("start sserver"),
        description=_("start server"),
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
        help=_("resize server"),
        description=_("resize server"),
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
        help=_("add flavor"),
        description=_("add flavor"),
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
                        "help": _("flavor name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["datacenter"],
                    {
                        "help": _("datacenter id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-core_x_socket"],
                    {
                        "help": _("core x socket"),
                        "action": "store",
                        "type": int,
                        "default": 1,
                    },
                ),
                (
                    ["vcpus"],
                    {"help": _("vcpus"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-guest_id"],
                    {
                        "help": _("guest id"),
                        "action": "store",
                        "type": str,
                        "default": "centos64Guest",
                    },
                ),
                (
                    ["ram"],
                    {"help": _("ram"), "action": "store", "type": int, "default": None},
                ),
                (
                    ["disk"],
                    {"help": _("disk"), "action": "store", "type": int, "default": None},
                ),
                (
                    ["-version"],
                    {
                        "help": _("version"),
                        "action": "store",
                        "type": str,
                        "default": "vmx-11",
                    },
                ),
            ]
        ),
    )
    def flavor_add(self):
        container = self.app.pargs.container
        name = self.app.pargs.name
        datacenter = self.app.pargs.datacenter
        core_x_socket = self.app.pargs.core_x_socket
        vcpus = self.app.pargs.vcpus
        guest_id = self.app.pargs.guest_id
        ram = self.app.pargs.ram
        disk = self.app.pargs.disk
        version = self.app.pargs.version
        data = {
            "container": container,
            "name": name,
            "desc": name,
            "datacenter": datacenter,
            "core_x_socket": core_x_socket,
            "vcpus": vcpus,
            "guest_id": guest_id,
            "ram": ram,
            "disk": disk,
            "version": version,
        }
        uri = f"{self.baseuri}/flavors"
        res = self.cmp_post(uri, data={"flavor": data})
        self.app.render({"msg": f"Add flavor: {truncate(res)}"})

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
                (
                    ["-container"],
                    {
                        "help": _("container id"),
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

                uri = f"{self.baseuri}/volumetypes/{oid}/datastores"
                res = self.cmp_get(uri).get("datastores", [])
                res = sorted(res, key=lambda i: i["name"])
                self.c("\ndatastore", "underline")
                self.app.render(
                    res,
                    headers=["id", "uuid", "name", "state", "tag", "size", "freespace"],
                )
            else:
                self.app.render(res, details=True)
        else:
            params = ["container"]
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/volumetypes"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="volumetypes",
                headers=self._meta.vt_headers,
                fields=self._meta.vt_fields,
            )

    @ex(
        help=_("add volumetype"),
        description=_("add volumetype"),
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
                        "help": _("flavor name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["datacenter"],
                    {
                        "help": _("datacenter id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-disk_iops"],
                    {
                        "help": _("disk_iops. -1 set no limit"),
                        "action": "store",
                        "type": int,
                        "default": -1,
                    },
                ),
            ]
        ),
    )
    def volumetype_add(self):
        container = self.app.pargs.container
        name = self.app.pargs.name
        datacenter = self.app.pargs.datacenter
        disk_iops = self.app.pargs.disk_iops
        data = {
            "container": container,
            "name": name,
            "desc": name,
            "datacenter": datacenter,
            "disk_iops": disk_iops,
        }
        uri = f"{self.baseuri}/volumetypes"
        res = self.cmp_post(uri, data={"volumetype": data})
        self.app.render({"msg": f"Add volumetype: {truncate(res)}"})

    @ex(
        help=_("add datastore to volumetype"),
        description=_("add datastore to volumetype"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("volumetype id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["datastore"],
                    {
                        "help": _("datastore id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tag"],
                    {
                        "help": _("datastore tag"),
                        "action": "store",
                        "type": str,
                        "default": "default",
                    },
                ),
            ]
        ),
    )
    def volumetype_datastore_add(self):
        oid = self.app.pargs.id
        datastore = self.app.pargs.datastore
        tag = self.app.pargs.tag
        uri = f"{self.baseuri}/volumetypes/{oid}/datastores"
        data = {"datastore": {"uuid": datastore, "tag": tag}}
        self.cmp_post(uri, data)
        self.app.render({"msg": f"add datastore {datastore} to volumetype"})

    @ex(
        help=_("remove datastore from volumetype"),
        description=_("remove datastore from volumetype"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("volumetype id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["datastore"],
                    {
                        "help": _("datastore id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volumetype_datastore_del(self):
        oid = self.app.pargs.id
        datastore = self.app.pargs.datastore
        uri = f"{self.baseuri}/volumetypes/{oid}/datastores"
        data = {
            "datastore": {
                "uuid": datastore,
            }
        }
        self.cmp_delete(uri, data, entity=f"datastore {datastore}")

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
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/volumes"

            def render(self, res, **kwargs):
                self.app.render(
                    res,
                    key="volumes",
                    headers=self._meta.vol_headers,
                    fields=self._meta.vol_fields,
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render, pagesize=20)

    @ex(
        help=_("add volume"),
        description=_("add volume"),
        arguments=PARGS(
            [
                (
                    ["container"],
                    {"help": _("vsphere container id"), "action": "store", "type": str},
                ),
                (["name"], {"help": _("volume name"), "action": "store", "type": str}),
                (["folder"], {"help": _("folder id"), "action": "store", "type": str}),
                (["size"], {"help": _("volume size"), "action": "store", "type": str}),
                (
                    ["volume_type"],
                    {"help": _("volume type"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def volume_add(self):
        container = self.app.pargs.container
        name = self.app.pargs.name
        folder = self.app.pargs.folder
        size = self.app.pargs.size
        volume_type = self.app.pargs.volume_type
        uri = f"{self.baseuri}/volumes"
        data = {
            "volume": {
                "container": container,
                "name": name,
                "desc": name,
                "folder": folder,
                "size": size,
                "volume_type": volume_type,
            }
        }
        res = self.cmp_post(uri, data)
        self.app.render({"msg": f"add volume {res.get('uuid')}"})


    @ex(
        help=_("datasource manage"),
        description=_("datasource manager"),
        arguments=BASE_ARGS,
    )
    def datastore_manage(self):
        app = ManageDatasourceApp()
        app.set_parent(self)
        app.run()
