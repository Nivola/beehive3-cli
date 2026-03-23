# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from time import time
from cement import ex

from beecell.types.type_string import str2bool

from beehive3_cli.core.controller import BaseController, PARGS, ARGS
from beehive3_cli.core.util import load_config
from beehive3_cli.translate import _


class ResourceOrchestratorController(BaseController):
    class Meta:
        label = "containers"
        stacked_on = "res"
        stacked_type = "nested"
        description = _("resource container management")
        help = _("resource container management")

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
        super().pre_command_run()
        self.configure_cmp_api_client()

    @ex(
        help=_("list resource containers"),
        description=_("list resource containers"),
        example="beehive res containers get; beehive res containers get -id # -e <env>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("container uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("container name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-container_type"],
                    {
                        "help": _("container type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": _("container authorization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("container state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": _("container attributes"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-container_type_name"],
                    {
                        "help": _("container type name"),
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
            uri = f"{self.baseuri}/containers/{oid}"
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
            uri = f"{self.baseuri}/containers"
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
        help=_("dev: register resource container type"),
        description=_("register resource container type"),
        arguments=PARGS(
            [
                (
                    ["container_type_name"],
                    {
                        "help": _("container type name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
        hide=True
    )
    def register_type(self):
        uri = f"{self.baseuri}/containers/types/register"
        data = {"container_type_name": self.app.pargs.container_type_name}
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help=_("add resource container"),
        description=_("add resource container"),
        arguments=PARGS(
            [
                (
                    ["file"],
                    {
                        "help": _("container config as file"),
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
        uri = f"{self.baseuri}/containers"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add container {res['uuid']}"})

    @ex(
        help=_("update resource container"),
        description=_(
            """update resource container
            the file shall be a json or yaml
             the schema
            name = fields.String(default="test")
            desc = fields.String(default="test")
            active = fields.Boolean(default=True)
            conn = fields.Dict(default={})
            state = fields.Integer(default=0)
            tags = fields.Nested(UpdateResourceTagDescRequestSchema, allow_none=True)
            where
            class UpdateResourceTagDescRequestSchema(Schema):
            cmd = fields.String(default="add", required=True)
            values = fields.List(fields.String(default="test"), required=True)

        """
        ),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("container uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("container config as file"),
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
        uri = f"{self.baseuri}/containers/{oid}"
        res = self.cmp_put(uri, data=data)
        self.app.render({"msg": f"update container {res['uuid']}"})

    @ex(
        help=_("delete resource container"),
        description=_("delete resource container"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("container uuid"),
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
        uri = f"{self.baseuri}/containers/{oid}"
        self.cmp_delete(uri, entity=f"resource container {oid}")

    @ex(
        help=_("delete cache containers"),
        description=_("delete cache containers"),
        arguments=PARGS([]),
    )
    def delete_cache(self):
        uri = f"{self.baseuri}/containers/cache"
        self.cmp_delete(uri, entity="resource cache containers")

    @ex(
        help=_("list resource container types"),
        description=_("list resource container types"),
        arguments=ARGS(),
    )
    def types(self):
        uri = f"{self.baseuri}/containers/types"
        res = self.cmp_get(uri)
        self.app.render(res, key="resourcecontainertypes", headers=["category", "type"])

    @ex(
        help=_("ping resource container"),
        description=_("ping resource container"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("entity uuid"),
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
        uri = f"{self.baseuri}/containers/{oid}/ping"
        res = self.cmp_get(uri)
        self.app.render(
            {"resourcecontainer": oid, "ping": res["ping"]},
            headers=["resourcecontainer", "ping"],
        )

    @ex(
        help=_("ping all resource containers"),
        description=_("ping all resource container "),
        arguments=ARGS(),
    )
    def pings(self):
        """Ping all containers"""
        resp = []
        uri = f"{self.baseuri}/containers"
        res = self.cmp_get(uri)
        for rc in res["resourcecontainers"]:
            start = time()
            uri = f"{self.baseuri}/containers/{rc['id']}/ping"
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
        help=_("discover container <class> resources"),
        description=_("discover container <class> resources"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("entity uuid"),
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
        uri = f"{self.baseuri}/containers/{oid}/discover/types"
        res = self.cmp_get(uri, data="").get("discover_types")
        self.app.render(res, headers=["resource class"], fields=[0], maxsize=200)

    @ex(
        help=_("discover container"),
        description=_("discover container"),
        example=(
            "beehive res containers discover Podto1Openstack Provider.ComputeZone.ComputeStackV2 -e <env>; "
            "beehive res containers discover Podto1Vsphere Vsphere.DataCenter.Folder.Server -e <env>"
        ),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("entity uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["resclass"],
                    {
                        "help": _("entity resclass"),
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
        uri = f"{self.baseuri}/containers/{oid}/discover"
        res = self.cmp_get(uri, data=f"type={resclass}", timeout=240).get("discover_resources")

        headers = ["id", "name", "parent", "type"]
        self.c("new resources", "underline")
        self.app.render(res, key="new", headers=headers, maxsize=200)
        self.c("died resources", "underline")
        self.app.render(res, key="died", headers=headers, maxsize=200)
        self.c("changed resources", "underline")
        self.app.render(res, key="changed", headers=headers, maxsize=200)

    @ex(
        help=_("discover container (only remote)"),
        description=_("discover container (only remote)"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("entity uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["resclass"],
                    {
                        "help": _("entity resclass"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def discover_remote(self):
        oid = self.app.pargs.id
        resclass = self.app.pargs.resclass
        uri = f"{self.baseuri}/containers/{oid}/discover_remote"
        res = self.cmp_get(uri, data=f"type={resclass}", timeout=240).get("discover_resources")
        print(res)

    @ex(
        help=_("discover container"),
        description=_("discover container"),
        example=(
            "beehive res containers discover Podto1Openstack Provider.ComputeZone.ComputeStackV2 -e <env>; "
            "beehive res containers discover Podto1Vsphere Vsphere.DataCenter.Folder.Server -e <env>"
        ),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("entity uuid"),
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
        uri = f"{self.baseuri}/containers/{oid}/discover/types"
        types = self.cmp_get(uri, data="").get("discover_types")

        res = {"new": [], "died": [], "changed": []}
        for dtype in types:
            uri = f"{self.baseuri}/containers/{oid}/discover"
            parres = self.cmp_get(uri, data=f"type={dtype}").get("discover_resources")
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
        help=_("synchronize container <class> resources"),
        description=_("synchronize container <class> resources"),
        example=(
            "beehive res containers synchronizes Podto1Grafana; "
            "beehive res containers synchronize Podto2Vsphere Vsphere.DataCenter.Folder.Server -e <env>"
        ),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("container id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["resclass"],
                    {
                        "help": _("entity resclass"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-new"],
                    {
                        "help": _("add new physical entities. Default True"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-died"],
                    {
                        "help": _("delete not alive physical entities. Default False"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
                (
                    ["-changed"],
                    {
                        "help": _("update physical entities. Default False"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
                (
                    ["-ext_id"],
                    {
                        "help": _("physical entity id"),
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
        uri = f"{self.baseuri}/containers/{oid}/discover"
        self.cmp_put(uri, data={"synchronize": data})

    @ex(
        help=_("synchronize container resources"),
        description=_("synchronize container resources"),
        example="beehive res containers synchronizes Podto1Grafana; beehive res containers synchronizes Podto2Grafana",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("entity uuid"),
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
        uri = f"{self.baseuri}/containers/{oid}/discover/types"
        types = self.cmp_get(uri, data="").get("discover_types")

        for dtype in types:
            self.c(f"synchronize {dtype}", "underline")
            data = {
                "synchronize": {
                    "types": dtype,
                    "new": True,
                    "died": True,
                    "changed": True,
                }
            }
            uri = f"{self.baseuri}/containers/{oid}/discover"
            self.cmp_put(uri, data=data)
