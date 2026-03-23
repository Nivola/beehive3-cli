# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex

from beehive3_cli.translate import _
from beehive3_cli.core.controller import BaseController, PARGS, ARGS


class ResourceTagController(BaseController):
    class Meta:
        stacked_on = "res"
        stacked_type = "nested"
        label = "tags"
        description = _("tags management")
        help = _("tags management")

        cmp = {"baseuri": "/v1.0/nrs", "subsystem": "resource"}

        fields = [
            "id",
            "name",
            "date.creation",
            "date.modified",
            "resources",
            "containers",
            "links",
        ]
        headers = [
            "id",
            "name",
            "creation",
            "modified",
            "resources",
            "containers",
            "links",
        ]

    def pre_command_run(self):
        super().pre_command_run()
        self.configure_cmp_api_client()

    @ex(
        help=_("list resource tags"),
        description=_("list resource tags"),
        example="beehive res tags get",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("tag uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("tag name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-resource"],
                    {
                        "help": _("resource"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/tags/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("resourcetag")
                self.app.render(res, details=True)
            else:
                self.app.render(res, key="resourcetag", details=True)
        else:
            params = [
                "container",
                # "type",
                "name",
                # "objid",
                # "ext_id",
                # "parent",
                # "state",
                # "tags",
                "resource",
            ]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/tags"

            def render(self, res, **kwargs):
                self.app.render(
                    res,
                    key="resourcetags",
                    headers=self._meta.headers,
                    fields=self._meta.fields,
                    maxsize=40,
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render, pagesize=50)

    @ex(
        help=_("add resource tag"),
        description=_("add resource tag"),
        arguments=ARGS(
            [
                (
                    ["value"],
                    {"help": _("resource tag value"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def add(self):
        value = self.app.pargs.value

        data = {
            "value": value,
        }
        uri = f"{self.baseuri}/tags"
        res = self.cmp_post(uri, data={"resourcetag": data})
        self.app.render({"msg": f"add resource tag {res['uuid']}"})

    @ex(
        help=_("update resource tag"),
        description=_("update resource tag"),
        arguments=ARGS(
            [
                (["id"], {"help": _("resource tag uuid"), "action": "store", "type": str}),
                (
                    ["-value"],
                    {
                        "help": _("resource tag value"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.id
        value = self.app.pargs.value
        uri = f"{self.baseuri}/tags/{oid}"
        self.cmp_put(uri, data={"resourcetag": {"value": value}})
        self.app.render({"msg": f"update resource tag {oid}"})

    @ex(
        help=_("patch resource tags"),
        description=_("patch resource tags"),
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": _("comma separated resource tag uuids"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def patch(self):
        oids = self.app.pargs.ids.split(",")
        params = {}
        for oid in oids:
            data = {"resourcetag": params}
            uri = f"{self.baseuri}/tags/{oid}"
            self.cmp_patch(uri, data=data)
            self.app.render({"msg": f"patch resource tag {oid}"})

    @ex(
        help=_("delete resource tags"),
        description=_("delete resource tags"),
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": _("comma separated resource tag uuids"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if true force the delete"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oids = self.app.pargs.ids.split(",")
        force = self.app.pargs.force
        for oid in oids:
            uri = f"{self.baseuri}/tags/{oid}"
            if force is True:
                uri += "?force=true"
            self.cmp_delete(uri, entity=f"tag {oid}")
