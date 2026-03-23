# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from logging import getLogger, DEBUG
from os import listdir
from os.path import expanduser
from re import findall, search
from sys import path
from datetime import datetime
from time import time, sleep
from requests import get
from yaml import full_load
from cement import ex
from beecell.logger import LoggerHelper
from beecell.types.type_string import str2bool, truncate
from beecell.types.type_dict import dict_get
from beecell.types.type_date import format_date
from beecell.simple import dynamic_import
from beehive3_cli.core.controller import BaseController, PAGINATION_ARGS, ARGS
from beehive3_cli.core.util import load_config, load_environment_config
from beehive3_cli.plugins.platforms.controllers import ChildPlatformController
from beehive3_cli.plugins.platforms.controllers.k8s import BaseK8sController
from beehive3_cli.plugins.platforms.util.platform_customize import CostomizeManager
from beehive3_cli.translate import _


class LoggerHelperLevel():
    CRITICAL = 50
    FATAL = 50
    ERROR = 40
    WARNING = 30
    WARN = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0
    DEBUG2 = -10
    DEBUG3 = -20

    def get(self, level):
        return getattr(self, level, self.DEBUG)


class CmpController(BaseK8sController):
    class Meta:
        label = "cmp"
        description = _("cmp management")
        help = _("cmp management")

    # @ex(
    #     help='get cmp packages version',
    #     description='get cmp packages version',
    #     arguments=ARGS()
    # )
    # def versions(self):
    #     cmds = [
    #         'cd /usr/local/lib/beehive/beehive100/lib/python2.7/site-packages',
    #         "python -c 'import beehive; print(beehive.__version__)'",
    #         "python -c 'import beecell; print(beecell.__version__)'",
    #         "python -c 'import beedrones; print(beedrones.__version__)'",
    #         "python -c 'import beehive_oauth2; print(beehive_oauth2.__version__)'",
    #         "python -c 'import beehive_resource; print(beehive_resource.__version__)'",
    #         "python -c 'import beehive_service; print(beehive_service.__version__)'",
    #         "python -c 'import beehive_ssh; print(beehive_ssh.__version__)'"
    #     ]
    #     res = self.ansible_task('beehive', '&&'.join(cmds), frmt='custom')
    #     if res is None:
    #         raise Exception("Could not get versions. Is Ansible properly configured in order to work in %s "
    #                         "inventory?" % self.env)
    #     ver = [
    #         {'package': 'beehive', 'version': res[0]},
    #         {'package': 'beecell', 'version': res[1]},
    #         {'package': 'beedrones', 'version': res[2]},
    #         {'package': 'beehive_oauth2', 'version': res[3]},
    #         {'package': 'beehive_resource', 'version': res[4]},
    #         {'package': 'beehive_service', 'version': res[5]},
    #         {'package': 'beehive_ssh', 'version': res[6]},
    #     ]
    #
    #     self.app.render(ver, headers=['package', 'version'])


class CmpTestController(ChildPlatformController):
    class Meta: # type: ignore
        label = "tests"
        stacked_on = "cmp"
        stacked_type = "nested"
        description = _("cmp test management")
        help = _("cmp test management")

    def _verbose_log_path(self, l_path: str):
        if self.app.config.get("log.clilog", "verbose_log"):
            transform = {"msg": lambda x: self.color_string(x, "YELLOW")}
            log_message = f"Searching for test files in {l_path}"
            self.app.render({"msg": log_message}, transform=transform)
            self.app.log.debug(log_message)

    @ex(
        help=_("list cmp regression tests"),
        description=_("list cmp regression tests"),
        arguments=ARGS(
            PAGINATION_ARGS,
            [
                (
                    ["-package"],
                    {
                        "help": _("python package"),
                        "action": "store",
                        "type": str,
                        "default": "beehive_tests",
                    },
                ),
                (
                    ["-plan"],
                    {
                        "help": _("name of the test plan"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group"],
                    {
                        "help": _("name of the sub test group"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ],
        ),
    )
    def get(self):
        package = self.app.pargs.package
        plan = self.app.pargs.plan
        group = self.app.pargs.group
        local_package_path = expanduser(self.app.config.get("beehive", "local_package_path"))
        self._verbose_log_path(local_package_path)
        if package is not None and plan is not None:
            prj = package.replace("_", "-")
            path.append(f"{local_package_path}/{prj}")
            test_run = dynamic_import(f"{package}.regression.{plan}")
            test_groups = filter(lambda x: x.find("tests_") == 0, dir(test_run))

            if group is not None:
                self.app.render(
                    [
                        {
                            "package": package,
                            "test-plan": plan,
                            "test-group": group,
                            "idx": p,
                            "test": i,
                        }
                        for p, i in enumerate(getattr(test_run, group))
                    ],
                    headers=["package", "test-plan", "test-group", "idx", "test"],
                )
            else:
                self.app.render(
                    [{"package": package, "test-plan": plan, "test-group": i} for i in test_groups],
                    headers=["package", "test-plan", "test-group"],
                )
        else:
            packages = [
                "beehive_tests",
            ]
            res = []
            for package in packages:
                prj = package.replace("_", "-")
                test_file = f"{local_package_path}/{prj}/{package}/regression"
                try:
                    files = listdir(expanduser(test_file))
                    for file in files:
                        if file != "__init__.py" and file[-2:] == "py":
                            test_name = file.replace(".py", "")
                            res.append({"package": package, "test-plan": test_name})
                except:
                    pass

            self.app.render(res, headers=["package", "test-plan"])

    @ex(
        help=_("run cmp regression tests"),
        description=_("run cmp regression tests"),
        arguments=ARGS(
            PAGINATION_ARGS,
            [
                (
                    ["-package"],
                    {
                        "help": _("python package"),
                        "action": "store",
                        "type": str,
                        "default": "beehive_tests",
                    },
                ),
                (
                    ["-plan"],
                    {
                        "help": _("name of the test plan"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group"],
                    {
                        "help": _("name of the sub test group"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-list"],
                    {
                        "help": _("list of test id to run"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-test"],
                    {
                        "help": _("name of test to run"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-mainconf"],
                    {
                        "help": _("optional main test configuration"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-conf"],
                    {
                        "help": _("optional extra test configuration"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-validate"],
                    {
                        "help": _("if True enable api validation in test"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-user"],
                    {
                        "help": _("user used to run test. Ex. test1, admin [default=test1]"),
                        "action": "store",
                        "type": str,
                        "default": "test1",
                    },
                ),
                (
                    ["-concurrency"],
                    {
                        "help": _("specify how many tests run in parallel for massive test [default=2]"),
                        "action": "store",
                        "type": str,
                        "default": 2,
                    },
                ),
                (
                    ["-failfast"],
                    {
                        "help": _("specify failfast [default=True]"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
                (
                    ["-fromtest"],
                    {
                        "help": _("from test: group name or test name (skip tests before)"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-totest"],
                    {
                        "help": _("to test: group name or test name (skip tests after)"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ],
        ),
    )
    def run(self):
        package = self.app.pargs.package
        plan = self.app.pargs.plan
        group = self.app.pargs.group
        test = self.app.pargs.test
        tests = self.app.pargs.list
        config = self.app.pargs.mainconf
        extra_config = self.app.pargs.conf
        validate = self.app.pargs.validate
        user = self.app.pargs.user
        l_max = self.app.pargs.concurrency

        failfast = self.app.pargs.failfast
        fromtest = self.app.pargs.fromtest
        totest = self.app.pargs.totest
        b_failfast = str2bool(failfast)

        local_package_path = expanduser(self.app.config.get("beehive", "local_package_path"))
        if config is None:
            config = f"{local_package_path}/beehive-tests/beehive_tests/configs/test/beehive.yml"
        self._verbose_log_path(local_package_path)
        args = {
            "conf": config,
            "exconf": extra_config,
            "validate": validate,
            "user": user,
            "max": int(l_max),
            "failfast": b_failfast,
        }

        prj = package.replace("_", "-")
        local_path = expanduser(self.app.config.get("beehive", "local_package_path"))
        test_file = f"{local_path}/{prj}/{package}/regression"

        file_list = [f.replace(".py", "") for f in listdir(test_file)]
        if plan in file_list:
            path.append(f"{local_package_path}/{prj}")
            test_run = dynamic_import(f"{package}.regression.{plan}")
            if group is not None and test is None:
                test_run.tests = getattr(test_run, group)

            elif test is not None:
                test_run.tests = [test]

            print("run tests:")

            # print("AAA test_run.tests: %s" % test_run.tests)
            if fromtest is not None:
                b_found = False
                tests = []

                if isinstance(test_run.tests, dict):
                    tests = {}
                    keys = list(test_run.tests.keys())
                    for key in keys:
                        if key == fromtest:
                            b_found = True
                        if b_found:
                            tests[key] = test_run.tests.get(key)
                else:
                    for item in test_run.tests:
                        if item == fromtest:
                            b_found = True
                        if b_found:
                            tests.append(item)

                test_run.tests = tests

            if totest is not None:
                b_found = False
                tests = []
                for item in test_run.tests:
                    if not b_found:
                        tests.append(item)
                    if item == totest:
                        b_found = True

                test_run.tests = tests

            # print("BBB test_run.tests: %s" % test_run.tests)
            for item in test_run.tests:
                print(f"- {item}")
            test_run.run(args)
        raise Exception(f"Test {plan} is not available")


class CmpSubsystemController(BaseK8sController):
    class Meta:
        label = "subsystems"
        stacked_on = "cmp"
        stacked_type = "nested"
        description = _("cmp subsystems management")
        help = _("cmp subsystems management")

        available_subsytems = ["auth", "event", "ssh", "resource", "service"]
        available_subsytems_api = {
            "auth": "/v1.0/nas",
            "event": "/v1.0/nes",
            "ssh": "/v1.0/gas",
            "resource": "/v1.0/nrs",
            "service": "/v1.0/nws",
        }
        available_packages = [
            "beecell",
            "beedrones",
            "beehive",
            "beehive-oauth2",
            "beehive-resource",
            "beehive-resource-bck",
            "beehive-service",
            "beehive-service-netaas",
            "beehive-ssh",
        ]

    def __multi_get(self, data, key, separator="."):
        keys = key.split(separator)
        res = data
        for k in keys:
            if isinstance(res, list):
                try:
                    res = res[int(k)]
                except:
                    res = {}
            else:
                if res is not None:
                    res = res.get(k, {})
        # if isinstance(res, list):
        #     res = res
        if res is None or res == {}:
            res = "-"

        return res

    def pre_command_run(self):
        super().pre_command_run()

        self.cmp_config = self.config.get("cmp", {})
        self.prefix_path = self.cmp_config.get("prefix_path")

    def template(self, data, l_vars):
        m = findall(r"\{\{[\s\w\.]+\}\}", data)
        for i in m:
            keys = i[3:-3]
            value = str(self.__multi_get(l_vars, keys))
            value = self.template(value, l_vars)
            data = data.replace(i, value)
        return data

    def __sync(self, pkgs, base_remote_package_path):
        from beecell.paramiko_shell.shell import Rsync

        if pkgs == "all":
            pkgs = self._meta.available_packages
        else:
            pkgs = pkgs.split(",")

        user = dict_get(self.conf, "ssh.user")
        pwd = dict_get(self.conf, "ssh.pwd")
        host = dict_get(self.conf, "hosts.0")

        rsync_client = Rsync(user=user, pwd=pwd)
        rsync_client.add_exclude("*.pyc")
        rsync_client.add_exclude("*.pyo")
        rsync_client.add_exclude("__pycache__")

        for pkg in pkgs:
            if pkg not in self._meta.available_packages:
                continue

            local_package_path = f"{self.local_package_path}/{pkg}"
            remote_package_path = f"{user}@{host}:{base_remote_package_path}"
            rsync_client.run(local_package_path, remote_package_path)
            print(f"sync package {pkg} to {remote_package_path}")

    def __create_subsystem(self, update=False):
        from beehive.common.helper import BeehiveHelper

        # self.disable_progress()
        #subsystem = self.app.pargs.subsystem
        file_name = self.app.pargs.file

        # get ansible inventory with vars as dict
        # vars = self.get_inventory_dict('beehive')

        # read template file
        # file_name = self.ansible_path + '/subsystems/%s-system.yml' % subsystem
        # config = load_config(file_name)

        with open(file_name, "r", encoding="utf-8") as f:
            config = f.read()

        mysql = dict_get(self.config, f"orchestrators.mariadb.{self.env}")
        self.config["mysql"] = {
            "host": dict_get(mysql, "hosts.0"),
            "port": dict_get(mysql, "port"),
        }

        # apply vars to template
        config = self.app.template.render(config, self.config)
        config = full_load(config)

        # setup logger on stdout
        frmt = "%(asctime)s - %(message)s"
        LoggerHelper.simple_handler([getLogger("beehive")], DEBUG, frmt=frmt)

        # create and run subsystem helper
        helper = BeehiveHelper()
        helper.create_subsystem(config, update=update)

    @ex(
        help=_("get cmp subsystem config"),
        description=_("get cmp subsystem config"),
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        import sh

        oid = self.app.pargs.id
        info_path = f"{self.ansible_path}/k8s/cmp"

        if oid is None:
            deploy = []
            for subsystem in self._meta.available_subsytems:
                subsystem_path = f"{info_path}/{subsystem}/base"
                files = listdir(expanduser(subsystem_path))
                deploy.extend(
                    [
                        {"subsystem": subsystem, "component": f.rstrip(".yml")}
                        for f in files
                        if f not in ["_res", "kustomization.yml"]
                    ]
                )

            self.app.render(deploy, headers=["subsystem", "component"])
        elif oid in self._meta.available_subsytems:
            subsystem_path = f"{info_path}/{oid}/{self.env}"
            data = load_config(f"{expanduser(subsystem_path)}/kustomization.yml")
            namespace = data.get("namespace")
            params = dict_get(data, "configMapGenerator.0.literals")

            try:
                deploy_data = sh.kubectl("kustomize", subsystem_path)
            except sh.CommandNotFound as e:
                raise Exception("command kubectl not found") from e

            deploy_datas = [full_load(d) for d in deploy_data.split("---")]

            # print data
            self.c("\nnamespace:", "underline")
            print(namespace)

            self.c("\nsubsystem items:", "underline")
            items = []
            for d in deploy_datas:
                kind = d.get("kind")

                if kind == "ConfigMap":
                    item = {
                        "kind": kind,
                        "name": dict_get(d, "metadata.name"),
                    }
                    items.append(item)
                    # print(dict_get(d, 'data'))
                elif kind == "Deployment":
                    for c in dict_get(d, "spec.template.spec.containers"):
                        item = {
                            "kind": kind,
                            "name": dict_get(d, "metadata.name"),
                            "role": dict_get(d, "metadata.labels.role"),
                            "replicas": dict_get(d, "spec.replicas"),
                            "container": {
                                "name": c.get("name"),
                                "cmd": " ".join(c.get("command")),
                                "image": c.get("image"),
                            },
                        }
                        items.append(item)
            self.app.render(
                items,
                headers=[
                    "kind",
                    "name",
                    "role",
                    "replicas",
                    "container.name",
                    "container.image",
                    "container.cmd",
                ],
            )

            self.c("\nparams:", "underline")
            printed_params = []
            for param in params:
                values = param.split("=")
                key = values[0]
                value = "=".join(values[1:])
                printed_params.append({"key": key, "value": value})
            self.app.render(printed_params, headers=["key", "value"], maxsize=200)

    @ex(
        help=_("get cmp subsystems"),
        description=_("get cmp subsystems"),
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": _("deployment role"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def runtime_get(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        namespace = self.default_namespace

        services = []
        deploys = []
        pods = []
        if oid is None:
            services = self.show_application("core", namespace, kinds=["Service"])

            deploys = []
            for subsystem in self._meta.available_subsytems:
                deploys.extend(self.show_application(subsystem, namespace, kinds=["Deployment"]))
        elif oid in self._meta.available_subsytems:
            services = self.show_application("core", namespace, kinds=["Service"])
            services = [k for k in services if k.metadata.name.find(oid) > 0]
            deploys = self.show_application(oid, namespace, kinds=["Deployment"])
            if role is not None:
                name = f"{role}-{oid}"
                deploys = [d for d in deploys if d.metadata.name.find(name) >= 0]
                pods = self.list_pod(namespace, name=name, as_dict=True)

        self.c("\nservices", "underline")
        self.print_k8s_response(services, kinds=["Service"])

        self.c("\ndeploys", "underline")
        self.print_k8s_response(deploys, kinds=["Deployment"])

        if len(pods) > 0:
            self.c("\npods", "underline")
            headers = [
                "name",
                "status",
                "ip",
                "host_ip",
                "namespace",
                "container",
                "date",
            ]
            fields = [
                "metadata.name",
                "status.phase",
                "status.pod_ip",
                "status.container_statuses.0.container_id",
                "status.host_ip",
                "status.container_statuses.0.image",
                "status.start_time",
            ]
            self.app.render(pods, headers=headers, fields=fields, maxsize=45)

    @ex(
        help=_("ping cmp subsystems"),
        description=_("ping cmp subsystems"),
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": _("deployment role"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def runtime_ping(self):
        #oid = self.app.pargs.id
        #role = self.app.pargs.role
        namespace = self.default_namespace

        services = self.list_service(namespace, name="clusterip")
        items = []
        for service in services:
            for k8s_host in self.k8s_hosts:
                item = {
                    "kind": service.kind,
                    "name": service.metadata.name,
                    "namespace": service.metadata.namespace,
                    "type": service.spec.type,
                    "cluster_ip": service.spec.cluster_ip,
                    "k8s_host": k8s_host,
                    "node_port": service.spec.ports[0].node_port,
                    "target_port": service.spec.ports[0].target_port,
                    "creation_date": format_date(service.metadata.creation_timestamp),
                }
                items.append(item)

        template = "{:10} {:30} {:>8} {:30} {:9} {:9} {:6} {:>8}"
        headers = [
            "service",
            "host",
            "port",
            "remote_uri",
            "api_ping",
            "sql_ping",
            "redis_ping",
            "redis_identity_ping",
            "status",
            "elapsed",
        ]
        ok = self.app.colored_text.output("OK", "GREEN")
        ko = self.app.colored_text.output("KO", "RED")

        if self.is_output_dynamic():
            self.app.render(None, headers=headers, template=template)

        resp = []

        for item in items:
            port = item.get("node_port")
            host = item.get("k8s_host")
            name = item.get("name").replace("-clusterip", "").replace("uwsgi-", "")

            start = time()
            api = self._meta.available_subsytems_api.get(name)
            url = f"http://{host}:{port}{api}/ping"
            self.app.log.debug(url)
            resd = {"service": name, "host": host, "port": port, "remote_uri": ""}
            res = [name, host, port]
            resp.append(resd)
            try:
                # issue a get request
                http = get(url, timeout=120)
                response = http.json()
                self.app.log.debug(f"ping {url}: {response}")
                if http.status_code == 200:
                    sql_ping = response.get("sql_ping")
                    redis_ping = response.get("redis_ping")
                    redis_identity_ping = response.get("redis_identity_ping")
                    status = ko
                    if response.get("sql_ping") is True:
                        status = ok
                    res.extend(
                        [
                            response.get("uri"),
                            True,
                            sql_ping,
                            status,
                            round(time() - start, 3),
                            True,
                        ]
                    )
                    resd["elapsed"] = round(time() - start, 3)
                    resd["api_ping"] = True
                    resd["status"] = status
                    resd["remote_uri"] = response.get("uri")
                    resd["sql_ping"] = sql_ping
                    resd["redis_ping"] = redis_ping
                    resd["redis_identity_ping"] = redis_identity_ping
                else:
                    res.extend(["", False, False, ko, round(time() - start, 3)])
                    resd["elapsed"] = round(time() - start, 3)
                    resd["api_ping"] = False
                    resd["sql_ping"] = False
                    resd["redis_ping"] = False
                    resd["redis_identity_ping"] = False
                    resd["status"] = "KO"
            except Exception as exception:
                self.app.log.error(exception, exc_info=False)
                res.extend(["", False, False, ko, round(time() - start, 3)])
                resd["elapsed"] = round(time() - start, 3)
                resd["api_ping"] = False
                resd["sql_ping"] = False
                resd["redis_ping"] = False
                resd["redis_identity_ping"] = False
                resd["status"] = "KO"

            if self.is_output_dynamic():
                self.app.render(res, template=template)

        if self.is_output_dynamic() is False:
            self.app.render(resp, headers=headers, table_style="simple")

    def send_api_request(self, host, port, l_path):
        url = f"http://{host}:{port}{l_path}"
        self.app.log.debug(f"send request to {url}")
        # issue a get request
        #start = time()
        http = get(url, timeout=120)
        response = http.json()
        self.app.log.debug(f"response: {response}")
        # res['elapsed'] = round(time() - start, 3)
        if http.status_code != 200:
            raise Exception(response.get("error"))
        return response

    def send_api_ping(self, host, port, subsystem):
        try:
            api = self._meta.available_subsytems_api.get(subsystem)
            self.send_api_request(host, port, f"{api}/ping")
            return True
        except:
            return False

    def send_api_spec(self, host, port, subsystem):
        try:
            res = self.send_api_request(host, port, "/apispec_1.json")
            return res
        except:
            return {}

    @ex(
        help=_("get cmp instance openapi spec"),
        description=_("get cmp instance openapi spec"),
        example="beehive platform cmp subsystems runtime-api-spec service -e <env> -f json",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def runtime_api_spec(self):
        oid = self.app.pargs.id
        namespace = self.default_namespace

        services = self.list_service(namespace, name=f"uwsgi-{oid}")
        if len(services) < 1:
            raise Exception(f"no service found for subsystem {oid}")
        service = services[0]

        for k8s_host in self.k8s_hosts:
            port = service.spec.ports[0].node_port
            ping = self.send_api_ping(k8s_host, port, oid)
            if ping is True:
                res = self.send_api_spec(k8s_host, port, oid)
                break

        if self.is_output_text():
            resp = []
            for __, info in res.get("paths").items():
                for method, info2 in info.items():
                    resp.append(
                        {
                            "path": path,  #'%s:%s' % (path, method.upper()),
                            "method": method.upper(),
                            "summary": dict_get(info2, "summary"),  # .split('\n')[0],
                            "parameters": ",".join(
                                [p.get("name", "") for p in dict_get(info2, "parameters", default=[])]
                            ),
                        }
                    )
            self.app.render(resp, headers=["path", "method", "summary"], maxsize=200)
        else:
            self.app.render(res, details=True)

    @ex(
        help=_("get cmp instance swagger web interface"),
        description=_("get cmp instance swagger web interface"),
        example="beehive platform cmp subsystems runtime-apidocs service -e <env>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def runtime_apidocs(self):
        oid = self.app.pargs.id
        namespace = self.default_namespace

        services = self.list_service(namespace, name=f"uwsgi-{oid}")
        if len(services) < 1:
            raise Exception(f"no service found for subsystem {oid}")
        service = services[0]

        resp = []
        for k8s_host in self.k8s_hosts:
            port = service.spec.ports[0].node_port
            ping = self.send_api_ping(k8s_host, port, oid)
            if ping is True:
                resp.append({"url": f"http://{k8s_host}:{port}/apidocs"})
                break

        if self.is_output_text():
            self.app.render(resp, headers=["url"], maxsize=200)
        else:
            self.app.render(resp, details=True)

    @ex(
        help=_("get cmp instance capabilities"),
        description=_("get cmp instance capabilities"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def runtime_capabilities(self):
        oid = self.app.pargs.id
        namespace = self.default_namespace

        services = self.list_service(namespace, name=f"uwsgi-{oid}")
        if len(services) < 1:
            raise Exception(f"no service found for subsystem {oid}")
        service = services[0]

        items = []
        for k8s_host in self.k8s_hosts:
            port = service.spec.ports[0].node_port
            ping = self.send_api_ping(k8s_host, port, oid)
            if ping is True:
                api = self._meta.available_subsytems_api.get(oid)
                res = self.send_api_request(k8s_host, port, f"{api}/api/capabilities")
                for module, apis in res.get("modules", {}).items():
                    for api in apis.get("api", []):
                        item = {
                            "module": module,
                            "method": api.get("method"),
                            "uri": api.get("uri"),
                        }
                        items.append(item)
                break

        headers = ["module", "method", "uri"]
        self.app.render(items, headers=headers)

    @ex(
        help=_("get cmp instance versions"),
        description=_("get cmp instance versions"),
        example="beehive platform cmp subsystems runtime-version service",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def runtime_version(self):
        oid = self.app.pargs.id
        namespace = self.default_namespace
        self.app.pargs.notruncate = True

        services = self.list_service(namespace, name=f"uwsgi-{oid}")
        if len(services) < 1:
            # raise Exception('no service found for subsystem %s and role %s' % (oid, role))
            raise Exception(f"no service found for subsystem {oid}")
        service = services[0]
        # print("service: %s" % service)

        packages = []
        image_info = {}
        for k8s_host in self.k8s_hosts:
            port = service.spec.ports[0].node_port
            ping = self.send_api_ping(k8s_host, port, oid)
            if ping is True:
                api = self._meta.available_subsytems_api.get(oid)
                # print("api: %s" % api)
                res = self.send_api_request(k8s_host, port, f"{api}/versions")
                packages = res.get("packages", [])
                image_info = res.get("image_info", {})
                break

        headers = ["name", "version", "git_last_commit"]
        self.app.render(packages, headers=headers)

        self.c("\nimage", "underline")
        self.app.render(image_info, details=True)

    @ex(
        help=_("get cmp subsystem pod log"),
        description=_("get cmp subsystem pod log"),
        arguments=ARGS(
            [
                (
                    ["subsystem"],
                    {
                        "help": _("subsystem. e.g. resource, service"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["role"],
                    {
                        "help": _("deployment role. e.g. uwsgi"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-follow"],
                    {
                        "help": _("follow log. Default: true."),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-lines"],
                    {
                        "help": _("number of log lines to show. Default: 100. Ignored when follow is true."),
                        "action": "store",
                        "type": int,
                        "default": 100,
                    },
                ),
            ]
        ),
    )
    def runtime_log(self):
        """
        Show k8s pod log
        """
        oid = self.app.pargs.subsystem
        role = self.app.pargs.role
        follow = str2bool(self.app.pargs.follow)
        lines = self.app.pargs.lines
        namespace = self.default_namespace

        name = f"{role}-{oid}"
        self.get_pod_log(namespace, name=name, follow=follow, tail_lines=lines)

    @ex(
        help=_("create cmp subsystem structure (db, data)"),
        description=_("create cmp subsystem structure (db, data)"),
        arguments=ARGS(
            [
                (
                    ["subsystem"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("subsystem config file full path"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def create(self):
        self.__create_subsystem(update=False)

    @ex(
        help=_("update cmp subsystem structure (db, data)"),
        description=_("update cmp subsystem structure (db, data)"),
        arguments=ARGS(
            [
                (
                    ["subsystem"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("subsystem config file full path"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def update(self):
        self.__create_subsystem(update=True)

    @ex(
        help=_("update cmp nivola python packages - use with devel env"),
        description=_("update cmp nivola python packages - use with devel env"),
        arguments=ARGS(
            [
                (
                    ["-path"],
                    {
                        "help": _("remote package path"),
                        "action": "store",
                        "type": str,
                        "default": "/opt/cmp",
                    },
                ),
                (
                    ["-pkgs"],
                    {
                        "help": _("list of package to sync"),
                        "action": "store",
                        "type": str,
                        "default": "all",
                    },
                ),
            ]
        ),
    )
    def sync(self):
        base_remote_package_path = self.app.pargs.path
        pkgs = self.app.pargs.pkgs
        self.__sync(pkgs, base_remote_package_path)

    @ex(
        help=_("deploy cmp subsystem"),
        description=_("deploy cmp subsystem"),
        arguments=ARGS(
            [
                (
                    ["-subsystem"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def deploy(self):
        subsystem = self.app.pargs.subsystem
        namespace = self.default_namespace
        if subsystem is not None and subsystem in self._meta.available_subsytems:
            print(f"deploy: {subsystem}")
            self.deploy_application(subsystem, namespace)
        else:
            first = True
            for subsystem in self._meta.available_subsytems:
                if first is False:
                    sleep(10)
                print(f"deploy: {subsystem}")
                self.deploy_application(subsystem, namespace)
                first = False

    @ex(
        help=_("undeploy cmp subsystem"),
        description=_("undeploy cmp subsystem"),
        arguments=ARGS(
            [
                (
                    ["-subsystem"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def undeploy(self):
        subsystem = self.app.pargs.subsystem
        namespace = self.default_namespace
        if subsystem is not None and subsystem in self._meta.available_subsytems:
            self.undeploy_application(subsystem, namespace)
        else:
            for subsystem in self._meta.available_subsytems:
                self.undeploy_application(subsystem, namespace)

    @ex(
        help=_("redeploy cmp subsystem"),
        description=_("redeploy cmp subsystem"),
        arguments=ARGS(
            [
                (
                    ["subsystem"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-path"],
                    {
                        "help": _("remote package path"),
                        "action": "store",
                        "type": str,
                        "default": "/opt/cmp",
                    },
                ),
                (
                    ["-pkgs"],
                    {
                        "help": _("list of package to sync"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
            ]
        ),
    )
    def redeploy(self):
        subsystem = self.app.pargs.subsystem
        namespace = self.default_namespace
        base_remote_package_path = self.app.pargs.path
        pkgs = self.app.pargs.pkgs

        if subsystem in self._meta.available_subsytems:
            self.undeploy_application(subsystem, namespace)
            self.__sync(pkgs, base_remote_package_path)
            self.deploy_application(subsystem, namespace)
        else:
            raise Exception(f"subsystem can be one of {self._meta.available_subsytems}")

    @ex(
        help=_("maintenance get"),
        description=_("maintenance get"),
        arguments=ARGS(
            [
                (
                    ["subsystem"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def maintenance_get(self):
        subsystem = self.app.pargs.subsystem
        namespace = self.default_namespace

        api = self._meta.available_subsytems_api.get(subsystem)
        if api is None:
            print(self.app.colored_text.output(f"ERROR: subsystem '{subsystem}' not found", "RED"))
            return

        services = self.list_service(namespace, name="clusterip")
        items = []
        for service in services:
            for k8s_host in self.k8s_hosts:
                item = {
                    "kind": service.kind,
                    "name": service.metadata.name,
                    "namespace": service.metadata.namespace,
                    "type": service.spec.type,
                    "cluster_ip": service.spec.cluster_ip,
                    "k8s_host": k8s_host,
                    "node_port": service.spec.ports[0].node_port,
                    "target_port": service.spec.ports[0].target_port,
                    "creation_date": format_date(service.metadata.creation_timestamp),
                }
                # print("item: %s" % item)
                items.append(item)

        for item in items:
            port = item.get("node_port")
            host = item.get("k8s_host")
            name = item.get("name").replace("-clusterip", "").replace("uwsgi-", "")

            if name == subsystem:
                api = self._meta.available_subsytems_api.get(name)
                url = f"http://{host}:{port}{api}/cmp_maintenance"
                self.app.log.debug(url)

                http = get(url, timeout=120)
                response = http.json()
                self.app.log.debug(f"maintenance_get {url}: {response}")
                self.app.render(response.get("methods"), headers=["method", "enabled"])

    @ex(
        help=_("maintenance set"),
        description=_("maintenance set"),
        arguments=ARGS(
            [
                (
                    ["subsystem"],
                    {
                        "help": _("subsystem. Ex. resource, service"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["method"],
                    {
                        "help": _("http method: get, post, put, delete"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["enabled"],
                    {
                        "help": _("enabled True/False"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def maintenance_set(self):
        subsystem = self.app.pargs.subsystem
        method = self.app.pargs.method
        enabled = self.app.pargs.enabled
        # namespace = self.default_namespace
        # print("subsystem: %s" % subsystem)

        api = self._meta.available_subsytems_api.get(subsystem)
        if api is None:
            print(self.app.colored_text.output(f"ERROR: subsystem '{subsystem}' not found", "RED"))
            return

        methods = ["get", "post", "put", "delete"]
        if method not in methods:
            print(self.app.colored_text.output(f"ERROR: method '{method}' incorrect", "RED"))
            return

        if str2bool(enabled) is None:
            print(self.app.colored_text.output(f"ERROR: enabled value '{enabled}' incorrect", "RED"))
            return

        methods = {
            "method": method,
            "enabled": enabled,
        }
        data_methods = {"methods": methods}

        self._meta.cmp = {"baseuri": f"{api}", "subsystem": f"{subsystem}"}
        self.configure_cmp_api_client()

        uri = f"{self.baseuri}/cmp_maintenance"
        self.app.log.debug(uri)
        res = self.cmp_post(uri, data=data_methods, timeout=600)
        self.app.log.debug(f"res: {res}")

        maintenance_set_response = res["MaintenanceSetResponse"]
        ok = maintenance_set_response["ok"]
        if ok is True:
            print(f"set method '{method}' enabled '{enabled}'")


class CmpCustomizeController(BaseController):
    class Meta: # type: ignore
        label = "customize"
        stacked_on = "cmp"
        stacked_type = "nested"
        description = _("cmp customization")
        help = _("cmp customization")

    def pre_command_run(self):
        super().pre_command_run()
        self.config_path = expanduser(self.app.config.get("beehive", "cmp_post_install_path"))

    @ex(
        help=_("get available configurations"),
        description=_("get available configurations"),
        example="beehive platform cmp customize get -e <env>",
        arguments=ARGS([
            (
                ["-local"],
                {
                    "help": _("serch only path from current working diractory. " ),
                    "action": "store_true",
                    "default": False,
                },
            ),]
        ),
    )
    def get(self):
        manager = CostomizeManager(self)
        res = manager.get_available_configs()
        self.app.render(res, headers=["name", "type"])

    @ex(
        help=_("show configuration"),
        description=_("show configuration"),
        example="beehive platform cmp customize show prod/business/vm.m16.large",
        arguments=ARGS(
            [
                (["config"], {"help": _("config file"), "action": "store", "type": str}),
                (
                    ["-filter"],
                    {
                        "help": _(
                            "filter to apply <entity list key>:<key to filter>:<value>. "
                            "Ex. resource.entities.site_networks:name:NVLP3-Prov-WEB2-test"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-local"],
                    {
                        "help": _("serch only path from current working diractory. " ),
                        "action": "store_true",
                        "default": False,
                    },
                ),

            ]
        ),
    )
    def show(self):
        config = self.app.pargs.config
        config_filter = self.app.pargs.filter
        manager = CostomizeManager(self)
        configs = manager.show_configs(config)

        if config_filter is not None:
            manager.apply_filter(config_filter)
            configs = manager.configs

        self.app.render(configs, details=True)

    @ex(
        help=_("run customization. This command can be used many times to add new items"),
        description=_("run customization. This command can be used many times to add new items"),
        example="beehive platform cmp customize run prod/resource/provider/image1 -e <env>",
        arguments=ARGS(
            [
                (["config"], {"help": _("config file"), "action": "store", "type": str}),
                (
                    ["-filter"],
                    {
                        "help": _(
                            "filter to apply <entity list key>:<key to filter>:<value>. "
                            "Ex. resource.entities.site_networks:name:NVLP3-Prov-WEB2-test"
                        ),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-sections"],
                    {
                        "help": _("comma separated list of section to execute"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dry"],
                    {
                        # "help": _("if True no changes were written (where managed!)"),
                        "help": _("Deprecated use flag --dry-run instead"),
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
                (
                    ["-local"],
                    {
                        "help": _("serch only path from current working diractory. " ),
                        "action": "store_true",
                        "default": False,
                    },
                ),

            ]
        ),
    )
    def run(self):
        config = self.app.pargs.config
        config_filter = self.app.pargs.filter
        sections = self.app.pargs.sections
        dry = self.app.pargs.dryrun
        manager = CostomizeManager(self)
        manager.load_configs(config)
        if config_filter is not None:
            manager.apply_filter(config_filter)
        manager.run(sections, dry)

class CmpPostInstallController(CmpCustomizeController):
    class Meta: # type: ignore
        label = "post_install"
        stacked_on = "cmp"
        stacked_type = "nested"
        description = _("DEPRECATED - cmp post install management")
        help = _("DEPRECATED - cmp post install management")


class CmpLog2Controller(ChildPlatformController):
    class Meta: # type: ignore
        label = "logs"
        stacked_on = "cmp"
        stacked_type = "nested"
        description = _("cmp logs management")
        help = _("cmp logs management")

        index_headers = [
            "name",
            "replicas",
            "shards",
            "uuid",
            "version",
            "creation_date",
        ]
        index_fields = [
            "settings.index.provided_name",
            "settings.index.number_of_replicas",
            "settings.index.number_of_shards",
            "settings.index.uuid",
            "settings.index.version.created",
            "settings.index.creation_date",
        ]

    def pre_command_run(self):
        super().pre_command_run()

        self.es = self.config_elastic()

        config = load_environment_config(self.app)

        orchestrators = config.get("orchestrators", {}).get("k8s", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception("No k8s default platform is available for this environment. Select another environment")

        if label not in orchestrators:
            raise Exception(f"Valid label are: {', '.join(orchestrators.keys())}")
        k8s_conf = orchestrators.get(label)
        self.k8s_namespace = k8s_conf.get("default_namespace")
        self.k8s_cluster = k8s_conf.get("cluster")
        self.cmp_cert_postfix = k8s_conf.get("cmp_cert_postfix", "cmp_nivola")

    def get_current_elastic_index(self):
        today = datetime.now().strftime("%Y.%m.%d")
        return f"{self.k8s_cluster}-{self.k8s_namespace}-filebeat-7.12.0-{today}-{self.cmp_cert_postfix}"

    def get_current_elastic_event_index(self):
        today = datetime.now().strftime("%Y.%m.%d")
        return f"cmp-event-{self.elk_env}-pylogbeat-2.0.0-{today}-{self.cmp_cert_postfix}"

    def __transform_msg(self, val):
        pattern = r"\d{4}-\d{2}-\d{2}.*"
        if search(pattern, val):
            try:
                head, msg = val.split("|")
                head = head.split(" ")
                if val.find("INFO") >= 0:
                    msg = self.app.colored_text.output(msg, "WHITE")
                elif val.find("DEBUG2") >= 0:
                    msg = self.app.colored_text.output(msg, "GREEN")
                elif val.find("DEBUG") >= 0:
                    msg = self.app.colored_text.output(msg, "BLUE")
                elif val.find("ERROR") >= 0:
                    msg = self.app.colored_text.output(msg, "RED")
                elif val.find("WARNING") >= 0:
                    msg = self.app.colored_text.output(msg, "YELLOW")
                else:
                    msg = self.app.colored_text.output(msg, "GRAY")

                val = f"{head[2]:8} {head[4]} {head[5]}{msg}"
            except:
                val = self.app.colored_text.output(val, "GRAY")
        else:
            val = self.app.colored_text.output(val, "GRAY")
        return val

    @ex(
        help=_("show log for cmp engine"),
        description=_("show log for cmp engine"),
        example="beehive platform cmp logs engine -pod resource-app-78dc4b74ff-f989q -size 500",
        arguments=ARGS(
            PAGINATION_ARGS,
            [
                (
                    ["-index"],
                    {
                        "help": _("index name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("container partial name. Ex. uwsgi-auth, worker-auth, uwsgi-ssh"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sort"],
                    {
                        "help": _("sort field. Ex. date:desc"),
                        "action": "store",
                        "type": str,
                        "default": "timestamp:desc",
                    },
                ),
                (
                    ["-pod"],
                    {
                        "help": _("pod name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-op"],
                    {
                        "help": _("oepration id. Can be api_id, task_id, task_id:step_name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ],
        ),
    )
    def engine(self):
        index = self.app.pargs.index
        name = self.app.pargs.name
        pod = self.app.pargs.pod
        op = self.app.pargs.op
        sort = self.app.pargs.sort
        page = self.app.pargs.page
        size = self.app.pargs.size

        if index is None:
            index = self.get_current_elastic_index()

        match = []
        if name is not None:
            match.append({"match": {"kubernetes.container.name": {"query": name, "operator": "and"}}})

        if pod is not None:
            match.append({"match": {"kubernetes.pod.name": {"query": pod, "operator": "and"}}})
            # match.append({'query_string': {'query': pod+'*', 'fields': ['kubernetes.pod.name']}})

        if op is not None:
            match.append({"match": {"message": {"query": op, "operator": "and"}}})

        if name is None and pod is None and op is None:
            query = {"bool": {"must": [{"match": {"kubernetes.namespace": {"query": f"beehive-{self.env}"}}}]}}
        else:
            query = {"bool": {"must": match}}

        transform = {
            "container.name": lambda n: truncate(n, 20),
            # 'container.id': lambda n: n[:10],
            "message": self.__transform_msg,
        }
        header = ["timestamp", "host", "container-name", "pod", "message"]
        field = [
            "timestamp",
            "host.name",
            "kubernetes.container.name",
            "kubernetes.pod.name",
            "message",
        ]
        self._query(
            index,
            query,
            page,
            size,
            sort,
            header=header,
            field=field,
            maxsize=5000,
            transform=transform,
            pretty=False,
        )

    @ex(
        help=_("show cmp events"),
        description=_("show cmp events"),
        arguments=ARGS(
            PAGINATION_ARGS,
            [
                (
                    ["-index"],
                    {
                        "help": _("index name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-kvargs"],
                    {
                        "help": _("kvargs like query string"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": _("event id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("event id"),
                        "action": "store",
                        "type": str,
                        "default": "API",
                    },
                ),
                (
                    ["-sort"],
                    {
                        "help": _("sort field. Ex. date:desc"),
                        "action": "store",
                        "type": str,
                        "default": "@timestamp:desc",
                    },
                ),
            ],
        ),
    )
    def event(self):
        index = self.app.pargs.index
        eventid = self.app.pargs.id
        event_type = self.app.pargs.type
        kvargs = self.app.pargs.kvargs
        sort = self.app.pargs.sort
        page = self.app.pargs.page
        size = self.app.pargs.size

        if index is None:
            index = self.get_current_elastic_event_index()

        if eventid is None:
            match = [
                {"match": {"type": {"query": event_type, "operator": "or"}}},
            ]
        else:
            match = [
                {"match": {"event_id": {"query": eventid, "operator": "and"}}},
            ]
        if kvargs is not None:
            match.append({"match_phrase": {"data.kwargs": kvargs}})

        query = {"bool": {"must": match}}
        data = self._query(index, query, page, size, sort, render=False).get("values")
        if eventid is None:
            headers = [
                "event_id",
                "opid",
                "op",
                "@timestamp",
                "elapsed",
                "response",
                "user",
                "ip",
                "dest-ip",
                "dest-port",
            ]
            fields = [
                "event_id",
                "data.opid",
                "data.op",
                "@timestamp",
                "data.elapsed",
                "data.response.0",
                "source.user",
                "source.ip",
                "dest.ip",
                "dest.port",
            ]
            self.app.render(data, headers=headers, fields=fields, maxsize=100)
        else:
            self.app.render(data[0], details=True)

    @ex(
        help=_("get api request received"),
        description=_("get api request received"),
        example="beehive platform cmp logs api -e <env>",
        arguments=ARGS(
            PAGINATION_ARGS,
            [
                (
                    ["-index"],
                    {
                        "help": _("index name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": _("api request id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-uri"],
                    {
                        "help": _("api request ri. uri:method"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-user"],
                    {
                        "help": _("api request source user"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ip"],
                    {
                        "help": _("api request source ip"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sort"],
                    {
                        "help": _("sort field. Ex. @timestamp:desc"),
                        "action": "store",
                        "type": str,
                        "default": "@timestamp:desc",
                    },
                ),
            ],
        ),
    )
    def api(self):
        index = self.app.pargs.index
        eventid = self.app.pargs.id
        sort = self.app.pargs.sort
        page = self.app.pargs.page
        size = self.app.pargs.size
        uri = self.app.pargs.uri
        user = self.app.pargs.user
        ip = self.app.pargs.ip

        if index is None:
            index = self.get_current_elastic_event_index()

        if eventid is None:
            match = [
                {"match": {"type": {"query": "API", "operator": "and"}}},
            ]
        else:
            match = [
                {"match": {"event_id": {"query": eventid, "operator": "and"}}},
            ]

        if uri is not None:
            match.append({"match": {"data.op": {"query": uri, "operator": "and"}}})
        if user is not None:
            match.append({"match": {"source.user": {"query": user, "operator": "and"}}})
        if ip is not None:
            match.append({"match": {"source.ip": {"query": ip, "operator": "and"}}})

        query = {"bool": {"must": match}}

        if eventid is None:
            headers = [
                "id",
                "api_id",
                "@timestamp",
                "uri",
                "elapsed",
                "response-code",
                "user",
                "source",
                "dest",
            ]
            fields = [
                "event_id",
                "data.api_id",
                "@timestamp",
                "data.op",
                "data.elapsed",
                "data.response.0",
                "source.user",
                "source.ip",
                "dest.ip",
            ]
            data = self._query(index, query, page, size, sort, render=False).get("values")
            # if self.is_output_text():
            #     for i in data:
            #         path = dict_get(i, 'data.op').split(':')
            #         i['path'] = path[0]
            #         i['method'] = path[-1]
            self.app.render(data, headers=headers, fields=fields, maxsize=100)
        else:
            api = self._query(index, query, page, 200, sort, render=False).get("values")[0]
            apiid = dict_get(api, "data.api_id")
            if self.is_output_text():
                query = {
                    "bool": {
                        "must": [
                            {"match": {"data.api_id": {"query": apiid, "operator": "and"}}},
                        ]
                    }
                }
                data = self._query(index, query, page, 200, sort, render=False).get("values")
                newdata = []
                for item in data:
                    if dict_get(item, "event_id") != eventid:
                        newdata.append(item)
                newdata.reverse()

                dest = api.pop("dest")
                source = api.pop("source")
                inner_data = api.pop("data")

                self.app.render(api, details=True)
                self.c("\nsource", "underline")
                self.app.render(source, details=True)
                self.c("\ndestination", "underline")
                self.app.render(dest, details=True)
                self.c("\ndata", "underline")
                self.app.render(inner_data, details=True)
                self.c("\nworkflow", "underline")
                headers = [
                    "opid",
                    "@timestamp",
                    "type",
                    "operation",
                    "elapsed",
                    "response-code",
                    "user",
                    "ip-addr",
                    "dest-ip-addr",
                    "dest-port",
                ]
                fields = [
                    "data.opid",
                    "@timestamp",
                    "type",
                    "data.op",
                    "data.elapsed",
                    "data.response.0",
                    "source.user",
                    "source.ip",
                    "dest.ip",
                    "dest.port",
                ]
                self.app.render(newdata, headers=headers, fields=fields, maxsize=100)
            else:
                self.app.render(api, details=True, maxsize=100)
