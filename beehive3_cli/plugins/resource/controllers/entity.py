# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

import os
from urllib.parse import urlencode

from pygments import format as pyg_format
from pygments.formatters import NullFormatter
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.token import Token

from cement import ex
from ujson import loads

from beecell.simple import set_request_params
from beecell.types.type_string import truncate

from beehive3_cli.core.controller import BaseController, PARGS, ARGS, StringAction
from beehive3_cli.core.util import TreeStyle
from beehive3_cli.translate import _


class ResourceEntityController(BaseController):
    class Meta:
        stacked_on = "res"
        stacked_type = "nested"
        label = "entities"
        description = _("entities management")
        help = _("entities management")

        cmp = {"baseuri": "/v1.0/nrs", "subsystem": "resource"}

        headers = [
            "id",
            "uuid",
            "objdef",
            "name",
            "container",
            "parent",
            "active",
            "state",
            "date",
            "ext_id",
        ]
        fields = [
            "id",
            "uuid",
            "__meta__.definition",
            "name",
            "container",
            "parent",
            "active",
            "base_state",
            "date.creation",
            "ext_id",
        ]
        link_fields = [
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
        link_headers = [
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
        task_headers = [
            "uuid",
            "name",
            "parent",
            "api_id",
            "status",
            "start_time",
            "stop_time",
            "duration",
        ]
        task_fields = [
            "uuid",
            "alias",
            "parent",
            "api_id",
            "status",
            "start_time",
            "stop_time",
            "duration",
        ]

    def pre_command_run(self):
        super().pre_command_run()
        self.configure_cmp_api_client()

    def __print_tree(self, resource, space="    ", print_header=False):
        """
        Recursively prints a resource tree, formatting the output with Pygments.
        Passes the 'child' node and 'space' to the helper method for clarity and consistency.
        """

        def _get_formatted_child_tokens(child, space="    "):
            """
            Generates tokens for a single child node in the tree,
            extracting data from the 'child' itself and handling the relation logic.
            """
            # Extract necessary data from the child node
            child_type = child.get("type")
            child_name = child.get("name")
            child_id = child.get("id")
            child_ext_id = child.get("ext_id")
            child_state = child.get("state")
            child_reuse = child.get("reuse")
            relation = child.get("relation")
            link = child.get("link")
            container_name = child.get("container_name")

            yield (Token.Text.Whitespace, space) # Use 'space' as passed


            if relation is None:
                # Case: direct relation (=>)
                yield (Token.Operator, "=>")
            else:
                # Case: linked relation (--link:relation-->)
                yield (Token.Operator, f"--{link}:{relation}-->")
                # Add container_name only if a linked relation exists and a name is present
                if container_name:
                    yield (Token.Operator, f" ({container_name}) ")

            yield (Token.Name, f" [{child_type}] ")
            yield (Token.Literal.String, child_name)
            yield (Token.Text.Whitespace, " - ")
            yield (Token.Literal.String, f"{child_id} {{{child_ext_id}}}")
            yield (Token.Literal.String, f" [{child_state}]")
            yield (Token.Literal.String, f" ({child_reuse})")

        # --- Header Logic (remains as before, it's specific) ---
        if print_header:
            def _create_header_data():
                """Generates tokens for the main resource header line."""
                yield (Token.Name, f" [{resource.get('type')}] ")
                yield (Token.Literal.String, resource.get("name"))
                yield (Token.Text.Whitespace, " - ")
                yield (Token.Literal.Number, str(resource.get("id")))
                yield (Token.Literal.String, f" [{resource.get('state')}]")

            if not os.isatty(1):
                # disable style
                header_data = pyg_format(_create_header_data(), NullFormatter())
            else:
                header_data = pyg_format(_create_header_data(), Terminal256Formatter(style=TreeStyle))
            print(header_data)

        # --- Child Nodes Logic ---
        for child_item in resource.get("children", []):
            # Pass the current 'child_item' and 'space' to the helper method
            if not os.isatty(1):
                # disable style
                child_data = pyg_format(
                    _get_formatted_child_tokens(child_item, space),
                    NullFormatter()
                )
            else:
                child_data = pyg_format(
                    _get_formatted_child_tokens(child_item, space),
                    Terminal256Formatter(style=TreeStyle)
                )
            print(child_data)

            # Recursive call for the children of the current node
            self.__print_tree(child_item, space=space + "    ")


    @ex(
        help=_("get the last resource error from a job"),
        description=_("get the last resource error from a job"),
        arguments=[
            (
                ["entity"],
                {"help": _("resource entity is or name"), "action": "store", "type": str},
            )
        ],
    )
    def errors(self):
        oid = self.app.pargs.entity
        uri = f"{self.baseuri}/{self._meta.label}/{oid}/errors"
        resp = self.cmp_get(uri).get("resource_errors")[0]
        self.app.render({"error": resp}, headers=["error"], maxsize=200)

    @ex(
        help=_("get resource entity tree"),
        description=_("get resource entity tree"),
        example="beehive res entities tree $SERVER -e <env>; beehive res entities tree <uuid> -e <env>",
        arguments=ARGS(
            [
                (
                    ["entity"],
                    {
                        "help": _("resource entity is or name"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("if True show tree by parent - child"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-link"],
                    {
                        "help": _("if True show tree by link relation"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def tree(self):
        oid = self.app.pargs.entity
        params = ["parent", "link"]
        data = self.format_paginated_query(params)
        uri = f"{self.baseuri}/entities/{oid}/tree"
        res = self.cmp_get(uri, data=data).get("resourcetree", {})
        self.__print_tree(res, print_header=True)

    @ex(
        help=_("list resource entities"),
        description=_("list resource entities"),
        example="beehive res entities get -id <uuid> -e <env>; beehive res entities get -id 715 -e <env>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("entity id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-container"],
                    {
                        "help": _("container uuid or name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("entity type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": _("entity authorization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext_id"],
                    {
                        "help": _("entity physical id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attribute"],
                    {
                        "help": _("entity attributes"),
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
            ]
        ),
    )
    def get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/entities/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("resource")
                attributes = res.pop("attributes", {})
                self.app.render(res, details=True)
                self.c("\nattributes", "underline")
                self.app.render(attributes, details=True)

                uri = f"{self.baseuri}/entities/{oid}/tree"
                tree = self.cmp_get(uri).get("resourcetree", {})
                self.c("\ntree", "underline")
                self.__print_tree(tree, print_header=True)

                uri = f"{self.baseuri}/links"
                links = self.cmp_get(uri, data={"resource": oid})
                self.c("\nlinks", "underline")
                transform = {"details.attributes.colortext": False}
                self.app.render(
                    links.get("resourcelinks"),
                    headers=self._meta.link_headers,
                    fields=self._meta.link_fields,
                    transform=transform,
                )

                uri = f"{self.baseuri}/entities/{oid}/linked"
                linked = self.cmp_get(uri)
                self.c("\nlinked entities", "underline")
                self.app.render(
                    linked.get("resources"),
                    headers=self._meta.headers,
                    fields=self._meta.fields,
                )

                data = urlencode({"objid": res["__meta__"]["objid"], "size": -1})
                uri = "/v2.0/nrs/worker/tasks"
                res = self.cmp_get(uri, data=data).get("task_instances")
                transform = {
                    "parent": lambda n: truncate(n, 20),
                    "status": self.color_error,
                }
                self.c("\ntasks [last 10]", "underline")
                self.app.render(
                    res,
                    headers=self._meta.task_headers,
                    fields=self._meta.task_fields,
                    maxsize=80,
                    transform=transform,
                )
            else:
                self.app.render(res, key="resource", details=True)
        else:
            params = [
                "container",
                "type",
                "name",
                "desc",
                "objid",
                "ext_id",
                "parent",
                "state",
                "tags",
                "attribute",
            ]
            mappings = {"name": lambda n: "%" + n + "%", "attribute": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/entities"


            def render(self, res, **kwargs):
                transform = {"base_state": self.color_error}
                self.app.render(
                    res,
                    key="resources",
                    headers=self._meta.headers,
                    fields=self._meta.fields,
                    transform=transform,
                    maxsize=50,
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render, pagesize=20)

    @ex(
        help=_("list simple resource entities"),
        description=_("list simple resource entities"),
        example="beehive res entities simple-get -id <uuid> -e <env>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("entity id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-uuids"],
                    {
                        "help": _("comma separated list of uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("entity name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("entity description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-container"],
                    {
                        "help": _("container uuid or name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("entity type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": _("entity authorization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext_id"],
                    {
                        "help": _("entity physical id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("entity parent"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("entity state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attribute"],
                    {
                        "help": _("entity attributes"),
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
            ]
        ),
    )
    def simple_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/simple_entities/{oid}"
            res = self.cmp_get(uri)
            self.app.render(res, key="resource", details=True)
        else:
            params = [
                "container",
                "type",
                "name",
                "desc",
                "objid",
                "ext_id",
                "parent",
                "state",
                "tags",
                "attribute",
                "uuids",
            ]
            mappings = {"name": lambda n: "%" + n + "%", "attribute": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/simple_entities"

            def render(self, res, **kwargs):
                transform = {"base_state": self.color_error}
                self.app.render(
                    res,
                    key="resources",
                    headers=self._meta.headers,
                    fields=self._meta.fields,
                    transform=transform,
                    maxsize=50,
                )

            res = self.cmp_get_pages(uri, data=data, fn_render=render, pagesize=20)

    @ex(
        help=_("list resource entity types"),
        description=_("list resource entity types"),
        example="beehive res entities types -e <env>",
        arguments=ARGS(
            [
                (
                    ["-type"],
                    {
                        "help": _("entity type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subsystem"],
                    {
                        "help": _("entity type subsystem"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def types(self):
        params = ["type", "subsystem"]
        mappings = {}
        data = self.format_paginated_query(params, mappings=mappings)
        uri = f"{self.baseuri}/entities/types"
        res = self.cmp_get(uri, data=data)
        self.app.render(res, key="resourcetypes", headers=["id", "type", "resclass"], maxsize=400)

    @ex(
        help=_("add resource entity"),
        description=_("add resource entity"),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("resource entity name"), "action": "store", "type": str},
                ),
                (
                    ["-desc"],
                    {
                        "help": _("resource entity description"),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["container"],
                    {"help": _("resource container uuid"), "action": "store", "type": str},
                ),
                (
                    ["resclass"],
                    {"help": _("resource entity class"), "action": "store", "type": str},
                ),
                (
                    ["-ext_id"],
                    {
                        "help": _("resource entity physical id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("resource entity parent uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attribute"],
                    {
                        "help": _("resource entity attributes"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": _("resource entity tags"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add(self):
        container = self.app.pargs.container
        resclass = self.app.pargs.resclass
        name = self.app.pargs.name
        data = {
            "container": container,
            "resclass": resclass,
            "name": name,
        }
        data.update(set_request_params(self.app.pargs, ["desc", "ext_id", "parent", "attribute", "tags"]))
        uri = f"{self.baseuri}/entities"
        res = self.cmp_post(uri, data={"resource": data})
        self.app.render({"msg": f"add entity {res['uuid']}"})

    @ex(
        help=_("update resource entity"),
        description=_("update resource entity"),
        example="beehive res entities update 2760833",
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
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-active"],
                    {
                        "help": _("resource entity active"),
                        "action": "store",
                        "type": bool,
                        "default": True,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": _("if True force resource metadata update and bypass type specific update"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext_id"],
                    {
                        "help": _("resource physical id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attribute"],
                    {
                        "help": _("resource entity attributes. NB: overwrites the whole attribute object"),
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
        attribute = self.app.pargs.attribute
        data = set_request_params(self.app.pargs, ["force", "name", "desc", "ext_id", "active"])
        if attribute is not None:
            attribute = loads(attribute)
            data.update({"attribute": attribute})
        uri = f"{self.baseuri}/entities/{oid}"
        self.cmp_put(uri, data={"resource": data})
        self.app.render({"msg": f"update resource entity {oid}"})

    @ex(
        help=_("check resource entity"),
        description=_("check resource entity"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def check(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/entities/{oid}/check"
        res = self.cmp_get(uri).get("resource")
        self.app.render({"state": res["state"]}, details=True)
        self.app.render({"messages": res.get("check",{}).get("msg")}, details=True)

    @ex(
        help=_("patch resource entities"),
        description=_("patch resource entities"),
        example="beehive res entities patch -id 772411 -e <env>",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": _("comma separated resource entity ids"),
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
            data = {"resource": params}
            uri = f"{self.baseuri}/entities/{oid}"
            self.cmp_patch(uri, data=data)
            self.app.render({"msg": f"patch resource entity {oid}"})
            #
            # uri = '%s/entities/%s/check' % (self.baseuri, oid)
            # res = self.cmp_get(uri).get('resource')
            # self.app.render({'state': res['state']}, details=True)
            # print('Messages:')
            # self.app.render(res['check']['msg'], details=True)
            # print('#####################################\n')

    @ex(
        help=_("delete resource entities"),
        description=_("delete resource entities"),
        example="beehive res entities delete <uuid> -e <env> -y; beehive res entities delete 1509508",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": _("comma separated resource entity ids"),
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
                        "default": "true",
                    },
                ),
                (
                    ["-deep"],
                    {
                        "help": _("if false delete only resource record and permissions"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oids = self.app.pargs.ids.split(",")
        force = self.app.pargs.force
        deep = self.app.pargs.deep
        for oid in oids:
            uri = f"{self.baseuri}/entities/{oid}?"
            uri += f"force={force}&deep={deep}"
            self.cmp_delete(uri, entity=f"entity {oid}")

    @ex(
        help=_("get resource entity cache"),
        description=_("get resource entity cache"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def cache_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/entities/{oid}/cache"
        res = self.cmp_get(uri)
        self.app.render(res, headers=["key", "value"], maxsize=100)

    @ex(
        help=_("delete resource entity cache"),
        description=_("delete resource entity cache"),
        example="beehive res entities cache-del <uuid> -e <env>; beehive res entities cache-del 2763044 -e <env>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def cache_del(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/entities/{oid}/cache"
        self.cmp_put(uri)
        self.app.render({"msg": f"delete resource {oid} cache"})

    @ex(
        help=_("get resource entity config"),
        description=_("get resource entity config"),
        example="beehive res entities config-get 809282; beehive res entities config-get 809291",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def config_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/entities/{oid}/config"
        res = self.cmp_get(uri).get("config")
        self.app.render(res, details=True)

    @ex(
        help=_("update resource entity config"),
        description=_("update resource entity config"),
        example=(
            "beehive res entities config-set -value 100 809282 configs.size; "
            "beehive res entities config-set -value 310 2246492 configs.size"
        ),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
                (
                    ["config_key"],
                    {
                        "help": _("config key like config.key"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-value"],
                    {
                        "help": _("config value"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def config_set(self):
        oid = self.app.pargs.id
        key = self.app.pargs.config_key
        value = self.app.pargs.value
        uri = f"{self.baseuri}/entities/{oid}/config"
        self.cmp_put(uri, data={"config": {"key": key, "value": value}})
        self.app.render({"msg": f"update resource entity {oid} config"})

    @ex(
        help=_("enable resource quotas and metrics discover"),
        description=_("enable resource quotas and metric discover"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def enable_quotas(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/entities/{oid}"
        self.cmp_put(uri, data={"resource": {"enable_quotas": True}})
        self.app.render({"msg": f"enable resource {oid} quotas and metrics discover"})

    @ex(
        help=_("disable resource quotas and metrics discover"),
        description=_("disable resource quotas and metric discover"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def disable_quotas(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/entities/{oid}"
        self.cmp_put(uri, data={"resource": {"disable_quotas": True}})
        self.app.render({"msg": f"disable resource {oid} quotas and metrics discover"})

    @ex(
        help=_("get linked resource entities"),
        description=_("get linked resource entities"),
        example="beehive res entities linked <uuid> -e <env>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
                (
                    ["-type"],
                    {
                        "help": _("entity type"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def linked(self):
        oid = self.app.pargs.id
        params = [
            "type",
        ]
        mappings = {"name": lambda n: "%" + n + "%"}
        data = self.format_paginated_query(params, mappings=mappings)
        uri = f"{self.baseuri}/entities/{oid}/linked"
        res = self.cmp_get(uri, data=data)
        self.app.render(res, key="resources", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("get resource entity metrics"),
        description=_("get resource entity metrics"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def metrics(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/entities/{oid}/metrics"
        res = self.cmp_get(uri).get("resource")
        metrics = res.pop("metrics")
        self.app.render(res, details=True)
        self.c("\nmetrics", "underline")
        self.app.render(metrics, headers=["key", "type", "unit", "value"])

    @ex(
        help=_("reset resource state"),
        description=_("reset resource state"),
        example="beehive res entities state <uuid> -state active",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
                (
                    ["-state"],
                    {
                        "help": _("resource state"),
                        "action": "store",
                        "type": str,
                        "default": "active",
                    },
                ),
            ]
        ),
    )
    def state(self):
        oid = self.app.pargs.id
        state = self.app.pargs.state.upper()
        data = {"state": state}
        uri = f"{self.baseuri}/entities/{oid}/state"
        self.cmp_put(uri, data=data)
        res = {"msg": f"set resource {oid} state to {state}"}
        self.app.render(res)

    @ex(
        help=_("add tag to resource"),
        description=_("add tag to resource"),
        example="beehive res entities tag-add 2763074 nws$volume_bck",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
                (
                    ["tag"],
                    {
                        "help": _("tag name"),
                        "action": "store",
                        "type": str,
                        "default": "active",
                    },
                ),
            ]
        ),
    )
    def tag_add(self):
        oid = self.app.pargs.id
        tag = self.app.pargs.tag
        data = {"resource": {"tags": {"cmd": "add", "values": [tag]}}}
        uri = f"{self.baseuri}/entities/{oid}"
        res = self.cmp_put(uri, data=data)
        res = {"msg": f"add tag {tag} to resource {oid} "}
        self.app.render(res)

    @ex(
        help=_("remove tag from resource"),
        description=_("remove tag from resource"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
                (
                    ["tag"],
                    {
                        "help": _("tag name"),
                        "action": "store",
                        "type": str,
                        "default": "active",
                    },
                ),
            ]
        ),
    )
    def tag_del(self):
        oid = self.app.pargs.id
        tag = self.app.pargs.tag
        data = {"resource": {"tags": {"cmd": "remove", "values": [tag]}}}
        uri = f"{self.baseuri}/entities/{oid}"
        res = self.cmp_put(uri, data=data)
        res = {"msg": f"remove tag {tag} from resource {oid} "}
        self.app.render(res)

    @ex(
        help=_("get tags of resource"),
        description=_("get tags of resource"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("resource id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def tag_get(self):
        oid = getattr(self.app.pargs, "id", None)
        data = {"resource": oid}
        uri = f"{self.baseuri}/tags"
        res = self.cmp_get(uri, data=data)

        fields = ["id", "name"]
        headers = ["id", "name"]
        self.app.render(res, key="resourcetags", headers=headers, fields=fields, maxsize=45)

    @ex(
        help=_("register resource entity"),
        description=_("register resource entity"),
        example="beehive res entities register <id>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("resource entity id"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def register(self):
        oid = self.app.pargs.id
        uri = f"/v2.0/nrs/entities/{oid}/register"
        self.cmp_put(uri)
