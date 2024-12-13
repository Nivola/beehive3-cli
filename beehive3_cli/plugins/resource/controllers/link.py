# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beecell.simple import set_request_params
from beehive3_cli.core.controller import BaseController, PARGS, ARGS
from cement import ex
from ujson import loads


class ResourceLinkController(BaseController):
    class Meta:
        stacked_on = "res"
        stacked_type = "nested"
        label = "links"
        description = "links management"
        help = "links management"

        cmp = {"baseuri": "/v1.0/nrs", "subsystem": "resource"}

        fields = [
            "id",
            "name",
            "active",
            "details.type",
            "details.start_resource",
            "details.end_resource",
            "details.attributes",
            "date.creation",
            "date.modified",
        ]
        headers = [
            "id",
            "name",
            "active",
            "type",
            "start",
            "end",
            "attributes",
            "creation",
            "modified",
        ]

    def pre_command_run(self):
        super(ResourceLinkController, self).pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help="list resource links",
        description="list resource links",
        example="beehive res links get 2143757;beehive res links get -id 2143757",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "link uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "link name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-resource"],
                    {
                        "help": "start or end resource uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "link type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": "link authorization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": "link tags",
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
            uri = "%s/links/%s" % (self.baseuri, oid)
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
            uri = "%s/links" % self.baseuri
            res = self.cmp_get(uri, data=data)

            transform = {"details.attributes.subnet": lambda x: x, "details.attributes.subnet.colortext": False}

            self.app.render(
                res,
                key="resourcelinks",
                headers=self._meta.headers,
                fields=self._meta.fields,
                transform=transform,
                maxsize=40,
            )

    @ex(
        help="add resource link",
        description="add resource link",
        example="beehive res links add link-49186-747644 relation 49186 747644 -e <env>;beehive res links add link-52343-747563 relation 52343 747563 -e <env>",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "resource link name", "action": "store", "type": str},
                ),
                (
                    ["type"],
                    {
                        "help": "resource link type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["start_resource"],
                    {"help": "start resource uuid", "action": "store", "type": str},
                ),
                (
                    ["end_resource"],
                    {"help": "end resource uuid", "action": "store", "type": str},
                ),
                (
                    ["-attributes"],
                    {
                        "help": "resource link attributes",
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
        type = self.app.pargs.type
        start_resource = self.app.pargs.start_resource
        end_resource = self.app.pargs.end_resource
        attrib = self.app.pargs.attributes
        if attrib is not None:
            attrib = loads(attrib)
        else:
            attrib = {}

        data = {
            "type": type,
            "name": name,
            "attributes": attrib,
            "start_resource": start_resource,
            "end_resource": end_resource,
        }
        uri = "%s/links" % self.baseuri
        res = self.cmp_post(uri, data={"resourcelink": data})
        self.app.render({"msg": "add resource link %s" % res["uuid"]})

    @ex(
        help="update resource link",
        description="update resource link",
        example="beehive res links update 2890463 -end_resource 17569 -e <env>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource link uuid", "action": "store", "type": str},
                ),
                (
                    ["-name"],
                    {
                        "help": "resource link name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "resource link type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-start_resource"],
                    {
                        "help": "start resource uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-end_resource"],
                    {
                        "help": "end resource uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": "resource link attributes",
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
        uri = "%s/links/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data={"resourcelink": data})
        self.app.render({"msg": "update resource link %s" % oid})

    @ex(
        help="patch resource links",
        description="patch resource links",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": "comma separated resource link uuids",
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
            uri = "%s/links/%s" % (self.baseuri, oid)
            self.cmp_patch(uri, data=data)
            self.app.render({"msg": "patch resource link %s" % oid})

    @ex(
        help="delete resource links",
        description="delete resource links",
        example="beehive res links delete #### -e <env>",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": "comma separated resource link uuids",
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
            uri = "%s/links/%s" % (self.baseuri, oid)
            if force is True:
                uri += "?force=true"
            self.cmp_delete(uri, entity="link %s" % oid)
