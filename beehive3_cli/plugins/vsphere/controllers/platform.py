# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from sys import stdout
from datetime import datetime
from time import sleep
from typing import Literal, Union, Optional, Dict
from cement.ext.ext_argparse import ex
from beecell.types.type_string import truncate, str2bool
from beecell.types.type_list import merge_list
from beecell.types.type_date import format_date
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import BaseController, BASE_ARGS, StringAction
from beehive3_cli.core.util import load_environment_config, load_config, rotating_bar, stoprotation
from beehive3_cli.translate import _


def VSPHERE_ARGS(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": _("vsphere platform reference label"),
            },
        ),
        (
            ["-P", "--project"],
            {
                "action": "store",
                "dest": "project",
                "help": _("vsphere current project name"),
            },
        ),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class VspherePlatformController(BaseController):
    class Meta: # type: ignore
        label = "vsphere"
        stacked_on = "platform"
        stacked_type = "nested"
        description = _("vsphere platform")
        help = _("vsphere platform")

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
            "freeAddressCount",
        ]
        ippool_fields = [
            "objectId",
            "name",
            "dnsSuffix",
            "gateway",
            "ipRanges",
            "totalAddressCount",
            "usedAddressCount",
            "freeAddressCount",
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

        super().pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("vsphere", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No vsphere default platform is available for this environment. Select another environment"
                )

        if label not in orchestrators:
            raise Exception(f"Valid label are: {', '.join(orchestrators.keys())}")
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
        rot_bar = rotating_bar()

        def trace():
            # stdout.write(".")
            stdout.write(next(rot_bar))
            stdout.flush()

        state = self.client.wait_task(task, delta=1, trace=trace, raise_on_error=True)
        return state

    def __format_rule_source_dest(
        self, obj: Optional[Union[str, Dict]], source_or_dest: Literal["source", "destination"]
    ) -> Optional[str]:
        if not obj:
            return None
        if isinstance(obj, str):
            return obj
        if source_or_dest == "source":
            inner = obj.get("source")
        elif source_or_dest == "destination":
            inner = obj.get("destination")
        else:
            inner = None

        if not inner:
            # should not happen
            self.app.error(f"Unhandled case. inner {source_or_dest} is {inner}")
            return inner

        if not isinstance(inner, list):
            inner = [inner]

        res = []
        for rule in inner:
            # i_type = rule.get("type")
            i_name = rule.get("name")
            i_value = rule.get("value")
            if i_name:
                # res.append(f"{i_type}:{i_name} ({i_value})")
                res.append(f"{i_name} ({i_value})")
            else:
                # res.append(f"{i_type}:{i_value}")
                res.append(f"{i_value}")
        return "\n".join(res)

    def __format_rule_services(self, obj: Optional[Union[str, Dict]]) -> Optional[str]:
        if not obj:
            return None
        if isinstance(obj, str):
            return obj
        inner = obj.get("service")

        if not inner:
            # should not happen
            self.app.error("Unhandled case. inner is None")
            return inner

        if not isinstance(inner, list):
            inner = [inner]
        res = []
        for service in inner:
            # s_isValid = service.get("isValid")
            s_destination_port = service.get("destinationPort")
            s_protocol_name = service.get("protocolName")
            s_protocol = service.get("protocol")
            s_subprotocol = service.get("subProtocol")
            tmp = ""
            if s_protocol_name:
                tmp = f"{s_protocol_name}"
            else:
                tmp = f"{s_protocol}"
                if s_subprotocol != s_protocol:
                    tmp += f"-{s_subprotocol}"
            if s_destination_port:
                tmp += f" {s_destination_port}"
            res.append(tmp)
        return "\n".join(res)

    def _render_rules(self, rules):
        if self.is_output_text():
            self.c("\nrules - general", "underline")
            self.app.render(
                rules,
                headers=[
                    "id",
                    "name",
                    "sectionId",
                    "direction",
                    "logged",
                    "packetType",
                    "disabled",
                ],
                maxsize=200,
            )
            self.c("\nrules - detail", "underline")

            transform = {
                "sources": lambda x: self.__format_rule_source_dest(x, "source"),
                "destinations": lambda x: self.__format_rule_source_dest(x, "destination"),
                "services": self.__format_rule_services,
            }
            self.app.render(
                rules,
                headers=[
                    "id",
                    "sources",
                    "destinations",
                    "services",
                ],
                transform=transform,
                maxsize=200,
            )
        else:
            self.app.render({"rules": rules}, details=True)

    @ex(help=_("ping vsphere"), description=_("ping vsphere"), arguments=VSPHERE_ARGS())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(
        help=_("get vsphere version"),
        description=_("get vsphere version"),
        example="beehive platform vsphere version",
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
        help=_("get vsphere custom fields"),
        description=_("get vsphere custom fields configured on vcenter"),
        example="beehive platform vsphere custom fields",
        arguments=VSPHERE_ARGS(),
    )
    def get_custom_fields(self):
        custom_fields = self.client.get_custom_fields()
        self.app.render(data=custom_fields, headers=["key", "name", "managedObjectType"])

    @ex(
        help=_("get vsphere nsx manager info"),
        description=_("get vsphere nsx manager info"),
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
        help=_("reboot vsphere nsx manager"),
        description=_("reboot vsphere nsx manager"),
        arguments=VSPHERE_ARGS(),
    )
    def nsx_manager_reboot(self):
        res = self.client.system.nsx.reboot_appliance()
        self.app.render(res, details=True)

    @ex(
        help=_("get vsphere nsx manager events"),
        description=_("get vsphere nsx manager events"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-page"],
                    {
                        "help": _("list page [default=0]"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": _("list page size [default=20]"),
                        "action": "store",
                        "type": int,
                        "default": 20,
                    },
                ),
            ]
        ),
    )
    def nsx_manager_event_get(self):
        page = getattr(self.app.pargs, "page", None)
        page_size = getattr(self.app.pargs, "size", None)
        start_index = page * page_size
        res = self.client.system.nsx.get_system_events(start_index=start_index, page_size=page_size)
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
        help=_("get vsphere nsx manager controllers"),
        description=_("get vsphere nsx manager controllers"),
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
        help=_("get datacenters"),
        description=_("get datacenters"),
        example="beehive platform vsphere datacenter-get -e <env>",
        arguments=VSPHERE_ARGS(
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
        help=_("get datacenter sessions"),
        description=_("get datacenter sessions"),
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
        help=_("get clusters"),
        description=_("get clusters"),
        arguments=VSPHERE_ARGS(
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
        help=_("get hosts"),
        description=_("get hosts"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("host id"),
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
        help=_("get resource pools"),
        description=_("get resource pools"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("resource pool id"),
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
        help=_("delete resource pool"),
        description=_("delete resource pool"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("resource pool id"),
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
        self.client.cluster.resource_pool.remove(respool)
        self.app.render({"msg": f"delete resource pool {oid}"})

    @ex(
        help=_("get datastores"),
        description=_("get datastores"),
        arguments=VSPHERE_ARGS(
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
        help=_("get folders"),
        description=_("get folders"),
        example="beehive platform vsphere folder-get -id group-v261 -e <env>",
        arguments=VSPHERE_ARGS(
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
            res = self.client.folder.get(oid)
            # print(res)
            if res is None:
                print(f"Folder not found {oid}")
            else:
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
        help=_("add vsphere folder"),
        description=_("add vsphere folder"),
        arguments=VSPHERE_ARGS(
            [
                (["name"], {"help": _("folder name"), "action": "store", "type": str}),
                (
                    ["desc"],
                    {
                        "help": _("folder description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-datacenter"],
                    {
                        "help": _("parent datacenter morid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-folder"],
                    {
                        "help": _("parent folder morid"),
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
        self.app.render({"msg": f"add folder {name}: {msg}"})

    @ex(
        help=_("update vsphere folder"),
        description=_("update vsphere folder"),
        example="beehive platform vsphere folder-update group-xxxx -desc <description>.notifysan-preprod -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("folder id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("folder name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("folder description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-datacenter"],
                    {
                        "help": _("parent datacenter morid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-folder"],
                    {
                        "help": _("parent folder morid"),
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
        self.client.folder.update(folder, name, desc)
        self.app.render({"msg": f"update folder {oid}"})

    @ex(
        help=_("delete vsphere folder"),
        description=_("delete vsphere folder"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def folder_del(self):
        oid = self.app.pargs.id
        obj = self.client.folder.get(oid)
        task = self.client.folder.remove(obj)
        # print("task: %s" % task)
        state = self.wait_task(task)
        # print("state: %s" % state)
        if state == "error":
            self.app.render({"msg": f"Error deleting folder {oid} ...see log"})
        else:
            self.app.render({"msg": f"Delete folder {oid}"})

    @ex(
        help=_("get servers"),
        description=_("get servers"),
        example="beehive platform vsphere server-get -names xxxxx-1 -e <env>",
        arguments=VSPHERE_ARGS(
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
                        "help": _("server name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-names"],
                    {
                        "help": _("filter by name like"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-template"],
                    {
                        "help": _("true list only template"),
                        "action": "store_true",
                        "default": False,
                    },
                ),
                (
                    ["-ipaddress"],
                    {
                        "help": _("server ipaddress"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dnsname"],
                    {
                        "help": _("server dnsname"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-cluster"],
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
    def server_get(self):
        oid = getattr(self.app.pargs, "id", None)
        cluster = self.app.pargs.cluster
        client = self.client
        server = client.server
        folder = client.folder
        if oid is not None:
            res = server.get(oid)
            data = server.detail(res)

            if self.is_output_text():
                if res is None:
                    self.app.render(data, details=True)
                else:
                    self.app.pargs.notruncate = True
                    volumes = data.pop("volumes", [])
                    networks = data.pop("networks", [])
                    config_data = server.hardware.get_config_data(res)
                    file_layout = config_data.pop("file_layout", {})
                    config_data.pop("network", {})
                    config_data.pop("storage", {})
                    files = file_layout.pop("files", [])
                    video = config_data.pop("video", {})
                    other = config_data.pop("other", {})
                    controllers = other.pop("controllers", {})
                    input_devices = other.pop("input_devices", {})
                    pci = other.pop("pci", {})
                    sg = server.security_groups(res)

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
                objs = client.cluster.get_servers(cluster)
            else:
                name = self.app.pargs.name
                names = self.app.pargs.names
                template = self.app.pargs.template
                ipaddress = self.app.pargs.ipaddress
                dnsname = self.app.pargs.dnsname

                project = self.app.pargs.project
                if project:
                    # e.g. ComputeService-4567...
                    folders = folder.get_folders_by_name(project)
                    if len(folders) == 0:
                        raise Exception(f"No projects found matching: {project}")

                    objs = []
                    for f in folders:
                        servers = folder.get_servers(f["obj"]._moId)
                        if servers and len(servers) > 0:
                            objs.extend(servers)
                else:
                    # get folders
                    folders = folder.list()

                    # get servers
                    objs = server.list(
                        name=name,
                        names=names,
                        template=template,
                        ipaddress=ipaddress,
                        dnsname=dnsname,
                        findAllByIp=True,
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
                    info = server.info(o)
                    info["parent"] = folder_idx.get(info["parent"], info["parent"])
                    res.append(info)
            self.app.render(res, headers=self._meta.server_headers, maxsize=30)

    @ex(
        help=_("add vsphere server [todo:]"),
        description=_("add vsphere server"),
        arguments=VSPHERE_ARGS(
            [
                (["name"], {"help": _("server name"), "action": "store", "type": str}),
                (
                    ["startip"],
                    {
                        "help": _("start ip"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["stopip"],
                    {
                        "help": _("stop ip"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["gw"],
                    {
                        "help": _("gateway"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["dns1"],
                    {"help": _("dns1"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["dns2"],
                    {"help": _("dns2"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-prefix"],
                    {"help": _("prefix"), "action": "store", "type": int, "default": 24},
                ),
                (
                    ["-dnssuffix"],
                    {
                        "help": _("dns zone"),
                        "action": "store",
                        "type": str,
                        "default": "domain.local",
                    },
                ),
            ]
        ),
    )
    def server_add(self):
        raise Exception("Unsupported")

    @ex(
        help=_("delete vsphere server"),
        description=_("delete vsphere server"),
        arguments=VSPHERE_ARGS(
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
        server = self.client.server.get_by_morid(oid)
        try:
            self.client.server.stop(server)
            # self.wait_task(task)
        except:
            pass
        task = self.client.server.remove(server)
        state = self.wait_task(task)
        # print("state: %s" % state)
        if state == "error":
            self.app.render({"msg": f"Error deleting server {oid} ...see log"})
        else:
            self.app.render({"msg": f"Delete server {oid}"})

    @ex(
        help=_("get vsphere server console"),
        description=_("get vsphere server console"),
        arguments=VSPHERE_ARGS(
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
        server = self.client.server.get_by_morid(oid)
        res = self.client.server.remote_console(server)
        self.app.render(res, details=True)

    @ex(
        help=_("get vsphere server devices"),
        description=_("get vsphere server devices"),
        arguments=VSPHERE_ARGS(
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
    def server_device_get(self):
        oid = self.app.pargs.id
        server = self.client.server.get_by_morid(oid)
        res = self.client.server.hardware.get_devices(server)
        self.app.render(
            res,
            headers=["key", "unitNumber", "summary", "label", "device type", "backing"],
        )

    @ex(
        help=_("get vsphere server guest info"),
        description=_("get vsphere server guest info"),
        arguments=VSPHERE_ARGS(
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
    def server_guest_info(self):
        oid = self.app.pargs.id
        server = self.client.server.get_by_morid(oid)
        res = self.client.server.guest_info(server)
        self.app.render(res, details=True)

    @ex(
        help=_("run vsphere server command using guest tool"),
        description=_("run vsphere server command using guest tool"),
        arguments=VSPHERE_ARGS(
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
                    ["cmd"],
                    {
                        "help": _("command"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["user"],
                    {"help": _("user"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["pwd"],
                    {
                        "help": _("password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-params"],
                    {
                        "help": _("command params. Use + as space"),
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
        self.client.server.guest_utils.guest_execute_command(
            server,
            user,
            pwd,
            path_to_program=ps_path,
            program_arguments=params,
            program=params,
        )

    @ex(
        help=_("disable vsphere server firewall"),
        description=_("disable vsphere server firewall"),
        arguments=VSPHERE_ARGS(
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
                    ["pwd"],
                    {
                        "help": _("server admin password"),
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
        self.client.server.guest_disable_firewall(server, pwd)
        self.app.render({"msg": f"disable server {oid} firewall"})

    @ex(
        help=_("copy ssh key on server"),
        description=_("copy ssh key on server"),
        arguments=VSPHERE_ARGS(
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
                    ["user"],
                    {"help": _("user"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["pwd"],
                    {
                        "help": _("password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pubkey"],
                    {
                        "help": _("ssh public key to set. Specify file name where key is stored"),
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
        help=_("change vsphere server password"),
        description=_("change vsphere server password"),
        arguments=VSPHERE_ARGS(
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
                    ["user"],
                    {"help": _("user"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["pwd"],
                    {
                        "help": _("password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["newpwd"],
                    {
                        "help": _("new password"),
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
        help=_("setup vsphere server network"),
        description=_("setup vsphere server network"),
        arguments=VSPHERE_ARGS(
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
                    ["user"],
                    {"help": _("user"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["pwd"],
                    {
                        "help": _("password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ipaddr"],
                    {
                        "help": _("ip address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-prefix"],
                    {
                        "help": _("ip address"),
                        "action": "store",
                        "type": int,
                        "default": 24,
                    },
                ),
                (
                    ["-macaddr"],
                    {
                        "help": _("mac address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["gw"],
                    {
                        "help": _("network gateway"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["hostname"],
                    {
                        "help": _("hostname"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["dns"],
                    {
                        "help": _("comma separated list of dns"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["dns_search"],
                    {
                        "help": _("dns search"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_network_setup(self):
        #dns = " ".join(self.app.pargs.dns.split(","))
        oid = self.app.pargs.id
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        ipaddr = self.app.pargs.ipaddr
        prefix = self.app.pargs.prefix
        macaddr = self.app.pargs.macaddr
        gw = self.app.pargs.gw
        hostname = self.app.pargs.hostname
        dns_search = self.app.pargs.dns_search
        server = self.client.server.get_by_morid(oid)
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
        help=_("setup vsphere server network"),
        description=_("setup vsphere server network"),
        arguments=VSPHERE_ARGS(
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
                    ["user"],
                    {"help": _("user"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["pwd"],
                    {
                        "help": _("password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ipaddr"],
                    {
                        "help": _("ip address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_network_destroy_config(self):
        #user = self.app.pargs.user
        oid = self.app.pargs.id
        pwd = self.app.pargs.pwd
        ipaddr = self.app.pargs.ipaddr
        server = self.client.server.get_by_morid(oid)
        self.client.server.guest_destroy_network_config(server, pwd, ipaddr)
        self.app.render({"msg": "Destroying network config done"})

    @ex(
        help=_("get vsphere server security groups"),
        description=_("get vsphere security groups"),
        arguments=VSPHERE_ARGS(
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
    def server_sg_get(self):
        oid = self.app.pargs.id
        server = self.client.server.get_by_morid(oid)
        res = self.client.server.security_groups(server)
        self.app.render(res, headers=["objectId", "name"])

    @ex(
        help=_("add security to server"),
        description=_("add security to server"),
        arguments=VSPHERE_ARGS(
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
                    ["sgid"],
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
        sgid = self.app.pargs.sgid
        self.client.server.security_group_add(oid, sgid)
        self.app.render({"msg": f"add security group {sgid} to server {oid}"})

    @ex(
        help=_("remove security from server"),
        description=_("remove security from server"),
        arguments=VSPHERE_ARGS(
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
                    ["sgid"],
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
        sgid = self.app.pargs.sgid
        self.client.server.security_group_del(oid, sgid)
        self.app.render({"msg": f"remove security group {sgid} from server {oid}"})

    @ex(
        help=_("start vsphere server"),
        description=_("start vsphere server"),
        arguments=VSPHERE_ARGS(
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
    def server_start(self):
        oid = self.app.pargs.id
        server = self.client.server.get_by_morid(oid)
        task = self.client.server.start(server)
        self.wait_task(task)

    @ex(
        help=_("stop vsphere server"),
        description=_("stop vsphere server"),
        arguments=VSPHERE_ARGS(
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
    def server_stop(self):
        oid = self.app.pargs.id
        server = self.client.server.get_by_morid(oid)
        self.client.server.stop(server)
        # self.wait_task(task)

    @ex(
        help=_("get disk of vsphere server"),
        description=_("get disk of vsphere server"),
        arguments=VSPHERE_ARGS(
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
        help=_("add disk to vsphere server"),
        description=_("add disk to vsphere server"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["server_id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["size"],
                    {
                        "help": _("disk size"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["datastore_id"],
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
        help=_("delete disk from vsphere server"),
        description=_("delete disk from vsphere server"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["server_id"],
                    {
                        "help": _("server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["disk_object_id"],
                    {
                        "help": _("disk object id"),
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
        help=_("extend disk of vsphere server"),
        description=_("delete disk from vsphere server"),
        arguments=VSPHERE_ARGS(
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
                    ["disk_object_id"],
                    {
                        "help": _("disk object id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["size"],
                    {
                        "help": _("disk size in Gb"),
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
        help=_("get vsphere server snapshot"),
        description=_("get vsphere server snapshot"),
        arguments=VSPHERE_ARGS(
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
                    ["-snapshot"],
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
        help=_("create vsphere server snapshot"),
        description=_("create vsphere server snapshot"),
        arguments=VSPHERE_ARGS(
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
        server = self.client.server.get_by_morid(oid)
        task = self.client.server.snapshot.create(server, name)
        self.wait_task(task)

    @ex(
        help=_("delete vsphere server snapshot"),
        description=_("delete vsphere server snapshot"),
        arguments=VSPHERE_ARGS(
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
        server = self.client.server.get_by_morid(oid)
        task = self.client.server.snapshot.remove(server, snapshot)
        self.wait_task(task)

    @ex(
        help=_("revert vsphere server to snapshot"),
        description=_("revert vsphere server to snapshot"),
        arguments=VSPHERE_ARGS(
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
        server = self.client.server.get_by_morid(oid)
        task = self.client.server.snapshot.revert(server, snapshot)
        self.wait_task(task)

    #
    # vapp
    #
    @ex(
        help=_("get vapps"),
        description=_("get vapps"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("vapp id"),
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
        help=_("get dvss"),
        description=_("get dvss"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {"help": _("dvs id"), "action": "store", "type": str, "default": None},
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
        help=_("get dvpgs"),
        description=_("get dvpgs"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("dvpg id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-list_servers"],
                    {"help": _("list also servers if id provided"), "action": "store_true", "default": False},
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
                self.app.render(data, details=True)

                if self.app.pargs.list_servers:
                    res1 = self.client.network.get_network_servers(oid)
                    servers = []
                    for s in res1:
                        servers.append(self.client.server.info(s))
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
        help=_("find dvpgs"),
        description=_("find dvpgs"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-name"],
                    {
                        "help": _("name filter"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vlan_id"],
                    {
                        "help": _("will iterate on list to find dvpg with specified vlan id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-dvs_id"],
                    {
                        "help": _("filter by dvs id (dvpg 'parent')"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dvpg_find(self):
        query_name = self.app.pargs.name
        query_vlan = self.app.pargs.vlan_id
        query_dvs = self.app.pargs.dvs_id
        if not (query_vlan or query_name or query_dvs):
            raise Exception("Specify at least one filter")
        objs = self.client.network.list_networks()
        if not objs:
            return
        self.app.render({"msg": f"{len(objs)} total dvpgs"})
        res = []
        matches = 0
        for o in objs:
            if "vim.dvs.DistributedVirtualPortgroup" not in str(o):
                # consider only port groups, not networks
                continue

            o_name = o.get("name")
            # partial name match
            if query_name and query_name not in o_name:
                continue

            print(self.styler.clear_line() + f"[Found: {matches}] Querying {o_name}", end="", flush=True)

            o_dvs = o.get("obj").config.distributedVirtualSwitch._moId
            # exact match
            if query_dvs and query_dvs != o_dvs:
                continue

            vlan_id = o.get("obj").config.defaultPortConfig.vlan.vlanId
            # exact match
            if query_vlan:
                if not isinstance(vlan_id, int):
                    self.app.warning(f"{o_name} has vlad id {vlan_id}. Unexpected type. Ignoring...")
                    continue
                if vlan_id != query_vlan:
                    continue
            res.append({"id": o.get("obj")._moId, "name": o_name, "dvs_id": o_dvs, "vlan_id": vlan_id})
            matches = matches + 1

        print(self.styler.clear_line(), end="")
        self.app.print(f"Found {len(res)} dvpgs matching the search query")
        self.app.render(res, headers=["id", "name", "dvs_id", "vlan_id"])

    @ex(
        help=_("add vsphere dvpg"),
        description=_("add vsphere dvpg"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("dvpg name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["vlan"],
                    {
                        "help": _("dvpg vlan"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["dvs"],
                    {
                        "help": _("dvpg dvs"),
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
        self.app.render({"msg": f"create dvpg {name}"})

    @ex(
        help=_("delete vsphere dvpg"),
        description=_("delete vsphere dvpg"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("dvpg id"),
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
            self.app.render({"msg": f"delete dvpg {oid}"})

    @ex(
        help=_("get securitygroup rules"),
        description=_("get securitygroup rules"),
        example="beehive platform vsphere sg-rule-get securitygroup-##### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("securitygroup id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-section_name"],
                    {
                        "help": _(
                            "section name (partial of total). e.g. ComputeService-#######[-avz###-#-section]. "
                            "Warning: first match will be used"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def sg_rule_get(self):
        oid = getattr(self.app.pargs, "id", None)
        rules = self.client.network.nsx.dfw.filter_rules(
            security_groups=[oid], section_name=self.app.pargs.section_name
        )
        self._render_rules(rules)

    @ex(
        help=_("get securitygroups"),
        description=_("get securitygroups"),
        example="beehive platform vsphere sg-get -section_name -section_name ComputeService-###### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("securitygroup id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-section_name"],
                    {
                        "help": _(
                            "section name (partial of total). e.g. ComputeService-########[-avz###-#-section]. "
                            "Warning: first match will be used."
                        ),
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
        section_name = getattr(self.app.pargs, "section_name", None)
        if oid:
            # if oid given show security group general info
            res = self.client.network.nsx.sg.get(oid)
            #data = self.client.network.nsx.sg.detail(res)

            if self.is_output_text():
                members = res.pop("member", [])
                self.app.render(res, details=True)
                self.c("\nmembers", "underline")
                self.app.render(members, headers=["objectId", "name", "objectTypeName"])
            else:
                self.app.render(res, details=True)
        if oid or section_name:
            # if section name or oid, get rules
            if not oid:
                sgs = None
            else:
                # also filter by security group
                sgs = [oid]
            rules = self.client.network.nsx.dfw.filter_rules(security_groups=sgs, section_name=section_name)
            self._render_rules(rules)
        if not oid and not section_name:
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
        help=_("delete vsphere securitygroup"),
        description=_("delete vsphere securitygroup"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("securitygroup id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force delete"),
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
        self.app.render({"msg": f"Delete securitygroup {oid}"})

    @ex(
        help=_("delete vsphere securitygroup member"),
        description=_("delete vsphere securitygroup member"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("securitygroup id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["member"],
                    {
                        "help": _("member to remove"),
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
        self.app.render({"msg": f"Delete security-group {oid} member {member}"})

    @ex(
        help=_("add vsphere securitygroup member"),
        description=_("add vsphere securitygroup member"),
        example="beehive platform vsphere sg-member-add securitygroup-##### vm-##### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("securitygroup id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["member"],
                    {
                        "help": _("member to add"),
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
        self.app.render({"msg": f"Add security-group {oid} member {member}"})

    # dfw
    def __print_sections(self, data, stype):
        sections = data[stype]["section"]
        if not isinstance(sections, list):
            sections = [sections]
        for s in sections:
            s["timestamp"] = format_date(datetime.fromtimestamp(float(s["timestamp"]) / 1000))
            rules = s.get("rule", [])
            if not isinstance(rules, list):
                rules = [rules]
            s["rules"] = len(rules)
        self.app.render(
            sections,
            headers=["id", "type", "timestamp", "generationNumber", "name", "rules"],
        )

    def __convert_proto(self, service):
        proto = service.get("protocol")
        #subproto = service.get("subProtocol")
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
                        data.append(f"  {self.__convert_proto(o)}:{o.get('destinationPort')}")
            elif key == "appliedToList":
                if len(objs) > 0:
                    data.append("appliedTo:")
                    for o in objs:
                        data.append(f"  {o.get('type')}:{o.get('value')}")
            elif key == "sources":
                if len(objs) > 0:
                    data.append("sources:")
                    for o in objs:
                        data.append(f"  {o.get('type')}:{o.get('value')}")
            elif key == "destinations":
                if len(objs) > 0:
                    data.append("destinations:")
                    for o in objs:
                        data.append(f"  {o.get('type')}:{o.get('value')}")

            rule[key] = "\n".join(data)
        else:
            rule[key] = ""
        return rule

    def __print_rule_datail(self, title, data):
        if not isinstance(data, list):
            data = [data]
        self.app.render(data, headers=["type", "name", "value"])

    @ex(
        help=_("get distributed firewall status"),
        description=_("get distributed firewall status"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-section"],
                    {
                        "help": _("section id"),
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
        help=_("get distributed firewall sections"),
        description=_("get distributed firewall sections"),
        example="beehive platform vsphere dfw-section-get -id 1053 -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("section id"),
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
            if self.is_output_text():
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
                self.app.render(res, details=True)
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
        help=_("check distributed firewall sections"),
        description=_("check distributed firewall sections"),
        arguments=VSPHERE_ARGS(),
    )
    def dfw_section_check(self):
        res = self.client.network.nsx.dfw.get_config()
        sections = res["layer3Sections"]["section"]
        if not isinstance(sections, list):
            sections = [sections]
        for s in sections:
            if s.get("name") == "None":
                print(s.get("id"), s.get("name"))
                self.client.network.nsx.dfw.delete_section(s.get("id"))

    @ex(
        help="update distributed firewall section",
        description="update distributed firewall section",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["section"],
                    {
                        "help": _("section id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("updated section data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dfw_section_update(self):
        section_id = self.app.pargs.section
        data_file = self.app.pargs.file
        data = load_config(data_file)

        self.client.network.nsx.dfw.update_layer3_section(section_id, data)
        self.app.render({"msg": f"Section {section_id} updated"})

    @ex(
        help=_("get distributed firewall rules"),
        description=_("get distributed firewall rules"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["section"],
                    {
                        "help": _("section id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["rule"],
                    {
                        "help": _("rule id"),
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
        if self.is_output_text():
            sources = res.pop("sources", {}).pop("source", [])
            destinations = res.pop("destinations", {}).pop("destination", [])
            applied_to_list = res.pop("appliedToList", {}).pop("appliedTo", [])
            services = res.pop("services", {}).pop("service", [])

            self.app.render(res, details=True)
            self.c("\nsources", "underline")
            self.__print_rule_datail("sources", sources)
            self.c("\ndestinatios", "underline")
            self.__print_rule_datail("destinations", destinations)
            self.c("\nappliedTo", "underline")
            self.__print_rule_datail("appliedTo", applied_to_list)
            self.c("\nservices", "underline")
            if not isinstance(services, list):
                services = [services]
            self.app.render(
                services,
                headers=["protocol", "subProtocol", "destinationPort", "protocolName"],
            )
        else:
            self.app.render(res, details=True)

    @ex(
        help=_("add distributed firewall sections"),
        description=_("add distributed firewall sections"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("section name"),
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
        self.app.render({"msg": f"add section {name}"})

    @ex(
        help=_("delete distributed firewall sections"),
        description=_("delete distributed firewall sections"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["section"],
                    {
                        "help": _("section id"),
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
        self.client.network.nsx.dfw.delete_section(section)
        self.app.render({"msg": f"Delete section {section}"})

    @ex(
        help=_("add distributed firewall rule"),
        description=_("add distributed firewall rule"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["section"],
                    {
                        "help": _("section id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("rule name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-action"],
                    {
                        "help": _("rule action: allow or deny"),
                        "action": "store",
                        "type": str,
                        "default": "allow",
                    },
                ),
                (
                    ["-direction"],
                    {
                        "help": _("rule name"),
                        "action": "store",
                        "type": str,
                        "default": "in",
                    },
                ),
                (
                    ["-sources"],
                    {
                        "help": _("rule sources. Ex. SecurityGroup:securitygroup-#####,Ipv4Address:###.###.###.###/24"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dests"],
                    {
                        "help": _("rule sources. Ex. SecurityGroup:securitygroup-#####,Ipv4Address:###.###.###.###/24"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-services"],
                    {
                        "help": _("rule services"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-appliedto"],
                    {
                        "help": _("rule context. Ex. DISTRIBUTED_FIREWALL:DISTRIBUTED_FIREWALL"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-log"],
                    {
                        "help": _("rule logging: 'true' to enable, 'false' to disable"),
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
        logged = self.app.pargs.log

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

        if logged is not None and logged in ["true", "True", "false", "False"]:
            logged = logged.lower()
        else:
            logged = "false"

        self.client.network.nsx.dfw.get_layer3_section(sectionid=section)
        self.client.network.nsx.dfw.create_rule(
            section,
            name,
            action,
            direction=direction,
            logged=logged,
            sources=sources,
            destinations=dests,
            services=services,
            appliedto=appliedtos,
            precedence="default",
        )
        self.app.render({"msg": f"add rule {name}"})

    @ex(
        help=_("delete distributed firewall rules"),
        description=_("delete distributed firewall rules"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["section"],
                    {
                        "help": _("section id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["rules"],
                    {
                        "help": _("comma separated list of rules id"),
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
        _, res_etag = self.client.network.nsx.dfw.get_layer3_section_and_etag(sectionid=section)
        for rule in rules:
            self.client.network.nsx.dfw.delete_rule(section, rule, res_etag)
        self.app.render({"msg": f"Delete section {section} rules {rules}"})

    @ex(
        help="update distributed firewall rule",
        description="update distributed firewall rule",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["section"],
                    {
                        "help": _("section id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["rule"],
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
                        "help": _("rule name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                # (
                #     ["-action"],
                #     {
                #         "help": "rule action: allow or deny",
                #         "action": "store",
                #         "type": str,
                #         "default": "allow",
                #     },
                # ),
                (
                    ["-disable"],
                    {
                        "help": _("rule on/off: True to disable rule, False to enable"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-log"],
                    {
                        "help": _("rule logging: True to enable logging, False to disable"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                # (
                #     ["-sources"],
                #     {
                #         "help": "rule sources. Ex. SecurityGroup:securitygroup-22,Ipv4Address:10.1.1.0/24",
                #         "action": "store",
                #         "type": str,
                #         "default": None,
                #     },
                # ),
                # (
                #     ["-dests"],
                #     {
                #         "help": "rule sources. Ex. SecurityGroup:securitygroup-22,Ipv4Address:10.1.1.0/24",
                #         "action": "store",
                #         "type": str,
                #         "default": None,
                #     },
                # ),
                # (
                #     ["-services"],
                #     {
                #         "help": "rule services",
                #         "action": "store",
                #         "type": str,
                #         "default": None,
                #     },
                # ),
                (
                    ["-appliedto"],
                    {
                        "help": _("the firewall element which the rule is applied to.") + " " + _("E.g.:") + " " +
                            "DISTRIBUTED_FIREWALL:DISTRIBUTED_FIREWALL, SecurityGroup:<sg_ext_id>",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-direction"],
                    {
                        "help": _("rule direction. Can be: 'in' for ingress, 'out' for egress"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dfw_rule_update(self):

        def validate_bool(in_str):
            if in_str is not None:
                if in_str.lower() in ["true", "false"]:
                    return in_str.lower()
                raise Exception("Bad parameter value")
            return None

        def validate_direction(in_str):
            if in_str is not None:
                if in_str.lower() in ["in", "out"]:
                    return in_str.lower()
                raise Exception("Bad parameter value")
            return None

        section = self.app.pargs.section
        rule = self.app.pargs.rule
        name = self.app.pargs.name
        disable = self.app.pargs.disable
        logged = self.app.pargs.log
        appliedto = self.app.pargs.appliedto
        direction = self.app.pargs.direction

        # TODO: add management of sources, destinations, action, etc.

        disable = validate_bool(disable)
        logged = validate_bool(logged)
        direction = validate_direction(direction)

        self.client.network.nsx.dfw.get_layer3_section(sectionid=section)
        self.client.network.nsx.dfw.update_rule(
            section,
            rule,
            new_disable=disable,
            new_name=name,
            new_sources=None,
            new_destinations=None,
            new_action=None,
            new_logged=logged,
            # new_services=None,
            new_appliedto=appliedto,
            new_direction=direction
        )
        self.app.render({"msg": f"update rule {rule}"})

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
        help=_("add member to distributed firewall exclusion list"),
        description=_("add member to distributed firewall exclusion list"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["member"],
                    {
                        "help": _("member id"),
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
        self.client.network.nsx.dfw.add_item_to_exclusion_list(member)
        self.app.render({"msg": f"add member {member} to exclusion list"})

    @ex(
        help=_("delete member from distributed firewall exclusion list"),
        description=_("delete member from distributed firewall exclusion list"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["member"],
                    {
                        "help": _("member id"),
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
        self.client.network.nsx.dfw.remove_item_from_exclusion_list(member)
        self.app.render({"msg": f"delete member {member} from exclusion list"})

    @ex(
        help=_("get nsx transport zones"),
        description=_("get nsx transport zones"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("transport zone id"),
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
        help=_("get logical switch"),
        description=_("get logical switch"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("logical switch id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dvpg"],
                    {
                        "help": _("dvpg id"),
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
                    self.c(f"\nbacking - {context.pop('objectId')}", "underline")
                    self.app.render(backing, details=True)
            else:
                self.app.render(res, details=True)

        elif dvpg is not None:
            res = self.client.network.nsx.lg.get_by_dvpg(dvpg)
            if res is None:
                raise Exception(f"no valid logical switch found for dvpg {dvpg}")

            if self.is_output_text():
                backings = res.pop("vdsContextWithBacking", [])

                self.app.render(res, details=True)
                for backing in backings:
                    context = backing.get("switch")
                    self.c(f"\nbacking - {context.pop('objectId')}", "underline")
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
        help=_("delete logical switch"),
        description=_("delete logical switch"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("logical switch id"),
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
        self.app.render({"msg": f"delete logical switch {oid}"})

    @ex(
        help=_("get vsphere ippools"),
        description=_("get ippools"),
        example="beehive platform vsphere ippool-get -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("ippool id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-range"],
                    {
                        "help": _("ippool range, start/stop ip comma separated"),
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
            pool_range = self.app.pargs.range
            if pool_range is not None:
                pool_range = pool_range.split(",")
            objs = self.client.network.nsx.ippool.list(pool_range=pool_range)
            res = []
            transform = None
            for o in objs:
                res.append(self.client.network.nsx.ippool.info(o))
                transform = {
                    "ipRanges": lambda x: "\n".join(
                        [
                            f"{item['id']:12} {item['startAddress']:17} {item['endAddress']}"
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
        help=_("add vsphere ippool"),
        description=_("add vsphere ippool"),
        arguments=VSPHERE_ARGS(
            [
                (["name"], {"help": _("ippool name"), "action": "store", "type": str}),
                (
                    ["startip"],
                    {
                        "help": _("start ip"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["stopip"],
                    {
                        "help": _("stop ip"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["gw"],
                    {
                        "help": _("gateway"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["dns1"],
                    {"help": _("dns1"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["dns2"],
                    {"help": _("dns2"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-prefix"],
                    {"help": _("prefix"), "action": "store", "type": int, "default": 24},
                ),
                (
                    ["-dnssuffix"],
                    {
                        "help": _("dns zone"),
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
        self.app.render({"msg": f"add ippool {name}: {msg}"})

    @ex(
        help=_("update vsphere ippool"),
        description=_("update vsphere ippool"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("ippool id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("ippool name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-startip"],
                    {
                        "help": _("start ip"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-stopip"],
                    {
                        "help": _("stop ip"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-gw"],
                    {
                        "help": _("gateway"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dns1"],
                    {"help": _("dns1"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-dns2"],
                    {"help": _("dns2"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-prefix"],
                    {"help": _("prefix"), "action": "store", "type": int, "default": None},
                ),
                (
                    ["-dnssuffix"],
                    {
                        "help": _("dns zone"),
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
        self.app.render({"msg": f"update ippool {oid}: {msg}"})

    @ex(
        help=_("delete vsphere ippool"),
        description=_("delete vsphere ippool"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("ippool id"),
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
        #obj = self.client.network.nsx.ippool.exists(pool_id=oid)
        self.client.network.nsx.ippool.delete(oid)
        self.app.render({"msg": f"Delete ippool {oid}"})

    @ex(
        help=_("get all allocated ippool ips"),
        description=_("get all allocated ippool ips"),
        example="beehive platform vsphere ippool-ip-usage ipaddresspool-##### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("ippool id"),
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
        import ipaddress
        res.sort(key=lambda x: ipaddress.ip_address(x.get("ipAddress")))
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
        help=_("assign ippool ip"),
        description=_("assign ippool ip"),
        example="beehive platform vsphere ippool-ip-use ipaddresspool-##### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("ippool id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ip"],
                    {
                        "help": _("ippool ip to use"),
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
        help=_("release ippool ip"),
        description=_("release ippool ip"),
        example="beehive platform vsphere ippool-ip-release ipaddresspool-##### ###.###.###.###",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("ippool id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ip"],
                    {
                        "help": _("ippool ip to use"),
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
        help=_("get ipsets"),
        description=_("get ipsets"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("ipset id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-range"],
                    {
                        "help": _("ipset range. use format 'start_ip,end_ip'"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {"help": _("ipset partial or complete name"), "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def ipset_get(self):
        oid = getattr(self.app.pargs, "id", None)
        name = self.app.pargs.name
        if oid is not None:
            res = self.client.network.nsx.ipset.get(oid)
            data = self.client.network.nsx.ipset.detail(res)

            if self.is_output_text():
                self.app.render(data, details=True)
            else:
                self.app.render(res, details=True)
        else:
            from ipaddress import IPv4Address, AddressValueError

            def try_cast_to_ip(address_str: str, raise_exc=False):
                """
                string to Ipv4 address
                """
                res = None
                try:
                    res = IPv4Address(address_str)
                except AddressValueError as exception:
                    res = None
                    self.app.error(f"Invalid ip address {address_str}: {exception}")
                    if raise_exc:
                        raise AddressValueError(f"Invalid ip address {address_str}") from exception
                    self.app.error(f"Ignoring invalid ip address {address_str}...")
                return res

            def try_cast_to_ip_start_end(input_str: str, separator=",", raise_exc=False):
                """
                from a,b or a-b to (IPv4Address(a),IPv4Address(b))
                """
                first, *rest = input_str.split(separator)
                start_ip = try_cast_to_ip(first, raise_exc=raise_exc)
                end_ip = None
                if rest:
                    tmp_end = rest[0]
                    if len(rest) > 1:
                        self.app.warning(f"Too many values. Only one will be considered: {tmp_end}")
                    end_ip = try_cast_to_ip(tmp_end)
                    if end_ip and end_ip < start_ip:
                        self.app.error(f"End ip {end_ip} is before start ip {start_ip}!. Ignoring ip address...")
                        end_ip = None
                return start_ip, end_ip

            def check_range_overlap(
                start1: IPv4Address, start2: IPv4Address, end1: IPv4Address = None, end2: IPv4Address = None
            ):
                """
                True if ranges overlap even partially
                """
                if not end2:
                    end2 = start2
                if start1 > end2:
                    return False
                if end1 and end1 < start2:
                    return False
                return True

            ip_range: str = self.app.pargs.range
            if ip_range is not None:
                start_ip, end_ip = try_cast_to_ip_start_end(ip_range, raise_exc=True)

            objs = self.client.network.nsx.ipset.list()
            res = []
            for o in objs:
                info = self.client.network.nsx.ipset.info(o)

                # name filter
                if name and name not in info.get("name", ""):
                    continue

                # ip filter
                if ip_range:
                    # transform "info.value" to a List[Union(IPv4Address,Tuple[IPv4Address,IPv4Address])]
                    info = self.client.network.nsx.ipset.parse_dict(info)

                    network_ranges = info.get("value")
                    if not network_ranges:
                        # go to next ipset object
                        continue

                    is_in_any_network = False
                    for range_i in network_ranges:
                        if isinstance(range_i, IPv4Address):
                            start2 = range_i
                            end2 = None
                        else:
                            start2, end2 = range_i

                        # check if there's any overlap at all
                        if not check_range_overlap(start_ip, start2, end_ip, end2):
                            # go to next range
                            continue

                        # found
                        is_in_any_network = True
                        break

                    if not is_in_any_network:
                        # go to next ipset object
                        continue

                res.append(info)

            self.app.render(res, headers=self._meta.ipset_headers, maxsize=400)

    @ex(
        help=_("add vsphere ipset"),
        description=_("add vsphere ipset"),
        arguments=VSPHERE_ARGS(
            [
                (["name"], {"help": _("ipset name"), "action": "store", "type": str}),
                (
                    ["desc"],
                    {
                        "help": _("ipset description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["cidr"],
                    {
                        "help": _("list of ip. Ex. ###.###.###.###-###.###.###.### or cidr"),
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
        self.app.render({"msg": f"add ipset {name}"})

    @ex(
        help=_("update vsphere ipset"),
        description=_("update vsphere ipset"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("ipset id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (["-name"], {"help": _("ipset name"), "action": "store", "type": str}),
            ]
        ),
    )
    def ipset_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        self.client.network.nsx.ipset.update(oid, name=name)
        self.app.render({"msg": f"Update ipset {oid}"})

    @ex(
        help=_("delete vsphere ipset"),
        description=_("delete vsphere ipset"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("ipset id"),
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
        self.app.render({"msg": f"Delete ipset {oid}"})

    @ex(
        help=_("get vsphere edges"),
        description=_("get vsphere edges"),
        example="beehive platform vsphere edge-get -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("edge id"),
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
                    "secondaryAddresses",
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
                    "addressGroups.addressGroup.secondaryAddresses.ipAddress",
                    "enableProxyArp",
                    "enableSendRedirects",
                ]
                def secondary_addresses(val):
                    if isinstance(val, list):
                        val = "\n".join(val)
                    return val

                transform = {"vnic.addressGroups.addressGroup.secondaryAddresses.ipAddress": secondary_addresses}
                self.app.render(vnics, headers=headers, fields=fields, transform=transform)
            else:
                self.app.render(res, details=True)
        else:
            objs = self.client.network.nsx.edge.list()
            res = []
            for o in objs:
                res.append(self.client.network.nsx.edge.info(o))
            self.app.render(res, headers=self._meta.edge_headers, fields=self._meta.edge_fields)

    @ex(
        help=_("get vsphere edge job"),
        description=_("get vsphere edge job"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {"help": _("job id"), "action": "store", "type": str, "default": None},
                )
            ]
        ),
    )
    def edge_job_get(self):
        oid = getattr(self.app.pargs, "id", None)
        res = self.client.network.nsx.edge.get_job(oid)
        self.app.render(res, details=True)

    def __wait_from_edge_job(self, jobid, edge, operation):
        self.app.log.debug(f"wait for edge job: {jobid}")
        res = self.client.network.nsx.edge.get_job(jobid)
        status = res["status"]
        stdout.flush()
        elapsed = 0
        rot_bar = rotating_bar()
        while status not in ["COMPLETED", "FAILED", "ROLLBACK", "TIMEOUT"]:
            # stdout.write(".")
            stdout.write(next(rot_bar))
            stdout.flush()
            sleep(5)
            res = self.client.network.nsx.edge.get_job(jobid)
            status = res["status"]
            elapsed += 5
            if elapsed > 600:
                status = "TIMEOUT"
        stoprotation()
        print(f"{operation} edge {edge} {status}")

    @ex(
        help=_("add vsphere edge"),
        description=_("add vsphere edge"),
        arguments=VSPHERE_ARGS(
            [
                (["name"], {"help": _("edge name"), "action": "store", "type": str}),
                (
                    ["datacenter"],
                    {"help": _("datacenter mor-id"), "action": "store", "type": str},
                ),
                (
                    ["cluster"],
                    {"help": _("cluster mor-id"), "action": "store", "type": str},
                ),
                (
                    ["datastore"],
                    {"help": _("datastore mor-id"), "action": "store", "type": str},
                ),
                (
                    ["uplink_dvpg"],
                    {"help": _("uplink dvpg mor-id"), "action": "store", "type": str},
                ),
                (
                    ["uplink_ipaddress"],
                    {"help": _("uplink address"), "action": "store", "type": str},
                ),
                (
                    ["uplink_prefix"],
                    {
                        "help": _("uplink prefix"),
                        "action": "store",
                        "type": int,
                        "default": 24,
                    },
                ),
                (
                    ["pwd"],
                    {"help": _("admin user password"), "action": "store", "type": str},
                ),
                (
                    ["dns1"],
                    {"help": _("dns name server 1"), "action": "store", "type": str},
                ),
                (["domain"], {"help": _("dns zone"), "action": "store", "type": str}),
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
        help=_("delete vsphere edge"),
        description=_("delete vsphere edge"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def edge_del(self):
        oid = self.app.pargs.id
        res = self.client.network.nsx.edge.delete(oid)
        job = self.client.network.nsx.edge.get_job(res)
        edge = job["result"]["value"]
        self.__wait_from_edge_job(res, edge, "delete")
        # self.app.render({'msg': 'delete edge %s' % oid}, details=True)

    @ex(
        help=_("set vsphere edge admin password"),
        description=_("set vsphere edge admin password"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": _("edge admin password"),
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
        self.app.render({"msg": f"set edge {oid} admin password"}, details=True)

    @ex(
        help=_("get edge appliances"),
        description=_("get edge appliances"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-appliance"],
                    {
                        "help": _("appliance id"),
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
            except Exception as exc:
                raise Exception('Wrong appliance index') from exc
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
        help=_("get edge vnics"),
        description=_("get edge vnics"),
        example="beehive platform vsphere edge-vnic-get -id edge-##### -vnic 0 -e <env>",
        arguments=VSPHERE_ARGS(
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
                (
                    ["-vnic"],
                    {
                        "help": _("vnic id"),
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
                except Exception as exc:
                    raise Exception('Wrong vnic index') from exc
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
        help=_("add edge vnic"),
        description=_("add edge vnic"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["index"],
                    {
                        "help": _("vnic index"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("vnic type. Uplink or Internal"),
                        "action": "store",
                        "type": str,
                        "default": "Internal",
                    },
                ),
                (
                    ["portgroup"],
                    {
                        "help": _("vnic portgroup id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ip"],
                    {
                        "help": _("vnic primary ip"),
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
        self.app.render({"msg": f"add edge {oid} vnic {index}"})

    @ex(
        help=_("update edge vnic"),
        description=_("update edge vnic"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["vnic"],
                    {
                        "help": _("vnic index"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-secondary_ip_add"],
                    {
                        "help": _("add sub-interface"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-secondary_ip_del"],
                    {
                        "help": _("remove sub-interface"),
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
        self.client.network.nsx.edge.vnic_update(oid, vnic, **data)
        self.app.render({"msg": f"update edge {oid} vnic {vnic}"})

    @ex(
        help=_("delete edge vnic"),
        description=_("delete edge vnic"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["vnic"],
                    {
                        "help": _("vnic index"),
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
        self.app.render({"msg": f"delete edge {oid} vnic {vnic}"})

    @ex(
        help=_("get edge firewall config"),
        description=_("get edge firewall config"),
        example="beehive platform vsphere edge-fw-config edge-##### --notruncate -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
        help=_("get edge firewall rule"),
        description=_("get edge firewall rule"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["rule"],
                    {
                        "help": _("rule id"),
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
        help=_("add edge firewall rule"),
        description=_("add edge firewall rule"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("rule name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-action"],
                    {
                        "help": _("rule action. Can be: accept, deny"),
                        "action": "store",
                        "type": str,
                        "default": "accept",
                    },
                ),
                (
                    ["-direction"],
                    {
                        "help": _("rule direction. Can be: 'in' for ingress, 'out' for egress"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-logged"],
                    {
                        "help": _("rule logged"),
                        "action": "store",
                        "type": str,
                        "default": False,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("rule description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": _("rule name"),
                        "action": "store",
                        "type": str,
                        "default": True,
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
                    ["-app"],
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
        self.app.render({"msg": f"create firewall rule {name}"})

    @ex(
        help=_("update edge firewall rule"),
        description=_("update edge firewall rule"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["edge"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["id"],
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
                        "help": _("rule name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("rule description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-act"],
                    {
                        "help": _("rule action"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dir"],
                    {
                        "help": _("rule direction. Can be: 'in' for ingress, 'out' for egress"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-src_add"],
                    {
                        "help": _("add rule source"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-src_del"],
                    {
                        "help": _("remove rule source"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dst_add"],
                    {
                        "help": _("add rule destination"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dst_del"],
                    {
                        "help": _("remove rule destination"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-appl"],
                    {
                        "help": _("rule application"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-logged"],
                    {
                        "help": _("enable rule log"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": _("enable rule"),
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
        self.app.render({"msg": f"update firewall rule {rule_id}"})

    @ex(
        help=_("delete edge firewall rule"),
        description=_("delete edge firewall rule"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["rule"],
                    {
                        "help": _("rule id"),
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
        self.app.render({"msg": f"delete firewall rule {rule}"})

    @ex(
        help=_("get edge nat config"),
        description=_("get edge nat config"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
        help=_("add edge nat rule"),
        description=_("add edge nat rule"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["desc"],
                    {
                        "help": _("rule description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["action"],
                    {
                        "help": _("can be dnat, snat"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["original_address"],
                    {
                        "help": _("original address"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["translated_address"],
                    {
                        "help": _("translated address"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-logged"],
                    {
                        "help": _("if True enable logging"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": _("if True enable nat"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
                (
                    ["-original_port"],
                    {
                        "help": _("original port"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-translated_port"],
                    {
                        "help": _("translated port"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-protocol"],
                    {
                        "help": _("protocol"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vnic"],
                    {"help": _("vnic"), "action": "store", "type": str, "default": 0},
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
        self.app.render({"msg": f"create nat rule {desc}"})

    @ex(
        help=_("delete edge nat rule"),
        description=_("delete edge nat rule"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["rule"],
                    {
                        "help": _("rule id"),
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
        self.app.render({"msg": f"delete nat rule {rule}"})

    @ex(
        help=_("get edge routing info"),
        description=_("get edge routing info"),
        example="beehive platform vsphere edge-route-get -e <env>  edge-#####",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def edge_route_get(self):
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.route(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("get edge static routes"),
        description=_("get edge static routes"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
        help=_("add edge default route"),
        description=_("add edge default route"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["gateway"],
                    {
                        "help": _("edge gateway"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-mtu"],
                    {"help": _("mtu"), "action": "store", "type": str, "default": 1500},
                ),
                (
                    ["-vnic"],
                    {"help": _("vnic"), "action": "store", "type": str, "default": 0},
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
        help=_("add edge static route"),
        description=_("add edge static route"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["desc"],
                    {
                        "help": _("rule description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["network"],
                    {"help": _("network"), "action": "store", "type": str, "default": ""},
                ),
                (
                    ["next_hop"],
                    {
                        "help": _("next_hop address"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-mtu"],
                    {"help": _("mtu"), "action": "store", "type": str, "default": 1500},
                ),
                (
                    ["-vnic"],
                    {
                        "help": _("if True enable logging"),
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
        self.app.render({"msg": f"create static route {desc}"})

    @ex(
        help=_("delete edge static route"),
        description=_("delete edge static route"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
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
        #edge = self.client.network.nsx.edge.get(oid)
        self.client.network.nsx.edge.route_static_del_all(oid)
        self.app.render({"msg": f"delete all edge {oid} routes"})

    @ex(
        help=_("get edge syslog config"),
        description=_("get edge syslog config"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def edge_syslog_get(self):
        oid = self.app.pargs.id
        res = self.client.network.nsx.edge.syslog(oid)
        self.app.render(res, details=True)

    @ex(
        help=_("add edge syslog servers"),
        description=_("add edge syslog servers"),
        example="beehive platform vsphere edge-syslog-add edge-##### ###.###.###.###:514 -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["servers"],
                    {
                        "help": _("rsyslog server ip address comma separated"),
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
        self.app.render({"msg": f"add syslog servers {servers} to edge {oid}"})

    @ex(
        help=_("delete edge syslog servers"),
        description=_("delete edge syslog servers"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
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
        self.app.render({"msg": f"delete syslog servers from edge {oid}"})

    @ex(
        help=_("get vsphere edge l2 vpn config"),
        description=_("get vsphere edge l2 vpn config"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def edge_l2vpn_get(self):
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.l2vpn(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("get edge ssl vpn config"),
        description=_("get edge ssl vpn config"),
        example="beehive platform vsphere edge-sslvpn-get edge-##### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
        help=_("get vsphere edge sslvpn sessions"),
        description=_("get vsphere edge sslvpn sessions"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def edge_sslvpn_session_get(self):
        oid = self.app.pargs.id
        res = self.client.network.nsx.edge.sslvpn_session_get(oid)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("delete vsphere edge sslvpn session"),
        description=_("delete vsphere edge sslvpn session"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["session"],
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
    def edge_sslvpn_session_delete(self):
        oid = self.app.pargs.id
        session = self.app.pargs.session
        res = self.client.network.nsx.edge.sslvpn_session_delete(oid, session)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("add edge ssl vpn server config"),
        description=_("add edge ssl vpn server config"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ip"],
                    {
                        "help": _("server ip address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["port"],
                    {
                        "help": _("server port"),
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
        help=_("add edge ssl vpn private network"),
        description=_("add edge ssl vpn private network"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["network"],
                    {
                        "help": _("network cidr"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-optimize"],
                    {
                        "help": _("send tunnel optimize"),
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
        help=_("delete all the edge ssl vpn private network"),
        description=_("delete all the  edge ssl vpn private network"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["network"],
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
    def edge_sslvpn_private_network_del(self):
        oid = self.app.pargs.id
        network = self.app.pargs.network
        self.client.network.nsx.edge.sslvpn_private_network_delete(oid, network)

    @ex(
        help=_("delete all the edge ssl vpn private network"),
        description=_("delete all the  edge ssl vpn private network"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
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
        help=_("add edge ssl vpn ippool"),
        description=_("add edge ssl vpn ippool"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ip_range"],
                    {
                        "help": _("ip range. Default 172.30.0.10-172.30.0.99"),
                        "action": "store",
                        "type": str,
                        "default": "172.30.0.10-172.30.0.99",
                    },
                ),
                (
                    ["-netmask"],
                    {
                        "help": _("netmask. Default 255.255.255.0"),
                        "action": "store",
                        "type": str,
                        "default": "255.255.255.0",
                    },
                ),
                (
                    ["-gateway"],
                    {
                        "help": _("gateway. Default 172.30.0.1"),
                        "action": "store",
                        "type": str,
                        "default": "172.30.0.1",
                    },
                ),
                (
                    ["-primary_dns"],
                    {
                        "help": _("primary dns. Default 10.103.48.1"),
                        "action": "store",
                        "type": str,
                        "default": "10.103.48.1",
                    },
                ),
                (
                    ["-secondary_dns"],
                    {
                        "help": _("secondary dns. Default 10.103.48.2"),
                        "action": "store",
                        "type": str,
                        "default": "10.103.48.2",
                    },
                ),
                (
                    ["-dns_suffix"],
                    {
                        "help": _("dns suffix"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-wins_server"],
                    {
                        "help": _("wins server"),
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
        help=_("delete all the edge ssl vpn ippool"),
        description=_("delete all the  edge ssl vpn ippool"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ippool"],
                    {
                        "help": _("ippool id"),
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
        help=_("delete all the edge ssl vpn ippool"),
        description=_("delete all the  edge ssl vpn ippool"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
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
        help=_("add edge ssl vpn install pkg"),
        description=_("add edge ssl vpn install pkg"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {"help": _("install package name"), "action": "store", "type": str},
                ),
                (
                    ["gateways"],
                    {
                        "help": _("comma separated list of gateway. server:port"),
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
        help=_("delete all the edge ssl vpn install pkg"),
        description=_("delete all the  edge ssl vpn install pkg"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["install_pkg"],
                    {
                        "help": _("install_pkg id"),
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
        help=_("delete all the edge ssl vpn install pkg"),
        description=_("delete all the  edge ssl vpn install pkg"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
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
        help=_("add edge ssl vpn user"),
        description=_("add edge ssl vpn user"),
        example="beehive platform vsphere edge-sslvpn-user-add edge-##### #### xxxxx abc def abc_def ",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (["user_id"], {"help": _("user id"), "action": "store", "type": str}),
                (
                    ["password"],
                    {"help": _("user password"), "action": "store", "type": str},
                ),
                (
                    ["first_name"],
                    {"help": _("first name"), "action": "store", "type": str},
                ),
                (["last_name"], {"help": _("last name"), "action": "store", "type": str}),
                (
                    ["desc"],
                    {
                        "help": _("user description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": "",
                    },
                ),
                (
                    ["-disable"],
                    {
                        "help": _("disable user account"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
                (
                    ["-password_never_expires"],
                    {
                        "help": _("password never expires"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-change_password_on_next_login"],
                    {
                        "help": _("change password on next login"),
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
        help=_("change edge ssl vpn user password"),
        description=_("change edge ssl vpn user password"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (["user_id"], {"help": _("user id"), "action": "store", "type": str}),
                (
                    ["password"],
                    {"help": _("user password"), "action": "store", "type": str},
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
        help=_("delete all the edge ssl vpn user"),
        description=_("delete all the  edge ssl vpn user"),
        example="beehive platform vsphere edge-sslvpn-user-del edge-##### user-412 -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("edge id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["user"],
                    {
                        "help": _("user id"),
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
        help=_("enable edge ssl vpn service"),
        description=_("enable edge ssl vpn service"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def edge_sslvpn_enable(self):
        oid = self.app.pargs.id
        self.client.network.nsx.edge.sslvpn_enable(oid)

    @ex(
        help=_("disable edge ssl vpn service"),
        description=_("disable edge ssl vpn service"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def edge_sslvpn_disable(self):
        oid = self.app.pargs.id
        self.client.network.nsx.edge.sslvpn_disable(oid)

    @ex(
        help=_("delete edge ssl vpn service"),
        description=_("delete edge ssl vpn service"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def edge_sslvpn_delete(self):
        oid = self.app.pargs.id
        self.client.network.nsx.edge.sslvpn_delete(oid)

    @ex(
        help=_("delete vsphere edge"),
        description=_("delete vsphere edge"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def edge_availability_config(self):
        """Get edge high availability config.

        fields:
          edge                  edge mor-id"""
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.high_availability(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("get edge dns config"),
        description=_("get edge dns config"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def edge_dns_config(self):
        """Get edge dns config.

        fields:
          edge                  edge mor-id"""
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.dns(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("get edge dhcp config"),
        description=_("get edge dhcp config"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def edge_dhcp_config(self):
        """Get edge dhcp config.

        fields:
          edge                  edge mor-id"""
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.dhcp(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("get edge ipsec config"),
        description=_("get edge ipsec config"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def edge_ipsec_config(self):
        """Get edge ipsec config.

        fields:
          edge                  edge mor-id"""
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.ipsec(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("get edge global load balancer config"),
        description=_("get edge global load balancer config"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
    def edge_gslb_config(self):
        oid = self.app.pargs.id
        edge = self.client.network.nsx.edge.get(oid)
        res = self.client.network.nsx.edge.gslb(edge)
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("enable edge load balancer"),
        description=_("enable edge load balancer configuration"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_start(self):
        edge_id = self.app.pargs.edge
        self.client.network.nsx.edge.lb.config_update(edge_id, enabled=True)
        msg = {"msg": f"Enable load balancer on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("disable edge load balancer"),
        description=_("disable edge load balancer configuration"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_stop(self):
        edge_id = self.app.pargs.edge
        self.client.network.nsx.edge.lb.config_update(edge_id, enabled=False)
        msg = {"msg": f"Disable load balancer on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("get edge load balancer config"),
        description=_("get edge load balancer config"),
        example="beehive platform vsphere edge-lb-config-get edge-##### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
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
                        for m in pool.pop("member", []):
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
        help=_("set general edge load balancer parameters"),
        description=_("set general edge load balancer parameters"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (
                    ["-acceleration"],
                    {
                        "help": _(
                            "force load balancer to use L4 engine which is faster and more efficient than L7 engine"
                        ),
                        "action": "store",
                        "type": str,
                        "choices": [True, False],
                    },
                ),
                (
                    ["-logging"],
                    {
                        "help": _("enable/disable load balancer logging"),
                        "action": "store",
                        "type": str,
                        "choices": [True, False],
                    },
                ),
                (
                    ["-log_level"],
                    {
                        "help": _("logging level"),
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

        self.client.network.nsx.edge.lb.config_update(edge_id, **data)
        msg = {"msg": f"Update load balancer configuration on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("get edge load balancer statistics"),
        description=_("get edge load balancer statistics"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (
                    ["-pool"],
                    {
                        "help": _("pool id"),
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
        help=_("get edge load balancer pools"),
        description=_("get edge load balancer pools"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (
                    ["-id"],
                    {
                        "help": _("pool id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("pool name"),
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
                    msg = {"msg": f"Pool {pool_name} not found"}
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
        help=_("add edge load balancer pool"),
        description=_("add edge load balancer pool"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["name"], {"help": _("pool name"), "action": "store", "type": str}),
                (
                    ["algorithm"],
                    {
                        "metavar": "algorithm",
                        "help": _("balancing algorithm {round-robin,ip-hash,leastconn,uri}"),
                        "choices": ["round-robin", "ip-hash", "leastconn", "uri"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("pool description"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-transparent"],
                    {
                        "help": _("whether client IP addresses are visible to the backend servers"),
                        "action": "store",
                        "type": bool,
                        "default": False,
                        "choices": [True, False],
                    },
                ),
                (
                    ["-monitor"],
                    {"help": _("health check monitor id"), "action": "store", "type": str},
                ),
                (
                    ["-ip_ver"],
                    {
                        "help": _("ip address version"),
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
        msg = {"msg": f"Add pool {res.get('ext_id')} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("add member to edge load balancer pool"),
        description=_("add member to edge load balancer pool"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["id"], {"help": _("pool id"), "action": "store", "type": str}),
                (["name"], {"help": _("member name"), "action": "store", "type": str}),
                (
                    ["-ip_addr"],
                    {
                        "help": _("member ip address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-grouping_obj_id"],
                    {
                        "help": _("member grouping object id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": _("member port"),
                        "action": "store",
                        "type": int,
                        "default": 80,
                    },
                ),
                (
                    ["-monit_port"],
                    {
                        "help": _("monitor port"),
                        "action": "store",
                        "type": int,
                        "default": 80,
                    },
                ),
                (
                    ["-weight"],
                    {
                        "help": _("member weight"),
                        "action": "store",
                        "type": int,
                        "default": 1,
                    },
                ),
                (
                    ["-max_conn"],
                    {
                        "help": _(
                            "maximum number of concurrent connections a member can handle. Default is 0 which "
                            "means unlimited"
                        ),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-min_conn"],
                    {
                        "help": _(
                            "minimum number of concurrent connections a member can handle. Default is 0 which "
                            "means unlimited"
                        ),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-cond"],
                    {
                        "help": _("Whether the member is enabled or disabled. Default is enabled"),
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
        msg = {"msg": f"Add member {name} in pool {pool_id} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("remove member from edge load balancer pool"),
        description=_("remove member from edge load balancer pool"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["pool"], {"help": _("pool id"), "action": "store", "type": str}),
                (
                    ["ids"],
                    {
                        "help": _("comma separated list of member ids"),
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

        self.client.network.nsx.edge.lb.pool_members_del(edge_id, pool_id, member_ids)
        msg = {"msg": f"Remove members {member_ids} from pool {pool_id} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("update edge load balancer pool"),
        description=_("update edge load balancer pool"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["id"], {"help": _("pool id"), "action": "store", "type": str}),
                (
                    ["-algorithm"],
                    {
                        "metavar": "algorithm",
                        "help": _("balancing algorithm {round-robin,ip-hash,leastconn,uri}"),
                        "choices": ["round-robin", "ip-hash", "leastconn", "uri"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-transparent"],
                    {
                        "help": _("whether client IP addresses are visible to the backend servers"),
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

        self.client.network.nsx.edge.lb.pool_update(edge_id, pool_id, **params)
        msg = {"msg": f"Update pool {pool_id} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("delete edge load balancer pool"),
        description=_("delete edge load balancer pool"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["id"], {"help": _("pool id"), "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_pool_del(self):
        edge_id = self.app.pargs.edge
        pool_id = self.app.pargs.id

        self.client.network.nsx.edge.lb.pool_del(edge_id, pool_id)
        msg = {"msg": f"Delete pool {pool_id} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("get edge load balancer application profiles"),
        description=_("get edge load balancer application profiles"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (
                    ["-id"],
                    {
                        "help": _("application profile id"),
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
        help=_("add edge load balancer application profile"),
        description=_("add edge load balancer application profile"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["name"], {"help": _("profile name"), "action": "store", "type": str}),
                (
                    ["template"],
                    {
                        "metavar": "template",
                        "help": _("network traffic template {TCP,UDP,HTTP,HTTPS}"),
                        "choices": ["TCP", "UDP", "HTTP", "HTTPS"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-http_redirect_url"],
                    {
                        "help": _("HTTP redirect URL"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-persistence"],
                    {
                        "help": _("persistence method"),
                        "choices": ["cookie", "ssl_sessionid", "sourceip", "msrdp"],
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-expire"],
                    {
                        "help": _("persistence time in seconds [Default=300]"),
                        "action": "store",
                        "type": str,
                        "default": 300,
                    },
                ),
                (
                    ["-cookie_name"],
                    {
                        "help": _("cookie name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-cookie_mode"],
                    {
                        "help": _("cookie mode [Default=insert]"),
                        "choices": ["insert", "prefix", "app"],
                        "action": "store",
                        "type": str,
                        "default": "insert",
                    },
                ),
                (
                    ["-insert_x_forwarded_for"],
                    {
                        "help": _("insert X-Forwarded-for HTTP header [Default=False]"),
                        "action": "store",
                        "type": bool,
                        "choices": [True, False],
                        "default": False,
                    },
                ),
                (
                    ["-ssl_passthrough"],
                    {
                        "help": _("enable SSL passthrough [Default=False]"),
                        "action": "store",
                        "type": bool,
                        "choices": [True, False],
                        "default": False,
                    },
                ),
                (
                    ["-client_ssl_serv_cert"],
                    {
                        "help": _("client service certificate id. Required when client ssl=True"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-client_ssl_ca_cert"],
                    {
                        "help": _("client ca certificate id [Optional]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-client_ssl_cipher"],
                    {
                        "help": _("client cipher suite [Default=DEFAULT]"),
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
                        "help": _("whether peer certificate should be verified [Default=Ignore]"),
                        "choices": ["Required", "Ignore"],
                        "action": "store",
                        "type": str,
                        "default": "Ignore",
                    },
                ),
                (
                    ["-server_ssl_serv_cert"],
                    {
                        "help": _("server service certificate id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-server_ssl_ca_cert"],
                    {
                        "help": _("server ca certificate id. Mandatory if -server_auth is set to Required"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-server_ssl_cipher"],
                    {
                        "help": _("server cipher suite [Default=DEFAULT]"),
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
                        "help": _("whether peer certificate should be verified [Default=Ignore]"),
                        "choices": ["Required", "Ignore"],
                        "action": "store",
                        "type": str,
                        "default": "Ignore",
                    },
                ),
                (
                    ["-server_ssl_enabled"],
                    {
                        "help": _("enable pool side SSL [Default=False]"),
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
        msg = {"msg": f"Add app profile {res.get('ext_id')} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("update edge load balancer application profile"),
        description=_("update edge load balancer application profile"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["id"], {"help": _("profile id"), "action": "store", "type": str}),
                (
                    ["-http_redirect_url"],
                    {
                        "help": _("HTTP redirect URL"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-persistence"],
                    {
                        "help": _("persistence method"),
                        "choices": ["cookie", "ssl_sessionid", "sourceip", "msrdp"],
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-expire"],
                    {
                        "help": _("persistence time in seconds [Default=300]"),
                        "action": "store",
                        "type": str,
                        "default": 300,
                    },
                ),
                (
                    ["-cookie_name"],
                    {
                        "help": _("cookie name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-cookie_mode"],
                    {
                        "help": _("cookie mode [Default=insert]"),
                        "choices": ["insert", "prefix", "app"],
                        "action": "store",
                        "type": str,
                        "default": "insert",
                    },
                ),
                (
                    ["-insert_x_forwarded_for"],
                    {
                        "help": _("insert X-Forwarded-for HTTP header [Default=False]"),
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

        self.client.network.nsx.edge.lb.app_profile_update(edge_id, profile_id, **params)
        msg = {"msg": f"Update app profile {profile_id} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("delete edge load balancer application profile"),
        description=_("delete edge load balancer application profile"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["id"], {"help": _("profile id"), "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_app_profile_del(self):
        edge_id = self.app.pargs.edge
        profile_id = self.app.pargs.id

        self.client.network.nsx.edge.lb.app_profile_del(edge_id, profile_id)
        msg = {"msg": f"Delete profile {profile_id} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("get edge load balancer application rules"),
        description=_("get edge load balancer application rules"),
        example="beehive platform vsphere edge-lb-rule-get -e <env> -id edge-#####",
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (
                    ["-id"],
                    {
                        "help": _("rule id"),
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
        help=_("add edge load balancer application rule"),
        description=_("add edge load balancer application rule"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["name"], {"help": _("rule name"), "action": "store", "type": str}),
                (
                    ["script"],
                    {
                        "help": _(
                            "rule script. If it starts with '@', read content from a file. "
                            "E.g.: acl is_site01 hdr_dom(host) -i test-lb.site01.nivolapiemonte.it | use_backend "
                            "test-pool-1 if is_site01"
                        ),
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
        self.client.network.nsx.edge.lb.app_rule_add(edge_id, name, script)
        msg = {"msg": f"Add application rule {name} to edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("update edge load balancer application rules"),
        description=_("update edge load balancer application rules"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["id"], {"help": _("rule id"), "action": "store", "type": str}),
                (
                    ["-name"],
                    {
                        "help": _("rule name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-script"],
                    {
                        "help": _("rule script"),
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
        self.client.network.nsx.edge.lb.app_rule_update(edge_id, rule_id, name=name, script=script)
        msg = {"msg": f"Update application rule {rule_id} to edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("delete edge load balancer application rules"),
        description=_("delete edge load balancer application rules"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["id"], {"help": _("rule id"), "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_rule_del(self):
        edge_id = self.app.pargs.edge
        rule_id = self.app.pargs.id
        self.client.network.nsx.edge.lb.app_rule_del(edge_id, rule_id)
        msg = {"msg": f"Delete application rule {rule_id} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("get edge load balancer monitors"),
        description=_("get edge load balancer monitors"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["-id"], {"help": _("monitor id"), "action": "store", "type": str}),
                (["-name"], {"help": _("monitor name"), "action": "store", "type": str}),
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
                    msg = {"msg": f"Health monitor {monitor_name} not found"}
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
        help=_("add edge load balancer monitor"),
        description=_("add edge load balancer monitor"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["name"], {"help": _("monitor name"), "action": "store", "type": str}),
                (
                    ["type"],
                    {
                        "metavar": "type",
                        "help": _("monitor type {HTTP,HTTPS,TCP,ICMP,UDP}"),
                        "choices": ["HTTP", "HTTPS", "TCP", "ICMP", "UDP"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-interval"],
                    {
                        "help": _("interval in seconds in which a server is to be tested [Default=5]"),
                        "action": "store",
                        "type": int,
                        "default": 5,
                    },
                ),
                (
                    ["-timeout"],
                    {
                        "help": _(
                            "maximum time in seconds in which a response from the server must be received "
                            "[Default=15]"
                        ),
                        "action": "store",
                        "type": int,
                        "default": 15,
                    },
                ),
                (
                    ["-max_retries"],
                    {
                        "help": _(
                            "maximum number of times the server is tested before it is declared down [Default=3]"
                        ),
                        "action": "store",
                        "type": int,
                        "default": 3,
                    },
                ),
                (
                    ["-method"],
                    {
                        "help": _(
                            "method to send the health check request to the server [Default=GET for HTTP/HTTPS "
                            "monitor type]"
                        ),
                        "choices": ["GET", "POST", "OPTIONS"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-url"],
                    {
                        "help": _('URL to GET or POST [Default="/" for HTTP/HTTPS monitor type]'),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-expected"],
                    {
                        "help": _('expected string [Default="HTTP/1" for HTTP/HTTPS monitor type]'),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-send"],
                    {
                        "help": _(
                            "string to be sent to the backend server after a connection is established. This "
                            "option is mandatory when monitor type is UDP."
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-receive"],
                    {
                        "help": _(
                            "string to be received from the backend server for HTTP/HTTPS protocol. This "
                            "option is mandatory when monitor type is UDP."
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-extension"],
                    {
                        "help": _("advanced monitor configuration."),
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
        msg = {"msg": f"Add monitor {res.get('ext_id')} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("update edge load balancer service monitor"),
        description=_("update edge load balancer service monitor"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["id"], {"help": _("monitor id"), "action": "store", "type": str}),
                (
                    ["-interval"],
                    {
                        "help": _("interval in seconds in which a server is to be tested [Default=5]"),
                        "action": "store",
                        "type": int,
                        "default": 5,
                    },
                ),
                (
                    ["-timeout"],
                    {
                        "help": _(
                            "maximum time in seconds in which a response from the server must be received "
                            "[Default=15]"
                        ),
                        "action": "store",
                        "type": int,
                        "default": 15,
                    },
                ),
                (
                    ["-max_retries"],
                    {
                        "help": _(
                            "maximum number of times the server is tested before it is declared down [Default=3]"
                        ),
                        "action": "store",
                        "type": int,
                        "default": 3,
                    },
                ),
                (
                    ["-method"],
                    {
                        "help": _(
                            "method to send the health check request to the server [Default=GET for HTTP/HTTPS "
                            "monitor type]"
                        ),
                        "choices": ["GET", "POST", "OPTIONS"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-url"],
                    {
                        "help": _('URL to GET or POST [Default="/" for HTTP/HTTPS monitor type]'),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-expected"],
                    {
                        "help": _('expected string [Default="HTTP/1" for HTTP/HTTPS monitor type]'),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-send"],
                    {
                        "help": _(
                            "string to be sent to the backend server after a connection is established. This "
                            "option is mandatory when monitor type is UDP."
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-receive"],
                    {
                        "help": _(
                            "string to be received from the backend server for HTTP/HTTPS protocol. This "
                            "option is mandatory when monitor type is UDP."
                        ),
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

        self.client.network.nsx.edge.lb.monitor_update(edge_id, monitor_id, **params)
        msg = {"msg": f"Update monitor {monitor_id} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("delete edge load balancer monitor"),
        description=_("delete edge load balancer monitor"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["id"], {"help": _("monitor id"), "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_monitor_del(self):
        edge_id = self.app.pargs.edge
        monitor_id = self.app.pargs.id

        self.client.network.nsx.edge.lb.monitor_del(edge_id, monitor_id)
        msg = {"msg": f"Delete monitor {monitor_id} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("get edge load balancer virtual servers"),
        description=_("get edge load balancer virtual servers"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (
                    ["-id"],
                    {
                        "help": _("virtual server id"),
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
        help=_("add edge load balancer virtual server"),
        description=_("add edge load balancer virtual server"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (
                    ["name"],
                    {"help": _("virtual server name"), "action": "store", "type": str},
                ),
                (
                    ["ip_address"],
                    {
                        "help": _("ip address that the load balancer is listening on"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["protocol"],
                    {
                        "metavar": "protocol",
                        "help": _("virtual server protocol {HTTP,HTTPS}"),
                        "choices": ["HTTP", "HTTPS"],
                        "action": "store",
                        "type": str,
                    },
                ),
                (["port"], {"help": _("port number"), "action": "store", "type": int}),
                (
                    ["app_profile"],
                    {"help": _("application profile id"), "action": "store", "type": str},
                ),
                (["pool"], {"help": _("pool id"), "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": _("virtual server description"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-max_conn"],
                    {
                        "help": _("maximum concurrent connections"),
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-max_conn_rate"],
                    {
                        "help": _("maximum incoming new connection requests per second"),
                        "action": "store",
                        "type": int,
                    },
                ),
                (
                    ["-acceleration_enabled"],
                    {
                        "help": _("use faster L4 load balancer engine rather than L7 load balancer engine"),
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
        msg = {"msg": f"Add virtual server {res.get('ext_id')} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("update edge load balancer virtual server"),
        description=_("update edge load balancer virtual server"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["id"], {"help": _("virtual server id"), "action": "store", "type": str}),
                (
                    ["-enabled"],
                    {
                        "help": _("whether the virtual server is enabled"),
                        "choices": [True, False],
                        "action": "store",
                        "type": bool,
                    },
                ),
                (
                    ["-ip_address"],
                    {
                        "help": _("ip address that the load balancer is listening on"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-protocol"],
                    {
                        "help": _("virtual server protocol"),
                        "choices": [True, False],
                        "action": "store",
                        "type": str,
                    },
                ),
                (["-port"], {"help": _("port number"), "action": "store", "type": int}),
                (
                    ["-app_profile"],
                    {"help": _("application profile id"), "action": "store", "type": str},
                ),
                (["-pool"], {"help": _("pool id"), "action": "store", "type": str}),
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

        self.client.network.nsx.edge.lb.virt_server_update(edge_id, virt_srv_id, **params)
        msg = {"msg": f"Update virtual server {virt_srv_id} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("delete edge load balancer virtual server"),
        description=_("delete edge load balancer virtual server"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["id"], {"help": _("virtual server id"), "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_virt_server_del(self):
        edge_id = self.app.pargs.edge
        virt_srv_id = self.app.pargs.id

        self.client.network.nsx.edge.lb.virt_server_del(edge_id, virt_srv_id)
        msg = {"msg": f"Delete virtual server {virt_srv_id} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("enable edge load balancer virtual server"),
        description=_("enable edge load balancer virtual server"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["id"], {"help": _("virtual server id"), "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_virt_server_enable(self):
        edge_id = self.app.pargs.edge
        virt_srv_id = self.app.pargs.id

        self.client.network.nsx.edge.lb.virt_server_enable(edge_id, virt_srv_id)
        msg = {"msg": f"Enable virtual server {virt_srv_id} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("disable edge load balancer virtual server"),
        description=_("disable edge load balancer virtual server"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (["id"], {"help": _("virtual server id"), "action": "store", "type": str}),
            ]
        ),
    )
    def edge_lb_virt_server_disable(self):
        edge_id = self.app.pargs.edge
        virt_srv_id = self.app.pargs.id

        self.client.network.nsx.edge.lb.virt_server_disable(edge_id, virt_srv_id)
        msg = {"msg": f"Disable virtual server {virt_srv_id} on edge {edge_id}"}
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("Add account in description of nsx virtual server"),
        description=_("add account in description of nsx virtual server"),
        arguments=VSPHERE_ARGS(
            [
                (["edge"], {"help": _("edge id"), "action": "store", "type": str}),
                (
                    ["-id"],
                    {
                        "help": _("virtual server id"),
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
            nodes_uri = f"{controller.api.baseuri}/nodes"
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
                    self.app.log.debug(f"Skip {edge_id} {vs_id} it has no enabled ip in pool {pool_id}")
                account_desc = get_account_desc_by_params(controller, params)
                vs["account"] = account_desc

        def update_vs_descriptions(edge_pool_vs):
            for edge_id in edge_pool_vs:
                vss = edge_pool_vs[edge_id].values()
                for vs in vss:
                    vs_id = vs["virtualServerId"]
                    vs_description = vs.get("virtualServerDescription")
                    if vs_description is not None and '"account":' in vs_description:
                        self.app.log.debug(f"Skip {edge_id} {vs_id} it has description {vs_description}")
                        continue
                    account = vs["account"]
                    if account is None:
                        continue
                    params = {
                        "description": {"account": account},
                    }
                    self.app.log.debug(f"Update {edge_id} {vs_id} with account {account}")
                    net_nsx_lb.virt_server_update(edge_id, vs_id, **params)

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
                    self.app.log.debug(f"Skip {edge_id} {vs_id} it is disabled")
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
        help=_("list vsphere dlr"),
        description=_("list vsphere dlr"),
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
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
        help=_("Clone Vsphere server"),
        description=_("Clone an Existing VSphere Virtual Machine"),
        example="beehive platform vsphere server-clone-v1 -id vm-##### -e <env>",
        arguments=VSPHERE_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("Existing server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("server clone name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["hostname"],
                    {
                        "help": _("server hostname"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-domain"],
                    {
                        "help": _("domain name of the site where to put the cloned vm"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-destenv"],
                    {
                        "help": _("destination environment where migrate the cloned vm"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-folder"],
                    {
                        "help": _("vsphere parent folder id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-datastore"],
                    {
                        "help": _("datastore id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-cluster"],
                    {
                        "help": _("cluster id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dvpg"],
                    {
                        "help": _("dvportgroup"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-password"],
                    {
                        "help": _("admin password for the new cloned vm"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ipaddr"],
                    {
                        "help": _("ip address for the new cloned vm"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subnet"],
                    {
                        "help": _("subnet mask for the new cloned vm"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-defaultgw"],
                    {
                        "help": _("default gateway for the new cloned vm"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-httpproxy"],
                    {
                        "help": _("http proxy ip_addr:port for the new cloned vm"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-httpsproxy"],
                    {
                        "help": _("https proxy ip_addr:port for the new cloned vm"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dns1"],
                    {
                        "help": _("primary dns server for the new cloned vm"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dns2"],
                    {
                        "help": _("secondary dns server for the new cloned vm"),
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
            raise Exception(f"Vsphere Server {oid} does not exist")

        network = None
        if dest_dvportgroup_id is not None:
            network = client_dest.network.get_network(dest_dvportgroup_id)
            if network is None:
                raise Exception(f"Vsphere dvportgroup {dest_dvportgroup_id} does not exist")

        dest_folder = None
        if dest_folder_id is not None:
            dest_folder = client_dest.folder.get(dest_folder_id)
            if dest_folder is None:
                raise Exception(f"Vsphere Folder {dest_folder_id} does not exist")

        dest_datastore = None
        if dest_datastore_id is not None:
            dest_datastore = client_dest.datastore.get(dest_datastore_id)
            if dest_datastore is None:
                raise Exception(f"Vsphere Datastore {dest_datastore_id} does not exist")

        dest_cluster = None
        if dest_cluster_id is not None:
            dest_cluster = client_dest.cluster.get(dest_cluster_id)
            if dest_cluster is None:
                raise Exception(f"Vsphere Cluster {dest_cluster_id} does not exist")

        self.app.log.debug(
            "Cloning Vsphere server %s into %s (cluster %s, datastore %s, folder %s, dvpg %s)",
            oid, dest_server_name, dest_cluster_id, dest_datastore_id, dest_folder_id, dest_dvportgroup_id
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
                {"msg": f"Cloned vm {oid} into vm {cloned_vm_id} located on vcenter {dest_vsphere_id}"}
            )
        else:
            self.app.render({"msg": f"Fail to clone to clone vm {oid}"})
            if (
                clone_task.info is not None
                and clone_task.info.error is not None
                and len(clone_task.info.error.faultMessage) > 0
            ):
                self.app.render(clone_task.info.error.faultMessage[0].message)
