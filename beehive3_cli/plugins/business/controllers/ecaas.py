# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

import random
from urllib.parse import urlencode
from cement import ex

from beecell.types.type_dict import dict_get
from beecell.types.type_string import str2bool
from beehive3_cli.core.controller import ARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild
from beehive3_cli.translate import _


class ContaineraaServiceController(BusinessControllerChild):
    class Meta:
        label = "ecaas"
        description = _("container service management")
        help = _("container service management")

    @ex(
        help=_("get container service info"),
        description=_(
            "This command retrieves information about the container service for the specified account. "
            "The 'account' argument is required and specifies the account ID to get container info for."
        ),
        example="beehive bu ecaas info risca; beehive bu ecaas info ucs",
        arguments=ARGS(
            [
                (["account"], {"help": _("account id"), "action": "store", "type": str}),
            ]
        ),
    )
    def info(self):
        account = self.app.pargs.account
        account = self.get_account(account).get("uuid")
        data = {"owner-id": account}
        uri = f"{self.baseuri}/containerservices"
        res = self.cmp_get(uri, data=data)

        res = dict_get(res, "DescribeContainerResponse", default={})
        if len(res.get("containerSet")) > 0:
            res = dict_get(res, "containerSet.0")
            self.app.render(res, details=True, maxsize=400)

    @ex(
        help=_("get container service quotas"),
        description=_(
            "This command gets the container service quotas for a given account id. "
            "The account id is a required argument for this command to retrieve "
            "the quotas allocated to that account."
        ),
        example="beehive bu ecaas quotas <uuid>; beehive bu ecaas quotas <uuid>",
        arguments=ARGS(
            [
                (["account"], {"help": _("account id"), "action": "store", "type": str}),
            ]
        ),
    )
    def quotas(self):
        account = self.app.pargs.account
        account = self.get_account(account).get("uuid")
        data = {"owner-id": account}
        uri = f"{self.baseuri}/containerservices/describeaccountattributes"
        res = self.cmp_get(uri, data=urlencode(data))
        res = dict_get(res, "DescribeAccountAttributesResponse.accountAttributeSet")
        headers = ["name", "value", "used"]
        fields = [
            "attributeName",
            "attributeValueSet.0.item.attributeValue",
            "attributeValueSet.0.item.nvl-attributeUsed",
        ]
        self.app.render(res, headers=headers, fields=fields)


class ContainerServiceNamespaceController(BusinessControllerChild):
    class Meta:
        stacked_on = "ecaas"
        stacked_type = "nested"
        label = "namespaces"
        description = _("container namespace service management")
        help = _("container namespace service management")

        cmp = {"baseuri": "/v1.0/nws", "subsystem": "service"}

    @ex(
        help=_("list container namespaces"),
        description=_(
            "This command lists all the container namespaces configured in the Nivola CMP ecaas account specified. "
            "Namespaces are used to logically group container objects like servers, services etc. "
            "No arguments are required for this command to just display the namespace names."
        ),
        example="beehive bu ecaas namespaces list -account isee2015-preprod",
        arguments=ARGS(
            [
                (
                    ["-accounts"],
                    {
                        "help": _("list of account id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("list of container instances id comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("list of tag comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
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
    def list(self):
        params = ["accounts", "name", "tags"]
        mappings = {"accounts": self.get_account_ids, "tags": lambda x: x.split(","), "name": lambda n: "%" + n + "%"}
        aliases = {
            "accounts": "owner-id.N",
            # "name": "NamespaceName",
            "name": "name-pattern",
            "tags": "tag-key.N",
            "size": "MaxItems",
            "page": "Marker",
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = f"{self.baseuri}/containerservices/namespaces/describenamespaces"

        def render(self, res, **kwargs):
            page = kwargs.get("page", 0)
            res = res.get("DescribeNamespacesResponse")

            total = res.get("namespaceTotal")
            res = res.get("namespaceInfo", [])
            resp = {
                "count": len(res),
                "page": page,
                "total": total,
                "sort": {"field": "date.creation", "order": "desc"},
                "namespaces": res,
            }

            headers = [
                "id",
                "name",
                "status",
                "account",
                "cluster_name",
                "cpu",
                "memory",
                "storage",
                "chart",
                "network\npolicy\nactive",
                "creation"
            ]

            fields = [
                "id",
                "name",
                "state",
                "ownerAlias",
                "namespace.cluster_name",
                "namespace.limit_cpu",
                "namespace.limit_memory",
                "namespace.limit_storage",
                "namespace.chartTargetRevision",
                "namespace.networkPolicyActive",
                "creationDate"
            ]

            transform = {}
            self.app.render(
                resp,
                key="namespaces",
                headers=headers,
                fields=fields,
                maxsize=100,
                transform=transform,
            )

        self.cmp_get_pages(
            uri,
            data=data,
            pagesize=10,
            key_total_name="DescribeNamespacesResponse.namespaceTotal",
            key_list_name="DescribeNamespacesResponse.namespaceInfo",
            fn_render=render,
        )

    @ex(
        help=_("get container namespace"),
        description=_(
            "This command retrieves information about a specific container namespace. "
            "The namespace is identified by its unique id which must be provided as an required argument."
        ),
        example="beehive bu ecaas namespaces get <uuid>",
        arguments=ARGS(
            [
                (["id"], {"help": _("namespace id"), "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {"namespace-id.N": [oid]}  # container-namespace-id
        elif self.is_name(oid):
            data = {"NamespaceName": oid}
        uri = f"{self.baseuri}/containerservices/namespaces/describenamespaces"
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, "DescribeNamespacesResponse", default={})

        if len(res.get("namespaceInfo")) > 0:
            if self.is_output_text():
                res = dict_get(res, "namespaceInfo.0")
                namespace = res.pop("namespace", [])
                self.app.render(res, details=True, maxsize=400)

                self.c("\nnamespace", "underline")
                self.app.render(namespace, details=True, maxsize=400)
            else:
                self.app.render(res, details=True, maxsize=400)

    @ex(
        help=_("create a container namespace"),
        description=_(
            "This command creates a container namespace. "
            "It requires the parent account id as an argument to add the namespace under."
        ),
        example="beehive bu ecaas namespaces add ...",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {"help": _("parent account id"), "action": "store", "type": str},
                ),
                (
                    ["cluster_name"],
                    {
                        "help": _("cluster name rancher"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["codice_ente"],
                    {"help": _("codice ente"), "action": "store", "type": str},
                ),
                (
                    ["codice_prodotto"],
                    {"help": _("codice prodotto"), "action": "store", "type": str},
                ),
                (
                    ["environment"],
                    {"help": _("environment"), "action": "store", "type": str},
                ),
                (
                    ["-email_pm"],
                    {"help": _("email pm"), "action": "store", "type": str, "default": None},
                ),
                # limit
                (
                    ["limit_cpu"],
                    {"help": _("limit cpu"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["limit_memory"],
                    {"help": _("limit memory"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["limit_storage"],
                    {"help": _("limit storage"), "action": "store", "type": str, "default": None},
                ),
                # backup
                (
                    ["backup_policy"],
                    {"help": _("backup policy"), "action": "store", "type": str, "default": None},
                ),
                # abilitazioni
                (
                    ["-allowedHosts"],
                    {"help": _("allowedHosts"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-allowedCIDR"],
                    {"help": _("allowedCIDR"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-allowedHostPatterns"],
                    {"help": _("allowedHostPatterns"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-networkPolicyActive"],
                    {"help": _("networkPolicyActive"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-norescreate"],
                    {
                        "help": _("norescreate_namespace"),
                        "action": "store",
                        "type": str,
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get("uuid")
        cluster_name = self.app.pargs.cluster_name
        codice_ente = self.app.pargs.codice_ente
        codice_prodotto = self.app.pargs.codice_prodotto
        environment = self.app.pargs.environment
        email_pm = self.app.pargs.email_pm

        limit_cpu = self.app.pargs.limit_cpu
        limit_memory = self.app.pargs.limit_memory
        limit_storage = self.app.pargs.limit_storage

        backup_policy = self.app.pargs.backup_policy
        allowed_hosts = self.app.pargs.allowedHosts
        allowed_host_patterns = self.app.pargs.allowedHostPatterns
        allowed_cidr = self.app.pargs.allowedCIDR
        network_policy_active = self.app.pargs.networkPolicyActive
        norescreate = self.app.pargs.norescreate

        if not codice_ente.islower():
            raise Exception("codice_ente must be lowercase")
        if not codice_prodotto.islower():
            raise Exception("codice_prodotto must be lowercase")

        namespace_name = f"{codice_prodotto}-{codice_ente}-{environment}"
        data = {
            "owner-id": account,
            "name": namespace_name,
            "cluster_name": cluster_name,
            "codice_ente": codice_ente,
            "codice_prodotto": codice_prodotto,
            "environment": environment,
        }

        if email_pm is not None:
            data.update({"email_pm": email_pm})

        if limit_cpu is not None:
            data.update({"limit_cpu": limit_cpu})
        if limit_memory is not None:
            data.update({"limit_memory": limit_memory})
        if limit_storage is not None:
            data.update({"limit_storage": limit_storage})

        if backup_policy is not None:
            data.update({"backup_policy": backup_policy})

        if allowed_hosts is not None:
            if allowed_hosts == "-":
                allowed_hosts = ""
            data.update({"allowedHosts": allowed_hosts})

        if allowed_host_patterns is not None:
            if allowed_host_patterns == "-":
                allowed_host_patterns = ""
            data.update({"allowedHostPatterns": allowed_host_patterns})

        if allowed_cidr is not None:
            if allowed_cidr == "-":
                allowed_cidr = ""
            data.update({"allowedCIDR": allowed_cidr})

        if network_policy_active is not None:
            data.update({"networkPolicyActive": network_policy_active})

        if norescreate is not None:
            data.update({"norescreate": norescreate})

        # print('data: %s' % data)

        uri = f"{self.baseuri}/containerservices/namespaces/createnamespace"
        res = self.cmp_post(uri, data={"namespace": data}, timeout=600)

        create_namespace_response = dict_get(res, "CreateNamespaceResponse")
        namespace_id = dict_get(create_namespace_response, "namespaceId")
        self.wait_for_service(namespace_id)
        self.app.render({"msg": f"Add container namespace {namespace_id} in CMP and Git"})


    @ex(
        help=_("update a container namespace"),
        description=_(
            "This command updates a container namespace."
        ),
        example="beehive bu ecaas namespaces update <uuid> <params>",
        arguments=ARGS(
            [
                (
                    ["oid"],
                    {
                        "help": _("namespace oid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email_pm"],
                    {"help": _("email pm"), "action": "store", "type": str, "default": None},
                ),
                # limit
                (
                    ["-limit_cpu"],
                    {"help": _("limit cpu"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-limit_memory"],
                    {"help": _("limit memory"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-limit_storage"],
                    {"help": _("limit storage"), "action": "store", "type": str, "default": None},
                ),
                # backup
                (
                    ["-backup_policy"],
                    {"help": _("backup policy"), "action": "store", "type": str, "default": None},
                ),
                # abilitazioni
                (
                    ["-allowedHosts"],
                    {"help": _("allowedHosts"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-allowedCIDR"],
                    {"help": _("allowedCIDR"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-allowedHostPatterns"],
                    {"help": _("allowedHostPatterns"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-networkPolicyActive"],
                    {"help": _("networkPolicyActive"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-norescreate"],
                    {
                        "help": _("norescreate_namespace"),
                        "action": "store",
                        "type": str,
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.oid
        email_pm = self.app.pargs.email_pm

        limit_cpu = self.app.pargs.limit_cpu
        limit_memory = self.app.pargs.limit_memory
        limit_storage = self.app.pargs.limit_storage

        backup_policy = self.app.pargs.backup_policy
        allowed_hosts = self.app.pargs.allowedHosts
        allowed_host_patterns = self.app.pargs.allowedHostPatterns
        allowed_cidr = self.app.pargs.allowedCIDR
        network_policy_active = self.app.pargs.networkPolicyActive

        norescreate = self.app.pargs.norescreate

        data = {
            "oid": oid,
        }

        if email_pm is not None:
            data.update({"email_pm": email_pm})

        if limit_cpu is not None:
            data.update({"limit_cpu": limit_cpu})
        if limit_memory is not None:
            data.update({"limit_memory": limit_memory})
        if limit_storage is not None:
            data.update({"limit_storage": limit_storage})

        if backup_policy is not None:
            data.update({"backup_policy": backup_policy})

        if allowed_hosts is not None:
            if allowed_hosts == "-":
                allowed_hosts = ""
            data.update({"allowedHosts": allowed_hosts})

        if allowed_host_patterns is not None:
            if allowed_host_patterns == "-":
                allowed_host_patterns = ""
            data.update({"allowedHostPatterns": allowed_host_patterns})

        if allowed_cidr is not None:
            if allowed_cidr == "-":
                allowed_cidr = ""
            data.update({"allowedCIDR": allowed_cidr})

        if network_policy_active is not None:
            data.update({"networkPolicyActive": network_policy_active})

        if norescreate is not None:
            data.update({"norescreate": norescreate})

        # print('update data: %s' % data)

        uri = f"{self.baseuri}/containerservices/namespaces/updatenamespace"
        res = self.cmp_put(uri, data={"namespace": data}, timeout=600)

        update_namespace_response = dict_get(res, "UpdateNamespaceResponse")
        namespace_id = dict_get(update_namespace_response, "namespaceId")
        self.wait_for_service(namespace_id)
        self.app.render({"msg": f"Update container namespace {namespace_id} in CMP and Git"})


    @ex(
        help=_("delete a container namespace"),
        description=_(
            "Delete a container namespace by providing the container namespace id as an argument. "
            "This will remove the namespace and all child objects like dashboards, "
            "alerts etc within that namespace permanently."
        ),
        example="beehive bu ecaas namespaces delete <uuid>",
        arguments=ARGS(
            [
                (
                    ["container_namespace_id"],
                    {"help": _("container namespace id"), "action": "store", "type": str},
                ),
                (
                    ["-noresdelete"],
                    {
                        "help": _("noresdelete_namespace"),
                        "action": "store",
                        "type": str,
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def delete(self):
        container_namespace_id = self.app.pargs.container_namespace_id
        noresdelete = self.app.pargs.noresdelete

        data = {
            "NamespaceId": container_namespace_id,
        }

        b_noresdelete = False
        if noresdelete is not None:
            data.update({"noresdelete": noresdelete})
            b_noresdelete: bool = str2bool(noresdelete)

        entity = f"container namespace {container_namespace_id}"
        if not b_noresdelete:
            check_number = str(random.randint(1000, 9999))

            msg = self.app.colored_text.yellow(
                f"ATTENTION: if you are really sure you want to delete the "
                f"{entity} <<< COMPLETELY >>>, enter the code {check_number}: "
            )

            digits = input(msg)
            if digits != check_number:
                print("The code entered is incorrect")
                return

        uri = f"{self.baseuri}/containerservices/namespaces/deletenamespace"
        self.cmp_delete(uri, data=data, entity=entity, output=False)
        state = self.wait_for_service(container_namespace_id, accepted_state="DELETED")
        if state == "DELETED":
            if b_noresdelete:
                print(f"{entity} deleted in CMP")
            else:
                print(f"{entity} deleted in CMP and Git")

    @ex(
        help=_("get namespace clusters"),
        description=_(
            "This command is used to get namespace clusters"
        ),
        example="beehive bu ecaas namespace clusters test-vsphere",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("parent account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def clusters(self):
        data = {"owner-id": self.get_account(self.app.pargs.account)["uuid"]}
        uri = f"{self.baseuri}/containerservices/namespaces/clusternames"
        res = self.cmp_get(uri, data=data).get("DescribeNamespaceClusterNameResponse")
        self.app.render(
            res,
            headers=["cluster"],
            fields=["cluster_name"],
            key="clusterSet",
        )

    @ex(
        help=_("get namespace environments"),
        description=_(
            "This command is used to get namespace environments"
        ),
        example="beehive bu ecaas namespace environments test-vsphere",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("parent account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def environments(self):
        data = {"owner-id": self.get_account(self.app.pargs.account)["uuid"]}
        uri = f"{self.baseuri}/containerservices/namespaces/environments"
        res = self.cmp_get(uri, data=data).get("DescribeNamespaceEnvironmentResponse")
        self.app.render(
            res,
            headers=["environment"],
            fields=["environment_name"],
            key="environmentSet",
        )

    @ex(
        help=_("get namespace backup policies"),
        description=_(
            "This command is used to get namespace backup policies"
        ),
        example="beehive bu ecaas namespace backuppolicies test-vsphere",
        arguments=ARGS(
            [
                (
                    ["account"],
                    {
                        "help": _("parent account id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def backuppolicies(self):
        data = {"owner-id": self.get_account(self.app.pargs.account)["uuid"]}
        uri = f"{self.baseuri}/containerservices/namespaces/backuppolicies"
        res = self.cmp_get(uri, data=data).get("DescribeNamespaceBackupPolicyResponse")
        self.app.render(
            res,
            headers=["backup policy"],
            fields=["backup_policy_name"],
            key="backupPolicySet",
        )
