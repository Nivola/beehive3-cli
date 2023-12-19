# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from logging import getLogger, DEBUG
from os import listdir
from re import findall, search
from sys import path
from base64 import b64decode
from datetime import datetime
from time import time, sleep
from requests import get
from yaml import full_load
import sh
from cement import ex
from beecell.logger import LoggerHelper
from beecell.paramiko_shell.shell import ParamikoShell, Rsync
from beecell.types.type_string import str2bool, truncate
from beecell.types.type_dict import dict_get
from beecell.types.type_date import format_date
from beecell.simple import dynamic_import
from beehive.common.helper import BeehiveHelper
from beehive3_cli.core.controller import BaseController, PAGINATION_ARGS, ARGS
from beehive3_cli.core.util import load_config, load_environment_config
from beehive3_cli.plugins.platform.controllers import ChildPlatformController
from beehive3_cli.plugins.platform.controllers.k8s import BaseK8sController
from beehive3_cli.plugins.platform.util.platform_customize import CostomizeManager


class LoggerHelperLevel(object):
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
        description = "cmp management"
        help = "cmp management"

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
    class Meta:
        label = "tests"
        stacked_on = "cmp"
        stacked_type = "nested"
        description = "cmp test management"
        help = "cmp test management"

    @ex(
        help="list cmp regression tests",
        description="list cmp regression tests",
        arguments=ARGS(
            PAGINATION_ARGS,
            [
                (
                    ["-package"],
                    {
                        "help": "python package",
                        "action": "store",
                        "type": str,
                        "default": "beehive_tests",
                    },
                ),
                (
                    ["-plan"],
                    {
                        "help": "name of the test plan",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group"],
                    {
                        "help": "name of the sub test group",
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
        if package is not None and plan is not None:
            prj = package.replace("_", "-")
            path.append("%s/%s" % (self.app.config.get("beehive", "local_package_path"), prj))
            test_run = dynamic_import("%s.regression.%s" % (package, plan))
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
                test_file = "%s/%s/%s/regression" % (
                    self.app.config.get("beehive", "local_package_path"),
                    prj,
                    package,
                )
                try:
                    files = listdir(test_file)
                    for file in files:
                        if file != "__init__.py" and file[-2:] == "py":
                            test_name = file.replace(".py", "")
                            res.append({"package": package, "test-plan": test_name})
                except:
                    pass

            self.app.render(res, headers=["package", "test-plan"])

    @ex(
        help="run cmp regression tests",
        description="run cmp regression tests",
        arguments=ARGS(
            PAGINATION_ARGS,
            [
                (
                    ["-package"],
                    {
                        "help": "python package",
                        "action": "store",
                        "type": str,
                        "default": "beehive_tests",
                    },
                ),
                (
                    ["-plan"],
                    {
                        "help": "name of the test plan",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-group"],
                    {
                        "help": "name of the sub test group",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-list"],
                    {
                        "help": "list of test id to run",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-test"],
                    {
                        "help": "name of test to run",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-mainconf"],
                    {
                        "help": "optional main test configuration",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-conf"],
                    {
                        "help": "optional extra test configuration",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-validate"],
                    {
                        "help": "if True enable api validation in test",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-user"],
                    {
                        "help": "user used to run test. Ex. test1, admin [default=test1]",
                        "action": "store",
                        "type": str,
                        "default": "test1",
                    },
                ),
                (
                    ["-concurrency"],
                    {
                        "help": "specify how many tests run in parallel for massive test [default=2]",
                        "action": "store",
                        "type": str,
                        "default": 2,
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
        max = self.app.pargs.concurrency

        if config is None:
            config = "%s/beehive-tests/beehive_tests/configs/test/beehive.yml" % self.app.config.get(
                "beehive", "local_package_path"
            )

        args = {
            "conf": config,
            "exconf": extra_config,
            "validate": validate,
            "user": user,
            "max": int(max),
        }

        prj = package.replace("_", "-")
        test_file = "%s/%s/%s/regression" % (
            self.app.config.get("beehive", "local_package_path"),
            prj,
            package,
        )
        file_list = [f.replace(".py", "") for f in listdir(test_file)]
        if plan not in file_list:
            raise Exception("Test %s is not available" % plan)
        else:
            path.append("%s/%s" % (self.app.config.get("beehive", "local_package_path"), prj))
            test_run = dynamic_import("%s.regression.%s" % (package, plan))
            if group is not None:
                if tests is not None:
                    idxs = tests.split(",")
                    all_tests = getattr(test_run, group)
                    tests = []
                    for idx in idxs:
                        tests.append(all_tests[int(idx)])
                    test_run.tests = tests
                else:
                    test_run.tests = getattr(test_run, group)
            elif test is not None:
                test_run.tests = [test]
            print("run tests:")
            for item in test_run.tests:
                print("- %s" % item)
            test_run.run(args)


class CmpSubsystemController(BaseK8sController):
    class Meta:
        label = "subsystems"
        stacked_on = "cmp"
        stacked_type = "nested"
        description = "cmp subsystems management"
        help = "cmp subsystems management"

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
        super(CmpSubsystemController, self).pre_command_run()

        self.cmp_config = self.config.get("cmp", {})
        self.prefix_path = self.cmp_config.get("prefix_path")

    def template(self, data, vars):
        m = findall("\{\{[\s\w\.]+\}\}", data)
        for i in m:
            keys = i[3:-3]
            value = str(self.__multi_get(vars, keys))
            value = self.template(value, vars)
            data = data.replace(i, value)
        return data

    def __get_ssh_client(self):
        keystring = b64decode(dict_get(self.conf, "ssh.sshkey", ""))
        user = dict_get(self.conf, "ssh.user", "")
        host = dict_get(self.conf, "hosts.0", "")
        client = ParamikoShell(host, user, keystring=keystring)
        return client

    def __sync(self, pkgs, base_remote_package_path):
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

            local_package_path = "%s/%s" % (self.local_package_path, pkg)
            remote_package_path = "%s@%s:%s" % (user, host, base_remote_package_path)
            rsync_client.run(local_package_path, remote_package_path)
            print("sync package %s to %s" % (pkg, remote_package_path))

    def __create_subsystem(self, update=False):
        # self.disable_progress()
        subsystem = self.app.pargs.subsystem
        file_name = self.app.pargs.file

        # get ansible inventory with vars as dict
        # vars = self.get_inventory_dict('beehive')

        # read template file
        # file_name = self.ansible_path + '/subsystems/%s-system.yml' % subsystem
        # config = load_config(file_name)
        f = open(file_name, "r")
        config = f.read()
        f.close()

        mysql = dict_get(self.config, "orchestrators.mariadb.%s" % self.env)
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
        help="get cmp subsystem config",
        description="get cmp subsystem config",
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "subsystem. Ex. resource, service",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        info_path = "%s/k8s/cmp" % self.ansible_path

        if oid is None:
            deploy = []
            for subsystem in self._meta.available_subsytems:
                subsystem_path = "%s/%s/%s" % (info_path, subsystem, "base")
                files = listdir(subsystem_path)
                deploy.extend(
                    [
                        {"subsystem": subsystem, "component": f.rstrip(".yml")}
                        for f in files
                        if f not in ["_res", "kustomization.yml"]
                    ]
                )

            self.app.render(deploy, headers=["subsystem", "component"])
        elif oid in self._meta.available_subsytems:
            subsystem_path = "%s/%s/%s" % (info_path, oid, self.env)
            data = load_config("%s/kustomization.yml" % subsystem_path)
            namespace = data.get("namespace")
            params = dict_get(data, "configMapGenerator.0.literals")

            deploy_data = sh.kubectl("kustomize", subsystem_path)
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
        help="get cmp subsystems",
        description="get cmp subsystems",
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "subsystem. Ex. resource, service",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": "deployment role",
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
                name = "%s-%s" % (role, oid)
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
            self.app.render(pods, headers=headers, fields=fields, maxsize=40)

    @ex(
        help="ping cmp subsystems",
        description="ping cmp subsystems",
        arguments=ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "subsystem. Ex. resource, service",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": "deployment role",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def runtime_ping(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
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
            url = "http://%s:%s%s/ping" % (host, port, api)
            self.app.log.debug(url)
            resd = {"service": name, "host": host, "port": port, "remote_uri": ""}
            res = [name, host, port]
            resp.append(resd)
            try:
                # issue a get request
                http = get(url)
                response = http.json()
                self.app.log.debug("ping %s: %s" % (url, response))
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
            except Exception as ex:
                self.app.log.error(ex, exc_info=False)
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

    def send_api_request(self, host, port, path):
        url = "http://%s:%s%s" % (host, port, path)
        self.app.log.debug("send request to %s" % url)
        try:
            # issue a get request
            start = time()
            http = get(url)
            response = http.json()
            self.app.log.debug("response: %s" % response)
            # res['elapsed'] = round(time() - start, 3)
            if http.status_code == 200:
                return response
            else:
                raise Exception(response.get("error"))
        except Exception:
            raise

    def send_api_ping(self, host, port, subsystem):
        try:
            api = self._meta.available_subsytems_api.get(subsystem)
            self.send_api_request(host, port, "%s/ping" % api)
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
        help="get cmp instance openapi spec",
        description="get cmp instance openapi spec",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "subsystem. Ex. resource, service",
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

        services = self.list_service(namespace, name="uwsgi-%s" % oid)
        if len(services) < 1:
            raise Exception("no service found for subsystem %s" % oid)
        service = services[0]

        for k8s_host in self.k8s_hosts:
            port = service.spec.ports[0].node_port
            ping = self.send_api_ping(k8s_host, port, oid)
            if ping is True:
                res = self.send_api_spec(k8s_host, port, oid)
                break

        if self.is_output_text():
            resp = []
            for path, info in res.get("paths").items():
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
        help="get cmp instance swagger web interface",
        description="get cmp instance swagger web interface",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "subsystem. Ex. resource, service",
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

        services = self.list_service(namespace, name="uwsgi-%s" % oid)
        if len(services) < 1:
            raise Exception("no service found for subsystem %s" % oid)
        service = services[0]

        resp = []
        for k8s_host in self.k8s_hosts:
            port = service.spec.ports[0].node_port
            ping = self.send_api_ping(k8s_host, port, oid)
            if ping is True:
                resp.append({"url": "http://%s:%s/apidocs" % (k8s_host, port)})
                break

        if self.is_output_text():
            self.app.render(resp, headers=["url"], maxsize=200)
        else:
            self.app.render(resp, details=True)

    @ex(
        help="get cmp instance capabilities",
        description="get cmp instance capabilities",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "subsystem. Ex. resource, service",
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

        services = self.list_service(namespace, name="uwsgi-%s" % oid)
        if len(services) < 1:
            raise Exception("no service found for subsystem %s" % oid)
        service = services[0]

        items = []
        for k8s_host in self.k8s_hosts:
            port = service.spec.ports[0].node_port
            ping = self.send_api_ping(k8s_host, port, oid)
            if ping is True:
                api = self._meta.available_subsytems_api.get(oid)
                res = self.send_api_request(k8s_host, port, "%s/api/capabilities" % api)
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
        help="get cmp instance versions",
        description="get cmp instance versions",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "subsystem. Ex. resource, service",
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

        services = self.list_service(namespace, name="uwsgi-%s" % oid)
        if len(services) < 1:
            # raise Exception('no service found for subsystem %s and role %s' % (oid, role))
            raise Exception("no service found for subsystem %s" % (oid))
        service = services[0]

        items = []
        for k8s_host in self.k8s_hosts:
            port = service.spec.ports[0].node_port
            ping = self.send_api_ping(k8s_host, port, oid)
            if ping is True:
                api = self._meta.available_subsytems_api.get(oid)
                res = self.send_api_request(k8s_host, port, "%s/versions" % api).get("packages", [])
                break

        headers = ["name", "version"]
        self.app.render(res, headers=headers)

    @ex(
        help="get cmp subsystem pod log",
        description="get cmp subsystem pod log",
        arguments=ARGS(
            [
                (
                    ["subsystem"],
                    {
                        "help": "subsystem. e.g. resource, service",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["role"],
                    {
                        "help": "deployment role. e.g. uwsgi",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-follow"],
                    {
                        "help": "follow log. Default: true.",
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-lines"],
                    {
                        "help": "number of log lines to show. Default: 100. Ignored when follow is true.",
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
        help="create cmp subsystem structure (db, data)",
        description="create cmp subsystem structure (db, data)",
        arguments=ARGS(
            [
                (
                    ["subsystem"],
                    {
                        "help": "subsystem. Ex. resource, service",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": "subsystem config file full path",
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
        help="update cmp subsystem structure (db, data)",
        description="update cmp subsystem structure (db, data)",
        arguments=ARGS(
            [
                (
                    ["subsystem"],
                    {
                        "help": "subsystem. Ex. resource, service",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": "subsystem config file full path",
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
        help="update cmp nivola python packages - use with devel env",
        description="update cmp nivola python packages - use with devel env",
        arguments=ARGS(
            [
                (
                    ["-path"],
                    {
                        "help": "remote package path",
                        "action": "store",
                        "type": str,
                        "default": "/opt/cmp",
                    },
                ),
                (
                    ["-pkgs"],
                    {
                        "help": "list of package to sync",
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
        help="deploy cmp subsystem",
        description="deploy cmp subsystem",
        arguments=ARGS(
            [
                (
                    ["-subsystem"],
                    {
                        "help": "subsystem. Ex. resource, service",
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
            print("deploy: %s" % subsystem)
            self.deploy_application(subsystem, namespace)
        else:
            first = True
            for subsystem in self._meta.available_subsytems:
                if first is False:
                    sleep(10)
                print("deploy: %s" % subsystem)
                self.deploy_application(subsystem, namespace)
                first = False

    @ex(
        help="undeploy cmp subsystem",
        description="undeploy cmp subsystem",
        arguments=ARGS(
            [
                (
                    ["-subsystem"],
                    {
                        "help": "subsystem. Ex. resource, service",
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
        help="redeploy cmp subsystem",
        description="redeploy cmp subsystem",
        arguments=ARGS(
            [
                (
                    ["subsystem"],
                    {
                        "help": "subsystem. Ex. resource, service",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-path"],
                    {
                        "help": "remote package path",
                        "action": "store",
                        "type": str,
                        "default": "/opt/cmp",
                    },
                ),
                (
                    ["-pkgs"],
                    {
                        "help": "list of package to sync",
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
            raise Exception("subsystem can be one of %s" % self._meta.available_subsytems)


# class CmpInstanceController(ChildPlatformController):
#     setup_cmp = False
#
#     class Meta:
#         label = 'instances'
#         stacked_on = 'cmp'
#         stacked_type = 'nested'
#         description = "cmp instances management"
#
#     def check_instance(self, subsystem, vassal, group='beehive', playbook=None):
#         pass
#         # print('\nCheck instances status:')
#         #
#         # runners = self.get_runners()
#         # hosts = []
#         # for runner in runners:
#         #     hosts.extend(self.get_hosts(runner, ['beehive']))
#         # vars = runners[0].get_hosts_vars([hosts[0]])
#         #
#         # instances = vars.get('instance')
#         # vassal = [subsystem, vassal]
#         # count = 0
#         # wait_hosts = []
#         # port = instances.get('%s-%s' % tuple(vassal)).get('port')
#         # # for host in hosts:
#         # #     wait_hosts.append({'host': str(host), 'port': port})
#         #
#         # run_data = {
#         #     'local_package_path': self.local_package_path,
#         #     'host_port': port,
#         #     'tags': ['wait']
#         # }
#         # if playbook is None:
#         #     playbook = self.beehive_playbook
#         # self.ansible_playbook(group, run_data, playbook=playbook)
#         # print('')
#
#     @ex(
#         help='sync beehive package an all cmp nodes with local git repository and restart instances',
#         description='sync beehive package an all cmp nodes with local git repository and restart instances',
#         arguments=ARGS([
#             (['subsystem'], {'help': 'subsystem. Ex. resource, service', 'action': 'store', 'type': str}),
#             (['vassal'], {'help': 'vassal. Ex. 01', 'action': 'store', 'type': str}),
#             (['-log-level'], {'help': 'DEBUG, DEBUG2, DEBUG3 [default=DEBUG]', 'action': 'store', 'type': str,
#                               'default': 'DEBUG'}),
#         ])
#     )
#     def sync(self):
#         subsystem = self.app.pargs.subsystem
#         vassal = self.app.pargs.vassal
#         level = self.app.pargs.log_level.upper()
#         level = LoggerHelperLevel().get(level)
#         run_data = {
#             'local_package_path': self.local_package_path,
#             'subsystem': subsystem,
#             'vassal': '%s-%s' % (subsystem, vassal),
#             'tags': ['sync-dev'],
#             'logging_level': level
#         }
#         # if git_packages is not None:
#         #     git_packages = git_packages.split(',')
#         #     run_data['git_packages'] = []
#         #     for git_package in git_packages:
#         #         pkg = {
#         #             'uri': 'https://{{ git_user }}:{{ git_pwd | string }}@{{ git_host }}/1362',
#         #             'prj': git_package,
#         #             'pkg': git_package.replace('-', '_')
#         #         }
#         #         run_data['git_packages'].append(pkg)
#
#         self.ansible_playbook('beehive', run_data, playbook=self.beehive_playbook)
#         self.check_instance(subsystem, vassal)
#
#     @ex(
#         help='deploy cmp instance for subsystem',
#         description='deploy cmp instance for subsystem',
#         arguments=ARGS([
#             (['subsystem'], {'help': 'subsystem. Ex. resource, service', 'action': 'store', 'type': str}),
#             (['instance'], {'help': 'instance. Ex. 01', 'action': 'store', 'type': str}),
#             (['-log-level'], {'help': 'DEBUG, DEBUG2, DEBUG3 [default=DEBUG]', 'action': 'store', 'type': str,
#                               'default': 'DEBUG'}),
#         ])
#     )
#     def deploy(self):
#         subsystem = self.app.pargs.subsystem
#         instance = self.app.pargs.instance
#         level = self.app.pargs.log_level.upper()
#         level = LoggerHelperLevel().get(level)
#         run_data = {
#             'subsystem': subsystem,
#             'vassal': '%s-%s' % (subsystem, instance),
#             'tags': ['deploy'],
#             'logging_level': level
#         }
#         self.ansible_playbook('beehive', run_data, playbook=self.beehive_playbook)
#         self.check_instance(subsystem, instance)
#
#     @ex(
#         help='undeploy cmp instance for subsystem',
#         description='undeploy cmp instance for subsystem',
#         arguments=ARGS([
#             (['subsystem'], {'help': 'subsystem. Ex. resource, service', 'action': 'store', 'type': str}),
#             (['instance'], {'help': 'instance. Ex. 01', 'action': 'store', 'type': str}),
#         ])
#     )
#     def undeploy(self):
#         subsystem = self.app.pargs.subsystem
#         instance = self.app.pargs.instance
#         run_data = {
#             'subsystem': subsystem,
#             'vassal': '%s-%s' % (subsystem, instance),
#             'tags': ['undeploy']
#         }
#         self.ansible_playbook('beehive', run_data, playbook=self.beehive_playbook)
#
#     @ex(
#         help='deploy single cmp instance for subsystem',
#         description='deploy single cmp instance for subsystem',
#         arguments=ARGS([
#             (['subsystem'], {'help': 'subsystem. Ex. resource, service', 'action': 'store', 'type': str}),
#             (['instance'], {'help': 'instance. Ex. 01', 'action': 'store', 'type': str}),
#             (['-log-level'], {'help': 'DEBUG, DEBUG2, DEBUG3 [default=DEBUG]', 'action': 'store', 'type': str,
#                               'default': 'DEBUG'}),
#         ])
#     )
#     def deploy_single(self):
#         subsystem = self.app.pargs.subsystem
#         instance = self.app.pargs.instance
#         level = self.app.pargs.level.upper()
#         level = LoggerHelperLevel().get(level)
#         run_data = {
#             'subsystem': subsystem,
#             'vassal': '%s-%s' % (subsystem, instance),
#             'tags': ['deploy'],
#             'logging_level': level
#         }
#         self.ansible_playbook('beehive-init', run_data, playbook=self.beehive_init_playbook)
#         self.check_instance(subsystem, instance, group='beehive-init', playbook=self.beehive_init_playbook)
#
#     @ex(
#         help='ping cmp instances',
#         description='ping cmp instances',
#         arguments=ARGS()
#     )
#     def ping(self):
#         runners = self.get_runners()
#         hosts = []
#         for runner in runners:
#             hosts.extend(self.get_hosts(runner, ['beehive']))
#         vars = runners[0].get_hosts_vars([hosts[0]])
#
#         instances = vars.get('instance')
#
#         resp = []
#         for instance, port in instances.items():
#             port = port.get('port')
#             subsytem, instance = instance.split('-')
#
#             for host in hosts:
#                 start = time()
#                 url = 'http://%s:%s/v1.0/server/ping' % (host, port)
#                 self.app.log.debug(url)
#                 try:
#                     # issue a get request
#                     http = get(url)
#                     # response = http.json()
#                     elasped = time() - start
#                     if http.status_code == 200:
#                         resp.append({'subsystem': subsytem, 'instance': instance, 'host': str(host),
#                                      'port': port, 'ping': True, 'status': 'UP', 'elapsed': elasped})
#                     else:
#                         resp.append({'subsystem': subsytem, 'instance': instance, 'host': str(host),
#                                      'port': port, 'ping': False, 'status': 'DOWN', 'elapsed': elasped})
#                 except Exception as ex:
#                     elasped = time() - start
#                     self.app.log.error(ex)
#                     resp.append(
#                         {'subsystem': subsytem, 'instance': instance, 'host': str(host), 'port': port,
#                          'ping': False, 'status': 'DOWN', 'elapsed': elasped})
#
#         print_header = True
#         table_style = 'simple'
#         headers = ['subsystem', 'instance', 'host', 'port', 'status', 'elapsed']
#         self.app.render(resp, headers=headers, print_header=print_header, table_style=table_style)
#
#     @ex(
#         help='get cmp instance capabilities',
#         description='get cmp instance capabilities',
#         arguments=ARGS([
#             (['subsystem'], {'help': 'subsystem. Ex. resource, service', 'action': 'store', 'type': str}),
#             (['instance'], {'help': 'instance. Ex. 01', 'action': 'store', 'type': str}),
#         ])
#     )
#     def capabilities(self):
#         subsystem = self.app.pargs.subsystem
#         instance = self.app.pargs.instance
#         runners = self.get_runners()
#         hosts = []
#         for runner in runners:
#             hosts.extend(self.get_hosts(runner, ['beehive']))
#         vars = runners[0].get_hosts_vars([hosts[0]])
#         inst = '%s-%s' % (subsystem, instance)
#         instances = {inst: vars.get('instance').get(inst)}
#
#         resp = []
#         for instance, port in instances.items():
#             port = port.get('port')
#
#             for host in hosts:
#                 url = 'http://%s:%s/v1.0/server' % (host, port)
#                 self.app.log.debug(url)
#                 try:
#                     # issue a get request
#                     http = get(url)
#                     res = http.json()
#                     if http.status_code == 200:
#                         for module, apis in res.get('modules', {}).items():
#                             for api in apis.get('api', []):
#                                 resp.append({
#                                     'host': str(host),
#                                     'module': module,
#                                     'method': api.get('method'),
#                                     'uri': api.get('uri')
#                                 })
#                 except Exception as ex:
#                     self.app.log.error(ex)
#                 except Exception as ex:
#                     self.app.log.error(ex)
#
#         headers = ['host', 'module', 'method', 'uri']
#         self.app.render(resp, headers=headers)


class CmpPostInstallController(BaseController):
    class Meta:
        label = "post_install"
        stacked_on = "cmp"
        stacked_type = "nested"
        description = "DEPRECATED - cmp post install management"
        help = "DEPRECATED - cmp post install management"

    def pre_command_run(self):
        super(CmpPostInstallController, self).pre_command_run()

        self.config_path = self.app.config.get("beehive", "cmp_post_install_path")

    @ex(
        help="get post install available configurations",
        description="get post install available configurations",
        arguments=ARGS(),
    )
    def get(self):
        manager = CostomizeManager(self)
        res = manager.get_available_configs()
        self.app.render(res, headers=["name", "type"])

    @ex(
        help="get post install available configurations",
        description="get post install available configurations",
        arguments=ARGS(
            [
                (["config"], {"help": "config file", "action": "store", "type": str}),
                (
                    ["-filter"],
                    {
                        "help": "filter to apply <entity list key>:<key to filter>:<value>. "
                        "Ex. resource.entities.site_networks:name:NVLP3-Prov-WEB2-test",
                        "action": "store",
                        "type": str,
                        "default": None,
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
        help="run post install. This command can be used many times to add new items",
        description="run post install. This command can be used many times to add new items",
        arguments=ARGS(
            [
                (["config"], {"help": "config file", "action": "store", "type": str}),
                (
                    ["-filter"],
                    {
                        "help": "filter to apply <entity list key>:<key to filter>:<value>. "
                        "Ex. resource.entities.site_networks:name:NVLP3-Prov-WEB2-test",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-sections"],
                    {
                        "help": "comma separated list of section to execute",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def run(self):
        config = self.app.pargs.config
        config_filter = self.app.pargs.filter
        sections = self.app.pargs.sections
        manager = CostomizeManager(self)
        manager.load_configs(config)
        if config_filter is not None:
            manager.apply_filter(config_filter)
        manager.run(sections)


class CmpCustomizeController(BaseController):
    class Meta:
        label = "customize"
        stacked_on = "cmp"
        stacked_type = "nested"
        description = "cmp customization"
        help = "cmp customization"

    def pre_command_run(self):
        super(CmpCustomizeController, self).pre_command_run()

        self.config_path = self.app.config.get("beehive", "cmp_post_install_path")

    @ex(
        help="get available configurations",
        description="get available configurations",
        arguments=ARGS(),
    )
    def get(self):
        manager = CostomizeManager(self)
        res = manager.get_available_configs()
        self.app.render(res, headers=["name", "type"])

    @ex(
        help="show configuration",
        description="show configuration",
        arguments=ARGS(
            [
                (["config"], {"help": "config file", "action": "store", "type": str}),
                (
                    ["-filter"],
                    {
                        "help": "filter to apply <entity list key>:<key to filter>:<value>. "
                        "Ex. resource.entities.site_networks:name:NVLP3-Prov-WEB2-test",
                        "action": "store",
                        "type": str,
                        "default": None,
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
        help="run customization. This command can be used many times to add new items",
        description="run customization. This command can be used many times to add new items",
        arguments=ARGS(
            [
                (["config"], {"help": "config file", "action": "store", "type": str}),
                (
                    ["-filter"],
                    {
                        "help": "filter to apply <entity list key>:<key to filter>:<value>. "
                        "Ex. resource.entities.site_networks:name:NVLP3-Prov-WEB2-test",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-sections"],
                    {
                        "help": "comma separated list of section to execute",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def run(self):
        config = self.app.pargs.config
        config_filter = self.app.pargs.filter
        sections = self.app.pargs.sections
        manager = CostomizeManager(self)
        manager.load_configs(config)
        if config_filter is not None:
            manager.apply_filter(config_filter)
        manager.run(sections)


class CmpLog2Controller(ChildPlatformController):
    class Meta:
        label = "logs"
        stacked_on = "cmp"
        stacked_type = "nested"
        description = "cmp logs management"
        help = "cmp logs management"

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
        super(CmpLog2Controller, self).pre_command_run()

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
            raise Exception("Valid label are: %s" % ", ".join(orchestrators.keys()))
        k8s_conf = orchestrators.get(label)
        self.k8s_namespace = k8s_conf.get("default_namespace")
        self.k8s_cluster = k8s_conf.get("cluster")
        self.cmp_cert_postfix = k8s_conf.get("cmp_cert_postfix", "cmp_nivola")

    def get_current_elastic_index(self):
        return "%s-%s-filebeat-7.12.0-%s-%s" % (
            self.k8s_cluster,
            self.k8s_namespace,
            datetime.now().strftime("%Y.%m.%d"),
            self.cmp_cert_postfix,
        )

    def get_current_elastic_event_index(self):
        return "cmp-event-%s-pylogbeat-2.0.0-%s-%s" % (
            self.elk_env,
            datetime.now().strftime("%Y.%m.%d"),
            self.cmp_cert_postfix,
        )

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

                val = "%-8s %s %s%s" % (head[2], head[4], head[5], msg)
            except:
                val = self.app.colored_text.output(val, "GRAY")
        else:
            val = self.app.colored_text.output(val, "GRAY")
        return val

    @ex(
        help="show log for cmp engine",
        description="show log for cmp engine",
        arguments=ARGS(
            PAGINATION_ARGS,
            [
                (
                    ["-index"],
                    {
                        "help": "index name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "container partial name. Ex. uwsgi-auth, worker-auth, uwsgi-ssh",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sort"],
                    {
                        "help": "sort field. Ex. date:desc",
                        "action": "store",
                        "type": str,
                        "default": "timestamp:desc",
                    },
                ),
                (
                    ["-pod"],
                    {
                        "help": "pod name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-op"],
                    {
                        "help": "oepration id. Can be api_id, task_id, task_id:step_name",
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
            query = {"bool": {"must": [{"match": {"kubernetes.namespace": {"query": "beehive-%s" % self.env}}}]}}
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
        help="show cmp events",
        description="show cmp events",
        arguments=ARGS(
            PAGINATION_ARGS,
            [
                (
                    ["-index"],
                    {
                        "help": "index name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-kvargs"],
                    {
                        "help": "kvargs like query string",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": "event id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "event id",
                        "action": "store",
                        "type": str,
                        "default": "API",
                    },
                ),
                (
                    ["-sort"],
                    {
                        "help": "sort field. Ex. date:desc",
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
        help="get api request received",
        description="get api request received",
        arguments=ARGS(
            PAGINATION_ARGS,
            [
                (
                    ["-index"],
                    {
                        "help": "index name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": "api request id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-uri"],
                    {
                        "help": "api request ri. uri:method",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-user"],
                    {
                        "help": "api request source user",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ip"],
                    {
                        "help": "api request source ip",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sort"],
                    {
                        "help": "sort field. Ex. @timestamp:desc",
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


# class CmpLogController(ChildPlatformController):
#     class Meta:
#         label = 'logs'
#         stacked_on = 'cmp'
#         stacked_type = 'nested'
#         description = "cmp logs management"
#         help = "cmp logs management"
#
#         index_headers = ['name', 'replicas', 'shards', 'uuid', 'version', 'creation_date']
#         index_fields = ['settings.index.provided_name', 'settings.index.number_of_replicas',
#                         'settings.index.number_of_shards', 'settings.index.uuid', 'settings.index.version.created',
#                         'settings.index.creation_date']
#
#     def pre_command_run(self):
#         super(CmpLogController, self).pre_command_run()
#
#         self.es = self.config_elastic()
#
#     @ex(
#         help='list available log indexes',
#         description='list available log indexes',
#         arguments=ARGS()
#     )
#     def get(self):
#         res = list(self.es.indices.get('cmp-%s*' % self.env).values())
#         transform = {'settings.index.creation_date': lambda x: format_date(datetime.utcfromtimestamp(int(x) / 1000))}
#         self.app.render(res, headers=self._meta.index_headers, fields=self._meta.index_fields, transform=transform)
#
#     @ex(
#         help='delete log index',
#         description='delete log index',
#         arguments=ARGS([
#             (['index'], {'help': 'index name', 'action': 'store', 'type': str}),
#         ])
#     )
#     def delete(self):
#         index = self.app.pargs.index
#         res = self.es.indices.delete(index=index)
#         self.app.render({'msg': 'delete index %s' % index}, headers=['msg'], maxsize=200)
#
#     @ex(
#         help='show log for api instances',
#         description='show log for api instances',
#         arguments=ARGS(PAGINATION_ARGS, [
#             (['-index'], {'help': 'index name', 'action': 'store', 'type': str, 'default': None}),
#             (['app'], {'help': 'simple query like field1:value1,field2:value2a+value2b', 'action': 'store',
#                        'type': str, 'default': None}),
#             (['-sort'], {'help': 'sort field. Ex. date:desc', 'action': 'store', 'type': str, 'default': 'date:desc'}),
#             (['-pretty'], {'help': 'if true show pretty logs', 'action': 'store', 'type': bool, 'default': True}),
#             (['-server'], {'help': 'server ip', 'action': 'store', 'type': str, 'default': None}),
#             (['-thread'], {'help': 'execution thread', 'action': 'store', 'type': str, 'default': None}),
#             (['-api_id'], {'help': 'api id', 'action': 'store', 'type': str, 'default': None}),
#         ])
#     )
#     def api_engine(self):
#         index = self.app.pargs.index
#         app = self.app.pargs.app
#         server = self.app.pargs.server
#         thread = self.app.pargs.thread
#         api_id = self.app.pargs.api_id
#         sort = self.app.pargs.sort
#         page = self.app.pargs.page
#         size = self.app.pargs.size
#         pretty = self.app.pargs.pretty
#
#         if index is None:
#             index = self.get_current_elastic_index()
#
#         match = [
#             {'match': {'app': {'query': app, 'operator': 'and'}}},
#             {'match': {'component': {'query': 'api', 'operator': 'and'}}},
#         ]
#
#         if server is not None:
#             match.append({'match': {'server': {'query': server, 'operator': 'and'}}})
#
#         if thread is not None:
#             match.append({'match': {'thread': {'query': thread, 'operator': 'and'}}})
#
#         if api_id is not None:
#             match.append({'match': {'api_id': {'query': api_id, 'operator': 'and'}}})
#
#         query = {
#             'bool': {
#                 'must': match
#             }
#         }
#
#         header = '{date} [{server}] {api_id:10} {thread} {levelname:7} {func}:{lineno} - {message}'
#         self._query(index, query, page, size, sort, pretty=pretty, header=header)
#
#     @ex(
#         help='show log for worker instances',
#         description='show log for worker instances',
#         arguments=ARGS(PAGINATION_ARGS, [
#             (['-index'], {'help': 'index name', 'action': 'store', 'type': str, 'default': None}),
#             (['app'], {'help': 'simple query like field1:value1,field2:value2a+value2b', 'action': 'store',
#                        'type': str, 'default': None}),
#             (['-sort'], {'help': 'sort field. Ex. date:desc', 'action': 'store', 'type': str, 'default': 'date:desc'}),
#             (['-pretty'], {'help': 'if true show pretty logs', 'action': 'store', 'type': bool, 'default': True}),
#             (['-server'], {'help': 'server ip', 'action': 'store', 'type': str, 'default': None}),
#             (['-task'], {'help': 'task id', 'action': 'store', 'type': str, 'default': None}),
#         ])
#     )
#     def worker_engine(self):
#         index = self.app.pargs.index
#         app = self.app.pargs.app
#         server = self.app.pargs.server
#         task = self.app.pargs.task
#         sort = self.app.pargs.sort
#         page = self.app.pargs.page
#         size = self.app.pargs.size
#         pretty = self.app.pargs.pretty
#
#         if index is None:
#             index = self.get_current_elastic_index()
#
#         match = [
#             {'match': {'app': {'query': app, 'operator': 'and'}}},
#             {'match': {'component': {'query': 'task', 'operator': 'and'}}},
#         ]
#
#         if server is not None:
#             match.append({'match': {'server': {'query': server, 'operator': 'and'}}})
#
#         if task is not None:
#             match.append({'match': {'task_id': {'query': task, 'operator': 'and'}}})
#
#         query = {
#             'bool': {
#                 'must': match
#             }
#         }
#         self.app.log.debug(query)
#
#         header = '{date} [{server}] {task_id} {levelname:7} {func}:{lineno} - {message}'
#         self._query(index, query, page, size, sort, pretty=pretty, header=header)
#
#     @ex(
#         help='get events',
#         description='get events',
#         arguments=ARGS(PAGINATION_ARGS, [
#             (['-index'], {'help': 'index name', 'action': 'store', 'type': str, 'default': None}),
#             (['-kvargs'], {'help': 'kvargs like query string', 'action': 'store', 'type': str, 'default': None}),
#             (['-id'], {'help': 'event id', 'action': 'store', 'type': str, 'default': None}),
#             (['-type'], {'help': 'event id', 'action': 'store', 'type': str, 'default': 'SSH'}),
#             (['-sort'], {'help': 'sort field. Ex. date:desc', 'action': 'store', 'type': str, 'default': 'date:desc'}),
#         ])
#     )
#     def event(self):
#         index = self.app.pargs.index
#         eventid = self.app.pargs.id
#         event_type = self.app.pargs.type
#         kvargs = self.app.pargs.kvargs
#         sort = self.app.pargs.sort
#         page = self.app.pargs.page
#         size = self.app.pargs.size
#
#         if index is None:
#             index = self.get_current_elastic_event_index()
#
#         if eventid is None:
#             match = [
#                 {'match': {'type': {'query': event_type, 'operator': 'or'}}},
#             ]
#         else:
#             match = [
#                 {'match': {'event_id': {'query': eventid, 'operator': 'and'}}},
#             ]
#         if kvargs is not None:
#             match.append({'match_phrase': {'data.kwargs': kvargs}})
#
#         query = {
#             'bool': {
#                 'must': match
#             }
#         }
#         data = self._query(index, query, page, size, sort, render=False).get('values')
#         if eventid is None:
#             headers = ['event_id', 'op_id', 'op', 'date', 'elapsed', 'response', 'user', 'ip', 'dest-ip', 'dest-port']
#             fields = ['event_id', 'data.op_id', 'data.op', 'date', 'data.elapsed', 'data.response.0', 'source.user',
#                       'source.ip', 'dest.ip', 'dest.port']
#             self.app.render(data, headers=headers, fields=fields, maxsize=100)
#         else:
#             self.app.render(data[0], details=True)
#
#     @ex(
#         help='get api request received',
#         description='get api request received',
#         arguments=ARGS(PAGINATION_ARGS, [
#             (['-index'], {'help': 'index name', 'action': 'store', 'type': str, 'default': None}),
#             (['-id'], {'help': 'api request id', 'action': 'store', 'type': str, 'default': None}),
#             (['-sort'], {'help': 'sort field. Ex. date:desc', 'action': 'store', 'type': str, 'default': 'date:desc'}),
#             (['-uri'], {'help': 'api request ri. uri:method', 'action': 'store', 'type': str, 'default': None}),
#             (['-user'], {'help': 'api request source user', 'action': 'store', 'type': str, 'default': None}),
#             (['-ip'], {'help': 'api request source ip', 'action': 'store', 'type': str, 'default': None}),
#         ])
#     )
#     def api(self):
#         index = self.app.pargs.index
#         eventid = self.app.pargs.id
#         sort = self.app.pargs.sort
#         page = self.app.pargs.page
#         size = self.app.pargs.size
#         uri = self.app.pargs.uri
#         user = self.app.pargs.user
#         ip = self.app.pargs.ip
#
#         if index is None:
#             index = self.get_current_elastic_event_index()
#
#         if eventid is None:
#             match = [
#                 {'match': {'type': {'query': 'API', 'operator': 'and'}}},
#             ]
#         else:
#             # match = [
#             #     {'match': {'data.api_id': {'query': apiid, 'operator': 'and'}}},
#             # ]
#             match = [
#                 {'match': {'event_id': {'query': eventid, 'operator': 'and'}}},
#             ]
#
#         if uri is not None:
#             match.append({'match': {'data.op': {'query': uri, 'operator': 'and'}}})
#         if user is not None:
#             match.append({'match': {'source.user': {'query': user, 'operator': 'and'}}})
#         if ip is not None:
#             match.append({'match': {'source.ip': {'query': ip, 'operator': 'and'}}})
#
#         query = {
#             'bool': {
#                 'must': match
#             }
#         }
#
#         if eventid is None:
#             headers = ['id', 'api_id', 'date', 'method', 'uri', 'elapsed', 'response-code', 'user', 'source', 'dest']
#             fields = ['event_id', 'data.api_id', 'date', 'method', 'path', 'data.elapsed', 'data.response.0',
#                       'source.user', 'source.ip', 'dest.ip']
#             data = self._query(index, query, page, size, sort, render=False).get('values')
#             if self.is_output_text():
#                 for i in data:
#                     path = dict_get(i, 'data.op').split(':')
#                     i['path'] = path[0]
#                     i['method'] = path[-1]
#             self.app.render(data, headers=headers, fields=fields, maxsize=100)
#         else:
#             api = self._query(index, query, page, 200, sort, render=False).get('values')[0]
#             apiid = dict_get(api, 'data.api_id')
#             if self.is_output_text():
#                 query = {
#                     'bool': {
#                         'must': [
#                             {'match': {'data.api_id': {'query': apiid, 'operator': 'and'}}},
#                         ]
#                     }
#                 }
#                 data = self._query(index, query, page, 200, sort, render=False).get('values')
#                 newdata = []
#                 for item in data:
#                     if dict_get(item, 'event_id') != eventid:
#                         newdata.append(item)
#                 newdata.reverse()
#
#                 dest = api.pop('dest')
#                 source = api.pop('source')
#                 inner_data = api.pop('data')
#
#                 self.app.render(api, details=True)
#                 self.c('\nsource', 'underline')
#                 self.app.render(source, details=True)
#                 self.c('\ndestination', 'underline')
#                 self.app.render(dest, details=True)
#                 self.c('\ndata', 'underline')
#                 self.app.render(inner_data, details=True)
#                 self.c('\nworkflow', 'underline')
#                 headers = ['opid', 'date', 'type', 'operation', 'elapsed', 'response-code', 'user', 'ip-addr',
#                            'dest-ip-addr', 'dest-port']
#                 fields = ['data.opid', 'date', 'type', 'data.op', 'data.elapsed', 'data.response.0', 'source.user',
#                           'source.ip', 'dest.ip', 'dest.port']
#                 self.app.render(newdata, headers=headers, fields=fields, maxsize=100)
#             else:
#                 self.app.render(api, details=True, maxsize=100)
#
#     @ex(
#         help='get logs of api request received',
#         description='get logs of api request received',
#         arguments=ARGS(PAGINATION_ARGS, [
#             (['-index'], {'help': 'index name', 'action': 'store', 'type': str, 'default': None}),
#             (['id'], {'help': 'api request id', 'action': 'store', 'type': str, 'default': None}),
#             (['-sort'], {'help': 'sort field. Ex. date:desc', 'action': 'store', 'type': str, 'default': 'date:desc'}),
#             (['-pretty'], {'help': 'if true show pretty logs', 'action': 'store', 'type': bool, 'default': True}),
#         ])
#     )
#     def api_logs(self):
#         index = self.app.pargs.index
#         eventid = self.app.pargs.id
#         sort = self.app.pargs.sort
#         page = self.app.pargs.page
#         size = self.app.pargs.size
#         pretty = self.app.pargs.pretty
#
#         if index is None:
#             index = self.get_current_elastic_event_index()
#             index2 = self.get_current_elastic_index()
#
#         match = [
#             {'match': {'event_id': {'query': eventid, 'operator': 'and'}}},
#         ]
#
#         query = {
#             'bool': {
#                 'must': match
#             }
#         }
#
#         # get api event record
#         api = self._query(index, query, page, size, sort, render=False).get('values')[0]
#         apiid = dict_get(api, 'data.api_id')
#         op = dict_get(api, 'data.op')
#         app = 'auth'
#         if op.find('nws') > 0:
#             app = 'service'
#         elif op.find('nrs') > 0:
#             app = 'resource'
#         elif op.find('nes') > 0:
#             app = 'event'
#         elif op.find('gas') > 0:
#             app = 'ssh'
#
#         # get api logs
#         if apiid is not None:
#             match = [
#                 {'match': {'app': {'query': app, 'operator': 'and'}}},
#                 {'match': {'component': {'query': 'api', 'operator': 'and'}}},
#                 {'match': {'api_id': {'query': apiid, 'operator': 'and'}}}
#             ]
#
#             query = {
#                 'bool': {
#                     'must': match
#                 }
#             }
#
#             header = '{date} [{server}] {api_id:10} {thread} {levelname:7} {func}:{lineno} - {message}'
#             self._query(index2, query, page, 1000, sort, pretty=pretty, header=header)
#
#     @ex(
#         help='get api request received',
#         description='get api request received',
#         arguments=ARGS(PAGINATION_ARGS, [
#             (['-index'], {'help': 'index name', 'action': 'store', 'type': str, 'default': None}),
#             (['opid'], {'help': 'operation id', 'action': 'store', 'type': str, 'default': None}),
#         ])
#     )
#     def operation(self):
#         index = self.app.pargs.index
#         opid = self.app.pargs.opid
#
#         if index is None:
#             index = self.get_current_elastic_event_index()
#
#         match = [
#             {'match': {'data.opid': {'query': opid, 'operator': 'and'}}},
#         ]
#
#         query = {
#             'bool': {
#                 'must': match
#             }
#         }
#         self.app.log.debug(query)
#
#         data = self._query(index, query, 0, 1, None, render=False).get('values')
#         if len(data) == 0:
#             raise Exception('operation %s does not exist' % opid)
#         data = data[0]
#         if self.is_output_text():
#             dest = data.pop('dest')
#             source = data.pop('source')
#             inner_data = data.pop('data')
#
#             self.app.render(data, details=True)
#             self.c('\nsource', 'underline')
#             self.app.render(source, details=True)
#             self.c('\ndestination', 'underline')
#             self.app.render(dest, details=True)
#             self.c('\ndata', 'underline')
#             self.app.render(inner_data, details=True)
#         else:
#             self.app.render(data, details=True)
