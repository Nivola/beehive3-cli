# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from time import time
from cement import ex
from beecell.types.type_string import str2bool
from beehive3_cli.core.controller import BaseController, PARGS, ARGS
from beehive3_cli.core.util import load_config


class ResourceOrchestratorController(BaseController):
    class Meta:
        label = "containers"
        stacked_on = "res"
        stacked_type = "nested"
        description = "resource container management"
        help = "resource container management"

        cmp = {"baseuri": "/v1.0/nrs", "subsystem": "resource"}

        headers = [
            "id",
            "category",
            "objdef",
            "name",
            "active",
            "state",
            "ping",
            "creation",
            "modified",
            "resources",
        ]
        fields = [
            "id",
            "category",
            "__meta__.definition",
            "name",
            "active",
            "state",
            "ping",
            "date.creation",
            "date.modified",
            "resources",
        ]

    def pre_command_run(self):
        super(ResourceOrchestratorController, self).pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help="list resource containers",
        description="list resource containers",
        example="beehive res containers get;beehive res containers get -id # -e <env>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "container uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "container name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-container_type"],
                    {
                        "help": "container type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": "container authorization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": "container state",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": "container attributes",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": "entity tags",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-container_type_name"],
                    {
                        "help": "container type name",
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
            uri = "%s/containers/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                conn = res.get("resourcecontainer").pop("conn", {})

                self.app.render(res, key="resourcecontainer", details=True)
                self.c("\nconnection", "underline")
                self.app.render(conn, details=True)
            else:
                self.app.render(res, key="resourcecontainer", details=True)
        else:
            params = ["container_type", "name", "objid", "attributes", "state", "tags", "container_type_name"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "%s/containers" % self.baseuri
            res = self.cmp_get(uri, data=data)

            def color_error(val):
                if val == "ERROR":
                    val = self.app.colored_text.output(val, "REDonBLACK")
                return val

            transform = {"state": color_error}

            self.app.render(
                res,
                key="resourcecontainers",
                headers=self._meta.headers,
                fields=self._meta.fields,
                transform=transform,
                maxsize=400,
            )

    @ex(
        help="add resource container",
        description="add resource container",
        arguments=PARGS(
            [
                (
                    ["file"],
                    {
                        "help": "container config as file",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        data = {"resourcecontainer": data}
        uri = "%s/containers" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "add container %s" % res["uuid"]})

    @ex(
        help="update resource container",
        description="update resource container",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "container uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": "container config as file",
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
        data_file = self.app.pargs.file
        data = load_config(data_file)
        data = {"resourcecontainer": data}
        uri = "%s/containers/%s" % (self.baseuri, oid)
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "update container %s" % res["uuid"]})

    @ex(
        help="delete resource container",
        description="delete resource container",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "container uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = "%s/containers/%s" % (self.baseuri, oid)
        self.cmp_delete(uri, entity="resource container %s" % oid)

    @ex(
        help="delete cache containers",
        description="delete cache containers",
        arguments=PARGS([]),
    )
    def delete_cache(self):
        uri = "%s/containers/cache" % (self.baseuri)
        self.cmp_delete(uri, entity="resource cache containers")

    @ex(
        help="list resource container types",
        description="list resource container types",
        arguments=ARGS(),
    )
    def types(self):
        uri = "%s/containers/types" % self.baseuri
        res = self.cmp_get(uri)
        self.app.render(res, key="resourcecontainertypes", headers=["category", "type"])

    @ex(
        help="ping resource container",
        description="ping resource container",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "entity uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def ping(self):
        oid = self.app.pargs.id
        uri = "%s/containers/%s/ping" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(
            {"resourcecontainer": oid, "ping": res["ping"]},
            headers=["resourcecontainer", "ping"],
        )

    @ex(
        help="ping all resource containers",
        description="ping all resource container ",
        arguments=ARGS(),
    )
    def pings(self):
        """Ping all containers"""
        resp = []
        uri = "%s/containers" % self.baseuri
        res = self.cmp_get(uri)
        for rc in res["resourcecontainers"]:
            start = time()
            uri = "%s/containers/%s/ping" % (self.baseuri, rc["id"])
            res = self.cmp_get(uri)
            elapsed = time() - start
            resp.append(
                {
                    "uuid": rc["uuid"],
                    "name": rc["name"],
                    "ping": res["ping"],
                    "category": rc["category"],
                    "type": rc["__meta__"]["definition"],
                    "elapsed": elapsed,
                }
            )

        self.app.render(resp, headers=["uuid", "name", "category", "type", "ping", "elapsed"])

    @ex(
        help="discover container <class> resources",
        description="discover container <class> resources",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "entity uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def discover_types(self):
        oid = self.app.pargs.id
        uri = "%s/containers/%s/discover/types" % (self.baseuri, oid)
        res = self.cmp_get(uri, data="").get("discover_types")
        self.app.render(res, headers=["resource class"], fields=[0], maxsize=200)

    @ex(
        help="discover container",
        description="discover container",
        example="beehive res containers discover Podto1Openstack Provider.ComputeZone.ComputeStackV2 -e <env>;beehive res containers discover Podto1Vsphere Vsphere.DataCenter.Folder.Server -e <env>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "entity uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["resclass"],
                    {
                        "help": "entity resclass",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def discover(self):
        oid = self.app.pargs.id
        resclass = self.app.pargs.resclass
        uri = "%s/containers/%s/discover" % (self.baseuri, oid)
        res = self.cmp_get(uri, data="type=%s" % resclass, timeout=240).get("discover_resources")

        headers = ["id", "name", "parent", "type"]
        self.c("new resources", "underline")
        self.app.render(res, key="new", headers=headers, maxsize=200)
        self.c("died resources", "underline")
        self.app.render(res, key="died", headers=headers, maxsize=200)
        self.c("changed resources", "underline")
        self.app.render(res, key="changed", headers=headers, maxsize=200)

    @ex(
        help="discover container",
        description="discover container",
        example="beehive res containers discover Podto1Openstack Provider.ComputeZone.ComputeStackV2 -e <env>;beehive res containers discover Podto1Vsphere Vsphere.DataCenter.Folder.Server -e <env>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "entity uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def discovers(self):
        oid = self.app.pargs.id

        # get types
        uri = "%s/containers/%s/discover/types" % (self.baseuri, oid)
        types = self.cmp_get(uri, data="").get("discover_types")

        res = {"new": [], "died": [], "changed": []}
        for type in types:
            uri = "%s/containers/%s/discover" % (self.baseuri, oid)
            parres = self.cmp_get(uri, data="type=%s" % type).get("discover_resources")
            res["new"].extend(parres["new"])
            res["died"].extend(parres["died"])
            res["changed"].extend(parres["changed"])

        headers = ["id", "name", "parent", "type"]
        self.c("new resources", "underline")
        self.app.render(res, key="new", headers=headers)
        self.c("died resources", "underline")
        self.app.render(res, key="died", headers=headers)
        self.c("changed resources", "underline")
        self.app.render(res, key="changed", headers=headers)

    @ex(
        help="synchronize container <class> resources",
        description="synchronize container <class> resources",
        example="beehive res containers synchronizes Podto1Grafana;beehive res containers synchronize Podto2Vsphere Vsphere.DataCenter.Folder.Server -e <env>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "container id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["resclass"],
                    {
                        "help": "entity resclass",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-new"],
                    {
                        "help": "add new physical entities. Default True",
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-died"],
                    {
                        "help": "delete not alive physical entities. Default False",
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
                (
                    ["-changed"],
                    {
                        "help": "update physical entities. Default False",
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
                (
                    ["-ext_id"],
                    {
                        "help": "physical entity id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def synchronize(self):
        oid = self.app.pargs.id
        new = str2bool(self.app.pargs.new)
        died = str2bool(self.app.pargs.died)
        changed = str2bool(self.app.pargs.changed)

        resclass = self.app.pargs.resclass
        ext_id = self.app.pargs.ext_id
        data = {"types": resclass, "new": new, "died": died, "changed": changed}
        if ext_id is not None:
            data["ext_id"] = ext_id
        uri = "%s/containers/%s/discover" % (self.baseuri, oid)
        self.cmp_put(uri, data={"synchronize": data})

    @ex(
        help="synchronize container resources",
        description="synchronize container resources",
        example="beehive res containers synchronizes Podto1Grafana;beehive res containers synchronizes Podto2Grafana",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "entity uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def synchronizes(self):
        oid = self.app.pargs.id

        # get types
        uri = "%s/containers/%s/discover/types" % (self.baseuri, oid)
        types = self.cmp_get(uri, data="").get("discover_types")

        for type in types:
            self.c("synchronize %s" % type, "underline")
            data = {
                "synchronize": {
                    "types": type,
                    "new": True,
                    "died": True,
                    "changed": True,
                }
            }
            uri = "%s/containers/%s/discover" % (self.baseuri, oid)
            self.cmp_put(uri, data=data)
