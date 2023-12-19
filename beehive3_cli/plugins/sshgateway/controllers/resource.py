# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte
# (C) Copyright 2020-2021 CSI-Piemonte

from beecell.simple import set_request_params
from beehive3_cli.core.controller import BaseController, PARGS, ARGS
from cement import ex


class SshGatewayResourceController(BaseController):
    class Meta:
        label = "res_sshgateway"
        stacked_on = "base"
        stacked_type = "nested"
        description = "ssh gateway orchestrator"
        help = "ssh gateway orchestrator"

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
        super(SshGatewayResourceController, self).pre_command_run()
        self.configure_cmp_api_client()

    @ex(
        help="get configuration",
        description="get configuration",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "configuration id",
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
            uri = "%s/configuration/%s" % (self.baseuri, oid)
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
            uri = "%s/configuration" % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="configurations",
                headers=self._meta.list_headers,
                fields=self._meta.list_fields,
            )

    @ex(
        help="add configuration",
        description="add configuration",
        arguments=ARGS(
            [
                (
                    ["container"],
                    {
                        "help": "container uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": "configuration name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["gw_type"],
                    {
                        "metavar": "gw_type",
                        "help": "ssh gateway type (gw_dbaas,gw_vm,gw_ext)",
                        "choices": ["gw_dbaas", "gw_vm", "gw_ext"],
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "configuration description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (["-res_id"], {"help": "resource uuid of the destination cli object"}),
                (
                    ["-ip_port"],
                    {
                        "help": "ip and port. only if gw_type=gw_ext",
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
        uri = "%s/configuration" % (self.baseuri)
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help="update configuration",
        description="update configuration",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
                (
                    ["-name"],
                    {
                        "help": "resource entity name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "resource entity description",
                        "action": "store",
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
        uri = "%s/configuration/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data={"configuration": data})
        self.app.render({"msg": "update configuration %s" % oid})

    @ex(
        help="delete configurations",
        description="delete configurations",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": "comma separated configuration ids",
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
            uri = "%s/configuration/%s?" % (self.baseuri, oid)
            self.cmp_delete(uri, entity="configuration %s" % oid)
