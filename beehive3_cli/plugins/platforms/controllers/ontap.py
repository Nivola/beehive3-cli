# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from typing import List, Dict
from cement import ex
from beecell.simple import merge_list
from beehive3_cli.core.controller import BaseController, BASE_ARGS
from beehive3_cli.core.util import load_environment_config, CmpUtils
from beehive3_cli.translate import _


def ontap_args(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {"action": "store", "dest": "orchestrator", "help": _("ontap platform reference label")},
        ),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


def ontap_pargs(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {"action": "store", "dest": "orchestrator", "help": _("ontap platform reference label")},
        ),
    ]
    # unfortunately mandatory, in order to change default sort field (id field would result in error)
    ontap_pagination_args = [
        (
            ["-size"],
            {
                "help": _("list page size [default=20]"),
                "action": "store",
                "type": int,
                "default": 20,
            },
        ),
        (
            ["-page"],
            {"help": _("list page [default=0]"), "action": "store", "type": int, "default": 0},
        ),
        (
            ["-field"],
            {
                "help": _("list sort field [default=id]"),
                "action": "store",
                "type": str,
                "default": "name",
            },
        ),
        (
            ["-order"],
            {
                "help": _("list sort order [default=DESC]"),
                "action": "store",
                "type": str,
                "default": "DESC",
            },
        ),
    ]
    res = merge_list(BASE_ARGS, ontap_pagination_args, orchestrator_args, *list_args)
    return res


class OntapController(BaseController):
    class Meta:
        label = "ontap"
        stacked_on = "platform"
        stacked_type = "nested"
        description = _("netapp ontap management")
        help = _("netapp ontap management")

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
            data_float = float(data)

            kb_size = 1024
            mb_size = kb_size * 1024
            gb_size = mb_size * 1024
            tb_size = gb_size * 1024

            int_res = ""
            if try_precise:
                data_val = data_float
                data_unit = "B"

                # Controllo sequenziale per trovare l'unità più grande compatibile
                if data_float >= tb_size and data_float % tb_size == 0:
                    data_val = data_float / tb_size
                    data_unit = "TB"
                elif data_float >= gb_size and data_float % gb_size == 0:
                    data_val = data_float / gb_size
                    data_unit = "GB"
                elif data_float >= mb_size and data_float % mb_size == 0:
                    data_val = data_float / mb_size
                    data_unit = "MB"
                elif data_float >= kb_size and data_float % kb_size == 0:
                    data_val = data_float / kb_size
                    data_unit = "KB"

                int_res = f" ({data_val} {data_unit})"

            if kb_size < data_float < mb_size:
                data = f"{round(data_float / kb_size, 2)} KB{int_res}"
            elif mb_size <= data_float < gb_size:
                data = f"{round(data_float / mb_size, 2)} MB{int_res}"
            elif gb_size <= data_float < tb_size:
                data = f"{round(data_float / gb_size, 2)} GB{int_res}"
            elif data_float >= tb_size:
                data = f"{round(data_float / tb_size, 2)} TB{int_res}"
            else:
                data = f"{data_float} B"

        except ValueError as err:
            error_msg = f"Conv error for data {data}: {err}"
            data = f"{data} B"
            self.app.log.error(error_msg, exc_info=True)

        return data

    def pre_command_run(self):
        super().pre_command_run()

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
            raise Exception(f"Valid labels are: {', '.join(orchestrators.keys())}")
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

        self.client = OntapManager(host, user, pwd, port=port, proto=proto, timeout=30.0, key=self.key)
        self.client.authorize()

    @ex(help=_("ping ontap"), description=_("ping ontap"), arguments=ontap_args())
    def ping(self):
        """
        Ping ontap
        """
        res = self.client.ping()
        self.app.render({"response": res}, headers=["response"])

    @ex(help=_("cluster get"), description=_("cluster get"), arguments=ontap_args())
    def cluster_get(self):
        """
        Get ontap cluster
        """
        resp = self.client.cluster.get()
        self.app.render(resp, details=True, maxsize=200)

    @ex(help=_("cluster peer get"), description=_("cluster peer get"), arguments=ontap_args())
    def cluster_peer_get(self):
        """
        Get ontap cluster peers
        """
        resp = self.client.cluster.list_peers()
        headers = ["uuid", "name"]
        fields = ["uuid", "name"]
        self.app.render(resp, headers=headers, fields=fields)

    @ex(
        help=_("get svm"),
        description=_("get svm"),
        arguments=ontap_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("svm uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("svm name like"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-order_by"],
                    {
                        "help": _("order by"),
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
        help=_("svm get peer"),
        description=_("svm get peer"),
        arguments=ontap_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("svm uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-svm"],
                    {
                        "help": _("svm name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("name like"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-order_by"],
                    {
                        "help": _("order by"),
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
        help=_("get volume"),
        description=_("get volume. it is possible to sort by name, create_date"),
        # can actually sort by any of the fields in "fields" (see implementation)
        arguments=ontap_pargs(
            [
                (
                    ["-id"],
                    {
                        "help": _("volume uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("volume name like filter. '*' is the wildcard character"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-svm"],
                    {
                        "help": _("svm name to limit the search to (volumes 'in that svm')"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-H"],
                    {
                        "help": _("human readable (i.e. B, KB, MB, GB, TB)"),
                        "action": "store_true",
                    },
                ),
                (
                    ["-precise"],
                    {"help": _("show also size as precise integer multiple of bytes"), "action": "store_true"},
                ),
            ]
        ),
    )
    def volume_get(self):
        """
        Get ontap volumes
        """
        size = self.app.pargs.size
        page = self.app.pargs.page
        field = self.app.pargs.field
        order = self.app.pargs.order
        order_by = None
        if field:
            order_by = f"{field} {order}"

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
                        self.__render_cifs_grants(acls)
                elif security_style == "unix":
                    self.c("nas nfs:", "underline")
                    export_policy = nas.get("export_policy", None)
                    export_policy_rules = []
                    if export_policy is not None:
                        export_policy = self.client.protocol.get_nfs_export_policy(export_policy.get("id"))
                        export_policy_rules = export_policy.pop("rules", [])
                    self.__render_nfs_grants(export_policy_rules)

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
            if size>0:
                data["max_records"] = size
            if page>0:
                data["page"] = page

            if self.app.pargs.svm:
                data["svm.name"] = self.app.pargs.svm
            if self.app.pargs.name:
                data["name"] = self.app.pargs.name
            if order_by:
                data["order_by"] = order_by

            res = self.client.volume.list(**data)

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

            if isinstance(res, dict):
                # paginated
                field, order = res.pop("order_by", "N/A N/A").split(" ") # type: ignore
                res["sort"] = {"field": field, "order": order}
                self.app.render(res, key="records", headers=headers, fields=fields, transform=transform)
            else:
                # old api. not paginated
                self.app.render(res, headers=headers, fields=fields, maxsize=200, transform=transform)

    @ex(
        help=_("get ontap volume snapshots"),
        description=_("get ontap volume snapshots"),
        arguments=ontap_args(
            [
                (
                    ["volume"],
                    {
                        "help": _("volume uuid"),
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
        help=_("dev:delete ontap volume"),
        description=_("delete ontap volume"),
        hide=True,
        arguments=ontap_args(
            [
                (
                    ["volume_uuid"],
                    {
                        "help": "ontap volume uuid",
                        "action": "store",
                        "type": str,
                        "default": None
                    }
                )
            ]
        )
    )
    def volume_del(self):
        volume_uuid = self.app.pargs.volume_uuid
        yn = self._ct.prompt_choice("This is dangerous. I know what I'm doing: ")
        if yn == "n":
            self.app.warning("Aborting operation.")
            return
        # checking it exists
        try:
            res = self.client.volume.get(volume_uuid, short_info=True)
        except Exception as ex:
            raise Exception("Error while retrieving volume. Error: %s" % ex) from ex
        self.app.render(res, details=True)
        yn = self._ct.prompt_choice("Please confirm again. I know what I'm doing: ")
        if yn == "n":
            self.app.warning("Aborting operation.")
        # deleting for real
        self.client.volume.delete(volume_uuid)
        self.app.print("Volume deleted successfully")

    @ex(
        help=_("get ontap snapmirror relationships"),
        description=_("get ontap snapmirror relationships"),
        arguments=ontap_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("relationship uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-source_path"],
                    {
                        "help": _("source path"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-source_svm"],
                    {
                        "help": _("source svm"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dest_path"],
                    {
                        "help": _("dest path"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dest_svm"],
                    {
                        "help": _("dest svm"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-get_policy_detail"],
                    {
                        "help": "get policy detail",
                        "action": "store_true",
                    },
                )
            ]
        ),
    )
    def snapmirror_get(self):
        """
        Get snapmirror relationships
        """
        if self.app.pargs.id is not None:
            resp = self.client.snapmirror.get(self.app.pargs.id, get_policy_detail=self.app.pargs.get_policy_detail)
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
            if self.app.pargs.dest_svm:
                data["destination.svm.name"] = self.app.pargs.dest_svm

            resp = self.client.snapmirror.list(search_local=True, search_remote=True, **data)

            headers = [
                "uuid",
                "source-path",
                "dest-path",
                "dest-cluster",
                "location",
                "state",
                "healthy",
                #"policy_name"
            ]
            fields = [
                "uuid",
                "source.path",
                "destination.path",
                "destination.cluster.name",
                "local_remote",
                "state",
                "healthy",
                #"policy.name"
            ]
            self.app.render(
                resp, headers=headers, fields=fields, maxsize=200,
                #detail_row_headers=detail_headers,
                #detail_row_fields=detail_fields
            )

    @ex(
        hide=True,
        help=_("delete ontap snapmirror relationships"),
        description=_("delete ontap snapmirror relationships"),
        arguments=ontap_args(
            [
                (
                    ["id"],
                    {
                        "help": _("relationship uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def snapmirror_delete(self):
        rel_id = self.app.pargs.id
        yn = self._ct.prompt_choice("This is dangerous. I know what I'm doing: ")
        if yn == "n":
            self.app.warning("Aborting operation.")
            return
        # checking it exists
        try:
            res = self.client.snapmirror.get(rel_id)
        except Exception as exception:
            raise Exception("Error while retrieving relationship. Not deletable through cli.") from exception
        self.app.render(res, details=True)
        yn = self._ct.prompt_choice("Please confirm again. I know what I'm doing: ")
        if yn == "n":
            self.app.warning("Aborting operation.")
        # deleting for real
        self.client.snapmirror.delete(rel_id)

    @ex(
        help=_("get ontap snaplock volume information"),
        description=_("get ontap snaplock volume information"),
        arguments=ontap_args(
            [
                (
                    ["id"],
                    {
                        "help": _("volume uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def snaplock_info(self):
        """
        get ontap volume snaplock info, if present
        """
        res = self.client.volume.get_snaplock_info(self.app.pargs.id)
        self.app.render(res, details=True)

    @ex(
        help=_("get ontap volume usage"),
        description=_("get ontap volume usage"),
        arguments=ontap_args(
            [
                (
                    ["svms"],
                    {"help": _("comma separated list of svms"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-H"],
                    {
                        "help": _("human readable (i.e. B, KB, MB, GB, TB)"),
                        "action": "store_true",
                    },
                ),
                (
                    ["-precise"],
                    {"help": _("show also size as precise integer multiple of bytes"), "action": "store_true"},
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
            subtotal = sum(item.get("space", {}).get("size", 0) for item in res if item.get("name").find("_root") < 0)
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

    # qtree #

    @ex(
        help=_("get qtree"),
        description=_("get qtree"),
        arguments=ontap_pargs(
            [
                (
                    ["-id"],
                    {
                        "help": _("qtree uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("qtree name like"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-volume_uuid"],
                    {
                        "help": _("id of the volume the qtree is in"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-volume_name"],
                    {
                        "help": _("name of the volume the qtree is in"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def qtree_get(self):
        volume_uuid = self.app.pargs.volume_uuid
        volume_name = self.app.pargs.volume_name
        qtree_id = self.app.pargs.id
        qtree_name = self.app.pargs.name
        size = self.app.pargs.size
        page = self.app.pargs.page
        field = self.app.pargs.field
        order = self.app.pargs.order

        if field == "uuid":
            field = "id"
        order_by = f"{field} {order}"

        if volume_uuid:
            if not CmpUtils.is_valid_uuid(volume_uuid):
                raise Exception("Provided id is not a valid uuid. Try again.")

        if volume_name is not None and qtree_id is not None:
            raise Exception("Use volume uuid instead of volume name to get qtree details.")

        if volume_uuid is not None and qtree_id is not None:
            resp = self.client.qtree.get(volume=volume_uuid, qtree=qtree_id)
            if self.is_output_text():
                # TODO
                self.app.render(resp, details=True, maxsize=200)
            else:
                self.app.render(resp, details=True, maxsize=200)
        else:
            data = {}
            if volume_name:
                data["volume.name"] = volume_name
            if volume_uuid:
                data["volume.uuid"] = volume_uuid
            if qtree_id:
                data["id"] = qtree_id
            if qtree_name:
                data["name"] = qtree_name
            if size:
                data["max_records"] = size
            if page:
                data["page"] = page
            if order_by:
                data["order_by"] = order_by
            resp = self.client.qtree.list(**data)

            headers = [
                "volume_id",
                "volume_name",
                "id",
                "name",
                "proto",
                "path",
            ]
            fields = [
                "volume.uuid",
                "volume.name",
                "id",
                "name",
                "security_style",
                "nas.path",
            ]
            field, order = resp.pop("order_by", "N/A N/A").split(" ")
            resp["sort"] = {"field": field, "order": order}
            self.app.render(resp, key="records", headers=headers, fields=fields, maxsize=200)

    # misc
    @ex(help=_("get version"), description=_("get version"), arguments=ontap_args())
    def version(self):
        res = self.client.version()
        self.app.render(res, details=True)

    @ex(help=_("get all quotas"), description=_("get all quotas"), arguments=ontap_args())
    def quotas_all(self):
        self.client.usage.list_all()

    # aggregates

    @ex(
        help=_("get aggregate"),
        description=_("get aggregate"),
        arguments=ontap_pargs(
            [
                (
                    ["-id"],
                    {
                        "help": _("aggregate uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("aggregate name like"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-show_space"],
                    {
                        "help": _("show aggregate total and available"),
                        "action": "store_true",
                        "default": False,
                    },
                ),
                (
                    ["-show_type"],
                    {
                        "help":_("show aggregate type (ssd or capacity)"),
                        "action":"store_true",
                        "default": False
                    }
                ),
                (
                    ["-show_node"],
                    {
                        "help":_("show aggregate nodes"),
                        "action":"store_true",
                        "default": False
                    }
                )
            ]
        ),
    )
    def aggregate_get(self):
        """
        Get ontap aggregate
        """
        page = self.app.pargs.page
        size = self.app.pargs.size
        aggregate_id = self.app.pargs.id

        field = self.app.pargs.field
        order = self.app.pargs.order

        order_by = None
        if field:
            order_by = f"{field} {order}"

        params = {"max_records": size, "page": page}
        if order_by:
            params["order_by"] = order_by

        show_space = self.app.pargs.show_space
        show_type = self.app.pargs.show_type
        show_node = self.app.pargs.show_node
        num_selected_options = show_space + show_type + show_node
        if num_selected_options > 1:
            self.app.warning(
                "options -show_space, -show_type, -show_node are mutually exclusive: defaulting to show_type"
            )
            show_space = False
            show_node = False
            show_type = True
        elif num_selected_options==0:
            show_type = True

        headers = [
            "aggregate uuid",
            "aggregate name",
        ]
        fields = [
            "uuid",
            "name"
        ]
        transform = {
            "space.block_storage.size": self.get_pretty_size,
            "space.block_storage.available": self.get_pretty_size,
        }

        res = {}
        if aggregate_id:
            res = self.client.aggregate.get(aggregate_id)
            self.app.render(res, details=True, maxsize=200)
        else:
            if show_space:
                headers.extend([
                    "size",
                    "available",
                ])
                fields.extend([
                    "space.block_storage.size",
                    "space.block_storage.available",
                ])

                # always order by space available = default behavior
                # remove any custom order
                params.pop("order_by", None)

                res: Dict = self.client.aggregate.list_with_space(**params) # type: ignore
            elif show_type:
                headers.extend([
                    "disk class",
                    "disk type"
                ])
                fields.extend([
                    "block_storage.primary.disk_class",
                    "block_storage.primary.disk_type"
                ])

                res: Dict = self.client.aggregate.list_with_disk_info(**params) # type: ignore
            elif show_node:
                headers.extend([
                    "node uuid",
                    "node name"
                ])
                fields.extend([
                    "node.uuid",
                    "node.name",
                ])

                res: Dict = self.client.aggregate.list_with_node(**params) # type: ignore
            field, order = res.pop("order_by", "N/A N/A").split(" ") # type: ignore
            res["sort"] = {"field": field, "order": order}
            self.app.render(res, key="records", headers=headers, fields=fields, transform=transform)

    # cifs share

    @ex(
        help=_("get cifs share"),
        description=_("get cifs share "),
        arguments=ontap_pargs(
            [
                (
                    ["-name"],
                    {
                        "help": _("share name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-svm_name"],
                    {
                        "help": _("svm name to limit the search to (shares 'in that svm')"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-svm_uuid"],
                    {
                        "help": _("svm uuid to limit the search to (shares 'in that svm')"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def share_get(self):
        """
        Get ontap cifs share
        """
        name = self.app.pargs.name
        svm_name = self.app.pargs.svm_name
        svm_uuid = self.app.pargs.svm_uuid
        page = self.app.pargs.page
        size = self.app.pargs.size
        field = self.app.pargs.field
        order = self.app.pargs.order

        if field != "name":
            field = "name"
        order_by = f"{field} {order}"

        if svm_uuid:
            if not CmpUtils.is_valid_uuid(svm_uuid):
                raise Exception("Provided id is not a valid uuid. Try again.")

        if name is not None and svm_name is not None:
            print(self.app.colored_text.yellow("Warning: use svm uuid instead of svm name to get share details."))

        if name is not None and svm_uuid is not None:
            if not CmpUtils.is_valid_uuid(svm_uuid):
                raise Exception("Provided svm id is not a valid uuid. Try again.")
            res = self.client.protocol.get_cifs_share(svm_uuid, name)
            self.app.render(res, details=True, maxsize=200)
        else:
            data = {}
            if name:
                data["name"] = name
            if svm_name:
                data["svm"] = svm_name
            if svm_uuid:
                raise Exception("Use svm name instead of svm uuid.")
            if size:
                data["max_records"] = size
            if page:
                data["page"] = page
            if order_by:
                data["order_by"] = order_by
            resp = self.client.protocol.list_cifs_shares(**data)

            headers = [
                "svm_uuid",
                "svm_name",
                "volume_uuid",
                "volume_name",
                "name",
                "path",
            ]
            fields = [
                "svm.uuid",
                "svm.name",
                "volume.uuid",
                "volume.name",
                "name",
                "path",
            ]
            field, order = resp.pop("order_by", "N/A N/A").split(" ")
            resp["sort"] = {"field": field, "order": order}
            self.app.render(resp, key="records", headers=headers, fields=fields, maxsize=200)

    @ex(
        help=_("get export policy"),
        description=_("get export policy"),
        arguments=ontap_args(
            [
                (
                    ["volume_id"],
                    {
                        "help": _("volume uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def export_policy_get(self):
        """
        Get ontap volume export policy a.k.a. access grant
        """
        volume_id = self.app.pargs.volume_id
        if not CmpUtils.is_valid_uuid(volume_id):
            raise Exception("Provided id is not a valid uuid. Try again.")
        res = self.client.volume.get(volume_id)
        if self.is_output_text():
            nas = res.pop("nas", {})
            security_style = nas.get("security_style", None)
            if security_style == "ntfs":
                shares = self.client.protocol.list_cifs_shares(**{"volume.uuid": res.get("uuid")})
                for share in shares:
                    acls = share.pop("acls", [])
                    self.__render_cifs_grants(acls)
            elif security_style == "unix":
                export_policy = nas.get("export_policy", None)
                export_policy_rules = []
                if export_policy is not None:
                    export_policy_id = export_policy.get("id")
                    export_policy = self.client.protocol.get_nfs_export_policy(export_policy_id)
                    export_policy_rules = export_policy.pop("rules", [])
                self.__render_nfs_grants(export_policy_rules)
            else:
                pass
        else:
            self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("get snapshot policies"),
        description=_("get snapshot policies"),
        arguments=ontap_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("snapshot policy uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def snapshot_policy_get(self):
        """
        Get snapshot policies.
        """
        snapshot_policy_id = self.app.pargs.id
        if snapshot_policy_id is not None:
            if not CmpUtils.is_valid_uuid(snapshot_policy_id):
                raise Exception("Provide a valid uuid. Try again.")
            res = self.client.snapshot_policy.get(snapshot_policy_id)
            res.pop("_links")
            self.app.render(res, details=True)
        else:
            res = self.client.snapshot_policy.list()
            headers = ["uuid", "name"]
            fields = ["uuid", "name"]
            self.app.render(res, headers=headers, fields=fields, maxsize=100)

    @ex(
        help=_("get snapmirror policies"),
        description=_("get snapmirror policies"),
        arguments=ontap_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("snapmirror policy uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["--order-by"],
                    {
                        "help": "order list by name or cmp_policy_type",
                        "action": "store",
                        "type": str,
                        "choices": ["name"],
                        "default": "name"
                    }
                ),
                (
                    ["--show-all"],
                    {
                        "help": "show also non-standard policies",
                        "action": "store_true",
                        "default": False
                    }
                )
            ]
        )
    )
    def snapmirror_policy_get(self):
        """
        Get snapmirror policies.
        """
        snapmirror_policy_id = self.app.pargs.id
        if snapmirror_policy_id is not None:
            if not CmpUtils.is_valid_uuid(snapmirror_policy_id):
                raise Exception("Provide a valid uuid. Try again.")
            res = self.client.snapmirror_policy.get(snapmirror_policy_id)
            res.pop("_links")
            self.app.render(res, details=True)
        else:
            order_by = self.app.pargs.order_by
            res = self.client.snapmirror_policy.list(
                order_by=order_by, show_all=self.app.pargs.show_all
            )
            headers = ["uuid", "name", "cmp_policy_type"]
            fields = ["uuid", "name", "cmp_policy_type"]
            self.app.render(res, headers=headers, fields=fields, maxsize=100)

    def __render_nfs_grants(self, grants: List):
        headers = [
            "index",
            "rw_rule",
            "ro_rule",
            "superuser",
            "protocols",
            "clients",
        ]
        transform = {
            "rw_rule": ", ".join,
            "ro_rule": ", ".join,
            "superuser": ", ".join,
            "protocols": ", ".join,
            "clients": lambda x: ", ".join([n["match"] for n in x]),
        }
        self.app.render(grants, headers=headers, maxsize=200, transform=transform)

    def __render_cifs_grants(self, grants: []):
        headers = ["acl_permission", "user_or_group", "type"]
        self.app.render(grants, headers=headers, maxsize=200)

    @ex(
        help=_("get volume(s) currently connected clients"),
        description=_("get volume(s) currently connected clients"),
        arguments=ontap_args(
            [
                (
                    ["-volume_id"],
                    {
                        "help": _("volume uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-svm_id"],
                    {
                        "help": _("svm uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    }
                ),
                (
                    ["-svm_name"],
                    {
                        "help": _("svm uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    }
                ),
            ]
        )
    )
    def connected_clients(self):
        volume_id = self.app.pargs.volume_id
        svm_id = self.app.pargs.svm_id
        svm_name = self.app.pargs.svm_name
        if svm_name:
            params = {"name": svm_name}
            svms = self.client.svm.list(**params)
            if not svms:
                raise Exception("svm %s not found" % svm_name)
            if len(svms)>1:
                raise Exception("more than one svm with name %s" % svm_name)
            svm = svms[0]
            svm_id = svm.get("uuid")

        clients = self.client.volume.connected_clients(volume_id, svm_id)

        # Sort by SVM, then volume, then client IP
        clients_sorted = sorted(
            clients,
            key=lambda c: (c.get("svm",{}).get("name"), c.get("volume",{}).get("name"))
        )

        headers = [
            "svm",
            "volume",
            "client_ip",
            "protocol"
        ]
        fields = [
            "svm.name",
            "volume.name",
            "client_ip",
            "protocol"
        ]
        self.app.render(clients_sorted, headers=headers, fields=fields)
