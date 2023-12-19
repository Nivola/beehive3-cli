# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive3_cli.core.controller import BaseController, PARGS
from cement import ex


class AwxController(BaseController):
    class Meta:
        label = "res_awx"
        stacked_on = "base"
        stacked_type = "nested"
        description = "awx orchestrator"
        help = "awx orchestrator"

        cmp = {"baseuri": "/v1.0/nrs/awx", "subsystem": "resource"}

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
        super(AwxController, self).pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help="get projects",
        description="get projects",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "project id",
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
            uri = "%s/projects/%s" % (self.baseuri, oid)
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
            uri = "%s/projects" % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="projects",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    @ex(
        help="get job templates",
        description="get job templates",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "job template id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def job_template_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = "%s/job_templates/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("job_template")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "%s/job_templates" % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="job_templates",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )
