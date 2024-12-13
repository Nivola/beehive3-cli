# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from urllib.parse import urlencode
from pygments import format
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.token import Token
from cement import ex
from ujson import loads
from beecell.simple import set_request_params
from beecell.types.type_string import truncate
from beehive3_cli.core.controller import BaseController, PARGS, ARGS, StringAction
from beehive3_cli.core.util import TreeStyle


class ResourceEntityController(BaseController):
    class Meta:
        stacked_on = "res"
        stacked_type = "nested"
        label = "entities"
        description = "entities management"
        help = "entities management"

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
        super(ResourceEntityController, self).pre_command_run()

        self.configure_cmp_api_client()

    def __print_tree(self, resource, space="   ", print_header=False):
        if print_header is True:

            def create_data():
                yield (Token.Name, " [%s] " % resource.get("type"))
                yield (Token.Literal.String, resource.get("name"))
                yield (Token.Text.Whitespace, " - ")
                yield (Token.Literal.Number, str(resource.get("id")))
                yield (Token.Literal.String, " [%s]" % resource.get("state"))

            data = format(create_data(), Terminal256Formatter(style=TreeStyle))
            print(data)

        for child in resource.get("children", []):
            relation = child.get("relation")
            link = child.get("link")
            if relation is None:

                def create_data():
                    yield (Token.Text.Whitespace, space)
                    yield (Token.Operator, "=>")
                    yield (Token.Name, " [%s] " % child.get("type"))
                    yield (Token.Literal.String, child.get("name"))
                    yield (Token.Text.Whitespace, " - ")
                    yield (
                        Token.Literal.String,
                        "%s {%s}" % (child.get("id"), child.get("ext_id")),
                    )
                    yield (Token.Literal.String, " [%s]" % child.get("state"))
                    yield (Token.Literal.String, " (%s)" % child.get("reuse"))

                data = format(create_data(), Terminal256Formatter(style=TreeStyle))
            else:

                def create_data():
                    yield (Token.Text.Whitespace, space)
                    yield (Token.Operator, "--%s:%s-->" % (link, relation))
                    yield (Token.Operator, " (%s) " % child.get("container_name"))
                    yield (Token.Name, "[%s] " % child.get("type"))
                    yield (Token.Literal.String, child.get("name"))
                    yield (Token.Text.Whitespace, " - ")
                    yield (
                        Token.Literal.String,
                        "%s {%s}" % (child.get("id"), child.get("ext_id")),
                    )
                    yield (Token.Literal.String, " [%s]" % child.get("state"))
                    yield (Token.Literal.String, " (%s)" % child.get("reuse"))

                data = format(create_data(), Terminal256Formatter(style=TreeStyle))
            print(data)
            self.__print_tree(child, space=space + "   ")

    @ex(
        help="get the last resource error from a job",
        description="get the last resource error from a job",
        arguments=[
            (
                ["entity"],
                {"help": "resource entity is or name", "action": "store", "type": str},
            )
        ],
    )
    def errors(self):
        oid = self.app.pargs.entity
        uri = "%s/%s/%s/errors" % (self.baseuri, self._meta.label, oid)
        resp = self.cmp_get(uri).get("resource_errors")[0]
        self.app.render({"error": resp}, headers=["error"], maxsize=200)

    @ex(
        help="get resource entity tree",
        description="get resource entity tree",
        example="beehive res entities tree $SERVER -e <env>;beehive res entities tree <uuid> -e <env>",
        arguments=ARGS(
            [
                (
                    ["entity"],
                    {
                        "help": "resource entity is or name",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": "if True show tree by parent - child",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-link"],
                    {
                        "help": "if True show tree by link relation",
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
        uri = "%s/entities/%s/tree" % (self.baseuri, oid)
        res = self.cmp_get(uri, data=data).get("resourcetree", {})
        self.__print_tree(res, print_header=True)

    @ex(
        help="list resource entities",
        description="list resource entities",
        example="beehive res entities get -id <uuid> -e <env>;beehive res entities get -id 715 -e <env>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "entity id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "entity name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "entity description",
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
                        "help": "entity type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": "entity authorization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext_id"],
                    {
                        "help": "entity physical id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": "entity parent",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": "entity state",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attributes"],
                    {
                        "help": "entity attributes",
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
            ]
        ),
    )
    def get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = "%s/entities/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("resource")
                attributes = res.pop("attributes", {})
                # container = res.pop('container', {})

                # uri = '%s/containers/%s' % (self.baseuri, res.pop('container'))
                # container = self.cmp_get(uri).get('resourcecontainer', {})
                # container = {
                #     'id': container['id'],
                #     'uuid': container['uuid'],
                #     'name': container['name'],
                #     'desc': container['desc'],
                # }
                #
                self.app.render(res, details=True)
                # self.c('\ncontainer', 'underline')
                # self.app.render(container, details=True)
                self.c("\nattributes", "underline")
                self.app.render(attributes, details=True)

                uri = "%s/entities/%s/tree" % (self.baseuri, oid)
                tree = self.cmp_get(uri).get("resourcetree", {})
                self.c("\ntree", "underline")
                self.__print_tree(tree, print_header=True)

                uri = "%s/links" % self.baseuri
                links = self.cmp_get(uri, data={"resource": oid})
                self.c("\nlinks", "underline")
                self.app.render(
                    links.get("resourcelinks"),
                    headers=self._meta.link_headers,
                    fields=self._meta.link_fields,
                )

                uri = "%s/entities/%s/linked" % (self.baseuri, oid)
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
                    # 'name': lambda n: n.split('.')[-1],
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
            ]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = "%s/entities" % self.baseuri

            # uri = '%s/containers' % self.baseuri
            # containers = self.cmp_get(uri).get('resourcecontainers', [])
            # c_idx = {str(c['id']): c['name'] for c in containers}

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
        help="list resource entity types",
        description="list resource entity types",
        example="beehive res entities types -e <env>",
        arguments=ARGS(
            [
                (
                    ["-type"],
                    {
                        "help": "entity type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-subsystem"],
                    {
                        "help": "entity type subsystem",
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
        uri = "%s/entities/types" % self.baseuri
        res = self.cmp_get(uri, data=data)
        self.app.render(res, key="resourcetypes", headers=["id", "type", "resclass"], maxsize=400)

    @ex(
        help="add resource entity",
        description="add resource entity",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": "resource entity name", "action": "store", "type": str},
                ),
                (
                    ["-desc"],
                    {
                        "help": "resource entity description",
                        "action": "store",
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["container"],
                    {"help": "resource container uuid", "action": "store", "type": str},
                ),
                (
                    ["resclass"],
                    {"help": "resource entity class", "action": "store", "type": str},
                ),
                (
                    ["-ext_id"],
                    {
                        "help": "resource entity physical id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": "resource entity parent uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attribute"],
                    {
                        "help": "resource entity attributes",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-tags"],
                    {
                        "help": "resource entity tags",
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
        uri = "%s/entities" % self.baseuri
        res = self.cmp_post(uri, data={"resource": data})
        self.app.render({"msg": "add entity %s" % res["uuid"]})

    @ex(
        help="update resource entity",
        description="update resource entity",
        example="beehive res entities update 2760833 -ext_id=" ";beehive res entities update 2760833 ",
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
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                        "default": None,
                    },
                ),
                (
                    ["-active"],
                    {
                        "help": "resource entity active",
                        "action": "store",
                        "type": bool,
                        "default": True,
                    },
                ),
                (
                    ["-force"],
                    {
                        "help": "if True force resource metadata update and bypass type specific update",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ext_id"],
                    {
                        "help": "resource physical id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attribute"],
                    {
                        "help": "resource entity attributes",
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
        uri = "%s/entities/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data={"resource": data})
        self.app.render({"msg": "update resource entity %s" % oid})

    @ex(
        help="check resource entity",
        description="check resource entity",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def check(self):
        oid = self.app.pargs.id
        uri = "%s/entities/%s/check" % (self.baseuri, oid)
        res = self.cmp_get(uri).get("resource")
        self.app.render({"state": res["state"]}, details=True)
        print("Messages:")
        self.app.render(res["check"]["msg"], details=True)

    # @ex(
    #     help='checks resource entities',
    #     description='checks resource entities',
    #     arguments=PARGS([
    #         (['-id'], {'help': 'entity id', 'action': 'store', 'type': str, 'default': None}),
    #         (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
    #         (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
    #         (['-container'], {'help': 'container uuid or name', 'action': 'store', 'type': str, 'default': None}),
    #         (['-type'], {'help': 'entity type', 'action': 'store', 'type': str, 'default': None}),
    #         (['-objid'], {'help': 'entity authorization id', 'action': 'store', 'type': str, 'default': None}),
    #         (['-ext_id'], {'help': 'entity physical id', 'action': 'store', 'type': str, 'default': None}),
    #         (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
    #         (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
    #         (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
    #         (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
    #     ])
    # )
    # def checks(self):
    #     oid = getattr(self.app.pargs, 'id', None)
    #     if oid is not None:
    #         uri = '%s/entities/%s' % (self.baseuri, oid)
    #         res = self.cmp_get(uri)
    #
    #         if self.is_output_text():
    #             uri = '%s/entities/%s/check' % (self.baseuri, oid)
    #             res = self.cmp_get(uri).get('resource')
    #             self.app.render({'state': res['state']}, details=True)
    #             print('Messages:')
    #             self.app.render(res['check']['msg'], details=True)
    #         else:
    #             self.app.render(res, key='resource', details=True)
    #     else:
    #         params = ['container', 'type', 'name', 'desc', 'objid', 'ext_id', 'parent', 'state', 'tags']
    #         mappings = {'name': lambda n: '%' + n + '%'}
    #         data = self.format_paginated_query(params, mappings=mappings)
    #         uri = '%s/entities' % self.baseuri
    #         res = self.cmp_get(uri, data=data)
    #
    #         # uri = '%s/containers' % self.baseuri
    #         # containers = self.cmp_get(uri).get('resourcecontainers', [])
    #         # c_idx = {str(c['id']): c['name'] for c in containers}
    #
    #         for item in res.get('resources'):
    #             if item['state'] in ['ACTIVE']:
    #                 uri = '%s/entities/%s/check' % (self.baseuri, item['id'])
    #                 check = self.cmp_get(uri).get('resource')
    #                 item['base_state'] = check['state']
    #                 # self.app.render(check['check']['msg'], details=True)
    #
    #         transform = {'state': self.color_error}
    #         self.app.render(res, key='resources', headers=self._meta.headers, fields=self._meta.fields,
    #                         transform=transform, maxsize=50)

    @ex(
        help="patch resource entities",
        description="patch resource entities",
        example="beehive res entities patch -id 772411 -e <env>",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": "comma separated resource entity ids",
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
            uri = "%s/entities/%s" % (self.baseuri, oid)
            self.cmp_patch(uri, data=data)
            self.app.render({"msg": "patch resource entity %s" % oid})
            #
            # uri = '%s/entities/%s/check' % (self.baseuri, oid)
            # res = self.cmp_get(uri).get('resource')
            # self.app.render({'state': res['state']}, details=True)
            # print('Messages:')
            # self.app.render(res['check']['msg'], details=True)
            # print('#####################################\n')

    @ex(
        help="delete resource entities",
        description="delete resource entities",
        example="beehive res entities delete <uuid> -e <env> -y;beehive res entities delete 1509508",
        arguments=ARGS(
            [
                (
                    ["ids"],
                    {
                        "help": "comma separated resource entity ids",
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
                        "default": "true",
                    },
                ),
                (
                    ["-deep"],
                    {
                        "help": "if false delete only resource record and permissions",
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
            uri = "%s/entities/%s?" % (self.baseuri, oid)
            uri += "force=%s&deep=%s" % (force, deep)
            self.cmp_delete(uri, entity="entity %s" % oid)

    @ex(
        help="get resource entity cache",
        description="get resource entity cache",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def cache_get(self):
        oid = self.app.pargs.id
        uri = "%s/entities/%s/cache" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, headers=["key", "value"], maxsize=100)

    @ex(
        help="delete resource entity cache",
        description="delete resource entity cache",
        example="beehive res entities cache-del <uuid> -e <env>;beehive res entities cache-del 2763044 -e <env>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def cache_del(self):
        oid = self.app.pargs.id
        uri = "%s/entities/%s/cache" % (self.baseuri, oid)
        res = self.cmp_put(uri)
        self.app.render({"msg": "delete resource %s cache" % oid})

    @ex(
        help="get resource entity config",
        description="get resource entity config",
        example="beehive res entities config-get 809282;beehive res entities config-get 809291",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def config_get(self):
        oid = self.app.pargs.id
        uri = "%s/entities/%s/config" % (self.baseuri, oid)
        res = self.cmp_get(uri).get("config")
        self.app.render(res, details=True)

    @ex(
        help="update resource entity config",
        description="update resource entity config",
        example="beehive res entities config-set -value 100 809282 configs.size;beehive res entities config-set -value 310 2246492 configs.size",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
                (
                    ["config_key"],
                    {
                        "help": "config key like config.key",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-value"],
                    {
                        "help": "config value",
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
        uri = "%s/entities/%s/config" % (self.baseuri, oid)
        self.cmp_put(uri, data={"config": {"key": key, "value": value}})
        self.app.render({"msg": "update resource entity %s config" % oid})

    @ex(
        help="enable resource quotas and metrics discover",
        description="enable resource quotas and metric discover",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def enable_quotas(self):
        oid = self.app.pargs.id
        uri = "%s/entities/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data={"resource": {"enable_quotas": True}})
        self.app.render({"msg": "enable resource %s quotas and metrics discover" % oid})

    @ex(
        help="disable resource quotas and metrics discover",
        description="disable resource quotas and metric discover",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def disable_quotas(self):
        oid = self.app.pargs.id
        uri = "%s/entities/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data={"resource": {"disable_quotas": True}})
        self.app.render({"msg": "disable resource %s quotas and metrics discover" % oid})

    @ex(
        help="get linked resource entities",
        description="get linked resource entities",
        example="beehive res entities linked get -id <uuid> -e <env>;beehive res entities linked <uuid> -e <env>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def linked(self):
        oid = self.app.pargs.id
        uri = "%s/entities/%s/linked" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key="resources", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help="get resource entity metrics",
        description="get resource entity metrics",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def metrics(self):
        oid = self.app.pargs.id
        uri = "%s/entities/%s/metrics" % (self.baseuri, oid)
        res = self.cmp_get(uri).get("resource")
        metrics = res.pop("metrics")
        self.app.render(res, details=True)
        self.c("\nmetrics", "underline")
        self.app.render(metrics, headers=["key", "type", "unit", "value"])

    @ex(
        help="reset resource state",
        description="reset resource state",
        example="beehive res entities state <uuid> -state active",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
                (
                    ["-state"],
                    {
                        "help": "resource state",
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
        uri = "%s/entities/%s/state" % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        res = {"msg": "set resource %s state to %s" % (oid, state)}
        self.app.render(res)

    @ex(
        help="add tag to resource",
        description="add tag to resource",
        example="beehive res entities tag-add 2763074 nws\$volume_bck;beehive res entities tag-add 2763047 nws\$volume_bck",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
                (
                    ["tag"],
                    {
                        "help": "tag name",
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
        uri = "%s/entities/%s" % (self.baseuri, oid)
        res = self.cmp_put(uri, data=data)
        res = {"msg": "add tag %s to resource %s " % (tag, oid)}
        self.app.render(res)

    @ex(
        help="remove tag from resource",
        description="remove tag from resource",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "resource entity id", "action": "store", "type": str},
                ),
                (
                    ["tag"],
                    {
                        "help": "tag name",
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
        uri = "%s/entities/%s" % (self.baseuri, oid)
        res = self.cmp_put(uri, data=data)
        res = {"msg": "remove tag %s from resource %s " % (tag, oid)}
        self.app.render(res)

    @ex(
        help="get tags of resource",
        description="get tags of resource",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "resource id",
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
        uri = "%s/tags" % self.baseuri
        res = self.cmp_get(uri, data=data)

        fields = ["id", "name"]
        headers = ["id", "name"]
        self.app.render(res, key="resourcetags", headers=headers, fields=fields, maxsize=45)
