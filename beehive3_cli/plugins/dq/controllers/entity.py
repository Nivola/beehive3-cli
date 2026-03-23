# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex
from tinydb import TinyDB, Query

from pygments.formatters.terminal256 import Terminal256Formatter
from pygments import format as pyg_format
from pygments.token import Token

from beecell.simple import dict_get

from beehive3_cli.core.controller import BaseController, PARGS
from beehive3_cli.core.util import TreeStyle
from beehive3_cli.translate import _


class DqResourceEntityController(BaseController):
    class Meta:
        stacked_on = "dq_res"
        stacked_type = "nested"
        label = "dq_entities"
        description = _("entities data quality")
        help = _("entities data quality")

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

        db = TinyDB("./bad_resource.json")
        self.table_resource = db.table("resources")
        self.query = Query()

    def __print_tree(self, resource, space="    ", print_header=False):
        """
        Recursively prints a resource tree, formatting the output with Pygments.
        It uses a unified helper to generate tokens for child nodes based on their relation.
        """

        def _get_formatted_child_tokens(child, space="    "):
            """
            Generates Pygments tokens for a single child node in the tree,
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

            yield (Token.Text.Whitespace, space)

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

        # --- Header Logic (specific to the main resource) ---
        if print_header:
            def _create_header_data():
                """Generates tokens for the main resource header line."""
                yield (Token.Name, f" [{resource.get('type')}] ")
                yield (Token.Literal.String, resource.get("name"))
                yield (Token.Text.Whitespace, " - ")
                yield (Token.Literal.Number, str(resource.get("id")))
                yield (Token.Literal.String, f" [{resource.get('state')}]")

            header_data = pyg_format(_create_header_data(), Terminal256Formatter(style=TreeStyle))
            print(header_data)

        # --- Child Nodes Logic ---
        for child_item in resource.get("children", []):
            # Pass the current 'child_item' and 'space' to the helper method
            child_data = pyg_format(
                _get_formatted_child_tokens(child_item, space),
                Terminal256Formatter(style=TreeStyle)
            )
            print(child_data)

            # Recursive call for the children of the current node
            self.__print_tree(child_item, space=space + "    ")

    @ex(
        help=_("check resource entities"),
        description=_("check resource entities"),
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
                    ["-attributes"],
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
    def check(self):
        oid = self.app.pargs.id
        if oid is not None:
            uri = f"{self.baseuri}/entities/{oid}/check"
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
            uri = f"{self.baseuri}/entities"
            res = self.cmp_get(uri, data=data)

            if "page" in res:
                print(f"Page: {res['page']}")
                print(f"Count: {res['count']}")
                print(f"Total: {res['total']}")
                print(f"From: {res['page'] * res['count']} To: {(res['page'] + 1) * res['count']}")
                print(f"Order: {res.get('sort').get('field')} {res.get('sort').get('order')}")

            tmpl = "{idx:6} {id:8} {name:60.60} {container:10} {parent:10} {active:7} {state:10.10}"
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
                uri = f"{self.baseuri}/entities/{item['id']}/check"
                item = self.cmp_get(uri).get("resource")

                if item.get("state") != "ACTIVE":
                    data = self.table_resource.search(self.query.id == item["id"])
                    if len(data) == 0:
                        self.table_resource.insert(item)

                item["idx"] = idx
                self.app.log.warning(item)
                check = item.pop("check")
                lrepr = tmpl.format(**item) + str(check)
                print(lrepr)
                idx += 1

    @ex(
        help=_("get bad resources"),
        description=_("get bad resources"),
        arguments=PARGS(
            [
                (
                    ["-definition"],
                    {
                        "help": _("entity definition"),
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
        help=_("get bad resources"),
        description=_("get bad resources"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("entity id"),
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
        help=_("remove bad resource"),
        description=_("remove bad resource"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("entity id"),
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
        uri = f"{self.baseuri}/entities/{oid}"
        self.cmp_delete(uri, data="")

        data = self.table_resource.search(self.query.id == oid)
        if len(data) > 0:
            self.table_resource.remove(doc_ids=[data[0].doc_id])

    @ex(
        help=_("repair compute volume tree"),
        description=_("repair compute volume tree"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("entity id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-definition"],
                    {
                        "help": _("entity definition"),
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
            uri = f"{self.baseuri}/entities/{oid}/check"
            res = self.cmp_get(uri, data="").get("resource", {})

            print("################################################")
            print(f"# compute volume uuid:       {res['uuid']}")
            print(f"# compute volume name:       {name}")
            print(f"# compute volume hypervisor: {res['hypervisor']}")
            print(f"# compute volume usage:      {res['used']}")
            print(f"# compute volume attachment: {res['attachment']}")
            print(f"# check:                     {res['check']}")

            if res["check"] is True:
                data = self.table_resource.search(self.query.id == oid)
                if len(data) > 0:
                    self.table_resource.remove(doc_ids=[data[0].doc_id])
                continue

            uri = f"/v1.0/nrs/provider/instances/{server_name}"
            instance = self.cmp_get(uri).get("instance", [])

            server_type = instance.get("hypervisor")

            # get tree
            uri = f"{self.baseuri}/entities/{server_name}/tree"
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

            child = None
            # physical server volumes
            for child in main["children"]:
                if dict_get(child, "__meta__.definition") == "Vsphere.DataCenter.Folder.Server":
                    break

            if child is None:
                print("Child is None")
                return

            uri = f"/v1.0/nrs/{server_type}/servers/{child['id']}"
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

            input()

    @ex(
        help=_("repair compute volume tree"),
        description=_("repair compute volume tree"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("entity id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-definition"],
                    {
                        "help": _("entity definition"),
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
            uri = f"{self.baseuri}/entities/{oid}/tree"
            res = self.cmp_get(uri, data="").get("resourcetree", {})
            main = None
            if len(res["children"]) < 1:
                self.app.log.warning("Compute volume %s has not children", oid)
                continue
            for children in res["children"]:
                if dict_get(children, "attributes.main", default=False):
                    main = children

            size = dict_get(item, "attributes.configs.size")

            if main is not None:
                print("################################################")
                print(f"# compute volume id:         {oid}")
                print(f"# compute volume uuid:       {res['uuid']}")
                print(f"# compute volume name:       {name}")
                # print('# compute volume hypervisor: %s' % res['hypervisor'])
                # print('# compute volume usage:      %s' % res['used'])
                # print('# compute volume attachment: %s' % res['attachment'])
                print(f"# zone volume:               {main['id']} - {main['name']}")

                # get container
                relation = children.get("relation")
                if relation is None or len(relation) < 1:
                    continue
                site_id = relation.split(".")[1]
                uri = f"/v1.0/nrs/provider/sites/{site_id}"
                site = self.cmp_get(uri).get("site")
                orchestrators = site.pop("orchestrators")
                container = [o for o in orchestrators if o["type"] == dict_get(children, "attributes.type")][0]["id"]

                uri = f"{self.baseuri}/entities"

                # first search
                data = {
                    "container": container,
                    "name": f"{main['name']}-{container}-volume",
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
                        uri = f"{self.baseuri}/links"
                        data = {"end_resource": p["id"], "type": "relation"}
                        links = self.cmp_get(uri, data=data).get("count", 0)
                        if links > 0:
                            continue

                        print(f"# physical resource:         {p['id']} - {p['name']}")
                        find_vol = p
                        find_num += 1
                if find_num == 0:
                    self.app.error(f"physical volume for {main['name']} in container {container} does not exist")
                    continue
                if find_num > 1:
                    indata = input(f"\nrepair entity {oid}? ")
                    try:
                        indata = int(indata)
                    except:
                        pass
                else:
                    indata = int(find_vol["id"])

                if indata == "s":
                    print("skip")
                    continue
                if isinstance(indata, int):
                    data = {
                        "type": "relation",
                        "name": f"{main['id']}-{indata}-link",
                        "attributes": {},
                        "start_resource": str(main["id"]),
                        "end_resource": str(indata),
                    }
                    uri = f"{self.baseuri}/links"
                    res = self.cmp_post(uri, data={"resourcelink": data})
                    print(f"MSG: create link: {res['uuid']}")

                    data = self.table_resource.search(self.query.id == oid)
                    if len(data) > 0:
                        self.table_resource.remove(doc_ids=[data[0].doc_id])

                # print check
                uri = f"{self.baseuri}/entities/{oid}/check"
                item = self.cmp_get(uri).get("resource")
                check = item.get("check")
                if check.get("check") is True:
                    print("MSG: check is OK")
                else:
                    self.app.error(check.get("msg"))

                # print tree
                uri = f"{self.baseuri}/entities/{oid}/tree"
                res = self.cmp_get(uri, data="").get("resourcetree", {})
                self.__print_tree(res, print_header=True)

                # input()

    @ex(
        help=_("check compute instance"),
        description=_("check compute instance"),
        arguments=PARGS(
            [
                (
                    ["-hypervisor"],
                    {
                        "help": _("hypervisor"),
                        "action": "store",
                        "type": str,
                        "default": "vsphere",
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("name filter"),
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
            uri = f"{self.baseuri}/entities/{oid}/tree"
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

            child = None
            # physical server volumes
            for child in main["children"]:
                if dict_get(child, "__meta__.definition") == "Vsphere.DataCenter.Folder.Server":
                    break

            if child is None:
                print("Child is None")
                return

            uri = f"/v1.0/nrs/{server_type}/servers/{child['id']}"
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
                    uri = f"{self.baseuri}/entities/{oid}"
                    data = {"resource": {}}
                    self.cmp_patch(uri, data=data)
                    print("patch compute instance")
