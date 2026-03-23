# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from ujson import loads
from cement import ex
from beecell.simple import set_request_params
from beehive3_cli.translate import _
from beehive3_cli.core.controller import BaseController, PARGS, ARGS


class ResourceLinkController(BaseController):
    class Meta:
        stacked_on = "res"
        stacked_type = "nested"
        label = "links"
        description = _("links management")
        help = _("links management")

        cmp = {"baseuri": "/v1.0/nrs", "subsystem": "resource"}

        fields = [
            "id",
            "name",
            "active",
            "details.type",
            "details.start_resource",
            "details.end_resource",
            "date.creation",
            "date.modified",
            "details.attributes",
        ]
        headers = [
            "id",
            "name",
            "active",
            "type",
            "start",
            "end",
            "creation",
            "modified",
            "attributes",
        ]

    def pre_command_run(self):
        super().pre_command_run()
        self.configure_cmp_api_client()

    @ex(
        help=_("list resource links"),
        description=_("list resource links"),
        example="beehive res links get -id 2143757",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("link uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("link name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-resource"],
                    {
                        "help": _("start or end resource uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("link type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": _("link authorization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("link tags"),
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
            uri = f"{self.baseuri}/links/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("resourcelink")
                details = res.pop("details")
                start_resource = details.pop("start_resource", {})
                end_resource = details.pop("end_resource", {})

                self.app.render(res, details=True)
                self.c("\ndetails", "underline")
                self.app.render(details, details=True)
                self.c("\nstart_resource", "underline")
                self.app.render(start_resource, details=True)
                self.c("\nend_resource", "underline")
                self.app.render(end_resource, details=True)
            else:
                self.app.render(res, key="resourcelink", details=True)
        else:
            params = ["name", "resource", "type", "objid", "tags"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/links"
            res = self.cmp_get(uri, data=data)

            transform = {"details.attributes.colortext": False}

            self.app.render(
                res,
                key="resourcelinks",
                headers=self._meta.headers,
                fields=self._meta.fields,
                transform=transform,
                maxsize=40,
            )

    @ex(
        help=_("add resource link"),
        description=_("add resource link"),
        example="beehive res links add link-49186-747644 relation 49186 747644 -e <env>",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("resource link name"), "action": "store", "type": str},
                ),
                (
                    ["type"],
                    {
                        "help": _("resource link type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["start_resource"],
                    {"help": _("start resource uuid"), "action": "store", "type": str},
                ),
                (
                    ["end_resource"],
                    {"help": _("end resource uuid"), "action": "store", "type": str},
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("resource link attributes"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add(self):
        name = self.app.pargs.name
        ltype = self.app.pargs.type
        start_resource = self.app.pargs.start_resource
        end_resource = self.app.pargs.end_resource
        attrib = self.app.pargs.attributes
        if attrib is not None:
            attrib = loads(attrib)
        else:
            attrib = {}

        data = {
            "type": ltype,
            "name": name,
            "attributes": attrib,
            "start_resource": start_resource,
            "end_resource": end_resource,
        }
        uri = f"{self.baseuri}/links"
        res = self.cmp_post(uri, data={"resourcelink": data})
        self.app.render({"msg": f"add resource link {res['uuid']}"})

    @ex(
        help=_("update resource link"),
        description=_("update resource link"),
        example="beehive res links update 2890463 -end_resource 17569 -e <env>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource link uuid"), "action": "store", "type": str},
                ),
                (
                    ["-name"],
                    {
                        "help": _("resource link name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("resource link type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-start_resource"],
                    {
                        "help": _("start resource uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-end_resource"],
                    {
                        "help": _("end resource uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("resource link attributes"),
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
        attrib = self.app.pargs.attributes
        data = set_request_params(
            self.app.pargs,
            ["name", "type", "start_resource", "end_resource", "attributes"],
        )
        if "attributes" in list(data.keys()):
            data["attributes"] = loads(attrib)
        else:
            attrib = {}
        uri = f"{self.baseuri}/links/{oid}"
        self.cmp_put(uri, data={"resourcelink": data})
        self.app.render({"msg": f"update resource link {oid}"})

    @ex(
        help=_("patch resource links"),
        description=_("patch resource links"),
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": _("comma separated resource link uuids"),
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
            data = {"resourcelink": params}
            uri = f"{self.baseuri}/links/{oid}"
            self.cmp_patch(uri, data=data)
            self.app.render({"msg": f"patch resource link {oid}"})

    @ex(
        help=_("delete resource links"),
        description=_("delete resource links"),
        example="beehive res links delete #### -e <env>",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": _("comma separated resource link uuids"),
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
            uri = f"{self.baseuri}/links/{oid}"
            if force is True:
                uri += "?force=true"
            self.cmp_delete(uri, entity=f"link {oid}")

    @ex(
        help=_("register resource link"),
        description=_("register resource link"),
        example="beehive res links register <id>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource link uuid"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def register(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/links/{oid}/register"
        self.cmp_put(uri)
