# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte
# (C) Copyright 2020-2021 CSI-Piemonte

from cement import ex
from beecell.simple import merge_list
from beehive3_cli.core.controller import PAGINATION_ARGS, BaseController, BASE_ARGS
from beehive3_cli.core.util import load_environment_config, CmpUtils


def ONTAP_ARGS(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {"action": "store", "dest": "orchestrator", "help": "ontap platform reference label"},
        ),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


def ONTAP_PARGS(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {"action": "store", "dest": "orchestrator", "help": "ontap platform reference label"},
        ),
    ]
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, orchestrator_args, *list_args)
    return res


class OntapController(BaseController):
    class Meta:
        label = "ontap"
        stacked_on = "platform"
        stacked_type = "nested"
        description = "netapp ontap management"
        help = "netapp ontap management"

    def get_pretty_size_precise(self, data):
        """
        size without decimal places
        """
        return self.get_pretty_size(data, try_precise=True)

    def get_pretty_size(self, data, try_precise=False):
        """
        Convert size to pretty string.
        NB: rounded to 2 decimal places (e.g. 1.994 -> 1.99, 1.995 -> 2)
        """
        try:
            data = float(data)

            KB = 1024
            MB = KB * 1024
            GB = MB * 1024
            TB = GB * 1024

            int_res = ""
            if try_precise:
                data_val = data
                data_unit = "B"
                if data >= KB and data % KB == 0:
                    data_val = data / KB
                    data_unit = "KB"
                if data >= MB and data % MB == 0:
                    data_val = data / MB
                    data_unit = "MB"
                if data >= GB and data % GB == 0:
                    data_val = data / GB
                    data_unit = "GB"
                if data >= TB and data % TB == 0:
                    data_val = data / TB
                    data_unit = "TB"
                int_res = f" ({data_val} {data_unit})"

            if KB < data < MB:
                data = f"{round(data / KB, 2)} KB{int_res}"
            elif MB <= data < GB:
                data = f"{round(data / MB, 2)} MB{int_res}"
            elif GB <= data < TB:
                data = f"{round(data / GB, 2)} GB{int_res}"
            elif data >= TB:
                data = f"{round(data / TB, 2)} TB{int_res}"
            else:
                data = f"{data} B"
        except ValueError as err:
            data = f"{data} B"
            self.app.log.error(f"Conv error for data {data}: {err}", exc_info=True)
        return data

    def pre_command_run(self):
        super(OntapController, self).pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("ontap", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No ontap default platform is available for this environment. Select another environment"
                )

        if label not in orchestrators:
            raise Exception("Valid labels are: %s" % ", ".join(orchestrators.keys()))
        conf = orchestrators.get(label)

        host = conf.get("host")
        port = conf.get("port", 80)
        proto = conf.get("proto", "http")
        user = conf.get("user")
        pwd = conf.get("pwd")

        if self.app.config.get("log.clilog", "verbose_log"):
            transform = {"msg": lambda x: self.color_string(x, "YELLOW")}
            self.app.render(
                {"msg": f"Using ontap orchestrator {label}: {proto}://{host}:{port} - user:{user}"},
                transform=transform,
            )
            self.app.log.debug(f"Using ontap orchestrator {label}: {proto}://{host}:{port} - user:{user}")

        from beedrones.ontapp.client import OntapManager

        self.client = OntapManager(host, user, pwd, port=port, proto=proto, timeout=30.0)
        self.client.authorize()

    @ex(help="ping ontap", description="ping ontap", arguments=ONTAP_ARGS())
    def ping(self):
        """
        Ping ontap
        """
        res = self.client.ping()
        self.app.render({"response": res}, headers=["response"])

    @ex(help="cluster get", description="cluster get", arguments=ONTAP_ARGS())
    def cluster_get(self):
        """
        Get ontap cluster
        """
        resp = self.client.cluster.get()
        self.app.render(resp, details=True, maxsize=200)

    @ex(help="cluster peer get", description="cluster peer get", arguments=ONTAP_ARGS())
    def cluster_peer_get(self):
        """
        Get ontap cluster peers
        """
        resp = self.client.cluster.list_peers()
        headers = ["uuid", "name"]
        fields = ["uuid", "name"]
        self.app.render(resp, headers=headers, fields=fields)

    @ex(
        help="get svm",
        description="get svm",
        arguments=ONTAP_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "svm uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "svm name like",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-order_by"],
                    {
                        "help": "order by",
                        "action": "store",
                        "type": str,
                        "default": "name",
                    },
                ),
            ]
        ),
    )
    def svm_get(self):
        """
        Get ontap svms
        """
        if self.app.pargs.id is not None:
            if not CmpUtils.is_valid_uuid(self.app.pargs.id):
                raise Exception("Provided id is not a valid uuid. Try again.")

            resp = self.client.svm.get(self.app.pargs.id)
            if self.is_output_text():
                ip_interfaces = resp.pop("ip_interfaces", [])
                aggregates = resp.pop("aggregates", [])
                self.app.render(resp, details=True)

                self.c("\nip_interfaces", "underline")
                headers = ["uuid", "name", "ip-address", "services"]
                fields = ["uuid", "name", "ip.address", "services"]
                self.app.render(ip_interfaces, headers=headers, fields=fields, maxsize=200)

                self.c("\naggregates", "underline")
                headers = ["uuid", "name"]
                fields = ["uuid", "name"]
                self.app.render(aggregates, headers=headers, fields=fields, maxsize=200)
            else:
                self.app.render(resp, details=True, maxsize=200)
        else:
            if self.app.pargs.name is not None:
                name = f"*{self.app.pargs.name}*"
            else:
                name = None
            resp = self.client.svm.list(**{"name": name, "order_by": self.app.pargs.order_by})

            headers = [
                "uuid",
                "name",
                "state",
                "nfs.enabled",
                "cifs.enabled",
                "ad_domain",
                "ip_interface",
                "ip.address",
            ]
            fields = [
                "uuid",
                "name",
                "state",
                "nfs.enabled",
                "cifs.enabled",
                "cifs.ad_domain.fqdn",
                "ip_interfaces.0.name",
                "ip_interfaces.0.ip.address",
            ]
            self.app.render(resp, headers=headers, fields=fields, maxsize=200)

    @ex(
        help="svm get peer",
        description="svm get peer",
        arguments=ONTAP_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "svm uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-svm"],
                    {
                        "help": "svm name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "name like",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-order_by"],
                    {
                        "help": "order by",
                        "action": "store",
                        "type": str,
                        "default": "name",
                    },
                ),
            ]
        ),
    )
    def svm_peer_get(self):
        """
        Get ontap svms peers
        """
        if self.app.pargs.id is not None:
            if not CmpUtils.is_valid_uuid(self.app.pargs.id):
                raise Exception("Provided id is not a valid uuid. Try again.")

            resp = self.client.svm.get_peer(self.app.pargs.id)
            if self.is_output_text():
                self.app.render(resp, details=True, maxsize=200)
            else:
                self.app.render(resp, details=True, maxsize=200)
        else:
            data = {"order_by": self.app.pargs.order_by}
            if self.app.pargs.svm:
                data["svm.name"] = self.app.pargs.svm
            if self.app.pargs.name:
                data["name"] = f"*{self.app.pargs.name}*"
            resp = self.client.svm.list_peers(**data)

            headers = ["uuid", "name", "state", "source-svm", "dest-svm", "dest-cluster", "applications"]
            fields = ["uuid", "name", "state", "svm.name", "peer.svm.name", "peer.cluster.name", "applications"]
            self.app.render(resp, headers=headers, fields=fields, maxsize=200)

    # volume #

    @ex(
        help="get volume",
        description="get volume",
        arguments=ONTAP_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "volume uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "volume name like",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-svm"],
                    {
                        "help": "svm name to limit the search to (volumes 'in that svm')",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-H"],
                    {
                        "help": "human readable (i.e. B, KB, MB, GB, TB)",
                        "action": "store_true",
                    },
                ),
                (
                    ["-precise"],
                    {"help": "show also size as precise integer multiple of bytes", "action": "store_true"},
                ),
            ]
        ),
    )
    def volume_get(self):
        """
        Get ontap volumes
        """
        if self.app.pargs.id is not None:
            if not CmpUtils.is_valid_uuid(self.app.pargs.id):
                raise Exception("Provided id is not a valid uuid. Try again.")

            resp = self.client.volume.get(self.app.pargs.id)
            if self.is_output_text():
                statistics = resp.pop("statistics", {})
                space = resp.pop("space", {})
                nas = resp.pop("nas", {})
                aggregates = resp.pop("aggregates", {})
                metric = resp.pop("metric", {})
                encryption = resp.pop("encryption", {})
                files = resp.pop("files", {})
                self.app.render(resp, details=True, maxsize=200)
                self.c("\nnas", "underline")
                self.app.render(nas, details=True, maxsize=200)
                security_style = nas.get("security_style", None)
                if security_style == "ntfs":
                    self.c("nas cifs:", "underline")
                    shares = self.client.protocol.list_cifs_shares(**{"volume.uuid": resp.get("uuid")})
                    for share in shares:
                        share.pop("_links")
                        share.pop("svm")
                        acls = share.pop("acls", [])
                        self.app.render(share, details=True, maxsize=200)
                        headers = ["acl.permission", "user_or_group", "type"]
                        fields = ["permission", "user_or_group", "type"]
                        self.app.render(acls, headers=headers, fields=fields, maxsize=200)
                elif security_style == "unix":
                    self.c("nas nfs:", "underline")
                    export_policy = nas.get("export_policy", None)
                    if export_policy is not None:
                        export_policy = self.client.protocol.get_nfs_export_policy(export_policy.get("id"))
                        export_policy_rules = export_policy.pop("rules", [])
                    headers = [
                        "rule.index",
                        "rw_rule",
                        "ro_rule",
                        "superuser",
                        "anonymous_user",
                        "protocols",
                        "clients",
                    ]
                    fields = ["index", "rw_rule", "ro_rule", "superuser", "anonymous_user", "protocols", "clients"]
                    self.app.render(export_policy_rules, headers=headers, fields=fields, maxsize=200)

                self.c("\nencryption", "underline")
                self.app.render(encryption, details=True, maxsize=200)

                self.c("\nfiles", "underline")
                self.app.render(files, details=True, maxsize=200)

                self.c("\nstatistics", "underline")
                self.app.render(statistics, details=True, maxsize=200)

                self.c("\nmetric", "underline")
                self.app.render(metric, details=True, maxsize=200)

                self.c("\nspace", "underline")
                self.app.render(space, details=True, maxsize=200)

                self.c("\naggregates", "underline")
                headers = ["uuid", "name"]
                fields = ["uuid", "name"]
                self.app.render(aggregates, headers=headers, fields=fields, maxsize=200)
            else:
                self.app.render(resp, details=True, maxsize=200)
        else:
            data = {}
            if self.app.pargs.svm:
                data["svm.name"] = self.app.pargs.svm
            if self.app.pargs.name:
                data["name"] = self.app.pargs.name
            resp = self.client.volume.list(**data)

            headers = [
                "uuid",
                "name",
                "svm",
                "type",
                "state",
                "size",
                "available",
                "security_style",
                "snapmirror",
                "create_time",
            ]
            fields = [
                "uuid",
                "name",
                "svm.name",
                "type",
                "state",
                "space.size",
                "space.available",
                "nas.security_style",
                "snapmirror.is_protected",
                "create_time",
            ]

            if self.app.pargs.H:
                if self.app.pargs.precise:
                    transform = {
                        "space.size": self.get_pretty_size_precise,
                        "space.available": self.get_pretty_size_precise,
                    }
                else:
                    transform = {"space.size": self.get_pretty_size, "space.available": self.get_pretty_size}
            else:
                transform = None

            self.app.render(resp, headers=headers, fields=fields, maxsize=200, transform=transform)

    @ex(
        help="get ontap volume snapshots",
        description="get ontap volume snapshots",
        arguments=ONTAP_ARGS(
            [
                (
                    ["volume"],
                    {
                        "help": "volume uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def volume_snapshot_get(self):
        snapshots = self.client.volume.get_snapshots(self.app.pargs.volume)
        headers = [
            "uuid",
            "name",
            "create_time",
            # "expiry_time",
            # "state"
        ]
        fields = [
            "uuid",
            "name",
            "create_time",
            # "expiry_time",
            # "state"
        ]
        self.app.render(snapshots, headers=headers, fields=fields, maxsize=200)

    @ex(
        help="get ontap snapmirror volumes",
        description="get ontap snapmirror volumes",
        arguments=ONTAP_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "svm uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-source_path"],
                    {
                        "help": "source path",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-source_svm"],
                    {
                        "help": "source svm",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dest_path"],
                    {
                        "help": "dest path",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def snapmirror_get(self):
        """
        Get snapmirror volumes
        """
        if self.app.pargs.id is not None:
            resp = self.client.snapmirror.get(self.app.pargs.id)
            if self.is_output_text():
                self.app.render(resp, details=True, maxsize=200)
            else:
                self.app.render(resp, details=True, maxsize=200)
        else:
            data = {}
            if self.app.pargs.dest_path:
                data["destination.path"] = self.app.pargs.dest_path
            if self.app.pargs.source_path:
                data["source.path"] = self.app.pargs.source_path
            if self.app.pargs.source_svm:
                data["source.svm.name"] = self.app.pargs.source_svm

            resp = self.client.snapmirror.list(**data)

            headers = [
                "uuid",
                "policy",
                "source-path",
                "dest-path",
                "dest-cluster",
                # "state",
                # "restore",
                # "healthy"
            ]
            fields = [
                "uuid",
                "policy.type",
                "source.path",
                "destination.path",
                "destination.cluster.name",
                # "state",
                # "restore",
                # "healthy",
            ]
            self.app.render(resp, headers=headers, fields=fields, maxsize=200)

    @ex(
        help="get ontap volume usage",
        description="get ontap volume usage",
        arguments=ONTAP_ARGS(
            [
                (["svms"], {"help": "comma separated list of svms", "action": "store", "type": str, "default": None}),
                (
                    ["-H"],
                    {
                        "help": "human readable (i.e. B, KB, MB, GB, TB)",
                        "action": "store_true",
                    },
                ),
                (
                    ["-precise"],
                    {"help": "show also size as precise integer multiple of bytes", "action": "store_true"},
                ),
            ]
        ),
    )
    def volume_usage(self):
        """
        Get ontap volume usage aggregated by svm
        """
        resp = []
        total = 0
        if self.app.pargs.svms is not None:
            svms = self.app.pargs.svms
            svms = svms.split(",")

        for svm in svms:
            res = self.client.volume.list(**{"svm.name": svm})
            subtotal = sum([item.get("space", {}).get("size", 0) for item in res if item.get("name").find("_root") < 0])
            total += subtotal
            res.append({"name": "TOTAL", "space": {"size": subtotal}})
            resp.extend(res)
        resp.append({"name": "FULL TOTAL", "space": {"size": total}})

        if self.app.pargs.H:
            if self.app.pargs.precise:
                transform = {"space.size": self.get_pretty_size_precise}
            else:
                transform = {"space.size": self.get_pretty_size}
        else:
            transform = None

        headers = ["uuid", "name", "svm", "type", "state", "size"]
        fields = ["uuid", "name", "svm.name", "type", "state", "space.size"]
        self.app.render(resp, headers=headers, fields=fields, maxsize=200, transform=transform)
