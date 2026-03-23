# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from sys import stdout
from datetime import datetime
from time import sleep, time
from copy import deepcopy
from ujson import loads
from cement import ex

from beecell.types.type_string import str2bool
from beecell.types.type_dict import dict_get
from beecell.types.type_date import format_date
from beecell.types.type_list import merge_list
from beedrones.openstack.client import OpenstackManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS, StringAction
from beehive3_cli.core.util import load_environment_config, load_config, stoprotation, rotating_bar
from beehive3_cli.translate import _


def OPENSTACK_ARGS(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": _("openstack platform reference label"),
            },
        ),
        (
            ["-P", "--project"],
            {
                "action": "store",
                "dest": "project",
                "help": _("openstack current project name"),
            },
        ),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class OpenstackPlatformController(BaseController):
    class Meta:
        label = "openstack"
        stacked_on = "platform"
        stacked_type = "nested"
        description = _("openstack platform")
        help = _("openstack platform")

    def pre_command_run(self):
        super().pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("openstack", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No openstack default platform is available for this environment. Select another environment"
                )

        if label not in orchestrators:
            raise Exception(f"Valid label are: {', '.join(orchestrators.keys())}")

        conf = orchestrators.get(label)

        project = getattr(self.app.pargs, "project", None)
        if project is None:
            project = conf.get("project")

        proto = conf.get("proto")
        vhost = conf.get("vhost")
        port = conf.get("port")
        path = conf.get("path")
        uri = f"{proto}://{vhost}:{port}{path}"

        if self.app.config.get("log.clilog", "verbose_log"):
            # log to stdout and to logfile
            self.app.print(f"Using openstack orchestrator: {label} (uri: {uri} - project: {project})", color="YELLOW")
            self.app.log.debug(f"Using openstack orchestrator: {label} (uri: {uri} - project: {project})")

        command = getattr(self.app.pargs, "command", None)

        self.client = OpenstackManager(uri, default_region=conf.get("region"))
        if command in ('token-release', 'token-validate'):
            print(f"no authorize per command: {command}")
        else:
            self.client.authorize(
                conf.get("user"),
                conf.get("pwd"),
                project=project,
                domain=conf.get("domain"),
                key=self.key,
            )

        # get mariadb config
        mariadb_confg = conf.get("mariadb", None)
        self.mariadb = {}
        if mariadb_confg is not None:
            self.mariadb = {
                "hosts": mariadb_confg.get("hosts"),
                "port": mariadb_confg.get("port"),
                "user": mariadb_confg.get("user"),
                "pwd": mariadb_confg.get("pwd"),
            }

    def __get_orchestartors(self, instances, vip=True):
        """ """
        self.config = load_environment_config(self.app)
        orchestrators = self.config.get("orchestrators", {}).get("openstack", {})
        orchestrators_available = orchestrators.keys()

        confs = []
        if instances is None:
            instances = orchestrators_available
        else:
            instances = instances.split(",")
        for instance in instances:
            if instance not in orchestrators_available:
                self.app.log.error(f"Select orchestrators among: {orchestrators_available}")
                raise Exception(f"Select orchestrators among: {orchestrators_available}")

            conf = orchestrators.get(instance)
            hosts = conf.pop("hosts")
            if vip is True:
                hosts = [conf.get("vhost")]
            for host in hosts:
                uri = f"{conf.get('proto')}://{host}:{conf.get('port')}{conf.get('path')}"
                new_conf = deepcopy(conf)
                new_conf["instance"] = instance
                new_conf["uri"] = uri
                new_conf["host"] = host
                confs.append(new_conf)
        return confs

    def __get_client(self, conf):
        """ """
        client = OpenstackManager(conf.get("uri"), default_region=conf.get("region"))
        client.authorize(
            conf.get("user"),
            str(conf.get("pwd")),
            project=conf.get("project"),
            domain=conf.get("domain"),
            key=self.key,
        )
        return client

    def __get_mariadb_engine(self, host, port, user, db):
        from beecell.db import MysqlManager

        db_uri = f"mysql+pymysql://{user['name']}:{user['password']}@{host}:{port}/{db}"
        server = MysqlManager(1, db_uri)
        server.create_simple_engine()
        self.app.log.info(f"Get maria engine for {db_uri}")
        return server

    def run_cmd(self, func, configs):
        """Run command on openstack instances"""
        try:
            resp = []
            for config in configs:
                start = time()
                res = func(config)
                elapsed = time() - start
                resp.append(
                    {
                        "instance": config["instance"],
                        "host": config["host"],
                        "elapsed": elapsed,
                        "response": res,
                    }
                )
                self.app.log.info(f"Query openstack {config['host']} : {elapsed}")
            self.app.render(resp, headers=["instance", "host", "elapsed", "response"], maxsize=300)
        except Exception as exc:
            self.error(exc)

    @ex(
        help=_("ping mariadb instances"),
        description=_("ping mariadb instances"),
        example="beehive platform openstack mariadb-ping -e <env>",
        arguments=OPENSTACK_ARGS([]),
    )
    def mariadb_ping(self):
        hosts = self.mariadb.get("hosts", [])
        port = self.mariadb.get("port")
        user = {"name": self.mariadb.get("user"), "password": self.mariadb.get("pwd")}
        db = "mysql"

        resp = []
        for host in hosts:
            server = self.__get_mariadb_engine(host, port, user, db)
            res = server.ping()
            resp.append({"host": host, "response": res})
            self.app.log.info(f"Ping maria : {res}")

        self.app.render(resp, headers=["host", "response"])

    @ex(
        help=_("get mariadb galera cluster status"),
        description=_("get mariadb galera cluster status"),
        example="beehive platform openstack mariadb-cluster-status -e <env>",
        arguments=OPENSTACK_ARGS([]),
    )
    def mariadb_cluster_status(self):
        hosts = self.mariadb.get("hosts", [])
        port = self.mariadb.get("port")
        user = {"name": self.mariadb.get("user"), "password": self.mariadb.get("pwd")}
        db = "mysql"

        resp = []
        cluster_size = len(hosts)
        for host in hosts:
            try:
                server = self.__get_mariadb_engine(host, port, user, db)
                status = server.get_galera_cluster_status()
                self.app.log.info(f"get maria cluster status : {status}")
                summary_status = (
                    (status["wsrep_cluster_status"] == "Primary")
                    and int(status["wsrep_cluster_size"]) == cluster_size
                    and (status["wsrep_local_state_comment"] == "Synced")
                )
                status.update({"check_host": host, "status": summary_status})
                resp.append(status)
            except Exception as exc:
                self.app.log.error(exc)
                status = {"check_host": host, "status": False}
                resp.append(status)

        headers = [
            "check_host",
            "wsrep_cluster_status",
            "wsrep_cluster_size",
            "wsrep_local_state_comment",
            "status",
        ]
        self.app.render(resp, headers=headers)

    @ex(
        help=_("ultra ping openstack"),
        description=_("ultra ping openstack"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-vip"],
                    {
                        "help": _("if true check only the vip"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
    )
    def ultra_ping(self):
        instances = None
        vip = str2bool(self.app.pargs.vip)

        def func(conf):
            try:
                client = self.__get_client(conf)
                client.ping()
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)
                return False
            return True

        configs = self.__get_orchestartors(instances, vip=vip)
        self.run_cmd(func, configs)

    @ex(
        help=_("ultra ping openstack instances using an heavy query"),
        description=_("ultra ping openstack instances using an heavy query"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-vip"],
                    {
                        "help": _("if true check only the vip"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
    )
    def ultra_ping2(self):
        instances = None
        vip = str2bool(self.app.pargs.vip)

        def func(conf):
            try:
                client = self.__get_client(conf)
                client.server.list()
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)
                return False
            return True

        configs = self.__get_orchestartors(instances, vip=vip)
        self.run_cmd(func, configs)

    @ex(
        help=_("ultra ping openstack instances components"),
        description=_("ultra ping openstack instances components"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-vip"],
                    {
                        "help": _("if true check only the vip"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
    )
    def ultra_ping3(self):
        instances = None
        vip = str2bool(self.app.pargs.vip)

        def func(conf):
            res = {
                "keystone": False,
                "compute": False,
                "block-storage": False,
                "object-storage": False,
                "network": False,
                "orchestrator": False,
                "manila": False,
                "aodh": False,
                "glance": False,
                "gnocchi": False,
                "masakari": False,
            }
            try:
                client = self.__get_client(conf)
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)
                return res

            try:
                client.identity.api()
                res["keystone"] = True
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)

            try:
                client.system.compute_api()
                res["compute"] = True
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)

            try:
                client.system.object_storage_api()
                res["object-storage"] = True
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)

            try:
                client.system.storage_api()
                res["block-storage"] = True
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)

            try:
                client.system.network_api()
                res["network"] = True
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)

            try:
                client.system.orchestrator_api()
                res["orchestrator"] = True
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)

            try:
                client.manila.api()
                res["manila"] = True
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)

            try:
                client.aodh.api()
                res["aodh"] = True
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)

            try:
                client.glance.api()
                res["glance"] = True
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)

            try:
                client.gnocchi.api()
                res["gnocchi"] = True
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)

            try:
                client.masakari.api()
                res["masakari"] = True
            except Exception as exc:
                self.app.log.error(exc, exc_info=True)

            return res

        configs = self.__get_orchestartors(instances, vip=vip)
        self.run_cmd(func, configs)

    @ex(help=_("ping openstack"), description=_("ping openstack"), arguments=OPENSTACK_ARGS())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(
        help=_("get openstack version"),
        description=_("get openstack version"),
        example="beehive platform openstack version -e <env>",
        arguments=OPENSTACK_ARGS(),
    )
    def version(self):
        res = self.client.version()
        if self.is_output_text():
            self.app.render({"msg": f"version: {res}"})
        else:
            self.app.render({"version": res}, headers=["version"])

    @ex(
        help=_("validate token openstack"),
        description=_("validate token openstack"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["token"],
                    {
                        "help": _("token"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def token_validate(self):
        identity_token = self.client.identity.token
        print(f"identity token: {identity_token}")

        token = getattr(self.app.pargs, "token", None)
        res = self.client.identity.validate_token(token)
        print(f"validate token {token} - res: {res}")

    @ex(
        help=_("release token openstack"),
        description=_("release token openstack"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["token"],
                    {
                        "help": _("token"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def token_release(self):
        identity_token = self.client.identity.token
        print(f"identity token: {identity_token}")

        token = getattr(self.app.pargs, "token", None)
        res = self.client.identity.release_token(token)
        print(f"release token {token} - res: {res}")

    @ex(
        help=_("get openstack keystone catalog"),
        description=_("get openstack keystone catalog"),
        arguments=OPENSTACK_ARGS(),
    )
    def catalog(self):
        res = self.client.get_catalog()
        self.app.render(res, details=True)

    @ex(help=_("get users"), description=_("get users"), arguments=OPENSTACK_ARGS())
    def sys_user_get(self):
        res = self.client.identity.user.list(detail=True)
        self.app.render(res, headers=["id", "name", "domain_id"])

    @ex(
        help=_("get api versions"),
        description=_("get api versions"),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_api_get(self):
        resp = []

        res = self.client.system.compute_api().get("versions", [])
        for r in res:
            r["component"] = "compute"
        resp.extend(res)

        res = self.client.system.storage_api().get("versions", [])
        for r in res:
            r["component"] = "storage"
        resp.extend(res)

        res = self.client.system.network_api().get("versions", [])
        for r in res:
            r["component"] = "network"
        resp.extend(res)

        res = self.client.system.orchestrator_api().get("versions", [])
        for r in res:
            r["component"] = "orchestrator"
        resp.extend(res)

        try:
            res = self.client.system.manila_api().get("versions", [])
            for r in res:
                r["component"] = "manila"
            resp.extend(res)
        except:
            pass

        self.app.render(
            resp,
            headers=["component", "id", "version", "min_version", "status", "updated"],
        )

    @ex(
        help=_("get api extensions"),
        description=_("get api extensions"),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_api_extension_get(self):
        resp = []
        res = self.client.system.network_api_extension().get("extensions", [])
        for r in res:
            r["component"] = "network"
        resp.extend(res)
        self.app.render(resp, headers=["component", "name", "alias", "description", "updated"])

    @ex(
        help=_("get compute services"),
        description=_("get compute service"),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_compute_service_get(self):
        res = self.client.system.compute_services()
        headers = ["id", "host", "zone", "binary", "state", "status", "updated_at"]
        self.app.render(res, headers=headers, maxsize=200)

    @ex(
        help=_("get compute availability zones"),
        description=_("get compute availability zones"),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_compute_zone_get(self):
        res = self.client.system.compute_zones()
        resp = []
        for item in res:
            hosts = item.get("hosts", {})
            if hosts is None:
                hosts = {}
            resp.append(
                {
                    "state": item["zoneState"]["available"],
                    "hosts": ",".join(hosts.keys()),
                    "name": item["zoneName"],
                }
            )
        self.app.render(resp, headers=["name", "hosts", "state"], maxsize=200)

    @ex(
        help=_("get physical hosts"),
        description=_("get physical hosts"),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_compute_host_get(self):
        res = self.client.system.compute_hosts()
        self.app.render(res, headers=["service", "host_name", "zone"], maxsize=200)

    @ex(
        help=_("set physical host status"),
        description=_("set physical host status"),
        arguments=OPENSTACK_ARGS([(["host"], {"help": _("host id"), "action": "store", "type": str})]),
    )
    def sys_compute_host_status(self):
        host = self.app.pargs.host
        self.client.system.compute_host_status(host)
        self.app.render({"msg": f"set host {host} status"})

    @ex(
        help=_("get compute host aggregates"),
        description=_("get compute host aggregates"),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_compute_host_aggregate_get(self):
        res = self.client.system.compute_host_aggregates()
        self.app.render(
            res,
            headers=["id", "name", "availability_zone", "hosts", "created_at"],
            maxsize=200,
        )

    @ex(
        help=_(
            "displays extra statistical information from the machine that hosts the hypervisor through the API for "
            "the hypervisor (XenAPI or KVM/libvirt)."
        ),
        description=_(
            "displays extra statistical information from the machine that hosts the hypervisor through the "
            "API for the hypervisor (XenAPI or KVM/libvirt)."
        ),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_compute_hypervisor_get(self):
        res = self.client.system.compute_hypervisors()
        headers = [
            "id",
            "hypervisor_hostname",
            "host_ip",
            "status",
            "state",
            "vcpus",
            "vcpus_used",
            "memory_mb",
            "free_ram_mb",
            "local_gb",
            "local_gb_used",
            "free_disk_gb",
            "current_workload",
            "running_vms",
        ]
        self.app.render(res, headers=headers, maxsize=200)

    @ex(
        help=_("compute hypervisors statistics"),
        description=_("compute hypervisors statistics"),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_compute_hypervisor_stats(self):
        res = self.client.system.compute_hypervisors_statistics()
        headers = [
            "count",
            "vcpus_used",
            "local_gb_used",
            "memory_mb",
            "current_workload",
            "vcpus",
            "running_vms",
            "free_disk_gb",
            "disk_available_least",
            "local_gb",
            "free_ram_mb",
            "memory_mb_used",
        ]
        self.app.render(res, headers=headers, maxsize=200)

    @ex(
        help=_(
            "displays extra statistical information from the machine that hosts the hypervisor through the API for "
            "the hypervisor (XenAPI or KVM/libvirt)."
        ),
        description=_(
            "displays extra statistical information from the machine that hosts the hypervisor through the "
            "API for the hypervisor (XenAPI or KVM/libvirt)."
        ),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_compute_hypervisor_servers(self):
        hosts = self.client.system.compute_hypervisors()
        host_idx = {h["hypervisor_hostname"]: h for h in hosts}
        for h in hosts:
            h["vms"] = {"nostate": 0}

        servers = self.client.server.list(detail=True, limit=10000)
        for s in servers:
            status = s["status"]
            power_state = s["OS-EXT-STS:power_state"]
            host = s["OS-EXT-SRV-ATTR:host"]
            h = host_idx.get(host)
            if power_state == 0:
                h["vms"]["nostate"] += 1
            else:
                if status not in h["vms"]:
                    h["vms"][status] = 1
                else:
                    h["vms"][status] += 1

        headers = [
            "id",
            "hypervisor_hostname",
            "host_ip",
            "status",
            "state",
            "running_vms",
            "vms",
        ]
        self.app.render(hosts, headers=headers, maxsize=200)

    @ex(
        help=_(
            "get compute agents. Use guest agents to access files on the disk, configure networking, and run other "
            "applications and scripts in the guest while it runs. This hypervisor-specific extension is not currently "
            "enabled for KVM. Use of guest agents is possible only if the underlying service provider uses the Xen "
            "driver."
        ),
        description=_(
            "get compute agents. Use guest agents to access files on the disk, configure networking, and run "
            "other applications and scripts in the guest while it runs. This hypervisor-specific extension is "
            "not currently enabled for KVM. Use of guest agents is possible only if the underlying service "
            "provider uses the Xen driver."
        ),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_compute_agent_get(self):
        """Get"""
        res = self.client.system.compute_agents()
        self.app.render(res, headers=[], maxsize=200)

    @ex(
        help=_("get storage service."),
        description=_("get storage service."),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_storage_service_get(self):
        res = self.client.system.storage_services()
        headers = ["id", "host", "zone", "binary", "state", "status", "updated_at"]
        self.app.render(res, headers=headers, maxsize=200)

    @ex(
        help=_("lists all hosts summary info that is not disabled"),
        description=_("lists all hosts summary info that is not disabled"),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_storage_host_get(self):
        res = self.client.volume_v3.list_hosts()
        headers = [
            "zone",
            "service",
            "service-status",
            "service-state",
            "host_name",
            "last-update",
        ]
        self.app.render(res, headers=headers)

    @ex(
        help=_("lists all back-end storage pools"),
        description=_("lists all back-end storage pools"),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_storage_backend_storage_pool_get(self):
        res = self.client.volume_v3.get_backend_storage_pools()
        headers = [
            "name",
            "qos",
            "protocol",
            "driver_version",
            "reserved_%",
            "backend_name",
            "free_gb",
            "total_gb",
            "updated",
        ]
        fields = [
            "name",
            "capabilities.QoS_support",
            "capabilities.storage_protocol",
            "capabilities.driver_version",
            "capabilities.reserved_percentage",
            "capabilities.volume_backend_name",
            "capabilities.free_capacity_gb",
            "capabilities.total_capacity_gb",
            "capabilities.updated",
        ]
        self.app.render(res, headers=headers, fields=fields, maxsize=200)

    @ex(
        help=_("shows capabilities for a storage back end"),
        description=_("shows capabilities for a storage back end"),
        arguments=OPENSTACK_ARGS([(["host"], {"help": _("host id"), "action": "store", "type": str})]),
    )
    def sys_storage_backend_capabilitie(self):
        oid = self.app.pargs.host
        res = self.client.volume_v3.get_backend_capabilities(oid)

        def manage_data(data):
            props = data.pop("properties", {})
            sections = [
                {
                    "title": "properties",
                    "headers": ["name", "type", "description", "title"],
                    "fields": ["name", "type", "description", "title"],
                }
            ]

            section = []
            for k, v in props.items():
                v["name"] = k
                section.append(v)

            sections[0]["value"] = section

            return data, sections

        self.app.render(res, details=True, manage_data=manage_data)

    @ex(
        help=_("get network agents"),
        description=_("get network agents"),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_network_agent_get(self):
        res = self.client.system.network_agents()
        headers = [
            "id",
            "host",
            "availability_zone",
            "binary",
            "agent_type",
            "alive",
            "started_at",
        ]
        self.app.render(res, headers=headers, maxsize=200)

    @ex(
        help=_("get api versions"),
        description=_("get api versions"),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_network_service_provider_get(self):
        """Get network service providers."""
        res = self.client.system.network_service_providers()
        self.app.render(res, headers=["service_type", "name", "default"], maxsize=200)

    @ex(
        help=_("get heat services"),
        description=_("get heat services"),
        arguments=OPENSTACK_ARGS(),
    )
    def sys_orchestrator_service_get(self):
        res = self.client.system.orchestrator_services()
        headers = ["id", "host", "zone", "binary", "state", "status", "updated_at"]
        self.app.render(res, headers=headers, maxsize=200)

    @ex(
        help=_("get keystone users"),
        description=_("get keystone users"),
        arguments=OPENSTACK_ARGS(),
    )
    def keystone_user_get(self):
        res = self.client.identity.user.list(detail=True)
        self.app.render(res, headers=["id", "name", "domain_id", "enabled"])

    @ex(
        help=_("get keystone roles"),
        description=_("get keystone roles"),
        arguments=OPENSTACK_ARGS(),
    )
    def keystone_role_get(self):
        res = self.client.identity.role.list(detail=False)
        self.app.render(res, headers=["id", "name"])

    @ex(help=_("get regions"), description=_("get regions"), arguments=OPENSTACK_ARGS())
    def region_get(self):
        res = self.client.identity.get_regions()
        self.app.render(res, headers=["id", "parent_region_id", "description"])

    @ex(
        help=_("get domains"),
        description=_("get domains"),
        arguments=OPENSTACK_ARGS(
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
    def domain_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.domain.get(oid)
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.domain.list(**params)
            self.app.render(res, headers=["id", "description"])

    @ex(
        help=_("get projects"),
        description=_("get projects"),
        arguments=OPENSTACK_ARGS(
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
            res = self.client.project.get(oid)

            if self.is_output_text():
                self.app.render(res, details=True)

                quotas = self.client.project.get_quotas(oid)
                self.c("\nquotas", "underline")
                self.app.render(quotas, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.project.list(**params)
            headers = ["id", "parent_id", "domain_id", "name", "description", "enabled"]
            self.app.render(res, headers=headers)

    @ex(
        help=_("get project quotas"),
        description=_("get project quotas"),
        arguments=OPENSTACK_ARGS(
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
        oid = self.app.pargs.id
        res = self.client.project.get_quotas(oid)

        if self.is_output_text():
            resp = []
            for k, v in res.items():
                for k1, v1 in v.items():
                    data = {"component": k, "quota": k1, "value": v1}
                    resp.append(data)
            self.app.render(resp, headers=["component", "quota", "value"], maxsize=200)
        else:
            self.app.render(res, details=True)

    @ex(
        help=_("set project quotas"),
        description=_("set project quotas"),
        arguments=OPENSTACK_ARGS(
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
                    ["quota_type"],
                    {
                        "help": _("project quota type. can be compute, block, network, share"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["quota"],
                    {
                        "help": _("project quota name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["value"],
                    {
                        "help": _("project quota value"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_quota_set(self):
        oid = self.app.pargs.id
        quota_type = self.app.pargs.quota_type
        quota = self.app.pargs.quota
        value = self.app.pargs.value
        self.client.project.update_quota(oid, quota_type, quota, value)
        self.app.render(
            {"msg": f"update quota {quota_type} {quota} with value {value}"},
            maxsize=200,
        )

    @ex(
        help=_("add openstack project"),
        description=_("add openstack project"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("project name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["domain"],
                    {
                        "help": _("project domain id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("project description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("parent project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": _("enabled status"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
    )
    def project_add(self):
        name = self.app.pargs.name
        description = self.app.pargs.desc
        domain = self.app.pargs.domain
        enabled = str2bool(self.app.pargs.enabled)
        parent_id = self.app.pargs.parent
        res = self.client.project.create(
            name,
            domain,
            is_domain=False,
            parent_id=parent_id,
            description=description,
            enabled=enabled,
        )
        self.app.render({"msg": f"create project {res['id']}"})

    @ex(
        help=_("update openstack project"),
        description=_("update openstack project"),
        arguments=OPENSTACK_ARGS(
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
                    ["-name"],
                    {
                        "help": _("project name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("project description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-domain"],
                    {
                        "help": _("parent domain id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("parent project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": _("enabled status"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        description = self.app.pargs.desc
        domain = self.app.pargs.domain
        enabled = self.app.pargs.enabled
        parent_id = self.app.pargs.parent
        self.client.project.update(
            oid,
            name=name,
            domain=domain,
            enabled=enabled,
            description=description,
            parent_id=parent_id,
        )
        self.app.render({"msg": f"update project {oid}"})

    @ex(
        help=_("delete openstack project"),
        description=_("delete openstack project"),
        arguments=OPENSTACK_ARGS(
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
    def project_del(self):
        oid = self.app.pargs.id
        self.client.project.delete(oid)
        self.app.render({"msg": f"Delete project {oid}"})

    @ex(
        help=_("get openstack project members"),
        description=_("get openstack project members"),
        arguments=OPENSTACK_ARGS(
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
        oid = self.app.pargs.id
        res = self.client.project.get_members(oid)
        self.app.render(res, headers=["user_id", "user_name", "role_id", "role_name"])

    @ex(
        help=_("get openstack project default members"),
        description=_("get openstack project default members"),
        arguments=OPENSTACK_ARGS(
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
    def project_default_member_set(self):
        params = {}
        objs = self.client.project.list(**params)

        size = 200
        count = 0
        users = self.client.identity.user.list(name="admin")
        admin_id = None
        if len(users) > 0:
            admin_id = users[0].get("id")

        users = self.client.identity.user.list(name="opsviewer")
        opsviewer_id = None
        if len(users) > 0:
            opsviewer_id = users[0].get("id")

        roles = self.client.identity.role.list()
        trilio_backup_role_id = None
        for role in roles:
            if role.get("name") == "trilio_backup_role":
                trilio_backup_role_id = role.get("id")
            if role.get("name") == "admin":
                admin_role_id = role.get("id")

        for obj in objs:
            if obj.get("name").find("ComputeService-") == 0:
                roles = []
                members = self.client.project.get_members(obj.get("id"))
                print(f"project: ({obj.get('id')}, {obj.get('name')})")
                for m in members:
                    print(f"- get user role: ({m.get('user_name')}, {m.get('role_name')})")
                    roles.append((m.get("user_name"), m.get("role_name")))
                if ("admin", "trilio_backup_role") not in roles:
                    self.client.project.assign_member(obj.get("id"), admin_id, trilio_backup_role_id)
                    print("- add user role: (admin, trilio_backup_role)")
                if ("opsviewer", "trilio_backup_role") not in roles:
                    self.client.project.assign_member(obj.get("id"), opsviewer_id, trilio_backup_role_id)
                    print("- add user role: (opsviewer, trilio_backup_role)")
                if ("opsviewer", "admin") not in roles:
                    self.client.project.assign_member(obj.get("id"), opsviewer_id, admin_role_id)
                    print("- add user role: (opsviewer, admin)")
                count += 1
                if count > size:
                    break

    @ex(
        help=_("get networks"),
        description=_("get networks"),
        example="beehive platform openstack network-get -id <uuid> --env test",
        arguments=OPENSTACK_ARGS(
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
            res = self.client.network.get(oid)

            if self.is_output_text():
                res.pop("subnets", None)
                self.app.render(res, details=True)

                self.c("\nsubnets", "underline")
                subnets = self.client.network.subnet.list(network=oid)
                headers = [
                    "id",
                    "tenant_id",
                    "name",
                    "cidr",
                    "pools",
                    "gateway_ip",
                    "enable_dhcp",
                    "service_types",
                ]
                fields = [
                    "id",
                    "tenant_id",
                    "name",
                    "cidr",
                    "allocation_pools",
                    "gateway_ip",
                    "enable_dhcp",
                    "service_types",
                ]
                transform = {"allocation_pools": lambda x: f"{x[0]['start']}:{x[0]['end']}"}
                self.app.render(subnets, headers=headers, fields=fields, transform=transform)

                self.c("\nports", "underline")
                ports = self.client.network.port.list(network=oid)
                headers = [
                    "id",
                    "tenant_id",
                    "name",
                    "ip_address",
                    "mac_address",
                    "status",
                    "device_owner",
                    "security_groups",
                ]
                fields = [
                    "id",
                    "tenant_id",
                    "name",
                    "fixed_ips.0.ip_address",
                    "mac_address",
                    "status",
                    "device_owner",
                    "security_groups",
                ]
                self.app.render(ports, headers=headers, fields=fields)
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.network.list(**params)
            headers = [
                "id",
                "tenant_id",
                "name",
                "segmentation_id",
                "external",
                "shared",
                "type",
                "mtu",
            ]
            fields = [
                "id",
                "tenant_id",
                "name",
                "provider:segmentation_id",
                "router:external",
                "shared",
                "provider:network_type",
                "mtu",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("add openstack network"),
        description=_("add openstack network"),
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": _("network name"), "action": "store", "type": str}),
                (
                    ["project"],
                    {
                        "help": _("parent project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-physical_network"],
                    {
                        "help": _("physical network"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-segmentation_id"],
                    {
                        "help": _("segmentation id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("network type. Can be flat, vlan, vxlan, or gre"),
                        "action": "store",
                        "type": str,
                        "default": "vlan",
                    },
                ),
                (
                    ["-mt"],
                    {
                        "help": _("the maximum transmission unit MTU"),
                        "action": "store",
                        "type": int,
                        "default": 1500,
                    },
                ),
            ]
        ),
    )
    def network_add(self):
        name = self.app.pargs.name
        tenant_id = self.app.pargs.project
        physical_network = self.app.pargs.physical_network
        segmentation_id = self.app.pargs.segmentation_id
        network_type = self.app.pargs.type
        mtu = self.app.pargs.mtu
        self.client.network.create(
            name,
            tenant_id,
            physical_network,
            segmentation_id=segmentation_id,
            network_type=network_type,
            mtu=mtu,
        )
        self.app.render({"msg": f"add network {name}"})

    @ex(
        help=_("update openstack network"),
        description=_("update openstack network"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("network name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-shared"],
                    {
                        "help": _("network shared"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-mtu"],
                    {
                        "help": _("network mtu"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def network_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        mtu = self.app.pargs.mtu
        shared = str2bool(self.app.pargs.shared)
        self.client.network.update(oid, name=name, shared=shared, mtu=mtu)
        self.app.render({"msg": f"update network {oid}"})

    @ex(
        help=_("delete openstack network"),
        description=_("delete openstack network"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
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
    def network_del(self):
        oid = self.app.pargs.id
        self.client.network.delete(oid)
        self.app.render({"msg": f"Delete network {oid}"})

    @ex(
        help=_("get subnets"),
        description=_("get subnets"),
        example="beehive platform openstack subnet-get -id <uuid> --env test",
        arguments=OPENSTACK_ARGS(
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
                (
                    ["-project"],
                    {
                        "help": _("project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
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
    def subnet_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.network.subnet.get(oid)

            if self.is_output_text():
                self.app.render(res, details=True)

                self.c("\nallocation pool", "underline")
                report = {
                    "pool_size": res["pool_size"],
                    "pool_used": res["pool_used"],
                    "pool_available": res["pool_available"],
                }
                self.app.render(report, details=True)

                self.c("\nports", "underline")
                headers = [
                    "id",
                    "tenant_id",
                    "name",
                    "ip_address",
                    "mac_address",
                    "status",
                    "device_owner",
                    "security_groups",
                ]
                fields = [
                    "id",
                    "tenant_id",
                    "name",
                    "fixed_ips.0.ip_address",
                    "mac_address",
                    "status",
                    "device_owner",
                    "security_groups",
                ]
                ports = self.client.network.port.list(subnet_id=res["id"])
                self.app.render(ports, headers=headers, fields=fields)
            else:
                self.app.render(res, details=True)
        else:
            tenant = self.app.pargs.project
            network = self.app.pargs.network
            res = self.client.network.subnet.list(tenant=tenant, network=network)
            headers = [
                "id",
                "tenant_id",
                "name",
                "network_id",
                "cidr",
                "enable_dhcp",
                "service_types",
                "pool_size",
                "pool_used",
                "pool_available",
            ]
            fields = [
                "id",
                "tenant_id",
                "name",
                "network_id",
                "cidr",
                "enable_dhcp",
                "service_types",
                "pool_size",
                "pool_used",
                "pool_available",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("add openstack subnet"),
        description=_("add openstack subnet"),
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": _("subnet name"), "action": "store", "type": str}),
                (
                    ["network"],
                    {
                        "help": _("parent network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-gateway"],
                    {
                        "help": _("gateway ip"),
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
                    ["-enable-dhcp"],
                    {
                        "help": _("enable dhcp"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["dns"],
                    {
                        "help": _("comma separated subnet dns"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def subnet_add(self):
        name = self.app.pargs.name
        network_id = self.app.pargs.network
        gateway_ip = self.app.pargs.gateway
        cidr = self.app.pargs.cidr
        enable_dhcp = str2bool(self.app.pargs.enable_dhcp)
        dns = self.app.pargs.dns.split(",")

        network = self.client.network.get(network_id)
        tenant_id = network["tenant_id"]

        self.client.network.subnet.create(
            name,
            network_id,
            tenant_id,
            gateway_ip,
            cidr,
            allocation_pools=None,
            enable_dhcp=enable_dhcp,
            host_routes=None,
            dns_nameservers=dns,
            service_types=None,  # NB: va solo se si usa l'update ma non si sa perché
        )
        self.app.render({"msg": f"add subnet {name}"})

    @ex(
        help=_("update openstack subnet"),
        description=_("update openstack subnet"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("subnet id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("subnet name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("subnet description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def subnet_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        self.client.network.subnet.update(oid, name, desc)
        self.app.render({"msg": f"update subnet {oid}"})

    @ex(
        help=_("delete openstack subnet"),
        description=_("delete openstack subnet"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
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
    def subnet_del(self):
        oid = self.app.pargs.id
        self.client.network.subnet.delete(oid)
        self.app.render({"msg": f"Delete subnet {oid}"})

    @ex(
        help=_("get ports"),
        description=_("get ports"),
        example="beehive platform openstack port-get -id <uuid> --env test",
        arguments=OPENSTACK_ARGS(
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
                (
                    ["-project"],
                    {
                        "help": _("project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": _("network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": _("the port status. Value is ACTIVE or DOWN"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-device"],
                    {
                        "help": _("the id of the device that uses this port"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-device_owner"],
                    {
                        "help": _(
                            "the entity type that uses this port. For example: - compute:nova (server "
                            "instance), network:dhcp (DHCP agent) - network:router_interface (router "
                            "interface)."
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-security_group"],
                    {
                        "help": _("the id of any attached security groups"),
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
            res = self.client.network.port.get(oid)
            self.app.render(res, details=True)
        else:
            tenant = self.app.pargs.project
            network = self.app.pargs.network
            status = self.app.pargs.status
            device_id = self.app.pargs.device
            device_owner = self.app.pargs.device_owner
            security_group = self.app.pargs.security_group
            # subnet_id = self.app.pargs.subnet
            # ip_address = self.app.pargs.ip_address
            res = self.client.network.port.list(
                tenant=tenant,
                network=network,
                status=status,
                device_id=device_id,
                device_owner=device_owner,
                security_group=security_group,
            )
            headers = [
                "id",
                "tenant_id",
                "name",
                "ip_address",
                "mac_address",
                "status",
                "device_owner",
                "security_groups",
            ]
            fields = [
                "id",
                "tenant_id",
                "name",
                "fixed_ips.0.ip_address",
                "mac_address",
                "status",
                "device_owner",
                "security_groups",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("add openstack port"),
        description=_("add openstack port"),
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": _("port name"), "action": "store", "type": str}),
                (
                    ["network"],
                    {
                        "help": _("network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subnet"],
                    {
                        "help": _("subnet id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tenant"],
                    {
                        "help": _("tenant id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ipaddress"],
                    {
                        "help": _("ip addresses associated to subnet"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-allowed-ipaddress"],
                    {
                        "help": _("allowed ip address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-allowed-macaddress"],
                    {
                        "help": _("allowed ip macaddress"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-host"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-device_owner"],
                    {
                        "help": _("device owner"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-security_groups"],
                    {
                        "help": _("One or more security group id."),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def port_add(self):
        name = self.app.pargs.name
        tenant_id = self.app.pargs.tenant
        network_id = self.app.pargs.network
        subnet_id = self.app.pargs.subnet
        ip_address = self.app.pargs.ipaddress
        host_id = self.app.pargs.host
        allowed_ipaddress = self.app.pargs.allowed_ipaddress
        allowed_macaddress = self.app.pargs.allowed_macaddress
        device_owner = self.app.pargs.device_owner
        security_groups = self.app.pargs.security_groups

        allowed_address_pairs = None
        if allowed_ipaddress is not None or allowed_macaddress is not None:
            allowed_address_pairs = {}
            if allowed_ipaddress is not None:
                allowed_address_pairs["ip_address"] = allowed_ipaddress
            if allowed_macaddress is not None:
                allowed_address_pairs["mac_address"] = allowed_macaddress
            allowed_address_pairs = [allowed_address_pairs]

        fixed_ips = None
        if subnet_id is not None or ip_address is not None:
            fixed_ips = {}
            if subnet_id is not None:
                fixed_ips["subnet_id"] = subnet_id
            if ip_address is not None:
                fixed_ips["ip_address"] = ip_address
            fixed_ips = [fixed_ips]

        if security_groups is not None:
            security_groups = security_groups.split(",")

        network = self.client.network.get(network_id)
        if tenant_id is None:
            tenant_id = network["tenant_id"]
        res = self.client.network.port.create(
            name,
            network_id,
            fixed_ips,
            host_id=host_id,
            tenant_id=tenant_id,
            profile=None,
            vnic_type=None,
            device_owner=device_owner,
            device_id=None,
            security_groups=security_groups,
            mac_address=None,
            allowed_address_pairs=allowed_address_pairs,
        )
        self.app.render({"msg": f"add port {res['id']}"})
        self.app.render(res, details=True)

    @ex(
        help=_("add openstack port"),
        description=_("add openstack port"),
        arguments=OPENSTACK_ARGS([]),
    )
    def port_add_batch(self):
        tenant_id = "uuid..."
        network_id = "uuid..."
        subnet_id = "uuid..."
        device_owner = "vsphere:ippool"
        allocated_ports = self.client.network.port.list(network=network_id)
        allocated_port_ips = [dict_get(port, "fixed_ips.0.ip_address") for port in allocated_ports]
        ip_tmpl = "84.1.2.%s"
        for i in range(2, 171):
            ip_address = ip_tmpl % i
            fixed_ips = [{"subnet_id": subnet_id, "ip_address": ip_address}]
            allowed_address_pairs = [{"ip_address": ip_address}]
            name = f"port-{ip_address.replace('.', '-')}"
            if ip_address not in allocated_port_ips:
                port = self.client.network.port.create(
                    name,
                    network_id,
                    fixed_ips,
                    tenant_id=tenant_id,
                    profile=None,
                    vnic_type=None,
                    device_owner=device_owner,
                    allowed_address_pairs=allowed_address_pairs,
                )
                print(f"add port {port['id']}")

    @ex(
        help=_("update openstack port"),
        description=_("update openstack port"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("port id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("port name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("port description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-sgs"],
                    {
                        "help": _("port security groups comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-allowed_ips"],
                    {
                        "help": _("a comma separated list of allowed ip address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port_security_enabled"],
                    {
                        "help": _("enable or disable port security"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def port_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        sgs = self.app.pargs.sgs
        allowed_ips = self.app.pargs.allowed_ips
        port_security_enabled = self.app.pargs.port_security_enabled
        allowed_address_pairs = None
        if sgs is not None:
            sgs = sgs.split(",")
        if port_security_enabled is not None:
            port_security_enabled = str2bool(port_security_enabled)
            if port_security_enabled is False:
                allowed_address_pairs = []
                sgs = []
        if allowed_ips is not None:
            if allowed_ips == "del":
                allowed_address_pairs = []
            else:
                allowed_ips = allowed_ips.split(",")
                allowed_address_pairs = [{"ip_address": ip} for ip in allowed_ips]

        self.client.network.port.update(
            oid,
            name,
            desc,
            security_groups=sgs,
            allowed_address_pairs=allowed_address_pairs,
            port_security_enabled=port_security_enabled,
        )
        self.app.render({"msg": f"update port {oid}"})

    @ex(
        help=_("delete openstack port"),
        description=_("delete openstack port"),
        example="beehive platform openstack port-del <uuid> -e <env>",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
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
    def port_del(self):
        oid = self.app.pargs.id
        self.client.network.port.delete(oid)
        self.app.render({"msg": f"Delete port {oid}"})

    @ex(
        help=_("get floatingips"),
        description=_("get floatingips"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("floatingip id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def floatingip_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.network.floatingip.get(oid)
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.network.floatingip.list(**params)
            headers = [
                "id",
                "tenant_id",
                "status",
                "floating_ip_address",
                "fixed_ip_address",
            ]
            fields = [
                "id",
                "tenant_id",
                "status",
                "floating_ip_address",
                "fixed_ip_address",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("delete openstack floatingip"),
        description=_("delete openstack floatingip"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("floatingip id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def floatingip_del(self):
        oid = self.app.pargs.id
        self.client.network.floatingip.delete(oid)
        self.app.render({"msg": f"Delete floatingip {oid}"})

    @ex(
        help=_("get routers"),
        description=_("get routers"),
        arguments=OPENSTACK_ARGS(
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
            res = self.client.network.router.get(oid)

            if self.is_output_text():
                routes = res.pop("routes")
                self.app.render(res, details=True)
                self.c("\nroutes", "underline")
                self.app.render(routes, headers=["nexthop", "destination"])
                self.c("\nports", "underline")
                ports = self.client.network.port.list(device_id=oid)
                headers = [
                    "id",
                    "name",
                    "ip_address",
                    "mac_address",
                    "status",
                    "device_owner",
                    "security_groups",
                ]
                fields = [
                    "id",
                    "name",
                    "fixed_ips.0.ip_address",
                    "mac_address",
                    "status",
                    "device_owner",
                    "security_groups",
                ]
                self.app.render(ports, headers=headers, fields=fields)
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.network.router.list(**params)
            headers = ["id", "tenant_id", "name", "ha", "status"]
            fields = ["id", "tenant_id", "name", "ha", "status"]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("add openstack router"),
        description=_("add openstack router"),
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": _("router name"), "action": "store", "type": str}),
                (
                    ["tenant"],
                    {
                        "help": _("parent project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": _("physical router"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext-subnet"],
                    {
                        "help": _("external subnet"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext-ip"],
                    {
                        "help": _("external ip address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def router_add(self):
        name = self.app.pargs.name
        tenant_id = self.app.pargs.tenant
        network = self.app.pargs.network
        ext_subnet = self.app.pargs.ext_subnet
        ext_ip = self.app.pargs.ext_ip
        external_ips = None
        if ext_subnet is not None and ext_ip is not None:
            external_ips = [{"subnet_id": ext_subnet, "ip": ext_ip}]
        self.client.network.router.create(name, tenant_id, network, external_ips=external_ips)
        self.app.render({"msg": f"add router {name}"})

    @ex(
        help=_("update openstack router"),
        description=_("update openstack router"),
        arguments=OPENSTACK_ARGS(
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
                    ["-name"],
                    {
                        "help": _("router name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": _("physical router"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext-subnet"],
                    {
                        "help": _("external subnet"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext-ip"],
                    {
                        "help": _("external ip address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-routes"],
                    {
                        "help": _("routes like dest:nexthop,dest:nexthop"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def router_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        network = self.app.pargs.network
        ext_subnet = self.app.pargs.ext_subnet
        ext_ip = self.app.pargs.ext_ip
        routes = self.app.pargs.routes
        external_ips = None
        if ext_subnet is not None and ext_ip is not None:
            external_ips = [{"subnet_id": ext_subnet, "ip": ext_ip}]
        router_routes = None
        if routes is not None:
            router_routes = []
            for r in routes.split(","):
                d, n = r.split(":")
                router_routes.append({"nexthop": n, "destination": d})
        self.client.network.router.update(
            oid,
            name=name,
            network=network,
            external_ips=external_ips,
            routes=router_routes,
        )
        self.app.render({"msg": f"update router {oid}"})

    @ex(
        help=_("reset openstack router routes"),
        description=_("reset openstack router routes"),
        arguments=OPENSTACK_ARGS(
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
            ]
        ),
    )
    def router_reset_routes(self):
        oid = self.app.pargs.id
        self.client.network.router.update(oid, routes=[])
        self.app.render({"msg": f"reset router {oid} routes"})

    @ex(
        help=_("rewrite existing openstack router routes"),
        description=_("rewrite existing openstack router routes"),
        arguments=OPENSTACK_ARGS(
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
            ]
        ),
    )
    def router_rewrite_routes(self):
        oid = self.app.pargs.id

        res = self.client.network.router.get(oid)
        routes = res.pop("routes")

        router_routes = []
        for route in routes:
            router_routes.append(
                {
                    "nexthop": route.get("nexthop"),
                    "destination": route.get("destination"),
                }
            )

        self.client.network.router.update(oid, routes=[])
        print("reset routes")
        sleep(5)
        self.client.network.router.update(oid, routes=router_routes)
        print(f"apply routes: {routes}")

    @ex(
        help=_("delete openstack router"),
        description=_("delete openstack router"),
        arguments=OPENSTACK_ARGS(
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
            ]
        ),
    )
    def router_del(self):
        oid = self.app.pargs.id
        self.client.network.router.delete(oid)
        self.app.render({"msg": f"Delete router {oid}"})

    @ex(
        help=_("add openstack router internal interfafe"),
        description=_("add openstack router internal interfafe"),
        arguments=OPENSTACK_ARGS(
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
                (
                    ["-ip"],
                    {
                        "help": _("intarface ip"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def router_port_add(self):
        oid = self.app.pargs.id
        subnet_id = self.app.pargs.subnet
        ip_address = self.app.pargs.ip

        router = self.client.network.router.get(oid)
        subnet = self.client.network.subnet.get(subnet_id)
        name = f"{router['name']}-{subnet['name']}"

        if subnet_id is not None or ip_address is not None:
            fixed_ips = {"subnet_id": subnet_id, "ip_address": ip_address}
            fixed_ips = [fixed_ips]
            network_id = subnet["network_id"]
            tenant_id = router["tenant_id"]

            port = self.client.network.port.create(name, network_id, fixed_ips, host_id=None, tenant_id=tenant_id)
            interface = self.client.network.router.add_internal_interface(oid, None, port=port["id"])
        else:
            interface = self.client.network.router.add_internal_interface(oid, subnet_id)
        self.app.render({"msg": f"add router {oid} internal port {interface['id']}"})

    @ex(
        help=_("delete openstack router internal interfafe"),
        description=_("delete openstack router internal interfafe"),
        arguments=OPENSTACK_ARGS(
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
        subnet_id = self.app.pargs.subnet

        interface = self.client.network.router.delete_internal_interface(oid, subnet_id)
        self.app.render({"msg": f"delete router {oid} internal port {interface['id']}"})

    @ex(
        help=_("get security_groups"),
        description=_("get security_groups"),
        example="beehive platform openstack security-group-get -id <uuid> --env test",
        arguments=OPENSTACK_ARGS(
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
            ]
        ),
    )
    def security_group_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.network.security_group.get(oid)

            if self.is_output_text():
                rules = res.pop("security_group_rules", [])
                self.app.render(res, details=True)
                self.c("\nrules", "underline")
                self.app.render(
                    rules,
                    headers=[
                        "id",
                        "direction",
                        "ethertype",
                        "remote_group_id",
                        "remote_ip_prefix",
                        "protocol",
                        "port_range_min",
                        "port_range_max",
                        "created_at",
                        "updated_at",
                        "revision_number",
                    ],
                )

                ports = self.client.network.port.list(security_group=oid)
                headers = [
                    "id",
                    "tenant_id",
                    "name",
                    "ip_address",
                    "mac_address",
                    "status",
                    "device_owner",
                    "security_groups",
                ]
                fields = [
                    "id",
                    "tenant_id",
                    "name",
                    "fixed_ips.0.ip_address",
                    "mac_address",
                    "status",
                    "device_owner",
                    "security_groups",
                ]
                self.c("\nports", "underline")
                self.app.render(ports, headers=headers, fields=fields)
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.network.security_group.list(**params)
            headers = ["id", "tenant_id", "name"]
            fields = ["id", "tenant_id", "name"]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("add openstack security group"),
        description=_("add openstack security group"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {"help": _("security_group name"), "action": "store", "type": str},
                ),
                (
                    ["project"],
                    {
                        "help": _("parent project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def security_group_add(self):
        name = self.app.pargs.name
        project = self.app.pargs.project
        self.client.network.security_group.create(name, name, project)
        self.app.render({"msg": f"add security group {name}"})

    @ex(
        help=_("update openstack security group"),
        description=_("update openstack security group"),
        arguments=OPENSTACK_ARGS(
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
                    ["-name"],
                    {
                        "help": _("security_group name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("security_group description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def security_group_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        self.client.network.security_group.update(oid, name, desc)
        self.app.render({"msg": f"update security_group {oid}"})

    @ex(
        help=_("delete openstack security_group"),
        description=_("delete openstack security_group"),
        arguments=OPENSTACK_ARGS(
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
            ]
        ),
    )
    def security_group_del(self):
        oid = self.app.pargs.id
        self.client.network.security_group.delete(oid)
        self.app.render({"msg": f"delete security_group {oid}"})

    @ex(
        help=_("get openstack security group rule"),
        description=_("get openstack security group rule"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
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
    def security_group_rule_get(self):
        oid = self.app.pargs.id
        res = self.client.network.security_group.get_rule(oid)
        self.app.render(res, details=True)

    @ex(
        help=_("add openstack security group rule"),
        description=_("add openstack security group rule"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("security group rule id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-direction"],
                    {
                        "help": _("direction. Can be ingress or egress"),
                        "action": "store",
                        "type": str,
                        "default": "ingress",
                    },
                ),
                (
                    ["-ethertype"],
                    {
                        "help": _("Must be IPv4 or IPv6"),
                        "action": "store",
                        "type": str,
                        "default": "IPv4",
                    },
                ),
                (
                    ["-port_min"],
                    {
                        "help": _("port range min"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port_max"],
                    {
                        "help": _("port range max"),
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
                    ["-remote_ip"],
                    {
                        "help": _("remote ip"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def security_group_rule_add(self):
        oid = self.app.pargs.id
        direction = self.app.pargs.direction
        ethertype = self.app.pargs.ethertype
        port_min = self.app.pargs.port_min
        port_max = self.app.pargs.port_max
        protocol = self.app.pargs.protocol
        remote_ip = self.app.pargs.remote_ip
        self.client.network.security_group.create_rule(
            oid,
            direction,
            ethertype=ethertype,
            port_range_min=port_min,
            port_range_max=port_max,
            protocol=protocol,
            remote_group_id=None,
            remote_ip_prefix=remote_ip,
        )
        self.app.render({"msg": f"create security group rule {oid}"})

    @ex(
        help=_("delete openstack security group rule"),
        description=_("delete openstack security group rule"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("security group rule id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def security_group_rule_del(self):
        oid = self.app.pargs.id
        self.client.network.security_group.delete_rule(oid)
        self.app.render({"msg": f"delete security group rule {oid}"})

    @ex(
        help=_("check openstack security_group"),
        description=_("check openstack security_group"),
        arguments=OPENSTACK_ARGS(
            [
                (["-delete"], {"help": _("security_group id"), "action": "store_true"}),
            ]
        ),
    )
    def security_group_check(self):
        delete = self.app.pargs.delete
        obj = self.client.network.security_group.list()
        sg_index = {i["tenant_id"]: i for i in obj}
        projects = self.client.project.list()
        projects_ids = [i["id"] for i in projects]
        for k, v in sg_index.items():
            if k not in projects_ids:
                print(v["id"], v["name"])
                if delete is True:
                    self.client.network.security_group.delete(v["id"])

    @ex(
        help=_("get images"),
        description=_("get images"),
        arguments=OPENSTACK_ARGS(
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
                    ["-owner"],
                    {"help": _("owner"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-visibility"],
                    {
                        "help": _("image visibility: all, public, private, shared, community"),
                        "action": "store",
                        "type": str,
                        "default": "all",
                    },
                ),
            ]
        ),
    )
    def image_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.image.get(oid)
            block_device_mapping_str = res.get("block_device_mapping", "")
            if block_device_mapping_str != "":
                block_device_mapping = loads(block_device_mapping_str)
                # Inject links from nova image to cinder snapshot
                res["snapshot_ids"] = ",".join([a["snapshot_id"] for a in block_device_mapping])
            self.app.render(res, details=True)
        else:
            glance_version = float(self.client.glance.api()[0]["id"][1:])
            params = {}
            if glance_version > 2.6:
                params = {
                    "visibility": self.app.pargs.visibility,
                }
            owner = self.app.pargs.owner
            if owner is not None:
                params["owner"] = owner
            res = self.client.image.list(**params)
            headers = [
                "id",
                "name",
                "owner",
                "status",
                "disk_format",
                "created_at",
                "min_disk",
                "min_Ram",
                "size",
                "hw_qemu_guest_agent",
                "img_config_drive",
            ]
            fields = [
                "id",
                "name",
                "owner",
                "status",
                "disk_format",
                "created_at",
                "min_disk",
                "min_ram",
                "size",
                "hw_qemu_guest_agent",
                "img_config_drive",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("get image schemas"),
        description=_("get image schemas"),
        arguments=OPENSTACK_ARGS(
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
    def image_schema_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.image.get_schema(oid)
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.image.list_schemas(**params)
            headers = ["name"]
            fields = ["name"]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("add openstack image"),
        description=_("add openstack image"),
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": _("image name"), "action": "store", "type": str}),
                (
                    ["-disk_format"],
                    {
                        "help": _("disk format e.g.: ami, ari, aki, vhd, vhdx, vmdk, raw, qcow2, vdi, ploop, iso"),
                        "action": "store",
                        "type": str,
                        "default": "qcow2",
                    },
                ),
                (
                    ["-min_disk"],
                    {
                        "help": _("amount of disk space in GB that is required to boot the image."),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-min_ram"],
                    {
                        "help": _("amount of RAM in MB that is required to boot the image"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-visibility"],
                    {
                        "help": _("image visibility: public, private, shared, or community"),
                        "action": "store",
                        "type": str,
                        "default": "public",
                    },
                ),
            ]
        ),
    )
    def image_add(self):
        name = self.app.pargs.name
        disk_format = self.app.pargs.disk_format
        min_ram = self.app.pargs.min_ram
        min_disk = self.app.pargs.min_disk
        visibility = self.app.pargs.visibility
        self.client.image.create(
            name,
            disk_format=disk_format,
            min_disk=min_disk,
            min_ram=min_ram,
            visibility=visibility,
        )
        self.app.render({"msg": f"add image {name}"})

    @ex(
        help=_("upload openstack image"),
        description=_("upload openstack image"),
        arguments=OPENSTACK_ARGS(
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
                    ["name"],
                    {
                        "help": _("image file name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def image_upload(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        filename = f"{name}.qcow2"
        with open(filename, "rb") as f:
            data = f.read()

        self.client.image.upload(oid, data)
        self.app.render({"msg": f"upload image {oid}"})

    @ex(
        help=_("download openstack image"),
        description=_("download openstack image"),
        arguments=OPENSTACK_ARGS(
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
                    ["name"],
                    {
                        "help": _("image file name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def image_download(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        data = self.client.image.download(oid)
        with open(f"{name}.qcow2", "wb") as f:
            f.write(data)
        self.app.render({"msg": f"download image {oid}"})

    @ex(
        help=_("delete openstack image"),
        description=_("delete openstack image"),
        arguments=OPENSTACK_ARGS(
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
    def image_del(self):
        oid = self.app.pargs.id
        self.client.image.delete(oid)
        self.app.render({"msg": f"Delete image {oid}"})

    @ex(
        help=_("get image tasks"),
        description=_("get image tasks"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("image task id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def image_task_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.image.get_task(oid)
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.image.list_tasks(**params)
            headers = ["id", "owner", "type", "status", "created_at", "updated_at"]
            fields = ["id", "owner", "type", "status", "created_at", "updated_at"]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("get flavors"),
        description=_("get flavors"),
        example="beehive platform openstack flavor-get -id <uuid> -e <env>",
        arguments=OPENSTACK_ARGS(
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
            res = self.client.flavor.get(oid)
            self.app.render(res, details=True)
        else:
            params = {"detail": True}
            res = self.client.flavor.list(**params)
            for item in res:
                aggregate_instance_extra_specs = self.client.flavor.extra_spec_list(item.get("id"))
                item["aggregato"] = dict_get(
                    aggregate_instance_extra_specs,
                    "aggregate_instance_extra_specs:tipo",
                )
            headers = [
                "id",
                "name",
                "ram",
                "vcpus",
                "swap",
                "is_public",
                "rxtx_factor",
                "disk",
                "ephemeral",
                "disabled",
                "aggregato",
            ]
            fields = [
                "id",
                "name",
                "ram",
                "vcpus",
                "swap",
                "os-flavor-access:is_public",
                "rxtx_factor",
                "disk",
                "OS-FLV-EXT-DATA:ephemeral",
                "OS-FLV-DISABLED:disabled",
                "aggregato",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("add flavor"),
        description=_("add flavor"),
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": _("flavor name"), "action": "store", "type": str}),
                (
                    ["vcpu"],
                    {"help": _("vcpu"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["ram"],
                    {"help": _("ram"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["disk"],
                    {"help": _("disk"), "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def flavor_add(self):
        name = self.app.pargs.name
        vcpu = self.app.pargs.vcpu
        ram = self.app.pargs.ram
        disk = self.app.pargs.disk
        self.client.flavor.create(name, vcpu, ram, disk, desc=None)
        self.app.render({"msg": f"add flavor {name}"})

    @ex(
        help=_("update openstack flavor"),
        description=_("update openstack flavor"),
        arguments=OPENSTACK_ARGS(
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
                    ["-name"],
                    {
                        "help": _("flavor name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("flavor description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def flavor_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        self.client.flavor.update(oid, name, desc)
        self.app.render({"msg": f"update flavor {oid}"})

    @ex(
        help=_("delete openstack flavor"),
        description=_("delete openstack flavor"),
        arguments=OPENSTACK_ARGS(
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
            ]
        ),
    )
    def flavor_del(self):
        oid = self.app.pargs.id
        self.client.flavor.delete(oid)
        self.app.render({"msg": f"Delete flavor {oid}"})

    @ex(
        help=_("get flavor extra specs"),
        description=_("get flavor extra specs"),
        arguments=OPENSTACK_ARGS(
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
                    ["-spec"],
                    {
                        "help": _("flavor extra spec key"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def flavor_extra_spec_get(self):
        oid = self.app.pargs.id
        spec = self.app.pargs.spec
        if spec is not None:
            res = self.client.flavor.extra_spec_get(oid, spec)
            self.app.render(res, details=True)
        else:
            res = self.client.flavor.extra_spec_list(oid)
            self.app.render(res, details=True)

    @ex(
        help=_("add flavor extra spec"),
        description=_("add flavor"),
        arguments=OPENSTACK_ARGS(
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
                    ["spec"],
                    {
                        "help": _("flavor extra spec keys. Syntax k1:v1,k2:v2"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def flavor_extra_spec_add(self):
        oid = self.app.pargs.id
        spec_str = self.app.pargs.spec
        spec = {}
        for item in spec_str.split(","):
            k = item.split(":")
            spec[k[0]] = k[1]
        self.client.flavor.extra_spec_create(oid, spec)
        self.app.render({"msg": f"add flavor {oid} extra spec {spec_str}"})

    @ex(
        help=_("update openstack flavor"),
        description=_("update openstack flavor"),
        arguments=OPENSTACK_ARGS(
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
                    ["spec"],
                    {
                        "help": _("flavor extra spec key. Syntax k1:v1"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["spec_value"],
                    {
                        "help": _("flavor extra spec key"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def flavor_extra_spec_update(self):
        oid = self.app.pargs.id
        spec = self.app.pargs.spec
        spec_value = self.app.pargs.spec_value
        self.client.flavor.extra_spec_update(oid, spec, spec_value)
        self.app.render({"msg": f"update flavor {oid} extra spec {spec}"})

    @ex(
        help=_("delete openstack flavor"),
        description=_("delete openstack flavor"),
        arguments=OPENSTACK_ARGS(
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
                    ["spec"],
                    {
                        "help": _("flavor extra spec key"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def flavor_extra_spec_del(self):
        oid = self.app.pargs.id
        spec = self.app.pargs.spec
        self.client.flavor.extra_spec_delete(oid, spec)
        self.app.render({"msg": f"Delete flavor {oid} extra spec {spec}"})

    @ex(
        help=_("get aggregates"),
        description=_("get aggregates"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("aggregate id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def aggregate_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.aggregate.get(oid)
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.aggregate.list(**params)
            headers = [
                "id",
                "uuid",
                "name",
                "availability_zone",
                "hosts",
                "metadata",
                "created_at",
                "updated_at",
                "deleted_at",
            ]
            fields = [
                "id",
                "uuid",
                "name",
                "availability_zone",
                "hosts",
                "metadata",
                "created_at",
                "updated_at",
                "deleted_at",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("add aggregate"),
        description=_("add aggregate"),
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": _("aggregate name"), "action": "store", "type": str}),
                (
                    ["availability_zone"],
                    {
                        "help": _("availability zone"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def aggregate_add(self):
        name = self.app.pargs.name
        availability_zone = self.app.pargs.availability_zone
        self.client.aggregate.create(name, availability_zone)
        self.app.render({"msg": f"add aggregate {name}"})

    @ex(
        help=_("update openstack aggregate"),
        description=_("update openstack aggregate"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("aggregate id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("aggregate name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-availability_zone"],
                    {
                        "help": _("aggregate availability zone"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def aggregate_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        availability_zone = self.app.pargs.availability_zone
        self.client.aggregate.update(oid, name=name, availability_zone=availability_zone)
        self.app.render({"msg": f"update aggregate {oid}"})

    @ex(
        help=_("delete openstack aggregate"),
        description=_("delete openstack aggregate"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("aggregate id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def aggregate_del(self):
        oid = self.app.pargs.id
        self.client.aggregate.delete(oid)
        self.app.render({"msg": f"Delete aggregate {oid}"})

    @ex(
        help=_("add host to openstack aggregate"),
        description=_("add host to openstack aggregate"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("aggregate id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["host"],
                    {
                        "help": _("host_id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def aggregate_host_add(self):
        oid = self.app.pargs.id
        host = self.app.pargs.host
        self.client.aggregate.add_host(oid, host)
        self.app.render({"msg": f"update aggregate {oid}"})

    @ex(
        help=_("delete host from openstack aggregate"),
        description=_("delete host from openstack aggregate"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("aggregate id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["host"],
                    {
                        "help": _("host_id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def aggregate_host_del(self):
        oid = self.app.pargs.id
        host = self.app.pargs.host
        self.client.aggregate.del_host(oid, host)
        self.app.render({"msg": f"update aggregate {oid}"})

    @ex(
        help=_("update metadata to openstack aggregate"),
        description=_("update metadata  to openstack aggregate"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("aggregate id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["metadata"],
                    {
                        "help": _("key:value,key:value"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def aggregate_metadat_update(self):
        oid = self.app.pargs.id
        metadata_str = self.app.pargs.metadata
        metadata = {}
        for item in metadata_str.split(","):
            k = item.split(":")
            metadata[k[0]] = k[1]
        self.client.aggregate.update_metatdata(oid, metadata)
        self.app.render({"msg": f"update aggregate {oid} metadata"})

    @ex(
        help=_("get keypairs"),
        description=_("get keypairs"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("keypair id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def keypair_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.keypair.get(oid)
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.keypair.list(**params)
            headers = ["name", "public_key", "fingerprint"]
            fields = ["name", "public_key", "fingerprint"]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("delete openstack keypair"),
        description=_("delete openstack keypair"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("keypair id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def keypair_del(self):
        oid = self.app.pargs.id
        self.client.keypair.delete(oid)
        self.app.render({"msg": f"Delete keypair {oid}"})

    @ex(
        help=_("get server groups"),
        description=_("get server groups"),
        example="beehive platform openstack server-group-get -e <env>",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("server group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": _("number of item to return"),
                        "action": "store",
                        "type": int,
                        "default": 20,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": _("page to return"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
            ]
        ),
    )
    def server_group_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.server_group.get(oid)
            self.app.render(res, details=True)
        else:
            limit = self.app.pargs.size
            page = self.app.pargs.page
            offset = page * limit
            res = self.client.server_group.list(limit=limit, offset=offset)
            for item in res:
                item["members"] = ",".join(item["members"])
                item["policies2"] = ",".join(item["policies"])
            resp = {
                "server_groups": res,
                "page": page,
                "count": len(res),
                "total": "",
                "sort": {"field": "", "order": ""},
            }
            headers = ["id", "name", "policies", "members"]
            fields = ["id", "name", "policies2", "members"]
            self.app.render(resp, key="server_groups", headers=headers, fields=fields, maxsize=200)

    @ex(
        help=_("add openstack server group"),
        description=_("add openstack server group"),
        example=(
            "beehive platform openstack server-group-add Csi.LavoroFormazioneProfessionale.pangea-preprod.wf-appl "
            "-p soft-affinity -e <env>; "
        ),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {"help": _("server group name"), "action": "store", "type": str},
                ),
                (
                    ["-policy"],
                    {
                        "help": _(
                            "one policy name to associate with the server group. Policy names are:"
                            ' "anti-affinity" servers in this group must be scheduled to different hosts,'
                            ' "affinity" servers in this group must be scheduled to the same host, '
                            ' "soft-anti-affinity" servers in this group should be scheduled to different '
                            "hosts if possible, but if not possible then they should still be scheduled instead "
                            'of resulting in a build failure, "soft-affinity" servers in this group should be '
                            "scheduled to the same host if possible, but if not possible then they should still "
                            "be scheduled instead of resulting in a build failure"
                        ),
                        "action": "store",
                        "type": str,
                        "default": "soft-anti-affinity",
                    },
                ),
            ]
        ),
    )
    def server_group_add(self):
        name = self.app.pargs.name
        policy = self.app.pargs.policy
        if policy not in [
            "anti-affinity",
            "affinity",
            "soft-anti-affinity",
            "soft-affinity",
        ]:
            raise Exception(
                "only anti-affinity, affinity, soft-anti-affinity and soft-affinity are supported as " "policy"
            )
        self.client.server_group.create(name, policies=[policy])
        self.app.render({"msg": f"add server group {name}"})

    @ex(
        help=_("delete openstack server group"),
        description=_("delete openstack server group"),
        example="beehive platform openstack server-group-del <uuid>",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_group_del(self):
        oid = self.app.pargs.id
        self.client.server_group.delete(oid)
        self.app.render({"msg": f"Delete server group {oid}"})

    @ex(
        help=_("add openstack server group member"),
        description=_("add openstack server group member"),
        example="beehive platform openstack server-group-member-add <uuid> <uuid> -e <env>",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["server"],
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
    def server_group_member_add(self):
        oid = self.app.pargs.id
        server_id = self.app.pargs.server

        # check server and server group exist
        sg = self.client.server_group.get(oid)
        self.client.server.get(server_id)
        if server_id in sg.get("members", []):
            raise Exception(f"server {server_id} already in server group {oid}")

        date = format_date(datetime.now(), format="%Y-%m-%d %H:%M:%S")

        hosts = self.mariadb.get("hosts", [])
        port = self.mariadb.get("port")
        user = {"name": self.mariadb.get("user"), "password": self.mariadb.get("pwd")}
        db = "nova_api"

        def statements(conn):
            result = conn.execute(f"SELECT * from nova_api.instance_groups WHERE uuid='{oid}';")
            group = result.fetchall()
            if len(group) == 1:
                group_id = group[0][2]
                conn.execute(
                    "INSERT INTO `instance_group_member`(created_at, instance_uuid, group_id) "
                    f"values ('{date}', '{server_id}', '{group_id}');"
                )
            return True

        server = self.__get_mariadb_engine(hosts[0], port, user, db)
        server.exec_statements(statements)
        self.app.render({"msg": f"add server {server_id} in server group {oid}"})

    @ex(
        help=_("delete openstack server group member"),
        description=_("delete openstack server group member"),
        example="beehive platform openstack server-group-member-del <uuid> <uuid> -e <env>",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("server group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["server"],
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
    def server_group_member_del(self):
        oid = self.app.pargs.id
        server_id = self.app.pargs.server

        # check server and server group exist
        sg = self.client.server_group.get(oid)
        self.client.server.get(server_id)
        if server_id not in sg.get("members", []):
            raise Exception(f"server {server_id} not in server group {oid}")

        hosts = self.mariadb.get("hosts", [])
        port = self.mariadb.get("port")
        user = {"name": self.mariadb.get("user"), "password": self.mariadb.get("pwd")}
        db = "nova_api"

        def statements(conn):
            result = conn.execute(f"SELECT * from nova_api.instance_groups WHERE uuid='{oid}';")
            group = result.fetchall()
            if len(group) == 1:
                #group_id = group[0][2]
                conn.execute(f"DELETE FROM nova_api.instance_group_member WHERE instance_uuid='{server_id}';")
            return True

        server = self.__get_mariadb_engine(hosts[0], port, user, db)
        server.exec_statements(statements)
        self.app.render({"msg": f"delete server {server_id} from server group {oid}"})

    @ex(
        help=_("get servers"),
        description=_("get servers"),
        example="beehive platform openstack server-get -id <uuid> -e <env>",
        arguments=OPENSTACK_ARGS(
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
                    ["-host"],
                    {
                        "help": _("compute node name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": _("server status"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-power_state"],
                    {
                        "help": _("server power stage"),
                        "action": "store",
                        "choices": ["NOSTATE", "RUNNING", "PAUSED", "SHUTDOWN", "CRASHED", "SUSPENDED"],
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-updated_at"],
                    {
                        "help": _(
                            "Filter the server list result by a date and time stamp when the instance was "
                            "updated. The date and timestamp format is ISO 8601: "
                            "CCYY-MM-DDThh:mm:ss±hh:mm. For example, 2015-08-27T09:49:58-05:00"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ip"],
                    {"help": _("Filter by ip address"), "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def server_get(self):
        oid = getattr(self.app.pargs, "id", None)
        client = self.client
        server = client.server
        all_tenants = True
        if oid is not None:
            res = server.get(oid)
            if self.is_output_text():
                server_volumes = res.pop("os-extended-volumes:volumes_attached")
                res["flavor"]["name"] = client.flavor.get(res["flavor"]["id"]).get("name")
                self.app.render(res, details=True)
                # get volumes
                volume_v3 = client.volume_v3
                volumes = [volume_v3.get(v["id"]) for v in server_volumes]
                headers = [
                    "id",
                    "name",
                    "os-vol-tenant-attr:tenant_id",
                    "size",
                    "status",
                    "type",
                    "bootable",
                ]
                fields = [
                    "id",
                    "name",
                    "os-vol-tenant-attr:tenant_id",
                    "size",
                    "status",
                    "volume_type",
                    "bootable",
                ]
                self.c("\nvolumes", "underline")
                self.app.render(volumes, headers=headers, fields=fields, maxsize=200)
            else:
                self.app.render(res, details=True)
        else:
            prjid_to_desc = {p["id"]: p.get("description") for p in client.project.list()}
            pargs = self.app.pargs
            if pargs.project is not None:
                all_tenants = False
                self.app.warning("Some filters may not be available when filtering by project")

            res = server.list(
                detail=True,
                host=pargs.host,
                status=pargs.status,
                updated_at=pargs.updated_at,
                all_tenants=all_tenants,
                ip=self.app.pargs.ip,
                power_state=self.app.pargs.power_state,
            )
            for i in res:
                i["addr"] = ",".join(a[0].get("addr") for a in i.get("addresses", []).values() if len(a) > 0)
                i["tenant_name"] = prjid_to_desc.get(i["tenant_id"])
            headers = [
                "id",
                "tenant",
                "name",
                "instance_name",
                "status",
                "power_state",
                "host",
                "addr",
                "updated",
            ]
            fields = [
                "id",
                "tenant_name",
                "name",
                "OS-EXT-SRV-ATTR:instance_name",
                "status",
                "OS-EXT-STS:power_state",
                "OS-EXT-SRV-ATTR:host",
                "addr",
                "updated",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("print host status"),
        description=_("print host status"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-host"],
                    {
                        "help": _("node name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-loop"],
                    {
                        "help": _("if value > 1 enable query loop"),
                        "action": "store",
                        "type": int,
                        "default": 1,
                    },
                ),
            ]
        ),
    )
    def host_status(self):
        res = self.client.system.compute_hypervisors()
        filter_host = self.app.pargs.host
        loop = self.app.pargs.loop
        for host_info in res:
            host = host_info.get("hypervisor_hostname")
            if filter_host is not None and host != filter_host:
                continue

            for i in range(loop):
                res = self.client.server.list(detail=True, host=host)
                resp = {
                    "active": 0,
                    "shutoff": 0,
                    "error": 0,
                    "no-state": 0,
                    "rebuild": 0,
                }
                for i in res:
                    status = i["status"]
                    if status == "ACTIVE":
                        resp["active"] += 1
                    elif status == "SHUTOFF":
                        resp["shutoff"] += 1
                    elif status == "ERROR":
                        resp["error"] += 1
                    elif status == "REBUILD":
                        resp["rebuild"] += 1
                    elif i["OS-EXT-STS:power_state"] == 0:
                        resp["no-state"] += 1
                print(f"host: {host}, server: {resp}")
                if loop > 1:
                    sleep(5)

    @ex(
        help=_("start servers for a host"),
        description=_("start servers for a host"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-host"],
                    {
                        "help": _("node name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_smart_start(self):
        host = self.app.pargs.host
        res = self.client.server.list(detail=True, host=host)
        for i in res:
            status = i["status"]
            # if status == 'REBUILD':
            #     print('server %s REBUILD' % i['id'])
            if status == "SHUTOFF":
                self.client.server.start(i["id"])
                print(f"start server {i['id']}")
                sleep(2)
            elif status == "ERROR":
                self.client.server.reset_state(i["id"], "error")
                print(f"reset state server {i['id']}")
                self.client.server.reboot(i["id"])
                print(f"hard reboot server {i['id']}")
                sleep(2)
            elif status == "REBUILD":
                self.client.server.reset_state(i["id"], "error")
                print(f"reset state server {i['id']}")
                self.client.server.reboot(i["id"])
                print(f"hard reboot server {i['id']}")
                sleep(2)
            elif i["OS-EXT-STS:power_state"] in [0, 3]:
                self.client.server.reset_state(i["id"], "error")
                print(f"reset state server {i['id']}")
                self.client.server.reboot(i["id"])
                print(f"hard reboot server {i['id']}")
                sleep(2)
            elif status == "ACTIVE":
                print(f"server {i['id']} OK")

    @ex(
        help=_("reset servers state for a host"),
        description=_("reset servers state for a host"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-host"],
                    {
                        "help": _("node name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_smart_reset_status(self):
        ## aggiornare il comando per lanciare tutte le vm con gli host in parallelo facendo precedere i dbs
        ##
        host = self.app.pargs.host
        res = self.client.server.list(detail=True, host=host)
        for i in res:
            if i["id"] in []:
                continue
            status = i["status"]
            if status == "ERROR":
                self.client.server.reset_state(i["id"], "active")
                print(f"hard reboot server {i['id']}")
            # if status == 'SHUTOFF':
            #     self.client.server.start(i['id'])
            #     print('start server %s' % i['id'])
            sleep(2)

    @ex(
        help=_("ping servers for a host"),
        description=_("ping servers for a host"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-host"],
                    {
                        "help": _("node name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("vm name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_smart_ping(self):
        host = self.app.pargs.host
        #name = self.app.pargs.name
        res = self.client.server.list(detail=True, host=host)
        for i in res:
            addr = list(i.get("addresses").values())
            if len(addr) > 0:
                addr = addr[0]
            if len(addr) > 0:
                addr = addr[0]
            if isinstance(addr, dict):
                addr = addr["addr"]
            i["addr"] = addr

            print(f"ping -c 3 {addr}")

    @ex(
        help=_("add openstack server"),
        description=_("add openstack server"),
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": _("server name"), "action": "store", "type": str}),
                (
                    ["-flavor"],
                    {
                        "help": _("flavor reference id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-boot_volume"],
                    {
                        "help": _("boot volume id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-admin_pass"],
                    {
                        "help": _("admin password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-description"],
                    {
                        "help": _("description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-security_groups"],
                    {
                        "help": _("security groups"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-networks"],
                    {
                        "help": _("list of networks"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-config_drive"],
                    {
                        "help": _("list of networks"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-availability_zone"],
                    {
                        "help": _("availability zone"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-image"],
                    {
                        "help": _("The UUID of the image to use for your server instance."),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_add(self):
        params = {}
        name = self.app.pargs.name
        name = self.app.pargs.name
        flavor = self.app.pargs.flavor
        params = self.add_field_from_pargs_to_data("boot_volume", params, "boot_volume")
        params = self.add_field_from_pargs_to_data("admin_pass", params, "adminpass")
        params = self.add_field_from_pargs_to_data("description", params, "description")
        params = self.add_field_from_pargs_to_data("availability_zone", params, "availability_zone")
        params = self.add_field_from_pargs_to_data("image", params, "image")
        params["config_drive"] = str2bool(self.app.pargs.config_drive)
        security_groups = self.app.pargs.security_groups
        if security_groups is not None:
            params["security_groups"] = self.app.pargs.security_groups.split(",")
        networks = self.app.pargs.networks
        if networks is not None:
            params["networks"] = [
                {"uuid": a, "tag": f"nic{e}"} for e, a in enumerate(self.app.pargs.networks.split(","))
            ]
        res = self.client.server.create(name, flavor, **params)
        self.app.render({"msg": f"add server {name} with id {res['id']}"})

    @ex(
        help=_("update openstack server"),
        description=_("update openstack server"),
        arguments=OPENSTACK_ARGS(
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
                    ["-name"],
                    {
                        "help": _("server name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("server description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_update(self):
        params = {}
        oid = self.app.pargs.id
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        self.client.server.update(oid, name, desc, **params)
        self.app.render({"msg": f"update server {oid}"})

    @ex(
        help=_("rebuild openstack server"),
        description=_("rebuild openstack server"),
        arguments=OPENSTACK_ARGS(
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
                    ["-image"],
                    {
                        "help": _("The UUID of the image to use for your server instance."),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_rebuild(self):
        params = {}
        oid = self.app.pargs.id
        params = self.add_field_from_pargs_to_data("image", params, "image")
        self.client.server.rebuild(oid, **params)
        self.app.render({"msg": f"update server {oid}"})

    @ex(
        help=_("delete openstack server"),
        description=_("delete openstack server"),
        arguments=OPENSTACK_ARGS(
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
        self.client.server.delete(oid)
        self.app.render({"msg": f"Delete server {oid}"})

    @ex(
        help=_("get openstack server diagnostics"),
        description=_("get openstack server diagnostics"),
        arguments=OPENSTACK_ARGS(
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
    def server_diagnostics(self):
        oid = self.app.pargs.id
        obj = self.client.server.diagnostics(oid)
        res = obj
        self.app.render(res, details=True)

    @ex(
        help=_("get openstack server console"),
        description=_("get openstack server console"),
        arguments=OPENSTACK_ARGS(
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
        res = self.client.server.get_vnc_console(oid)
        self.app.render([res], headers=["type", "url"], maxsize=400)

    @ex(
        help=_("get openstack server console output"),
        description=_("get openstack server console output"),
        arguments=OPENSTACK_ARGS(
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
    def server_console_output(self):
        oid = self.app.pargs.id
        res = self.client.server.get_console_output(oid)
        print(res)

    @ex(
        help=_("get openstack server ports"),
        description=_("get openstack server ports"),
        arguments=OPENSTACK_ARGS(
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
    def server_port_get(self):
        oid = self.app.pargs.id
        res = self.client.server.get_port_interfaces(oid)
        headers = ["name", "state", "port_id", "net_id", "ip_address"]
        fields = ["name", "port_state", "port_id", "net_id", "fixed_ips.0.ip_address"]
        self.app.render(res, headers=headers, fields=fields, maxsize=80)

    @ex(
        help=_("add openstack server port"),
        description=_("add openstack server port"),
        arguments=OPENSTACK_ARGS(
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
                    ["-port"],
                    {
                        "help": _("port id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-net"],
                    {
                        "help": _("network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ipaddress"],
                    {
                        "help": _("ip address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subnet"],
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
    def server_port_add(self):
        oid = self.app.pargs.id
        port_id = self.app.pargs.port
        net_id = self.app.pargs.net
        ip_address = self.app.pargs.ipaddress
        subnet_id = self.app.pargs.subnet
        fixed_ips = None
        if ip_address is not None and subnet_id is not None:
            fixed_ips = [[{"ip_address": ip_address, "subnet_id": subnet_id}]]
        self.client.server.add_port_interfaces(oid, port_id=port_id, net_id=net_id, fixed_ips=fixed_ips)
        msg = f"Add network interface to server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("delete openstack server port"),
        description=_("delete openstack server port"),
        arguments=OPENSTACK_ARGS(
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
                    ["port"],
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
    def server_port_del(self):
        oid = self.app.pargs.id
        port_id = self.app.pargs.port
        self.client.server.remove_port_interfaces(oid, port_id)
        msg = f"Delete port {port_id} from server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("get openstack server security group"),
        description=_("get openstack server security group"),
        arguments=OPENSTACK_ARGS(
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
        res = self.client.server.security_groups(oid)
        headers = ["id", "project", "name", "desc"]
        fields = ["id", "tenant_id", "name", "description"]
        self.app.render(res, headers=headers, fields=fields, maxsize=80)

    @ex(
        help=_("add openstack server security group"),
        description=_("add openstack server security group"),
        arguments=OPENSTACK_ARGS(
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
        self.client.server.add_security_group(oid, security_group)
        msg = f"Add security group {security_group} to server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("delete openstack server security group"),
        description=_("delete openstack server security group"),
        arguments=OPENSTACK_ARGS(
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
        self.client.server.remove_security_group(oid, security_group)
        msg = f"Delete security group {security_group} from server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("get openstack server volumes"),
        description=_("get openstack server volumes"),
        arguments=OPENSTACK_ARGS(
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
    def server_volume_get(self):
        oid = self.app.pargs.id
        res = self.client.server.get_volumes(oid)
        headers = ["id", "server-id", "device"]
        fields = ["volumeId", "serverId", "device"]
        self.app.render(res, headers=headers, fields=fields, maxsize=80)

    @ex(
        help=_("add openstack server volume"),
        description=_("add openstack server volume"),
        arguments=OPENSTACK_ARGS(
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
                    ["volume_id"],
                    {
                        "help": _("volume id (see volume-add to create it.)"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_volume_add(self):
        oid = self.app.pargs.server_id
        volume = self.app.pargs.volume_id
        self.client.server.add_volume(oid, volume)
        msg = f"Add volume {volume} to server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("delete openstack server volume"),
        description=_("delete openstack server volume"),
        arguments=OPENSTACK_ARGS(
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
        self.client.server.remove_volume(oid, volume)
        msg = f"Delete volume {volume} from server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("get openstack server metadata"),
        description=_("get openstack server metadata"),
        arguments=OPENSTACK_ARGS(
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
    def server_metadata_get(self):
        oid = self.app.pargs.id
        res = self.client.server.get_metadata(oid)
        res = [{"key": k, "value": v} for k, v in res.items()]
        headers = ["key", "value"]
        fields = ["key", "value"]
        self.app.render(res, headers=headers, fields=fields, maxsize=80)

    @ex(
        help=_("add openstack server metadata"),
        description=_("add openstack server metadata"),
        arguments=OPENSTACK_ARGS(
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
    def server_metadata_add(self):
        oid = self.app.pargs.id
        metadata = self.app.pargs.metadata
        if metadata.find("@") == 0:
            metadata = load_config(metadata.lstrip("@"))
            metadata = loads(metadata)
        else:
            metadata = metadata.split(":")
            metadata = {metadata[0]: metadata[1]}
        self.client.server.add_metadata(oid, metadata)
        msg = f"Add metadata {metadata} to server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("delete openstack server metadata"),
        description=_("delete openstack server metadata"),
        arguments=OPENSTACK_ARGS(
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
                    ["key_name"],
                    {
                        "help": _("key name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_metadata_del(self):
        oid = self.app.pargs.id
        key = self.app.pargs.key_name
        self.client.server.remove_metadata(oid, key)
        msg = f"Delete metadata {key} from server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("get server actions"),
        description=_("get server actions"),
        arguments=OPENSTACK_ARGS(
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
                    ["-action"],
                    {
                        "help": _("action id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_action_get(self):
        oid = getattr(self.app.pargs, "id", None)
        action = getattr(self.app.pargs, "action", None)
        if action is not None:
            res = self.client.server.get_actions(oid, action_id=action)
            self.app.render(res, details=True)
        else:
            res = self.client.server.get_actions(oid)
            headers = [
                "action-id",
                "action",
                "user-id",
                "project-id",
                "instance-id",
                "start-time",
                "message",
            ]
            fields = [
                "request_id",
                "action",
                "user_id",
                "project_id",
                "instance_uuid",
                "start_time",
                "message",
            ]
            self.app.render(res, headers=headers, fields=fields)

    def __get_server_info(self, oid):
        server = self.client.server.get(oid)
        return server

    def __wait_for_server_status(self, oid, func=None):
        status = None
        required_status = ["ACTIVE", "SHUTOFF", "ERROR"]
        rot_bar = rotating_bar()
        while status not in required_status:
            server = self.__get_server_info(oid)
            status = server.get("status")
            if func is not None:
                func(server)
            else:
                stdout.write(next(rot_bar))
                stdout.flush()
            sleep(1)
        stoprotation()

    @ex(
        help=_("start server"),
        description=_("start server"),
        arguments=OPENSTACK_ARGS(
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
        self.client.server.start(oid)
        msg = f"Start server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("stop server"),
        description=_("stop server"),
        arguments=OPENSTACK_ARGS(
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
        self.client.server.stop(oid)
        msg = f"Stop server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("reboot server"),
        description=_("reboot server"),
        arguments=OPENSTACK_ARGS(
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
    def server_reboot(self):
        oid = self.app.pargs.id
        self.client.server.reset_state(oid, "active")
        self.client.server.reboot(oid)
        msg = f"Reboot server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("pause server"),
        description=_("pause server"),
        arguments=OPENSTACK_ARGS(
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
    def server_pause(self):
        oid = self.app.pargs.id
        self.client.server.pause(oid)
        msg = f"Pause server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("unpause server"),
        description=_("unpause server"),
        arguments=OPENSTACK_ARGS(
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
    def server_unpause(self):
        oid = self.app.pargs.id
        self.client.server.unpause(oid)
        msg = f"Unpause server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("lock server"),
        description=_("lock server"),
        arguments=OPENSTACK_ARGS(
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
    def server_lock(self):
        oid = self.app.pargs.id
        self.client.server.lock(oid)
        msg = f"Lock server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("unlock server"),
        description=_("unlock server"),
        arguments=OPENSTACK_ARGS(
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
    def server_unlock(self):
        oid = self.app.pargs.id
        self.client.server.unlock(oid)
        msg = f"Unlock server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("suspend server"),
        description=_("suspend server"),
        arguments=OPENSTACK_ARGS(
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
    def server_suspend(self):
        oid = self.app.pargs.id
        self.client.server.suspend(oid)
        msg = f"Suspend server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("resume server"),
        description=_("resume server"),
        arguments=OPENSTACK_ARGS(
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
    def server_resume(self):
        oid = self.app.pargs.id
        self.client.server.resume(oid)
        msg = f"Resume server {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("reset server state"),
        description=_("reset server state"),
        arguments=OPENSTACK_ARGS(
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
                    ["state"],
                    {
                        "help": _("server state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_reset_state(self):
        oid = self.app.pargs.id
        state = self.app.pargs.state
        self.client.server.reset_state(oid, state)
        msg = f"Reset state for server {oid} to {state}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("set server flavor"),
        description=_("set server flavor"),
        arguments=OPENSTACK_ARGS(
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
        self.client.server.set_flavor(oid, flavor)
        msg = f"Resize server {oid} using flavor {flavor}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("server migration list"),
        description=_("server migration list"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
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
    def server_migration_list(self):
        oid = self.app.pargs.id
        res = self.client.server.list_migration(oid=oid)
        self.app.render(
            res,
            headers=[
                "id",
                "uuid",
                "instance_uuid",
                "source_node",
                "dest_node",
                "status",
                "created_at",
                "updated_at",
            ],
        )

    @ex(
        help=_("force server migration"),
        description=_("force server migration"),
        arguments=OPENSTACK_ARGS(
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
                    ["migration_id"],
                    {
                        "help": _("server migration id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_migration_force(self):
        oid = self.app.pargs.id
        migration_id = self.app.pargs.migration_id
        self.client.server.force_migration(oid, migration_id)
        self.app.render({"msg": f"force server {oid} migration {migration_id}"})

    @ex(
        help=_("abort server migration"),
        description=_("abort server migration"),
        arguments=OPENSTACK_ARGS(
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
                    ["migration_id"],
                    {
                        "help": _("server migration id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_migration_del(self):
        oid = self.app.pargs.id
        migration_id = self.app.pargs.migration_id
        self.client.server.abort_migration(oid, migration_id)
        self.app.render({"msg": f"abort server {oid} migration {migration_id}"})

    @ex(
        help=_("migrate server"),
        description=_("migrate server"),
        arguments=OPENSTACK_ARGS(
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
                    ["-host"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-live"],
                    {
                        "help": _("if true enable live migration"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
    )
    def server_migrate(self):
        oid = self.app.pargs.id
        host = self.app.pargs.host
        live = str2bool(self.app.pargs.live)
        if live is False:
            self.client.server.migrate(oid, host)
        else:
            self.client.server.live_migrate(oid, host)

        def print_host(server):
            print(server.get("OS-EXT-SRV-ATTR:host"))

        self.__wait_for_server_status(oid, print_host)
        self.app.render({"msg": f"Migrate server {oid}"})

    @ex(
        help=_("create image from a server"),
        description=_("server create image"),
        arguments=OPENSTACK_ARGS(
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
                        "help": _("image name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def server_create_image(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        res = self.client.server.create_image(oid, name)
        self.app.render({"msg": f"Creating image {res['image_id']} from server {oid}"})

    @ex(
        help=_("migrate servers"),
        description=_("migrate servers"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["from_host"],
                    {
                        "help": _("starting host"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-to_host"],
                    {
                        "help": _("destination host"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-live"],
                    {
                        "help": _("if true enable live migration"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
    )
    def servers_migrate(self):
        from_host = self.app.pargs.from_host
        to_host = self.app.pargs.to_host
        live = str2bool(self.app.pargs.live)
        servers = self.client.server.list(detail=False, host=from_host)
        for s in servers:
            oid = s["id"]

            if live is False:
                self.client.server.migrate(oid, to_host)
            else:
                self.client.server.live_migrate(oid, to_host)

            def print_host(server):
                print(server.get("OS-EXT-SRV-ATTR:host"))

            self.__wait_for_server_status(oid, print_host)
            self.app.render({"msg": f"Migrate server {oid}"})

    def __get_stack(self, oid):
        obj = self.client.heat.stack.list(oid=oid)
        if len(obj) <= 0:
            raise Exception(f"Stack {oid} not found")
        obj = obj[0]
        return obj

    @ex(
        help=_("get stacks"),
        description=_("get stacks"),
        arguments=OPENSTACK_ARGS(
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
            stack = self.client.heat.stack.list(oid=oid)
            if len(stack) == 0:
                raise Exception(f"Stack {oid} was not found")
            stack = stack[0]
            res = self.client.heat.stack.get(stack["stack_name"], oid)

            if self.is_output_text():
                parameters = [{"parameter": item, "value": val} for item, val in res.pop("parameters").items()]
                outputs = res.pop("outputs", [])
                self.app.render(res, details=True)

                self.c("\nparameters", "underline")
                self.app.render(parameters, headers=["parameter", "value"], maxsize=800)
                self.c("\noutputs", "underline")
                self.app.render(
                    outputs,
                    headers=["key", "value", "desc", "error"],
                    fields=[
                        "output_key",
                        "output_value",
                        "description",
                        "output_error",
                    ],
                    maxsize=50,
                )

            else:
                self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.heat.stack.list(**params)
            headers = [
                "id",
                "project",
                "stack_name",
                "stack_owner",
                "stack_status",
                "creation_time",
            ]
            fields = [
                "id",
                "project",
                "stack_name",
                "stack_owner",
                "stack_status",
                "creation_time",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("add openstack stack"),
        description=_("add openstack stack"),
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": _("stack name"), "action": "store", "type": str}),
                (
                    ["project"],
                    {
                        "help": _("parent project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["physical_stack"],
                    {
                        "help": _("physical stack"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def stack_add(self):
        name = self.app.pargs.name
        tenant_id = self.app.pargs.tenant
        physical_stack = self.app.pargs.physical_stack
        # segmentation_id = self.app.pargs.segmentation_id
        self.client.heat.stack.create(name, tenant_id, physical_stack)  # , segmentation_id=segmentation_id)
        self.app.render({"msg": f"add stack {name}"})

    @ex(
        help=_("update openstack stack"),
        description=_("update openstack stack"),
        arguments=OPENSTACK_ARGS(
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
                    ["-name"],
                    {
                        "help": _("stack name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("stack description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def stack_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        self.client.heat.stack.update(oid, name, desc)
        self.app.render({"msg": f"update stack {oid}"})

    @ex(
        help=_("delete openstack stack"),
        description=_("delete openstack stack"),
        arguments=OPENSTACK_ARGS(
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
    def stack_del(self):
        oid = self.app.pargs.id
        obj = self.__get_stack(oid)
        self.client.heat.stack.delete(obj["stack_name"], oid)
        # self.wait_stack_delete(obj['stack_name'], oid)
        res = {"msg": f"Delete stack {oid}"}
        self.app.render(res, headers=["msg"])

    @ex(
        help=_("get heat stack resources"),
        description=_("get heat stack resources"),
        arguments=OPENSTACK_ARGS(
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
                    ["-resource"],
                    {
                        "help": _("stack resource name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def stack_resource_get(self):
        oid = self.app.pargs.id
        resource = self.app.pargs.resource
        stack = self.__get_stack(oid)
        res = self.client.heat.stack.resource.list(stack_name=stack["stack_name"], oid=oid, name=resource)
        if resource is None:
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
        else:
            self.app.render(res[0], details=True, maxsize=200)

    @ex(
        help=_("mark the specified resource in the stack as unhealthy"),
        description=_("mark the specified resource in the stack as unhealthy"),
        arguments=OPENSTACK_ARGS(
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
                    ["-resource"],
                    {
                        "help": _("stack resource name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def stack_resource_patch(self):
        oid = self.app.pargs.id
        resource = self.app.pargs.resource
        stack = self.__get_stack(oid)
        res = self.client.heat.stack.resource.patch(stack_name=stack["stack_name"], oid=oid, name=resource)
        res = {"msg": f"mark the resource {resource} in the stack as unhealthy"}
        self.app.render(res, headers=["msg"], maxsize=200)

    #
    # share
    #
    @ex(
        help=_("get manila share types"),
        description=_("get manila share types"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("share type id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("share type description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_type_get(self):
        oid = getattr(self.app.pargs, "id", None)
        desc = self.app.pargs.desc
        if oid is not None:
            res = self.client.manila.share_type.get(oid)
            self.app.render(res, details=True)
        else:
            params = {"desc": desc}
            res = self.client.manila.share_type.list(**params)
            headers = [
                "id",
                "name",
                "description",
                "extra_specs",
                "required_extra_specs",
            ]
            fields = [
                "id",
                "name",
                "description",
                "extra_specs",
                "required_extra_specs",
            ]

            def extra_specs_func(data):
                res = []
                for k, v in data.items():
                    res.append(f"{k}={v}")
                return "\n".join(res)

            transform = {
                "extra_specs": extra_specs_func,
                "required_extra_specs": extra_specs_func,
            }
            self.app.render(res, headers=headers, fields=fields, maxsize=200, transform=transform)

    @ex(
        help=_("get manila share limits"),
        description=_("get manila share limits"),
        arguments=OPENSTACK_ARGS(),
    )
    def share_limit_get(self):
        res = self.client.manila.limits().get("limits").get("absolute")
        self.app.render(res, details=True)

    @ex(
        help=_("get manila share messages"),
        description=_("get manila share messages"),
        arguments=OPENSTACK_ARGS(
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
    def share_message_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.manila.messages(resource_id=oid)[0]
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.manila.messages(**params)
            headers = [
                "id",
                "action_id",
                "resource_type",
                "resource_id",
                "message_level",
                "created_at",
                "user_message",
            ]
            fields = [
                "id",
                "action_id",
                "resource_type",
                "resource_id",
                "message_level",
                "created_at",
                "user_message",
            ]

            self.app.render(res, headers=headers, fields=fields, maxsize=200, transform=None)

    @ex(
        help=_("get manila shares"),
        description=_("get manila shares"),
        arguments=OPENSTACK_ARGS(
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
            res = self.client.manila.share.get(oid)

            if self.is_output_text():
                self.app.render(res, details=True)

                self.c("\nexports:", "underline")
                exports = self.client.manila.share.list_export_locations(oid)
                self.app.render(exports, headers=["id", "path"], maxsize=200)

                self.c("\ngrant:", "underline")
                grants = self.client.manila.share.action.list_access(oid)
                self.app.render(
                    grants,
                    headers=["id", "access_type", "access_level", "state", "access_to"],
                )
            else:
                self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.manila.share.list(details=True, **params)
            headers = [
                "id",
                "name",
                "project_id",
                "size",
                "created_at",
                "share_type",
                "share_proto",
                "status",
                "is_public",
            ]
            fields = [
                "id",
                "name",
                "project_id",
                "size",
                "created_at",
                "share_type",
                "share_proto",
                "status",
                "is_public",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("get export locations of a manila share"),
        description=_("get export locations of a manila share"),
        arguments=OPENSTACK_ARGS(
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
    def share_export_locations_get(self):
        oid = getattr(self.app.pargs, "id", None)
        exports = self.client.manila.share.list_export_locations(oid)
        self.app.render(exports, headers=["id", "path"], maxsize=200)

    @ex(
        help=_("add manila share"),
        description=_("add manila share"),
        arguments=OPENSTACK_ARGS(
            [
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
                    ["size"],
                    {
                        "help": _("share size in GB"),
                        "action": "store",
                        "type": int,
                        "default": 1,
                    },
                ),
                (
                    ["proto"],
                    {
                        "help": _("share protocol (NFS, CIFS, GlusterFS, HDFS, or CephFS. CephFS)"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["type"],
                    {
                        "help": _("share type id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-snapshot"],
                    {
                        "help": _("share snapshot id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group"],
                    {
                        "help": _("share group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": _(
                            "the id of a share network where the share server exists or will be created. "
                            "If is None and you provide a snapshot_id, the network value from the snapshot "
                            "is used"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_add(self):
        name = self.app.pargs.name
        size = self.app.pargs.size
        proto = self.app.pargs.proto
        share_type = self.app.pargs.type
        snapshot = self.app.pargs.snapshot
        group = self.app.pargs.group
        network = self.app.pargs.network
        res = self.client.manila.share.create(
            proto,
            size,
            name=name,
            description=name,
            share_type=share_type,
            is_public=False,
            availability_zone="nova",
            snapshot_id=snapshot,
            share_group_id=group,
            share_network_id=network,
        )
        self.app.render({"msg": f"add manila share {res['id']}"})

    @ex(
        help=_("delete manila shares"),
        description=_("delete manila shares"),
        arguments=OPENSTACK_ARGS(
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
                        "help": _("if true force delete"),
                        "action": "store",
                        "type": bool,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def share_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        if force is True:
            self.client.manila.share.action.force_delete(oid)
        else:
            self.client.manila.share.delete(oid)
        self.app.render({"msg": f"delete manila share {oid}"})

    @ex(
        help=_("extend manila share size"),
        description=_("extend manila share size"),
        arguments=OPENSTACK_ARGS(
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
                        "help": _("new size of the share, in GBs."),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_size_extend(self):
        oid = self.app.pargs.id
        new_size = self.app.pargs.size
        self.client.manila.share.action.extend(oid, new_size)
        self.app.render({"msg": f"Extend share {oid} to {new_size}"})

    @ex(
        help=_("shrink manila share size"),
        description=_("shrink manila share size"),
        arguments=OPENSTACK_ARGS(
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
                        "help": _("new size of the share, in GBs."),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_size_shrink(self):
        oid = self.app.pargs.id
        new_size = self.app.pargs.size
        self.client.manila.share.action.shrink(oid, new_size)
        self.app.render({"msg": f"Shrink share {oid} to {new_size}"})

    #
    # share network
    #
    @ex(
        help=_("get manila share networks"),
        description=_("get manila share networks"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("share network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": _("neutron network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subnet"],
                    {
                        "help": _("neutron subnet id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_network_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.manila.network.get(oid)
            self.app.render(res, details=True)
        else:
            params = {}
            self.add_field_from_pargs_to_data("network", params, "neutron_net_id")
            self.add_field_from_pargs_to_data("subnet", params, "neutron_subnet_id")
            res = self.client.manila.network.list(details=True, **params)
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

    @ex(
        help=_("add manila share network"),
        description=_("add manila share network"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("share network name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("share network description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["network"],
                    {
                        "help": _(
                            "The UUID of a neutron network when setting up or updating a share network subnet "
                            "with neutron. Specify both a neutron network and a neutron subnet that belongs "
                            "to that neutron network."
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["subnet"],
                    {
                        "help": _(
                            "The UUID of the neutron subnet when setting up or updating a share network subnet "
                            "with neutron. Specify both a neutron network and a neutron subnet that belongs to "
                            "that neutron network."
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-availability_zone"],
                    {
                        "help": _("The UUID or name of an availability zone for the share network subnet."),
                        "action": "store",
                        "type": str,
                        "default": "nova",
                    },
                ),
            ]
        ),
    )
    def share_network_add(self):
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        network = self.app.pargs.network
        subnet = self.app.pargs.subnet
        availability_zone = self.app.pargs.availability_zone
        if desc is None:
            desc = name
        self.client.manila.network.create(
            name=name,
            description=desc,
            neutron_net_id=network,
            neutron_subnet_id=subnet,
            availability_zone=availability_zone,
        )
        self.app.render({"msg": f"add manila share network {name}"})

    @ex(
        help=_("update manila share network"),
        description=_("update manila share network"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("share network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("share network name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("share network description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": _(
                            "The UUID of a neutron network when setting up or updating a share network subnet "
                            "with neutron. Specify both a neutron network and a neutron subnet that belongs "
                            "to that neutron network."
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subnet"],
                    {
                        "help": _(
                            "The UUID of the neutron subnet when setting up or updating a share network subnet "
                            "with neutron. Specify both a neutron network and a neutron subnet that belongs to "
                            "that neutron network."
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_network_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        network = self.app.pargs.network
        subnet = self.app.pargs.subnet
        if desc is None:
            desc = name
        self.client.manila.network.create(
            oid,
            name=name,
            description=desc,
            neutron_net_id=network,
            neutron_subnet_id=subnet,
        )
        self.app.render({"msg": f"update manila share network {oid}"})

    @ex(
        help=_("delete manila share networks"),
        description=_("delete manila share networks"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_network_del(self):
        oid = self.app.pargs.id
        self.client.manila.network.delete(oid)
        self.app.render({"msg": f"delete manila share {oid}"})

    @ex(
        help=_("add security service to share network"),
        description=_("add security service to share network"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["service"],
                    {
                        "help": _("security service id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_network_security_service_add(self):
        oid = self.app.pargs.id
        service = self.app.pargs.service
        self.client.manila.network.add_security_service(oid, service)
        self.app.render({"msg": f"add security service to share network {oid}"})

    @ex(
        help=_("delete security service from share network"),
        description=_("delete security service from share network"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share network id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["service"],
                    {
                        "help": _("security service id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_network_security_service_del(self):
        oid = self.app.pargs.id
        service = self.app.pargs.service
        self.client.manila.network.add_security_service(oid, service)
        self.app.render({"msg": f"delete security service from share network {oid}"})

    #
    # share server
    #
    @ex(
        help=_("get manila share servers"),
        description=_("get manila share servers"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("share server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_server_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.manila.server.get(oid)
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.manila.server.list(**params)
            headers = [
                "id",
                "project_id",
                "host",
                "share_network_id",
                "share_network_name",
                "updated_at",
                "status",
            ]
            fields = [
                "id",
                "project_id",
                "host",
                "share_network_id",
                "share_network_name",
                "updated_at",
                "status",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("delete manila share servers"),
        description=_("delete manila share servers"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("share server id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_server_del(self):
        oid = self.app.pargs.id
        self.client.manila.server.delete(oid)
        self.app.render({"msg": f"delete manila share {oid}"})

    #
    # share grant
    #
    @ex(
        help=_("add manila share access grant"),
        description=_("add manila share access grant"),
        example=(
            "beehive platform openstack share-grant-add <uuid> -level rw -type ip -to ###.###.###.###/32; "
        ),
        arguments=OPENSTACK_ARGS(
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
                    ["-level"],
                    {
                        "help": _(
                            "the access level to the share. rw: Read and write (RW) access. ro: Read-only (RO) "
                            "access."
                        ),
                        "action": "store",
                        "type": str,
                        "default": "rw",
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _(
                            "the access rule type. ip: Authenticates an instance through its IP address. cert: "
                            "Authenticates an instance through a TLS certificate. user: Authenticates by a user "
                            "or group name."
                        ),
                        "action": "store",
                        "type": str,
                        "default": "ip",
                    },
                ),
                (
                    ["-to"],
                    {
                        "help": _(
                            "the value that defines the access. ip: A valid format is XX.XX.XX.XX or XX.XX.XX.XX/XX."
                            " For example 0.0.0.0/0. cert: Specify the TLS identity as the IDENTKEY. A valid value "
                            "is any string up to 64 characters long in the common name (CN) of the certificate. The "
                            "meaning of a string depends on its interpretation. user: A valid value is an "
                            "alphanumeric string that can contain some special characters and is from 4 to 32 "
                            "characters long."
                        ),
                        "action": "store",
                        "type": str,
                        "default": "0.0.0.0/0",
                    },
                ),
            ]
        ),
    )
    def share_grant_add(self):
        oid = self.app.pargs.id
        access_level = self.app.pargs.level
        access_type = self.app.pargs.type
        access_to = self.app.pargs.to
        res = self.client.manila.share.action.grant_access(oid, access_level, access_type, access_to)
        self.app.render(res, headers=["id", "access_type", "access_level", "state", "access_to"])

    @ex(
        help=_("remove manila share access grant"),
        description=_("remove manila share access grant"),
        arguments=OPENSTACK_ARGS(
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
                        "help": _("grant id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_grant_remove(self):
        oid = self.app.pargs.id
        access_id = self.app.pargs.access_id
        self.client.manila.share.action.revoke_access(oid, access_id)
        self.app.render({"msg": f"Revoke access {oid} to share {access_id}"})

    @ex(
        help=_("reset manila share status"),
        description=_("reset manila share status"),
        arguments=OPENSTACK_ARGS(
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
                    ["-status"],
                    {
                        "help": _(
                            "the share access status. One of: available, creating, migrating_to, error_deleting, "
                            "error, migrating, deleting"
                        ),
                        "action": "store",
                        "type": str,
                        "default": "available",
                    },
                ),
            ]
        ),
    )
    def share_status_reset(self):
        oid = self.app.pargs.id
        status = self.app.pargs.status
        self.client.manila.share.action.reset_status(oid, status)
        self.app.render({"msg": f"Reset status of share {oid} to {status}"})

    #
    # share snapshot
    #
    @ex(
        help=_("revert manila share to snapshot"),
        description=_("revert manila share to snapshot"),
        arguments=OPENSTACK_ARGS(
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
                    ["snapshot_id"],
                    {
                        "help": _("the share snapshot id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_snapshot_revert(self):
        oid = self.app.pargs.id
        snapshot_id = self.app.pargs.snapshot_id
        self.client.manila.share.action.revert(oid, snapshot_id)
        self.app.render({"msg": f"Revert share {oid} to snapshot_id {snapshot_id}"})

    #
    # volume messages
    #
    @ex(
        help=_("get volume messages"),
        description=_("get volume messages"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("volume message id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_message_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.volume_v3.get(oid)

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.volume_v3.messages(**params)
            headers = ["id", "user_message", "resource_uuid", "created_at"]
            fields = ["id", "user_message", "resource_uuid", "created_at"]
            self.app.render(res, headers=headers, fields=fields, maxsize=200)

    #
    # volume backend
    #
    @ex(
        help=_("get all back-end storage pools that are known to the scheduler service"),
        description=_("get all back-end storage pools that are known to the scheduler service"),
        example="beehive platform openstack volume-backend-get -backendname podto2-transito -e <env> -f json",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-hostname"],
                    {
                        "help": _("backend storage pool hostname"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-backendname"],
                    {
                        "help": _("volume backend name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_backend_get(self):
        hostname = self.app.pargs.hostname
        backend_name = self.app.pargs.backendname
        params = {"hostname": hostname, "backend_name": backend_name}
        res = self.client.volume_v3.get_backend_storage_pools(**params)
        headers = ["name", "backend_name", "utilization", "free_capacity_gb"]
        fields = [
            "name",
            "capabilities.volume_backend_name",
            "capabilities.utilization",
            "capabilities.free_capacity_gb",
        ]
        self.app.render(res, headers=headers, fields=fields, maxsize=1000)

    #
    # volume
    #
    @ex(
        help=_("get volumes"),
        description=_("get volumes"),
        example="beehive platform openstack volume-get -e <env> -id <uuid>",
        arguments=OPENSTACK_ARGS(
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
                    ["-limit"],
                    {
                        "help": _("requests a page size of items. Use -1 to list all the volume"),
                        "action": "store",
                        "type": int,
                        "default": 20,
                    },
                ),
                (
                    ["-offset"],
                    {
                        "help": _(
                            "used in conjunction with limit to return a slice of items. offset is where to "
                            "start in the list"
                        ),
                        "action": "store",
                        "type": str,
                        "default": 0,
                    },
                ),
            ]
        ),
    )
    def volume_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.volume_v3.get(oid)

            if self.is_output_text():
                attachments = res.pop("attachments", [])
                metadata = res.pop("metadata", {})
                image_metadata = res.pop("volume_image_metadata", {})
                self.app.render(res, details=True)

                self.c("\nattachments", "underline")
                self.app.render(
                    attachments,
                    headers=[
                        "attachment_id",
                        "server_id",
                        "attached_at",
                        "host_name",
                        "device",
                    ],
                )
                self.c("\nmetadata", "underline")
                self.app.render(metadata, details=True)
                self.c("\nimage metadata", "underline")
                self.app.render(image_metadata, details=True)
            else:
                self.app.render(res, details=True)
        else:
            limit = self.app.pargs.limit
            offset = self.app.pargs.offset
            params = {"detail": True, "limit": limit, "offset": offset}
            if limit == -1:
                res = self.client.volume_v3.list_all(detail=True)
            else:
                res = self.client.volume_v3.list(**params)
            headers = [
                "id",
                "name",
                "os-vol-tenant-attr:tenant_id",
                "size",
                "status",
                "type",
                "bootable",
                "created_at",
                "attachments.0.server_id",
            ]
            fields = [
                "id",
                "name",
                "os-vol-tenant-attr:tenant_id",
                "size",
                "status",
                "volume_type",
                "bootable",
                "created_at",
                "attachments.0.server_id",
            ]
            print(f"Page: {offset}")
            print(f"Count: {limit}")
            print(f"Total: {self.client.volume_v3.volume_count}")
            print("Order:")
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("add volume"),
        description=_("add volume"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("volume name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["size"],
                    {
                        "help": _("volume size in Gb"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("volume type"),
                        "action": "store",
                        "type": str,
                        "default": "nfsgold",
                    },
                ),
                (
                    ["-snapshot_id"],
                    {
                        "help": _("the snapshot id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_add(self):
        name = self.app.pargs.name
        size = self.app.pargs.size
        volume_type = self.app.pargs.type
        snapshot_id = self.app.pargs.snapshot_id
        params = {
            "name": name,
            "size": size,
            "volume_type": volume_type,
            "snapshot_id": snapshot_id,
        }
        res = self.client.volume_v3.create(**params)
        self.app.render({"msg": f"Created volume {name}, id {res['id']}, size {res['size']} Gb"})

    @ex(
        help=_("migrate volume"),
        description=_("migrate volume"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["volume_id"],
                    {
                        "help": _("volume id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["host"],
                    {"help": _("host"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-force_host_copy"],
                    {
                        "help": _("force_host_copy"),
                        "action": "store",
                        "type": str,
                        "default": "False",
                    },
                ),
                (
                    ["-lock_volume"],
                    {
                        "help": _("lock_volume"),
                        "action": "store",
                        "type": bool,
                        "default": "False",
                    },
                ),
            ]
        ),
    )
    def volume_migrate(self):
        volume_id = self.app.pargs.volume_id
        host = self.app.pargs.host
        force_host_copy = str2bool(self.app.pargs.force_host_copy)
        lock_volume = str2bool(self.app.pargs.lock_volume)
        self.client.volume_v3.migrate(volume_id, host, force_host_copy=force_host_copy, lock_volume=lock_volume)
        self.app.render({"msg": f"Migrated volume {volume_id} on host {host}"})

    @ex(
        help=_("volume api extensions"),
        description=_("list volume Block Storage API extensions"),
        arguments=OPENSTACK_ARGS([]),
    )
    def volume_api_extensions(self):
        res = self.client.volume_v3.api_extensions()
        headers = ["alias", "name", "description", "namespace", "links", "updated"]
        fields = ["alias", "name", "description", "namespace", "links", "updated"]
        self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("update volume"),
        description=_("update volume"),
        arguments=OPENSTACK_ARGS(
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
                    ["-name"],
                    {
                        "help": _("volume name"),
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
        name = self.app.pargs.name
        self.client.volume_v3.update(oid, name=name)
        msg = f"Update volume {oid}"
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help=_("delete volume"),
        description=_("delete volume"),
        arguments=OPENSTACK_ARGS(
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
                        "help": _("force delete"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
            ]
        ),
    )
    def volume_del(self):
        oid = self.app.pargs.id
        force = str2bool(self.app.pargs.force)
        self.client.volume_v3.delete(oid, force=force)
        self.app.render({"msg": f"Delete volume {oid}"})

    @ex(
        help=_("extend volume"),
        description=_("extend volume"),
        arguments=OPENSTACK_ARGS(
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
                (["size"], {"help": _("new volume size"), "action": "store", "type": str}),
            ]
        ),
    )
    def volume_extend(self):
        oid = self.app.pargs.id
        size = self.app.pargs.size
        self.client.volume_v3.extend(oid, size)
        self.app.render({"msg": f"extend volume {oid}"})

    @ex(
        help=_("unmanage volume"),
        description=_("unmanage volume"),
        arguments=OPENSTACK_ARGS(
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
    def volume_unmanage(self):
        oid = self.app.pargs.id
        self.client.volume_v3.unmanage(oid)
        self.app.render({"msg": f"unmanage volume {oid}"})

    @ex(
        help=_("manage volume"),
        description=_("manage volume"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["source_volume_id"],
                    {
                        "help": _("source volume id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("new volume name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("new volume description"),
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
                    ["-bootable"],
                    {
                        "help": _("bootable value"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-host"],
                    {
                        "help": _("source volume host"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-cluster"],
                    {
                        "help": _("source volume cluster"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_manage(self):
        source_volume_id = self.app.pargs.source_volume_id
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        volume_type = self.app.pargs.volume_type
        bootable = str2bool(self.app.pargs.bootable)
        host = self.app.pargs.host
        cluster = self.app.pargs.cluster
        self.client.volume_v3.manage(
            source_volume_id,
            name,
            volume_type,
            bootable=bootable,
            desc=desc,
            availability_zone="nova",
            host=host,
            cluster=cluster,
        )
        self.app.render({"msg": f"manage volume {source_volume_id}"})

    @ex(
        help=_("set volume status"),
        description=_("set volume status"),
        arguments=OPENSTACK_ARGS(
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
                    ["-status"],
                    {
                        "help": _("volume id"),
                        "action": "store",
                        "type": str,
                        "default": "available",
                    },
                ),
            ]
        ),
    )
    def volume_status_set(self):
        oid = self.app.pargs.id
        status = self.app.pargs.status
        self.client.volume_v3.reset_status(oid, status, "detached", "success")
        self.app.render({"msg": f"Reset volume {oid} status to {status}"})

    @ex(
        help=_("clone volume"),
        description=_("clone volume"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("volume name"),
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
                    ["project"],
                    {
                        "help": _("project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-volume_type"],
                    {
                        "help": _("the volume type id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_clone(self):
        name = self.app.pargs.name
        volume_id = self.app.pargs.volume
        project_id = self.app.pargs.project
        volume_type = self.app.pargs.volume_type
        self.client.volume_v3.clone(name, volume_id, project_id, volume_type=volume_type)
        self.app.render({"msg": f"Clone volume {volume_id}"})

    @ex(
        help=_("get volume types"),
        description=_("get volume types"),
        example="beehive platform openstack volume-type-get -e <env>",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("volume type id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_type_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.volume_v3.type.get(oid)
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.volume_v3.type.list(**params)
            headers = ["id", "name", "is_public", "qos_specs_id", "extra_specs"]
            fields = ["id", "name", "is_public", "qos_specs_id", "extra_specs"]
            self.app.render(res, headers=headers, fields=fields, maxsize=200)

    @ex(
        help=_("change volume type"),
        description=_("change volume type"),
        example="beehive platform openstack volume-type-update <uuid> <uuid> -e <env>",
        arguments=OPENSTACK_ARGS(
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
                    ["volume_type"],
                    {
                        "help": _("volume type id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_type_update(self):
        oid = self.app.pargs.id
        volume_type = self.app.pargs.volume_type
        rot_bar = rotating_bar()

        snapshots = self.client.volume_v3.snapshot.list(volume_id=oid)
        for snapshot in snapshots:
            self.client.volume_v3.snapshot.delete(snapshot["id"])
            try:
                while True:
                    self.client.volume_v3.snapshot.get(snapshot["id"])
                    # stdout.write(".")
                    stdout.write(next(rot_bar))
                    stdout.flush()
                    sleep(1)
            except:
                stoprotation()
                self.app.render({"msg": f"remove snapshot {snapshot['id']}"})
        stoprotation()
        self.client.volume_v3.change_type(oid, volume_type)
        res = self.client.volume_v3.get(oid)
        status = res["status"]
        while status == "retyping":
            stdout.write(".")
            stdout.flush()
            sleep(2)
            res = self.client.volume_v3.get(oid)
            status = res["status"]
        stoprotation()
        self.app.render({"msg": f"change volume {oid} type to {volume_type}"})

    @ex(
        help=_("get volume attachments"),
        description=_("get volume attachments"),
        arguments=OPENSTACK_ARGS(
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
                    ["-instance"],
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
    def volume_attachment_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.volume_v3.attachment.get(oid)

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            params = {}
            params = self.add_field_from_pargs_to_data("instance", params, "instance_id")
            res = self.client.volume_v3.attachment.list(**params)
            headers = [
                "id",
                "volume_id",
                "instance",
                "attach_mode",
                "status",
                "attached_at",
                "detached_at",
            ]
            fields = [
                "id",
                "volume_id",
                "instance",
                "attach_mode",
                "status",
                "attached_at",
                "detached_at",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("attach volume from server"),
        description=_("attach volume from server"),
        example="beehive platform openstack volume-attach <uuid> <uuid> /dev/vda -e <env>",
        arguments=OPENSTACK_ARGS(
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
                    ["instance"],
                    {
                        "help": _("instance id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["mountpoint"],
                    {
                        "help": _("instance mountpoint. ex. /dev/vda"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_attach(self):
        oid = self.app.pargs.id
        instance = self.app.pargs.instance
        mountpoint = self.app.pargs.mountpoint
        self.client.volume_v3.attach_volume_to_server(oid, instance, mountpoint)
        self.app.render({"msg": f"attach volume {oid}"})

    @ex(
        help=_("detach volume from server"),
        description=_("detach volume from server"),
        example="beehive platform openstack volume-detach <uuid> -e <env>",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("volume id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def volume_detach(self):
        oid = self.app.pargs.id
        attachment = self.client.volume_v3.attachment.list(volume_id=oid)
        self.client.volume_v3.detach_volume_from_server(oid, attachment[0]["id"])
        self.app.render({"msg": f"detach volume {oid}"})

    @ex(
        help=_("update volume"),
        description=_("update volume"),
        arguments=OPENSTACK_ARGS(
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
                    ["-bootable"],
                    {
                        "help": _("bootable status"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
            ]
        ),
    )
    def volume_bootable_status_update(self):
        oid = self.app.pargs.id
        bootable = str2bool(self.app.pargs.bootable)
        self.client.volume_v3.update_bootable_status(oid, bootable=bootable)
        msg = f"Update volume {oid} bootable status"
        self.app.render({"msg": msg})

    #
    # volume metadata
    #
    @ex(
        help=_("add volume metadata"),
        description=_("add volume metadata"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("snapshot id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["metadata"],
                    {
                        "help": _("key:value string metadata"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_metadata_add(self):
        oid = self.app.pargs.id
        metadata = self.app.pargs.metadata
        metadata = metadata.split(":")
        metadata = {metadata[0]: metadata[1]}
        self.client.volume_v3.add_metadata(oid, metadata)
        self.app.render({"msg": f"add metadata {metadata} to volume {oid}"})

    @ex(
        help=_("del volume metadata"),
        description=_("del volume metadata"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("snapshot id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["metadata"],
                    {
                        "help": _("metadata key"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_metadata_del(self):
        oid = self.app.pargs.id
        metadata = self.app.pargs.metadata
        self.client.volume_v3.remove_metadata(oid, metadata)
        self.app.render({"msg": f"remove metadata {metadata} to volume {oid}"})

    #
    # volume image metadata
    #
    @ex(
        help=_("add volume image metadata"),
        description=_("add volume image metadata"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("snapshot id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["metadata"],
                    {
                        "help": _("key:value string metadata"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_image_metadata_add(self):
        oid = self.app.pargs.id
        metadata = self.app.pargs.metadata
        metadata = metadata.split(":")
        metadata = {metadata[0]: metadata[1]}
        self.client.volume_v3.set_image_metadata(oid, metadata)
        self.app.render({"msg": f"add image metadata {metadata} to volume {oid}"})

    @ex(
        help=_("del volume image metadata"),
        description=_("del volume image metadata"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("snapshot id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["metadata"],
                    {
                        "help": _("metadata key"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_image_metadata_del(self):
        oid = self.app.pargs.id
        metadata = self.app.pargs.metadata
        self.client.volume_v3.remove_image_metadata(oid, metadata)
        self.app.render({"msg": f"remove image metadata {metadata} to volume {oid}"})

    #
    # volume snapshot
    #
    @ex(
        help=_("get volume snapshots"),
        description=_("get volume snapshots"),
        example="beehive platform openstack volume-snapshot-get -e <env>",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("snapshot id"),
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
                    ["-group_snapshot"],
                    {
                        "help": _("group snapshot id"),
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
        if oid is not None:
            res = self.client.volume_v3.snapshot.get(oid)
            self.app.render(res, details=True)
        else:
            params = {}
            volume_id = self.app.pargs.volume
            group_snapshot_id = self.app.pargs.group_snapshot
            if volume_id is not None:
                params["volume_id"] = volume_id
            elif group_snapshot_id is not None:
                params["group_snapshot_id"] = group_snapshot_id
            res = self.client.volume_v3.snapshot.list(**params)
            fields = [
                "id",
                "name",
                "descriptions",
                "volume_id",
                "os-extended-snapshot-attributes:project_id",
                "status",
                "created_at",
                "os-extended-snapshot-attributes:progress",
                "size",
            ]
            headers = [
                "id",
                "name",
                "desc",
                "volume-id",
                "project-id",
                "status",
                "created",
                "progress",
                "size",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("add volume snapshots"),
        description=_("add volume snapshots"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("snapshot name"),
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
                    ["-desc"],
                    {
                        "help": _("snapshot description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("indicates whether to snapshot, even if the volume is attached"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
    )
    def volume_snapshot_add(self):
        name = self.app.pargs.name
        volume = self.app.pargs.volume
        desc = self.app.pargs.desc
        force = str2bool(self.app.pargs.force)
        data = {"name": name, "description": desc, "volume_id": volume, "force": force}
        res = self.client.volume_v3.snapshot.create(**data)
        self.app.render(
            {"msg": f"adding snapshot {res['id']} with name {name} for volume {volume}"},
            maxsize=200,
        )

    @ex(
        help=_("delete volume snapshot"),
        description=_("delete volume snapshot"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("snapshot id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def volume_snapshot_del(self):
        oid = self.app.pargs.id
        self.client.volume_v3.snapshot.delete(oid)
        self.app.render({"msg": f"Delete volume snapshot {oid}"})

    @ex(
        help=_("set volume snapshot status"),
        description=_("set volume snapshot status"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("snapshot id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": _("snapshot status"),
                        "action": "store",
                        "type": str,
                        "default": "available",
                    },
                ),
            ]
        ),
    )
    def volume_snapshot_status_set(self):
        oid = self.app.pargs.id
        status = self.app.pargs.status
        self.client.volume_v3.snapshot.reset_status(oid, status)
        self.app.render({"msg": f"set volume snapshot {oid} status to {status}"})

    @ex(
        help=_("revert volume to snapshot"),
        description=_("revert volume to snapshot"),
        arguments=OPENSTACK_ARGS(
            [
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
        volume = self.app.pargs.volume
        snapshot = self.app.pargs.snapshot
        self.client.volume_v3.snapshot.revert_to(volume, snapshot)
        self.app.render({"msg": f"revert volume {volume} to snapshot {snapshot}"})

    #
    # volume group type
    #
    @ex(
        help=_("get volume group types"),
        description=_("get volume group types"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("volume group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_group_type_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.volume_v3.group.get_type(oid)
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.volume_v3.group.list_types(**params)
            headers = ["id", "name", "desc", "is_public", "specs"]
            fields = ["id", "name", "description", "is_public", "group_specs"]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("add volume group type"),
        description=_("add volume group type"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("volume group type name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group_specs"],
                    {
                        "help": _("volume group type specs"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_group_type_add(self):
        name = self.app.pargs.name
        group_specs = self.app.pargs.group_specs
        data = {
            "name": name,
        }
        if group_specs is not None:
            data["group_specs"] = group_specs
        self.client.volume_v3.group.type_create(**data)
        self.app.render({"msg": f"add volume group type {name}"}, maxsize=200)

    @ex(
        help=_("delete volume group type"),
        description=_("delete volume group type"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("volume group type id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def volume_group_type_del(self):
        oid = self.app.pargs.id
        self.client.volume_v3.group.type_delete(oid)
        self.app.render({"msg": f"Delete volume group type {oid}"})

    #
    # volume group
    #
    @ex(
        help=_("get volume groups"),
        description=_("get volume groups"),
        example="beehive platform openstack volume-group-get",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("volume group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_group_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.volume_v3.group.get(oid)
            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            params = {"detail": True}
            res = self.client.volume_v3.group.list(**params)
            headers = [
                "id",
                "name",
                "availability_zone",
                "status",
                "group_type",
                "volume_types",
                "volumes",
                "created_at",
            ]
            fields = [
                "id",
                "name",
                "availability_zone",
                "status",
                "group_type",
                "volume_types",
                "volumes",
                "created_at",
            ]
            transform = {"volumes": len}
            self.app.render(res, headers=headers, fields=fields, transform=transform)

    @ex(
        help=_("add volume group"),
        description=_("add volume group"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("volume group name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-availability_zone"],
                    {
                        "help": _("volume group availability zone"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["volume_types"],
                    {
                        "help": _(
                            "the list of volume types. In an environment with multiple-storage back ends, "
                            "the scheduler determines where to send the volume based on the volume type."
                        ),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["group_type"],
                    {"help": _("group type id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def volume_group_add(self):
        name = self.app.pargs.name
        availability_zone = self.app.pargs.availability_zone
        volume_types = self.app.pargs.volume_types.split(",")
        group_type = self.app.pargs.group_type
        data = {"name": name, "group_type": group_type, "volume_types": volume_types}
        if availability_zone is not None:
            data["availability_zone"] = availability_zone
        res = self.client.volume_v3.group.create(**data)
        res_id = res["id"]
        self.app.render({"msg": f"added volume group {name} with id {res_id}"}, maxsize=200)

    @ex(
        help=_("update volume group"),
        description=_("update volume group"),
        arguments=OPENSTACK_ARGS(
            [
                (["id"], {"help": _("volume group id"), "action": "store", "type": str}),
                (
                    ["-name"],
                    {
                        "help": _("volume group name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("volume group availability zone"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-del"],
                    {
                        "help": _("One or more volume UUIDs, separated by commas, that you want to remove from group"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-add"],
                    {
                        "help": _("One or more volume UUIDs, separated by commas, that you want to add to group"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_group_update(self):
        oid = self.app.pargs.id
        data = {}
        data = self.add_field_from_pargs_to_data("name", data, "name")
        data = self.add_field_from_pargs_to_data("desc", data, "description")
        data = self.add_field_from_pargs_to_data("del", data, "remove_volumes")
        data = self.add_field_from_pargs_to_data("add", data, "add_volumes")
        self.client.volume_v3.group.update(oid, **data)
        self.app.render({"msg": f"update volume group {oid}"}, maxsize=200)

    @ex(
        help=_("delete volume group"),
        description=_("delete volume group"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("volume group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def volume_group_del(self):
        oid = self.app.pargs.id
        self.client.volume_v3.group.delete(oid)
        self.app.render({"msg": f"Delete volume group {oid}"})

    #
    # volume group snapshot
    #
    @ex(
        help=_("get volume group snapshots"),
        description=_("get volume group snapshots"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("volume group snapshot id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group"],
                    {
                        "help": _("volume group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_group_snapshot_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.volume_v3.group.get_snapshot(oid)

            if self.is_output_text():
                self.app.render(res, details=True)

                self.c("\nsimple volume snapshots", "underline")
                res = self.client.volume_v3.snapshot.list(group_snapshot_id=oid, all=False)
                fields = [
                    "id",
                    "name",
                    "descriptions",
                    "volume_id",
                    "os-extended-snapshot-attributes:project_id",
                    "status",
                    "created_at",
                    "os-extended-snapshot-attributes:progress",
                    "size",
                ]
                headers = [
                    "id",
                    "name",
                    "desc",
                    "volume-id",
                    "project-id",
                    "status",
                    "created",
                    "progress",
                    "size",
                ]
                self.app.render(res, headers=headers, fields=fields)
            else:
                self.app.render(res, details=True)
        else:
            params = {"detail": True}
            params = self.add_field_from_pargs_to_data("group", params, "group_id")
            res = self.client.volume_v3.group.list_snapshots(**params)
            headers = ["id", "name", "group", "group_type", "status", "created_at"]
            fields = ["id", "name", "group_id", "group_type_id", "status", "created_at"]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("add volume group snapshot"),
        description=_("add volume group snapshot"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["group"],
                    {
                        "help": _("volume group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("volume group snapshot name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("volume group snapshot description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def volume_group_snapshot_add(self):
        oid = self.app.pargs.group
        data = {}
        data = self.add_field_from_pargs_to_data("name", data, "name")
        data = self.add_field_from_pargs_to_data("desc", data, "description")
        self.client.volume_v3.group.create_snapshot(oid, **data)
        self.app.render({"msg": f"add volume group {oid} snapshot"}, maxsize=200)

    @ex(
        help=_("delete volume group snapshot"),
        description=_("delete volume group snapshot"),
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("volume group snapshot id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def volume_group_snapshot_del(self):
        oid = self.app.pargs.id
        self.client.volume_v3.group.delete_snapshot(oid)
        self.app.render({"msg": f"Delete volume group snapshot {oid}"})
