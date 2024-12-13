# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from json import loads
from sys import stdin, stdout
from threading import Thread
from queue import Queue
from io import StringIO
from yaml import safe_load_all
from six import ensure_text
from cement import ex
from beecell.simple import merge_list, str2bool, dict_get, format_date
from beehive3_cli.core.controller import BASE_ARGS, StringAction
from beehive3_cli.plugins.platform.controllers import ChildPlatformController
from beehive3_cli.plugins.platform.controllers.elastic import ElkController


def K8S_ARGS(*list_args):
    orchestrator_args = [
        (
            ["-C", "--cluster"],
            {
                "action": "store",
                "dest": "cluster",
                "help": "k8s cluster reference label",
            },
        ),
        (
            ["-N", "--namespace"],
            {"action": "store", "dest": "namespace", "help": "k8s current namespace"},
        ),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class BaseK8sController(ChildPlatformController):
    def pre_command_run(self):
        self.pre_command_run_inner()

    def pre_command_run_inner(self, orch_label: str = None):
        super(BaseK8sController, self).pre_command_run()
        from kubernetes import client as k8s_client

        self.k8s_deploy_config = f"{self.ansible_path}/k8s/cmp"

        orchestrators = self.config.get("orchestrators", {}).get("k8s", {})
        label = getattr(self.app.pargs, "cluster", None)

        if label is None and orch_label is not None:
            label = orch_label

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception("No k8s default platform is available for this environment. Select another environment")

        if label not in orchestrators:
            raise Exception("Valid label are: %s" % ", ".join(orchestrators.keys()))
        self.conf = orchestrators.get(label)

        # Create a configuration object
        self.configuration = k8s_client.Configuration()

        # get hosts
        self.k8s_hosts = self.conf.get("hosts")

        # Specify the endpoint of your Kube cluster
        self.configuration.host = "%s://%s:%s" % (
            self.conf.get("proto"),
            self.k8s_hosts[0],
            self.conf.get("port"),
        )

        # Security part.
        # In this simple example we are not going to verify the SSL certificate of
        # the remote cluster (for simplicity reason)
        self.configuration.verify_ssl = False
        # Nevertheless if you want to do it you can with these 2 parameters
        # configuration.verify_ssl=True
        # ssl_ca_cert is the filepath to the file that contains the certificate.
        # configuration.ssl_ca_cert="certificate"

        k8s_token = self.conf.get("token", None)
        cert_file = self.conf.get("cert_file", None)
        key_file = self.conf.get("key_file", None)
        if k8s_token is not None:
            self.configuration.api_key = {"authorization": "Bearer " + k8s_token}
        elif key_file is not None and cert_file is not None:
            self.configuration.cert_file = cert_file
            self.configuration.key_file = key_file

        # Create a ApiClient with our config
        self.client = k8s_client.ApiClient(self.configuration)
        self.default_namespace = self.conf.get("default_namespace")

    def get_namespace(self):
        namespace = getattr(self.app.pargs, "namespace")
        if namespace is None:
            namespace = self.default_namespace
        return namespace

    def __get_dict(self, obj, as_dict=False):
        """return as dict or as python object

        :param obj: object to convert
        :param as_dict: if True return dict
        :return: dict or python object
        """
        if as_dict is True:
            return obj.to_dict()
        return obj

    def list_pod(self, namespace, name=None, as_dict=False):
        """list pods

        :param namespace: namespace
        :param name: name filter
        :param as_dict: if True return pod as dict
        :return:
        """
        from kubernetes import client as k8s_client

        v1 = k8s_client.CoreV1Api(self.client)
        pods = v1.list_namespaced_pod(namespace).items
        res = []
        for pod in pods:
            if name is None or (name is not None and pod.metadata.name.find(name) >= 0):
                res.append(self.__get_dict(pod, as_dict))
        return res

    def list_service(self, namespace, name=None, as_dict=False):
        """list service

        :param namespace: namespace
        :param name: name filter
        :param as_dict: if True return pod as dict
        :return:
        """
        from kubernetes import client as k8s_client

        v1 = k8s_client.CoreV1Api(self.client)
        services = v1.list_namespaced_service(namespace).items
        res = []
        for service in services:
            if name is None or (name is not None and service.metadata.name.find(name) >= 0):
                res.append(self.__get_dict(service, as_dict))
        return res

    def __color_line(self, line, log_type=None):
        if line.find("INFO") >= 0:  # or log_type == 'INFO':
            log_type = "INFO"
            line = self.app.colored_text.output(line, "WHITE")
        elif line.find("DEBUG2") >= 0:  #  or log_type == 'DEBUG2':
            log_type = "DEBUG2"
            line = self.app.colored_text.output(line, "GREEN")
        elif line.find("DEBUG") >= 0:  #  or log_type == 'DEBUG':
            log_type = "DEBUG"
            line = self.app.colored_text.output(line, "BLUE")
        elif line.find("ERROR") >= 0:  #  or log_type == 'ERROR':
            log_type = "ERROR"
            line = self.app.colored_text.output(line, "RED")
        elif line.find("WARNING") >= 0:  #  or log_type == 'WARNING':
            log_type = "WARNING"
            line = self.app.colored_text.output(line, "YELLOW")
        else:
            # log_type = None
            line = self.app.colored_text.output(line, "GRAY")
        return line, log_type

    def __get_stream(self, client, pod, namespace):
        from kubernetes.stream import stream

        log_type = None
        for line in client.read_namespaced_pod_log(
            pod, namespace, follow=True, tail_lines=100, _preload_content=False
        ).stream():
            line = ensure_text(line).rstrip()
            line, log_type = self.__color_line(line, log_type=log_type)
            print(line)

    def get_pod_log(self, namespace, oid=None, name=None, tail_lines=100, follow=False):
        from kubernetes import client as k8s_client

        v1 = k8s_client.CoreV1Api(self.client)
        if oid is not None:
            if follow is True:
                self.__get_stream(v1, oid, namespace)
            else:
                log = v1.read_namespaced_pod_log(oid, namespace, tail_lines=tail_lines)
                for line in log.split("\n"):
                    line, log_type = self.__color_line(line)
                    print(line)
        elif name is not None:
            pods = v1.list_namespaced_pod(namespace).items
            log_pods = []
            for pod in pods:
                if pod.metadata.name.find(name) >= 0:
                    log_pods.append(pod.metadata.name)
            for log_pod in log_pods:
                if follow is True:
                    t = Thread(
                        target=self.__get_stream,
                        args=(
                            v1,
                            log_pod,
                            namespace,
                        ),
                    )
                    t.start()
                    t.join(5)
                else:
                    log = v1.read_namespaced_pod_log(log_pod, namespace, tail_lines=tail_lines)
                    print("-------------------------- %s --------------------------" % log_pod)
                    for line in log.split("\n"):
                        line, log_type = self.__color_line(line)
                        print(line)

    def get_yaml_document_all(self, deploy):
        import sh

        try:
            deploy_path = "%s/%s/%s" % (self.k8s_deploy_config, deploy, self.env)
            buf = StringIO()
            sh.kubectl("kustomize", deploy_path, _out=buf)
        except sh.ErrorReturnCode_2:
            print("deploy %s does not exist" % deploy_path)

        yml_document_all = safe_load_all(buf.getvalue())
        return yml_document_all

    def print_k8s_response(self, k8s_objects, kinds=None):
        items = []
        for k8s_object in k8s_objects:
            # k8s_object = k8s_object[0]

            if hasattr(k8s_object, "items"):
                k8s_object = k8s_object.items
            if not isinstance(k8s_object, list):
                k8s_object = [k8s_object]

            for k in k8s_object:
                if kinds is not None and k.kind not in kinds:
                    continue

                if k.kind == "Deployment":
                    for c in k.spec.template.spec.containers:
                        try:
                            cmd = " ".join(c.command)
                        except:
                            cmd = c.command
                        item = {
                            "kind": k.kind,
                            "name": k.metadata.name,
                            "namespace": k.metadata.namespace,
                            "role": k.metadata.labels.get("role"),
                            "replicas": "%s/%s" % (k.status.ready_replicas, k.status.replicas),
                            "creation_date": format_date(k.metadata.creation_timestamp),
                            "container": {"name": c.name, "cmd": cmd, "image": c.image},
                        }
                        items.append(item)
                elif k.kind == "Service":
                    item = {
                        "kind": k.kind,
                        "name": k.metadata.name,
                        "namespace": k.metadata.namespace,
                        "type": k.spec.type,
                        "cluster_ip": k.spec.cluster_ip,
                        "node_port": k.spec.ports[0].node_port,
                        "target_port": k.spec.ports[0].target_port,
                        "creation_date": format_date(k.metadata.creation_timestamp),
                    }
                    items.append(item)
                else:
                    item = {
                        "kind": k.kind,
                        "name": k.metadata.name,
                        "namespace": k.metadata.namespace,
                        "creation_date": format_date(k.metadata.creation_timestamp),
                    }
                    items.append(item)

        headers = ["kind", "name", "namespace", "creation_date"]
        if kinds is not None and len(kinds) == 1:
            kind = kinds[0]
            if kind == "Deployment":
                headers = [
                    "kind",
                    "name",
                    "namespace",
                    "creation_date",
                    "role",
                    "replicas",
                    "container.name",
                    "container.image",
                    "container.cmd",
                ]
            elif kind == "Service":
                headers = [
                    "kind",
                    "name",
                    "namespace",
                    "creation_date",
                    "type",
                    "cluster_ip",
                    "node_port",
                    "target_port",
                ]

        self.app.render(items, headers=headers)

    def show_application(self, app, namespace, kinds=None):
        from beehive3_cli.plugins.platform.util.k8s_util import list_from_dict
        from kubernetes.utils import FailToCreateError

        yml_document_all = self.get_yaml_document_all(app)

        failures = []
        k8s_objects = []
        for yml_document in yml_document_all:
            try:
                item = list_from_dict(self.client, yml_document, False, namespace=namespace, kinds=kinds)
                k8s_objects.extend(item)
            except FailToCreateError as failure:
                # failures.append(failure)
                try:
                    err = loads(failure.api_exceptions[0].body)
                    err = err["message"]
                except:
                    err = failure.api_exceptions[0].body
                self.app.error(err)

        return k8s_objects

    def deploy_application(self, app, namespace):
        from kubernetes.utils import create_from_dict, FailToCreateError

        yml_document_all = self.get_yaml_document_all(app)

        for yml_document in yml_document_all:
            try:
                created = create_from_dict(self.client, yml_document, False, namespace=namespace)
                for k in created:
                    item = {
                        "kind": k.kind,
                        "name": k.metadata.name,
                        "namespace": k.metadata.namespace,
                        "creation_date": format_date(k.metadata.creation_timestamp),
                    }
                    print("deploy {kind} {name} in namespace {namespace}".format(**item))
            except FailToCreateError as failure:
                try:
                    err = loads(failure.api_exceptions[0].body)
                    err = err["message"]
                except:
                    err = failure.api_exceptions[0].body
                self.app.error(err)

    def undeploy_application(self, app, namespace):
        from kubernetes.utils import FailToCreateError
        from beehive3_cli.plugins.platform.util.k8s_util import delete_from_dict

        yml_document_all = self.get_yaml_document_all(app)

        for yml_document in yml_document_all:
            try:
                deleted = delete_from_dict(self.client, yml_document, False, namespace=namespace)
                for k in deleted:
                    item = {
                        "kind": k["kind"],
                        "name": k["name"],
                        "namespace": k["namespace"],
                    }
                    print("undeploy {kind} {name} in namespace {namespace}".format(**item))
            except FailToCreateError as failure:
                try:
                    err = loads(failure.api_exceptions[0].body)
                    err = err["message"]
                except:
                    err = failure.api_exceptions[0].body
                self.app.error(err)


class K8sController(BaseK8sController, ElkController):
    class Meta:
        label = "k8s"
        description = "k8s management"
        help = "k8s management"

    @ex(help="ping k8s cluster", description="ping k8s cluster", arguments=K8S_ARGS())
    def ping(self):
        from kubernetes import client as k8s_client

        resp = []
        proto = self.conf.get("proto")
        port = self.conf.get("port")
        for host in self.conf.get("hosts"):
            self.configuration.host = "%s://%s:%s" % (proto, host, port)
            self.client = self.k8s_client.ApiClient(self.configuration)
            v1 = k8s_client.ApisApi(self.client)
            try:
                res = v1.get_api_versions()
                resp.append({"host": host, "response": True})
            except:
                resp.append({"host": host, "response": False})

        self.app.render(resp, headers=["host", "response"], maxsize=200)

    @ex(
        help="get k8s nodes",
        description="get k8s nodes",
        arguments=K8S_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "node id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def node_get(self):
        from kubernetes import client as k8s_client

        node = self.app.pargs.id
        v1 = k8s_client.CoreV1Api(self.client)
        if node is not None:
            node = v1.read_node(node)
            res = {
                "uid": node.metadata.uid,
                "name": node.metadata.name,
                "ip": node.status.addresses[0].address,
                "capacity": node.status.capacity,
                "pod_cidr": node.spec.pod_cidr,
                "namespace": node.metadata.namespace,
                "info": {
                    "architecture": node.status.node_info.architecture,
                    "boot_id": node.status.node_info.boot_id,
                    "container_runtime_version": node.status.node_info.container_runtime_version,
                    "kernel_version": node.status.node_info.kernel_version,
                    "kube_proxy_version": node.status.node_info.kube_proxy_version,
                    "kubelet_version": node.status.node_info.kubelet_version,
                    "machine_id": node.status.node_info.machine_id,
                    "operating_system": node.status.node_info.operating_system,
                    "os_image": node.status.node_info.os_image,
                    "system_uuid": node.status.node_info.system_uuid,
                },
                "images": [{"names": v.names, "size": v.size_bytes} for v in node.status.images],
            }
            self.app.render(res, details=True)
        else:
            nodes = v1.list_node(watch=False)
            res = [
                {
                    "uid": p.metadata.uid,
                    "name": p.metadata.name,
                    "ip": p.status.addresses[0].address,
                    "cpu": p.status.capacity["cpu"],
                    "memory": p.status.capacity["memory"],
                    "images": len(p.status.images),
                    "os_image": p.status.node_info.os_image,
                    "kernel": p.status.node_info.kernel_version,
                    "container": p.status.node_info.container_runtime_version,
                }
                for p in nodes.items
            ]
            self.app.render(
                res,
                headers=[
                    "uid",
                    "name",
                    "ip",
                    "cpu",
                    "memory",
                    "images",
                    "os_image",
                    "kernel",
                    "container",
                ],
            )

    @ex(help="get k8s namespace", description="get k8s namespace", arguments=K8S_ARGS())
    def namespace_get(self):
        from kubernetes import client as k8s_client

        v1 = k8s_client.CoreV1Api(self.client)
        apps = v1.list_namespace()
        res = apps.to_dict().get("items", [])
        for i in res:
            i["metadata"]["creation_timestamp"] = str(i["metadata"]["creation_timestamp"])

        transform = {"metadata.creation_timestamp": lambda x: str(x)}
        headers = ["name", "creation"]
        fields = ["metadata.name", "metadata.creation_timestamp"]
        self.app.render(res, headers=headers, fields=fields, transform=transform, maxsize=200)

    @ex(help="get k8s service", description="get k8s service", arguments=K8S_ARGS())
    def service_get(self):
        from kubernetes import client as k8s_client

        namespace = self.get_namespace()
        v1 = k8s_client.CoreV1Api(self.client)
        if namespace == "all":
            apps = v1.list_service_for_all_namespaces()
            res = apps.to_dict().get("items", [])
            for i in res:
                i["metadata"]["creation_timestamp"] = str(i["metadata"]["creation_timestamp"])

            transform = {"metadata.creation_timestamp": lambda x: str(x)}
            headers = ["name", "creation", "type", "namespace", "cluster_ip", "ports"]
            fields = [
                "metadata.name",
                "metadata.creation_timestamp",
                "spec.type",
                "metadata.namespace",
                "spec.cluster_ip",
                "spec.ports",
            ]
            self.app.render(res, headers=headers, fields=fields, transform=transform, maxsize=200)
        else:
            apps = v1.list_namespaced_service(namespace)
            res = apps.to_dict().get("items", [])
            for i in res:
                i["metadata"]["creation_timestamp"] = str(i["metadata"]["creation_timestamp"])

            transform = {"spec.ports": lambda x: " ".join(["%s:%s" % (p["node_port"], p["target_port"]) for p in x])}
            headers = ["name", "creation", "type", "cluster_ip", "ports"]
            fields = [
                "metadata.name",
                "metadata.creation_timestamp",
                "spec.type",
                "spec.cluster_ip",
                "spec.ports",
            ]
            self.app.render(res, headers=headers, fields=fields, transform=transform, maxsize=200)

    @ex(
        help="get k8s deployment app",
        description="get k8s deployment app",
        arguments=K8S_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "deployment app id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def deploy_get(self):
        from kubernetes import client as k8s_client

        app = self.app.pargs.id
        namespace = self.get_namespace()
        v1 = k8s_client.AppsV1Api(self.client)
        if app is not None and namespace is not None:
            app = v1.read_namespaced_deployment(app, namespace)
            res = app.to_dict()
            res["metadata"]["creation_timestamp"] = str(res["metadata"]["creation_timestamp"])
            for c in res["status"]["conditions"]:
                c["last_transition_time"] = str(c["last_transition_time"])
                c["last_update_time"] = str(c["last_update_time"])

            metadata = res.pop("metadata")
            spec = res.pop("spec")
            template = spec.pop("template")
            status = res.pop("status")
            conditions = status.pop("conditions")
            self.app.render(res, details=True)
            self.c("\nmetadata", "underline")
            self.app.render(metadata, details=True)
            self.c("\nspec", "underline")
            self.app.render(spec, details=True)
            self.c("\nspec - template", "underline")
            self.app.render(template, details=True)
            self.c("\nstatus", "underline")
            self.app.render(status, details=True)
            self.c("\nstatus - conditions", "underline")
            self.app.render(
                conditions,
                headers=[
                    "type",
                    "status",
                    "reason",
                    "last_update_time",
                    "last_transition_time",
                    "message",
                ],
                maxsize=200,
            )

        elif namespace == "all":
            apps = v1.list_deployment_for_all_namespaces()
            res = apps.to_dict().get("items", [])
            headers = [
                "name",
                "namespace",
                "creation",
                "replicas",
                "available replicas",
                "ready replicas",
                "updated replicas",
            ]
            fields = [
                "metadata.name",
                "metadata.namespace",
                "metadata.creation_timestamp",
                "status.ready_replicas",
                "status.available_replicas",
                "status.replicas",
                "status.updated_replicas",
            ]
            self.app.render(res, headers=headers, fields=fields)
        elif namespace is not None:
            apps = v1.list_namespaced_deployment(namespace)
            res = apps.to_dict().get("items", [])
            for i in res:
                i["metadata"]["creation_timestamp"] = str(i["metadata"]["creation_timestamp"])
                for c in i["status"]["conditions"]:
                    c["last_transition_time"] = str(c["last_transition_time"])
                    c["last_update_time"] = str(c["last_update_time"])
            transform = {"metadata.creation_timestamp": lambda x: str(x)}
            headers = [
                "name",
                "creation",
                "replicas",
                "available replicas",
                "ready replicas",
                "updated replicas",
            ]
            fields = [
                "metadata.name",
                "metadata.creation_timestamp",
                "status.ready_replicas",
                "status.available_replicas",
                "status.replicas",
                "status.updated_replicas",
            ]
            self.app.render(res, headers=headers, fields=fields, transform=transform)

    @ex(
        help="get k8s pod",
        description="get k8s pod",
        arguments=K8S_ARGS(
            [
                (
                    ["-id"],
                    {"help": "pod id", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def pod_get(self):
        from kubernetes import client as k8s_client

        pod = self.app.pargs.id
        namespace = self.get_namespace()
        v1 = k8s_client.CoreV1Api(self.client)
        if pod is not None and namespace is not None:
            pod = v1.read_namespaced_pod(pod, namespace)
            res = pod.to_dict()
            res["metadata"]["creation_timestamp"] = str(res["metadata"]["creation_timestamp"])
            res["status"]["start_time"] = str(res["status"]["start_time"])
            for c in res["status"]["conditions"]:
                c["last_transition_time"] = str(c["last_transition_time"])

            metadata = res.pop("metadata")
            spec = res.pop("spec")
            containers = spec.pop("containers")
            volumes = spec.pop("volumes")
            status = res.pop("status")
            container_statuses = status.pop("container_statuses")
            conditions = status.pop("conditions")
            self.app.render(res, details=True)
            self.c("\nmetadata", "underline")
            self.app.render(metadata, details=True)
            self.c("\nspec", "underline")
            self.app.render(spec, details=True)
            self.c("\nspec - volumes", "underline")
            headers = ["name", "config_map.name", "secret.secret_name"]
            self.app.render(volumes, headers=headers, maxsize=200)
            self.c("\ncontainers", "underline")
            transform = {
                "volume_mounts": lambda x: "\n".join([n["name"] for n in x]),
                "command": lambda x: "\n".join(x),
            }
            headers = ["name", "image", "ports", "volume_mounts", "command"]
            self.app.render(containers, headers=headers, transform=transform, maxsize=200)
            headers = ["name", "started", "state.running.started_at", "container_id"]
            self.app.render(container_statuses, headers=headers, maxsize=200)
            self.c("\nstatus", "underline")
            self.app.render(status, details=True)
            self.c("\nstatus - conditions", "underline")
            self.app.render(
                conditions,
                headers=["type", "status", "reason", "last_transition_time", "message"],
                maxsize=200,
            )

        elif namespace == "all":
            pods = v1.list_pod_for_all_namespaces(watch=False)
            res = pods.to_dict().get("items")
            transform = {"status.container_statuses.0.container_id": lambda x: x.split("//")[1][:12]}
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
            self.app.render(res, headers=headers, fields=fields, transform=transform)
        elif namespace is not None:
            pods = v1.list_namespaced_pod(namespace)
            res = pods.to_dict().get("items")
            # transform = {'status.container_statuses.0.container_id': lambda x: x.split('//')[1][:12]}
            transform = {}
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
            self.app.render(res, headers=headers, fields=fields, transform=transform)

    @ex(
        help="get k8s pod elk log count",
        description="get k8s pod elk log count",
        arguments=K8S_ARGS(
            [
                (
                    ["-id"],
                    {"help": "pod id", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def pod_elk_log_count(self):
        from kubernetes import client as k8s_client

        index = "podto2-k8s-mgmt-beehive-podto2-filebeat-7.12.0-2021.05.19-cmp_nivola"
        # index = 'dev-k8s-mgmt-01-beehive-lab5-filebeat-7.12.0-2021.05.19-cmp_nivola'
        self.es = self.config_elastic()

        namespace = self.get_namespace()
        v1 = k8s_client.CoreV1Api(self.client)
        pods = v1.list_namespaced_pod(namespace)
        pods = pods.to_dict().get("items")

        resp = []
        for item in pods:
            name = dict_get(item, "metadata.name")
            query = {"match": {"kubernetes.pod.name": {"query": name, "operator": "and"}}}
            body = {"query": query}
            res = self.es.count(index=index, body=body)
            resp.append({"name": name, "count": res.get("count")})
        self.app.render(resp, headers=["name", "count"])

    @ex(
        help="get k8s pod",
        description="get k8s pod",
        arguments=K8S_ARGS(
            [
                (
                    ["-name"],
                    {
                        "help": "pod name like",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {"help": "pod id", "action": "store", "type": str, "default": None},
                ),
                (
                    ["-lines"],
                    {
                        "help": "the number of lines from the end of the logs to show",
                        "action": "store",
                        "type": int,
                        "default": 20,
                    },
                ),
                (
                    ["-follow"],
                    {
                        "help": "follow the log stream of the pod",
                        "action": "store_true",
                    },
                ),
            ]
        ),
    )
    def pod_log(self):
        pod = self.app.pargs.id
        name = self.app.pargs.name
        namespace = self.get_namespace()
        tail_lines = self.app.pargs.lines
        follow = str2bool(self.app.pargs.follow)
        self.get_pod_log(namespace, oid=pod, name=name, tail_lines=tail_lines, follow=follow)

    @ex(
        help="connect to k8s pod",
        description="connect to k8s pod",
        arguments=K8S_ARGS(
            [
                (
                    ["id"],
                    {"help": "pod id", "action": "store", "type": str, "default": None},
                ),
                (
                    ["-cmd"],
                    {
                        "help": "command to run",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": "",
                    },
                ),
            ]
        ),
    )
    def pod_connect(self):
        from kubernetes import client as k8s_client
        from kubernetes.stream import stream

        pod = self.app.pargs.id
        cmd = self.app.pargs.cmd
        namespace = self.get_namespace()
        v1 = k8s_client.CoreV1Api(self.client)

        # Calling exec interactively
        exec_command = ["/bin/bash"]
        console = stream(
            v1.connect_get_namespaced_pod_exec,
            pod,
            namespace,
            command=exec_command,
            stderr=True,
            stdin=True,
            stdout=True,
            tty=True,
            _preload_content=False,
        )

        # from gevent import spawn, joinall, sleep, socket, queue
        # from gevent.os import make_nonblocking, nb_read, nb_write

        # def write_output():
        #     cmd = ''
        #     while console.is_open():
        #         try:
        #             console.update(timeout=1)
        #             if console.peek_stdout():
        #                 nb_write(console.read_stdout())
        #             if console.peek_stderr():
        #                 nb_write(console.read_stderr())
        #         except socket.timeout:
        #             self.app.log.error('', exc_info=True)
        #         except Exception:
        #             self.app.log.error('', exc_info=True)
        #         sleep(0.005)
        #
        # def get_input():
        #     while console.is_open():
        #         try:
        #             console.update(timeout=1)
        #             x = nb_read(sys.stdin.fileno(), 1024)
        #             console.write_stdin(x)
        #         except Exception:
        #             self.app.log.error('', exc_info=True)
        #             break
        #         sleep(0.005)
        #
        # joinall([
        #     spawn(get_input),
        #     spawn(write_output)
        # ])

        cmds = Queue()

        def read_stdin(console):
            while console.is_open():
                cmd = stdin.readline()
                if cmd is not None and console.is_open():
                    console.write_stdin(cmd)
                    # cmds.put(cmd)

        def write_stdout(console):
            while console.is_open():
                # stdout = console.read_stdout()
                # stderr = console.peek_stderr()
                # if stdout:
                #     sys.stdout.write(stdout)
                # if stderr:
                #     sys.stdout.write(stderr)
                if console.peek_stdout():
                    data = console.read_stdout()
                    # cmd = cmds.get()
                    # data.remove(cmd)
                    stdout.write(data)
                elif console.peek_stderr():
                    stdout.write(console.read_stderr())
                stdout.flush()

        ts = []
        t = Thread(target=write_stdout, args=(console,))
        ts.append(t)
        t.start()
        t = Thread(target=read_stdin, args=(console,))
        ts.append(t)
        t.start()

        for t in ts:
            t.join()

        console.close()

        # commands = [
        #     "echo This message goes to stdout",
        #     "echo \"This message goes to stderr\" >&2",
        # ]

        # while resp.is_open():
        #     resp.update(timeout=1)
        #     if resp.peek_stdout():
        #         print("STDOUT: %s" % resp.read_stdout())
        #     if resp.peek_stderr():
        #         print("STDERR: %s" % resp.read_stderr())
        #     if commands:
        #         c = commands.pop(0)
        #         print("Running command... %s\n" % c)
        #         resp.write_stdin(c + "\n")
        #     else:
        #         break

        # resp.write_stdin(cmd)
        # sdate = resp.readline_stdout(timeout=3)
        # print("Server date command returns: %s" % sdate)
        # resp.write_stdin("whoami\n")
        # user = resp.readline_stdout(timeout=3)
        # print("Server user is: %s" % user)

        # resp.write_stdin(cmd + '\n')
        # data = resp.readline_stdout(timeout=3)
        # print(data)
        # resp.close()

    @ex(
        help="query k8s app",
        description="query k8s app",
        arguments=K8S_ARGS(
            [
                (
                    ["app"],
                    {
                        "help": "app name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def app_get(self):
        app = self.app.pargs.app
        namespace = self.get_namespace()
        k8s_objects = self.show_application(app, namespace)
        self.print_k8s_response(k8s_objects)

    @ex(
        help="add k8s app",
        description="add k8s app",
        arguments=K8S_ARGS(
            [
                (["app"], {"help": "app name", "action": "store", "type": str}),
            ]
        ),
    )
    def app_add(self):
        app = self.app.pargs.app
        namespace = self.get_namespace()
        self.deploy_application(app, namespace)

    @ex(
        help="delete k8s app",
        description="delete k8s app",
        arguments=K8S_ARGS(
            [
                (
                    ["app"],
                    {
                        "help": "app name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def app_del(self):
        app = self.app.pargs.app
        namespace = self.get_namespace()
        self.undeploy_application(app, namespace)
