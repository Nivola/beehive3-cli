# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive3_cli.core.controller import BaseController, PARGS
from cement import ex
from tinydb import TinyDB, Query


class DqResourceLinkController(BaseController):
    class Meta:
        stacked_on = "dq_res"
        stacked_type = "nested"
        label = "dq_links"
        description = "links data quality"
        help = "links data quality"

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
        super(DqResourceLinkController, self).pre_command_run()

        self.configure_cmp_api_client()

        db = TinyDB("./bad_resource.json")
        self.table_resource = db.table("resources")
        self.query = Query()

    @ex(
        help="repair resource links",
        description="repair resource links",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "link id",
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def check(self):
        # size = self.app.pargs.size
        # page = self.app.pargs.page
        uri = "%s/links" % self.baseuri
        res = self.cmp_get(uri, data={"size": 1})
        total = res["total"]
        print("found %s links" % total)

        page_size = 500
        page_num = round(total / page_size)
        print(total, page_num)
        for page in range(0, page_num):
            uri = "%s/links" % self.baseuri
            res = self.cmp_get(uri, data={"size": page_size, "page": page})
            print("found %s links from %s" % (res["count"], res["total"]))
            res = res.get("resourcelinks", [])
            idx = page_size * page + 1

            for item in res:
                oid = item["id"]
                print("# idx: %s - id: %s - name: %s" % (idx, oid, item["name"]))

                details = item.get("details")
                start_resource = details.get("start_resource")
                end_resource = details.get("end_resource")
                check = True

                uri = "%s/entities/%s" % (self.baseuri, start_resource)
                try:
                    self.cmp_get(uri).get("resource")
                    # print(' - start resource: %s - OK' % start_resource)
                except:
                    self.app.error(" - start resource: %s - KO" % start_resource)
                    check = False

                uri = "%s/entities/%s" % (self.baseuri, end_resource)
                try:
                    self.cmp_get(uri).get("resource")
                    # print(' - end resource: %s - OK' % end_resource)
                except:
                    self.app.error(" - end resource: %s - KO" % end_resource)
                    check = False

                if check is False:
                    data = self.table_link.search(self.query.id == item["id"])
                    if len(data) == 0:
                        self.table_link.insert(item)

                idx += 1

    @ex(
        help="get bad links",
        description="get bad links",
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
            items = self.table_link.search(self.query.__meta__.definition == definition)
        else:
            items = self.table_link.all()
        headers = ["definition", "id", "name", "type", "start_resource", "end_resource"]
        fields = [
            "__meta__.definition",
            "id",
            "name",
            "details.type",
            "details.start_resource",
            "details.end_resource",
        ]
        self.app.render(items, headers=headers, fields=fields)

    @ex(
        help="get bad links",
        description="get bad links",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "link id",
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
        data = self.table_link.search(self.query.id == oid)
        if len(data) > 0:
            self.table_link.remove(doc_ids=[data[0].doc_id])

    @ex(
        help="remove bad link",
        description="remove bad link",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "link id",
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
        uri = "%s/links/%s" % (self.baseuri, oid)
        self.cmp_delete(uri, data="")

        data = self.table_link.search(self.query.id == oid)
        if len(data) > 0:
            self.table_link.remove(doc_ids=[data[0].doc_id])
