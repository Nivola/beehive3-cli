# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from base64 import b64decode
from six import ensure_text
from cement import ex
from beecell.types.type_list import merge_list
from beecell.types.type_dict import dict_get
from beecell.simple import get_pretty_size
from beedrones.openstack.client import OpenstackManager
from beedrones.virt.manager import VirtManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS
from beehive3_cli.core.util import load_environment_config


def OPENSTACK_ARGS(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": "openstack platform reference label",
            },
        ),
        (
            ["-P", "--project"],
            {
                "action": "store",
                "dest": "project",
                "help": "openstack current project name",
            },
        ),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class VirshPlatformController(BaseController):
    class Meta:
        label = "virsh"
        stacked_on = "platform"
        stacked_type = "nested"
        description = "libvirt platform"
        help = "libvirt platform"

    def pre_command_run(self):
        super(VirshPlatformController, self).pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("openstack", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No openstack default platform is available for this environment. Select " "another environment"
                )

        if label not in orchestrators:
            raise Exception("Valid label are: %s" % ", ".join(orchestrators.keys()))
        conf = orchestrators.get(label)

        project = getattr(self.app.pargs, "project", None)
        if project is None:
            project = conf.get("project")
        uri = "%s://%s:%s%s" % (
            conf.get("proto"),
            conf.get("vhost"),
            conf.get("port"),
            conf.get("path"),
        )
        self.client = OpenstackManager(uri, default_region=conf.get("region"))
        self.client.authorize(
            conf.get("user"),
            conf.get("pwd"),
            project=project,
            domain=conf.get("domain"),
            key=self.key,
        )

        self.user = dict_get(conf, "node_params.user")
        self.user_key = dict_get(conf, "node_params.sshkey")

    def __get_virt_manager(self, host):
        hid = host.replace(".", "-")
        data = ensure_text(b64decode(self.user_key))
        data = data.rstrip("\n")
        fp = self.create_temp_file(data)
        keyname = fp.name
        client = VirtManager(hid, host, user=self.user, key=keyname)
        self.app.log.info("get virtmanager: %s" % client)
        server = client.connect()
        fp.close()
        return server

    @ex(
        help="get libvirt hosts",
        description="get libvirt hosts",
        arguments=OPENSTACK_ARGS(),
    )
    def hosts(self):
        nodes = self.client.system.compute_hypervisors()
        resp = []
        for node in nodes:
            host_ip = node.get("host_ip")
            try:
                server = self.__get_virt_manager(host_ip)
                item = server.info()
                resp.append(item)
            except Exception as ex:
                self.app.error(ex)
                self.app.log.error(ex, exc_info=True)
                resp.append({"ip_address": host_ip})

        headers = [
            "hostname",
            "hypervisor",
            "arch",
            "cpu",
            "ram",
            "ip_address",
            "vm-running",
        ]
        fields = [
            "hostname",
            "hypervisor.version",
            "info.0",
            "info.2",
            "info.1",
            "ip_address",
            "vm_running",
        ]
        self.app.render(resp, headers=headers, fields=fields, maxsize=200)

    @ex(
        help="get libvirt host domains",
        description="get libvirt host domains",
        arguments=OPENSTACK_ARGS(
            [
                (["hostip"], {"help": "host ip", "action": "store", "type": str}),
                (
                    ["-status"],
                    {
                        "help": "domain status can be: 1 - ACTIVE, 2 - INACTIVE, 4 - PERSISTENT, 8 - TRANSIENT, "
                        "16 - RUNNING, 32 - PAUSED, 64 - SHUTOFF, 128 - OTHER",
                        "action": "store",
                        "type": int,
                        "default": 1,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": "domain name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def domain_get(self):
        host_ip = self.app.pargs.hostip
        status = self.app.pargs.status
        domain = self.app.pargs.id
        server = self.__get_virt_manager(host_ip)
        if domain is None:
            domains = server.get_domains(status=status)
            resp = [d.info() for d in domains]
            headers = [
                "uuid",
                "name",
                "ops-name",
                "ops-project",
                "cpu",
                "ram",
                "ip-address",
                "active",
                "state",
                "time",
                "quest_agent",
            ]
            fields = [
                "uuid",
                "name",
                "metadata.nova:instance.nova:name",
                "metadata.nova:instance.nova:owner.nova:project.uuid",
                "cpu.sockets",
                "memory.#text",
                "ifaces.eth0.addrs.0.addr",
                "active",
                "state",
                "time",
                "quest_agent",
            ]
            self.app.render(resp, headers=headers, fields=fields, maxsize=200)
        else:
            domain = server.get_domain(name=domain)
            resp = domain.ext_info()
            if self.is_output_text():
                guest_info = resp.pop("guest_info", {}).get("supported_commands", [])
                file_system_info = resp.pop("file_system_info", [])
                devices = resp.pop("devices", [])
                metadata = resp.pop("metadata", {}).get("nova:instance")
                sysinfo = resp.pop("sysinfo", {}).get("system", {}).get("entry", [])
                ifaces = resp.pop("ifaces", {})
                self.app.render(resp, details=True)
                self.c("\nsystem info", "underline")
                self.app.render(sysinfo, headers=["name", "#text"])
                self.c("\nmetadata", "underline")
                self.app.render(metadata, details=True)
                self.c("\nguest info", "underline")
                self.app.render(guest_info, headers=["name", "enabled", "success-response"])
                self.c("\ndevice info", "underline")
                headers = {
                    "disk": [
                        "device",
                        "type",
                        "source.file",
                        "target.dev",
                        "target.bus",
                    ],
                    "controller": ["type", "index", "model"],
                    "interface": [
                        "type",
                        "mac.address",
                        "source.bridge",
                        "virtualport.type",
                        "target.dev",
                        "mtu.size",
                    ],
                    "serial": ["type", "log.file", "target.type", "target.port"],
                    "console": ["type", "log.file", "target.type", "target.port"],
                    "channel": [
                        "type",
                        "source.mode",
                        "source.path",
                        "target.type",
                        "target.name",
                        "address.type",
                    ],
                    "input": ["type", "address.type", "address.port"],
                    "graphics": ["type", "port", "autoport", "listen.0"],
                    "video": ["model.type", "model.vram", "address.type"],
                    "memballoon": ["model", "address.type"],
                }
                for k, v in devices.items():
                    self.c("\ndevice %s" % k, "underline")
                    self.app.render(v, headers=headers.get(k), maxsize=200)
                self.c("\ninterface info", "underline")
                interfaces = []
                for k, v in ifaces.items():
                    for addr in v.get("addrs"):
                        item = {"name": k, "macaddress": v["hwaddr"]}
                        item.update(addr)
                        interfaces.append(item)
                self.app.render(interfaces, headers=["name", "macaddress", "type", "addr", "prefix"])
                self.c("\nfile system info", "underline")
                self.app.render(
                    file_system_info,
                    headers=[
                        "name",
                        "mountpoint",
                        "type",
                        "disk.0.bus-type",
                        "size",
                        "usage",
                    ],
                )
            else:
                self.app.render(resp, details=True)

    @ex(
        help="ping libvirt host domains",
        description="ping libvirt host domains",
        arguments=OPENSTACK_ARGS(
            [
                (["hostip"], {"help": "host ip", "action": "store", "type": str}),
                (
                    ["-id"],
                    {
                        "help": "domain name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def domain_ping(self):
        host_ip = self.app.pargs.hostip
        domain = self.app.pargs.id
        server = self.__get_virt_manager(host_ip)
        if domain is None:
            domains = server.get_domains(status=1)
            resp = []
            for d in domains:
                info = d.info()
                info["ping"] = d.qemu_guest_ping()
                resp.append(info)
            headers = ["uuid", "name", "ops-name", "ip-address", "ping"]
            fields = [
                "uuid",
                "name",
                "metadata.nova:instance.nova:name",
                "ifaces.eth0.addrs.0.addr",
                "ping",
            ]
            self.app.render(resp, headers=headers, fields=fields, maxsize=200)
        else:
            domain = server.get_domain(name=domain)
            self.app.render(domain.ext_info(), details=True)

    @ex(
        help="get libvirt host domain usage date",
        description="get libvirt host domain usage data",
        arguments=OPENSTACK_ARGS(
            [
                (["hostip"], {"help": "host ip", "action": "store", "type": str}),
                (
                    ["-id"],
                    {
                        "help": "domain name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def domain_usage(self):
        host_ip = self.app.pargs.hostip
        domain = self.app.pargs.id
        server = self.__get_virt_manager(host_ip)
        if domain is None:
            resp = []
            domains = server.get_domains(status=1)
            for d in domains:
                info = d.info()
                info["ping"] = d.qemu_guest_ping()
                d.qemu_guest_exec_ping("10.101.0.10")
                resp.append(info)

            def transform_file_system(data):
                resp = []
                for item in data:
                    resp.append("%s: %s" % (item["mountpoint"], item.get("usage", "%")))
                return ", ".join(resp)

            def transform_ifaces(data):
                resp = []
                for item in data:
                    resp.append(
                        "%s: rx %s,tx %s"
                        % (
                            item["name"],
                            dict_get(item, "statistics.rx-bytes", default=""),
                            dict_get(item, "statistics.tx-bytes", default=""),
                        )
                    )
                return ", ".join(resp)

            transform = {
                "file_system": transform_file_system,
                "ifaces": transform_ifaces,
            }

            headers = [
                "uuid",
                "name",
                "ops-name",
                "ip-address",
                "ping",
                "file_system",
                "ifaces",
            ]
            fields = [
                "uuid",
                "name",
                "metadata.nova:instance.nova:name",
                "ifaces.1.ip-addresses.0.ip-address",
                "ping",
                "file_system",
                "ifaces",
            ]
            self.app.render(resp, headers=headers, fields=fields, maxsize=200, transform=transform)
        else:
            domain = server.get_domain(name=domain)
            self.app.render(domain.ext_info(), details=True)

    @ex(
        help="get libvirt host domain stats",
        description="get libvirt host domain stats",
        arguments=OPENSTACK_ARGS(
            [
                (["hostip"], {"help": "host ip", "action": "store", "type": str}),
                (
                    ["-id"],
                    {
                        "help": "domain name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def domain_stats(self):
        host_ip = self.app.pargs.hostip
        domain = self.app.pargs.id
        server = self.__get_virt_manager(host_ip)
        if domain is None:
            data = server.get_domain_stats(status=1)
            resp = []
            for item in data:
                net_count = item.get("net.count")
                vcpu_count = item.get("vcpu.current")
                block_count = item.get("block.count")
                blocks = {}
                for i in range(block_count):
                    size = int(item.get("block.%s.capacity" % i))
                    allocation = int(item.get("block.%s.allocation" % i))
                    usage = round((1 - allocation / size) * 100, 1)
                    blocks[item.get("block.%s.name" % i)] = {
                        "size": get_pretty_size(size),
                        "usage": str(usage) + "%",
                    }
                row = {
                    "name": item["name"],
                    "net": {
                        "count": net_count,
                        "tx": [get_pretty_size(item.get("net.%s.tx.bytes" % i)) for i in range(net_count)],
                        "rx": [get_pretty_size(item.get("net.%s.rx.bytes" % i)) for i in range(net_count)],
                    },
                    "vcpu": {
                        "count": vcpu_count,
                        "time": [item.get("vcpu.%s.time" % i) for i in range(vcpu_count)],
                    },
                    "block": blocks,
                    "memory": {
                        "current": get_pretty_size(item.get("balloon.current")),
                        "usable": get_pretty_size(item.get("balloon.usable")),
                    },
                }
                resp.append(row)

            headers = ["name", "vcpu", "memory.free", "net.tx", "net.rx", "block"]
            fields = [
                "name",
                "vcpu.count",
                "memory.usable",
                "net.tx",
                "net.rx",
                "block",
            ]
            self.app.render(resp, headers=headers, fields=fields, maxsize=200)
        else:
            domain = server.get_domain(name=domain)
            self.app.render(domain.ext_info(), details=True)

    @ex(
        help="get libvirt host domains",
        description="get libvirt host domains",
        arguments=OPENSTACK_ARGS(
            [
                (["hostip"], {"help": "host ip", "action": "store", "type": str}),
                (
                    ["-status"],
                    {
                        "help": "domain status can be: 1 - ACTIVE, 2 - INACTIVE, 4 - PERSISTENT, 8 - TRANSIENT, "
                        "16 - RUNNING, 32 - PAUSED, 64 - SHUTOFF, 128 - OTHER",
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
            ]
        ),
    )
    def servers(self):
        host_ip = self.app.pargs.hostip
        status = self.app.pargs.status

        host = self.__get_virt_manager(host_ip)
        domains = host.get_domains(status=status)
        domains = [d.info() for d in domains]
        servers = self.client.server.list(detail=True, host=host.info()["hostname"])

        resp = {}
        for s in servers:
            instance_name = s["OS-EXT-SRV-ATTR:instance_name"]
            item = {
                "virt_id": None,
                "virt_name": instance_name,
                "ops_id": s["id"],
                "ops_name": s["name"],
                "ops_status": s["status"],
                "is_openstack": True,
                "is_virt": False,
            }
            resp[s["OS-EXT-SRV-ATTR:instance_name"]] = item

        for d in domains:
            item = {
                "virt_id": d["uuid"],
                "virt_name": d["name"],
                "virt_status": d["state"],
                "is_virt": True,
            }
            if d["name"] in resp:
                resp[d["name"]].update(item)
            else:
                resp[d["name"]] = item

        resp = list(resp.values())

        headers = [
            "ops_id",
            "ops_name",
            "ops_status",
            "virt_id",
            "virt_name",
            "virt_status",
            "is_openstack",
            "is_virt",
        ]
        self.app.render(resp, headers=headers, maxsize=200)
