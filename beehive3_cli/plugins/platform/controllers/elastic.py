# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from datetime import datetime
from cement import ex
from beecell.simple import dict_get, format_date
from beedrones.elk.client_elastic import ElasticManager
from beehive3_cli.core.controller import ARGS, PARGS
from beehive3_cli.plugins.platform.controllers import ChildPlatformController


class ElkController(ChildPlatformController):
    setup_cmp = False

    class Meta:
        label = "elastic"
        stacked_on = "platform"
        stacked_type = "nested"
        description = "elastic management"
        help = "elastic management"

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
        super(ElkController, self).pre_command_run()

        from elasticsearch import Elasticsearch

        self.es: Elasticsearch = self.config_elastic()
        self.client_elastic = ElasticManager(es=self.es)

    @ex(help="ping elastic", description="ping elastic", arguments=ARGS())
    def ping(self):
        res = self.es.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(help="get elastic info", description="get elastic info", arguments=ARGS())
    def info(self):
        res = self.es.info()
        self.app.render(res, details=True)

    @ex(help="get cluster health", description="get cluster health", arguments=ARGS())
    def cluster_health(self):
        res = self.es.cluster.health()
        self.app.render(res, details=True)

    @ex(
        help="get cluster statistics",
        description="get cluster statistics",
        arguments=ARGS(),
    )
    def cluster_stats(self):
        res = self.es.cluster.stats()
        self.app.render(res, details=True)

    @ex(help="get cluster nodes", description="get cluster nodes", arguments=ARGS())
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
        help="get indexes",
        description="get indexes",
        arguments=ARGS(
            [
                (
                    ["-index"],
                    {
                        "help": "index name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-pattern"],
                    {
                        "help": "index pattern",
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
                # self.app.log.debug("+++++ index_get - provided_name: %s" % dict_get(item, 'settings.index.provided_name'))
                item["stats"] = res2.get(dict_get(item, "settings.index.provided_name"))
                # self.app.log.debug("+++++ index_get - item['stats']: %s" % item['stats'])
                # self.app.log.debug("+++++ index_get - size_in_bytes: %s" % dict_get(item['stats'], 'total.store.size_in_bytes'))

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
        help="list indexes",
        description="list indexes",
        arguments=ARGS(
            [
                (
                    ["-pattern"],
                    {
                        "help": "index pattern",
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
        print("Searching indices with pattern %s" % pattern)

        if pattern is not None:
            self.app.log.debug("+++++ index_list - pattern: %s" % pattern)
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
        help="get index statistics",
        description="get index statistics",
        arguments=ARGS(
            [
                (
                    ["index"],
                    {
                        "help": "index name",
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
        help="count index documents",
        description="count index documents",
        arguments=PARGS(
            [
                (
                    ["index"],
                    {
                        "help": "index name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-query"],
                    {
                        "help": "simple query like field1:value1",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sort"],
                    {
                        "help": "sort field. Ex. date:desc]",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-fields"],
                    {
                        "help": "comma separated list of fields to show",
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
        sort = self.app.pargs.sort
        page = self.app.pargs.page
        size = self.app.pargs.size
        show_fields = self.app.pargs.fields
        if query_data is None:
            query = {"match_all": {}}
        else:
            k, v = query_data.split(":")
            query = {"match": {k: {"query": v, "operator": "and"}}}
        page = page * size
        body = {"query": query}
        res = self.es.count(index=index, body=body)
        self.app.render(res, headers=["count", "_shards"], maxsize=200)
        return

    @ex(
        help="query index",
        description="query index",
        arguments=PARGS(
            [
                (
                    ["index"],
                    {
                        "help": "index name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-query"],
                    {
                        "help": "simple query like field1:value1",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sort"],
                    {
                        "help": "sort field. Ex. date:desc]",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-fields"],
                    {
                        "help": "comma separated list of fields to show",
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
        query_data = self.app.pargs.query
        sort = self.app.pargs.sort
        page = self.app.pargs.page
        size = self.app.pargs.size
        show_fields = self.app.pargs.fields

        if query_data is None:
            query = {"match_all": {}}
        else:
            k, v = query_data.split(":")
            query = {"match": {k: {"query": v, "operator": "and"}}}
            # query = {"match_phrase": {k: {"query": v}}}

        page = page * size
        body = {"query": query}
        # if sort is not None:
        #     sort = sort.split(':')
        #     body.update(self.get_elastic_query_order([]))
        res = self.es.search(index=index, body=body, from_=page, size=size, sort=sort)
        hits = res.get("hits", {})

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

    @ex(
        help="delete index",
        description="delete index",
        arguments=ARGS(
            [
                (
                    ["index"],
                    {
                        "help": "index name",
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
            self.app.render({"msg": "delete index %s" % item}, headers=["msg"], maxsize=200)

    # ------------------
    # -- ROLE MAPPING --
    # ------------------
    @ex(
        help="add role mapping",
        description="add role mapping",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "role mapping name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["role_name"],
                    {
                        "help": "role name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["user_email"],
                    {
                        "help": "user email",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["realm_name"],
                    {
                        "help": "realm name",
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
        help="get role mapping",
        description="get role mapping",
        arguments=ARGS(
            [
                (
                    ["-name"],
                    {
                        "help": "role mapping name",
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
        help="delete role mapping",
        description="delete role mapping",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "role mapping name",
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
        self.app.render({"msg": "delete role mapping %s" % role_mapping_name})

    # ----------
    # -- USER --
    # ----------
    @ex(
        help="add user",
        description="add user",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "user name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["password"],
                    {
                        "help": "password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["role"],
                    {"help": "role", "action": "store", "type": str, "default": None},
                ),
                (
                    ["-full_name"],
                    {
                        "help": "full_name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {
                        "help": "full_name",
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
        self.app.render({"msg": "add user %s" % res})

    @ex(
        help="get user",
        description="get user",
        arguments=ARGS(
            [
                (
                    ["-name"],
                    {
                        "help": "user name",
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
        help="delete user",
        description="delete user",
        arguments=ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "user name",
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
        self.app.render({"msg": "delete user %s" % user_name})
