# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from beecell.types.type_list import merge_list
from cement import ex
from beedrones.rancher.client import RancherManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS, PAGINATION_ARGS
from beehive3_cli.core.util import load_environment_config
from beehive3_cli.translate import _


def rancher_args(*list_args):
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
        description = _("rancher platform management")
        help = _("rancher platform management")

    def pre_command_run(self):
        super().pre_command_run()

        self.config = load_environment_config(self.app)
        orchestrators = self.config.get("orchestrators", {}).get("rancher", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No rancher default platform is available for this environment. Select another environment"
                )

        if label not in orchestrators:
            raise Exception(f"Valid labels are: {', '.join(orchestrators.keys())}")
        self.conf = orchestrators.get(label)

        uri = self.conf.get("uri")
        self.client = RancherManager(uri)
        self.client.authorize(self.conf.get("user"), self.conf.get("pwd"), key=self.key)

    #
    # Base commands
    #
    @ex(help=_("ping rancher"), description=_("ping rancher"), arguments=rancher_args())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(
        help=_("get server version"),
        description=_("get server version"),
        arguments=rancher_args(),
    )
    def version(self):
        res = self.client.version()
        self.app.render(res, headers=["server-version"])

    #
    # Users management
    #
    @ex(
        help=_("get users"),
        description=_("get users"),
        arguments=rancher_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("user id"),
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
        help=_("add user"),
        description=_("add user"),
        arguments=rancher_args(
            [
                (
                    ["name"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": _("user password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-chpwd"],
                    {
                        "help": _("change password flag, true or false"),
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
                (
                    ["-role"],
                    {
                        "help": _("user role, one among admin, restricted-admin, user, user-base"),
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
            self.app.render({"msg": f"Create user {oid}"})

            role = self.app.pargs.role
            if role is not None:
                self.client.user.set_global_role(oid, role)
                self.app.render({"msg": f"Set global role {role} to user {oid}"})
        else:
            self.app.render({"msg": f"{res.get('message')}"})

    @ex(
        help=_("delete user"),
        description=_("delete user"),
        arguments=rancher_args(
            [
                (
                    ["id"],
                    {
                        "help": _("user id"),
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
        self.app.render({"msg": f"Delete user {oid}"})

    @ex(
        help=_("add user"),
        description=_("add user"),
        arguments=rancher_args(
            [
                (
                    ["id"],
                    {
                        "help": _("user id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["role"],
                    {"help": _("role"), "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def user_set_global_role(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        self.client.user.set_global_role(oid, role)
        self.app.render({"msg": f"Set global role {role} to user {oid}"})

    #
    # Clusters management
    #
    @ex(
        help=_("get clusters"),
        description=_("get clusters"),
        arguments=rancher_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("cluster id"),
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
        help=_("Get projects within a cluster"),
        description=_("Get projects within a cluster"),
        arguments=rancher_args(
            [
                (
                    ["id"],
                    {
                        "help": _("cluster id"),
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
        help=_("cluster user"),
        description=_("cluster user"),
        arguments=rancher_args(
            [
                (
                    ["name"],
                    {
                        "help": _("cluster name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-k8sv"],
                    {
                        "help": _("kubernetes version"),
                        "action": "store",
                        "type": str,
                        "default": "v1.20.11-rancher1-1",
                    },
                ),
                (
                    ["-netp"],
                    {
                        "help": _("network provider, one among flannel, calico, canal, weave"),
                        "action": "store",
                        "type": str,
                        "default": "canal",
                    },
                ),
                (
                    ["-cloudp"],
                    {
                        "help": _("cloud provider"),
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
            self.app.render({"msg": f"Create cluster {oid}"})
        else:
            self.app.render({"msg": f"{res.get('message')}"})

    @ex(
        help=_("Get cluster registration command"),
        description=_("Get cluster registration command"),
        arguments=rancher_args(
            [
                (
                    ["id"],
                    {
                        "help": _("cluster id"),
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
        help=_("delete cluster"),
        description=_("delete cluster"),
        arguments=rancher_args(
            [
                (
                    ["id"],
                    {
                        "help": _("cluster id"),
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
        self.app.render({"msg": f"Delete cluster {oid}"})

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
