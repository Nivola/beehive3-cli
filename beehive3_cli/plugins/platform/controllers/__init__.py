# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from datetime import datetime
from binascii import crc32
from os import path
from re import search
from jinja2 import Template
from elasticsearch import Elasticsearch
from beecell.types.type_string import str2bool, truncate
from beecell.types.type_list import merge_list
from beehive3_cli.core.controller import BaseController, BASE_ARGS
from beehive3_cli.core.util import load_environment_config


def PLATFORM_ARGS(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": "mysql cluster or single node reference label",
            },
        ),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class ChildPlatformController(BaseController):
    class Meta:
        stacked_on = "platform"
        stacked_type = "nested"
        default_group = None

    def _default(self):
        self._parser.print_help()

    def pre_command_run(self):
        super(ChildPlatformController, self).pre_command_run()

        self.ansible_path = self.app.config.get("beehive", "ansible_path")
        self.local_package_path = self.app.config.get("beehive", "local_package_path")
        self.config = load_environment_config(self.app)

    def file_render(self, runner, resource, context={}):
        """render a j2 template using current ansible variables hacks:
        - iterate the rendering for values containig variables
        - in order to prevent looping in rendering iteration compute crc32 as
        hashing function and compare with previus crc. There may be some problems
        because of crc32 collissions maybe murmur (mmh3) should be better but
        at this time we do not want to have a new library
        """
        content, filename = self.file_content(resource)
        template = Template(content)

        hosts = self.get_hosts(runner, "beehive")
        context_data = runner.get_hosts_vars(hosts)
        for key in context.keys():
            context_data[key] = context[key]

        out_rep = template.render(**context_data)
        pp_crc = 0
        p_crc = 0
        c_crc = crc32(out_rep)
        # print('current crc = 0x%08x' % c_crc  )
        while search("{{.*}}", out_rep) and (p_crc != c_crc) and (pp_crc != c_crc):
            template = Template(out_rep)
            out_rep = template.render(**context_data)
            pp_crc = p_crc
            p_crc = c_crc
            c_crc = crc32(out_rep)
            # print('render iteration current crc = 0x%08x' % c_crc  )
        return out_rep, filename

    def file_content(self, valorname):
        """if valorname starts with @ return the file content try for path or relative to ansible_path
        otherwise return valorname itself
        """

        if valorname[0] == "@":
            name = valorname[1:]
            if path.isfile(name):
                filename = name
            else:
                filename = path.join(self.ansible_path, name)
            if path.isfile(filename):
                f = open(filename, "r")
                value = f.read()
                f.close()
                return value, filename
            else:
                raise Exception("%s is not a file" % name)
        else:
            # return '' for file so wi do not need to check
            return valorname, ""

    def config_elastic(self):
        config = load_environment_config(self.app)

        orchestrators = config.get("orchestrators", {}).get("elk", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception("No elk default platform is available for this environment. Select another environment")

        if label not in orchestrators:
            raise Exception("Valid label are: %s" % ", ".join(orchestrators.keys()))
        conf = orchestrators.get(label)

        self.elk_env = config.get("alias", self.env)
        hosts = conf.get("hosts")
        user = conf.get("user")
        pwd = conf.get("pwd")
        ssl = conf.get("ssl", False)

        elk_hosts = []
        for host in hosts:
            # elk_hosts.append(str(host))
            if ssl is False:
                elk_hosts.append("http://" + str(host) + ":9200")
            else:
                elk_hosts.append("https://" + str(host) + ":9200")

        if user is not None and pwd is not None:
            http_auth = (user, pwd)
        else:
            http_auth = None
        if ssl is False:
            elasticsearch = Elasticsearch(
                elk_hosts,
                # http_auth
                http_auth=http_auth,
                # sniff before doing anything
                # sniff_on_start=False,
                # refresh nodes after a node fails to respond
                # sniff_on_connection_fail=False,
                # and also every 60 seconds
                # sniffer_timeout=60
                timeout=60,
            )
        else:
            elasticsearch = Elasticsearch(
                elk_hosts,
                # http_auth
                http_auth=http_auth,
                # turn on SSL
                # use_ssl=True,
                # make sure we verify SSL certificates
                verify_certs=False,
                timeout=60,
            )

        return elasticsearch

    def get_elastic_query_order(self, fields):
        query = {"sort": [{f[0]: f[1]} for f in fields]}
        return query

    def get_current_elastic_index(self):
        return "cmp-%s-%s" % (self.env, datetime.now().strftime("%Y.%m.%d"))

    def get_current_elastic_event_index(self):
        return "cmp-event-%s-%s" % (self.env, datetime.now().strftime("%Y.%m.%d"))

    def _query(
        self,
        index,
        query,
        page,
        size,
        sort,
        pretty=True,
        header=[],
        field=[],
        render=True,
        maxsize=1000,
        transform=None,
    ):
        """Make elastic search query

        :param index: index name
        :param query: query to to
        :param page: query page
        :param size: query size
        :param sort: query sort field
        :param pretty: if True print list as pretty logs
        :param header: pretty header
        :param render: if False does not print result
        :return: query data
        """
        elasticsearch = self.config_elastic()
        pretty = str2bool(pretty)
        page = page * size

        # body = {"query": query}
        # self.app.log.debug("query request: %s" % body)
        # body.update(self.get_elastic_query_order([sort.split(":")]))

        self.app.log.debug("_query - index: %s" % index)
        self.app.log.debug("_query - sort: %s" % sort)
        self.app.log.debug("_query - query: %s" % query)
        self.app.log.debug("_query - pretty: %s" % pretty)
        # pretty = False

        # res = es.search(index=index, body=body, from_=page, size=size, sort=sort)
        res = elasticsearch.search(index=index, from_=page, size=size, sort=sort, query=query)
        self.app.log.debug("_query - query result: %s" % truncate(res, size=10000))

        hits = res.get("hits", {})
        values = []
        # headers = fields = []

        # if len(hits.get('hits', [])) > 0:
        #     fields = ['_id']
        #     fields.extend(hits.get('hits', [])[0].get('_source').keys())
        #     headers = fields
        #     headers[0] = 'id'

        for hit in hits.get("hits", []):
            value = hit.get("_source")
            value["id"] = hit.get("_id")
            values.append(value)

        self.app.log.debug("_query - values: %s" % len(values))
        self.app.log.debug("_query - page: %s" % page)
        self.app.log.debug("_query - size: %s" % size)

        total = hits.get("total", {})
        if isinstance(total, dict):
            total = total.get("value", 0)

        sort = sort.split(":")
        data = {
            "page": page,
            "count": size,
            "total": total,
            "sort": {"field": sort[0], "order": sort[1]},
            "values": values,
        }

        if render is True:
            if pretty:
                data = data.get("values", [])
                data.reverse()
                for raw in data:
                    if raw.get("levelname") == "INFO":
                        self.c(header.format(**raw), "white")
                    elif raw.get("levelname") == "DEBUG":
                        self.c(header.format(**raw), "blue")
                    elif raw.get("levelname") == "ERROR":
                        self.c(header.format(**raw), "red")
                    elif raw.get("levelname") == "WARNING":
                        self.c(header.format(**raw), "yellow")
                    else:
                        # self.c(header.format(**raw), "gray")
                        print(raw)
            else:
                data["values"].reverse()

                field = header

                self.app.render(
                    data,
                    key="values",
                    headers=header,
                    fields=field,
                    maxsize=maxsize,
                    transform=transform,
                )

        return data
