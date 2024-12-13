# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from sys import stdout
from datetime import datetime
from time import sleep
from cement.ext.ext_argparse import ex
from beecell.types.type_string import truncate, str2bool
from beecell.types.type_list import merge_list
from beecell.types.type_date import format_date
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import BaseController, BASE_ARGS, StringAction
from beehive3_cli.core.util import load_environment_config, load_config, rotating_bar


def VSPHERE_ARGS(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": "vsphere platform reference label",
            },
        ),
        (
            ["-P", "--project"],
            {
                "action": "store",
                "dest": "project",
                "help": "vsphere current project name",
            },
        ),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class VspherePlatformController(BaseController):
    class Meta:
        label = "vsphere"
        stacked_on = "platform"
        stacked_type = "nested"
        description = "vsphere platform"
        help = "vsphere platform"

        server_headers = [
            "id",
            "parent",
            "name",
            "os",
            "state",
            "ip_address",
            "hostname",
            "cpu",
            "ram",
            "template",
        ]
        host_headers = [
            "id",
            "name",
            "parent",
            "overallStatus",
            "biosVersion",
            "numCpuThreads",
            "memorySize",
            "model",
            "bootTime",
            "connectionState",
            "server",
        ]
        respool_headers = ["id", "name", "parent"]
        cluster_headers = [
            "id",
            "name",
            "parent",
            "overallStatus",
            "host",
            "totalMemory",
            "numCpuThreads",
        ]
        dc_headers = ["id", "name", "parent", "overallStatus"]
        datastore_headers = [
            "id",
            "name",
            "overallStatus",
            "accessible",
            "size",
            "freespace",
            "maintenanceMode",
            "type",
        ]
        folder_headers = ["id", "parent", "type", "name", "desc", "overallStatus"]
        vapp_headers = ["id", "parent", "name", "overallStatus"]
        dvs_headers = ["id", "parent", "name", "overallStatus"]
        dvpg_headers = ["id", "parent", "name", "overallStatus"]
        securitygroup_headers = ["id", "name", "rules"]
        lg_headers = ["objectId", "name", "tenant", "vdnId"]
        lg_fields = ["objectId", "description", "tenantId", "vdnId"]
        ippool_headers = [
            "objectId",
            "name",
            "dnsSuffix",
            "gateway",
            "ipRange      startAddress      endAddress",
            "totalAddressCount",
            "usedAddressCount",
        ]
        ippool_fields = [
            "objectId",
            "name",
            "dnsSuffix",
            "gateway",
            "ipRanges",
            "totalAddressCount",
            "usedAddressCount",
        ]
        ipset_headers = ["objectId", "name", "value"]
        edge_headers = ["id", "name", "type", "status", "state", "datacenter"]
        edge_fields = [
            "objectId",
            "name",
            "edgeType",
            "edgeStatus",
            "state",
            "datacenterName",
        ]
        edge_headers1 = [
            "id",
            "name",
            "type",
            "status",
            "state",
            "datacenter",
            "primaryAddress",
            "secondaryAddresses",
        ]
        edge_fields1 = [
            "objectId",
            "name",
            "edgeType",
            "edgeStatus",
            "state",
            "datacenterName",
            "vnic.addressGroups.addressGroup.primaryAddress",
            "vnic.addressGroups.addressGroup.secondaryAddresses.ipAddress",
        ]
        dlr_headers = ["objectId", "name", "value"]

    def pre_command_run(self):
        from beedrones.vsphere.client import VsphereManager

        super(VspherePlatformController, self).pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("vsphere", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No vsphere default platform is available for this environment. Select " "another environment"
                )

        if label not in orchestrators:
            raise Exception("Valid label are: %s" % ", ".join(orchestrators.keys()))
        conf = orchestrators.get(label)

        conf.get("vcenter")["pwd"] = str(conf.get("vcenter")["pwd"])
        conf.get("nsx")["pwd"] = str(conf.get("nsx")["pwd"])

        if self.app.config.get("log.clilog", "verbose_log"):
            host_vcenter = conf.get("vcenter", {}).get("host", None)
            host_nsx = conf.get("nsx", {}).get("host", None)

            # log to stdout and to logfile
            self.app.print(
                f"Using vsphere orchestrator: {label} (vcenter: {host_vcenter} - nsx: {host_nsx})", color="YELLOW"
            )
            self.app.log.debug(f"Using vsphere orchestrator: {label} (vcenter: {host_vcenter} - nsx: {host_nsx})")

        self.client = VsphereManager(conf.get("vcenter"), conf.get("nsx"), key=self.key)

    def wait_task(self, task):
        bar = rotating_bar()

        def trace():
            # stdout.write(".")
            stdout.write(next(bar))
            stdout.flush()

        self.client.wait_task(task, delta=1, trace=trace)

    @ex(help="ping vsphere", description="ping vsphere", arguments=VSPHERE_ARGS())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(
        help="get vsphere version",
        description="get vsphere version",
        example="beehive platform vsphere version;beehive platform vsphere version -e <env>",
        arguments=VSPHERE_ARGS(),
    )
    def version(self):
        res = self.client.version()
        if self.is_output_text():
            version_vcenter = res.get("vcenter")
            version_nsx = res.get("nsx")
            self.app.render(
                [{"which": "vcenter", "version": version_vcenter}, {"which": "nsx", "version": version_nsx}],
                headers=["", "version"],
                fields=["which", "version"],
            )
        else:
            self.app.render({"version": res}, headers=["version"])

    @ex(
        help="get vsphere nsx manager info",
        description="get vsphere nsx manager info",
        arguments=VSPHERE_ARGS(),
    )
    def nsx_manager_info(self):
        res = self.client.system.nsx.summary_info()
        res1 = self.client.system.nsx.query_appliance_syslog()
        res2 = self.client.system.nsx.components_summary()
        res.update(res1)
        components = []
        entries = dict_get(res2, "componentsByGroup.entry", default=[])
        for item in entries:
            comps = dict_get(item, "components.component", default=[])
            if isinstance(comps, dict):
                comps = [comps]
            for item2 in comps:
                components.append(item2)

        self.app.render(res, details=True)
        self.c("\ncomponents", "underline")
        self.app.render(
            components,
            headers=[
                "componentId",
                "componentGroup",
                "name",
                "description",
                "status",
                "enabled",
            ],
        )

    @ex(
        help="reboot vsphere nsx manager",
        description="reboot vsphere nsx manager",
        arguments=VSPHERE_ARGS(),
    )
    def nsx_manager_reboot(self):
        res = self.client.system.nsx.reboot_appliance()
        self.app.render(res, details=True)

    @ex(
        help="get vsphere nsx manager events",
        description="get vsphere nsx manager events",
        arguments=VSPHERE_ARGS(),
    )
    def nsx_manager_event_get(self):
        res = self.client.system.nsx.get_system_events()
        sort = dict_get(res, "pagingInfo.sortOrderAscending")
        if sort == "false":
            sort = "DESC"
        else:
            sort = "ASC"
        res["page"] = round(
            int(dict_get(res, "pagingInfo.startIndex")) / int(dict_get(res, "pagingInfo.pageSize")),
            0,
        )
        res["count"] = dict_get(res, "pagingInfo.pageSize")
        res["total"] = dict_get(res, "pagingInfo.totalCount")
        res["sort"] = {"field": dict_get(res, "pagingInfo.sortBy"), "order": sort}
        self.app.render(
            res,
            key="systemEvent",
            headers=[
                "eventId",
                "timestamp",
                "severity",
                "eventSource",
                "eventCode",
                "module",
                "message",
            ],
        )

    @ex(
        help="get vsphere nsx manager controllers",
        description="get vsphere nsx manager controllers",
        arguments=VSPHERE_ARGS(),
    )
    def nsx_controller_get(self):
        res = self.client.system.nsx.list_controllers()
        self.app.render(
            res,
            fields=[
                "id",
                "name",
                "status",
                "ipAddress",
                "version",
                "virtualMachineInfo.name",
                "hostInfo.name",
                "clusterInfo.name",
                "datastoreInfo.name",
            ],
            headers=[
                "id",
                "name",
                "status",
                "ipAddress",
                "version",
                "vm",
                "host",
                "cluster",
                "datastore",
            ],
            maxsize=200,
        )

    @ex(
        help="get datacenters",
        description="get datacenters",
        example="beehive platform vsphere datacenter-get -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "cluster id",
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
            res = self.client.datacenter.get(oid)

            if self.is_output_text():
                self.app.render(self.client.datacenter.detail(res), details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            objs = self.client.datacenter.list(**params)
            res = []
            for o in objs:
                res.append(self.client.datacenter.info(o))
            self.app.render(res, headers=self._meta.dc_headers)

    @ex(
        help="get datacenter sessions",
        description="get datacenter sessions",
        arguments=VSPHERE_ARGS(),
    )
    def datacenter_sessions(self):
        res = self.client.datacenter.sessions()
        headers = [
            "key",
            "user_name",
            "login_time",
            "last_active_time",
            "locale",
            "ip_address",
            "user_agent",
        ]
        self.app.render(res, headers=headers)

    @ex(
        help="get clusters",
        description="get clusters",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "cluster id",
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
            res = self.client.cluster.get(oid)

            if self.is_output_text():
                res1 = self.client.cluster.get_servers(oid)
                servers = []
                for s in res1:
                    servers.append(self.client.server.info(s))

                res2 = self.client.cluster.resource_pool.list(oid)
                respools = []
                for s in res2:
                    respools.append(self.client.cluster.resource_pool.info(s))

                res3 = self.client.cluster.host.list(cluster=oid)
                hosts = []
                for s in res3:
                    hosts.append(self.client.cluster.host.info(s))

                self.app.render(self.client.cluster.detail(res), details=True)
                self.c("\nhosts", "underline")
                self.app.render(hosts, headers=self._meta.host_headers)
                self.c("\nresource pools", "underline")
                self.app.render(respools, headers=self._meta.respool_headers)
                self.c("\nservers", "underline")
                self.app.render(servers, headers=self._meta.server_headers)
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            objs = self.client.cluster.list(**params)
            res = []
            for o in objs:
                res.append(self.client.cluster.info(o))
            if self.is_output_text():
                self.app.render(res, headers=self._meta.cluster_headers)
            else:
                self.app.render({"clusters": res}, details=True)

    @ex(
        help="get hosts",
        description="get hosts",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "host id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.cluster.host.get(oid)
            data = self.client.cluster.host.detail(res)

            if self.is_output_text():
                res1 = self.client.cluster.host.get_servers(oid)
                servers = []
                for s in res1:
                    servers.append(self.client.server.info(s))

                self.app.render(data, details=True)
                self.c("\nservers", "underline")
                self.app.render(servers, headers=self._meta.server_headers)
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            objs = self.client.cluster.host.list(**params)
            res = []
            for o in objs:
                d = self.client.cluster.host.info(o)
                d["bootTime"] = str(d["bootTime"])
                res.append(d)
            if self.is_output_text():
                self.app.render(res, headers=self._meta.host_headers)
            else:
                self.app.render({"hosts": res}, details=True)

    @ex(
        help="get resource pools",
        description="get resource pools",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "resource pool id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def respool_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.cluster.resource_pool.get(oid)

            if self.is_output_text():
                self.app.render(self.client.cluster.resource_pool.detail(res), details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            objs = self.client.cluster.resource_pool.list(**params)
            res = []
            for o in objs:
                res.append(self.client.cluster.resource_pool.info(o))
            self.app.render(res, headers=self._meta.respool_headers)

    @ex(
        help="delete resource pool",
        description="delete resource pool",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "resource pool id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def respool_del(self):
        oid = self.app.pargs.id
        respool = self.client.cluster.resource_pool.get(oid)
        res = self.client.cluster.resource_pool.remove(respool)
        self.app.render({"msg": "delete resource pool %s" % oid})

    @ex(
        help="get datastores",
        description="get datastores",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "datastore id",
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
            res = self.client.datastore.get(oid)
            data = self.client.datastore.detail(res)

            if self.is_output_text():
                # res1 = self.client.datastore.get_servers(oid)
                # servers = []
                # for s in res1:
                #     servers.append(self.client.server.info(s))

                self.app.render(data, details=True)
                # self.c('\nservers', 'underline')
                # self.app.render(servers, headers=self._meta.server_headers)
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            objs = self.client.datastore.list(**params)
            res = []
            for o in objs:
                res.append(self.client.datastore.info(o))
            self.app.render(res, headers=self._meta.datastore_headers)

    @ex(
        help="get folders",
        description="get folders",
        example="beehive platform vsphere folder-get -id group-v261 -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "folder id",
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
            res = self.client.folder.get(oid)
            data = self.client.folder.detail(res)

            if self.is_output_text():
                res1 = self.client.folder.get_servers(oid)
                servers = []
                for s in res1:
                    servers.append(self.client.server.info(s))

                self.app.render(data, details=True)
                self.c("\nservers", "underline")
                self.app.render(servers, headers=self._meta.server_headers)
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            objs = self.client.folder.list(**params)
            res = []
            for o in objs:
                res.append(self.client.folder.info(o))
            self.app.render(res, headers=self._meta.folder_headers)

    @ex(
        help="add vsphere folder",
        description="add vsphere folder",
        arguments=VSPHERE_ARGS(
            [
                (["name"], {"help": "folder name", "action": "store", "type": str}),
                (
                    ["desc"],
                    {
                        "help": "folder description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-datacenter"],
                    {
                        "help": "parent datacenter morid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-folder"],
                    {
                        "help": "parent folder morid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def folder_add(self):
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        folder = self.app.pargs.folder
        datacenter = self.app.pargs.datacenter
        if folder is not None:
            folder = self.client.folder.get(folder)
        if datacenter is not None:
            datacenter = self.client.datacenter.get(datacenter)
        msg = self.client.folder.create(name, desc=desc, folder=folder, datacenter=datacenter, vm=True)
        self.app.render({"msg": "add folder %s" % name})

    @ex(
        help="update vsphere folder",
        description="update vsphere folder",
        example="beehive platform vsphere folder-update group-xxxx -desc <description>.notifysan-preprod -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "folder id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "folder name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "folder description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-datacenter"],
                    {
                        "help": "parent datacenter morid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-folder"],
                    {
                        "help": "parent folder morid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def folder_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        folder = self.client.folder.get(oid)
        res = self.client.folder.update(folder, name, desc)
        self.app.render({"msg": "update folder %s" % oid})

    @ex(
        help="delete vsphere folder",
        description="delete vsphere folder",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "folder id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def folder_del(self):
        oid = self.app.pargs.id
        obj = self.client.folder.get(oid)
        task = self.client.folder.remove(obj)
        self.wait_task(task)
        self.app.render({"msg": "Delete folder %s" % oid})

    @ex(
        help="get servers",
        description="get servers",
        example="beehive platform vsphere server-get -id vm-xxxx -e <env> ;beehive platform vsphere server-get -names xxxxx-1 -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "server name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-names"],
                    {
                        "help": "filter by name like",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-template"],
                    {
                        "help": "true list only template",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ipaddress"],
                    {
                        "help": "server ipaddress",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dnsname"],
                    {
                        "help": "server dnsname",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-cluster"],
                    {
                        "help": "cluster id",
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
        cluster = self.app.pargs.cluster
        if oid is not None:
            res = self.client.server.get(oid)
            data = self.client.server.detail(res)

            if self.is_output_text():
                if res is None:
                    self.app.render(data, details=True)
                else:
                    self.app.pargs.notruncate = True
                    volumes = data.pop("volumes", [])
                    networks = data.pop("networks", [])
                    config_data = self.client.server.hardware.get_config_data(res)
                    file_layout = config_data.pop("file_layout", {})
                    config_data.pop("network", {})
                    config_data.pop("storage", {})
                    files = file_layout.pop("files", [])
                    video = config_data.pop("video", {})
                    other = config_data.pop("other", {})
                    controllers = other.pop("controllers", {})
                    input_devices = other.pop("input_devices", {})
                    pci = other.pop("pci", {})
                    sg = self.client.server.security_groups(res)

                    self.app.render(data, details=True)
                    self.c("\nconfiguration", "underline")
                    self.app.render(config_data, details=True)
                    self.c("\nfile_layout - base", "underline")
                    self.app.render(file_layout, details=True)
                    self.c("\nfile_layout - files", "underline")
                    self.app.render(
                        files,
                        headers=[
                            "key",
                            "name",
                            "type",
                            "size",
                            "uniqueSize",
                            "accessible",
                        ],
                        maxsize=200,
                    )
                    self.c("\ndevice - video", "underline")
                    self.app.render(video, details=True)
                    self.c("\ndevice - controllers", "underline")
                    self.app.render(controllers, headers=["name", "type", "key"])
                    self.c("\ndevice - input devices", "underline")
                    self.app.render(input_devices, headers=["name", "type", "key"])
                    self.c("\ndevice - pci", "underline")
                    self.app.render(pci, headers=["name", "type", "key"])
                    self.c("\nnetworks", "underline")
                    self.app.render(
                        networks,
                        headers=[
                            "name",
                            "mac_addr",
                            "dns",
                            "fixed_ipv4s",
                            "net_id",
                            "port_state",
                        ],
                    )
                    self.c("\nsecurity groups", "underline")
                    self.app.render(sg, headers=["objectId", "name"])
                    self.c("\nvolumes", "underline")
                    self.app.render(
                        volumes,
                        maxsize=200,
                        headers=[
                            "id",
                            "name",
                            "storage",
                            "size",
                            "unit_number",
                            "thin",
                            "mode",
                            "disk_object_id",
                        ],
                    )
            else:
                self.app.render(data, details=True)
        else:
            if cluster is not None:
                objs = self.client.cluster.get_servers(cluster)
            else:
                name = self.app.pargs.name
                names = self.app.pargs.names
                template = self.app.pargs.template
                ipaddress = self.app.pargs.ipaddress
                dnsname = self.app.pargs.dnsname

                project = self.app.pargs.project
                if project:
                    # e.g. ComputeService-4567...
                    folders = self.client.folder.get_folders_by_name(project)
                    if len(folders) == 0:
                        raise Exception("No projects found matching: %s" % project)

                    objs = []
                    for f in folders:
                        servers = self.client.folder.get_servers(f["obj"]._moId)
                        if servers and len(servers) > 0:
                            objs.extend(servers)
                else:
                    # get folders
                    folders = self.client.folder.list()

                    # get servers
                    objs = self.client.server.list(
                        name=name, names=names, template=template, ipaddress=ipaddress, dnsname=dnsname
                    )

            folder_idx = {}
            for f in folders:
                oid = f["obj"]._moId
                custom_values = f.get("customValue")
                if len(custom_values) > 0:
                    folder_idx[oid] = custom_values[0].value
                else:
                    folder_idx[oid] = f["name"]

            res = []
            for o in objs:
                if o is not None:
                    info = self.client.server.info(o)
                    info["parent"] = folder_idx.get(info["parent"], info["parent"])
                    res.append(info)
            self.app.render(res, headers=self._meta.server_headers, maxsize=30)

    @ex(
        help="add vsphere server [todo:]",
        description="add vsphere server",
        arguments=VSPHERE_ARGS(
            [
                (["name"], {"help": "server name", "action": "store", "type": str}),
                (
                    ["startip"],
                    {
                        "help": "start ip",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["stopip"],
                    {
                        "help": "stop ip",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["gw"],
                    {
                        "help": "gateway",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["dns1"],
                    {"help": "dns1", "action": "store", "type": str, "default": None},
                ),
                (
                    ["dns2"],
                    {"help": "dns2", "action": "store", "type": str, "default": None},
                ),
                (
                    ["-prefix"],
                    {"help": "prefix", "action": "store", "type": int, "default": 24},
                ),
                (
                    ["-dnssuffix"],
                    {
                        "help": "dns zone",
                        "action": "store",
                        "type": str,
                        "default": "domain.local",
                    },
                ),
            ]
        ),
    )
    def server_add(self):
        name = self.app.pargs.name
        startip = self.app.pargs.startip
        stopip = self.app.pargs.stopip
        gw = self.app.pargs.gw
        dns1 = self.app.pargs.dns1
        dns2 = self.app.pargs.dns2
        prefix = self.app.pargs.prefix
        dnssuffix = self.app.pargs.dnssuffix
        self.client.server.exists(pool_range=(startip, stopip))
        msg = self.client.server.create(
            name,
            prefix=prefix,
            gateway=gw,
            dnssuffix=dnssuffix,
            dns1=dns1,
            dns2=dns2,
            startip=startip,
            stopip=stopip,
        )
        self.app.render({"msg": "add server %s" % name})

    @ex(
        help="delete vsphere server",
        description="delete vsphere server",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
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
        server = self.client.server.get_by_morid(oid)
        try:
            self.client.server.stop(server)
            # self.wait_task(task)
        except:
            pass
        task = self.client.server.remove(server)
        self.wait_task(task)
        self.app.render({"msg": "Delete server %s" % oid})

    @ex(
        help="get vsphere server console",
        description="get vsphere server console",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
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
        server = self.client.server.get_by_morid(oid)
        res = self.client.server.remote_console(server)
        self.app.render(res, details=True)

    @ex(
        help="get vsphere server devices",
        description="get vsphere server devices",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_device_get(self):
        oid = self.app.pargs.id
        server = self.client.server.get_by_morid(oid)
        res = self.client.server.hardware.get_devices(server)
        self.app.render(
            res,
            headers=["key", "unitNumber", "summary", "label", "device type", "backing"],
        )

    @ex(
        help="get vsphere server guest info",
        description="get vsphere server guest info",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_guest_info(self):
        oid = self.app.pargs.id
        server = self.client.server.get_by_morid(oid)
        res = self.client.server.guest_info(server)
        self.app.render(res, details=True)

    @ex(
        help="run vsphere server command using guest tool",
        description="run vsphere server command using guest tool",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["cmd"],
                    {
                        "help": "command",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["user"],
                    {"help": "user", "action": "store", "type": str, "default": None},
                ),
                (
                    ["pwd"],
                    {
                        "help": "password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-params"],
                    {
                        "help": "command params. Use + as space",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
            ]
        ),
    )
    def server_guest_run_cmd(self):
        oid = self.app.pargs.id
        ps_path = self.app.pargs.cmd
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        params = " ".join(self.app.pargs.params.split("+"))

        server = self.client.server.get_by_morid(oid)
        res = self.client.server.guest_utils.guest_execute_command(
            server,
            user,
            pwd,
            path_to_program=ps_path,
            program_arguments=params,
            program=params,
        )

    @ex(
        help="disable vsphere server firewall",
        description="disable vsphere server firewall",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": "server admin password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_disable_firewall(self):
        oid = self.app.pargs.id
        pwd = self.app.pargs.pwd
        server = self.client.server.get_by_morid(oid)
        res = self.client.server.guest_disable_firewall(server, pwd)
        self.app.render({"msg": "disable server %s firewall" % oid})

    @ex(
        help="copy ssh key on server",
        description="copy ssh key on server",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["user"],
                    {"help": "user", "action": "store", "type": str, "default": None},
                ),
                (
                    ["pwd"],
                    {
                        "help": "password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pubkey"],
                    {
                        "help": "ssh public key to set. Specify file name where key is stored",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
            ]
        ),
    )
    def server_ssh_copy_id(self):
        oid = self.app.pargs.id
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        pub_key = self.app.pargs.pubkey
        key = load_config(pub_key)
        server = self.client.server.get_by_morid(oid)
        res = self.client.server.guest_setup_ssh_key(server, user, pwd, key)
        self.app.render(res)

    @ex(
        help="change vsphere server password",
        description="change vsphere server password",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["user"],
                    {"help": "user", "action": "store", "type": str, "default": None},
                ),
                (
                    ["pwd"],
                    {
                        "help": "password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["newpwd"],
                    {
                        "help": "new password",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
            ]
        ),
    )
    def server_ssh_change_pwd(self):
        oid = self.app.pargs.id
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        newpwd = self.app.pargs.newpwd
        server = self.client.server.get_by_morid(oid)
        res = self.client.server.guest_setup_admin_password(server, user, pwd, newpwd)
        self.app.render(res)

    @ex(
        help="setup vsphere server network",
        description="setup vsphere server network",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["user"],
                    {"help": "user", "action": "store", "type": str, "default": None},
                ),
                (
                    ["pwd"],
                    {
                        "help": "password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ipaddr"],
                    {
                        "help": "ip address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-prefix"],
                    {
                        "help": "ip address",
                        "action": "store",
                        "type": int,
                        "default": 24,
                    },
                ),
                (
                    ["-macaddr"],
                    {
                        "help": "mac address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["gw"],
                    {
                        "help": "network gateway",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["hostname"],
                    {
                        "help": "hostname",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["dns"],
                    {
                        "help": "comma separated list of dns",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["dns_search"],
                    {
                        "help": "dns search",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_network_setup(self):
        oid = self.app.pargs.id
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        ipaddr = self.app.pargs.ipaddr
        prefix = self.app.pargs.prefix
        macaddr = self.app.pargs.macaddr
        gw = self.app.pargs.gw
        hostname = self.app.pargs.hostname
        dns = " ".join(self.app.pargs.dns.split(","))
        dns_search = self.app.pargs.dns_search
        server = self.client.server.get_by_morid(oid)
        # res = self.client.server.guest_setup_network2(
        #     server,
        #     pwd,
        #     ipaddr,
        #     macaddr,
        #     gw,
        #     hostname,
        #     dns,
        #     dns_search,
        #     conn_name="net01",
        #     user=user,
        #     prefix=prefix,
        # )
        res = self.client.server.guest_setup_network(
            server,
            pwd,
            ipaddr,
            macaddr,
            gw,
            hostname,
            self.app.pargs.dns,
            dns_search,
            conn_name="net01",
            user=user,
            prefix=prefix,
        )

        self.app.render(res)

    @ex(
        help="setup vsphere server network",
        description="setup vsphere server network",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["user"],
                    {"help": "user", "action": "store", "type": str, "default": None},
                ),
                (
                    ["pwd"],
                    {
                        "help": "password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ipaddr"],
                    {
                        "help": "ip address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_network_destroy_config(self):
        oid = self.app.pargs.id
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        ipaddr = self.app.pargs.ipaddr
        server = self.client.server.get_by_morid(oid)
        res = self.client.server.guest_destroy_network_config(server, pwd, ipaddr)
        self.app.render(res)

    @ex(
        help="get vsphere server security groups",
        description="get vsphere security groups",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def server_sg_get(self):
        oid = self.app.pargs.id
        server = self.client.server.get_by_morid(oid)
        res = self.client.server.security_groups(server)
        self.app.render(res, headers=["objectId", "name"])

    @ex(
        help="add security to server",
        description="add security to server",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["sgid"],
                    {
                        "help": "security group id",
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
        sgid = self.app.pargs.sgid
        res = self.client.server.security_group_add(oid, sgid)
        self.app.render({"msg": "add security group %s to server %s" % (sgid, oid)})

    @ex(
        help="remove security from server",
        description="remove security from server",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["sgid"],
                    {
                        "help": "security group id",
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
        sgid = self.app.pargs.sgid
        res = self.client.server.security_group_del(oid, sgid)
        self.app.render({"msg": "remove security group %s from server %s" % (sgid, oid)})

    @ex(
        help="start vsphere server",
        description="start vsphere server",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def server_start(self):
        oid = self.app.pargs.id
        server = self.client.server.get_by_morid(oid)
        task = self.client.server.start(server)
        self.wait_task(task)

    @ex(
        help="stop vsphere server",
        description="stop vsphere server",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def server_stop(self):
        oid = self.app.pargs.id
        server = self.client.server.get_by_morid(oid)
        self.client.server.stop(server)
        # self.wait_task(task)

    @ex(
        help="get disk of vsphere server",
        description="get disk of vsphere server",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_disk_get(self):
        oid = self.app.pargs.id
        server = self.client.server.get_by_morid(oid)
        volumes = self.client.server.volumes(server)
        headers = [
            "id",
            "disk_object_id",
            "mode",
            "name",
            "size",
            "storage",
            "unit_number",
            "thin",
        ]
        self.app.render(volumes, headers=headers)

    @ex(
        help="add disk to vsphere server",
        description="add disk to vsphere server",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["server_id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["size"],
                    {
                        "help": "disk size",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["datastore_id"],
                    {
                        "help": "datastore id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_disk_add(self):
        oid = self.app.pargs.server_id
        size = self.app.pargs.size
        datastore = self.app.pargs.datastore_id
        server = self.client.server.get_by_morid(oid)
        datastore = self.client.datastore.get(datastore)
        disk_unit_number = self.client.server.get_available_hard_disk_unit_number(server)
        task = self.client.server.hardware.add_hard_disk(
            server, size, datastore, disk_type="thin", disk_unit_number=disk_unit_number
        )
        self.wait_task(task)

    @ex(
        help="delete disk from vsphere server",
        description="delete disk from vsphere server",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["server_id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["disk_object_id"],
                    {
                        "help": "disk object id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_disk_del(self):
        oid = self.app.pargs.server_id
        disk_object_id = self.app.pargs.disk_object_id
        server = self.client.server.get_by_morid(oid)
        task = self.client.server.hardware.delete_hard_disk(server, disk_object_id)
        self.wait_task(task)

    @ex(
        help="extend disk of vsphere server",
        description="delete disk from vsphere server",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["disk_object_id"],
                    {
                        "help": "disk object id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["size"],
                    {
                        "help": "disk size in Gb",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_disk_extend(self):
        oid = self.app.pargs.id
        disk_object_id = self.app.pargs.disk_object_id
        size = self.app.pargs.size
        server = self.client.server.get_by_morid(oid)
        task = self.client.server.hardware.extend_hard_disk(server, disk_object_id, size)
        self.wait_task(task)

    @ex(
        help="get vsphere server snapshot",
        description="get vsphere server snapshot",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-snapshot"],
                    {
                        "help": "snapshot id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_snapshot_get(self):
        oid = self.app.pargs.id
        snapshot = self.app.pargs.snapshot
        if snapshot is not None:
            server = self.client.server.get_by_morid(oid)
            snapshot = self.client.server.snapshot.get(server, snapshot)
            childs = snapshot.get("childs", [])
            childs_str = "".join(map(str, childs))
            snapshot.update({"childs": childs_str})
            self.app.render(snapshot, details=True)
        else:
            server = self.client.server.get_by_morid(oid)
            snapshots = self.client.server.snapshot.list(server)
            for sn in snapshots:
                childs = sn.get("childs", [])
                childs_str = "".join(map(str, childs))
                sn.update({"childs": childs_str})
            self.app.render(
                snapshots,
                headers=["id", "name", "creation_date", "state", "quiesced", "childs"],
            )

    @ex(
        help="create vsphere server snapshot",
        description="create vsphere server snapshot",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": "snapshot name",
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
        server = self.client.server.get_by_morid(oid)
        task = self.client.server.snapshot.create(server, name)
        self.wait_task(task)

    @ex(
        help="delete vsphere server snapshot",
        description="delete vsphere server snapshot",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["snapshot"],
                    {
                        "help": "snapshot id",
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
        server = self.client.server.get_by_morid(oid)
        task = self.client.server.snapshot.remove(server, snapshot)
        self.wait_task(task)

    @ex(
        help="revert vsphere server to snapshot",
        description="revert vsphere server to snapshot",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["snapshot"],
                    {
                        "help": "snapshot id",
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
        server = self.client.server.get_by_morid(oid)
        task = self.client.server.snapshot.revert(server, snapshot)
        self.wait_task(task)

    #
    # vapp
    #
    @ex(
        help="get vapps",
        description="get vapps",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "vapp id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def vapp_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.vapp.get(oid)
            data = self.client.vapp.detail(res)

            if self.is_output_text():
                self.app.render(data, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            objs = self.client.vapp.list(**params)
            res = []
            for o in objs:
                res.append(self.client.vapp.info(o))
            self.app.render(res, headers=self._meta.vapp_headers)

    @ex(
        help="get dvss",
        description="get dvss",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {"help": "dvs id", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def dvs_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.network.get_distributed_virtual_switch(oid)
            data = self.client.network.detail_distributed_virtual_switch(res)

            if self.is_output_text():
                self.app.render(data, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            objs = self.client.network.list_distributed_virtual_switches(**params)
            res = []
            for o in objs:
                res.append(self.client.network.info_distributed_virtual_switch(o))
            self.app.render(res, headers=self._meta.dvs_headers)

    @ex(
        help="get dvpgs",
        description="get dvpgs",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "dvpg id",
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
            res = self.client.network.get_network(oid)
            data = self.client.network.detail_network(res)

            if self.is_output_text():
                res1 = self.client.network.get_network_servers(oid)
                servers = []
                for s in res1:
                    servers.append(self.client.server.info(s))

                self.app.render(data, details=True)
                self.c("\nservers", "underline")
                self.app.render(servers, headers=self._meta.server_headers)
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            objs = self.client.network.list_networks(**params)
            res = []
            for o in objs:
                res.append(self.client.network.info_network(o))
            self.app.render(res, headers=self._meta.dvpg_headers, maxsize=200)

    @ex(
        help="add vsphere dvpg",
        description="add vsphere dvpg",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "dvpg name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["vlan"],
                    {
                        "help": "dvpg vlan",
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["dvs"],
                    {
                        "help": "dvpg dvs",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dvpg_add(self):
        name = self.app.pargs.name
        vlan = self.app.pargs.vlan
        dvs_id = self.app.pargs.dvs
        dvs = self.client.network.get_distributed_virtual_switch(dvs_id)
        task = self.client.network.create_distributed_port_group(name, name, vlan, dvs, numports=24)
        self.wait_task(task)
        self.app.render({"msg": "create dvpg %s" % name})

    @ex(
        help="delete vsphere dvpg",
        description="delete vsphere dvpg",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "dvpg id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dvpg_del(self):
        oid = self.app.pargs.id
        obj = self.client.network.get_network(oid)
        if obj is not None:
            task = self.client.network.remove_network(obj)
            self.wait_task(task)
            self.app.render({"msg": "delete dvpg %s" % oid})

    @ex(
        help="get securitygroups",
        description="get securitygroups",
        example="beehive platform vsphere sg-get securitygroup-######;beehive platform vsphere sg-get securitygroup-##### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "securitygroup id",
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
            res = self.client.network.nsx.sg.get(oid)
            data = self.client.network.nsx.sg.detail(res)

            if self.is_output_text():
                members = res.pop("member", [])
                self.app.render(res, details=True)
                self.c("\nmembers", "underline")
                self.app.render(members, headers=["objectId", "name", "objectTypeName"])
                rules = self.client.network.nsx.dfw.filter_rules(security_groups=[oid])
                self.c("\nrules", "underline")
                self.app.render(
                    rules,
                    headers=[
                        "id",
                        "name",
                        "sectionId",
                        "direction",
                        "logged",
                        "packetType",
                    ],
                )
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            objs = self.client.network.nsx.sg.list(**params)
            res = []
            sg_ids = []
            for obj in objs:
                res.append(self.client.network.nsx.sg.info(obj))
                sg_ids.append(obj["id"])
            rules = self.client.network.nsx.dfw.index_rules(security_groups=sg_ids)

            for item in res:
                item["rules"] = len(rules.get(item["id"], []))
            self.app.render(res, headers=self._meta.securitygroup_headers)

            self.entity_class = self.client.network.nsx.sg

    @ex(
        help="delete vsphere securitygroup",
        description="delete vsphere securitygroup",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "securitygroup id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": "if true force delete",
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def sg_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        self.client.network.nsx.sg.delete(oid, force)
        self.app.render({"msg": "Delete securitygroup %s" % oid})

    @ex(
        help="delete vsphere securitygroup member",
        description="delete vsphere securitygroup member",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "securitygroup id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["member"],
                    {
                        "help": "member to remove",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def sg_member_del(self):
        oid = self.app.pargs.id
        member = self.app.pargs.member
        self.client.network.nsx.sg.delete_member(oid, member)
        self.app.render({"msg": "Delete security-group %s member %s" % (oid, member)})

    @ex(
        help="add vsphere securitygroup member",
        description="add vsphere securitygroup member",
        example="beehive platform vsphere sg-member-add securitygroup-#### vm-#### -e <env>;beehive platform vsphere sg-member-add securitygroup-##### vm-##### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "securitygroup id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["member"],
                    {
                        "help": "member to add",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def sg_member_add(self):
        oid = self.app.pargs.id
        member = self.app.pargs.member
        self.client.network.nsx.sg.add_member(oid, member)
        self.app.render({"msg": "Add security-group %s member %s" % (oid, member)})

    # dfw
    def __print_sections(self, data, stype):
        sections = data[stype]["section"]
        if type(sections) is not list:
            sections = [sections]
        for s in sections:
            s["timestamp"] = format_date(datetime.fromtimestamp(float(s["timestamp"]) / 1000))
            rules = s.get("rule", [])
            if type(rules) is not list:
                rules = [rules]
            s["rules"] = len(rules)
        self.app.render(
            sections,
            headers=["id", "type", "timestamp", "generationNumber", "name", "rules"],
        )

    def __convert_proto(self, service):
        proto = service.get("protocol")
        subproto = service.get("subProtocol")
        protos = {"6": "tcp", "18": "udp"}
        return protos.get(proto, proto)

    def __set_rule_value(self, key, subkey, rule):
        if rule is not None and isinstance(rule, dict):
            objs = rule.pop(key, {}).pop(subkey, [])
            if isinstance(objs, dict):
                objs = [objs]

            data = []
            if key == "services":
                if len(objs) > 0:
                    data.append("services:")
                    for o in objs:
                        data.append("  %s:%s" % (self.__convert_proto(o), o.get("destinationPort")))
            elif key == "appliedToList":
                if len(objs) > 0:
                    data.append("appliedTo:")
                    for o in objs:
                        data.append("  %s:%s" % (o.get("type"), o.get("value")))
            elif key == "sources":
                if len(objs) > 0:
                    data.append("sources:")
                    for o in objs:
                        data.append("  %s:%s" % (o.get("type"), o.get("value")))
            elif key == "destinations":
                if len(objs) > 0:
                    data.append("destinations:")
                    for o in objs:
                        data.append("  %s:%s" % (o.get("type"), o.get("value")))

            rule[key] = "\n".join(data)
        else:
            rule[key] = ""
        return rule

    def __print_rule_datail(self, title, data):
        if type(data) is not list:
            data = [data]
        self.app.render(data, headers=["type", "name", "value"])

    @ex(
        help="get distributed firewall status",
        description="get distributed firewall status",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-section"],
                    {
                        "help": "section id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def dfw_status(self):
        section = self.app.pargs.section
        if section is not None:
            res = self.client.network.nsx.dfw.query_section_status(section)
        else:
            res = self.client.network.nsx.dfw.query_status()
        if self.format == "text":
            clusters = res.pop("clusterList", {}).get("clusterStatus", [])
            res["startTime"] = format_date(datetime.fromtimestamp(float(res["startTime"]) / 1000))
            self.app.render(res, details=True)
            for cluster in clusters:
                self.c(
                    "\n                                                       ",
                    "underline",
                )
                hosts = cluster.pop("hostStatusList", {}).get("hostStatus", [])
                for host in hosts:
                    host["startTime"] = format_date(datetime.fromtimestamp(float(host["startTime"]) / 1000))
                    host["endTime"] = format_date(datetime.fromtimestamp(float(host["endTime"]) / 1000))
                headers = [
                    "clusterId",
                    "status",
                    "hostId",
                    "hostName",
                    "generationNumber",
                    "errorCode",
                    "startTime",
                    "endTime",
                ]
                self.app.render(cluster, details=True)
                self.c("\nhosts", "underline")
                self.app.render(hosts, headers=headers)
        else:
            self.app.render(res, details=True)

    @ex(
        help="get distributed firewall sections",
        description="get distributed firewall sections",
        example="beehive platform vsphere dfw-section-get -e <env>;beehive platform vsphere dfw-section-get -id 1053 -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "section id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def dfw_section_get(self):
        section = self.app.pargs.id
        if section is not None:
            res = self.client.network.nsx.dfw.get_layer3_section(sectionid=section)

            rules = res.pop("rule", [])
            if isinstance(rules, dict):
                rules = [rules]
            self.app.render([res], headers=["id", "type", "timestamp", "generationNumber", "name"])

            self.c("\nrules", "underline")
            for r in rules:
                r = self.__set_rule_value("services", "service", r)
                r = self.__set_rule_value("sources", "source", r)
                r = self.__set_rule_value("destinations", "destination", r)
                r = self.__set_rule_value("appliedToList", "appliedTo", r)
            headers = [
                "id",
                "disabled",
                "logged",
                "name",
                "dir",
                "action",
                "packet",
                "sources",
                "destinations",
                "services",
                "appliedToList",
            ]
            fields = [
                "id",
                "disabled",
                "logged",
                "name",
                "direction",
                "action",
                "packetType",
                "sources",
                "destinations",
                "services",
                "appliedToList",
            ]

            transform = {"name": lambda x: truncate(x, 30)}

            self.app.render(
                rules,
                table_style="grid",
                headers=headers,
                fields=fields,
                maxsize=50,
                transform=transform,
            )
        else:
            res = self.client.network.nsx.dfw.get_config()
            data = [
                {"key": "contextId", "value": res["contextId"]},
                {"key": "timestamp", "value": res["timestamp"]},
                {"key": "generationNumber", "value": res["generationNumber"]},
            ]
            self.app.render(data, headers=["key", "value"])
            self.c("\nlayer3Sections", "underline")
            self.__print_sections(res, "layer3Sections")
            self.c("\nlayer2Sections", "underline")
            self.__print_sections(res, "layer2Sections")
            self.c("\nlayer3RedirectSections", "underline")
            self.__print_sections(res, "layer3RedirectSections")

    @ex(
        help="check distributed firewall sections",
        description="check distributed firewall sections",
        arguments=VSPHERE_ARGS(),
    )
    def dfw_section_check(self):
        res = self.client.network.nsx.dfw.get_config()
        sections = res["layer3Sections"]["section"]
        if type(sections) is not list:
            sections = [sections]
        for s in sections:
            if s.get("name") == "None":
                print(s.get("id"), s.get("name"))
                self.client.network.nsx.dfw.delete_section(s.get("id"))

    @ex(
        help="get distributed firewall rules",
        description="get distributed firewall rules",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["section"],
                    {
                        "help": "section id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["rule"],
                    {
                        "help": "rule id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dfw_rule_get(self):
        section = self.app.pargs.section
        rule = self.app.pargs.rule

        res = self.client.network.nsx.dfw.get_rule(section, rule)
        # self.app.render(res, details=True)
        services = res.pop("services", {}).pop("service", [])
        sources = res.pop("sources", {}).pop("source", [])
        destinations = res.pop("destinations", {}).pop("destination", [])
        appliedToList = res.pop("appliedToList", {}).pop("appliedTo", [])

        self.app.render(
            res,
            headers=[
                "id",
                "disabled",
                "logged",
                "name",
                "direction",
                "action",
                "packetType",
            ],
        )

        self.__print_rule_datail("sources", sources)
        self.__print_rule_datail("destinations", destinations)
        self.__print_rule_datail("appliedTo", appliedToList)
        self.c("\nservices", "underline")
        if type(services) is not list:
            services = [services]
        self.app.render(
            services,
            headers=["protocol", "subProtocol", "destinationPort", "protocolName"],
        )

    @ex(
        help="add distributed firewall sections",
        description="add distributed firewall sections",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "section name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def dfw_section_add(self):
        name = self.app.pargs.name
        self.client.network.nsx.dfw.query_status()
        self.client.network.nsx.dfw.create_section(name)
        self.app.render({"msg": "add section %s" % name})

    @ex(
        help="delete distributed firewall sections",
        description="delete distributed firewall sections",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["section"],
                    {
                        "help": "section id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def dfw_section_del(self):
        section = self.app.pargs.section
        self.client.network.nsx.dfw.query_status()
        res = self.client.network.nsx.dfw.delete_section(section)
        self.app.render({"msg": "Delete section %s" % section})

    @ex(
        help="add distributed firewall rule",
        description="add distributed firewall rule",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["section"],
                    {
                        "help": "section id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": "rule name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-action"],
                    {
                        "help": "rule action: allow or deny",
                        "action": "store",
                        "type": str,
                        "default": "allow",
                    },
                ),
                (
                    ["-direction"],
                    {
                        "help": "rule name",
                        "action": "store",
                        "type": str,
                        "default": "inout",
                    },
                ),
                (
                    ["-sources"],
                    {
                        "help": "rule sources. Ex. SecurityGroup:securitygroup-#####,Ipv4Address:###.###.###.###/24",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dests"],
                    {
                        "help": "rule sources. Ex. SecurityGroup:securitygroup-#####,Ipv4Address:###.###.###.###/24",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-services"],
                    {
                        "help": "rule services",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-appliedto"],
                    {
                        "help": "rule sources. Ex. DISTRIBUTED_FIREWALL:DISTRIBUTED_FIREWALL",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dfw_rule_add(self):
        section = self.app.pargs.section
        name = self.app.pargs.name
        action = self.app.pargs.action
        direction = self.app.pargs.direction
        sources = self.app.pargs.sources
        dests = self.app.pargs.dests
        services = self.app.pargs.services
        appliedtos = self.app.pargs.appliedto

        if sources is not None:
            source_list = []
            for source in sources.split(","):
                source_item = source.split(":")
                source_list.append({"name": None, "value": source_item[1], "type": source_item[0]})
            sources = source_list

        if dests is not None:
            dest_list = []
            for dest in dests.split(","):
                dest_item = dest.split(":")
                dest_list.append({"name": None, "value": dest_item[1], "type": dest_item[0]})
            dests = dest_list

        if appliedtos is not None:
            appliedto_list = []
            for appliedto in appliedtos.split(","):
                appliedto_item = appliedto.split(":")
                appliedto_list.append(
                    {
                        "name": appliedto_item[1],
                        "value": appliedto_item[1],
                        "type": appliedto_item[0],
                    }
                )
            appliedtos = appliedto_list

        self.client.network.nsx.dfw.get_layer3_section(sectionid=section)
        self.client.network.nsx.dfw.create_rule(
            section,
            name,
            action,
            direction=direction,
            logged="false",
            sources=sources,
            destinations=dests,
            services=services,
            appliedto=appliedtos,
            precedence="default",
        )
        self.app.render({"msg": "add rule %s" % name})

    @ex(
        help="delete distributed firewall rules",
        description="delete distributed firewall rules",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["section"],
                    {
                        "help": "section id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["rules"],
                    {
                        "help": "comma separated list of rules id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dfw_rules_del(self):
        section = self.app.pargs.section
        rules = self.app.pargs.rules.split(",")
        self.client.network.nsx.dfw.get_layer3_section(sectionid=section)
        for rule in rules:
            self.client.network.nsx.dfw.delete_rule(section, rule)
        self.app.render({"msg": "Delete section %s rules %s" % (section, rules)})

    @ex(
        help="get distributed firewall exclusion list",
        description="get distributed firewall exclusion list",
        arguments=VSPHERE_ARGS(),
    )
    def dfw_exclusion_get(self):
        res = self.client.network.nsx.dfw.get_exclusion_list()
        res = res.get("excludeMember", [])
        if not isinstance(res, list):
            res = [res]
        resp = []
        for item in res:
            resp.append(item["member"])
        self.app.render(
            resp,
            headers=["objectId", "name", "scope.name", "objectTypeName", "revision"],
        )

    @ex(
        help="add member to distributed firewall exclusion list",
        description="add member to distributed firewall exclusion list",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["member"],
                    {
                        "help": "member id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def dfw_exclusion_add(self):
        member = self.app.pargs.member
        res = self.client.network.nsx.dfw.add_item_to_exclusion_list(member)
        self.app.render({"msg": "add member %s to exclusion list" % member})

    @ex(
        help="delete member from distributed firewall exclusion list",
        description="delete member from distributed firewall exclusion list",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["member"],
                    {
                        "help": "member id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def dfw_exclusion_del(self):
        member = self.app.pargs.member
        res = self.client.network.nsx.dfw.remove_item_from_exclusion_list(member)
        self.app.render({"msg": "delete member %s from exclusion list" % member})

    @ex(
        help="get nsx transport zones",
        description="get nsx transport zones",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "transport zone id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def transport_zone_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.network.nsx.lg.get_transport_zone(oid)

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.network.nsx.lg.list_transport_zones(**params)
            self.app.render(res, headers=self._meta.lg_headers)

    @ex(
        help="get logical switch",
        description="get logical switch",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "logical switch id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dvpg"],
                    {
                        "help": "dvpg id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def lg_get(self):
        oid = self.app.pargs.id
        dvpg = self.app.pargs.dvpg

        if oid is not None:
            res = self.client.network.nsx.lg.get(oid)

            if self.is_output_text():
                backings = res.pop("vdsContextWithBacking", [])

                self.app.render(res, details=True)
                for backing in backings:
                    context = backing.get("switch")
                    self.c("\nbacking - %s" % context.pop("objectId"), "underline")
                    self.app.render(backing, details=True)
            else:
                self.app.render(res, details=True)

        elif dvpg is not None:
            res = self.client.network.nsx.lg.get_by_dvpg(dvpg)
            if res is None:
                raise Exception("no valid logical switch found for dvpg %s" % dvpg)

            if self.is_output_text():
                backings = res.pop("vdsContextWithBacking", [])

                self.app.render(res, details=True)
                for backing in backings:
                    context = backing.get("switch")
                    self.c("\nbacking - %s" % context.pop("objectId"), "underline")
                    self.app.render(backing, details=True)
            else:
                self.app.render(res, details=True)

        else:
            params = {}
            objs = self.client.network.nsx.lg.list(**params)
            res = []
            sg_ids = []
            for obj in objs:
                res.append(self.client.network.nsx.lg.info(obj))
                sg_ids.append(obj["objectId"])
            self.app.render(res, headers=self._meta.lg_headers, fields=self._meta.lg_fields)

    @ex(
        help="delete logical switch",
        description="delete logical switch",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "logical switch id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def lg_del(self):
        oid = self.app.pargs.id
        self.client.network.nsx.lg.delete(oid)
        self.app.render({"msg": "delete logical switch %s" % oid})

    @ex(
        help="get vsphere ippools",
        description="get ippools",
        example="beehive platform vsphere ippool-get -e <env>;beehive platform vsphere ippool-get -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "ippool id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-range"],
                    {
                        "help": "ippool range",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def ippool_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.network.nsx.ippool.get(oid)
            data = self.client.network.nsx.ippool.detail(res)

            if self.is_output_text():
                self.app.render(data, details=True)
            else:
                self.app.render(res, details=True)
        else:
            range = self.app.pargs.range
            if range is not None:
                range = range.split(",")
            objs = self.client.network.nsx.ippool.list(pool_range=range)
            res = []
            transform = None
            for o in objs:
                res.append(self.client.network.nsx.ippool.info(o))
                transform = {
                    "ipRanges": lambda x: "\n".join(
                        [
                            "{:12} {:17} {}".format(item["id"], item["startAddress"], item["endAddress"])
                            for item in x.get("ipRangeDto")
                        ]
                    )
                }
            self.app.render(
                res,
                headers=self._meta.ippool_headers,
                fields=self._meta.ippool_fields,
                transform=transform,
                maxsize=100,
            )

    @ex(
        help="add vsphere ippool",
        description="add vsphere ippool",
        arguments=VSPHERE_ARGS(
            [
                (["name"], {"help": "ippool name", "action": "store", "type": str}),
                (
                    ["startip"],
                    {
                        "help": "start ip",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["stopip"],
                    {
                        "help": "stop ip",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["gw"],
                    {
                        "help": "gateway",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["dns1"],
                    {"help": "dns1", "action": "store", "type": str, "default": None},
                ),
                (
                    ["dns2"],
                    {"help": "dns2", "action": "store", "type": str, "default": None},
                ),
                (
                    ["-prefix"],
                    {"help": "prefix", "action": "store", "type": int, "default": 24},
                ),
                (
                    ["-dnssuffix"],
                    {
                        "help": "dns zone",
                        "action": "store",
                        "type": str,
                        "default": "domain.local",
                    },
                ),
            ]
        ),
    )
    def ippool_add(self):
        name = self.app.pargs.name
        startip = self.app.pargs.startip
        stopip = self.app.pargs.stopip
        gw = self.app.pargs.gw
        dns1 = self.app.pargs.dns1
        dns2 = self.app.pargs.dns2
        prefix = self.app.pargs.prefix
        dnssuffix = self.app.pargs.dnssuffix
        # self.client.network.nsx.ippool.exists(pool_range=(startip, stopip))
        msg = self.client.network.nsx.ippool.create(
            name,
            prefix=prefix,
            gateway=gw,
            dnssuffix=dnssuffix,
            dns1=dns1,
            dns2=dns2,
            startip=startip,
            stopip=stopip,
        )
        self.app.render({"msg": "add ippool %s" % name})

    @ex(
        help="update vsphere ippool",
        description="update vsphere ippool",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "ippool id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "ippool name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-startip"],
                    {
                        "help": "start ip",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-stopip"],
                    {
                        "help": "stop ip",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-gw"],
                    {
                        "help": "gateway",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dns1"],
                    {"help": "dns1", "action": "store", "type": str, "default": None},
                ),
                (
                    ["-dns2"],
                    {"help": "dns2", "action": "store", "type": str, "default": None},
                ),
                (
                    ["-prefix"],
                    {"help": "prefix", "action": "store", "type": int, "default": None},
                ),
                (
                    ["-dnssuffix"],
                    {
                        "help": "dns zone",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def ippool_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        startip = self.app.pargs.startip
        stopip = self.app.pargs.stopip
        gw = self.app.pargs.gw
        dns1 = self.app.pargs.dns1
        dns2 = self.app.pargs.dns2
        prefix = self.app.pargs.prefix
        dnssuffix = self.app.pargs.dnssuffix
        # self.client.network.nsx.ippool.exists(pool_range=(startip, stopip))
        msg = self.client.network.nsx.ippool.update(
            oid,
            name=name,
            prefixLength=prefix,
            gateway=gw,
            dnsSuffix=dnssuffix,
            dnsServer1=dns1,
            dnsServer2=dns2,
            startAddress=startip,
            endAddress=stopip,
        )
        self.app.render({"msg": "update ippool %s" % oid})

    @ex(
        help="delete vsphere ippool",
        description="delete vsphere ippool",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "ippool id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def ippool_del(self):
        oid = self.app.pargs.id
        obj = self.client.network.nsx.ippool.exists(pool_id=oid)
        self.client.network.nsx.ippool.delete(oid)
        self.app.render({"msg": "Delete ippool %s" % oid})

    @ex(
        help="get all allocated ippool ips",
        description="get all allocated ippool ips",
        example="beehive platform vsphere ippool-ip-usage ipaddresspool-##### -e <env>;beehive platform vsphere ippool-ip-usage ipaddresspool-##### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "ippool id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def ippool_ip_usage(self):
        oid = self.app.pargs.id
        self.client.network.nsx.ippool.exists(pool_id=oid)
        res = self.client.network.nsx.ippool.allocations(oid)
        headers = [
            "id",
            "ipAddress",
            "gateway",
            "dnsSuffix",
            "prefixLength",
            "subnetId",
            "dnsServer1",
            "dnsServer2",
        ]
        self.app.render(res, headers=headers)

    @ex(
        help="assign ippool ip",
        description="assign ippool ip",
        example="beehive platform vsphere ippool-ip-use ipaddresspool-##### -e <env>;beehive platform vsphere ippool-ip-use ipaddresspool-##### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "ippool id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ip"],
                    {
                        "help": "ippool ip to use",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def ippool_ip_use(self):
        oid = self.app.pargs.id
        ip = self.app.pargs.ip
        self.client.network.nsx.ippool.exists(pool_id=oid)
        res = self.client.network.nsx.ippool.allocate(oid, static_ip=ip)
        self.app.render(res, details=True)

    @ex(
        help="release ippool ip",
        description="release ippool ip",
        example="beehive platform vsphere ippool-ip-release ipaddresspool-##### ###.###.###.###;beehive platform vsphere ippool-ip-release ipaddresspool-##### ###.###.###.### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "ippool id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ip"],
                    {
                        "help": "ippool ip to use",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def ippool_ip_release(self):
        oid = self.app.pargs.id
        ip = self.app.pargs.ip
        self.client.network.nsx.ippool.exists(pool_id=oid)
        res = self.client.network.nsx.ippool.release(oid, ip)
        self.app.render(res, details=True)

    @ex(
        help="get ipsets",
        description="get ipsets",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "ipset id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-range"],
                    {
                        "help": "ipset range",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def ipset_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.network.nsx.ipset.get(oid)
            data = self.client.network.nsx.ipset.detail(res)

            if self.is_output_text():
                self.app.render(data, details=True)
            else:
                self.app.render(res, details=True)
        else:
            range = self.app.pargs.range
            if range is not None:
                range = range.split(",")
            objs = self.client.network.nsx.ipset.list()
            res = []
            for o in objs:
                res.append(self.client.network.nsx.ipset.info(o))
            self.app.render(res, headers=self._meta.ipset_headers)

    @ex(
        help="add vsphere ipset",
        description="add vsphere ipset",
        arguments=VSPHERE_ARGS(
            [
                (["name"], {"help": "ipset name", "action": "store", "type": str}),
                (
                    ["desc"],
                    {
                        "help": "ipset description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["cidr"],
                    {
                        "help": "list of ip. Ex. ###.###.###.###-###.###.###.### or cidr",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def ipset_add(self):
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        cidr = self.app.pargs.cidr
        self.client.network.nsx.ipset.create(name, desc, cidr)
        self.app.render({"msg": "add ipset %s" % name})

    @ex(
        help="update vsphere ipset",
        description="update vsphere ipset",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "ipset id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (["-name"], {"help": "ipset name", "action": "store", "type": str}),
            ]
        ),
    )
    def ipset_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        self.client.network.nsx.ipset.update(oid, name=name)
        self.app.render({"msg": "Update ipset %s" % oid})

    @ex(
        help="delete vsphere ipset",
        description="delete vsphere ipset",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "ipset id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def ipset_del(self):
        oid = self.app.pargs.id
        self.client.network.nsx.ipset.delete(oid)
        self.app.render({"msg": "Delete ipset %s" % oid})

    @ex(
        help="get vsphere edges",
        description="get vsphere edges",
        example="beehive platform vsphere edge-get -e <env>;beehive platform vsphere edge-get -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def edge_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.network.nsx.edge.get(oid)
            res = self.client.network.nsx.edge.detail(res)

            if self.is_output_text():
                settings = res.pop("cliSettings", {})
                autoconfiguration = res.pop("autoConfiguration", {})
                querydaemon = res.pop("queryDaemon", {})
                dnsclient = res.pop("dnsClient", {})
                features = res.pop("features", {})
                appliances = res.pop("appliances", [])
                vnics = res.pop("vnics", [])
                self.app.render(res, details=True)
                self.c("\nautoConfiguration", "underline")
                self.app.render(autoconfiguration, headers=["enabled", "rulePriority"])
                self.c("\nqueryDaemon", "underline")
                self.app.render(querydaemon, headers=["enabled", "port"])
                self.c("\ndnsClient", "underline")
                self.app.render(dnsclient, headers=["primaryDns", "secondaryDns", "domainName"])
                self.c("\nsettings", "underline")
                self.app.render(settings, details=True)
                self.c("\nfeatures", "underline")
                self.app.render(features, headers=["feature", "enabled", "version"])
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
            else:
                self.app.render(res, details=True)
        else:
            objs = self.client.network.nsx.edge.list()
            res = []
            for o in objs:
                res.append(self.client.network.nsx.edge.info(o))
            self.app.render(res, headers=self._meta.edge_headers, fields=self._meta.edge_fields)

    @ex(
        help="get vsphere edge job",
        description="get vsphere edge job",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {"help": "job id", "action": "store", "type": str, "default": None},
                )
            ]
        ),
    )
    def edge_job_get(self):
        oid = getattr(self.app.pargs, "id", None)
        res = self.client.network.nsx.edge.get_job(oid)
        self.app.render(res, details=True)

    def __wait_from_edge_job(self, jobid, edge, operation):
        self.app.log.debug("wait for edge job: %s" % jobid)
        res = self.client.network.nsx.edge.get_job(jobid)
        status = res["status"]
        stdout.flush()
        elapsed = 0
        bar = rotating_bar()
        while status not in ["COMPLETED", "FAILED", "ROLLBACK", "TIMEOUT"]:
            # stdout.write(".")
            stdout.write(next(bar))
            stdout.flush()
            sleep(5)
            res = self.client.network.nsx.edge.get_job(jobid)
            status = res["status"]
            elapsed += 5
            if elapsed > 600:
                status = "TIMEOUT"
        print("%s edge %s %s" % (operation, edge, status))

    @ex(
        help="add vsphere edge",
        description="add vsphere edge",
        arguments=VSPHERE_ARGS(
            [
                (["name"], {"help": "edge name", "action": "store", "type": str}),
                (
                    ["datacenter"],
                    {"help": "datacenter mor-id", "action": "store", "type": str},
                ),
                (
                    ["cluster"],
                    {"help": "cluster mor-id", "action": "store", "type": str},
                ),
                (
                    ["datastore"],
                    {"help": "datastore mor-id", "action": "store", "type": str},
                ),
                (
                    ["uplink_dvpg"],
                    {"help": "uplink dvpg mor-id", "action": "store", "type": str},
                ),
                (
                    ["uplink_ipaddress"],
                    {"help": "uplink address", "action": "store", "type": str},
                ),
                (
                    ["uplink_prefix"],
                    {
                        "help": "uplink prefix",
                        "action": "store",
                        "type": int,
                        "default": 24,
                    },
                ),
                (
                    ["pwd"],
                    {"help": "admin user password", "action": "store", "type": str},
                ),
                (
                    ["dns1"],
                    {"help": "dns name server 1", "action": "store", "type": str},
                ),
                (["domain"], {"help": "dns zone", "action": "store", "type": str}),
            ]
        ),
    )
    def edge_add(self):
        name = self.app.pargs.name
        datacenter = self.app.pargs.datacenter
        cluster_id = self.app.pargs.cluster
        datastore = self.app.pargs.datastore
        uplink_dvpg = self.app.pargs.uplink_dvpg
        uplink_ipaddress = self.app.pargs.uplink_ipaddress
        uplink_prefix = self.app.pargs.uplink_prefix
        pwd = self.app.pargs.pwd
        dns1 = self.app.pargs.dns1
        domain = self.app.pargs.domain

        # get resource pool
        cluster = self.client.cluster.get(cluster_id)
        respools = self.client.cluster.resource_pool.list(cluster._moId)
        respool = respools[0].get("obj")._moId

        data = {
            "name": name,
            "datacenterMoid": datacenter,
            "tenant": "prova",
            "fqdn": name,
            "applianceSize": "compact",
            "appliances": [{"resourcePoolId": respool, "datastoreId": datastore}],
            "vnics": [
                {
                    "type": "Uplink",
                    "portgroupId": uplink_dvpg,
                    "addressGroups": [
                        {
                            "primaryAddress": uplink_ipaddress,
                            "subnetPrefixLength": uplink_prefix,
                        }
                    ],
                }
            ],
            "password": pwd,
            "primaryDns": dns1,
            "domainName": domain,
        }
        res = self.client.network.nsx.edge.add(data)
        # self.app.render({'msg': 'create edge %s' % (data['name'], res)})
        job = self.client.network.nsx.edge.get_job(res)
        edge = job["result"][0]["value"]
        self.__wait_from_edge_job(res, edge, "create")

    @ex(
        help="delete vsphere edge",
        description="delete vsphere edge",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_del(self):
        oid = self.app.pargs.id
        res = self.client.network.nsx.edge.delete(oid)
        job = self.client.network.nsx.edge.get_job(res)
        edge = job["result"]["value"]
        self.__wait_from_edge_job(res, edge, "delete")
        # self.app.render({'msg': 'delete edge %s' % oid}, details=True)

    @ex(
        help="set vsphere edge admin password",
        description="set vsphere edge admin password",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": "edge admin password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_set_pwd(self):
        oid = self.app.pargs.id
        pwd = self.app.pargs.pwd
        self.client.network.nsx.edge.reset_password(oid, pwd)
        self.app.render({"msg": "set edge %s admin password" % oid}, details=True)

    @ex(
        help="get edge appliances",
        description="get edge appliances",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-appliance"],
                    {
                        "help": "appliance id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_appliance_get(self):
        oid = self.app.pargs.id
        appliance = self.app.pargs.appliance
        if appliance is not None:
            edge = self.client.network.nsx.edge.get(oid)
            try:
                data = self.client.network.nsx.edge.appliances(edge)
                if isinstance(data, dict):
                    data = [data]
                res = data[int(appliance)]
                server = self.client.server.get(res["vmId"])
                sdata = {"server." + k: v for k, v in self.client.server.info(server).items()}

                self.app.render(res, details=True, maxsize=200)
                self.app.render(sdata, details=True, maxsize=200)
            except:
                raise Exception("Wrong appliance index")
        else:
            edge = self.client.network.nsx.edge.get(oid)
            res = self.client.network.nsx.edge.appliances(edge)
            self.app.render(
                res,
                headers=[
                    "vmId",
                    "vmHostname",
                    "vmName",
                    "hostName",
                    "deployed",
                    "haAdminState",
                ],
            )

    @ex(
        help="get edge vnics",
        description="get edge vnics",
        example="beehive platform vsphere edge-vnic-get -id edge-##### -e <env>;beehive platform vsphere edge-vnic-get -id edge-##### -vnic 0 -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vnic"],
                    {
                        "help": "vnic id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_vnic_get(self):
        oid = self.app.pargs.id
        vnic = self.app.pargs.vnic
        if oid is not None:
            if vnic is not None:
                edge = self.client.network.nsx.edge.get(oid)
                try:
                    res = self.client.network.nsx.edge.vnics(edge)[int(vnic)]
                    self.app.render(res, details=True, maxsize=200)
                except:
                    raise Exception("Wrong vnic index")
            else:
                edge = self.client.network.nsx.edge.get(oid)
                res = self.client.network.nsx.edge.vnics(edge)
                headers = [
                    "index",
                    "name",
                    "type",
                    "primaryAddress",
                    "isConnected",
                    "portgroupName",
                ]
                fields = [
                    "index",
                    "name",
                    "type",
                    "addressGroups.addressGroup.primaryAddress",
                    "isConnected",
                    "portgroupName",
                ]
                self.app.render(res, headers=headers, fields=fields)
        else:
            objs = self.client.network.nsx.edge.list()
            res = []
            for o in objs:
                edge = self.client.network.nsx.edge.get(o["objectId"])
                data = self.client.network.nsx.edge.info(o)
                vnics = self.client.network.nsx.edge.vnics(edge)
                data["vnic"] = vnics[0]
                res.append(data)

            def secondary_addresses(val):
                if isinstance(val, list):
                    val = "\n".join(val)
                return val

            transform = {"vnic.addressGroups.addressGroup.secondaryAddresses.ipAddress": secondary_addresses}
            self.app.render(
                res,
                headers=self._meta.edge_headers1,
                fields=self._meta.edge_fields1,
                transform=transform,
                maxsize=400,
            )

    @ex(
        help="add edge vnic",
        description="add edge vnic",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["index"],
                    {
                        "help": "vnic index",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "vnic type. Uplink or Internal",
                        "action": "store",
                        "type": str,
                        "default": "Internal",
                    },
                ),
                (
                    ["portgroup"],
                    {
                        "help": "vnic portgroup id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ip"],
                    {
                        "help": "vnic primary ip",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_vnic_add(self):
        oid = self.app.pargs.id
        index = self.app.pargs.index
        vnic_type = self.app.pargs.type
        portgroup = self.app.pargs.portgroup
        ip = self.app.pargs.ip
        data = {
            "index": index,
            "type": vnic_type,
            "portgroupId": portgroup,
            "addressGroups": [{"primaryAddress": ip}],
        }
        self.client.network.nsx.edge.vnic_add(oid, data)
        self.app.render({"msg": "add edge %s vnic %s" % (oid, index)})

    @ex(
        help="update edge vnic",
        description="update edge vnic",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["vnic"],
                    {
                        "help": "vnic index",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-secondary_ip_add"],
                    {
                        "help": "add sub-interface",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-secondary_ip_del"],
                    {
                        "help": "remove sub-interface",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_vnic_update(self):
        oid = self.app.pargs.id
        vnic = self.app.pargs.vnic
        secondary_ip_add = self.app.pargs.secondary_ip_add
        secondary_ip_del = self.app.pargs.secondary_ip_del
        if secondary_ip_add is not None and secondary_ip_del is not None:
            raise Exception("Choose one action between add and delete for secondary ip address")
        if secondary_ip_add is not None:
            data = {"secondary_ip": secondary_ip_add, "action": "add"}
        elif secondary_ip_del is not None:
            data = {"secondary_ip": secondary_ip_del, "action": "delete"}
        else:
            data = {}
        res = self.client.network.nsx.edge.vnic_update(oid, vnic, **data)
        self.app.render({"msg": "update edge %s vnic %s" % (oid, vnic)})

    @ex(
        help="delete edge vnic",
        description="delete edge vnic",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["vnic"],
                    {
                        "help": "vnic index",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_vnic_del(self):
        oid = self.app.pargs.id
        vnic = self.app.pargs.vnic
        self.client.network.nsx.edge.vnic_del(oid, vnic)
        self.app.render({"msg": "delete edge %s vnic %s" % (oid, vnic)})

    @ex(
        help="get edge firewall config",
        description="get edge firewall config",
        example="beehive platform vsphere edge-fw-config edge-##### -e <env>;beehive platform vsphere edge-fw-config edge-##### --notruncate -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_fw_config(self):
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.firewall(edge)
        rules = res.pop("rules")

        for r in rules:
            source = r.get("source", {})
            new_source = []
            for k, v in source.items():
                if isinstance(v, list):
                    for v1 in v:
                        new_source.append("%s:%s" % (k, v1))
                else:
                    new_source.append("%s:%s" % (k, v))
            r["source"] = "\n".join(new_source)

            dest = r.get("destination", {})
            new_dest = []
            for k, v in dest.items():
                if isinstance(v, list):
                    for v1 in v:
                        new_dest.append("%s:%s" % (k, v1))
                else:
                    new_dest.append("%s:%s" % (k, v))
            r["destination"] = "\n".join(new_dest)

            application = r.get("application", {})
            new_application = []
            for k, v in application.items():
                if isinstance(v, list):
                    for v1 in v:
                        new_application.append("%s:%s" % (k, v1))
                if isinstance(v, dict):
                    new_application.append("%s:" % k)
                    for k1, v1 in v.items():
                        new_application.append("  %s:%s" % (k1, v1))
                else:
                    new_application.append("%s:%s" % (k, v))
            r["application"] = "\n".join(new_application)

        self.app.render(res, details=True, maxsize=200)
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

    @ex(
        help="get edge firewall rule",
        description="get edge firewall rule",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["rule"],
                    {
                        "help": "rule id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_fw_rule_get(self):
        oid = self.app.pargs.id
        rule = self.app.pargs.rule
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.firewall_rule(edge, rule)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="add edge firewall rule",
        description="add edge firewall rule",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": "rule name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-action"],
                    {
                        "help": "rule action. Can be: accept, deny",
                        "action": "store",
                        "type": str,
                        "default": "accept",
                    },
                ),
                (
                    ["-direction"],
                    {
                        "help": "rule direction. Can be: in, out",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-logged"],
                    {
                        "help": "rule logged",
                        "action": "store",
                        "type": str,
                        "default": False,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "rule description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": "rule name",
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
                (
                    ["-source"],
                    {
                        "help": "rule source. list of comma separated item like: ip:<ipAddress>, "
                        "grp:<groupingObjectId>, vnic:<vnicGroupId>",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dest"],
                    {
                        "help": "rule destination. list of comma separated item like: ip:<ipAddress>, "
                        "grp:<groupingObjectId>, vnic:<vnicGroupId>",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-app"],
                    {
                        "help": "rule application. list of comma separated item like: app:<applicationId>, "
                        "ser:proto+port+source_port",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_fw_rule_add(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        action = self.app.pargs.action
        direction = self.app.pargs.direction
        logged = self.app.pargs.logged
        desc = self.app.pargs.desc
        enabled = self.app.pargs.enabled
        source = self.app.pargs.source
        dest = self.app.pargs.dest
        appl = self.app.pargs.app
        if desc is None:
            desc = name
        if source:
            source = source.split(",")
        if dest:
            dest = dest.split(",")
        if appl:
            appl = appl.split(",")

        self.client.network.nsx.edge.get(oid)
        self.client.network.nsx.edge.firewall_rule_add(
            oid,
            name,
            action,
            desc=desc,
            direction=direction,
            source=source,
            dest=dest,
            application=appl,
            logged=logged,
            enabled=enabled,
        )
        self.app.render({"msg": "create firewall rule %s" % name})

    @ex(
        help="update edge firewall rule",
        description="update edge firewall rule",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["edge"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["id"],
                    {
                        "help": "rule id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "rule name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "rule description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-act"],
                    {
                        "help": "rule action",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dir"],
                    {
                        "help": "rule direction",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-src_add"],
                    {
                        "help": "add rule source",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-src_del"],
                    {
                        "help": "remove rule source",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dst_add"],
                    {
                        "help": "add rule destination",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dst_del"],
                    {
                        "help": "remove rule destination",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-appl"],
                    {
                        "help": "rule application",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-logged"],
                    {
                        "help": "enable rule log",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": "enable rule",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_fw_rule_update(self):
        edge_id = self.app.pargs.edge
        rule_id = self.app.pargs.id
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        action = self.app.pargs.act
        direction = self.app.pargs.dir
        source_add = self.app.pargs.src_add
        source_del = self.app.pargs.src_del
        dest_add = self.app.pargs.dst_add
        dest_del = self.app.pargs.dst_del
        appl = self.app.pargs.appl
        logged = self.app.pargs.logged
        enabled = self.app.pargs.enabled

        if source_add:
            source_add = source_add.split(",")
        if source_del:
            source_del = source_del.split(",")
        if dest_add:
            dest_add = dest_add.split(",")
        if dest_del:
            dest_del = dest_del.split(",")
        if appl:
            appl = appl.split(",")

        self.client.network.nsx.edge.get(edge_id)
        self.client.network.nsx.edge.firewall_rule_update(
            edge_id,
            rule_id,
            name=name,
            action=action,
            desc=desc,
            direction=direction,
            enabled=enabled,
            source_add=source_add,
            source_del=source_del,
            dest_add=dest_add,
            dest_del=dest_del,
            appl=appl,
            logged=logged,
        )
        self.app.render({"msg": "update firewall rule %s" % rule_id})

    @ex(
        help="delete edge firewall rule",
        description="delete edge firewall rule",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["rule"],
                    {
                        "help": "rule id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_fw_rule_del(self):
        oid = self.app.pargs.id
        rule = self.app.pargs.rule
        self.client.network.nsx.edge.get(oid)
        self.client.network.nsx.edge.firewall_rule_delete(oid, rule)
        self.app.render({"msg": "delete firewall rule %s" % rule})

    @ex(
        help="get edge nat config",
        description="get edge nat config",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_nat_config(self):
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.nat(edge)
        headers = [
            "id",
            "desc",
            "type",
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
        self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="add edge nat rule",
        description="add edge nat rule",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["desc"],
                    {
                        "help": "rule description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["action"],
                    {
                        "help": "can be dnat, snat",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["original_address"],
                    {
                        "help": "original address",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["translated_address"],
                    {
                        "help": "translated address",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-logged"],
                    {
                        "help": "if True enable logging",
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": "if True enable nat",
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
                (
                    ["-original_port"],
                    {
                        "help": "original port",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-translated_port"],
                    {
                        "help": "translated port",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-protocol"],
                    {
                        "help": "protocol",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vnic"],
                    {"help": "vnic", "action": "store", "type": str, "default": 0},
                ),
            ]
        ),
    )
    def edge_nat_rule_add(self):
        oid = self.app.pargs.id
        desc = self.app.pargs.desc
        action = self.app.pargs.action
        original_address = self.app.pargs.original_address
        translated_address = self.app.pargs.translated_address
        logged = self.app.pargs.logged
        enabled = self.app.pargs.enabled
        protocol = self.app.pargs.protocol
        translated_port = self.app.pargs.translated_port
        original_port = self.app.pargs.original_port
        vnic = self.app.pargs.vnic

        self.client.network.nsx.edge.get(oid)
        self.client.network.nsx.edge.nat_rule_add(
            oid,
            desc,
            action,
            original_address,
            translated_address,
            logged=logged,
            enabled=enabled,
            protocol=protocol,
            vnic=vnic,
            translated_port=translated_port,
            original_port=original_port,
        )
        self.app.render({"msg": "create nat rule %s" % desc})

    @ex(
        help="delete edge nat rule",
        description="delete edge nat rule",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["rule"],
                    {
                        "help": "rule id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_nat_rule_del(self):
        oid = self.app.pargs.id
        rule = self.app.pargs.rule
        self.client.network.nsx.edge.get(oid)
        self.client.network.nsx.edge.nat_rule_delete(oid, rule)
        self.app.render({"msg": "delete nat rule %s" % rule})

    @ex(
        help="get edge routing info",
        description="get edge routing info",
        example="beehive platform vsphere edge-route-get -e <env>  edge-#####;beehive platform vsphere edge-route-get -e <env> -id edge-#####",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_route_get(self):
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.route(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="get edge static routes",
        description="get edge static routes",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_route_static_get(self):
        oid = self.app.pargs.id
        res = self.client.network.nsx.edge.route_static_get(oid)
        self.app.render(
            res,
            headers=[
                "type",
                "description",
                "vnic",
                "network",
                "nextHop",
                "gateway",
                "mtu",
            ],
        )

    @ex(
        help="add edge default route",
        description="add edge default route",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["gateway"],
                    {
                        "help": "edge gateway",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-mtu"],
                    {"help": "mtu", "action": "store", "type": str, "default": 1500},
                ),
                (
                    ["-vnic"],
                    {"help": "vnic", "action": "store", "type": str, "default": 0},
                ),
            ]
        ),
    )
    def edge_route_default_add(self):
        oid = self.app.pargs.id
        gateway = self.app.pargs.gateway
        mtu = self.app.pargs.mtu
        vnic = self.app.pargs.vnic
        self.client.network.nsx.edge.route_default_add(oid, gateway, mtu=mtu, vnic=vnic)
        self.app.render({"msg": "create default route"})

    @ex(
        help="add edge static route",
        description="add edge static route",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["desc"],
                    {
                        "help": "rule description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["network"],
                    {"help": "network", "action": "store", "type": str, "default": ""},
                ),
                (
                    ["next_hop"],
                    {
                        "help": "next_hop address",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-mtu"],
                    {"help": "mtu", "action": "store", "type": str, "default": 1500},
                ),
                (
                    ["-vnic"],
                    {
                        "help": "if True enable logging",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_route_static_add(self):
        oid = self.app.pargs.id
        desc = self.app.pargs.desc
        network = self.app.pargs.network
        next_hop = self.app.pargs.next_hop
        mtu = self.app.pargs.mtu
        vnic = self.app.pargs.vnic
        self.client.network.nsx.edge.route_static_add(oid, desc, network, next_hop, mtu=mtu, vnic=vnic)
        self.app.render({"msg": "create static route %s" % desc})

    @ex(
        help="delete edge static route",
        description="delete edge static route",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def edge_route_del_all(self):
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        self.client.network.nsx.edge.route_static_del_all(oid)
        self.app.render({"msg": "delete all edge %s routes" % oid})

    @ex(
        help="get edge syslog config",
        description="get edge syslog config",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_syslog_get(self):
        oid = self.app.pargs.id
        res = self.client.network.nsx.edge.syslog(oid)
        self.app.render(res, details=True)

    @ex(
        help="add edge syslog servers",
        description="add edge syslog servers",
        example="beehive platform vsphere edge-syslog-add edge-##### ###.###.###.###:514 -e <env>;beehive platform vsphere edge-syslog-add edge-##### ###.###.###.###:514 -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["servers"],
                    {
                        "help": "rsyslog server ip address comma separated",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def edge_syslog_add(self):
        oid = self.app.pargs.id
        servers = self.app.pargs.servers.split(",")
        self.client.network.nsx.edge.syslog_add(oid, servers)
        self.app.render({"msg": "add syslog servers %s to edge %s" % (servers, oid)})

    @ex(
        help="delete edge syslog servers",
        description="delete edge syslog servers",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def edge_syslog_del(self):
        oid = self.app.pargs.id
        self.client.network.nsx.edge.syslog_del(oid)
        self.app.render({"msg": "delete syslog servers from edge %s" % oid})

    @ex(
        help="get vsphere edge l2 vpn config",
        description="get vsphere edge l2 vpn config",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_l2vpn_get(self):
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.l2vpn(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="get edge ssl vpn config",
        description="get edge ssl vpn config",
        example="beehive platform vsphere edge-sslvpn-get edge-##### -e <env>;beehive platform vsphere edge-sslvpn-get <uuid>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_get(self):
        oid = self.app.pargs.id
        sslvpn_config = self.client.network.nsx.edge.sslvpn(oid)

        advanced_config = sslvpn_config.pop("advancedConfig", {})
        server_settings = sslvpn_config.pop("serverSettings", {})
        client_configuration = sslvpn_config.pop("clientConfiguration", {})
        layout_configuration = sslvpn_config.pop("layoutConfiguration", {})
        ip_address_pools = sslvpn_config.pop("ipAddressPools", {}).get("ipAddressPool", [])
        private_networks = sslvpn_config.pop("privateNetworks", {}).get("privateNetwork", [])
        users = sslvpn_config.pop("users", {}).get("user", [])
        client_install_packages = sslvpn_config.pop("clientInstallPackages", {}).get("clientInstallPackage", {})
        authentication_configuration = sslvpn_config.pop("authenticationConfiguration", {}).get(
            "passwordAuthentication", {}
        )

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
        self.c(
            "\nauthentication configuration - primaryAuthServers - localAuthServer",
            "underline",
        )
        self.app.render(
            authentication_configuration.pop("primaryAuthServers", {}).get("localAuthServer"),
            details=True,
        )
        self.c(
            "\nauthentication configuration - primaryAuthServers - LdapAuthServer",
            "underline",
        )
        self.app.render(
            authentication_configuration.pop("primaryAuthServers", {}).get("LdapAuthServer", {}),
            details=True,
        )
        self.c(
            "\nauthentication configuration - primaryAuthServers - RadiusAuthServer",
            "underline",
        )
        self.app.render(
            authentication_configuration.pop("primaryAuthServers", {}).get("RadiusAuthServer", {}),
            details=True,
        )
        self.c(
            "\nauthentication configuration - primaryAuthServers - RsaAuthServer",
            "underline",
        )
        self.app.render(
            authentication_configuration.pop("primaryAuthServers", {}).get("RsaAuthServer", {}),
            details=True,
        )
        self.c("\nauthentication configuration - secondaryAuthServer", "underline")
        secondary_auth_server = authentication_configuration.pop("secondaryAuthServer", None)
        if secondary_auth_server is not None:
            self.app.render(secondary_auth_server, details=True)
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

    @ex(
        help="get vsphere edge sslvpn sessions",
        description="get vsphere edge sslvpn sessions",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_session_get(self):
        oid = self.app.pargs.id
        res = self.client.network.nsx.edge.sslvpn_session_get(oid)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="delete vsphere edge sslvpn session",
        description="delete vsphere edge sslvpn session",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["session"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_session_delete(self):
        oid = self.app.pargs.id
        session = self.app.pargs.session
        res = self.client.network.nsx.edge.sslvpn_session_delete(oid, session)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="add edge ssl vpn server config",
        description="add edge ssl vpn server config",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ip"],
                    {
                        "help": "server ip address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["port"],
                    {
                        "help": "server port",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_server_add(self):
        oid = self.app.pargs.id
        ip = self.app.pargs.ip
        port = self.app.pargs.port
        self.client.network.nsx.edge.sslvpn_server_config_add(oid, ip, port)

    @ex(
        help="add edge ssl vpn private network",
        description="add edge ssl vpn private network",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["network"],
                    {
                        "help": "network cidr",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-optimize"],
                    {
                        "help": "send tunnel optimize",
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_private_network_add(self):
        oid = self.app.pargs.id
        network = self.app.pargs.network
        optimize = self.app.pargs.optimize
        self.client.network.nsx.edge.sslvpn_private_network_add(oid, network, optimize=str2bool(optimize))

    @ex(
        help="delete all the edge ssl vpn private network",
        description="delete all the  edge ssl vpn private network",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["network"],
                    {
                        "help": "network id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_private_network_del(self):
        oid = self.app.pargs.id
        network = self.app.pargs.network
        self.client.network.nsx.edge.sslvpn_private_network_delete(oid, network)

    @ex(
        help="delete all the edge ssl vpn private network",
        description="delete all the  edge ssl vpn private network",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def edge_sslvpn_private_network_del_all(self):
        oid = self.app.pargs.id
        self.client.network.nsx.edge.sslvpn_private_network_delete_all(oid)

    @ex(
        help="add edge ssl vpn ippool",
        description="add edge ssl vpn ippool",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ip_range"],
                    {
                        "help": "ip range. Default 172.30.0.10-172.30.0.99",
                        "action": "store",
                        "type": str,
                        "default": "172.30.0.10-172.30.0.99",
                    },
                ),
                (
                    ["-netmask"],
                    {
                        "help": "netmask. Default 255.255.255.0",
                        "action": "store",
                        "type": str,
                        "default": "255.255.255.0",
                    },
                ),
                (
                    ["-gateway"],
                    {
                        "help": "gateway. Default 172.30.0.1",
                        "action": "store",
                        "type": str,
                        "default": "172.30.0.1",
                    },
                ),
                (
                    ["-primary_dns"],
                    {
                        "help": "primary dns. Default 10.103.48.1",
                        "action": "store",
                        "type": str,
                        "default": "10.103.48.1",
                    },
                ),
                (
                    ["-secondary_dns"],
                    {
                        "help": "secondary dns. Default 10.103.48.2",
                        "action": "store",
                        "type": str,
                        "default": "10.103.48.2",
                    },
                ),
                (
                    ["-dns_suffix"],
                    {
                        "help": "dns suffix",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-wins_server"],
                    {
                        "help": "wins server",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_ip_pool_add(self):
        oid = self.app.pargs.id
        ip_range = self.app.pargs.ip_range
        netmask = self.app.pargs.netmask
        gateway = self.app.pargs.gateway
        primary_dns = self.app.pargs.primary_dns
        secondary_dns = self.app.pargs.secondary_dns
        dns_suffix = self.app.pargs.dns_suffix
        wins_server = self.app.pargs.wins_server
        self.client.network.nsx.edge.sslvpn_ip_pool_add(
            oid,
            ip_range,
            netmask,
            gateway,
            primary_dns,
            secondary_dns,
            dns_suffix=dns_suffix,
            wins_server=wins_server,
        )

    @ex(
        help="delete all the edge ssl vpn ippool",
        description="delete all the  edge ssl vpn ippool",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ippool"],
                    {
                        "help": "ippool id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_ip_pool_del(self):
        oid = self.app.pargs.id
        ippool = self.app.pargs.ippool
        self.client.network.nsx.edge.sslvpn_ip_pool_delete(oid, ippool)

    @ex(
        help="delete all the edge ssl vpn ippool",
        description="delete all the  edge ssl vpn ippool",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def edge_sslvpn_ip_pool_del_all(self):
        oid = self.app.pargs.id
        self.client.network.nsx.edge.sslvpn_ip_pool_delete_all(oid)

    @ex(
        help="add edge ssl vpn install pkg",
        description="add edge ssl vpn install pkg",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {"help": "install package name", "action": "store", "type": str},
                ),
                (
                    ["gateways"],
                    {
                        "help": "comma separated list of gateway. server:port",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_install_pkg_add(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        gateways = self.app.pargs.gateways.split(",")
        self.client.network.nsx.edge.sslvpn_install_pkg_add(oid, name, [g.split(":") for g in gateways])

    @ex(
        help="delete all the edge ssl vpn install pkg",
        description="delete all the  edge ssl vpn install pkg",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["install_pkg"],
                    {
                        "help": "install_pkg id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_install_pkg_del(self):
        oid = self.app.pargs.id
        install_pkg = self.app.pargs.install_pkg
        self.client.network.nsx.edge.sslvpn_install_pkg_delete(oid, install_pkg)

    @ex(
        help="delete all the edge ssl vpn install pkg",
        description="delete all the  edge ssl vpn install pkg",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def edge_sslvpn_install_pkg_del_all(self):
        oid = self.app.pargs.id
        self.client.network.nsx.edge.sslvpn_install_pkg_delete_all(oid)

    @ex(
        help="add edge ssl vpn user",
        description="add edge ssl vpn user",
        example="beehive platform vsphere edge-sslvpn-user-add edge-##### abc abc abc def abc.def@ghi.lmno -password_never_expires false -change_password_on_next_login true ;beehive platform vsphere edge-sslvpn-user-add edge-##### #### xxxxx abc def abc_def ",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (["user_id"], {"help": "user id", "action": "store", "type": str}),
                (
                    ["password"],
                    {"help": "user password", "action": "store", "type": str},
                ),
                (
                    ["first_name"],
                    {"help": "first name", "action": "store", "type": str},
                ),
                (["last_name"], {"help": "last name", "action": "store", "type": str}),
                (
                    ["desc"],
                    {
                        "help": "user description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": "",
                    },
                ),
                (
                    ["-disable"],
                    {
                        "help": "disable user account",
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
                (
                    ["-password_never_expires"],
                    {
                        "help": "password never expires",
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-change_password_on_next_login"],
                    {
                        "help": "change password on next login",
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_user_add(self):
        oid = self.app.pargs.id
        user_id = self.app.pargs.user_id
        password = self.app.pargs.password
        first_name = self.app.pargs.first_name
        last_name = self.app.pargs.last_name
        description = self.app.pargs.desc
        disable = str2bool(self.app.pargs.disable)
        password_expires = str2bool(self.app.pargs.password_never_expires)
        change_password_on_next_login = str2bool(self.app.pargs.change_password_on_next_login)
        self.client.network.nsx.edge.sslvpn_user_add(
            oid,
            user_id,
            password,
            first_name,
            last_name,
            description,
            disable=disable,
            password_expires=password_expires,
            change_password_on_next_login=change_password_on_next_login,
        )

    """
    # DANGEROUS
    # uncomment to use

    @ex(
        help="change edge ssl vpn user password",
        description="change edge ssl vpn user password",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (["user_id"], {"help": "user id", "action": "store", "type": str}),
                (
                    ["password"],
                    {"help": "user password", "action": "store", "type": str},
                ),
            ]
        )
    )
    def edge_sslvpn_user_change_password(self):
        oid = self.app.pargs.id
        user_id = self.app.pargs.user_id
        password = self.app.pargs.password

        self.client.network.nsx.edge.sslvpn_user_modify(edge=oid,user_id=user_id,password=password)
    """

    @ex(
        help="delete all the edge ssl vpn user",
        description="delete all the  edge ssl vpn user",
        example="beehive platform vsphere edge-sslvpn-user-del edge-##### 73346;beehive platform vsphere edge-sslvpn-user-del edge-##### user-412 -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["user"],
                    {
                        "help": "user id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_user_del(self):
        oid = self.app.pargs.id
        user = self.app.pargs.user
        self.client.network.nsx.edge.sslvpn_user_delete(oid, user)

    @ex(
        help="enable edge ssl vpn service",
        description="enable edge ssl vpn service",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_enable(self):
        oid = self.app.pargs.id
        self.client.network.nsx.edge.sslvpn_enable(oid)

    @ex(
        help="disable edge ssl vpn service",
        description="disable edge ssl vpn service",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_disable(self):
        oid = self.app.pargs.id
        self.client.network.nsx.edge.sslvpn_disable(oid)

    @ex(
        help="delete edge ssl vpn service",
        description="delete edge ssl vpn service",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_sslvpn_delete(self):
        oid = self.app.pargs.id
        self.client.network.nsx.edge.sslvpn_delete(oid)

    @ex(
        help="delete vsphere edge",
        description="delete vsphere edge",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_availability_config(self):
        """Get edge high availability config.

        fields:
          edge                  edge mor-id"""
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.high_availability(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="get edge dns config",
        description="get edge dns config",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_dns_config(self):
        """Get edge dns config.

        fields:
          edge                  edge mor-id"""
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.dns(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="get edge dhcp config",
        description="get edge dhcp config",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_dhcp_config(self):
        """Get edge dhcp config.

        fields:
          edge                  edge mor-id"""
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.dhcp(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="get edge ipsec config",
        description="get edge ipsec config",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_ipsec_config(self):
        """Get edge ipsec config.

        fields:
          edge                  edge mor-id"""
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.ipsec(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="get edge global load balancer config",
        description="get edge global load balancer config",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_gslb_config(self):
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.gslb(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help="enable edge load balancer",
        description="enable edge load balancer configuration",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_start(self):
        edge_id = self.app.pargs.edge
        res = self.client.network.nsx.edge.lb.config_update(edge_id, enabled=True)
        msg = {"msg": "Enable load balancer on edge %s" % edge_id}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="disable edge load balancer",
        description="disable edge load balancer configuration",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_stop(self):
        edge_id = self.app.pargs.edge
        res = self.client.network.nsx.edge.lb.config_update(edge_id, enabled=False)
        msg = {"msg": "Disable load balancer on edge %s" % edge_id}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="get edge load balancer config",
        description="get edge load balancer config",
        example="beehive platform vsphere edge-lb-config-get edge-##### -e <env>;beehive platform vsphere edge-lb-config-get edge-##### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_config_get(self):
        edge_id = self.app.pargs.edge
        res = self.client.network.nsx.edge.lb.config_get(edge_id)

        def manage_data(data):
            sections = [
                {
                    "title": "monitor",
                    "headers": [
                        "id",
                        "name",
                        "interval",
                        "timeout",
                        "maxRetries",
                        "type",
                        "method",
                        "url",
                    ],
                    "fields": [
                        "monitorId",
                        "name",
                        "interval",
                        "timeout",
                        "maxRetries",
                        "type",
                        "method",
                        "url",
                    ],
                },
                {
                    "title": "pool",
                    "headers": [
                        "id",
                        "name",
                        "desc",
                        "transparent",
                        "algorithm",
                        "monitor_id",
                    ],
                    "fields": [
                        "poolId",
                        "name",
                        "description",
                        "transparent",
                        "algorithm",
                        "monitorId",
                    ],
                },
                {
                    "title": "applicationProfile",
                    "headers": [
                        "id",
                        "name",
                        "insertXForwardedFor",
                        "serverSslEnabled",
                        "template",
                        "sslPassthrough",
                        "clientSsl.clientAuth",
                        "clientSsl.ciphers",
                        "clientSsl.serviceCertificate",
                    ],
                    "fields": [
                        "applicationProfileId",
                        "name",
                        "insertXForwardedFor",
                        "serverSslEnabled",
                        "template",
                        "sslPassthrough",
                        "clientSsl.clientAuth",
                        "clientSsl.ciphers",
                        "clientSsl.serviceCertificate",
                    ],
                },
                {
                    "title": "applicationRule",
                    "headers": ["id", "name", "script"],
                    "fields": ["applicationRuleId", "name", "script"],
                },
                {
                    "title": "virtualServer",
                    "headers": [
                        "id",
                        "name",
                        "desc",
                        "app_rules",
                        "enabled",
                        "app_profile",
                        "conn_rate_limit",
                        "conn_limit",
                        "service_insert",
                        "acceleration",
                        "ip_addr",
                        "proto",
                        "port",
                    ],
                    "fields": [
                        "virtualServerId",
                        "name",
                        "description",
                        "applicationRuleId",
                        "enabled",
                        "applicationProfileId",
                        "connectionRateLimit",
                        "connectionLimit",
                        "enableServiceInsertion",
                        "accelerationEnabled",
                        "ipAddress",
                        "protocol",
                        "port",
                    ],
                },
            ]
            pool_members = []
            for item in sections:
                item["value"] = data.pop(item.get("title"))

                if item.get("title") == "pool":
                    for pool in item["value"]:
                        members = []
                        for m in pool.pop("member"):
                            m["poolId"] = pool.get("poolId")
                            m["poolName"] = pool.get("name")
                            members.append(m)
                        pool_members.extend(members)

            sections.append(
                {
                    "title": "pool members",
                    "value": pool_members,
                    "headers": [
                        "pool-id",
                        "pool-name",
                        "id",
                        "name",
                        "weight",
                        "ip-addr",
                        "condition",
                        "port",
                        "monitor-port",
                        "min-conn",
                        "max_conn",
                    ],
                    "fields": [
                        "poolId",
                        "poolName",
                        "memberId",
                        "name",
                        "weight",
                        "ipAddress",
                        "condition",
                        "port",
                        "monitorPort",
                        "minConn",
                        "maxConn",
                    ],
                }
            )

            return data, sections

        self.app.render(res, details=True, maxsize=200, manage_data=manage_data)

    @ex(
        help="set general edge load balancer parameters",
        description="set general edge load balancer parameters",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (
                    ["-acceleration"],
                    {
                        "help": "force load balancer to use L4 engine which is faster and more efficient than "
                        "L7 engine",
                        "action": "store",
                        "type": str,
                        "choices": [True, False],
                    },
                ),
                (
                    ["-logging"],
                    {
                        "help": "enable/disable load balancer logging",
                        "action": "store",
                        "type": str,
                        "choices": [True, False],
                    },
                ),
                (
                    ["-log_level"],
                    {
                        "help": "logging level",
                        "action": "store",
                        "type": str,
                        "choices": [
                            "emergency",
                            "alert",
                            "critical",
                            "error",
                            "warning",
                            "notice",
                            "info",
                            "debug",
                        ],
                    },
                ),
            ]
        ),
    )
    def edge_lb_config_set(self):
        edge_id = self.app.pargs.edge
        acceleration = self.app.pargs.acceleration
        acceleration = str2bool(acceleration)
        logging = self.app.pargs.logging
        logging = str2bool(logging)
        log_level = self.app.pargs.log_level

        data = {}
        if acceleration is not None:
            data.update({"acceleration_enabled": acceleration})
        if logging is not None:
            data.update({"logging": str2bool(logging)})
        if log_level is not None:
            data.update({"log_level": log_level})

        res = self.client.network.nsx.edge.lb.config_update(edge_id, **data)
        msg = {"msg": "Update load balancer configuration on edge %s" % edge_id}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="get edge load balancer statistics",
        description="get edge load balancer statistics",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (
                    ["-pool"],
                    {
                        "help": "pool id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_lb_stats_get(self):
        edge_id = self.app.pargs.edge
        pool_id = self.app.pargs.pool

        res = self.client.network.nsx.edge.lb.statistics_get(edge_id)

        if pool_id is not None:
            if self.is_output_text():
                pools = res.pop("pool", [])
                pools = [p for p in pools if dict_get(p, "poolId") == pool_id]
                if len(pools) > 0:
                    pool = pools[0]
                    member = pool.pop("member", [])

                    self.app.render(pool, details=True)
                    self.c("\nmembers", "underline")
                    headers = [
                        "memberId",
                        "name",
                        "ipAddress",
                        "status",
                        "failureCause",
                        "lastStateChangeTime",
                        "bytesIn",
                        "bytesOut",
                        "curSessions",
                        "httpReqTotal",
                        "httpReqRate",
                        "httpReqRateMax",
                        "maxSessions",
                        "rate",
                        "rateLimit",
                        "rateMax",
                        "totalSessions",
                    ]
                    fields = [
                        "memberId",
                        "name",
                        "ipAddress",
                        "status",
                        "bytesIn",
                        "bytesOut",
                        "curSessions",
                        "httpReqTotal",
                        "httpReqRate",
                        "httpReqRateMax",
                        "maxSessions",
                        "rate",
                        "rateLimit",
                        "rateMax",
                        "totalSessions",
                    ]
                    self.app.render(member, headers=headers, fields=fields)
                    self.c("\nmembers failure", "underline")
                    headers = [
                        "memberId",
                        "name",
                        "failureCause",
                        "lastStateChangeTime",
                    ]
                    fields = ["memberId", "name", "failureCause", "lastStateChangeTime"]
                    self.app.render(member, headers=headers, fields=fields)
            else:
                self.app.render(res, details=True)
        else:
            if self.is_output_text():
                pools = res.pop("pool", [])
                virt_servers = res.pop("virtualServer", [])

                self.c("\nvirtualServers", "underline")
                headers = [
                    "virtualServerId",
                    "name",
                    "ipAddress",
                    "status",
                    "bytesIn",
                    "bytesOut",
                    "curSessions",
                    "httpReqTotal",
                    "httpReqRate",
                    "httpReqRateMax",
                    "maxSessions",
                    "rate",
                    "rateLimit",
                    "rateMax",
                    "totalSessions",
                ]
                fields = [
                    "virtualServerId",
                    "name",
                    "ipAddress",
                    "status",
                    "bytesIn",
                    "bytesOut",
                    "curSessions",
                    "httpReqTotal",
                    "httpReqRate",
                    "httpReqRateMax",
                    "maxSessions",
                    "rate",
                    "rateLimit",
                    "rateMax",
                    "totalSessions",
                ]
                self.app.render(virt_servers, headers=headers, fields=fields)

                self.c("\npools", "underline")
                headers = [
                    "poolId",
                    "name",
                    "status",
                    "bytesIn",
                    "bytesOut",
                    "curSessions",
                    "httpReqTotal",
                    "httpReqRate",
                    "httpReqRateMax",
                    "maxSessions",
                    "rate",
                    "rateLimit",
                    "rateMax",
                    "totalSessions",
                ]
                fields = [
                    "poolId",
                    "name",
                    "status",
                    "bytesIn",
                    "bytesOut",
                    "curSessions",
                    "httpReqTotal",
                    "httpReqRate",
                    "httpReqRateMax",
                    "maxSessions",
                    "rate",
                    "rateLimit",
                    "rateMax",
                    "totalSessions",
                ]
                self.app.render(pools, headers=headers, fields=fields)
            else:
                self.app.render(res, details=True)

    def __render_members(self, members):
        self.c("\nmembers", "underline")
        headers = [
            "id",
            "name",
            "ipAddress",
            "weight",
            "monitorPort",
            "port",
            "maxConn",
            "minConn",
            "condition",
        ]
        fields = [
            "memberId",
            "name",
            "ipAddress",
            "weight",
            "monitorPort",
            "port",
            "maxConn",
            "minConn",
            "condition",
        ]
        self.app.render(members, headers=headers, fields=fields)

    @ex(
        help="get edge load balancer pools",
        description="get edge load balancer pools",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (
                    ["-id"],
                    {
                        "help": "pool id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "pool name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_lb_pool_get(self):
        edge_id = self.app.pargs.edge
        pool_id = self.app.pargs.id
        pool_name = self.app.pargs.name

        if pool_id is not None:
            res = self.client.network.nsx.edge.lb.pool_get(edge_id, pool_id)
            if self.is_output_text():
                members = res.pop("member", [])
                self.app.render(res, details=True)
                self.__render_members(members)
            else:
                self.app.render(res, details=True)
        else:
            res = self.client.network.nsx.edge.lb.pool_list(edge_id)
            if pool_name is not None:
                pool = next((item for item in res if item.get("name") == pool_name), None)
                if pool is not None:
                    members = pool.pop("member", [])
                    self.app.render(pool, details=True)
                    self.__render_members(members)
                else:
                    msg = {"msg": "Pool %s not found" % pool_name}
                    self.app.render(msg, headers=["msg"])
            else:
                headers = [
                    "id",
                    "name",
                    "desc",
                    "transparent",
                    "algorithm",
                    "monitor_id",
                ]
                fields = [
                    "poolId",
                    "name",
                    "description",
                    "transparent",
                    "algorithm",
                    "monitorId",
                ]
                self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="add edge load balancer pool",
        description="add edge load balancer pool",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["name"], {"help": "pool name", "action": "store", "type": str}),
                (
                    ["algorithm"],
                    {
                        "metavar": "algorithm",
                        "help": "balancing algorithm {round-robin,ip-hash,leastconn,uri}",
                        "choices": ["round-robin", "ip-hash", "leastconn", "uri"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "pool description",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-transparent"],
                    {
                        "help": "whether client IP addresses are visible to the backend servers",
                        "action": "store",
                        "type": bool,
                        "default": False,
                        "choices": [True, False],
                    },
                ),
                (
                    ["-monitor"],
                    {"help": "health check monitor id", "action": "store", "type": str},
                ),
                (
                    ["-ip_ver"],
                    {
                        "help": "ip address version",
                        "action": "store",
                        "type": str,
                        "choices": ["ipv4", "ipv6"],
                    },
                ),
            ]
        ),
    )
    def edge_lb_pool_add(self):
        edge_id = self.app.pargs.edge
        name = self.app.pargs.name
        algorithm = self.app.pargs.algorithm
        params = {
            "description": self.app.pargs.desc,
            "transparent": self.app.pargs.transparent,
            "monitor_id": self.app.pargs.monitor,
            "ip_version": self.app.pargs.ip_ver,
        }

        res = self.client.network.nsx.edge.lb.pool_add(edge_id, name, algorithm, **params)
        msg = {"msg": "Add pool %s on edge %s" % (res.get("ext_id"), edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="add member to edge load balancer pool",
        description="add member to edge load balancer pool",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["id"], {"help": "pool id", "action": "store", "type": str}),
                (["name"], {"help": "member name", "action": "store", "type": str}),
                (
                    ["-ip_addr"],
                    {
                        "help": "member ip address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-grouping_obj_id"],
                    {
                        "help": "member grouping object id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": "member port",
                        "action": "store",
                        "type": int,
                        "default": 80,
                    },
                ),
                (
                    ["-monit_port"],
                    {
                        "help": "monitor port",
                        "action": "store",
                        "type": int,
                        "default": 80,
                    },
                ),
                (
                    ["-weight"],
                    {
                        "help": "member weight",
                        "action": "store",
                        "type": int,
                        "default": 1,
                    },
                ),
                (
                    ["-max_conn"],
                    {
                        "help": "maximum number of concurrent connections a member can handle. Default is 0 which "
                        "means unlimited",
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-min_conn"],
                    {
                        "help": "minimum number of concurrent connections a member can handle. Default is 0 which "
                        "means unlimited",
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-cond"],
                    {
                        "help": "Whether the member is enabled or disabled. Default is enabled",
                        "action": "store",
                        "type": str,
                        "default": "enabled",
                    },
                ),
            ]
        ),
    )
    def edge_lb_pool_member_add(self):
        edge_id = self.app.pargs.edge
        pool_id = self.app.pargs.id
        name = self.app.pargs.name
        params = {
            "name": name,
            "ip_addr": self.app.pargs.ip_addr,
            "grouping_obj_id": self.app.pargs.grouping_obj_id,
            "port": self.app.pargs.port,
            "monitor_port": self.app.pargs.monit_port,
            "weight": self.app.pargs.weight,
            "max_conn": self.app.pargs.max_conn,
            "min_conn": self.app.pargs.min_conn,
            "condition": self.app.pargs.cond,
        }

        self.client.network.nsx.edge.lb.pool_members_add(edge_id, pool_id, [params])
        msg = {"msg": "Add member %s in pool %s on edge %s" % (name, pool_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="remove member from edge load balancer pool",
        description="remove member from edge load balancer pool",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["pool"], {"help": "pool id", "action": "store", "type": str}),
                (
                    ["ids"],
                    {
                        "help": "comma separated list of member ids",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def edge_lb_pool_members_del(self):
        edge_id = self.app.pargs.edge
        pool_id = self.app.pargs.pool
        member_ids = self.app.pargs.ids
        member_ids = member_ids.split(",")

        res = self.client.network.nsx.edge.lb.pool_member_del(edge_id, pool_id, member_ids)
        msg = {"msg": "Remove members %s from pool %s on edge %s" % (member_ids, pool_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="update edge load balancer pool",
        description="update edge load balancer pool",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["id"], {"help": "pool id", "action": "store", "type": str}),
                (
                    ["-algorithm"],
                    {
                        "metavar": "algorithm",
                        "help": "balancing algorithm {round-robin,ip-hash,leastconn,uri}",
                        "choices": ["round-robin", "ip-hash", "leastconn", "uri"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-transparent"],
                    {
                        "help": "whether client IP addresses are visible to the backend servers",
                        "action": "store",
                        "type": bool,
                        "default": False,
                        "choices": [True, False],
                    },
                ),
            ]
        ),
    )
    def edge_lb_pool_update(self):
        edge_id = self.app.pargs.edge
        pool_id = self.app.pargs.id
        params = {
            "algorithm": self.app.pargs.algorithm,
            "transparent": self.app.pargs.transparent,
        }

        res = self.client.network.nsx.edge.lb.pool_update(edge_id, pool_id, **params)
        msg = {"msg": "Update pool %s on edge %s" % (pool_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="delete edge load balancer pool",
        description="delete edge load balancer pool",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["id"], {"help": "pool id", "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_pool_del(self):
        edge_id = self.app.pargs.edge
        pool_id = self.app.pargs.id

        self.client.network.nsx.edge.lb.pool_del(edge_id, pool_id)
        msg = {"msg": "Delete pool %s on edge %s" % (pool_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="get edge load balancer application profiles",
        description="get edge load balancer application profiles",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (
                    ["-id"],
                    {
                        "help": "application profile id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_lb_app_profile_get(self):
        edge_id = getattr(self.app.pargs, "edge", None)
        profile_id = getattr(self.app.pargs, "id", None)
        if profile_id is not None:
            res = self.client.network.nsx.edge.lb.app_profile_get(edge_id, profile_id)

            def manage_data(data):
                sections = [
                    {
                        "title": "clientSsl",
                        "headers": ["serviceCertificate", "ciphers", "clientAuth"],
                        "fields": ["serviceCertificate", "ciphers", "clientAuth"],
                    }
                ]
                for item in sections:
                    item["value"] = data.pop(item.get("title"), None)

                return data, sections

            self.app.render(res, details=True, maxsize=200, manage_data=manage_data)

        else:
            res = self.client.network.nsx.edge.lb.app_profile_list(edge_id)
            headers = [
                "id",
                "name",
                "insertXForwardedFor",
                "serverSslEnabled",
                "template",
                "sslPassthrough",
                "clientSsl.clientAuth",
                "clientSsl.ciphers",
                "clientSsl.serviceCertificate",
            ]
            fields = [
                "applicationProfileId",
                "name",
                "insertXForwardedFor",
                "serverSslEnabled",
                "template",
                "sslPassthrough",
                "clientSsl.clientAuth",
                "clientSsl.ciphers",
                "clientSsl.serviceCertificate",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="add edge load balancer application profile",
        description="add edge load balancer application profile",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["name"], {"help": "profile name", "action": "store", "type": str}),
                (
                    ["template"],
                    {
                        "metavar": "template",
                        "help": "network traffic template {TCP,UDP,HTTP,HTTPS}",
                        "choices": ["TCP", "UDP", "HTTP", "HTTPS"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-http_redirect_url"],
                    {
                        "help": "HTTP redirect URL",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-persistence"],
                    {
                        "help": "persistence method",
                        "choices": ["cookie", "ssl_sessionid", "sourceip", "msrdp"],
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-expire"],
                    {
                        "help": "persistence time in seconds [Default=300]",
                        "action": "store",
                        "type": str,
                        "default": 300,
                    },
                ),
                (
                    ["-cookie_name"],
                    {
                        "help": "cookie name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-cookie_mode"],
                    {
                        "help": "cookie mode [Default=insert]",
                        "choices": ["insert", "prefix", "app"],
                        "action": "store",
                        "type": str,
                        "default": "insert",
                    },
                ),
                (
                    ["-insert_x_forwarded_for"],
                    {
                        "help": "insert X-Forwarded-for HTTP header [Default=False]",
                        "action": "store",
                        "type": bool,
                        "choices": [True, False],
                        "default": False,
                    },
                ),
                (
                    ["-ssl_passthrough"],
                    {
                        "help": "enable SSL passthrough [Default=False]",
                        "action": "store",
                        "type": bool,
                        "choices": [True, False],
                        "default": False,
                    },
                ),
                (
                    ["-client_ssl_serv_cert"],
                    {
                        "help": "client service certificate id. Required when client ssl=True",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-client_ssl_ca_cert"],
                    {
                        "help": "client ca certificate id [Optional]",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-client_ssl_cipher"],
                    {
                        "help": "client cipher suite [Default=DEFAULT]",
                        "choices": [
                            "DEFAULT",
                            "ECDHE-RSA-AES128-GCM-SHA256",
                            "ECDHE-RSA-AES256-GCM-SHA384",
                            "ECDHE-RSA-AES256-SHA",
                            "ECDHE-ECDSA-AES256-SHA",
                            "ECDH-ECDSA-AES256-SHA",
                            "ECDH-RSA-AES256-SHA",
                            "AES256-SHA AES128-SHA",
                            "DES-CBC3-SHA",
                        ],
                        "action": "store",
                        "type": str,
                        "default": "DEFAULT",
                    },
                ),
                (
                    ["-client_auth"],
                    {
                        "help": "whether peer certificate should be verified [Default=Ignore]",
                        "choices": ["Required", "Ignore"],
                        "action": "store",
                        "type": str,
                        "default": "Ignore",
                    },
                ),
                (
                    ["-server_ssl_serv_cert"],
                    {
                        "help": "server service certificate id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-server_ssl_ca_cert"],
                    {
                        "help": "server ca certificate id. Mandatory if -server_auth is set to Required",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-server_ssl_cipher"],
                    {
                        "help": "server cipher suite [Default=DEFAULT]",
                        "choices": [
                            "DEFAULT",
                            "ECDHE-RSA-AES128-GCM-SHA256",
                            "ECDHE-RSA-AES256-GCM-SHA384",
                            "ECDHE-RSA-AES256-SHA",
                            "ECDHE-ECDSA-AES256-SHA",
                            "ECDH-ECDSA-AES256-SHA",
                            "ECDH-RSA-AES256-SHA",
                            "AES256-SHA AES128-SHA",
                            "DES-CBC3-SHA",
                        ],
                        "action": "store",
                        "type": str,
                        "default": "DEFAULT",
                    },
                ),
                (
                    ["-server_auth"],
                    {
                        "help": "whether peer certificate should be verified [Default=Ignore]",
                        "choices": ["Required", "Ignore"],
                        "action": "store",
                        "type": str,
                        "default": "Ignore",
                    },
                ),
                (
                    ["-server_ssl_enabled"],
                    {
                        "help": "enable pool side SSL [Default=False]",
                        "choices": [True, False],
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def edge_lb_app_profile_add(self):
        edge_id = self.app.pargs.edge
        name = self.app.pargs.name
        template = self.app.pargs.template
        params = {
            "http_redirect_url": self.app.pargs.http_redirect_url,
            "persistence": {
                "method": self.app.pargs.persistence,
                "expire": self.app.pargs.expire,
                "cookie_name": self.app.pargs.cookie_name,
                "cookie_mode": self.app.pargs.cookie_mode,
            },
            "insert_x_forwarded_for": self.app.pargs.insert_x_forwarded_for,
            "ssl_passthrough": self.app.pargs.ssl_passthrough,
            "client_ssl_service_certificate": self.app.pargs.client_ssl_serv_cert,
            "client_ssl_ca_certificate": self.app.pargs.client_ssl_ca_cert,
            "client_ssl_cipher": self.app.pargs.client_ssl_cipher,
            "client_auth": self.app.pargs.client_auth,
            "server_ssl_service_certificate": self.app.pargs.server_ssl_serv_cert,
            "server_ssl_ca_certificate": self.app.pargs.server_ssl_ca_cert,
            "server_ssl_cipher": self.app.pargs.server_ssl_cipher,
            "server_auth": self.app.pargs.server_auth,
            "server_ssl_enabled": self.app.pargs.server_ssl_enabled,
        }

        res = self.client.network.nsx.edge.lb.app_profile_add(edge_id, name, template, **params)
        msg = {"msg": "Add app profile %s on edge %s" % (res.get("ext_id"), edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="update edge load balancer application profile",
        description="update edge load balancer application profile",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["id"], {"help": "profile id", "action": "store", "type": str}),
                (
                    ["-http_redirect_url"],
                    {
                        "help": "HTTP redirect URL",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-persistence"],
                    {
                        "help": "persistence method",
                        "choices": ["cookie", "ssl_sessionid", "sourceip", "msrdp"],
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-expire"],
                    {
                        "help": "persistence time in seconds [Default=300]",
                        "action": "store",
                        "type": str,
                        "default": 300,
                    },
                ),
                (
                    ["-cookie_name"],
                    {
                        "help": "cookie name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-cookie_mode"],
                    {
                        "help": "cookie mode [Default=insert]",
                        "choices": ["insert", "prefix", "app"],
                        "action": "store",
                        "type": str,
                        "default": "insert",
                    },
                ),
                (
                    ["-insert_x_forwarded_for"],
                    {
                        "help": "insert X-Forwarded-for HTTP header [Default=False]",
                        "action": "store",
                        "type": bool,
                        "choices": [True, False],
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def edge_lb_app_profile_update(self):
        edge_id = self.app.pargs.edge
        profile_id = self.app.pargs.id
        params = {
            "persistence": {
                "method": self.app.pargs.persistence,
                "cookieName": self.app.pargs.cookie_name,
                "cookieMode": self.app.pargs.cookie_mode,
                "expire": self.app.pargs.expire,
            },
            "insertXForwardedFor": self.app.pargs.insert_x_forwarded_for,
            "http_redirect_url": self.app.pargs.http_redirect_url,
        }

        res = self.client.network.nsx.edge.lb.app_profile_update(edge_id, profile_id, **params)
        msg = {"msg": "Update app profile %s on edge %s" % (profile_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="delete edge load balancer application profile",
        description="delete edge load balancer application profile",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["id"], {"help": "profile id", "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_app_profile_del(self):
        edge_id = self.app.pargs.edge
        profile_id = self.app.pargs.id

        res = self.client.network.nsx.edge.lb.app_profile_del(edge_id, profile_id)
        msg = {"msg": "Delete profile %s on edge %s" % (profile_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="get edge load balancer application rules",
        description="get edge load balancer application rules",
        example="beehive platform vsphere edge-lb-rule-get -e <env> -id edge-#####",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (
                    ["-id"],
                    {
                        "help": "rule id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_lb_rule_get(self):
        """Get edge load balancer application rules."""
        edge_id = self.app.pargs.edge
        rule_id = self.app.pargs.id
        if rule_id is not None:
            res = self.client.network.nsx.edge.lb.app_rule_get(edge_id, rule_id)
            self.app.render(res, details=True, maxsize=400)
        else:
            res = self.client.network.nsx.edge.lb.app_rule_list(edge_id)
            headers = ["id", "name", "script"]
            fields = ["applicationRuleId", "name", "script"]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="add edge load balancer application rule",
        description="add edge load balancer application rule",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["name"], {"help": "rule name", "action": "store", "type": str}),
                (
                    ["script"],
                    {
                        "help": 'rule script. If it starts with "@", read content from a file. '
                        "E.g. acl is_site01 hdr_dom(host) -i test-lb.site01.nivolapiemonte.it | use_backend "
                        "test-pool-1 if is_site01",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def edge_lb_rule_add(self):
        edge_id = self.app.pargs.edge
        name = self.app.pargs.name
        script = self.app.pargs.script
        if script is not None and script.find("@") == 0:
            script = BaseController.load_file(script.lstrip("@"))
        res = self.client.network.nsx.edge.lb.app_rule_add(edge_id, name, script)
        msg = {"msg": "Add application rule %s to edge %s" % (name, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="update edge load balancer application rules",
        description="update edge load balancer application rules",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["id"], {"help": "rule id", "action": "store", "type": str}),
                (
                    ["-name"],
                    {
                        "help": "rule name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-script"],
                    {
                        "help": "rule script",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_lb_rule_update(self):
        edge_id = self.app.pargs.edge
        rule_id = self.app.pargs.id
        name = self.app.pargs.name
        script = self.app.pargs.script
        if script is not None and script.find("@") == 0:
            script = BaseController.load_file(script.lstrip("@"))
        res = self.client.network.nsx.edge.lb.app_rule_update(edge_id, rule_id, name=name, script=script)
        msg = {"msg": "Update application rule %s to edge %s" % (rule_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="delete edge load balancer application rules",
        description="delete edge load balancer application rules",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["id"], {"help": "rule id", "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_rule_del(self):
        edge_id = self.app.pargs.edge
        rule_id = self.app.pargs.id
        res = self.client.network.nsx.edge.lb.app_rule_del(edge_id, rule_id)
        msg = {"msg": "Delete application rule %s on edge %s" % (rule_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="get edge load balancer monitors",
        description="get edge load balancer monitors",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["-id"], {"help": "monitor id", "action": "store", "type": str}),
                (["-name"], {"help": "monitor name", "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_monitor_get(self):
        """Get edge load balancer monitors."""
        edge_id = getattr(self.app.pargs, "edge", None)
        monitor_id = getattr(self.app.pargs, "id", None)
        monitor_name = getattr(self.app.pargs, "name", None)
        if monitor_id is not None:
            res = self.client.network.nsx.edge.lb.monitor_get(edge_id, monitor_id)
            self.app.render(res, details=True, maxsize=400)
        else:
            res = self.client.network.nsx.edge.lb.monitor_list(edge_id)
            if monitor_name is not None:
                monitor = next((item for item in res if item.get("name") == monitor_name), None)
                if monitor is not None:
                    self.app.render(monitor, details=True, maxsize=400)
                else:
                    msg = {"msg": "Health monitor %s not found" % monitor_name}
                    self.app.render(msg, headers=["msg"])
            else:
                headers = [
                    "id",
                    "type",
                    "name",
                    "url",
                    "method",
                    "interval",
                    "timeout",
                    "max_retries",
                ]
                fields = [
                    "monitorId",
                    "type",
                    "name",
                    "url",
                    "method",
                    "interval",
                    "timeout",
                    "maxRetries",
                ]
                self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="add edge load balancer monitor",
        description="add edge load balancer monitor",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["name"], {"help": "monitor name", "action": "store", "type": str}),
                (
                    ["type"],
                    {
                        "metavar": "type",
                        "help": "monitor type {HTTP,HTTPS,TCP,ICMP,UDP}",
                        "choices": ["HTTP", "HTTPS", "TCP", "ICMP", "UDP"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-interval"],
                    {
                        "help": "interval in seconds in which a server is to be tested [Default=5]",
                        "action": "store",
                        "type": int,
                        "default": 5,
                    },
                ),
                (
                    ["-timeout"],
                    {
                        "help": "maximum time in seconds in which a response from the server must be received "
                        "[Default=15]",
                        "action": "store",
                        "type": int,
                        "default": 15,
                    },
                ),
                (
                    ["-max_retries"],
                    {
                        "help": "maximum number of times the server is tested before it is declared down "
                        "[Default=3]",
                        "action": "store",
                        "type": int,
                        "default": 3,
                    },
                ),
                (
                    ["-method"],
                    {
                        "help": "method to send the health check request to the server [Default=GET for HTTP/HTTPS "
                        "monitor type]",
                        "choices": ["GET", "POST", "OPTIONS"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-url"],
                    {
                        "help": 'URL to GET or POST [Default="/" for HTTP/HTTPS monitor type]',
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-expected"],
                    {
                        "help": 'expected string [Default="HTTP/1" for HTTP/HTTPS monitor type]',
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-send"],
                    {
                        "help": "string to be sent to the backend server after a connection is established. This "
                        "option is mandatory when monitor type is UDP.",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-receive"],
                    {
                        "help": "string to be received from the backend server for HTTP/HTTPS protocol. This "
                        "option is mandatory when monitor type is UDP.",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-extension"],
                    {
                        "help": "advanced monitor configuration.",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_lb_monitor_add(self):
        edge_id = self.app.pargs.edge
        name = self.app.pargs.name
        monitor_type = self.app.pargs.type

        method = self.app.pargs.method
        if method is None and monitor_type in ["HTTP", "HTTPS"]:
            method = "GET"

        url = self.app.pargs.url
        if url is None and monitor_type in ["HTTP", "HTTPS"]:
            url = "/"

        expected = self.app.pargs.expected
        if expected is None and monitor_type in ["HTTP", "HTTPS"]:
            expected = "HTTP/1"

        params = {
            "interval": self.app.pargs.interval,
            "timeout": self.app.pargs.timeout,
            "max_retries": self.app.pargs.max_retries,
            "method": method,
            "url": url,
            "expected": expected,
            "send": self.app.pargs.send,
            "receive": self.app.pargs.receive,
            "extension": self.app.pargs.extension,
        }

        res = self.client.network.nsx.edge.lb.monitor_add(edge_id, name, monitor_type, **params)
        msg = {"msg": "Add monitor %s on edge %s" % (res.get("ext_id"), edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="update edge load balancer service monitor",
        description="update edge load balancer service monitor",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["id"], {"help": "monitor id", "action": "store", "type": str}),
                (
                    ["-interval"],
                    {
                        "help": "interval in seconds in which a server is to be tested [Default=5]",
                        "action": "store",
                        "type": int,
                        "default": 5,
                    },
                ),
                (
                    ["-timeout"],
                    {
                        "help": "maximum time in seconds in which a response from the server must be received "
                        "[Default=15]",
                        "action": "store",
                        "type": int,
                        "default": 15,
                    },
                ),
                (
                    ["-max_retries"],
                    {
                        "help": "maximum number of times the server is tested before it is declared down "
                        "[Default=3]",
                        "action": "store",
                        "type": int,
                        "default": 3,
                    },
                ),
                (
                    ["-method"],
                    {
                        "help": "method to send the health check request to the server [Default=GET for HTTP/HTTPS "
                        "monitor type]",
                        "choices": ["GET", "POST", "OPTIONS"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-url"],
                    {
                        "help": 'URL to GET or POST [Default="/" for HTTP/HTTPS monitor type]',
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-expected"],
                    {
                        "help": 'expected string [Default="HTTP/1" for HTTP/HTTPS monitor type]',
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-send"],
                    {
                        "help": "string to be sent to the backend server after a connection is established. This "
                        "option is mandatory when monitor type is UDP.",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-receive"],
                    {
                        "help": "string to be received from the backend server for HTTP/HTTPS protocol. This "
                        "option is mandatory when monitor type is UDP.",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_lb_monitor_update(self):
        edge_id = self.app.pargs.edge
        monitor_id = self.app.pargs.id
        params = {
            "interval": self.app.pargs.interval,
            "timeout": self.app.pargs.timeout,
            "max_retries": self.app.pargs.max_retries,
            "method": self.app.pargs.method,
            "url": self.app.pargs.url,
            "expected": self.app.pargs.expected,
            "send": self.app.pargs.send,
            "receive": self.app.pargs.receive,
        }

        res = self.client.network.nsx.edge.lb.monitor_update(edge_id, monitor_id, **params)
        msg = {"msg": "Update monitor %s on edge %s" % (monitor_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="delete edge load balancer monitor",
        description="delete edge load balancer monitor",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["id"], {"help": "monitor id", "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_monitor_del(self):
        edge_id = self.app.pargs.edge
        monitor_id = self.app.pargs.id

        self.client.network.nsx.edge.lb.monitor_del(edge_id, monitor_id)
        msg = {"msg": "Delete monitor %s on edge %s" % (monitor_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="get edge load balancer virtual servers",
        description="get edge load balancer virtual servers",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (
                    ["-id"],
                    {
                        "help": "virtual server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_lb_virt_server_get(self):
        edge_id = self.app.pargs.edge
        virt_srv_id = self.app.pargs.id
        if virt_srv_id is not None:
            res = self.client.network.nsx.edge.lb.virt_server_get(edge_id, virt_srv_id)
            self.app.render(res, details=True)
        else:
            res = self.client.network.nsx.edge.lb.virt_server_list(edge_id)
            headers = [
                "id",
                "name",
                "description",
                "enable",
                "ip_address",
                "protocol",
                "port",
                "app_profile",
                "pool",
            ]
            fields = [
                "virtualServerId",
                "name",
                "description",
                "enabled",
                "ipAddress",
                "protocol",
                "port",
                "applicationProfileId",
                "defaultPoolId",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="add edge load balancer virtual server",
        description="add edge load balancer virtual server",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (
                    ["name"],
                    {"help": "virtual server name", "action": "store", "type": str},
                ),
                (
                    ["ip_address"],
                    {
                        "help": "ip address that the load balancer is listening on",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["protocol"],
                    {
                        "metavar": "protocol",
                        "help": "virtual server protocol {HTTP,HTTPS}",
                        "choices": ["HTTP", "HTTPS"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (["port"], {"help": "port number", "action": "store", "type": int}),
                (
                    ["app_profile"],
                    {"help": "application profile id", "action": "store", "type": str},
                ),
                (["pool"], {"help": "pool id", "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": "virtual server description",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-max_conn"],
                    {
                        "help": "maximum concurrent connections",
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-max_conn_rate"],
                    {
                        "help": "maximum incoming new connection requests per second",
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-acceleration_enabled"],
                    {
                        "help": "use faster L4 load balancer engine rather than L7 load balancer " "engine",
                        "choices": [True, False],
                        "action": "store",
                        "type": bool,
                    },
                ),
            ]
        ),
    )
    def edge_lb_virt_server_add(self):
        edge_id = self.app.pargs.edge
        name = self.app.pargs.name
        ip_address = self.app.pargs.ip_address
        protocol = self.app.pargs.protocol
        port = self.app.pargs.port
        app_profile = self.app.pargs.app_profile
        pool = self.app.pargs.pool
        params = {
            "description": self.app.pargs.desc,
            "max_conn": self.app.pargs.max_conn,
            "max_conn_rate": self.app.pargs.max_conn_rate,
            "acceleration_enabled": self.app.pargs.acceleration_enabled,
        }

        res = self.client.network.nsx.edge.lb.virt_server_add(
            edge_id, name, ip_address, protocol, port, app_profile, pool, **params
        )
        msg = {"msg": "Add virtual server %s on edge %s" % (res.get("ext_id"), edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="update edge load balancer virtual server",
        description="update edge load balancer virtual server",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["id"], {"help": "virtual server id", "action": "store", "type": str}),
                (
                    ["-enabled"],
                    {
                        "help": "whether the virtual server is enabled",
                        "choices": [True, False],
                        "action": "store",
                        "type": bool,
                    },
                ),
                (
                    ["-ip_address"],
                    {
                        "help": "ip address that the load balancer is listening on",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-protocol"],
                    {
                        "help": "virtual server protocol",
                        "choices": [True, False],
                        "action": "store",
                        "type": str,
                    },
                ),
                (["-port"], {"help": "port number", "action": "store", "type": int}),
                (
                    ["-app_profile"],
                    {"help": "application profile id", "action": "store", "type": str},
                ),
                (["-pool"], {"help": "pool id", "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_virt_server_update(self):
        edge_id = self.app.pargs.edge
        virt_srv_id = self.app.pargs.id
        params = {
            "enabled": self.app.pargs.enabled,
            "ip_address": self.app.pargs.ip_address,
            "protocol": self.app.pargs.protocol,
            "port": self.app.pargs.port,
            "app_profile": self.app.pargs.app_profile,
            "pool": self.app.pargs.pool,
        }

        res = self.client.network.nsx.edge.lb.virt_server_update(edge_id, virt_srv_id, **params)
        msg = {"msg": "Update virtual server %s on edge %s" % (virt_srv_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="delete edge load balancer virtual server",
        description="delete edge load balancer virtual server",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["id"], {"help": "virtual server id", "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_virt_server_del(self):
        edge_id = self.app.pargs.edge
        virt_srv_id = self.app.pargs.id

        self.client.network.nsx.edge.lb.virt_server_del(edge_id, virt_srv_id)
        msg = {"msg": "Delete virtual server %s on edge %s" % (virt_srv_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="enable edge load balancer virtual server",
        description="enable edge load balancer virtual server",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["id"], {"help": "virtual server id", "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_virt_server_enable(self):
        edge_id = self.app.pargs.edge
        virt_srv_id = self.app.pargs.id

        self.client.network.nsx.edge.lb.virt_server_enable(edge_id, virt_srv_id)
        msg = {"msg": "Enable virtual server %s on edge %s" % (virt_srv_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="disable edge load balancer virtual server",
        description="disable edge load balancer virtual server",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (["id"], {"help": "virtual server id", "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_virt_server_disable(self):
        edge_id = self.app.pargs.edge
        virt_srv_id = self.app.pargs.id

        self.client.network.nsx.edge.lb.virt_server_disable(edge_id, virt_srv_id)
        msg = {"msg": "Disable virtual server %s on edge %s" % (virt_srv_id, edge_id)}
        self.app.render(msg, headers=["msg"])

    @ex(
        help="Add account in description of nsx virtual server",
        description="add account in description of nsx virtual server",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": "edge id", "action": "store", "type": str}),
                (
                    ["-id"],
                    {
                        "help": "virtual server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def edge_lb_virt_server_add_account_desc(self):
        def get_account_desc_by_params(controller, params):
            nodes_uri = "%s/nodes" % controller.api.baseuri
            for item in params:
                nodes = controller.cmp_get(nodes_uri, data=item).get("nodes", [])
                if len(nodes) < 1:
                    continue
                for node in nodes:
                    node_uri = node["__meta__"]["uri"]
                    enr_node = controller.cmp_get(node_uri)
                    enr_nodes = enr_node.get("node", [])
                    enr_groups = enr_nodes.get("groups", [])
                    if len(enr_groups) < 1:
                        continue
                    enr_group = enr_groups[0]
                    account = enr_group["name"]
                    return account
            return None

        def add_edge_account(controller, edge_pool_vs, edge_id):
            pool_vs = edge_pool_vs[edge_id]
            pool_d = {p["poolId"]: p for p in net_nsx_lb.pool_list(edge_id)}
            for pool_id in pool_vs.keys():
                vs = pool_vs[pool_id]
                pool = pool_d[pool_id]
                params = [
                    {"ip_address": a["ipAddress"], "names": a["name"]}
                    for a in pool.get("member", [])
                    if a.get("condition") == "enabled"
                ]
                if len(params) < 1:
                    self.app.log.debug("Skip %s %s it has no enabled ip in pool %s" % (edge_id, vs_id, pool_id))
                account_desc = get_account_desc_by_params(controller, params)
                vs["account"] = account_desc

        def update_vs_descriptions(edge_pool_vs):
            for edge_id in edge_pool_vs:
                vss = edge_pool_vs[edge_id].values()
                for vs in vss:
                    vs_id = vs["virtualServerId"]
                    vs_description = vs.get("virtualServerDescription")
                    if vs_description is not None and '"account":' in vs_description:
                        self.app.log.debug("Skip %s %s it has description %s" % (edge_id, vs_id, vs_description))
                        continue
                    account = vs["account"]
                    if account is None:
                        continue
                    params = {
                        "description": {"account": account},
                    }
                    self.app.log.debug("Update %s %s with account %s" % (edge_id, vs_id, account))
                    pool = net_nsx_lb.virt_server_update(edge_id, vs_id, **params)

        from beehive3_cli.core.cmp_api_client import CmpApiClient

        edge_id = getattr(self.app.pargs, "edge", None)
        virt_srv_id = getattr(self.app.pargs, "id", None)
        net_nsx_edge = self.client.network.nsx.edge
        net_nsx_lb = net_nsx_edge.lb
        edge_ids = []
        if edge_id is not None:
            edge_ids = [edge_id]
        else:
            edge_ids = [a["objectId"] for a in net_nsx_edge.list()]
        edge_pool_vs = {}
        for edge_id in edge_ids:
            vss = []
            if virt_srv_id is not None:
                vs_n = net_nsx_lb.virt_server_get(edge_id, virt_srv_id)
                if vs_n is not None:
                    vss = [vs_n]
            else:
                vss = net_nsx_lb.virt_server_list(edge_id)

            if len(vss) < 1:
                continue
            edge_pool_vs[edge_id] = {}
            for vs in vss:
                vs_id = vs["virtualServerId"]
                vs_description = vs.get("description")
                if vs.get("enabled") != "true":
                    self.app.log.debug("Skip %s %s it is disabled" % (edge_id, vs_id))
                    continue
                edge_pool_vs[edge_id][vs["defaultPoolId"]] = {
                    "virtualServerId": vs_id,
                    "virtualServerDescription": vs_description,
                }
        cmp = {"baseuri": "/v1.0/gas", "subsystem": "ssh"}
        self.api = CmpApiClient(
            self.app,
            cmp.get("subsystem"),
            cmp.get("baseuri"),
            self.key,
        )
        for edge_id in edge_pool_vs:
            add_edge_account(self, edge_pool_vs, edge_id)
        update_vs_descriptions(edge_pool_vs)

    @ex(
        help="list vsphere dlr",
        description="list vsphere dlr",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "edge id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dlr_get(self):
        """List distributed logical routers"""
        objs = self.client.network.nsx.dlr.list()
        res = []
        for obj in objs:
            res.append(self.client.network.nsx.dlr.info(obj))
        self.app.render(res, headers=["objectId", "name", "value"])

        oid = self.app.pargs.edge
        network = self.client.network.nsx.dlr.get(oid)
        res = self.client.network.nsx.dlr.detail(network)
        self.app.render(res, details=True)

    @ex(
        help="Clone Vsphere server",
        description="Clone an Existing VSphere Virtual Machine",
        example="beehive platform vsphere server-clone-v1 vm-##### -e <env>;beehive platform vsphere server-clone-v1 -id vm-##### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "Existing server id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": "server clone name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["hostname"],
                    {
                        "help": "server hostname",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-domain"],
                    {
                        "help": "domain name of the site where to put the cloned vm",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-destenv"],
                    {
                        "help": "destination environment where migrate the cloned vm",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-folder"],
                    {
                        "help": "vsphere parent folder id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-datastore"],
                    {
                        "help": "datastore id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-cluster"],
                    {
                        "help": "cluster id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dvpg"],
                    {
                        "help": "dvportgroup",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-password"],
                    {
                        "help": "admin password for the new cloned vm",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ipaddr"],
                    {
                        "help": "ip address for the new cloned vm",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subnet"],
                    {
                        "help": "subnet mask for the new cloned vm",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-defaultgw"],
                    {
                        "help": "default gateway for the new cloned vm",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-httpproxy"],
                    {
                        "help": "http proxy ip_addr:port for the new cloned vm",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-httpsproxy"],
                    {
                        "help": "https proxy ip_addr:port for the new cloned vm",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dns1"],
                    {
                        "help": "primary dns server for the new cloned vm",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dns2"],
                    {
                        "help": "secondary dns server for the new cloned vm",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_clone(self):
        from pyVmomi import vim
        from beedrones.vsphere.client import VsphereManager

        pargs = self.app.pargs
        oid = pargs.id
        dest_server_name = pargs.name
        dest_cluster_id = pargs.cluster
        dest_folder_id = pargs.folder
        dest_datastore_id = pargs.datastore
        dest_dvportgroup_id = pargs.dvpg
        admin_password = pargs.password
        hostname = pargs.hostname
        ipaddr = pargs.ipaddr
        subnet = pargs.subnet
        defaultgw = pargs.defaultgw
        httpproxy = pargs.httpproxy
        httpsproxy = pargs.httpsproxy
        primary_dns = pargs.dns1
        secondary_dns = pargs.dns2
        domain = pargs.domain
        dest_env = pargs.destenv

        if dest_env is not None:
            config_dest = load_environment_config(self.app, env=dest_env)
            orchestrators_dest = config_dest.get("orchestrators", {}).get("vsphere", {})
            conf_dest = orchestrators_dest[dest_env]
            client_dest = VsphereManager(conf_dest.get("vcenter"), conf_dest.get("nsx"), key=self.key)
        else:
            client_dest = self.client

        server = self.client.server.get(oid)
        if server is None:
            raise Exception("Vsphere Server %s does not exist" % oid)

        network = None
        if dest_dvportgroup_id is not None:
            network = client_dest.network.get_network(dest_dvportgroup_id)
            if network is None:
                raise Exception("Vsphere dvportgroup %s does not exist" % dest_dvportgroup_id)

        dest_folder = None
        if dest_folder_id is not None:
            dest_folder = client_dest.folder.get(dest_folder_id)
            if dest_folder is None:
                raise Exception("Vsphere Folder %s does not exist" % dest_folder_id)

        dest_datastore = None
        if dest_datastore_id is not None:
            dest_datastore = client_dest.datastore.get(dest_datastore_id)
            if dest_datastore is None:
                raise Exception("Vsphere Datastore %s does not exist" % dest_datastore_id)

        dest_cluster = None
        if dest_cluster_id is not None:
            dest_cluster = client_dest.cluster.get(dest_cluster_id)
            if dest_cluster is None:
                raise Exception("Vsphere Cluster %s does not exist" % dest_cluster_id)

        self.app.log.debug(
            "Cloning Vsphere server %s into %s (cluster %s, datastore %s, folder %s, dvpg %s)"
            % (oid, dest_server_name, dest_cluster_id, dest_datastore_id, dest_folder_id, dest_dvportgroup_id)
        )

        clone_task = self.client.server.create_clone(
            server,
            dest_server_name,
            hostname,
            domain,
            client_dest,
            dest_folder,
            dest_datastore,
            dest_cluster,
            network,
            admin_password,
            ipaddr,
            subnet,
            defaultgw,
            [primary_dns, secondary_dns],
            httpproxy,
            httpsproxy,
        )
        clone_result = self.client.wait_task(clone_task)
        dest_vsphere_id = client_dest.vsphere_id
        if clone_result == vim.TaskInfo.State.success:
            cloned_vm_id = clone_task.info.result._moId
            self.app.render(
                {"msg": "Cloned vm %s into vm %s located on vcenter %s" % (oid, cloned_vm_id, dest_vsphere_id)}
            )
        else:
            self.app.render({"msg": "Fail to clone to clone vm %s" % oid})
            if (
                clone_task.info is not None
                and clone_task.info.error is not None
                and len(clone_task.info.error.faultMessage) > 0
            ):
                self.app.render(clone_task.info.error.faultMessage[0].message)
