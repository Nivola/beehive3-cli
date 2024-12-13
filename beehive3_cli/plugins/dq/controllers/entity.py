# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from pygments.formatters.terminal256 import Terminal256Formatter
from pygments import format
from pygments.token import Token
from cement import ex
from tinydb import TinyDB, Query
from beecell.simple import dict_get
from beehive3_cli.core.controller import BaseController, PARGS
from beehive3_cli.core.util import TreeStyle


class DqResourceEntityController(BaseController):
    class Meta:
        stacked_on = "dq_res"
        stacked_type = "nested"
        label = "dq_entities"
        description = "entities data quality"
        help = "entities data quality"

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
        super(DqResourceEntityController, self).pre_command_run()

        self.configure_cmp_api_client()

        db = TinyDB("./bad_resource.json")
        self.table_resource = db.table("resources")
        self.query = Query()

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
        help="check resource entities",
        description="check resource entities",
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
    def check(self):
        oid = self.app.pargs.id
        if oid is not None:
            uri = "%s/entities/%s/check" % (self.baseuri, oid)
            item = self.cmp_get(uri).get("resource")
            check = item.get("check")
            if check.get("check") is False:
                item["state"] = "ERROR"
            self.app.render(item, details=True)
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
            res = self.cmp_get(uri, data=data)

            if "page" in res:
                print("Page: %s" % res["page"])
                print("Count: %s" % res["count"])
                print("Total: %s" % res["total"])
                print("From: %s To: %s" % (res["page"] * res["count"], (res["page"] + 1) * res["count"]))
                print("Order: %s %s" % (res.get("sort").get("field"), res.get("sort").get("order")))

            tmpl = "{idx:6} {id:8} {name:60.60} {container:10} {parent:10} {active:7} {state:10.10}"
            line = "".join(["-" for i in range(40)])
            headers = {
                "idx": "idx",
                "id": "id",
                "name": "name",
                "container": "container",
                "parent": "parent",
                "active": "active",
                "state": "state",
            }
            print(tmpl.format(**headers))

            idx = res["page"] * res["count"] + 1
            for item in res.get("resources", []):
                uri = "%s/entities/%s/check" % (self.baseuri, item["id"])
                item = self.cmp_get(uri).get("resource")

                if item.get("state") != "ACTIVE":
                    data = self.table_resource.search(self.query.id == item["id"])
                    if len(data) == 0:
                        self.table_resource.insert(item)

                item["idx"] = idx
                self.app.log.warning(item)
                check = item.pop("check")
                repr = tmpl.format(**item) + str(check)
                print(repr)
                idx += 1

    @ex(
        help="get bad resources",
        description="get bad resources",
        arguments=PARGS(
            [
                (
                    ["-definition"],
                    {
                        "help": "entity definition",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def bad_get(self):
        definition = self.app.pargs.definition
        if definition is not None:
            items = self.table_resource.search(self.query.__meta__.definition == definition)
        else:
            items = self.table_resource.all()
        headers = [
            "definition",
            "id",
            "name",
            "container",
            "parent",
            "state",
            "check",
            "msg",
        ]
        fields = [
            "__meta__.definition",
            "id",
            "name",
            "container",
            "parent",
            "state",
            "check.check",
            "check.msg",
        ]
        self.app.render(items, headers=headers, fields=fields, showindex="always")

    @ex(
        help="get bad resources",
        description="get bad resources",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "entity id",
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def bad_remove(self):
        oid = self.app.pargs.id
        data = self.table_resource.search(self.query.id == oid)
        if len(data) > 0:
            self.table_resource.remove(doc_ids=[data[0].doc_id])

    @ex(
        help="remove bad resource",
        description="remove bad resource",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "entity id",
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def remove(self):
        oid = self.app.pargs.id
        uri = "%s/entities/%s" % (self.baseuri, oid)
        self.cmp_delete(uri, data="")

        data = self.table_resource.search(self.query.id == oid)
        if len(data) > 0:
            self.table_resource.remove(doc_ids=[data[0].doc_id])

    @ex(
        help="repair compute volume tree",
        description="repair compute volume tree",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "entity id",
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-definition"],
                    {
                        "help": "entity definition",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def compute_volume_check(self):
        oid = self.app.pargs.id
        definition = self.app.pargs.definition

        if oid is not None:
            items = self.table_resource.search(self.query.id == oid)
        elif definition is not None:
            items = self.table_resource.search(self.query.__meta__.definition == definition)
        else:
            items = self.table_resource.all()

        for item in items:
            oid = item["id"]
            name = item["name"]
            server_name = name[: name.find("-volume")]
            uri = "%s/entities/%s/check" % (self.baseuri, oid)
            res = self.cmp_get(uri, data="").get("resource", {})

            print("################################################")
            print("# compute volume uuid:       %s" % res["uuid"])
            print("# compute volume name:       %s" % name)
            print("# compute volume hypervisor: %s" % res["hypervisor"])
            print("# compute volume usage:      %s" % res["used"])
            print("# compute volume attachment: %s" % res["attachment"])
            print("# check:                     %s" % res["check"])

            if res["check"] is True:
                data = self.table_resource.search(self.query.id == oid)
                if len(data) > 0:
                    self.table_resource.remove(doc_ids=[data[0].doc_id])
                continue

            uri = "/v1.0/nrs/provider/instances/%s" % server_name
            instance = self.cmp_get(uri).get("instance", [])

            server_type = instance.get("hypervisor")

            # get tree
            uri = "%s/entities/%s/tree" % (self.baseuri, server_name)
            tree = self.cmp_get(uri, data="").get("resourcetree", {})
            self.c("\ncompute instance tree", "underline")
            self.__print_tree(tree, print_header=True)
            main = None
            for children in tree["children"]:
                if dict_get(children, "attributes.main", default=False):
                    main = children

            # print storage
            storage = instance.pop("block_device_mapping", [])
            self.c("\ncompute instance block device mapping", "underline")
            self.app.render(
                storage,
                headers=[
                    "id",
                    "name",
                    "boot_index",
                    "bootable",
                    "encrypted",
                    "volume_size",
                ],
            )

            # physical server volumes
            for child in main["children"]:
                if dict_get(child, "__meta__.definition") == "Vsphere.DataCenter.Folder.Server":
                    break
            uri = "/v1.0/nrs/%s/servers/%s" % (server_type, child["id"])
            server = self.cmp_get(uri).get("server")
            details = server.pop("details")
            volumes = details.pop("volumes")
            self.c("\nserver volumes", "underline")
            self.app.render(
                volumes,
                headers=[
                    "uuid",
                    "id",
                    "name",
                    "storage",
                    "size",
                    "unit_number",
                    "bootable",
                    "thin",
                    "mode",
                ],
                maxsize=200,
            )

            # if res['used'] is False and res['attachment'] is None:
            #     uri = '%s/entities/%s' % (self.baseuri, oid)
            #     self.cmp_delete(uri, entity='compute volume %s' % oid, confirm=False)

            input()

    @ex(
        help="repair compute volume tree",
        description="repair compute volume tree",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "entity id",
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-definition"],
                    {
                        "help": "entity definition",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def compute_volume_repair(self):
        oid = self.app.pargs.id
        definition = self.app.pargs.definition

        if oid is not None:
            items = self.table_resource.search(self.query.id == oid)
        elif definition is not None:
            items = self.table_resource.search(self.query.__meta__.definition == definition)
        else:
            items = self.table_resource.all()

        for item in items:
            oid = item["id"]
            name = item["name"]
            uri = "%s/entities/%s/tree" % (self.baseuri, oid)
            res = self.cmp_get(uri, data="").get("resourcetree", {})
            main = None
            for children in res["children"]:
                if dict_get(children, "attributes.main", default=False):
                    main = children

            size = dict_get(item, "attributes.configs.size")

            if main is not None:
                print("################################################")
                print("# compute volume id:         %s" % oid)
                print("# compute volume uuid:       %s" % res["uuid"])
                print("# compute volume name:       %s" % name)
                # print('# compute volume hypervisor: %s' % res['hypervisor'])
                # print('# compute volume usage:      %s' % res['used'])
                # print('# compute volume attachment: %s' % res['attachment'])
                print("# zone volume:               %s - %s" % (main["id"], main["name"]))

                # get container
                site_id = children.get("relation").split(".")[1]
                uri = "/v1.0/nrs/provider/sites/%s" % site_id
                site = self.cmp_get(uri).get("site")
                orchestrators = site.pop("orchestrators")
                container = [o for o in orchestrators if o["type"] == dict_get(children, "attributes.type")][0]["id"]

                uri = "%s/entities" % self.baseuri

                # first search
                data = {
                    "container": container,
                    "name": "%s-%s-volume" % (main["name"], container),
                }
                phyres = self.cmp_get(uri, data=data).get("resources", [])

                # second search
                if len(phyres) == 0:
                    pos = main["name"].find("-volume")
                    data = {
                        "container": container,
                        "name": "%" + main["name"][:pos] + "%",
                    }
                    phyres = self.cmp_get(uri, data=data).get("resources", [])

                find_num = 0
                find_vol = None
                for p in phyres:
                    if dict_get(p, "__meta__.definition") != "Openstack.Domain.Project.Volume":
                        vol_size = dict_get(p, "attributes.size")
                    else:
                        vol_size = size

                    if p["name"].find("volume") > 0 and vol_size == size:
                        # check volume is already linked
                        uri = "%s/links" % self.baseuri
                        data = {"end_resource": p["id"], "type": "relation"}
                        links = self.cmp_get(uri, data=data).get("count", 0)
                        if links > 0:
                            continue

                        print("# physical resource:         %s - %s" % (p["id"], p["name"]))
                        find_vol = p
                        find_num += 1
                if find_num == 0:
                    self.app.error("physical volume for %s in container %s does not exist" % (main["name"], container))
                    continue
                elif find_num > 1:
                    indata = input("\nrepair entity %s? " % oid)
                    try:
                        indata = int(indata)
                    except:
                        pass
                else:
                    indata = int(find_vol["id"])

                if indata == "s":
                    print("skip")
                    continue
                elif isinstance(indata, int):
                    data = {
                        "type": "relation",
                        "name": "%s-%s-link" % (main["id"], indata),
                        "attributes": {},
                        "start_resource": str(main["id"]),
                        "end_resource": str(indata),
                    }
                    uri = "%s/links" % self.baseuri
                    res = self.cmp_post(uri, data={"resourcelink": data})
                    print("MSG: create link: %s" % res["uuid"])

                    data = self.table_resource.search(self.query.id == oid)
                    if len(data) > 0:
                        self.table_resource.remove(doc_ids=[data[0].doc_id])

                # print check
                uri = "%s/entities/%s/check" % (self.baseuri, oid)
                item = self.cmp_get(uri).get("resource")
                check = item.get("check")
                if check.get("check") is True:
                    print("MSG: check is OK")
                else:
                    self.app.error(check.get("msg"))

                # print tree
                uri = "%s/entities/%s/tree" % (self.baseuri, oid)
                res = self.cmp_get(uri, data="").get("resourcetree", {})
                self.__print_tree(res, print_header=True)

                # input()

    @ex(
        help="check compute instance",
        description="check compute instance",
        arguments=PARGS(
            [
                (
                    ["-hypervisor"],
                    {
                        "help": "hypervisor",
                        "action": "store",
                        "type": str,
                        "default": "vsphere",
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "name filter",
                        "action": "store",
                        "type": str,
                        "default": "vsphere",
                    },
                ),
            ]
        ),
    )
    def check_compute_instance(self):
        hypervisor = self.app.pargs.hypervisor
        page = self.app.pargs.page
        name = self.app.pargs.name

        uri = "/v1.0/nrs/provider/instances"
        data = {"hypervisor": hypervisor, "page": page, "name": name}
        instances = self.cmp_get(uri, data=data).get("instances", [])

        # compute instance block device mapping
        for instance in instances:
            server_type = instance.get("hypervisor")
            oid = instance.get("id")

            # get tree
            uri = "%s/entities/%s/tree" % (self.baseuri, oid)
            tree = self.cmp_get(uri, data="").get("resourcetree", {})
            self.c("\ncompute instance tree", "underline")
            self.__print_tree(tree, print_header=True)
            main = None
            for children in tree["children"]:
                if dict_get(children, "attributes.main", default=False):
                    main = children

            # print storage
            storage = instance.pop("block_device_mapping", [])
            self.c("\ncompute instance block device mapping", "underline")
            self.app.render(
                storage,
                headers=[
                    "id",
                    "name",
                    "boot_index",
                    "bootable",
                    "encrypted",
                    "volume_size",
                ],
            )

            # physical server volumes
            for child in main["children"]:
                if dict_get(child, "__meta__.definition") == "Vsphere.DataCenter.Folder.Server":
                    break
            uri = "/v1.0/nrs/%s/servers/%s" % (server_type, child["id"])
            server = self.cmp_get(uri).get("server")
            details = server.pop("details")
            volumes = details.pop("volumes")
            self.c("\nserver volumes", "underline")
            self.app.render(
                volumes,
                headers=[
                    "uuid",
                    "name",
                    "storage",
                    "size",
                    "unit_number",
                    "bootable",
                    "thin",
                    "mode",
                ],
                maxsize=200,
            )

            if len(storage) < len(volumes):
                indata = input("next-> ")
                # indata = 'p'

                if indata == "p":
                    uri = "%s/entities/%s" % (self.baseuri, oid)
                    data = {"resource": {}}
                    self.cmp_patch(uri, data=data)
                    print("patch compute instance")

    # @ex(
    #     help='repair vsphere server',
    #     description='repair vsphere server',
    #     arguments=PARGS([
    #         (['-id'], {'help': 'entity id', 'action': 'store', 'type': int, 'default': None}),
    #         (['-definition'], {'help': 'entity definition', 'action': 'store', 'type': str, 'default': None}),
    #     ])
    # )
    # def repair_vsphere_server(self):
    #     oid = self.app.pargs.id
    #     definition = 'Vsphere.DataCenter.Folder.Server'
    #
    #     if oid is not None:
    #         items = self.table_resource.search(self.query.id == oid)
    #     else:
    #         items = self.table_resource.search(self.query.__meta__.definition == definition)
    #
    #     for item in items:
    #         oid = item['id']
    #
    #     print('found %s servers' % len(items))
    #     idx = 1
    #     for item in items:
    #         oid = item['id']
    #         print('#########################################')
    #         print('idx: %s - id: %s - name: %s' % (idx, oid, item['name']))
    #
    #         uri = '/v1.0/nrs/vsphere/servers/%s' % oid
    #         server = self.cmp_get(uri).get('server')
    #         details = server.pop('details')
    #         volumes = details.pop('volumes', [])
    #
    #         check = True
    #         for vol in volumes:
    #             if vol.get('uuid') is None:
    #                 check = False
    #
    #         idx += 1
    #
    #         if check is True:
    #             print(' skip')
    #             continue
    #
    #         self.app.render(volumes, headers=['uuid', 'id', 'name', 'storage', 'size', 'unit_number', 'bootable',
    #                                           'thin', 'mode'], maxsize=50)
    #
    #         try:
    #             uri = '%s/entities/%s' % (self.baseuri, oid)
    #             data = {'resource': {}}
    #             res = self.cmp_patch(uri, data=data)
    #         except Exception as ex:
    #             self.app.error(ex)
    #
    #         uri = '/v1.0/nrs/vsphere/servers/%s' % oid
    #         server = self.cmp_get(uri).get('server')
    #         details = server.pop('details')
    #         volumes = details.pop('volumes', [])
    #         self.app.render(volumes, headers=['uuid', 'id', 'name', 'storage', 'size', 'unit_number', 'bootable',
    #                                           'thin', 'mode'], maxsize=50)
    #
    #         if len(volumes) == len([v for v in volumes if v.get('uuid', None) is not None]):
    #             data = self.table_resource.search(self.query.id == oid)
    #             if len(data) > 0:
    #                 self.table_resource.remove(doc_ids=[data[0].doc_id])
    #
    #         # input()

    # @ex(
    #     help='repair vsphere server',
    #     description='repair vsphere server',
    #     arguments=PARGS([
    #         (['-id'], {'help': 'entity id', 'action': 'store', 'type': int, 'default': None}),
    #         (['-definition'], {'help': 'entity definition', 'action': 'store', 'type': str, 'default': None}),
    #     ])
    # )
    # def repair_volume(self):
    #     oid = self.app.pargs.id
    #     definition = 'Provider.ComputeZone.ComputeVolume'
    #
    #     if oid is not None:
    #         items = self.table_resource.search(self.query.id == oid)
    #     else:
    #         items = self.table_resource.search(self.query.__meta__.definition == definition)
    #
    #     for item in items:
    #         oid = item['id']
    #
    #     print('found %s volume' % len(items))
    #     idx = 1
    #     for item in items:
    #         oid = item['id']
    #         print('#########################################')
    #         print('idx: %s - id: %s - name: %s' % (idx, oid, item['name']))
    #
    #         oid = item['id']
    #         uri = '%s/entities/%s/tree' % (self.baseuri, oid)
    #         res = self.cmp_get(uri, data='').get('resourcetree', {})
    #         main = None
    #         for children in res['children']:
    #             if dict_get(children, 'attributes.main', default=False):
    #                 main = children
    #         if main is not None:
    #             for child in main.get('children', []):
    #                 if dict_get(child, 'type') == 'Vsphere.DataCenter.Folder.Server' or \
    #                         dict_get(child, 'type') == 'Openstack.Domain.Project.Server':
    #                     uri = '%s/links/%s' % (self.baseuri, child['link'])
    #                     self.cmp_delete(uri, confirm=False)
    #                     print('MSG: delete link: %s' % child['link'])
    #
    #                     data = self.table_resource.search(self.query.id == oid)
    #                     if len(data) > 0:
    #                         self.table_resource.remove(doc_ids=[data[0].doc_id])
    #
    #         # print tree
    #         uri = '%s/entities/%s/tree' % (self.baseuri, oid)
    #         res = self.cmp_get(uri, data='').get('resourcetree', {})
    #         self.__print_tree(res, print_header=True)
    #
    #         # input()

    # funzione di rimozione di ruoli associati a account, division e org
