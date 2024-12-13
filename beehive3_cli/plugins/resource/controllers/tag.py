# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive3_cli.core.controller import BaseController, PARGS, ARGS
from cement import ex


class ResourceTagController(BaseController):
    class Meta:
        stacked_on = "res"
        stacked_type = "nested"
        label = "tags"
        description = "tags management"
        help = "tags management"

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
        super(ResourceTagController, self).pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help="list resource tags",
        description="list resource tags",
        example="beehive res tags get -size -1;beehive res tags get ",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "tag uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "tag name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-resource"],
                    {
                        "help": "resource",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-container"],
                    {
                        "help": "container uuid or name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "tag type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": "tag authorization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext_id"],
                    {
                        "help": "tag physical id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": "tag parent",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": "tag state",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": "tag attributes",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": "tag tags",
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
            uri = "%s/tags/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("resourcetag")
                self.app.render(res, details=True)
            else:
                self.app.render(res, key="resourcetag", details=True)
        else:
            params = [
                "container",
                "type",
                "name",
                "objid",
                "ext_id",
                "parent",
                "state",
                "tags",
                "resource",
            ]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "%s/tags" % self.baseuri

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
        help="add resource tag",
        description="add resource tag",
        arguments=ARGS(
            [
                (
                    ["value"],
                    {"help": "resource tag value", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def add(self):
        value = self.app.pargs.value

        data = {
            "value": value,
        }
        uri = "%s/tags" % self.baseuri
        res = self.cmp_post(uri, data={"resourcetag": data})
        self.app.render({"msg": "add resource tag %s" % res["uuid"]})

    @ex(
        help="update resource tag",
        description="update resource tag",
        arguments=ARGS(
            [
                (["id"], {"help": "resource tag uuid", "action": "store", "type": str}),
                (
                    ["-value"],
                    {
                        "help": "resource tag value",
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
        uri = "%s/tags/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data={"resourcetag": {"value": value}})
        self.app.render({"msg": "update resource tag %s" % oid})

    @ex(
        help="patch resource tags",
        description="patch resource tags",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": "comma separated resource tag uuids",
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
            uri = "%s/tags/%s" % (self.baseuri, oid)
            self.cmp_patch(uri, data=data)
            self.app.render({"msg": "patch resource tag %s" % oid})

    @ex(
        help="delete resource tags",
        description="delete resource tags",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": "comma separated resource tag uuids",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": "if true force the delete",
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
            uri = "%s/tags/%s" % (self.baseuri, oid)
            if force is True:
                uri += "?force=true"
            self.cmp_delete(uri, entity="tag %s" % oid)
