# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from time import time
from requests import get

from beecell.simple import get_line
from beecell.types.type_string import bool2str
from beecell.types.type_dict import dict_get

from beehive3_cli.core.controller import ARGS, BaseController
from beehive3_cli.core.util import load_environment_config
from cement import ex


class CheckEngine(object):
    def __init__(self, app, env, key):
        self.app = app
        self.env = env
        self.key = key
        self.config = load_environment_config(self.app)
        self.orchestrators = self.config.get("orchestrators", {})

        self.elapsed = 0

        self.line_tmpl = "%-10s %-50s %6s %-35s %-8s %8s"
        self.line_template = "{:10} {:50} {:6} {:35} {:8} {:>11}"
        self.separator = self.line_tmpl % (
            get_line(10),
            get_line(50),
            get_line(6),
            get_line(35),
            get_line(8),
            get_line(8),
        )

    def __printline(self, data):
        if data[4] is True:
            data[4] = self.app.colored_text.output(bool2str(data[4]), "GREEN")
        else:
            data[4] = self.app.colored_text.output(bool2str(data[4]), "RED")
        val = self.line_template.format(*data)
        print(val)

    def __get_orchestrator(self, engine):
        orchestrators = self.orchestrators.get(engine, {})
        conf = orchestrators.get(self.env)
        return conf

    def __start_time(self):
        self.start = time()

    def __stop_time(self):
        self.elapsed = round(time() - self.start, 4)

    def print_header(self):
        print(self.line_tmpl % ("engine", "host", "port", "action", "status", "elapsed"))
        print(self.separator)

    def nginx(self):
        engine = "nginx"
        conf = self.__get_orchestrator(engine)
        if conf is None:
            return None

        hosts = conf.get("hosts", [])
        port = conf.get("port", 0)

        for host in hosts:
            self.__start_time()
            try:
                proxies = {
                    "http": None,
                    "https": None,
                }
                res = get("https://%s:%s" % (host, port), proxies=proxies, verify=False)
                self.app.log.debug("uri: https://%s:%s" % (host, port))
                if res.status_code == 200:
                    res = True
                    action = "ping https"
                else:
                    res = False
                    action = "ping https"
            except:
                self.app.log.warning("", exc_info=True)
                res = False
                action = "ping https"

            self.__stop_time()
            self.__printline([engine, host, port, action, res, self.elapsed])

    def mariadb(self):
        from beecell.db import MysqlManager

        engine = "mariadb"
        conf = self.__get_orchestrator(engine)
        if conf is None:
            return None

        hosts = conf.get("hosts", [])
        port = conf.get("port", 0)
        root = {"name": "root", "password": conf.get("users", {}).get("root")}

        def get_mysql_engine(host, port, user, db):
            db_uri = "mysql+pymysql://%s:%s@%s:%s/%s" % (
                user["name"],
                user["password"],
                host,
                port,
                db,
            )
            server = MysqlManager(1, db_uri)
            server.create_simple_engine()
            self.app.log.info("Get mysql engine for %s" % db_uri)
            return server

        db = "mysql"
        cluster_size = len(hosts)
        for host in hosts:
            self.__start_time()
            server = get_mysql_engine(host, port, root, db)
            res = server.ping()
            self.app.log.info("Ping mysql : %s" % res)
            self.__printline([engine, host, port, "ping mysql port", res, self.elapsed])
            self.__stop_time()
            self.__start_time()
            status = server.get_galera_cluster_status()
            self.app.log.info("get mysql cluster status : %s" % status)
            res = (
                (status["wsrep_cluster_status"] == "Primary")
                and int(status["wsrep_cluster_size"]) == cluster_size
                and (status["wsrep_local_state_comment"] == "Synced")
            )

            self.__stop_time()
            self.__printline([engine, host, port, "mysql galera clusters status", res, self.elapsed])

    def k8s(self):
        from kubernetes import client as k8s_client

        engine = "k8s"
        conf = self.__get_orchestrator(engine)
        if conf is None:
            return None

        hosts = conf.get("hosts", [])
        k8s_token = conf.get("token", "")
        proto = conf.get("proto", "http")
        port = conf.get("port", 0)

        # Create a configuration object
        configuration = k8s_client.Configuration()
        configuration.verify_ssl = False
        configuration.api_key = {"authorization": "Bearer " + k8s_token}

        for host in hosts:
            self.__start_time()
            configuration.host = "%s://%s:%s" % (proto, host, port)
            api_client = k8s_client.ApiClient(configuration)
            v1 = k8s_client.ApisApi(api_client)
            try:
                v1.get_api_versions()
                self.__printline([engine, host, port, "k8s ping", True, self.elapsed])
            except:
                self.__printline([engine, host, port, "k8s ping", False, self.elapsed])

    def vsphere(self):
        from beedrones.vsphere.client import VsphereManager

        engine = "vsphere"
        conf = self.__get_orchestrator(engine)
        if conf is None:
            return None

        if "vcenter" not in conf:
            return None

        conf.get("vcenter")["pwd"] = str(conf.get("vcenter")["pwd"])
        conf.get("nsx")["pwd"] = str(conf.get("nsx")["pwd"])
        client = VsphereManager(conf.get("vcenter"), conf.get("nsx"), key=self.key)
        self.__start_time()
        ping = client.system.ping_vsphere()
        self.__stop_time()
        self.__printline(
            [
                engine,
                conf.get("vcenter").get("host"),
                443,
                "vcenter ping",
                ping,
                self.elapsed,
            ]
        )
        self.__start_time()
        ping = client.system.ping_nsx()
        self.__stop_time()
        self.__printline(
            [
                engine,
                conf.get("nsx").get("host"),
                443,
                "vcenter nsx",
                ping,
                self.elapsed,
            ]
        )
        self.__start_time()
        controllers = client.system.nsx.list_controllers()
        c_status = True
        for c in controllers:
            if c.get("status") == "RUNNING":
                c_status = c_status and True
            else:
                c_status = c_status and False
        self.__stop_time()
        self.__printline(
            [
                engine,
                conf.get("nsx").get("host"),
                443,
                "vcenter nsx controllers",
                c_status,
                self.elapsed,
            ]
        )
        self.__start_time()
        res = client.system.nsx.components_summary()
        components = {}
        entries = dict_get(res, "componentsByGroup.entry", default=[])
        for item in entries:
            comps = dict_get(item, "components.component", default=[])
            if isinstance(comps, dict):
                comps = [comps]
            for item2 in comps:
                components[item2.get("id")] = item2
        c_status = True
        for c, v in components.items():
            if c in ["VPOSTGRES", "RABBITMQ", "NSX", "SSH"]:
                if c.get("status") == "RUNNING":
                    c_status = c_status and True
                else:
                    c_status = c_status and False
        self.__stop_time()
        self.__printline(
            [
                engine,
                conf.get("nsx").get("host"),
                443,
                "vcenter nsx components",
                c_status,
                self.elapsed,
            ]
        )

    def openstack(self):
        from beedrones.openstack.client import OpenstackManager

        engine = "openstack"
        conf = self.__get_orchestrator(engine)
        if conf is None:
            return None

        hosts = conf.get("hosts", [])
        proto = conf.get("proto", "http")
        port = conf.get("port", 0)
        path = conf.get("path", "")

        def get_client(uri, conf):
            client = OpenstackManager(uri, default_region=conf.get("region"))
            client.authorize(
                conf.get("user"),
                str(conf.get("pwd")),
                project=conf.get("project"),
                domain=conf.get("domain"),
                key=self.key,
            )
            return client

        for host in hosts:
            self.__start_time()
            try:
                uri = "%s://%s:%s%s" % (proto, host, port, path)
                client = get_client(uri, conf)
                res = client.ping()
            except:
                res = False
            self.__stop_time()
            self.__printline([engine, host, port, "openstack keystone ping", res, self.elapsed])

    def zabbix(self):
        from beedrones.zabbix.client import ZabbixManager

        engine = "zabbix"
        conf = self.__get_orchestrator(engine)
        if conf is None:
            return None

        hosts = conf.get("hosts", [])
        proto = conf.get("proto", "http")
        port = conf.get("port", 0)
        path = conf.get("path", "")

        def get_client(uri, conf):
            client = ZabbixManager(uri=uri)
            client.set_timeout(10.0)
            client.authorize(conf.get("user", ""), conf.get("pwd", ""))
            return client

        for host in hosts:
            self.__start_time()
            uri = "%s://%s:%s%s" % (proto, host, port, path)
            client = get_client(uri, conf)
            res = client.ping()
            self.__stop_time()
            self.__printline([engine, host, port, "zabbix ping", res, self.elapsed])

    def awx(self):
        from beedrones.awx.client import AwxManager

        engine = "awx"
        conf = self.__get_orchestrator(engine)
        if conf is None:
            return None

        hosts = conf.get("hosts", [])
        proto = conf.get("proto", "http")
        port = conf.get("port", 0)
        path = conf.get("path", "")

        def get_client(uri, conf):
            client = AwxManager(uri)
            client.authorize(conf.get("user"), conf.get("pwd"), key=self.key)
            return client

        for host in hosts:
            self.__start_time()
            uri = "%s://%s:%s%s" % (proto, host, port, path)
            client = get_client(uri, conf)
            res = client.ping()
            self.__stop_time()
            self.__printline([engine, host, port, "awx get token", res, self.elapsed])

    def elk(self):
        from elasticsearch import Elasticsearch

        engine = "elk"
        conf = self.__get_orchestrator(engine)
        if conf is None:
            return None

        hosts = conf.get("hosts", [])

        def get_client(host, conf):
            user = conf.get("user")
            pwd = conf.get("pwd")
            ssl = conf.get("ssl")
            use_ssl = False
            verify_certs = False
            if ssl is True:
                use_ssl = True
            if user is not None and pwd is not None:
                http_auth = (user, pwd)
            else:
                http_auth = None

            if use_ssl is False:
                host_url = "http://" + str(host) + ":9200"
            else:
                host_url = "https://" + str(host) + ":9200"

            client = Elasticsearch(
                [host_url],
                http_auth=http_auth,
                # use_ssl=use_ssl,
                verify_certs=verify_certs,
                timeout=60,
            )
            return client

        for host in hosts:
            self.__start_time()
            client = get_client(host, conf)
            res = client.ping()
            self.__stop_time()
            self.__printline([engine, host, "", "elastic ping", res, self.elapsed])

    def ontap(self):
        from beedrones.ontapp.client import OntapManager

        engine = "ontap"
        conf = self.__get_orchestrator(engine)
        if conf is None:
            return None

        host = self.config.get("host")
        port = self.config.get("port", 80)
        proto = self.config.get("proto", "http")
        user = self.config.get("user")
        pwd = self.config.get("pwd")
        self.client = OntapManager(host, user, pwd, port=port, proto=proto, timeout=30.0)
        self.client.authorize()


class CliPlatformController(BaseController):
    class Meta:
        label = "platform"
        stacked_on = "base"
        stacked_type = "nested"
        description = "platform management"
        help = "platform management"

    def _default(self):
        self._parser.print_help()

    def pre_command_run(self):
        super(CliPlatformController, self).pre_command_run()

        self.DEFAULT_ENGINE = ["nginx", "mariadb", "k8s", "vsphere", "openstack", "zabbix", "awx", "elk", "ontap"]

    @ex(
        help="check platform status",
        description="check platform status",
        arguments=ARGS(
            [
                (
                    ["-engines"],
                    {
                        "help": "engine name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def check(self):
        engines = self.app.pargs.engines

        check_engine = CheckEngine(self.app, self.env, self.key)
        if engines is None:
            engines = self.DEFAULT_ENGINE
        elif engines not in self.DEFAULT_ENGINE:
            raise Exception("engine can be only one of thiese: %s" % self.DEFAULT_ENGINE)

        check_engine.print_header()

        if isinstance(engines, list):
            for engine in engines:
                getattr(check_engine, engine)()
        else:
            getattr(check_engine, engines)()

        # proxysql
        # rabbit
        # redis

        # # veeam
        # # trilio
        # # radware
        # # dns
        # # squid
        # # socks

    @ex(
        help="get platform versions",
        description="get platform versions",
        arguments=ARGS(
            [
                (
                    ["-engine"],
                    {
                        "help": "engine name",
                        "action": "store",
                        "type": str,
                        "default": "all",
                    },
                ),
            ]
        ),
    )
    def version(self):
        engine = self.app.pargs.engine

        print(self.line_tmpl % ("engine", "host", "port", "action", "status"))
        print(self.separator)

        # openstack
        if engine in ["all", "openstack"]:
            self.__check_openstack()
