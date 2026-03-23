# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from datetime import datetime
from cement import ex

from beecell.simple import str2bool
from beehive3_cli.core.controller import PAGINATION_ARGS
from beehive3_cli.plugins.platforms.controllers import (
    ChildPlatformController,
    PLATFORM_ARGS,
)
from beehive3_cli.translate import _


class FirewallLogController(ChildPlatformController):
    class Meta:
        label = "fwlog"
        description = _("firewall logs management")
        help = _("firewall logs management")

        index_headers = [
            "name",
            "replicas",
            "shards",
            "uuid",
            "version",
            "creation_date",
        ]
        index_fields = [
            "settings.index.provided_name",
            "settings.index.number_of_replicas",
            "settings.index.number_of_shards",
            "settings.index.uuid",
            "settings.index.version.created",
            "settings.index.creation_date",
        ]

    def pre_command_run(self):
        super().pre_command_run()

        self.es = self.config_elastic()

    def get_current_elastic_index(self):
        l_date = datetime.now().strftime("%Y.%m.%d")
        return f"*-filebeat-7.10.0-{l_date}-infr_nivola"

    @ex(
        help=_("show log for dfw"),
        description=_("show log for dfw"),
        arguments=PLATFORM_ARGS(
            PAGINATION_ARGS,
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
                    ["-reject"],
                    {
                        "help": _("if true show only reject"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-sort"],
                    {
                        "help": _("sort field. Ex. @timestamp:desc"),
                        "action": "store",
                        "type": str,
                        "default": "@timestamp:desc",
                    },
                ),
                (
                    ["-pretty"],
                    {
                        "help": _("if true show pretty logs"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-ip"],
                    {
                        "help": _("ip address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ],
        ),
    )
    def dfw(self):
        index = self.app.pargs.index
        reject = self.app.pargs.reject
        sort = self.app.pargs.sort
        page = self.app.pargs.page
        size = self.app.pargs.size
        pretty = self.app.pargs.pretty
        ip = self.app.pargs.ip

        if index is None:
            index = self.get_current_elastic_index()

        reject = str2bool(reject)

        # match = [
        #     {'match': {'app': {'query': app, 'operator': 'and'}}},
        #     {'match': {'component': {'query': 'api', 'operator': 'and'}}},
        # ]
        #
        # if server is not None:
        #     match.append({'match': {'server': {'query': server, 'operator': 'and'}}})
        #
        # if thread is not None:
        #     match.append({'match': {'thread': {'query': thread, 'operator': 'and'}}})

        query_string = f"fields.log_server:{self.env}-vsphere* AND message:*dfwpktlogs*"
        if reject is True:
            query_string += " AND message:*REJECT*"
        if ip is not None:
            query_string += f" AND message:*{ip}*"

        query = {"query_string": {"query": query_string}}
        self.app.log.debug(query)

        header = "{@timestamp} - {message}"
        self._query(index, query, page, size, sort, pretty=pretty, header=header)

    @ex(
        help=_("show log for edge"),
        description=_("show log for edge"),
        arguments=PLATFORM_ARGS(
            PAGINATION_ARGS,
            [
                (
                    ["edge"],
                    {
                        "help": _("edge name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("log type: firewall, config, nat, "),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
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
                    ["-reject"],
                    {
                        "help": _("if true show only reject"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-sort"],
                    {
                        "help": _("sort field. Ex. @timestamp:desc"),
                        "action": "store",
                        "type": str,
                        "default": "@timestamp:desc",
                    },
                ),
                (
                    ["-pretty"],
                    {
                        "help": _("if true show pretty logs"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-ip"],
                    {
                        "help": _("ip address"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ],
        ),
    )
    def edge(self):
        edge = self.app.pargs.edge
        logtype = self.app.pargs.type
        index = self.app.pargs.index
        reject = self.app.pargs.reject
        sort = self.app.pargs.sort
        page = self.app.pargs.page
        size = self.app.pargs.size
        pretty = self.app.pargs.pretty
        ip = self.app.pargs.ip

        if index is None:
            index = self.get_current_elastic_index()

        reject = str2bool(reject)

        # match = [
        #     {'match': {'app': {'query': app, 'operator': 'and'}}},
        #     {'match': {'component': {'query': 'api', 'operator': 'and'}}},
        # ]
        #
        # if server is not None:
        #     match.append({'match': {'server': {'query': server, 'operator': 'and'}}})
        #
        # if thread is not None:
        #     match.append({'match': {'thread': {'query': thread, 'operator': 'and'}}})

        query_string = f"fields.log_server:{edge}"
        if logtype is not None:
            query_string += f" AND message:*{logtype}*"
        # if reject is True:
        #     query_string += ' AND message:*REJECT*'
        if ip is not None:
            query_string += f" AND message:*{ip}*"

        query = {"query_string": {"query": query_string}}
        self.app.log.debug(query)

        header = "{@timestamp} - {message}"
        self._query(index, query, page, size, sort, pretty=pretty, header=header)
