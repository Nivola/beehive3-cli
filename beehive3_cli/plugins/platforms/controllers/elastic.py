# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from datetime import datetime
from cement import ex
from beecell.simple import dict_get, format_date
from beehive3_cli.core.controller import ARGS, PARGS
from beehive3_cli.plugins.platforms.controllers import ChildPlatformController
from beehive3_cli.translate import _


class ElkController(ChildPlatformController):
    setup_cmp = False

    class Meta:
        label = "elastic"
        stacked_on = "platform"
        stacked_type = "nested"
        description = _("elastic management")
        help = _("elastic management")

        default_group = "elk"

        index_headers = [
            "name",
            "replicas",
            "shards",
            "uuid",
            "records",
            "size (MB)",
            "version",
            "creation_date",
        ]
        index_fields = [
            "settings.index.provided_name",
            "settings.index.number_of_replicas",
            "settings.index.number_of_shards",
            "settings.index.uuid",
            "stats.primaries.docs.count",
            "stats.total.store.size_in_bytes",
            "settings.index.version.created",
            "settings.index.creation_date",
        ]

    def pre_command_run(self):
        super().pre_command_run()

        from elasticsearch import Elasticsearch
        from beedrones.elk.client_elastic import ElasticManager

        self.es: Elasticsearch = self.config_elastic()
        self.client_elastic = ElasticManager(es=self.es)

    @ex(help=_("ping elastic"), description=_("ping elastic"), arguments=ARGS())
    def ping(self):
        res = self.es.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(
        help=_("get elastic info"),
        description=_("get elastic info"),
        example="beehive platform elastic info -e <env>",
        arguments=ARGS(),
    )
    def info(self):
        res = self.es.info()
        self.app.render(res, details=True)

    @ex(
        help=_("get cluster health"),
        description=_("get cluster health"),
        example="beehive platform elastic cluster-health -e <env>",
        arguments=ARGS(),
    )
    def cluster_health(self):
        res = self.es.cluster.health()
        self.app.render(res, details=True)

    @ex(
        help=_("get cluster statistics"),
        description=_("get cluster statistics"),
        example="beehive platform elastic cluster-stats -e <env>",
        arguments=ARGS(),
    )
    def cluster_stats(self):
        res = self.es.cluster.stats()
        self.app.render(res, details=True)

    @ex(
        help=_("get cluster nodes"),
        description=_("get cluster nodes"),
        example="beehive platform elastic cluster-nodes -e <env>",
        arguments=ARGS(),
    )
    def cluster_nodes(self):
        res = self.es.nodes.info().get("nodes")
        nodes = [
            {
                "id": k,
                "name": n["name"],
                "host": n["host"],
                "version": n["version"],
                "roles": n["roles"],
                "attributes": n["attributes"],
                "os": dict_get(n, "os.pretty_name"),
                "jvm": dict_get(n, "jvm.vm_name"),
                "transport": dict_get(n, "transport.publish_address"),
                "http": dict_get(n, "http.publish_address"),
            }
            for k, n in res.items()
        ]
        headers = ["id", "name", "host", "version", "roles", "attributes", "os", "jvm"]
        fields = ["id", "name", "host", "version", "roles", "attributes", "os", "jvm"]
        self.app.render(nodes, headers=headers, fields=fields)

    @ex(
        help=_("get indexes"),
        description=_("get indexes"),
        example="beehive platform elastic index-get -e <env>",
        arguments=ARGS(
            [
                (
                    ["-index"],
                    {
                        "help": _("index name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-pattern"],
                    {
                        "help": _("index pattern"),
                        "action": "store",
                        "type": str,
                        "default": "*",
                    },
                ),
            ]
        ),
    )
    def index_get(self):
        index = self.app.pargs.index
        if index is not None:
            res = self.es.indices.get(index=index).get(index, [])
            self.app.log.debug(res)

            if self.is_output_text():
                mappings = res.pop("mappings", {}).get("properties", {})

                # fields = [{
                #     'name': k,
                #     'type': v.get('type', None),
                #     'keyword_type': dict_get(v, 'fields.keyword.type'),
                #     'keyword_ignore_above': dict_get(v, 'fields.keyword.ignore_above'),
                # } for k, v in mappings.items()]
                fields = mappings

                self.app.render(dict_get(res, "settings.index"), details=True)
                self.c("\nmappings", "underline")
                self.app.render(
                    fields,
                    headers=["name", "type", "keyword_type", "keyword_ignore_above"],
                )
            else:
                self.app.render(res, details=True)
        else:
            pattern = self.app.pargs.pattern
            # self.app.log.debug("+++++ index_get - pattern: %s" % pattern)

            res = list(self.es.indices.get(index=pattern).values())
            # self.app.log.debug("+++++ index_get - res: %s" % res)

            res2 = self.es.indices.stats(index=pattern).get("indices", {})
            for item in res:
                item["stats"] = res2.get(dict_get(item, "settings.index.provided_name"))

            transform = {
                "settings.index.creation_date": lambda x: format_date(datetime.fromtimestamp(int(x) / 1000)),
                "stats.total.store.size_in_bytes": lambda x: round(float(x) / 1024 / 1024, 1),
            }
            self.app.render(
                res,
                headers=self._meta.index_headers,
                fields=self._meta.index_fields,
                transform=transform,
                maxsize=200,
            )

    @ex(
        help=_("list indexes"),
        description=_("list indexes"),
        example="beehive platform elastic index-list -pattern cmp-event-podto1-2026.01.* -e podto1",
        arguments=ARGS(
            [
                (
                    ["-pattern"],
                    {
                        "help": _("index pattern"),
                        "action": "store",
                        "type": str,
                        "default": "*",
                    },
                ),
            ]
        ),
    )
    def index_list(self):
        pattern = self.app.pargs.pattern
        # attention: pattern can match a local file!
        print(f"Searching indices with pattern {pattern}")

        if pattern is not None:
            self.app.log.debug(f"+++++ index_list - pattern: {pattern}")
            res = list(self.es.indices.get(index=pattern).values())
            # self.app.log.debug("+++++ index_get - res: %s" % res)
        else:
            res = list(self.es.indices.get(index=pattern).values())

        transform = {
            "settings.index.creation_date": lambda x: format_date(datetime.fromtimestamp(int(x) / 1000)),
        }
        index_list_headers = [
            "name",
            "replicas",
            "shards",
            "uuid",
            "version",
            "creation_date",
        ]
        index_list_fields = [
            "settings.index.provided_name",
            "settings.index.number_of_replicas",
            "settings.index.number_of_shards",
            "settings.index.uuid",
            "settings.index.version.created",
            "settings.index.creation_date",
        ]
        self.app.render(
            res,
            headers=index_list_headers,
            fields=index_list_fields,
            transform=transform,
            maxsize=200,
        )

    @ex(
        help=_("get index statistics"),
        description=_("get index statistics"),
        arguments=ARGS(
            [
                (
                    ["index"],
                    {
                        "help": _("index name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def index_stats(self):
        index = self.app.pargs.index
        es = self.config_elastic()
        res = es.indices.stats(index=index).get("indices", {}).get(index, [])
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help=_("count index documents"),
        description=_("count index documents"),
        arguments=PARGS(
            [
                (
                    ["index"],
                    {
                        "help": _("index name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-query"],
                    {
                        "help": _("simple query like field1:value1"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sort"],
                    {
                        "help": _("sort field. Ex. date:desc]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-fields"],
                    {
                        "help": _("comma separated list of fields to show"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def index_count(self):
        index = self.app.pargs.index
        query_data = self.app.pargs.query
        #sort = self.app.pargs.sort
        page = self.app.pargs.page
        size = self.app.pargs.size
        #show_fields = self.app.pargs.fields
        if query_data is None:
            query = {"match_all": {}}
        else:
            k, v = query_data.split(":")
            query = {"match": {k: {"query": v, "operator": "and"}}}
        page = page * size
        body = {"query": query}
        res = self.es.count(index=index, body=body)
        self.app.render(res, headers=["count", "_shards"], maxsize=200)

    @ex(
        help=_("query index"),
        description=_("query index"),
        example=(
            "beehive platform elastic index-query cmp-event-podto1-2024.11.* -e <env> "
            "-sort date:asc -f text -query "
            "source.user.keyword:abc.def@ghi.lmno,"
            "type.keyword:API,dest.pod.keyword:uwsgi-service-app-*,"
            "data.op.keyword:*serviceinsts*:DELETE -fields date,data"
        ),
        arguments=PARGS(
            [
                (
                    ["index"],
                    {
                        "help": _("index name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-custom_must"],
                    {
                        "help": _("custom_must es. \"{\\\"range\\\":{\\\"date\\\":{\\\"gte\\\":\\\"2026-02-09T06:00:00.000+01:00\\\",\\\"lt\\\":\\\"2026-02-09T10:00:00.000+01:00\\\"}}}\" "),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-query"],
                    {
                        "help": _("comma separated query like field1:value1,field2:value2"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-querynot"],
                    {
                        "help": _("comma separated query like field1:value1,field2:value2"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sort"],
                    {
                        "help": _("sort field. Ex. date:desc]"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-fields"],
                    {
                        "help": _("comma separated list of fields to show"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def index_query(self):
        index = self.app.pargs.index
        custom_must = self.app.pargs.custom_must
        query_data = self.app.pargs.query
        querynot_data = self.app.pargs.querynot
        sort = self.app.pargs.sort
        page = self.app.pargs.page
        size = self.app.pargs.size
        show_fields = self.app.pargs.fields

        if query_data is None:
            query = {"match_all": {}}
        else:
            # k, v = query_data.split(":")
            # query = {"match": {k: {"query": v, "operator": "and"}}}
            # query = {"match_phrase": {k: {"query": v}}}
            must = []
            if query_data is not None:
                must = self.get_filter_query(query_data, custom_must)

            must_not = []
            if querynot_data is not None:
                must_not = self.get_filter_query(querynot_data)

            # index = None # better abcd*
            query = {
                "bool": {
                    "must": must,
                    "must_not": must_not,
                }
            }
            print(f"query: {query}")

        # print("page: %s" % page)
        # print("size: %s" % size)
        page = page * size
        body = {"query": query}

        # print("sort: %s" % sort)
        if sort is None:
            sort_elastic = []
        else:
            sort = sort.split(':')
            sort_elastic = [{ sort[0]: sort[1] }]

        # print("sort_elastic: %s" % sort_elastic)
        res = self.es.search(index=index, body=body, from_=page, size=size, sort=sort_elastic)
        hits = res.get("hits", {})
        # print("hits: %s" % hits)

        values = []
        headers = fields = []
        if len(hits.get("hits", [])) > 0:
            fields = ["_id"]
            fields.extend(hits.get("hits", [])[0].get("_source").keys())
            headers = fields
            headers[0] = "id"

        for hit in hits.get("hits", []):
            value = hit.get("_source")
            value["id"] = hit.get("_id")
            values.append(value)

        total = hits.get("total", {})
        if isinstance(total, dict):
            total = total.get("value", 0)

        maxsize = 40
        if show_fields is not None:
            headers = fields = show_fields.split(",")
            maxsize = 1000

        data = {
            "page": page,
            "count": size,
            "total": total,
            "sort": {"field": "timestamp", "order": "ASC"},
            "values": values,
        }
        self.app.render(data, key="values", headers=headers, fields=fields, maxsize=maxsize)

    def get_filter_query(self, query_data, custom_must):
        must = []
        filters = query_data.split(",")
        for l_filter in filters:
            # k, v = filter.split(":")
            sep_index = l_filter.find(":")
            k = l_filter[0:sep_index]
            v = l_filter[sep_index + 1 :]
            if v.find("*") >= 0:
                must.append({"wildcard": {k: v}})
            else:
                must.append({"match_phrase": {k: v}})

        if custom_must is not None:
            import ujson as json
            print("custom_must: %s" % custom_must)
            params = json.loads(custom_must)
            must.append(params)
        # must.append({
        #     "range": {
        #         "date": {
        #         "gte": "2026-02-09T06:00:00.000+01:00",
        #         "lt": "2026-02-09T10:00:00.000+01:00"
        #         }
        #     }
        # })
        return must

    @ex(
        help=_("delete index"),
        description=_("delete index"),
        arguments=ARGS(
            [
                (
                    ["index"],
                    {
                        "help": _("index name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def index_del(self):
        index = self.app.pargs.index
        res = list(self.es.indices.get(index=index).keys())
        for item in res:
            res = self.es.indices.delete(index=item)
            self.app.render({"msg": f"delete index {item}"}, headers=["msg"], maxsize=200)

    # ------------------
    # -- ROLE MAPPING --
    # ------------------
    @ex(
        help=_("add role mapping"),
        description=_("add role mapping"),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("role mapping name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["role_name"],
                    {
                        "help": _("role name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["user_email"],
                    {
                        "help": _("user email"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["realm_name"],
                    {
                        "help": _("realm name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def role_mapping_add(self):
        role_mapping_name = self.app.pargs.name
        role_name = self.app.pargs.role_name
        user_email = self.app.pargs.user_email
        users_email = [user_email]
        realm_name = self.app.pargs.realm_name

        res = self.client_elastic.role_mapping.add(
            role_mapping_name=role_mapping_name,
            role_name=role_name,
            users_email=users_email,
            realm_name=realm_name,
        )
        self.app.render(res, details=True)

    @ex(
        help=_("get role mapping"),
        description=_("get role mapping"),
        arguments=ARGS(
            [
                (
                    ["-name"],
                    {
                        "help": _("role mapping name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def role_mapping_get(self):
        role_mapping_name = self.app.pargs.name
        if role_mapping_name is not None:
            res = self.client_elastic.role_mapping.get(role_mapping_name)
            self.app.render(res, details=True)
        else:
            res = self.client_elastic.role_mapping.get()
            # self.app.render(res, headers=['id', 'name', 'description'])
            self.app.render(res, details=True)

    @ex(
        help=_("delete role mapping"),
        description=_("delete role mapping"),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("role mapping name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def role_mapping_del(self):
        role_mapping_name = self.app.pargs.name
        self.client_elastic.role_mapping.delete(role_mapping_name)
        self.app.render({"msg": f"delete role mapping {role_mapping_name}"})

    # ----------
    # -- USER --
    # ----------
    @ex(
        help=_("add user"),
        description=_("add user"),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["password"],
                    {
                        "help": _("password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["role"],
                    {"help": _("role"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-full_name"],
                    {
                        "help": _("full_name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": _("full_name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def user_add(self):
        user_name = self.app.pargs.name
        password = self.app.pargs.password
        role = self.app.pargs.role
        full_name = self.app.pargs.full_name
        email = self.app.pargs.email

        res = self.client_elastic.user.add(
            user_name=user_name,
            password=password,
            role=role,
            full_name=full_name,
            email=email,
        )
        # self.app.render(res, details=True)
        self.app.render({"msg": f"add user {res}"})

    @ex(
        help=_("get user"),
        description=_("get user"),
        arguments=ARGS(
            [
                (
                    ["-name"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def user_get(self):
        user_name = self.app.pargs.name
        if user_name is not None:
            res = self.client_elastic.user.get(user_name)
            self.app.render(res, details=True)
        else:
            res = self.client_elastic.user.get()
            # self.app.render(res, headers=['username', 'roles', 'enabled'])
            self.app.render(res, details=True)

    @ex(
        help=_("delete user"),
        description=_("delete user"),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def user_del(self):
        user_name = self.app.pargs.name
        self.client_elastic.user.delete(user_name)
        self.app.render({"msg": f"delete user {user_name}"})
