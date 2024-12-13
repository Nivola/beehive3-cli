# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beecell.types.type_list import merge_list
from cement import ex
from beedrones.rancher.client import RancherManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS, PAGINATION_ARGS
from beehive3_cli.core.util import load_environment_config


def RANCHER_ARGS(*list_args):
    orchestrator_args = [
        # (['-C', '--cluster'], {'action': 'store', 'dest': 'cluster', 'help': 'rancher cluster reference label'}),
    ]
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, orchestrator_args, *list_args)
    return res


class RancherPlatformController(BaseController):
    class Meta:
        label = "rancher"
        stacked_on = "platform"
        stacked_type = "nested"
        description = "rancher platform management"
        help = "rancher platform management"

    def pre_command_run(self):
        super(RancherPlatformController, self).pre_command_run()

        self.config = load_environment_config(self.app)
        orchestrators = self.config.get("orchestrators", {}).get("rancher", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No rancher default platform is available for this environment. Select another " "environment"
                )

        if label not in orchestrators:
            raise Exception("Valid labels are: %s" % ", ".join(orchestrators.keys()))
        self.conf = orchestrators.get(label)

        uri = self.conf.get("uri")
        self.client = RancherManager(uri)
        self.client.authorize(self.conf.get("user"), self.conf.get("pwd"), key=self.key)

    #
    # Base commands
    #
    @ex(help="ping rancher", description="ping rancher", arguments=RANCHER_ARGS())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(
        help="get server version",
        description="get server version",
        arguments=RANCHER_ARGS(),
    )
    def version(self):
        res = self.client.version()
        self.app.render(res, headers=["server-version"])

    #
    # Users management
    #
    @ex(
        help="get users",
        description="get users",
        arguments=RANCHER_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "user id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def user_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.user.get(oid)
            if self.is_output_text():
                self.app.render(res, details=True)
                self.c("\nglobal role bindings", "underline")
                res = self.client.user.get_global_role_bindings_by_user(oid)
                headers = ["id", "uuid", "name", "type", "role", "created"]
                fields = ["id", "uuid", "name", "type", "globalRoleId", "created"]
                self.app.render(res, key="data", headers=headers, fields=fields)
            else:
                self.app.render(res, details=True)
        else:
            size = self.app.pargs.size
            res = self.client.user.list(limit=size)
            headers = [
                "uuid",
                "id",
                "name",
                "description",
                "type",
                "state",
                "creator",
                "created",
            ]
            fields = [
                "uuid",
                "id",
                "name",
                "description",
                "type",
                "state",
                "creatorId",
                "created",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="add user",
        description="add user",
        arguments=RANCHER_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "user name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": "user password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-chpwd"],
                    {
                        "help": "change password flag, true or false",
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": "user role, one among admin, restricted-admin, user, user-base",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def user_add(self):
        name = self.app.pargs.name
        data = {
            "name": name,
            "username": name,
            "password": self.app.pargs.pwd,
            "enabled": True,
            "mustChangePassword": self.app.pargs.chpwd,
            "principalIds": [],
        }

        description = self.app.pargs.desc
        if description is not None:
            data.update("description")

        res = self.client.user.add(**data)
        if res.get("type") == "user":
            oid = res.get("id")
            self.app.render({"msg": "Create user %s" % oid})

            role = self.app.pargs.role
            if role is not None:
                self.client.user.set_global_role(oid, role)
                self.app.render({"msg": "Set global role %s to user %s" % (role, oid)})
        else:
            self.app.render({"msg": "%s" % res.get("message")})

    @ex(
        help="delete user",
        description="delete user",
        arguments=RANCHER_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "user id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def user_del(self):
        oid = self.app.pargs.id
        self.client.user.delete(oid)
        self.app.render({"msg": "Delete user %s" % oid})

    @ex(
        help="add user",
        description="add user",
        arguments=RANCHER_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "user id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["role"],
                    {"help": "role", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def user_set_global_role(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        res = self.client.user.set_global_role(oid, role)
        self.app.render({"msg": "Set global role %s to user %s" % (role, oid)})

    #
    # Clusters management
    #
    @ex(
        help="get clusters",
        description="get clusters",
        arguments=RANCHER_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "cluster id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def cluster_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            res = self.client.cluster.get(oid)
            if self.is_output_text():
                keys = [
                    "actions",
                    "agentImage",
                    "agentImageOverride",
                    "allocatable",
                    "annotations",
                    "answers",
                    "appliedEnableNetworkPolicy",
                    "appliedPodSecurityPolicyTemplateId",
                    "appliedSpec",
                    "authImage",
                    "capabilities",
                    "capacity",
                    "clusterTemplateId",
                    "clusterTemplateRevisionId",
                    "conditions",
                    "defaultClusterRoleForProjectMembers",
                    "defaultPodSecurityPolicyTemplateId",
                    "desiredAgentImage",
                    "desiredAuthImage",
                    "eksStatus",
                    "enableClusterAlerting",
                    "enableClusterMonitoring",
                    "enableNetworkPolicy",
                    "gkeStatus",
                    "istioEnabled",
                    "labels",
                    "limits",
                    "links",
                    "localClusterAuthEndpoint",
                    "requested",
                    "scheduledClusterScan",
                    "windowsPreferedCluster",
                ]
                for key in keys:
                    res.pop(key, None)
                self.app.render(res, details=True)
                self.c("\nprojects", "underline")
                res = self.client.cluster.get_projects(oid)
                headers = ["uuid", "id", "name", "state", "created"]
                fields = ["uuid", "id", "name", "state", "created"]
                self.app.render(res, key="data", headers=headers, fields=fields)
            else:
                self.app.render(res, details=True)
        else:
            size = self.app.pargs.size
            res = self.client.cluster.list(limit=size)
            headers = [
                "uuid",
                "id",
                "name",
                "description",
                "type",
                "state",
                "creator",
                "created",
            ]
            fields = [
                "uuid",
                "id",
                "name",
                "description",
                "type",
                "state",
                "creatorId",
                "created",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="Get projects within a cluster",
        description="Get projects within a cluster",
        arguments=RANCHER_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "cluster id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def cluster_projects_get(self):
        cluster_id = self.app.pargs.id
        res = self.client.cluster.get_projects(cluster_id)
        headers = [
            "id",
            "name",
            "description",
            "type",
            "state",
            "namespace",
            "created",
            "creator",
        ]
        fields = [
            "id",
            "name",
            "description",
            "baseType",
            "state",
            "namespaceId",
            "created",
            "creatorId",
        ]
        self.app.render(res, key="data", headers=headers, fields=fields)

    @ex(
        help="cluster user",
        description="cluster user",
        arguments=RANCHER_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "cluster name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-k8sv"],
                    {
                        "help": "kubernetes version",
                        "action": "store",
                        "type": str,
                        "default": "v1.20.11-rancher1-1",
                    },
                ),
                (
                    ["-netp"],
                    {
                        "help": "network provider, one among flannel, calico, canal, weave",
                        "action": "store",
                        "type": str,
                        "default": "canal",
                    },
                ),
                (
                    ["-cloudp"],
                    {
                        "help": "cloud provider",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def cluster_add(self):
        name = self.app.pargs.name
        k8s_version = self.app.pargs.k8sv
        network_provider = self.app.pargs.netp
        cloud_provider = self.app.pargs.cloudp
        data = {
            "name": name,
            "k8s_version": k8s_version,
            "network_provider": network_provider,
            "cloud_provider": cloud_provider,
        }
        res = self.client.cluster.add(**data)
        if res.get("type") == "cluster":
            oid = res.get("id")
            self.app.render({"msg": "Create cluster %s" % oid})
        else:
            self.app.render({"msg": "%s" % res.get("message")})

    @ex(
        help="Get cluster registration command",
        description="Get cluster registration command",
        arguments=RANCHER_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "cluster id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def cluster_get_registration_cmd(self):
        cluster_id = self.app.pargs.id
        res = self.client.cluster.get_registration_cmd(cluster_id)
        self.app.render(res, headers=["command"], fields=["command"], maxsize=500)
        self.app.render(res, headers=["insecure command"], fields=["insecureCommand"], maxsize=500)
        self.app.render(res, headers=["node command"], fields=["nodeCommand"], maxsize=500)
        self.app.render(
            res,
            headers=["windows node command"],
            fields=["windowsNodeCommand"],
            maxsize=500,
        )

    @ex(
        help="delete cluster",
        description="delete cluster",
        arguments=RANCHER_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "cluster id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def cluster_del(self):
        oid = self.app.pargs.id
        self.client.cluster.delete(oid)
        self.app.render({"msg": "Delete cluster %s" % oid})

    #
    # Projects management
    #
    def project_get(self):
        # TODO
        pass

    def project_add(self):
        # TODO
        pass

    def project_del(self):
        # TODO
        pass
