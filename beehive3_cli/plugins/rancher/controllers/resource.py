# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from beehive3_cli.core.controller import BaseController, PARGS
from beehive3_cli.translate import _
from cement import ex


class RancherController(BaseController):
    class Meta:
        stacked_on = "base"
        stacked_type = "nested"
        label = "res_rancher"
        description = _("rancher orchestrator")
        help = _("rancher orchestrator")

        cmp = {"baseuri": "/v1.0/nrs/rancher", "subsystem": "resource"}

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

    def pre_command_run(self):
        super().pre_command_run()
        self.configure_cmp_api_client()

    @ex(
        help=_("get clusters"),
        description=_("get clusters"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("cluster id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def cluster_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/clusters/{oid}"
            res = self.cmp_get(uri)
            if self.is_output_text():
                res = res.get("cluster")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/clusters"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="clusters",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    def cluster_add(self):
        # TODO
        pass

    def cluster_del(self):
        # TODO
        pass

    @ex(
        help=_("get projects"),
        description=_("get projects"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/projects/{oid}"
            res = self.cmp_get(uri)
            if self.is_output_text():
                res = res.get("project")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/projects"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="projects",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    def project_add(self):
        # TODO
        pass

    def project_del(self):
        # TODO
        pass
