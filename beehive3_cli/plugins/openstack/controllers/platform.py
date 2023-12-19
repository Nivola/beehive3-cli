# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from datetime import datetime
from json import loads
from sys import stdout
from copy import deepcopy
from time import sleep, time
from ipaddress import IPv4Address
from cement import ex
from beecell.db import MysqlManager
from beecell.types.type_string import str2bool
from beecell.types.type_dict import dict_get
from beecell.types.type_date import format_date
from beecell.types.type_list import merge_list
from beedrones.openstack.client import OpenstackManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS, StringAction
from beehive3_cli.core.util import load_environment_config, load_config, rotating_bar


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


class OpenstackPlatformController(BaseController):
    class Meta:
        label = "openstack"
        stacked_on = "platform"
        stacked_type = "nested"
        description = "openstack platform"
        help = "openstack platform"

    def pre_command_run(self):
        super(OpenstackPlatformController, self).pre_command_run()

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

        if self.app.config.get("log.clilog", "verbose_log"):
            transform = {"msg": lambda x: self.color_string(x, "YELLOW")}
            self.app.render(
                {"msg": "Using openstack orchestrator: %s (uri: %s - project: %s)" % (label, uri, project)},
                transform=transform,
            )
            self.app.log.debug("Using openstack orchestrator: %s (uri: %s - project: %s)" % (label, uri, project))

        self.client = OpenstackManager(uri, default_region=conf.get("region"))
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
                self.app.log.error("Select orchestrators among: %s" % orchestrators_available)
                raise Exception("Select orchestrators among: %s" % orchestrators_available)

            conf = orchestrators.get(instance)
            hosts = conf.pop("hosts")
            if vip is True:
                hosts = [conf.get("vhost")]
            for host in hosts:
                uri = "%s://%s:%s%s" % (
                    conf.get("proto"),
                    host,
                    conf.get("port"),
                    conf.get("path"),
                )
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
        db_uri = "mysql+pymysql://%s:%s@%s:%s/%s" % (
            user["name"],
            user["password"],
            host,
            port,
            db,
        )
        server = MysqlManager(1, db_uri)
        server.create_simple_engine()
        self.app.log.info("Get maria engine for %s" % db_uri)
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
                self.app.log.info("Query openstack %s : %s" % (config["host"], elapsed))
            self.app.render(resp, headers=["instance", "host", "elapsed", "response"], maxsize=300)
        except Exception as ex:
            self.error(ex)

    @ex(
        help="ping mariadb instances",
        description="ping mariadb instances",
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
            self.app.log.info("Ping maria : %s" % res)

        self.app.render(resp, headers=["host", "response"])

    @ex(
        help="get mariadb galera cluster status",
        description="get mariadb galera cluster status",
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
                self.app.log.info("get maria cluster status : %s" % status)
                summary_status = (
                    (status["wsrep_cluster_status"] == "Primary")
                    and int(status["wsrep_cluster_size"]) == cluster_size
                    and (status["wsrep_local_state_comment"] == "Synced")
                )
                status.update({"check_host": host, "status": summary_status})
                resp.append(status)
            except Exception as ex:
                self.app.log.error(ex)
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
        help="ultra ping openstack",
        description="ultra ping openstack",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-vip"],
                    {
                        "help": "if true check only the vip",
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
                # client.server.list()
                client.ping()
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)
                return False
            return True

        configs = self.__get_orchestartors(instances, vip=vip)
        self.run_cmd(func, configs)

    @ex(
        help="ultra ping openstack instances using an heavy query",
        description="ultra ping openstack instances using an heavy query",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-vip"],
                    {
                        "help": "if true check only the vip",
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
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)
                return False
            return True

        configs = self.__get_orchestartors(instances, vip=vip)
        self.run_cmd(func, configs)

    @ex(
        help="ultra ping openstack instances components",
        description="ultra ping openstack instances components",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-vip"],
                    {
                        "help": "if true check only the vip",
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
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)
                return res

            try:
                client.identity.api()
                res["keystone"] = True
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)

            try:
                client.system.compute_api()
                res["compute"] = True
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)

            try:
                client.system.object_storage_api()
                res["object-storage"] = True
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)

            try:
                client.system.storage_api()
                res["block-storage"] = True
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)

            try:
                client.system.network_api()
                res["network"] = True
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)

            try:
                client.system.orchestrator_api()
                res["orchestrator"] = True
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)

            try:
                client.manila.api()
                res["manila"] = True
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)

            try:
                client.aodh.api()
                res["aodh"] = True
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)

            try:
                client.glance.api()
                res["glance"] = True
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)

            try:
                client.gnocchi.api()
                res["gnocchi"] = True
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)

            try:
                client.masakari.api()
                res["masakari"] = True
            except Exception as ex:
                self.app.log.error(ex, exc_info=True)

            return res

        configs = self.__get_orchestartors(instances, vip=vip)
        self.run_cmd(func, configs)

    @ex(help="ping openstack", description="ping openstack", arguments=OPENSTACK_ARGS())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(
        help="get openstack version",
        description="get openstack version",
        arguments=OPENSTACK_ARGS(),
    )
    def version(self):
        res = self.client.version()
        self.app.render({"version": res}, headers=["version"])

    @ex(
        help="get openstack keystone catalog",
        description="get openstack keystone catalog",
        arguments=OPENSTACK_ARGS(),
    )
    def catalog(self):
        res = self.client.get_catalog()
        self.app.render(res, details=True)

    @ex(help="get users", description="get users", arguments=OPENSTACK_ARGS())
    def sys_user_get(self):
        res = self.client.identity.user.list(detail=True)
        self.app.render(res, headers=["id", "name", "domain_id"])

    @ex(
        help="get api versions",
        description="get api versions",
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
        res = self.client.system.manila_api().get("versions", [])
        for r in res:
            r["component"] = "manila"
        resp.extend(res)
        self.app.render(
            resp,
            headers=["component", "id", "version", "min_version", "status", "updated"],
        )

    @ex(
        help="get api extensions",
        description="get api extensions",
        arguments=OPENSTACK_ARGS(),
    )
    def sys_api_extension_get(self):
        resp = []
        # res = self.client.system.compute_api().get('versions', [])
        # for r in res:
        #     r['component'] = 'compute'
        # resp.extend(res)
        # res = self.client.system.storage_api().get('versions', [])
        # for r in res:
        #     r['component'] = 'storage'
        # resp.extend(res)
        res = self.client.system.network_api_extension().get("extensions", [])
        for r in res:
            r["component"] = "network"
        resp.extend(res)
        # res = self.client.system.orchestrator_api().get('versions', [])
        # for r in res:
        #     r['component'] = 'orchestrator'
        # resp.extend(res)
        self.app.render(resp, headers=["component", "name", "alias", "description", "updated"])

    @ex(
        help="get compute services",
        description="get compute service",
        arguments=OPENSTACK_ARGS(),
    )
    def sys_compute_service_get(self):
        res = self.client.system.compute_services()
        headers = ["id", "host", "zone", "binary", "state", "status", "updated_at"]
        self.app.render(res, headers=headers, maxsize=200)

    @ex(
        help="get compute availability zones",
        description="get compute availability zones",
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
        help="get physical hosts",
        description="get physical hosts",
        arguments=OPENSTACK_ARGS(),
    )
    def sys_compute_host_get(self):
        res = self.client.system.compute_hosts()
        self.app.render(res, headers=["service", "host_name", "zone"], maxsize=200)

    @ex(
        help="set physical host status",
        description="set physical host status",
        arguments=OPENSTACK_ARGS([(["host"], {"help": "host id", "action": "store", "type": str})]),
    )
    def sys_compute_host_status(self):
        host = self.app.pargs.host
        res = self.client.system.compute_host_status(host)
        self.app.render({"msg": "set host %s status" % host})

    @ex(
        help="get compute host aggregates",
        description="get compute host aggregates",
        arguments=OPENSTACK_ARGS(),
    )
    def sys_compute_host_aggregate_get(self):
        res = self.client.system.compute_host_aggregates()
        self.app.render(
            res,
            headers=["id", "name", "availability_zone", "hosts", "created_at"],
            maxsize=200,
        )

    # @ex(
    #     help='get compute server groups',
    #     description='get compute server groups',
    #     arguments=OPENSTACK_ARGS()
    # )
    # def sys_compute_server_group_get(self):
    #     res = self.client.system.compute_server_groups()
    #     self.app.render(res, headers=['id', 'name', 'policies', 'members'], maxsize=200)

    @ex(
        help="displays extra statistical information from the machine that hosts the hypervisor through the API for "
        "the hypervisor (XenAPI or KVM/libvirt).",
        description="displays extra statistical information from the machine that hosts the hypervisor through the "
        "API for the hypervisor (XenAPI or KVM/libvirt).",
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
        help="compute hypervisors statistics",
        description="compute hypervisors statistics",
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
        help="displays extra statistical information from the machine that hosts the hypervisor through the API for "
        "the hypervisor (XenAPI or KVM/libvirt).",
        description="displays extra statistical information from the machine that hosts the hypervisor through the "
        "API for the hypervisor (XenAPI or KVM/libvirt).",
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
        help="get compute agents. Use guest agents to access files on the disk, configure networking, and run other "
        "applications and scripts in the guest while it runs. This hypervisor-specific extension is not currently "
        "enabled for KVM. Use of guest agents is possible only if the underlying service provider uses the Xen "
        "driver.",
        description="get compute agents. Use guest agents to access files on the disk, configure networking, and run "
        "other applications and scripts in the guest while it runs. This hypervisor-specific extension is "
        "not currently enabled for KVM. Use of guest agents is possible only if the underlying service "
        "provider uses the Xen driver.",
        arguments=OPENSTACK_ARGS(),
    )
    def sys_compute_agent_get(self):
        """Get"""
        res = self.client.system.compute_agents()
        self.app.render(res, headers=[], maxsize=200)

    @ex(
        help="get storage service.",
        description="get storage service.",
        arguments=OPENSTACK_ARGS(),
    )
    def sys_storage_service_get(self):
        res = self.client.system.storage_services()
        headers = ["id", "host", "zone", "binary", "state", "status", "updated_at"]
        self.app.render(res, headers=headers, maxsize=200)

    @ex(
        help="lists all hosts summary info that is not disabled",
        description="lists all hosts summary info that is not disabled",
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
        help="lists all back-end storage pools",
        description="lists all back-end storage pools",
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
        help="shows capabilities for a storage back end",
        description="shows capabilities for a storage back end",
        arguments=OPENSTACK_ARGS([(["host"], {"help": "host id", "action": "store", "type": str})]),
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
        help="get network agents",
        description="get network agents",
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
        help="get api versions",
        description="get api versions",
        arguments=OPENSTACK_ARGS(),
    )
    def sys_network_service_provider_get(self):
        """Get network service providers."""
        res = self.client.system.network_service_providers()
        self.app.render(res, headers=["service_type", "name", "default"], maxsize=200)

    @ex(
        help="get heat services",
        description="get heat services",
        arguments=OPENSTACK_ARGS(),
    )
    def sys_orchestrator_service_get(self):
        res = self.client.system.orchestrator_services()
        headers = ["id", "host", "zone", "binary", "state", "status", "updated_at"]
        self.app.render(res, headers=headers, maxsize=200)

    @ex(
        help="get keystone users",
        description="get keystone users",
        arguments=OPENSTACK_ARGS(),
    )
    def keystone_user_get(self):
        res = self.client.identity.user.list(detail=True)
        self.app.render(res, headers=["id", "name", "domain_id", "enabled"])

    @ex(
        help="get keystone roles",
        description="get keystone roles",
        arguments=OPENSTACK_ARGS(),
    )
    def keystone_role_get(self):
        res = self.client.identity.role.list(detail=False)
        self.app.render(res, headers=["id", "name"])

    @ex(help="get regions", description="get regions", arguments=OPENSTACK_ARGS())
    def region_get(self):
        res = self.client.identity.get_regions()
        self.app.render(res, headers=["id", "parent_region_id", "description"])

    @ex(
        help="get domains",
        description="get domains",
        arguments=OPENSTACK_ARGS(
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
    def domain_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.domain.get(oid)

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.domain.list(**params)
            self.app.render(res, headers=["id", "description"])

    @ex(
        help="get projects",
        description="get projects",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "project id",
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
        help="get project quotas",
        description="get project quotas",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "project id",
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
        help="set project quotas",
        description="set project quotas",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["quota_type"],
                    {
                        "help": "project quota type. can be compute, block, network, share",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["quota"],
                    {
                        "help": "project quota name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["value"],
                    {
                        "help": "project quota value",
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
        res = self.client.project.update_quota(oid, quota_type, quota, value)
        self.app.render(
            {"msg": "update quota %s %s with value %s" % (quota_type, quota, value)},
            maxsize=200,
        )

    @ex(
        help="add openstack project",
        description="add openstack project",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "project name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["domain"],
                    {
                        "help": "project domain id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "project description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": "parent project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": "enabled status",
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
        self.app.render({"msg": "create project %s" % res["id"]})

    @ex(
        help="update openstack project",
        description="update openstack project",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "project name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "project description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-domain"],
                    {
                        "help": "parent domain id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": "parent project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-enabled"],
                    {
                        "help": "enabled status",
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
        self.app.render({"msg": "update project %s" % oid})

    @ex(
        help="delete openstack project",
        description="delete openstack project",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "project id",
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
        self.app.render({"msg": "Delete project %s" % oid})

    @ex(
        help="get openstack project members",
        description="get openstack project members",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "project id",
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
        help="get openstack project default members",
        description="get openstack project default members",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "project id",
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
                print("project: (%s, %s)" % (obj.get("id"), obj.get("name")))
                for m in members:
                    print("- get user role: (%s, %s)" % (m.get("user_name"), m.get("role_name")))
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
        help="get networks",
        description="get networks",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
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
                transform = {"allocation_pools": lambda x: "%s:%s" % (x[0]["start"], x[0]["end"])}
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
        help="add openstack network",
        description="add openstack network",
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": "network name", "action": "store", "type": str}),
                (
                    ["project"],
                    {
                        "help": "parent project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-physical_network"],
                    {
                        "help": "physical network",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-segmentation_id"],
                    {
                        "help": "segmentation id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "network type. Can be flat, vlan, vxlan, or gre",
                        "action": "store",
                        "type": str,
                        "default": "vlan",
                    },
                ),
                (
                    ["-mt"],
                    {
                        "help": "the maximum transmission unit MTU",
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
        self.app.render({"msg": "add network %s" % name})

    @ex(
        help="update openstack network",
        description="update openstack network",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "network id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "network name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-shared"],
                    {
                        "help": "network shared",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-mtu"],
                    {
                        "help": "network mtu",
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
        res = self.client.network.update(oid, name=name, shared=shared, mtu=mtu)
        self.app.render({"msg": "update network %s" % oid})

    @ex(
        help="delete openstack network",
        description="delete openstack network",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
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
    def network_del(self):
        oid = self.app.pargs.id
        self.client.network.delete(oid)
        self.app.render({"msg": "Delete network %s" % oid})

    @ex(
        help="get subnets",
        description="get subnets",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "subnet id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-project"],
                    {
                        "help": "project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": "network id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                # (['-status'], {'help': 'the subnet status. Value is ACTIVE or DOWN', 'action': 'store', 'type': str,
                #                'default': None}),
                # (['-device'], {'help': 'the id of the device that uses this subnet', 'action': 'store', 'type': str,
                #                'default': None}),
                # (['-device_owner'], {'help': 'the entity type that uses this subnet. For example: - compute:nova (server '
                #                              'instance), network:dhcp (DHCP agent) - network:router_interface (router '
                #                              'interface).', 'action': 'store', 'type': str, 'default': None}),
                # (['-security_group'], {'help': 'the id of any attached security groups', 'action': 'store', 'type': str,
                #                        'default': None}),
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
                end = IPv4Address(dict_get(res, "allocation_pools.0.end"))
                start = IPv4Address(dict_get(res, "allocation_pools.0.start"))
                num = 1
                while start != end:
                    start += 1
                    num += 1

                ports = self.client.network.port.list(subnet_id=res["id"])
                report = {
                    "pool_size": num,
                    "pool_used": 0,
                    "pool_available": num,
                }
                for port in ports:
                    device_owner = port.get("device_owner")
                    # if device_owner == 'compute:twin':
                    #     report['twin'] += 1
                    if device_owner == "compute:nova":
                        report["pool_used"] += 1
                        report["pool_available"] -= 1
                    elif device_owner == "network:dhcp":
                        report["pool_used"] += 1
                        report["pool_available"] -= 1

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
                self.app.render(ports, headers=headers, fields=fields)
            else:
                self.app.render(res, details=True)
        else:
            tenant = self.app.pargs.project
            network = self.app.pargs.network
            # status = self.app.pargs.status
            # device_id = self.app.pargs.device
            # device_owner = self.app.pargs.device_owner
            # security_group = self.app.pargs.security_group
            # subnet_id = self.app.pargs.subnet
            # ip_address = self.app.pargs.ip_address
            res = self.client.network.subnet.list(tenant=tenant, network=network)
            headers = [
                "id",
                "tenant_id",
                "name",
                "network_id",
                "cidr",
                "enable_dhcp",
                "service_types",
            ]
            fields = [
                "id",
                "tenant_id",
                "name",
                "network_id",
                "cidr",
                "enable_dhcp",
                "service_types",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="add openstack subnet",
        description="add openstack subnet",
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": "subnet name", "action": "store", "type": str}),
                (
                    ["network"],
                    {
                        "help": "parent network id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-gateway"],
                    {
                        "help": "gateway ip",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["cidr"],
                    {
                        "help": "subnet cidr",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-enable-dhcp"],
                    {
                        "help": "enable dhcp",
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["dns"],
                    {
                        "help": "comma separated subnet dns",
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
            service_types=None,
        )
        self.app.render({"msg": "add subnet %s" % name})

    @ex(
        help="update openstack subnet",
        description="update openstack subnet",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "subnet id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "subnet name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "subnet description",
                        "action": "store",
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
        res = self.client.network.subnet.update(oid, name, desc)
        self.app.render({"msg": "update subnet %s" % oid})

    @ex(
        help="delete openstack subnet",
        description="delete openstack subnet",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "subnet id",
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
        self.app.render({"msg": "Delete subnet %s" % oid})

    @ex(
        help="get ports",
        description="get ports",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "port id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-project"],
                    {
                        "help": "project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": "network id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": "the port status. Value is ACTIVE or DOWN",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-device"],
                    {
                        "help": "the id of the device that uses this port",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-device_owner"],
                    {
                        "help": "the entity type that uses this port. For example: - compute:nova (server "
                        "instance), network:dhcp (DHCP agent) - network:router_interface (router "
                        "interface).",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-security_group"],
                    {
                        "help": "the id of any attached security groups",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
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
        help="add openstack port",
        description="add openstack port",
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": "port name", "action": "store", "type": str}),
                (
                    ["network"],
                    {
                        "help": "network id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subnet"],
                    {
                        "help": "subnet id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tenant"],
                    {
                        "help": "tenant id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ipaddress"],
                    {
                        "help": "ip addresses associated to subnet",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-allowed-ipaddress"],
                    {
                        "help": "allowed ip address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-allowed-macaddress"],
                    {
                        "help": "allowed ip macaddress",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-host"],
                    {
                        "help": "host id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-device_owner"],
                    {
                        "help": "device owner",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-security_groups"],
                    {
                        "help": "One or more security group id.",
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
        self.app.render({"msg": "add port %s" % res["id"]})
        self.app.render(res, details=True)

    @ex(
        help="add openstack port",
        description="add openstack port",
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
            name = "port-%s" % ip_address.replace(".", "-")
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
                print("add port %s" % port["id"])

    @ex(
        help="update openstack port",
        description="update openstack port",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "port id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "port name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "port description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-sgs"],
                    {
                        "help": "port security groups comma separated",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-allowed_ips"],
                    {
                        "help": "a comma separated list of allowed ip address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port_security_enabled"],
                    {
                        "help": "enable or disable port security",
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

        res = self.client.network.port.update(
            oid,
            name,
            desc,
            security_groups=sgs,
            allowed_address_pairs=allowed_address_pairs,
            port_security_enabled=port_security_enabled,
        )
        self.app.render({"msg": "update port %s" % oid})

    @ex(
        help="delete openstack port",
        description="delete openstack port",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "port id",
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
        self.app.render({"msg": "Delete port %s" % oid})

    @ex(
        help="get floatingips",
        description="get floatingips",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "floatingip id",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
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

    # @ex(
    #     help='add openstack floatingip',
    #     description='add openstack floatingip',
    #     arguments=OPENSTACK_ARGS([
    #         (['name'], {'help': 'floatingip name', 'action': 'store', 'type': str}),
    #         (['project'], {'help': 'parent project id', 'action': 'store', 'type': str, 'default': None}),
    #         (['physical_floatingip'], {'help': 'physical floatingip', 'action': 'store', 'type': str, 'default': None}),
    #         (['-segmentation_id'], {'help': 'segmentation id', 'action': 'store', 'type': str, 'default': None})
    #     ])
    # )
    # def floatingip_add(self):
    #     name = self.app.pargs.name
    #     tenant_id = self.app.pargs.tenant
    #     physical_floatingip = self.app.pargs.physical_floatingip
    #     segmentation_id = self.app.pargs.segmentation_id
    #     self.client.network.floatingip.create(name, tenant_id, physical_floatingip, segmentation_id=segmentation_id)
    #     self.app.render({'msg': 'add floatingip %s' % name})
    #
    # @ex(
    #     help='update openstack floatingip',
    #     description='update openstack floatingip',
    #     arguments=OPENSTACK_ARGS([
    #         (['id'], {'help': 'floatingip id', 'action': 'store', 'type': str, 'default': None}),
    #         (['-name'], {'help': 'floatingip name', 'action': 'store', 'type': str, 'default': None}),
    #         (['-desc'], {'help': 'floatingip description', 'action': 'store', 'action': StringAction, 'type': str,
    #                      'nargs': '+', 'default': None})
    #     ])
    # )
    # def floatingip_update(self):
    #     oid = self.app.pargs.id
    #     name = self.app.pargs.name
    #     desc = self.app.pargs.desc
    #     res = self.client.network.floatingip.update(oid, name, desc)
    #     self.app.render({'msg': 'update floatingip %s' % oid})

    @ex(
        help="delete openstack floatingip",
        description="delete openstack floatingip",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "floatingip id",
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
        self.app.render({"msg": "Delete floatingip %s" % oid})

    @ex(
        help="get routers",
        description="get routers",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "router id",
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
        help="add openstack router",
        description="add openstack router",
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": "router name", "action": "store", "type": str}),
                (
                    ["tenant"],
                    {
                        "help": "parent project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": "physical router",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext-subnet"],
                    {
                        "help": "external subnet",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext-ip"],
                    {
                        "help": "external ip address",
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
        self.app.render({"msg": "add router %s" % name})

    @ex(
        help="update openstack router",
        description="update openstack router",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "router id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "router name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": "physical router",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext-subnet"],
                    {
                        "help": "external subnet",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext-ip"],
                    {
                        "help": "external ip address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-routes"],
                    {
                        "help": "routes like dest:nexthop,dest:nexthop",
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
        self.app.render({"msg": "update router %s" % oid})

    @ex(
        help="reset openstack router routes",
        description="reset openstack router routes",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "router id",
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
        self.app.render({"msg": "reset router %s routes" % oid})

    @ex(
        help="rewrite existing openstack router routes",
        description="rewrite existing openstack router routes",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "router id",
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
        print("apply routes: %s" % routes)

    @ex(
        help="delete openstack router",
        description="delete openstack router",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "router id",
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
        self.app.render({"msg": "Delete router %s" % oid})

    @ex(
        help="add openstack router internal interfafe",
        description="add openstack router internal interfafe",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "router id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["subnet"],
                    {
                        "help": "subnet id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ip"],
                    {
                        "help": "intarface ip",
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
        name = "%s-%s" % (router["name"], subnet["name"])

        if subnet_id is not None or ip_address is not None:
            fixed_ips = {"subnet_id": subnet_id, "ip_address": ip_address}
            fixed_ips = [fixed_ips]
            network_id = subnet["network_id"]
            tenant_id = router["tenant_id"]

            port = self.client.network.port.create(name, network_id, fixed_ips, host_id=None, tenant_id=tenant_id)
            interface = self.client.network.router.add_internal_interface(oid, None, port=port["id"])
        else:
            interface = self.client.network.router.add_internal_interface(oid, subnet_id)
        self.app.render({"msg": "add router %s internal port %s" % (oid, interface["id"])})

    @ex(
        help="delete openstack router internal interfafe",
        description="delete openstack router internal interfafe",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "router id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["subnet"],
                    {
                        "help": "subnet id",
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
        self.app.render({"msg": "delete router %s internal port %s" % (oid, interface["id"])})

    @ex(
        help="get security_groups",
        description="get security_groups",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "security_group id",
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
        help="add openstack security group",
        description="add openstack security group",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {"help": "security_group name", "action": "store", "type": str},
                ),
                (
                    ["project"],
                    {
                        "help": "parent project id",
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
        self.app.render({"msg": "add security group %s" % name})

    @ex(
        help="update openstack security group",
        description="update openstack security group",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "security_group id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "security_group name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "security_group description",
                        "action": "store",
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
        res = self.client.network.security_group.update(oid, name, desc)
        self.app.render({"msg": "update security_group %s" % oid})

    @ex(
        help="delete openstack security_group",
        description="delete openstack security_group",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "security_group id",
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
        self.app.render({"msg": "delete security_group %s" % oid})

    @ex(
        help="get openstack security group rule",
        description="get openstack security group rule",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "security group rule id",
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
        self.client.network.security_group.get_rule(oid)
        self.app.render({"msg": "get security group rule %s" % oid})

    @ex(
        help="add openstack security group rule",
        description="add openstack security group rule",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "security group rule id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-direction"],
                    {
                        "help": "direction. Can be ingress or egress",
                        "action": "store",
                        "type": str,
                        "default": "ingress",
                    },
                ),
                (
                    ["-ethertype"],
                    {
                        "help": "Must be IPv4 or IPv6",
                        "action": "store",
                        "type": str,
                        "default": "IPv4",
                    },
                ),
                (
                    ["-port_min"],
                    {
                        "help": "port range min",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port_max"],
                    {
                        "help": "port range max",
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
                    ["-remote_ip"],
                    {
                        "help": "remote ip",
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
        self.app.render({"msg": "create security group rule %s" % oid})

    @ex(
        help="delete openstack security group rule",
        description="delete openstack security group rule",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "security group rule id",
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
        self.app.render({"msg": "delete security group rule %s" % oid})

    @ex(
        help="check openstack security_group",
        description="check openstack security_group",
        arguments=OPENSTACK_ARGS(
            [
                (["-delete"], {"help": "security_group id", "action": "store_true"}),
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
        help="get images",
        description="get images",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "image id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-owner"],
                    {"help": "owner", "action": "store", "type": str, "default": None},
                ),
                (
                    ["-visibility"],
                    {
                        "help": "image visibility: all, public, private, shared, or community",
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
            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
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
        help="get image schemas",
        description="get image schemas",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "image id",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.image.list_schemas(**params)
            headers = ["name"]
            fields = ["name"]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="add openstack image",
        description="add openstack image",
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": "image name", "action": "store", "type": str}),
                (
                    ["-disk_format"],
                    {
                        "help": "disk format e.g.: ami, ari, aki, vhd, vhdx, vmdk, raw, qcow2, vdi, ploop, iso",
                        "action": "store",
                        "type": str,
                        "default": "qcow2",
                    },
                ),
                (
                    ["-min_disk"],
                    {
                        "help": "amount of disk space in GB that is required to boot the image.",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-min_ram"],
                    {
                        "help": "amount of RAM in MB that is required to boot the image",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-visibility"],
                    {
                        "help": "image visibility: public, private, shared, or community",
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
        self.app.render({"msg": "add image %s" % name})

    # @ex(
    #     help='update openstack image',
    #     description='update openstack image',
    #     arguments=OPENSTACK_ARGS([
    #         (['id'], {'help': 'image id', 'action': 'store', 'type': str, 'default': None}),
    #         (['-name'], {'help': 'image name', 'action': 'store', 'type': str, 'default': None}),
    #         (['-desc'], {'help': 'image description', 'action': 'store', 'action': StringAction, 'type': str,
    #                      'nargs': '+', 'default': None})
    #     ])
    # )
    # def image_update(self):
    #     oid = self.app.pargs.id
    #     name = self.app.pargs.name
    #     desc = self.app.pargs.desc
    #     res = self.client.image.update(oid, name, desc)
    #     self.app.render({'msg': 'update image %s' % oid})

    @ex(
        help="upload openstack image",
        description="upload openstack image",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "image id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": "image file name",
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
        f = open(name + ".qcow2", "rb+")
        data = f.read()
        f.close()
        self.client.image.upload(oid, data)
        self.app.render({"msg": "upload image %s" % oid})

    @ex(
        help="download openstack image",
        description="download openstack image",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "image id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": "image file name",
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
        f = open(name + ".qcow2", "wb+")
        f.write(data)
        f.close()
        self.app.render({"msg": "download image %s" % oid})

    @ex(
        help="delete openstack image",
        description="delete openstack image",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "image id",
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
        self.app.render({"msg": "Delete image %s" % oid})

    @ex(
        help="get image tasks",
        description="get image tasks",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "image task id",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.image.list_tasks(**params)
            headers = ["id", "owner", "type", "status", "created_at", "updated_at"]
            fields = ["id", "owner", "type", "status", "created_at", "updated_at"]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="get flavors",
        description="get flavors",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "flavor id",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
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
        help="add flavor",
        description="add flavor",
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": "flavor name", "action": "store", "type": str}),
                (
                    ["vcpu"],
                    {"help": "vcpu", "action": "store", "type": str, "default": None},
                ),
                (
                    ["ram"],
                    {"help": "ram", "action": "store", "type": str, "default": None},
                ),
                (
                    ["disk"],
                    {"help": "disk", "action": "store", "type": str, "default": None},
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
        self.app.render({"msg": "add flavor %s" % name})

    @ex(
        help="update openstack flavor",
        description="update openstack flavor",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "flavor id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "flavor name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "flavor description",
                        "action": "store",
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
        res = self.client.flavor.update(oid, name, desc)
        self.app.render({"msg": "update flavor %s" % oid})

    @ex(
        help="delete openstack flavor",
        description="delete openstack flavor",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "flavor id",
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
        self.app.render({"msg": "Delete flavor %s" % oid})

    @ex(
        help="get flavor extra specs",
        description="get flavor extra specs",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "flavor id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-spec"],
                    {
                        "help": "flavor extra spec key",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.flavor.extra_spec_list(oid)
            self.app.render(res, details=True)

    @ex(
        help="add flavor extra spec",
        description="add flavor",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "flavor id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["spec"],
                    {
                        "help": "flavor extra spec keys. Syntax k1:v1,k2:v2",
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
        self.app.render({"msg": "add flavor %s extra spec %s" % (oid, spec_str)})

    @ex(
        help="update openstack flavor",
        description="update openstack flavor",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "flavor id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["spec"],
                    {
                        "help": "flavor extra spec key. Syntax k1:v1",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["spec_value"],
                    {
                        "help": "flavor extra spec key",
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
        res = self.client.flavor.extra_spec_update(oid, spec, spec_value)
        self.app.render({"msg": "update flavor %s extra spec %s" % (oid, spec)})

    @ex(
        help="delete openstack flavor",
        description="delete openstack flavor",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "flavor id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["spec"],
                    {
                        "help": "flavor extra spec key",
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
        self.app.render({"msg": "Delete flavor %s extra spec %s" % (oid, spec)})

    @ex(
        help="get aggregates",
        description="get aggregates",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "aggregate id",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
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
        help="add aggregate",
        description="add aggregate",
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": "aggregate name", "action": "store", "type": str}),
                (
                    ["availability_zone"],
                    {
                        "help": "availability zone",
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
        self.app.render({"msg": "add aggregate %s" % name})

    @ex(
        help="update openstack aggregate",
        description="update openstack aggregate",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "aggregate id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "aggregate name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-availability_zone"],
                    {
                        "help": "aggregate availability zone",
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
        self.app.render({"msg": "update aggregate %s" % oid})

    @ex(
        help="delete openstack aggregate",
        description="delete openstack aggregate",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "aggregate id",
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
        self.app.render({"msg": "Delete aggregate %s" % oid})

    @ex(
        help="add host to openstack aggregate",
        description="add host to openstack aggregate",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "aggregate id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["host"],
                    {
                        "help": "host_id",
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
        self.app.render({"msg": "update aggregate %s" % oid})

    @ex(
        help="delete host from openstack aggregate",
        description="delete host from openstack aggregate",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "aggregate id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["host"],
                    {
                        "help": "host_id",
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
        self.app.render({"msg": "update aggregate %s" % oid})

    @ex(
        help="update metadata to openstack aggregate",
        description="update metadata  to openstack aggregate",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "aggregate id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["metadata"],
                    {
                        "help": "key:value,key:value",
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
        self.app.render({"msg": "update aggregate %s metadata" % oid})

    @ex(
        help="get keypairs",
        description="get keypairs",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "keypair id",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.keypair.list(**params)
            headers = ["name", "public_key", "fingerprint"]
            fields = ["name", "public_key", "fingerprint"]
            self.app.render(res, headers=headers, fields=fields)

    # @ex(
    #     help='add openstack keypair',
    #     description='add openstack keypair',
    #     arguments=OPENSTACK_ARGS([
    #         (['name'], {'help': 'keypair name', 'action': 'store', 'type': str}),
    #         (['project'], {'help': 'parent project id', 'action': 'store', 'type': str, 'default': None}),
    #         (['physical_keypair'], {'help': 'physical keypair', 'action': 'store', 'type': str, 'default': None}),
    #         (['-segmentation_id'], {'help': 'segmentation id', 'action': 'store', 'type': str, 'default': None})
    #     ])
    # )
    # def keypair_add(self):
    #     name = self.app.pargs.name
    #     tenant_id = self.app.pargs.tenant
    #     physical_keypair = self.app.pargs.physical_keypair
    #     segmentation_id = self.app.pargs.segmentation_id
    #     self.client.keypair.create(name, tenant_id, physical_keypair, segmentation_id=segmentation_id)
    #     self.app.render({'msg': 'add keypair %s' % name})
    #
    # @ex(
    #     help='update openstack keypair',
    #     description='update openstack keypair',
    #     arguments=OPENSTACK_ARGS([
    #         (['id'], {'help': 'keypair id', 'action': 'store', 'type': str, 'default': None}),
    #         (['-name'], {'help': 'keypair name', 'action': 'store', 'type': str, 'default': None}),
    #         (['-desc'], {'help': 'keypair description', 'action': 'store', 'action': StringAction, 'type': str,
    #                      'nargs': '+', 'default': None})
    #     ])
    # )
    # def keypair_update(self):
    #     oid = self.app.pargs.id
    #     name = self.app.pargs.name
    #     desc = self.app.pargs.desc
    #     res = self.client.keypair.update(oid, name, desc)
    #     self.app.render({'msg': 'update keypair %s' % oid})

    @ex(
        help="delete openstack keypair",
        description="delete openstack keypair",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "keypair id",
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
        self.app.render({"msg": "Delete keypair %s" % oid})

    @ex(
        help="get server groups",
        description="get server groups",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "server group id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-size"],
                    {
                        "help": "number of item to return",
                        "action": "store",
                        "type": int,
                        "default": 20,
                    },
                ),
                (
                    ["-page"],
                    {
                        "help": "page to return",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
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
        help="add openstack server group",
        description="add openstack server group",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {"help": "server group name", "action": "store", "type": str},
                ),
                (
                    ["-policy"],
                    {
                        "help": "one policy name to associate with the server group. Policy names are:"
                        ' "anti-affinity" servers in this group must be scheduled to different hosts,'
                        ' "affinity" servers in this group must be scheduled to the same host, '
                        ' "soft-anti-affinity" servers in this group should be scheduled to different '
                        "hosts if possible, but if not possible then they should still be scheduled instead "
                        'of resulting in a build failure, "soft-affinity" servers in this group should be '
                        "scheduled to the same host if possible, but if not possible then they should still "
                        "be scheduled instead of resulting in a build failure",
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
        self.app.render({"msg": "add server group %s" % name})

    @ex(
        help="delete openstack server group",
        description="delete openstack server group",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server group id",
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
        self.app.render({"msg": "Delete server group %s" % oid})

    @ex(
        help="add openstack server group member",
        description="add openstack server group member",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server group id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["server"],
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
    def server_group_member_add(self):
        oid = self.app.pargs.id
        server_id = self.app.pargs.server

        # check server and server group exist
        sg = self.client.server_group.get(oid)
        self.client.server.get(server_id)
        if server_id in sg.get("members", []):
            raise Exception("server %s already in server group %s" % (server_id, oid))

        date = format_date(datetime.now(), format="%Y-%m-%d %H:%M:%S")

        hosts = self.mariadb.get("hosts", [])
        port = self.mariadb.get("port")
        user = {"name": self.mariadb.get("user"), "password": self.mariadb.get("pwd")}
        db = "nova_api"

        def statements(conn):
            result = conn.execute("SELECT * from nova_api.instance_groups WHERE uuid='%s';" % oid)
            group = result.fetchall()
            if len(group) == 1:
                group_id = group[0][2]
                conn.execute(
                    "INSERT INTO `instance_group_member`(created_at, instance_uuid, group_id) "
                    "values ('%s', '%s','%s');" % (date, server_id, group_id)
                )
            return True

        server = self.__get_mariadb_engine(hosts[0], port, user, db)
        server.exec_statements(statements)
        self.app.render({"msg": "add server %s in server group %s" % (server_id, oid)})

    @ex(
        help="delete openstack server group member",
        description="delete openstack server group member",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "server group id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["server"],
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
    def server_group_member_del(self):
        oid = self.app.pargs.id
        server_id = self.app.pargs.server

        # check server and server group exist
        sg = self.client.server_group.get(oid)
        self.client.server.get(server_id)
        if server_id not in sg.get("members", []):
            raise Exception("server %s not in server group %s" % (server_id, oid))

        hosts = self.mariadb.get("hosts", [])
        port = self.mariadb.get("port")
        user = {"name": self.mariadb.get("user"), "password": self.mariadb.get("pwd")}
        db = "nova_api"

        def statements(conn):
            result = conn.execute("SELECT * from nova_api.instance_groups WHERE uuid='%s';" % oid)
            group = result.fetchall()
            if len(group) == 1:
                group_id = group[0][2]
                conn.execute("DELETE FROM nova_api.instance_group_member WHERE instance_uuid='%s';" % server_id)
            return True

        server = self.__get_mariadb_engine(hosts[0], port, user, db)
        server.exec_statements(statements)
        self.app.render({"msg": "delete server %s from server group %s" % (server_id, oid)})

    @ex(
        help="get servers",
        description="get servers",
        arguments=OPENSTACK_ARGS(
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
                    ["-host"],
                    {
                        "help": "compute node name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": "server status",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-updated_at"],
                    {
                        "help": "Filter the server list result by a date and time stamp when the instance was "
                        "updated. The date and timestamp format is ISO 8601: "
                        "CCYY-MM-DDThh:mm:ss±hh:mm. For example, 2015-08-27T09:49:58-05:00",
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
            res = server.list(
                detail=True,
                host=pargs.host,
                status=pargs.status,
                updated_at=pargs.updated_at,
                all_tenants=all_tenants,
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
        help="print host status",
        description="print host status",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-host"],
                    {
                        "help": "node name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-loop"],
                    {
                        "help": "if value > 1 enable query loop",
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
                    # if i['id'] == 'e062ad5e-5973-4dd4-a5fc-f9bcb474aa2e':
                    #     continue
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
                print("host: %s, server: %s" % (host, resp))
                if loop > 1:
                    sleep(5)

    @ex(
        help="start servers for a host",
        description="start servers for a host",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-host"],
                    {
                        "help": "node name",
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
                print("start server %s" % i["id"])
                sleep(2)
            elif status == "ERROR":
                self.client.server.reset_state(i["id"], "error")
                print("reset state server %s" % i["id"])
                self.client.server.reboot(i["id"])
                print("hard reboot server %s" % i["id"])
                sleep(2)
            elif status == "REBUILD":
                self.client.server.reset_state(i["id"], "error")
                print("reset state server %s" % i["id"])
                self.client.server.reboot(i["id"])
                print("hard reboot server %s" % i["id"])
                sleep(2)
            elif i["OS-EXT-STS:power_state"] in [0, 3]:
                self.client.server.reset_state(i["id"], "error")
                print("reset state server %s" % i["id"])
                self.client.server.reboot(i["id"])
                print("hard reboot server %s" % i["id"])
                sleep(2)
            elif status == "ACTIVE":
                print("server %s OK" % i["id"])

    @ex(
        help="reset servers state for a host",
        description="reset servers state for a host",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-host"],
                    {
                        "help": "node name",
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
                print("hard reboot server %s" % i["id"])
            # if status == 'SHUTOFF':
            #     self.client.server.start(i['id'])
            #     print('start server %s' % i['id'])
            sleep(2)

    @ex(
        help="ping servers for a host",
        description="ping servers for a host",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-host"],
                    {
                        "help": "node name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "vm name",
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
        name = self.app.pargs.name
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

            # status = i['status']
            # if status == 'SHUTOFF':
            #     self.client.server.start(i['id'])
            #     print('start server %s' % i['id'])
            #     sleep(5)
            print("ping -c 3 %s" % addr)

    @ex(
        help="add openstack server",
        description="add openstack server",
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": "server name", "action": "store", "type": str}),
                (
                    ["-flavor"],
                    {
                        "help": "flavor reference id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-boot_volume"],
                    {
                        "help": "boot volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-admin_pass"],
                    {
                        "help": "admin password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-description"],
                    {
                        "help": "description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-security_groups"],
                    {
                        "help": "security groups",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-networks"],
                    {
                        "help": "list of networks",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-config_drive"],
                    {
                        "help": "list of networks",
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-availability_zone"],
                    {
                        "help": "availability zone",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-image"],
                    {
                        "help": "The UUID of the image to use for your server instance.",
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
                {"uuid": a, "tag": "nic%s" % e} for e, a in enumerate(self.app.pargs.networks.split(","))
            ]
        res = self.client.server.create(name, flavor, **params)
        self.app.render({"msg": "add server %s with id %s" % (name, res["id"])})

    @ex(
        help="update openstack server",
        description="update openstack server",
        arguments=OPENSTACK_ARGS(
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
                    ["-name"],
                    {
                        "help": "server name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "server description",
                        "action": "store",
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
        res = self.client.server.update(oid, name, desc, **params)
        self.app.render({"msg": "update server %s" % oid})

    @ex(
        help="rebuild openstack server",
        description="rebuild openstack server",
        arguments=OPENSTACK_ARGS(
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
                    ["-image"],
                    {
                        "help": "The UUID of the image to use for your server instance.",
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
        res = self.client.server.rebuild(oid, **params)
        self.app.render({"msg": "update server %s" % oid})

    @ex(
        help="delete openstack server",
        description="delete openstack server",
        arguments=OPENSTACK_ARGS(
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
        self.client.server.delete(oid)
        self.app.render({"msg": "Delete server %s" % oid})

    @ex(
        help="reset state of openstack server",
        description="reset state of  openstack server",
        arguments=OPENSTACK_ARGS(
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
                    ["state"],
                    {
                        "help": "server state",
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
        obj = self.client.server.reset_state(oid, state)

    @ex(
        help="get openstack server diagnostics",
        description="get openstack server diagnostics",
        arguments=OPENSTACK_ARGS(
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
    def server_diagnostics(self):
        oid = self.app.pargs.id
        obj = self.client.server.diagnostics(oid)
        res = obj
        self.app.render(res, details=True)

    @ex(
        help="get openstack server console",
        description="get openstack server console",
        arguments=OPENSTACK_ARGS(
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
        res = self.client.server.get_vnc_console(oid)
        self.app.render([res], headers=["type", "url"], maxsize=400)
        # sh.firefox(res.get('url'))

    @ex(
        help="get openstack server console output",
        description="get openstack server console output",
        arguments=OPENSTACK_ARGS(
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
    def server_console_output(self):
        oid = self.app.pargs.id
        res = self.client.server.get_console_output(oid)
        print(res)

    @ex(
        help="get openstack server ports",
        description="get openstack server ports",
        arguments=OPENSTACK_ARGS(
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
    def server_port_get(self):
        oid = self.app.pargs.id
        res = self.client.server.get_port_interfaces(oid)
        headers = ["name", "state", "port_id", "net_id", "ip_address"]
        fields = ["name", "port_state", "port_id", "net_id", "fixed_ips.0.ip_address"]
        self.app.render(res, headers=headers, fields=fields, maxsize=80)

    @ex(
        help="add openstack server port",
        description="add openstack server port",
        arguments=OPENSTACK_ARGS(
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
                    ["-port"],
                    {
                        "help": "port id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-net"],
                    {
                        "help": "network id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ipaddress"],
                    {
                        "help": "ip address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subnet"],
                    {
                        "help": "subnet id",
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
        msg = "Add network interface to server %s" % oid
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="delete openstack server port",
        description="delete openstack server port",
        arguments=OPENSTACK_ARGS(
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
                    ["port"],
                    {
                        "help": "port id",
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
        msg = "Delete port %s from server %s" % (port_id, oid)
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="get openstack server security group",
        description="get openstack server security group",
        arguments=OPENSTACK_ARGS(
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
        res = self.client.server.security_groups(oid)
        headers = ["id", "project", "name", "desc"]
        fields = ["id", "tenant_id", "name", "description"]
        self.app.render(res, headers=headers, fields=fields, maxsize=80)

    @ex(
        help="add openstack server security group",
        description="add openstack server security group",
        arguments=OPENSTACK_ARGS(
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
                    ["sg"],
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
        security_group = self.app.pargs.sg
        self.client.server.add_security_group(oid, security_group)
        msg = "Add security group %s to server %s" % (security_group, oid)
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="delete openstack server security group",
        description="delete openstack server security group",
        arguments=OPENSTACK_ARGS(
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
                    ["sg"],
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
        security_group = self.app.pargs.sg
        self.client.server.remove_security_group(oid, security_group)
        msg = "Delete security group %s from server %s" % (security_group, oid)
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="get openstack server volumes",
        description="get openstack server volumes",
        arguments=OPENSTACK_ARGS(
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
    def server_volume_get(self):
        oid = self.app.pargs.id
        res = self.client.server.get_volumes(oid)
        headers = ["id", "server-id", "device"]
        fields = ["volumeId", "serverId", "device"]
        self.app.render(res, headers=headers, fields=fields, maxsize=80)

    @ex(
        help="add openstack server volume",
        description="add openstack server volume",
        arguments=OPENSTACK_ARGS(
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
                    ["volume_id"],
                    {
                        "help": "volume id (see volume-add to create it.)",
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
        msg = "Add volume %s to server %s" % (volume, oid)
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="delete openstack server volume",
        description="delete openstack server volume",
        arguments=OPENSTACK_ARGS(
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
                    ["volume"],
                    {
                        "help": "volume id",
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
        msg = "Delete volume %s from server %s" % (volume, oid)
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="get openstack server metadata",
        description="get openstack server metadata",
        arguments=OPENSTACK_ARGS(
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
    def server_metadata_get(self):
        oid = self.app.pargs.id
        res = self.client.server.get_metadata(oid)
        res = [{"key": k, "value": v} for k, v in res.items()]
        headers = ["key", "value"]
        fields = ["key", "value"]
        self.app.render(res, headers=headers, fields=fields, maxsize=80)

    @ex(
        help="add openstack server metadata",
        description="add openstack server metadata",
        arguments=OPENSTACK_ARGS(
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
                    ["volume"],
                    {
                        "help": "volume id",
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
        res = self.client.server.add_metadata(oid, metadata)
        msg = "Add metadata %s to server %s" % (metadata, oid)
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="delete openstack server metadata",
        description="delete openstack server metadata",
        arguments=OPENSTACK_ARGS(
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
                    ["volume"],
                    {
                        "help": "volume id",
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
        key = self.app.pargs.key
        res = self.client.server.remove_metadata(oid, key)
        msg = "Delete metadata %s from server %s" % (key, oid)
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="get server actions",
        description="get server actions",
        arguments=OPENSTACK_ARGS(
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
                    ["-action"],
                    {
                        "help": "action id",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
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
        bar = rotating_bar()
        while status not in required_status:
            server = self.__get_server_info(oid)
            status = server.get("status")
            if func is not None:
                func(server)
            else:
                # stdout.write(".")
                stdout.write(next(bar))
                stdout.flush()
            sleep(1)

    @ex(
        help="start server",
        description="start server",
        arguments=OPENSTACK_ARGS(
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
        obj = self.client.server.start(oid)
        msg = "Start server %s" % oid
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="stop server",
        description="stop server",
        arguments=OPENSTACK_ARGS(
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
        obj = self.client.server.stop(oid)
        msg = "Stop server %s" % oid
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="reboot server",
        description="reboot server",
        arguments=OPENSTACK_ARGS(
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
    def server_reboot(self):
        oid = self.app.pargs.id
        self.client.server.reset_state(oid, "active")
        obj = self.client.server.reboot(oid)
        msg = "Reboot server %s" % oid
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="pause server",
        description="pause server",
        arguments=OPENSTACK_ARGS(
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
    def server_pause(self):
        oid = self.app.pargs.id
        obj = self.client.server.pause(oid)
        msg = "Pause server %s" % oid
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="unpause server",
        description="unpause server",
        arguments=OPENSTACK_ARGS(
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
    def server_unpause(self):
        oid = self.app.pargs.id
        obj = self.client.server.unpause(oid)
        msg = "Unpause server %s" % oid
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="lock server",
        description="lock server",
        arguments=OPENSTACK_ARGS(
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
    def server_lock(self):
        oid = self.app.pargs.id
        obj = self.client.server.lock(oid)
        msg = "Lock server %s" % oid
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="unlock server",
        description="unlock server",
        arguments=OPENSTACK_ARGS(
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
    def server_unlock(self):
        oid = self.app.pargs.id
        obj = self.client.server.unlock(oid)
        msg = "Unlock server %s" % oid
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="suspend server",
        description="suspend server",
        arguments=OPENSTACK_ARGS(
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
    def server_suspend(self):
        oid = self.app.pargs.id
        obj = self.client.server.suspend(oid)
        msg = "Suspend server %s" % oid
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="resume server",
        description="resume server",
        arguments=OPENSTACK_ARGS(
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
    def server_resume(self):
        oid = self.app.pargs.id
        obj = self.client.server.resume(oid)
        msg = "Resume server %s" % oid
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="reset server state",
        description="reset server state",
        arguments=OPENSTACK_ARGS(
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
                    ["state"],
                    {
                        "help": "server state",
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
        obj = self.client.server.reset_state(oid, state)
        msg = "Reset state for server %s to %s" % (oid, state)
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="set server flavor",
        description="set server flavor",
        arguments=OPENSTACK_ARGS(
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
                    ["flavor"],
                    {
                        "help": "flavor id",
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
        obj = self.client.server.set_flavor(oid, flavor)
        # obj = self.client.server.confirm_set_flavor(oid)
        msg = "Resize server %s using flavor %s" % (oid, flavor)
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="server migration list",
        description="server migration list",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
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
        help="force server migration",
        description="force server migration",
        arguments=OPENSTACK_ARGS(
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
                    ["migration_id"],
                    {
                        "help": "server migration id",
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
        res = self.client.server.force_migration(oid, migration_id)
        self.app.render({"msg": "force server %s migration %s" % (oid, migration_id)})

    @ex(
        help="abort server migration",
        description="abort server migration",
        arguments=OPENSTACK_ARGS(
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
                    ["migration_id"],
                    {
                        "help": "server migration id",
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
        res = self.client.server.abort_migration(oid, migration_id)
        self.app.render({"msg": "abort server %s migration %s" % (oid, migration_id)})

    @ex(
        help="migrate server",
        description="migrate server",
        arguments=OPENSTACK_ARGS(
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
                    ["-host"],
                    {
                        "help": "host id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-live"],
                    {
                        "help": "if true enable live migration",
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
            obj = self.client.server.migrate(oid, host)
        else:
            obj = self.client.server.live_migrate(oid, host)

        def print_host(server):
            print(server.get("OS-EXT-SRV-ATTR:host"))

        self.__wait_for_server_status(oid, print_host)
        self.app.render({"msg": "Migrate server %s" % oid})

    @ex(
        help="create image from a server",
        description="server create image",
        arguments=OPENSTACK_ARGS(
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
                        "help": "image name",
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
        self.app.render({"msg": "Creating image %s from server %s" % (res["image_id"], oid)})

    @ex(
        help="migrate servers",
        description="migrate servers",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["from_host"],
                    {
                        "help": "starting host",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-to_host"],
                    {
                        "help": "destination host",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-live"],
                    {
                        "help": "if true enable live migration",
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
                obj = self.client.server.migrate(oid, to_host)
            else:
                obj = self.client.server.live_migrate(oid, to_host)

            def print_host(server):
                print(server.get("OS-EXT-SRV-ATTR:host"))

            self.__wait_for_server_status(oid, print_host)
            self.app.render({"msg": "Migrate server %s" % oid})

    #
    # stack
    #
    # def wait_stack_create(self, name, oid):
    #     res = self.client.heat.stack.get(stack_name=name, oid=oid)
    #     status = res['stack_status']
    #
    #     while status == 'CREATE_IN_PROGRESS':
    #         self.self.app.log.debug(status)
    #         sleep(1)
    #         res = self.client.heat.stack.get(stack_name=name, oid=oid)
    #         status = res['stack_status']
    #         print status
    #
    # def wait_stack_delete(self, name, oid):
    #     res = self.client.heat.stack.get(stack_name=name, oid=oid)
    #     status = res['stack_status']
    #
    #     while status == 'DELETE_IN_PROGRESS':
    #         self.app.log.debug(status)
    #         sleep(1)
    #         res = self.client.heat.stack.get(stack_name=name, oid=oid)
    #         status = res['stack_status']
    #         print('.')

    def __get_stack(self, oid):
        obj = self.client.heat.stack.list(oid=oid)
        if len(obj) <= 0:
            raise Exception("Stack %s not found" % oid)
        obj = obj[0]
        return obj

    @ex(
        help="get stacks",
        description="get stacks",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "stack id",
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
                raise Exception("Stack %s was not found" % oid)
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
        help="add openstack stack",
        description="add openstack stack",
        arguments=OPENSTACK_ARGS(
            [
                (["name"], {"help": "stack name", "action": "store", "type": str}),
                (
                    ["project"],
                    {
                        "help": "parent project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["physical_stack"],
                    {
                        "help": "physical stack",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-segmentation_id"],
                    {
                        "help": "segmentation id",
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
        segmentation_id = self.app.pargs.segmentation_id
        self.client.heat.stack.create(name, tenant_id, physical_stack, segmentation_id=segmentation_id)
        self.app.render({"msg": "add stack %s" % name})

    @ex(
        help="update openstack stack",
        description="update openstack stack",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "stack id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "stack name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "stack description",
                        "action": "store",
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
        res = self.client.heat.stack.update(oid, name, desc)
        self.app.render({"msg": "update stack %s" % oid})

    @ex(
        help="delete openstack stack",
        description="delete openstack stack",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "stack id",
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
        res = {"msg": "Delete stack %s" % oid}
        self.app.render(res, headers=["msg"])

    @ex(
        help="get heat stack resources",
        description="get heat stack resources",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "stack id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-resource"],
                    {
                        "help": "stack resource name",
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
            self.app.render(res, headers=headers, fields=fields, maxsize=40)
        else:
            self.app.render(res[0], details=True, maxsize=200)

    @ex(
        help="mark the specified resource in the stack as unhealthy",
        description="mark the specified resource in the stack as unhealthy",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "stack id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-resource"],
                    {
                        "help": "stack resource name",
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
        res = {"msg": "mark the resource %s in the stack as unhealthy" % resource}
        self.app.render(res, headers=["msg"], maxsize=200)

    #
    # share
    #
    @ex(
        help="get manila share types",
        description="get manila share types",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "share type id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "share type description",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
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
                    res.append("%s=%s" % (k, v))
                return "\n".join(res)

            transform = {
                "extra_specs": extra_specs_func,
                "required_extra_specs": extra_specs_func,
            }
            self.app.render(res, headers=headers, fields=fields, maxsize=200, transform=transform)

    @ex(
        help="get manila share limits",
        description="get manila share limits",
        arguments=OPENSTACK_ARGS(),
    )
    def share_limit_get(self):
        res = self.client.manila.limits().get("limits").get("absolute")
        self.app.render(res, details=True)

    @ex(
        help="get manila share messages",
        description="get manila share messages",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "share id",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
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
        help="get manila shares",
        description="get manila shares",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "share id",
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
        help="add manila share",
        description="add manila share",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "share name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["size"],
                    {
                        "help": "share size in GB",
                        "action": "store",
                        "type": int,
                        "default": 1,
                    },
                ),
                (
                    ["proto"],
                    {
                        "help": "share protocol (NFS, CIFS, GlusterFS, HDFS, or CephFS. CephFS)",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["type"],
                    {
                        "help": "share type id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-snapshot"],
                    {
                        "help": "share snapshot id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group"],
                    {
                        "help": "share group id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": "the id of a share network where the share server exists or will be created. "
                        "If is None and you provide a snapshot_id, the network value from the snapshot "
                        "is used",
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
        self.app.render({"msg": "add manila share %s" % res["id"]})

    @ex(
        help="delete manila shares",
        description="delete manila shares",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "share id",
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
        self.app.render({"msg": "delete manila share %s" % oid})

    @ex(
        help="extend manila share size",
        description="extend manila share size",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "share id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["size"],
                    {
                        "help": "new size of the share, in GBs.",
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
        self.app.render({"msg": "Extend share %s to %s" % (oid, new_size)})

    @ex(
        help="shrink manila share size",
        description="shrink manila share size",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "share id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["size"],
                    {
                        "help": "new size of the share, in GBs.",
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
        self.app.render({"msg": "Shrink share %s to %s" % (oid, new_size)})

    #
    # share network
    #
    @ex(
        help="get manila share networks",
        description="get manila share networks",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "share network id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": "neutron network id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subnet"],
                    {
                        "help": "neutron subnet id",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
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
        help="add manila share network",
        description="add manila share network",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "share network name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "share network description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["network"],
                    {
                        "help": "The UUID of a neutron network when setting up or updating a share network subnet "
                        "with neutron. Specify both a neutron network and a neutron subnet that belongs "
                        "to that neutron network.",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["subnet"],
                    {
                        "help": "The UUID of the neutron subnet when setting up or updating a share network subnet "
                        "with neutron. Specify both a neutron network and a neutron subnet that belongs to "
                        "that neutron network.",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-availability_zone"],
                    {
                        "help": "The UUID or name of an availability zone for the share network subnet.",
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
        self.app.render({"msg": "add manila share network %s" % name})

    @ex(
        help="update manila share network",
        description="update manila share network",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "share network id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "share network name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "share network description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-network"],
                    {
                        "help": "The UUID of a neutron network when setting up or updating a share network subnet "
                        "with neutron. Specify both a neutron network and a neutron subnet that belongs "
                        "to that neutron network.",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subnet"],
                    {
                        "help": "The UUID of the neutron subnet when setting up or updating a share network subnet "
                        "with neutron. Specify both a neutron network and a neutron subnet that belongs to "
                        "that neutron network.",
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
        self.app.render({"msg": "update manila share network %s" % oid})

    @ex(
        help="delete manila share networks",
        description="delete manila share networks",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "share network id",
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
        self.app.render({"msg": "delete manila share %s" % oid})

    @ex(
        help="add security service to share network",
        description="add security service to share network",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "share network id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["service"],
                    {
                        "help": "security service id",
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
        self.app.render({"msg": "add security service to share network %s" % oid})

    @ex(
        help="delete security service from share network",
        description="delete security service from share network",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "share network id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["service"],
                    {
                        "help": "security service id",
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
        self.app.render({"msg": "delete security service from share network %s" % oid})

    #
    # share server
    #
    @ex(
        help="get manila share servers",
        description="get manila share servers",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "share server id",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
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
        help="delete manila share servers",
        description="delete manila share servers",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "share server id",
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
        self.app.render({"msg": "delete manila share %s" % oid})

    #
    # share grant
    #
    @ex(
        help="add manila share access grant",
        description="add manila share access grant",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "share id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-level"],
                    {
                        "help": "the access level to the share. rw: Read and write (RW) access. ro: Read-only (RO) "
                        "access.",
                        "action": "store",
                        "type": str,
                        "default": "rw",
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "the access rule type. ip: Authenticates an instance through its IP address. cert: "
                        "Authenticates an instance through a TLS certificate. user: Authenticates by a user "
                        "or group name.",
                        "action": "store",
                        "type": str,
                        "default": "ip",
                    },
                ),
                (
                    ["-to"],
                    {
                        "help": "the value that defines the access. ip: A valid format is XX.XX.XX.XX or XX.XX.XX.XX/XX."
                        " For example 0.0.0.0/0. cert: Specify the TLS identity as the IDENTKEY. A valid value "
                        "is any string up to 64 characters long in the common name (CN) of the certificate. The "
                        "meaning of a string depends on its interpretation. user: A valid value is an "
                        "alphanumeric string that can contain some special characters and is from 4 to 32 "
                        "characters long.",
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
        help="remove manila share access grant",
        description="remove manila share access grant",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "share id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["access_id"],
                    {
                        "help": "grant id",
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
        self.app.render({"msg": "Revoke access %s to share %s" % (oid, access_id)})

    @ex(
        help="reset manila share status",
        description="reset manila share status",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "share id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": "the share access status, which is new, error, active",
                        "action": "store",
                        "type": str,
                        "default": "active",
                    },
                ),
            ]
        ),
    )
    def share_status_reset(self):
        oid = self.app.pargs.id
        status = self.app.pargs.status
        self.client.manila.share.action.reset_status(oid, status)
        self.app.render({"msg": "Reset status of share %s to %s" % (oid, status)})

    #
    # share snapshot
    #
    @ex(
        help="revert manila share to snapshot",
        description="revert manila share to snapshot",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "share id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["snapshot_id"],
                    {
                        "help": "the share snapshot id",
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
        self.app.render({"msg": "Revert share %s to snapshot_id %s" % (oid, snapshot_id)})

    #
    # volume messages
    #
    @ex(
        help="get volume messages",
        description="get volume messages",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "volume message id",
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
        help="get all back-end storage pools that are known to the scheduler service",
        description="get all back-end storage pools that are known to the scheduler service",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-hostname"],
                    {
                        "help": "backend storage pool hostname",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-backendname"],
                    {
                        "help": "volume backend name",
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
        help="get volumes",
        description="get volumes",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-limit"],
                    {
                        "help": "requests a page size of items. Use -1 to list all the volume",
                        "action": "store",
                        "type": int,
                        "default": 20,
                    },
                ),
                (
                    ["-offset"],
                    {
                        "help": "used in conjunction with limit to return a slice of items. offset is where to "
                        "start in the list",
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
            print("Page: %s" % offset)
            print("Count: %s" % limit)
            print("Total: %s" % self.client.volume_v3.volume_count)
            print("Order:")
            self.app.render(res, headers=headers, fields=fields)

    # @ex(
    #     help='get volumes which are available to manage',
    #     description='get volumes which are available to manage',
    #     arguments=OPENSTACK_ARGS([
    #         (['host'], {'help': 'Cinder host on which to list manageable volumes; takes the form: '
    #                             'host@backend-name#pool', 'action': 'store', 'type': str}),
    #         (['-limit'], {'help': 'requests a page size of items', 'action': 'store', 'type': int, 'default': 20}),
    #         (['-offset'], {'help': 'used in conjunction with limit to return a slice of items. offset is where to '
    #                                'start in the list', 'action': 'store', 'type': str, 'default': 0}),
    #     ])
    # )
    # def volume_manageable_get(self):
    #     host = self.app.pargs.host
    #     limit = self.app.pargs.limit
    #     offset = self.app.pargs.offset
    #     params = {'limit': limit, 'offset': offset, 'host': host}
    #     res = self.client.volume_v3.manageable_volumes(**params)
    #     headers = ['id', 'name', 'safe_to_manage', 'reason_not_safe', 'size']
    #     fields = ['cinder_id', 'reference.source-name', 'safe_to_manage', 'reason_not_safe', 'size']
    #     print('Page: %s' % offset)
    #     print('Count: %s' % limit)
    #     print('Total: %s' % limit)
    #     print('Order:')
    #     self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="add volume",
        description="add volume",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "volume name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["size"],
                    {
                        "help": "volume size in Gb",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "volume type",
                        "action": "store",
                        "type": str,
                        "default": "nfsgold",
                    },
                ),
                (
                    ["-snapshot_id"],
                    {
                        "help": "the snapshot id",
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
        self.app.render({"msg": "Created volume %s, id %s, size %s Gb" % (name, res["id"], res["size"])})

    @ex(
        help="migrate volume",
        description="migrate volume",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["volume_id"],
                    {
                        "help": "volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["host"],
                    {"help": "host", "action": "store", "type": str, "default": None},
                ),
                (
                    ["-force_host_copy"],
                    {
                        "help": "force_host_copy",
                        "action": "store",
                        "type": str,
                        "default": "False",
                    },
                ),
                (
                    ["-lock_volume"],
                    {
                        "help": "lock_volume",
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
        res = self.client.volume_v3.migrate(volume_id, host, force_host_copy=force_host_copy, lock_volume=lock_volume)
        self.app.render({"msg": "Migrated volume %s on host %s" % (volume_id, host)})

    @ex(
        help="volume api extensions",
        description="list volume Block Storage API extensions",
        arguments=OPENSTACK_ARGS([]),
    )
    def volume_api_extensions(self):
        res = self.client.volume_v3.api_extensions()
        headers = ["alias", "name", "description", "namespace", "links", "updated"]
        fields = ["alias", "name", "description", "namespace", "links", "updated"]
        self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="update volume",
        description="update volume",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "volume name",
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
        msg = "Update volume %s" % oid
        self.app.render({"msg": msg}, headers=["msg"], maxsize=200)

    @ex(
        help="delete volume",
        description="delete volume",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": "force delete",
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
        self.app.render({"msg": "Delete volume %s" % oid})

    @ex(
        help="extend volume",
        description="extend volume",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (["size"], {"help": "new volume size", "action": "store", "type": str}),
            ]
        ),
    )
    def volume_extend(self):
        oid = self.app.pargs.id
        size = self.app.pargs.size
        self.client.volume_v3.extend(oid, size)
        self.app.render({"msg": "extend volume %s" % oid})

    @ex(
        help="unmanage volume",
        description="unmanage volume",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "volume id",
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
        self.app.render({"msg": "unmanage volume %s" % oid})

    @ex(
        help="manage volume",
        description="manage volume",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["source_volume_id"],
                    {
                        "help": "source volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                # (['source_volume_name'], {'help': 'source volume name', 'action': 'store', 'type': str, 'default': None}),
                (
                    ["name"],
                    {
                        "help": "new volume name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "new volume description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["volume_type"],
                    {
                        "help": "volume type id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-bootable"],
                    {
                        "help": "bootable value",
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-host"],
                    {
                        "help": "source volume host",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-cluster"],
                    {
                        "help": "source volume cluster",
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
        # source_volume_name = self.app.pargs.source_volume_name
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        volume_type = self.app.pargs.volume_type
        bootable = str2bool(self.app.pargs.bootable)
        host = self.app.pargs.host
        cluster = self.app.pargs.cluster
        res = self.client.volume_v3.manage(
            source_volume_id,
            name,
            volume_type,
            bootable=bootable,
            desc=desc,
            availability_zone="nova",
            host=host,
            cluster=cluster,
        )
        self.app.render({"msg": "manage volume %s" % source_volume_id})

    @ex(
        help="set volume status",
        description="set volume status",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": "volume id",
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
        self.app.render({"msg": "Reset volume %s status to %s" % (oid, status)})

    @ex(
        help="clone volume",
        description="clone volume",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "volume name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["volume"],
                    {
                        "help": "volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["project"],
                    {
                        "help": "project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-volume_type"],
                    {
                        "help": "the volume type id",
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
        self.app.render({"msg": "Clone volume %s" % volume_id})

    @ex(
        help="get volume types",
        description="get volume types",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "volume type id",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.volume_v3.type.list(**params)
            headers = ["id", "name", "is_public", "qos_specs_id", "extra_specs"]
            fields = ["id", "name", "is_public", "qos_specs_id", "extra_specs"]
            self.app.render(res, headers=headers, fields=fields, maxsize=200)

    @ex(
        help="change volume type",
        description="change volume type",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["volume_type"],
                    {
                        "help": "volume type id",
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
        bar = rotating_bar()

        snapshots = self.client.volume_v3.snapshot.list(volume_id=oid)
        for snapshot in snapshots:
            self.client.volume_v3.snapshot.delete(snapshot["id"])
            try:
                while True:
                    self.client.volume_v3.snapshot.get(snapshot["id"])
                    # stdout.write(".")
                    stdout.write(next(bar))
                    stdout.flush()
                    sleep(1)
            except:
                self.app.render({"msg": "remove snapshot %s" % snapshot["id"]})

        self.client.volume_v3.change_type(oid, volume_type)
        res = self.client.volume_v3.get(oid)
        status = res["status"]
        while status == "retyping":
            stdout.write(".")
            stdout.flush()
            sleep(2)
            res = self.client.volume_v3.get(oid)
            status = res["status"]

        self.app.render({"msg": "change volume %s type to %s" % (oid, volume_type)})

    @ex(
        help="get volume attachments",
        description="get volume attachments",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-instance"],
                    {
                        "help": "instance id",
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
        help="attach volume from server",
        description="attach volume from server",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["instance"],
                    {
                        "help": "instance id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["mountpoint"],
                    {
                        "help": "instance mountpoint. ex. /dev/vda",
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
        self.app.render({"msg": "attach volume %s" % oid})

    @ex(
        help="detach volume from server",
        description="detach volume from server",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "volume id",
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
        res = self.client.volume_v3.detach_volume_from_server(oid, attachment[0]["id"])
        self.app.render({"msg": "detach volume %s" % oid})

    @ex(
        help="update volume",
        description="update volume",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-bootable"],
                    {
                        "help": "bootable status",
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
        msg = "Update volume %s bootable status" % oid
        self.app.render({"msg": msg})

    #
    # volume metadata
    #
    @ex(
        help="add volume metadata",
        description="add volume metadata",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "snapshot id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["metadata"],
                    {
                        "help": "key:value string metadata",
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
        res = self.client.volume_v3.add_metadata(oid, metadata)
        self.app.render({"msg": "add metadata %s to volume %s" % (metadata, oid)})

    @ex(
        help="del volume metadata",
        description="del volume metadata",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "snapshot id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["metadata"],
                    {
                        "help": "metadata key",
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
        res = self.client.volume_v3.remove_metadata(oid, metadata)
        self.app.render({"msg": "remove metadata %s to volume %s" % (metadata, oid)})

    #
    # volume image metadata
    #
    @ex(
        help="add volume image metadata",
        description="add volume image metadata",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "snapshot id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["metadata"],
                    {
                        "help": "key:value string metadata",
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
        res = self.client.volume_v3.set_image_metadata(oid, metadata)
        self.app.render({"msg": "add image metadata %s to volume %s" % (metadata, oid)})

    @ex(
        help="del volume image metadata",
        description="del volume image metadata",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "snapshot id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["metadata"],
                    {
                        "help": "metadata key",
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
        res = self.client.volume_v3.remove_image_metadata(oid, metadata)
        self.app.render({"msg": "remove image metadata %s to volume %s" % (metadata, oid)})

    #
    # volume snapshot
    #
    @ex(
        help="get volume snapshots",
        description="get volume snapshots",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "snapshot id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-volume"],
                    {
                        "help": "volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group_snapshot"],
                    {
                        "help": "group snapshot id",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
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
        help="add volume snapshots",
        description="add volume snapshots",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "snapshot name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["volume"],
                    {
                        "help": "volume id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "snapshot description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": "indicates whether to snapshot, even if the volume is attached",
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
            {"msg": "adding snapshot %s with name %s for volume %s" % (res["id"], name, volume)},
            maxsize=200,
        )

    @ex(
        help="delete volume snapshot",
        description="delete volume snapshot",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "snapshot id",
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
        self.app.render({"msg": "Delete volume snapshot %s" % oid})

    @ex(
        help="set volume snapshot status",
        description="set volume snapshot status",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "snapshot id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-status"],
                    {
                        "help": "snapshot status",
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
        self.app.render({"msg": "set volume snapshot %s status to %s" % (oid, status)})

    @ex(
        help="revert volume to snapshot",
        description="revert volume to snapshot",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["volume"],
                    {
                        "help": "volume id",
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
    def volume_snapshot_revert(self):
        volume = self.app.pargs.volume
        snapshot = self.app.pargs.snapshot
        self.client.volume_v3.snapshot.revert_to(volume, snapshot)
        self.app.render({"msg": "revert volume %s to snapshot %s" % (volume, snapshot)})

    #
    # volume group type
    #
    @ex(
        help="get volume group types",
        description="get volume group types",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "volume group id",
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

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            params = {}
            res = self.client.volume_v3.group.list_types(**params)
            headers = ["id", "name", "desc", "is_public", "specs"]
            fields = ["id", "name", "description", "is_public", "group_specs"]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="add volume group type",
        description="add volume group type",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "volume group type name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group_specs"],
                    {
                        "help": "volume group type specs",
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
        self.app.render({"msg": "add volume group type %s" % name}, maxsize=200)

    @ex(
        help="delete volume group type",
        description="delete volume group type",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "volume group type id",
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
        self.app.render({"msg": "Delete volume group type %s" % oid})

    #
    # volume group
    #
    @ex(
        help="get volume groups",
        description="get volume groups",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "volume group id",
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
            transform = {"volumes": lambda x: len(x)}
            self.app.render(res, headers=headers, fields=fields, transform=transform)

    @ex(
        help="add volume group",
        description="add volume group",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "volume group name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-availability_zone"],
                    {
                        "help": "volume group availability zone",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["volume_types"],
                    {
                        "help": "the list of volume types. In an environment with multiple-storage back ends, "
                        "the scheduler determines where to send the volume based on the volume type.",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["group_type"],
                    {"help": "group type id", "action": "store", "type": str},
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
        self.app.render({"msg": "added volume group %s with id %s" % (name, res_id)}, maxsize=200)

    @ex(
        help="update volume group",
        description="update volume group",
        arguments=OPENSTACK_ARGS(
            [
                (["id"], {"help": "volume group id", "action": "store", "type": str}),
                (
                    ["-name"],
                    {
                        "help": "volume group name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "volume group availability zone",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-del"],
                    {
                        "help": "One or more volume UUIDs, separated by commas, that you want to remove from group",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-add"],
                    {
                        "help": "One or more volume UUIDs, separated by commas, that you want to add to group",
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
        self.app.render({"msg": "update volume group %s" % oid}, maxsize=200)

    @ex(
        help="delete volume group",
        description="delete volume group",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "volume group id",
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
        self.app.render({"msg": "Delete volume group %s" % oid})

    #
    # volume group snapshot
    #
    @ex(
        help="get volume group snapshots",
        description="get volume group snapshots",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "volume group snapshot id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group"],
                    {
                        "help": "volume group id",
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
        help="add volume group snapshot",
        description="add volume group snapshot",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["group"],
                    {
                        "help": "volume group id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "volume group snapshot name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "volume group snapshot description",
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
        self.app.render({"msg": "add volume group %s snapshot" % oid}, maxsize=200)

    @ex(
        help="delete volume group snapshot",
        description="delete volume group snapshot",
        arguments=OPENSTACK_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "volume group snapshot id",
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
        self.app.render({"msg": "Delete volume group snapshot %s" % oid})


#
#     @expose(aliases=['delete <id>'], aliases_only=True)
#     @check_error
#     def delete(self):
#         oid = self.app.pargs.id
#         res = self.client.volume.delete(oid)
#         res = {'msg': 'Delete volume %s' % oid}
#         self.app.log.info(res)
#         self.app.render(res, headers=['msg'])
#
#     @expose(aliases=['status <id> <status>'], aliases_only=True)
#     @check_error
#     def status(self):
#         oid = self.app.pargs.id
#         status = self.get_arg(name='status')
#         res = self.client.volume.reset_status(oid, status, None, None)
#         res = {'msg': 'Reset volume %s status' % oid}
#         self.app.render(res, headers=['msg'])
#
#     @expose(aliases=['check [delete=false]'], aliases_only=True)
#     @check_error
#     def check(self):
#         """Found all the orphan volumes
#     - delete: if true remove orphan volumes
#         """
#         delete = self.get_arg(name='delete', default=False, keyvalue=True)
#         obj = self.client.volume.list(detail=True)
#         sg_index = {i['os-vol-tenant-attr:tenant_id']: i for i in obj}
#         projects = self.client.project.list()
#         projects_ids = [i['id'] for i in projects]
#         for k, v in sg_index.items():
#             if k not in projects_ids:
#                 print v['id'], v['name']
#                 if delete is True:
#                     res = self.client.volume.delete(v['id'])
#
#


# class OpenstackPlatformVolumeBackupController(OpenstackPlatformControllerChild):
#     fields = ['id', 'name', 'description', 'volume_id', 'status', 'size', 'is_incremental', 'created_at']
#     headers = ['id', 'name', 'description', 'volume_id', 'status', 'size', 'is_incremental', 'created_at']
#
#     class Meta:
#         label = 'openstack.platform.volumes.backups'
#         alias = 'backups'
#         aliases = ['backups']
#         aliases_only = True
#         stacked_on = 'openstack.platform.volumes'
#         stacked_backup = 'nested'
#         description = "Openstack Volume Backups management"
#
#     def _ext_parse_args(self):
#         OpenstackPlatformControllerChild._ext_parse_args(self)
#
#         self.entity_class = self.client.volume.backup
#
#     @expose(aliases=['list [field=value]'], aliases_only=True)
#     @check_error
#     def list(self):
#         """List volume backup.
#         """
#         params = self.app.kvargs
#         params['detail'] = True
#         res = self.client.volume.backup.list(**params)
#         self.app.render(res, headers=self.headers, fields=self.fields)
#
#     @expose(aliases=['get <backup-id>'], aliases_only=True)
#     @check_error
#     def get(self):
#         """Get volume backup.
#
# fields:
#   backup-id           id of the backup"""
#         oid = self.get_arg(name='backup-id')
#         obj = self.client.volume.backup.get(oid)
#         res = obj
#         self.app.render(res, details=True)
#
#     @expose(aliases=['add <name> <volume-id> [field=..]'], aliases_only=True)
#     @check_error
#     def add(self):
#         """Add volume backup.
#
# fields:
#   name                  backup name
#   desc                  backup description [optional]
#   volume-id             id of the volume to backup
#   container             the container name [optional]
#   incremental           the backup mode. A valid value is true for incremental backup mode or false for full backup
#                         mode. [default=False]
#   force                 indicates whether to backup, even if the volume is attached. [default=False]
#   snapshot-id           the UUID of the source volume snapshot. [optional]"""
#         name = self.get_arg(name='name')
#         volume = self.get_arg(name='volume-id')
#         desc = self.get_arg(name='desc', keyvalue=True, default=name)
#         force = self.get_arg(name='force', keyvalue=True, default=False)
#         incremental = self.get_arg(name='incremental', keyvalue=True, default=False)
#         snapshot = self.get_arg(name='snapshot-id', keyvalue=True, default=None)
#         data = {
#             'name': name,
#             'desc': desc,
#             'volume_id': volume,
#             'force': force,
#             'incremental': incremental
#         }
#         if snapshot is not None:
#             data['snapshot_id'] = snapshot
#         res = self.client.volume.backup.create(**data)
#         msg = 'Add volume %s backup %s' % (volume, name)
#         self.app.render({'msg': msg}, headers=['msg'], maxsize=200)
#
#     @expose(aliases=['restore <backup-id> [field=..]'], aliases_only=True)
#     @check_error
#     def restore(self):
#         """Restore volume backup.
#
# fields:
#   backup-id             id of the backup to restore
#   volume-id             id of the volume where restore [optional]
#   volume-name           name of the volume where restore [optional]"""
#         backup_id = self.get_arg(name='backup-id')
#         volume_id = self.get_arg(name='volume-id', keyvalue=True, default=None)
#         volume_name = self.get_arg(name='volume-name', keyvalue=True, default=None)
#         res = self.client.volume.backup.restore(backup_id, name=volume_name, volume_id=volume_id)
#         msg = 'Restore backup %s volume %s|%s' % (backup_id, volume_name, volume_id)
#         self.app.render({'msg': msg}, headers=['msg'], maxsize=200)
#
#     @expose(aliases=['delete <backup-id>'], aliases_only=True)
#     @check_error
#     def delete(self):
#         """Delete volume backup.
#
# fields:
#   backup-id           id of the volume"""
#         oid = self.get_arg(name='backup-id')
#         res = self.client.volume.backup.delete(oid)
#         res = {'msg': 'Delete volume backup %s' % oid}
#         self.app.render(res, headers=['msg'])
#
#
# class OpenstackPlatformVolumeConsistencyGroupController(OpenstackPlatformControllerChild):
#     fields = ['id', 'name', 'description', 'status', 'availability_zone', 'created_at']
#     headers = ['id', 'name', 'description', 'status', 'zone', 'created_at']
#
#     class Meta:
#         label = 'openstack.platform.volumes.groups'
#         alias = 'groups'
#         aliases = ['groups']
#         aliases_only = True
#         stacked_on = 'openstack.platform.volumes'
#         stacked_consistencygroup = 'nested'
#         description = "Openstack Volume Consistency Groups management"
#
#     def _ext_parse_args(self):
#         OpenstackPlatformControllerChild._ext_parse_args(self)
#
#         self.entity_class = self.client.volume.consistencygroup
#
#     @expose(aliases=['list [field=value]'], aliases_only=True)
#     @check_error
#     def list(self):
#         """List volume consistency group.
#         """
#         params = self.app.kvargs
#         params['detail'] = True
#         res = self.client.volume.consistencygroup.list(**params)
#         self.app.render(res, headers=self.headers, fields=self.fields)
#
#     @expose(aliases=['get <group-id>'], aliases_only=True)
#     @check_error
#     def get(self):
#         """Get volume consistency group.
#
# fields:
#   group-id              id of the consistency group"""
#         oid = self.get_arg(name='group-id')
#         obj = self.client.volume.consistencygroup.get(oid)
#         res = obj
#         self.app.render(res, details=True)
#
#     @expose(aliases=['add <name> <volume-id> [field=..]'], aliases_only=True)
#     @check_error
#     def add(self):
#         """Add volume consistency group.
#
# fields:
#   name                  consistencygroup name
#   desc                  consistencygroup description [optional]
#   volume-id             id of the volume to consistencygroup
#   container             the container name [optional]
#   incremental           the consistencygroup mode. A valid value is true for incremental consistencygroup mode or false for full consistencygroup
#                         mode. [default=False]
#   force                 indicates whether to consistencygroup, even if the volume is attached. [default=False]
#   snapshot-id           the UUID of the source volume snapshot. [optional]"""
#         name = self.get_arg(name='name')
#         volume = self.get_arg(name='volume-id')
#         desc = self.get_arg(name='desc', keyvalue=True, default=name)
#         force = self.get_arg(name='force', keyvalue=True, default=False)
#         incremental = self.get_arg(name='incremental', keyvalue=True, default=False)
#         snapshot = self.get_arg(name='snapshot-id', keyvalue=True, default=None)
#         data = {
#             'name': name,
#             'desc': desc,
#             'volume_id': volume,
#             'force': force,
#             'incremental': incremental
#         }
#         if snapshot is not None:
#             data['snapshot_id'] = snapshot
#         res = self.client.volume.consistencygroup.create(**data)
#         msg = 'Add volume %s consistency group %s' % (volume, name)
#         self.app.render({'msg': msg}, headers=['msg'], maxsize=200)
#
#     @expose(aliases=['restore <group-id> [field=..]'], aliases_only=True)
#     @check_error
#     def restore(self):
#         """Restore volume consistency group.
#
# fields:
#   group-id              id of the consistency group to restore
#   volume-id             id of the volume where restore [optional]
#   volume-name           name of the volume where restore [optional]"""
#         consistencygroup_id = self.get_arg(name='group-id')
#         volume_id = self.get_arg(name='volume-id', keyvalue=True, default=None)
#         volume_name = self.get_arg(name='volume-name', keyvalue=True, default=None)
#         res = self.client.volume.consistencygroup.restore(consistencygroup_id, name=volume_name, volume_id=volume_id)
#         msg = 'Restore consistency group %s volume %s|%s' % (consistencygroup_id, volume_name, volume_id)
#         self.app.render({'msg': msg}, headers=['msg'], maxsize=200)
#
#     @expose(aliases=['delete <group-id>'], aliases_only=True)
#     @check_error
#     def delete(self):
#         """Delete volume consistency group.
#
# fields:
#   group-id             id of the volume"""
#         oid = self.get_arg(name='group-id')
#         res = self.client.volume.consistencygroup.delete(oid)
#         res = {'msg': 'Delete volume consistency group %s' % oid}
#         self.app.render(res, headers=['msg'])
#
#

# class OpenstackPlatformSwiftController(OpenstackPlatformControllerChild):
#     headers = ['id', 'action', 'server_id', 'config_id', 'creation_time', 'updated_time', 'status',
#                'status_reason']
#
#     class Meta:
#         label = 'openstack.platform.swift'
#         aliases = ['swift']
#         aliases_only = True
#         description = "Openstack Swift management"
#
#     def _ext_parse_args(self):
#         OpenstackPlatformControllerChild._ext_parse_args(self)
#
#         self.entity_class = self.client.swift
#
#     @expose()
#     @check_error
#     def containers(self):
#         """List containers
#         """
#         res = self.client.swift.container_read()
#         self.app.log.debug(res)
#         if self.format == 'text':
#             for item in res:
#                 if isinstance(item, list):
#                     self.app.render(item, headers=['name', 'count', 'last_modified', 'bytes'], maxsize=60)
#                 elif isinstance(item, dict):
#                     self.app.render(item, details=True)
#         else:
#             self.app.render(res, details=True)
#
#     @expose(aliases=['container <oid>'], aliases_only=True)
#     @check_error
#     def container(self):
#         """Get container by name
#         """
#         oid = self.app.pargs.id
#         res = self.client.swift.container_read(container=oid)
#         if self.format == 'text':
#             for item in res:
#                 if isinstance(item, list):
#                     self.app.render(item, headers=['name', 'hash', 'content_type', 'last_modified', 'bytes'],
#                                 maxsize=80)
#                 elif isinstance(item, dict):
#                     self.app.render(item, details=True)
#         else:
#             self.app.render(res, details=True)
#
#     @expose(aliases=['container_add <oid>'], aliases_only=True)
#     @check_error
#     def container_add(self):
#         container = 'prova'
#         res = self.client.swift.container_put(container=container, x_container_meta_name={'meta1': '', 'meta2': ''})
#
#     @expose(aliases=['container_delete <oid>'], aliases_only=True)
#     @check_error
#     def container_delete(self):
#         container = 'morbido'
#         res = self.client.swift.container_delete(container=container)
#
#     @expose(aliases=['object <container> <oid>'], aliases_only=True)
#     @check_error
#     def object(self):
#         """Get object by name
#         """
#         container = self.get_arg(name='container')
#         oid = self.app.pargs.id
#         res = self.client.swift.object_get(container=container, c_object=oid)
#         if self.format == 'text':
#             for item in res:
#                 if isinstance(item, list):
#                     self.app.render(item, headers=['name', 'hash', 'content_type', 'last_modified', 'bytes'],
#                                 maxsize=80)
#                 elif isinstance(item, dict):
#                     self.app.render(item, details=True)
#         else:
#             self.app.render(res, details=True)
#
#     @expose(aliases=['object-delete <container> <oid>'], aliases_only=True)
#     @check_error
#     def object_delete(self):
#         """Delete object by name
#         """
#         container = self.get_arg(name='container')
#         oid = self.app.pargs.id
#         res = self.client.swift.object_delete(container=container, c_object=oid)
#         msg = {'msg': 'Delete object %s:%s' % (container, oid)}
#         self.app.render(msg, headers=['msg'])
#
#
# class OpenstackPlatformManilaController(OpenstackPlatformControllerChild):
#     class Meta:
#         label = 'openstack.platform.manila'
#         aliases = ['manila']
#         aliases_only = True
#         description = "Openstack Manila management"
#
#     def _ext_parse_args(self):
#         OpenstackPlatformControllerChild._ext_parse_args(self)
#
#         self.entity_class = self.client.manila
#
#     @expose(aliases=['api [version]'], aliases_only=True)
#     @check_error
#     def api(self):
#         """List manila api versions
#
# fields:
#   version               api version [optional]"""
#         version = self.get_arg(default=None)
#         res = self.client.manila.api(version=version)
#         if version is None:
#             self.app.render(res, headers=['id', 'version', 'min_version', 'status', 'updated'])
#         else:
#             self.app.render(res, details=True)
#
#     @expose()
#     @check_error
#     def limits(self):
#         """List manila limits
#         """
#         res = self.client.manila.limits()
#         self.app.render(res, details=True)
#
#     @expose()
#     @check_error
#     def services(self):
#         """List manila api services
#         """
#         res = self.client.manila.services()
#         self.app.render(res, headers=['id', 'state', 'host', 'status', 'zone', 'binary', 'updated_at'])
#
#
# class OpenstackPlatformManilaChildController(OpenstackPlatformControllerChild):
#     class Meta:
#         stacked_on = 'openstack.platform.manila'
#         stacked_type = 'nested'
#
#
# class OpenstackPlatformManilaShareController(OpenstackPlatformManilaChildController):
#     class Meta:
#         label = 'openstack.platform.manila.share'
#         aliases = ['shares']
#         aliases_only = True
#         description = "Openstack Manila Share management"
#
#     def _ext_parse_args(self):
#         OpenstackPlatformControllerChild._ext_parse_args(self)
#
#         self.entity_class = self.client.manila.share
#
#     @expose(aliases=['list [key=value]'], aliases_only=True)
#     @check_error
#     def list(self):
#         """List manila shares
#         """
#         params = self.get_query_params(*self.app.pargs.extra_arguments)
#         res = self.client.manila.share.list(details=True, **params)
#         self.app.render(res, headers=['id', 'name', 'project_id', 'size', 'created_at', 'share_type', 'share_proto',
#                                   'status', 'is_public'], maxsize=40)
#
#     @expose(aliases=['get <id>'], aliases_only=True)
#     @check_error
#     def get(self):
#         """Get manila share by id
#         """
#         oid = self.app.pargs.id
#         res = self.client.manila.share.get(oid)
#         self.app.render(res, details=True)
#
#     @expose(aliases=['add <name> <size> <proto> <share_type>'], aliases_only=True)
#     @check_error
#     def add(self):
#         """Add manila share
#     - name: share name
#     - size: share in GB
#     - proto: share protocol (NFS, CIFS, GlusterFS, HDFS, or CephFS. CephFS)
#     - share_type: share type
#         """
#         name = self.get_arg(name='name')
#         size = self.get_arg(name='size')
#         proto = self.get_arg(name='proto')
#         share_type = self.get_arg(name='share_type')
#         res = self.client.manila.share.create(proto, size, name=name, description=name, share_type=share_type,
#                                        is_public=False, availability_zone='nova')
#         res = {'msg': 'Create manila share %s' % (name)}
#         self.app.render(res, headers=['msg'])
#
#     @expose(aliases=['delete <id> [force=true]'], aliases_only=True)
#     @check_error
#     def delete(self):
#         """Delete manila share
#     - force: if true force delete
#         """
#         oid = self.app.pargs.id
#         force = self.get_arg(name='force', default=False, keyvalue=True)
#         if force is True:
#             res = self.client.manila.share.action.force_delete(oid)
#         else:
#             res = self.client.manila.share.delete(oid)
#         res = {'msg': 'Delete manila share %s' % (oid)}
#         self.app.render(res, headers=['msg'])
#
#     @expose(aliases=['grant-list <id>'], aliases_only=True)
#     @check_error
#     def grant_list(self):
#         """List manila share <id> access list
#         """
#         oid = self.app.pargs.id
#         res = self.client.manila.share.action.list_access(oid)
#         self.app.render(res, headers=['id', 'access_type', 'access_level', 'state', 'access_to'])
#
#     @expose(aliases=['grant-add <id> <level> <type> <to>'], aliases_only=True)
#     @check_error
#     def grant_add(self):
#         """Add manila share <id> access grant
#     - level: The access level to the share. To grant or deny access to a share:
#         - rw: Read and write (RW) access.
#         - ro: Read-only (RO) access.
#     - type: The access rule type. Valid values are:
#         - ip: Authenticates an instance through its IP address.
#         - cert: Authenticates an instance through a TLS certificate.
#         - user: Authenticates by a user or group name.
#     - to: The value that defines the access. The back end grants or denies the access to it. Valid values are:
#         - ip: A valid format is XX.XX.XX.XX or XX.XX.XX.XX/XX. For example 0.0.0.0/0.
#         - cert: Specify the TLS identity as the IDENTKEY. A valid value is any string up to 64 characters long in the
#                 common name (CN) of the certificate. The meaning of a string depends on its interpretation.
#         - user: A valid value is an alphanumeric string that can contain some special characters and is from 4 to 32
#                 characters long.
#         """
#         oid = self.app.pargs.id
#         access_level = self.get_arg(name='access_level')
#         access_type = self.get_arg(name='access_type')
#         access_to = self.get_arg(name='access_to')
#         res = self.client.manila.share.action.grant_access(oid, access_level, access_type, access_to)
#         self.app.render(res, headers=['id', 'access_type', 'access_level', 'state', 'access_to'])
#
#     @expose(aliases=['grant-remove <id> <access_id>'], aliases_only=True)
#     @check_error
#     def grant_remove(self):
#         """Remove manila share <id> access grant
#         """
#         oid = self.app.pargs.id
#         access_id = self.get_arg(name='access_id')
#         res = self.client.manila.share.action.revoke_access(oid, access_id)
#         res = {'msg': 'Revoke access %s to share %s' % (oid, access_id)}
#         self.app.render(res, headers=['msg'], maxsize=200)
#
#     @expose(aliases=['reset-status <id> <status>'], aliases_only=True)
#     @check_error
#     def reset_status(self):
#         """Reset manila share <id> status
#     - status: The share access status, which is new, error, active
#         """
#         oid = self.app.pargs.id
#         status = self.get_arg(name='status')
#         res = self.client.manila.share.action.reset_status(oid, status)
#         res = {'msg': 'Reset status of share %s to %s' % (oid, status)}
#         self.app.render(res, headers=['msg'])
#
#     @expose(aliases=['size-extend <id> <new_size>'], aliases_only=True)
#     @check_error
#     def size_extend(self):
#         """Extend manila share <id>
#     - new_size: New size of the share, in GBs.
#         """
#         oid = self.app.pargs.id
#         new_size = self.get_arg(name='new_size')
#         res = self.client.manila.share.action.extend(oid, new_size)
#         res = {'msg': 'Extend share %s to %s' % (oid, new_size)}
#         self.app.render(res, headers=['msg'])
#
#     @expose(aliases=['size-shrink <id> <new_size>'], aliases_only=True)
#     @check_error
#     def size_shrink(self):
#         """Shrink manila share <id>
#     - new_size: New size of the share, in GBs.
#         """
#         oid = self.app.pargs.id
#         new_size = self.get_arg(name='new_size')
#         res = self.client.manila.share.action.shrink(oid, new_size)
#         res = {'msg': 'Shrink share %s to %s' % (oid, new_size)}
#         self.app.render(res, headers=['msg'])
#
#     @expose(aliases=['revert-to-snapshot <id> <snapshot_id>'], aliases_only=True)
#     @check_error
#     def revert_to_snapshot(self):
#         """Revert manila share <id> to snapshot
#     - snapshot_id: New size of the share, in GBs.
#         """
#         oid = self.app.pargs.id
#         snapshot_id = self.get_arg(name='snapshot_id')
#         res = self.client.manila.share.action.revert(oid, snapshot_id)
#         res = {'msg': 'Revert share %s to snapshot_id %s' % (oid, snapshot_id)}
#         self.app.render(res, headers=['msg'])
#
#
# class OpenstackPlatformManilaShareSnapshotController(OpenstackPlatformManilaChildController):
#     class Meta:
#         label = 'openstack.platform.manila.share_snapshot'
#         aliases = ['snapshots']
#         aliases_only = True
#         description = "Openstack Manila Share Snapshots management"
#
#     def _ext_parse_args(self):
#         OpenstackPlatformControllerChild._ext_parse_args(self)
#
#         self.entity_class = self.client.manila.share.snapshot
#
#     @expose(aliases=['list [key=value]'], aliases_only=True)
#     @check_error
#     def list(self):
#         """List manila share snapshots
#         """
#         params = self.get_query_params(*self.app.pargs.extra_arguments)
#         res = self.client.manila.share.snapshot.list(details=True, **params)
#         self.app.render(res, headers=['id', 'name', 'project_id', 'size', 'created_at', 'share_type', 'share_proto',
#                                   'export_location'], maxsize=40)
#
#     @expose(aliases=['get <id>'], aliases_only=True)
#     @check_error
#     def get(self):
#         """Get manila share snapshot by id
#         """
#         oid = self.app.pargs.id
#         res = self.client.manila.share.snapshot.get(oid)
#         self.app.render(res, details=True)
#
#     @expose(aliases=['add <share_id> <name>'], aliases_only=True)
#     @check_error
#     def add(self):
#         """Add manila share snapshot
#     - name: share name
#     - share_id: id of the share
#         """
#         share_id = self.get_arg(name='share_id')
#         name = self.get_arg(name='name')
#         res = self.client.manila.share.snapshot.create(share_id, name=name)
#         res = {'msg': 'Create %s %s' % (self.client.manila.share.snapshot, name)}
#         self.app.render(res, headers=['msg'])
#
#     @expose(aliases=['delete <id>'], aliases_only=True)
#     @check_error
#     def delete(self):
#         oid = self.app.pargs.id
#         res = self.client.manila.share.snapshot.delete(oid)
#         res = {'msg': 'Delete %s %s' % (self.entity_class, oid)}
#         self.app.render(res, headers=['msg'])
#
#
# class OpenstackPlatformManilaShareTypeController(OpenstackPlatformManilaChildController):
#     class Meta:
#         label = 'openstack.platform.manila.share_types'
#         aliases = ['types']
#         aliases_only = True
#         description = "Openstack Manila Share Type management"
#
#     def _ext_parse_args(self):
#         OpenstackPlatformControllerChild._ext_parse_args(self)
#
#         self.entity_class = self.client.manila.share_type
#
#     @expose(aliases=['list [default=true/false]'], aliases_only=True)
#     @check_error
#     def list(self):
#         """List manila share types
#     - default=true list default share types
#         """
#         params = self.get_query_params(*self.app.pargs.extra_arguments)
#         res = self.client.manila.share_type.list(**params)
#         self.app.render(res, headers=['id', 'name', 'access', 'backend'], fields=['id', 'name',
#                     'os-share-type-access:is_public', 'extra_specs.share_backend_name'], maxsize=60)
#
#     @expose(aliases=['extra-spec <id>'], aliases_only=True)
#     @check_error
#     def extra_spec(self):
#         """Get manila share type extra spec by id
#         """
#         oid = self.app.pargs.id
#         res = self.client.manila.share_type.get_extra_spec(oid)
#         self.app.render(res, details=True)
#
#     @expose(aliases=['access <id>'], aliases_only=True)
#     @check_error
#     def access(self):
#         """Get manila share type access by id. If share type access is True this command return error.
#         """
#         oid = self.app.pargs.id
#         res = self.client.manila.share_type.get_access(oid)
#         self.app.render(res, details=True)
#
#     @expose(aliases=['add <name> [key=value]'], aliases_only=True)
#     @check_error
#     def add(self):
#         """Creates a share type
#     - name: The share type name.
#     - desc: (Optional) The description of the share type.
#     - is_public: (Optional) Indicates whether is publicly accessible. Default is false.
#     - replication_type: (Optional) The share replication type.
#     - driver_handles_share_servers: (Optional) An extra specification that defines the driver mode for share server, or
#     storage, life cycle management. The Shared File Systems service creates a share server for the export of shares.
#     This value is true when the share driver manages, or handles, the share server life cycle. This value is false when
#     an administrator rather than a share driver manages the storage life cycle.
#     - mount_snapshot_support: (Optional) Boolean extra spec used for filtering of back ends by their capability to mount
#     share snapshots.
#     - revert_to_snapshot_support: (Optional) Boolean extra spec used for filtering of back ends by their capability to
#     revert shares to snapshots.
#     - create_share_from_snapshot_support: (Optional) Boolean extra spec used for filtering of back ends by their
#     capability to create shares from snapshots.
#     - snapshot_support: (Optional) An extra specification that filters back ends by whether they do or do not support
#     share snapshots.
#         """
#         name = self.get_arg(name='name')
#         desc = self.get_arg(name='desc', default=name, keyvalue=True)
#         is_public = self.get_arg(name='is_public', default=False, keyvalue=True)
#         replication_type = self.get_arg(name='replication_type', default=None, keyvalue=True)
#         driver_handles_share_servers = self.get_arg(name='driver_handles_share_servers', default=None, keyvalue=True)
#         mount_snapshot_support = self.get_arg(name='mount_snapshot_support', default=None, keyvalue=True)
#         revert_to_snapshot_support = self.get_arg(name='revert_to_snapshot_support', default=None, keyvalue=True)
#         create_share_from_snapshot_support = self.get_arg(name='create_share_from_snapshot_support', default=None,
#                                                           keyvalue=True)
#         snapshot_support = self.get_arg(name='snapshot_support', default=None, keyvalue=True)
#         res = self.client.manila.share_type.create(name, desc=desc, is_public=is_public, replication_type=replication_type,
#                                        driver_handles_share_servers=driver_handles_share_servers,
#                                        mount_snapshot_support=mount_snapshot_support,
#                                        revert_to_snapshot_support=revert_to_snapshot_support,
#                                        create_share_from_snapshot_support=create_share_from_snapshot_support,
#                                        snapshot_support=snapshot_support)
#         res = {'msg': 'Create %s %s' % (self.client.manila.share_type, name)}
#         self.app.render(res, headers=['msg'])
#
#     @expose(aliases=['delete <id>'], aliases_only=True)
#     @check_error
#     def delete(self):
#         oid = self.app.pargs.id
#         res = self.client.manila.share_type.delete(oid)
#         res = {'msg': 'Delete %s %s' % (self.client.manila.share_type, oid)}
#         self.app.render(res, headers=['msg'])
#
#
# class OpenstackPlatformManilaStoragePoolController(OpenstackPlatformManilaChildController):
#     class Meta:
#         label = 'openstack.platform.manila.storage_pool'
#         aliases = ['storage_pools']
#         aliases_only = True
#         description = "Openstack Manila storage Pool management"
#
#     def _ext_parse_args(self):
#         OpenstackPlatformControllerChild._ext_parse_args(self)
#
#         self.entity_class = self.client.manila.storage_pool
#
#     @expose(aliases=['list [key=value]'], aliases_only=True)
#     @check_error
#     def list(self):
#         """List manila storage pools
#         """
#         params = self.get_query_params(*self.app.pargs.extra_arguments)
#         res = self.client.manila.storage_pool.list(details=True, **params)
#         fields = ['name', 'pool', 'backend', 'host', 'capabilities.total_capacity_gb',
#                   'capabilities.free_capacity_gb']
#         headers = ['name', 'pool', 'backend', 'host', 'total_capacity_gb', 'free_capacity_gb']
#         self.app.render(res, headers=headers, fields=fields, maxsize=60)
#
#     @expose(aliases=['get <oid>'], aliases_only=True)
#     @check_error
#     def get(self):
#         """List manila storage pools
#
#         oid : pool name
#         """
#         oid = self.app.pargs.id
#         res = self.client.manila.storage_pool.list(details=True, pool=oid)
#         if len(res) == 0:
#             raise Exception('Pool %s does not exist' % oid)
#         self.app.render(res[0], details=True, maxsize=200)
#
#
# class OpenstackPlatformManilaQuotaSetController(OpenstackPlatformManilaChildController):
#     class Meta:
#         label = 'openstack.platform.manila.quota_set'
#         aliases = ['quota_set']
#         aliases_only = True
#         description = "Openstack Manila Quota Set management"
#
#     def _ext_parse_args(self):
#         OpenstackPlatformControllerChild._ext_parse_args(self)
#
#         self.entity_class = self.client.manila.quota_set
#
#     @expose(aliases=['get-default <project_id>'], aliases_only=True)
#     @check_error
#     def get_default(self):
#         """List manila default quota set per project
#         """
#         project_id = self.get_arg(name='project_id')
#         res = self.client.manila.quota_set.get_default(project_id)
#         self.app.render(res, details=True)
#
#     @expose(aliases=['get <project_id>'], aliases_only=True)
#     @check_error
#     def get(self):
#         """List manila quota set per project
#         """
#         project_id = self.get_arg(name='project_id')
#         res = self.client.manila.quota_set.get(project_id)
#         self.app.render(res, details=True)
#
#     @expose(aliases=['update <project_id> [key=value]'], aliases_only=True)
#     @check_error
#     def update(self):
#         """Update manila quota set per project
#     - gigabytes: The number of gigabytes for the tenant.
#     - snapshots: The number of snapshots for the tenant.
#     - snapshot_gigabytes: The number of gigabytes for the snapshots for the tenant.
#     - shares: The number of shares for the tenant.
#     - share_networks: The number of share networks for the tenant.
#     - share_groups: The number of share groups allowed for each tenant or user.
#     - share_group_snapshots: The number of share group snapshots allowed for each tenant or user.
#     - share_type: The name or UUID of the share type. If you specify this parameter in the URI, you show, update, or
#     delete quotas for this share type.
#         """
#         project_id = self.get_arg(name='project_id')
#         gigabytes = self.get_arg(name='gigabytes', default=None, keyvalue=True)
#         snapshots = self.get_arg(name='snapshots', default=None, keyvalue=True)
#         snapshot_gigabytes = self.get_arg(name='snapshot_gigabytes', default=None, keyvalue=True)
#         shares = self.get_arg(name='shares', default=None, keyvalue=True)
#         share_networks = self.get_arg(name='share_networks', default=None, keyvalue=True)
#         share_groups = self.get_arg(name='share_groups', default=None, keyvalue=True)
#         share_group_snapshots = self.get_arg(name='share_group_snapshots', default=None, keyvalue=True)
#         share_type = self.get_arg(name='share_type', default=None, keyvalue=True)
#         res = self.client.manila.quota_set.update(project_id, snapshots=snapshots, snapshot_gigabytes=snapshot_gigabytes,
#                                        shares=shares, share_networks=share_networks, share_groups=share_groups,
#                                        share_group_snapshots=share_group_snapshots, share_type=share_type,
#                                        gigabytes=gigabytes)
#         self.app.render(res, details=True)
#
