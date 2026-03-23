# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex
from beecell.simple import set_request_params
from beehive3_cli.core.controller import BaseController, PARGS, ARGS
from beehive3_cli.translate import _


class SshGatewayResourceController(BaseController):
    class Meta:
        label = "res_sshgateway"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("ssh gateway orchestrator")
        help = _("ssh gateway orchestrator")

        cmp = {"baseuri": "/v1.0/nrs/sshgateway", "subsystem": "resource"}

        headers = [
            "id",
            "uuid",
            "name",
            "desc",
            "ext_id",
            "parent",
            "container",
            "state",
        ]
        fields = [
            "id",
            "uuid",
            "name",
            "desc",
            "ext_id",
            "parent",
            "container",
            "state",
        ]

        list_headers = [
            "id",
            "uuid",
            "name",
            "desc",
            "container",
            "state",
            "gateway_type",
            "res_id",
            "ip_port",
        ]
        list_fields = [
            "id",
            "uuid",
            "name",
            "desc",
            "container",
            "state",
            "details.gw_type",
            "details.res_id",
            "details.ip_port",
        ]

    def pre_command_run(self):
        super().pre_command_run()
        self.configure_cmp_api_client()

    @ex(
        help=_("get configuration"),
        description=_("get configuration"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("configuration id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def configuration_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/configuration/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("configuration")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/configuration"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="configurations",
                headers=self._meta.list_headers,
                fields=self._meta.list_fields,
            )

    @ex(
        help=_("add configuration"),
        description=_("add configuration"),
        arguments=ARGS(
            [
                (
                    ["container"],
                    {
                        "help": _("container uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("configuration name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["gw_type"],
                    {
                        "metavar": "gw_type",
                        "help": _("ssh gateway type (gw_dbaas,gw_vm,gw_ext)"),
                        "choices": ["gw_dbaas", "gw_vm", "gw_ext"],
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("configuration description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (["-res_id"], {"help": _("resource uuid of the destination cli object")}),
                (
                    ["-ip_port"],
                    {
                        "help": _("ip and port. only if gw_type=gw_ext"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def configuration_add(self):
        if self.app.pargs.gw_type != "gw_ext" and self.app.pargs.res_id is None:
            self.app.pargs.ip_port = None
            self.app.error("you need to specify -res_id for the chosen value of gw_type")
            return

        if self.app.pargs.gw_type == "gw_ext" and self.app.pargs.res_id is None:
            self.app.pargs.res_id = None
            self.app.error("you need to specify -ip_port for the chosen value of gw_type")
            return

        configuration = {}
        configuration.update(set_request_params(self.app.pargs, ["container", "name", "desc", "gw_type", "res_id"]))
        data = {"configuration": configuration}
        uri = f"{self.baseuri}/configuration"
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help=_("update configuration"),
        description=_("update configuration"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
                (
                    ["-name"],
                    {
                        "help": _("resource entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("resource entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def configuration_update(self):
        oid = self.app.pargs.id
        data = set_request_params(self.app.pargs, ["name", "desc"])
        uri = f"{self.baseuri}/configuration/{oid}"
        self.cmp_put(uri, data={"configuration": data})
        self.app.render({"msg": f"update configuration {oid}"})

    @ex(
        help=_("delete configurations"),
        description=_("delete configurations"),
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": _("comma separated configuration ids"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def configuration_delete(self):
        oids = self.app.pargs.ids.split(",")

        for oid in oids:
            uri = f"{self.baseuri}/configuration/{oid}?"
            self.cmp_delete(uri, entity=f"configuration {oid}")
