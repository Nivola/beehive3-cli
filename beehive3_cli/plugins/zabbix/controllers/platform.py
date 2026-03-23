# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2026 CSI-Piemonte

from datetime import datetime
from cement import ex

from beecell.simple import merge_list
from beecell.types.type_date import get_date_from_timestamp, format_date
from beecell.types.type_dict import dict_get
from beecell.types.type_string import str2bool
from beecell.util import ensure_str
from beedrones.zabbix.client import ZabbixManager

from beehive3_cli.core.controller import BaseController, BASE_ARGS
from beehive3_cli.core.util import load_environment_config, load_config
from beehive3_cli.translate import _


def zabbix_args(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": _("zabbix platform reference label"),
            },
        ),
        (
            ["-P", "--project"],
            {
                "action": "store",
                "dest": "project",
                "help": _("zabbix current project name"),
            },
        ),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


def zabbix_pargs(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": _("zabbix platform reference label"),
            },
        ),
        (
            ["-P", "--project"],
            {
                "action": "store",
                "dest": "project",
                "help": _("zabbix host group name or id. e.g. Csi.Datacenter.Test or 1234.."),
            },
        ),
        (
            ["-size"],
            {
                "help": _("list page size [default=20]"),
                "action": "store",
                "type": int,
                "default": 20,
            },
        ),
        (
            ["-page"],
            {
                "help": _("list page [default=0]"),
                "action": "store",
                "type": int,
                "default": 0,
            },
        ),
        (
            ["-order"],
            {
                "help": _("list sort order [default=DESC]"),
                "action": "store",
                "type": str,
                "default": "DESC",
            },
        ),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class ZabbixPlatformController(BaseController):
    class Meta:
        label = "zabbix"
        stacked_on = "platform"
        stacked_type = "nested"
        description = _("zabbix platform")
        help = _("zabbix platform")

    def pre_command_run(self):
        super().pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("zabbix", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No zabbix default platform is available for this environment. Select another environment"
                )

        if label not in orchestrators:
            raise Exception(f"Valid label are: {', '.join(orchestrators.keys())}")
        conf = orchestrators.get(label)

        proto = conf.get("proto")
        host = conf.get("hosts")[0]
        port = conf.get("port")
        path = conf.get("path")
        uri = f"{proto}://{host}:{port}{path}"

        if self.app.config.get("log.clilog", "verbose_log"):
            project = getattr(self.app.pargs, "project", None)
            transform = {"msg": lambda x: self.color_string(x, "YELLOW")}
            self.app.render(
                {"msg": f"Using zabbix orchestrator: {label} (uri: {uri} - project: {project})"},
                transform=transform,
            )
            self.app.log.debug(f"Using zabbix orchestrator: {label} (uri: {uri} - project: {project})")

        # print(conf)
        self.client = ZabbixManager(uri=uri)
        self.client.set_timeout(60.0)
        self.client.authorize(conf.get("user"), conf.get("pwd"))

    def __get_host_by_name(self, name):
        res = self.client.host.list(search={"host": name})
        if len(res) > 0:
            return res[0]
        raise Exception(f"no host {name} found")

    def __get_host_group_id_by_name(self, name):
        count = self.client.hostgroup.list(countOutput=True)
        if count == 0:
            raise Exception("No host groups found")
        if name.isnumeric():
            # assume it's a group id
            try:
                # check it exists
                res = self.client.hostgroup.get(name)
                return name  # = res.get('groupid')
            except Exception as e:
                self.app.error(f"{e}. Trying using name filter...")
                # in the unlikely case the host group name is numeric

        res = self.client.hostgroup.list(selecthosts=None, name=[name])  # by exact name
        if len(res) == 0:
            raise Exception(f"No host groups names match exactly {name}")
        if len(res) > 1:
            raise Exception(f"Multiple groups match exactly {name}")

        return res[0].get("groupid")

    @ex(help=_("ping zabbix"), description=_("ping zabbix"), arguments=zabbix_args())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(
        help=_("get zabbix version"),
        description=_("get zabbix version"),
        arguments=zabbix_args(),
    )
    def version(self):
        res = self.client.version()
        self.app.render({"version": res}, headers=["version"])

    ############
    # trigger
    ############

    @ex(
        help=_("add trigger"),
        description=_("add trigger"),
        arguments=zabbix_args(
            [
                (
                    ["desc"],
                    {
                        "help": _("trigger description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["comment"],
                    {
                        "help": _("trigger comment"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["expression"],
                    {
                        "help": _("trigger expression"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["priority"],
                    {
                        "help": _(
                            "priority type. Can be: 0 (Default) not classified, 1 information, 2 warning, "
                            "3 average, 4 high, 5 disaster"
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def trigger_add(self):
        desc = self.app.pargs.desc
        comment = self.app.pargs.comment
        expression = self.app.pargs.expression
        priority = self.app.pargs.priority
        res = self.client.trigger.create(desc, comment, expression, priority)
        self.app.render({"msg": f"add trigger {res}"})

    @ex(
        help=_("list triggers"),
        description=_("list triggers"),
        arguments=zabbix_pargs(
            [
                (
                    ["-id"],
                    {
                        "help": _("trigger id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-field"],
                    {
                        "help": _("sort field"),
                        "action": "store",
                        "type": str,
                        "default": "triggerid",
                    },
                ),
                (
                    ["-host"],
                    {
                        "help": _("host id filter"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def trigger_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.trigger.get(oid)
            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            field = self.app.pargs.field
            order = self.app.pargs.order

            lfilter = {"countOutput": True}
            host = getattr(self.app.pargs, "host", None)
            if host is not None:
                lfilter.update({"hostids": [host]})

            count = self.client.trigger.list(**lfilter)
            res = self.client.trigger.list(limit=size, offset=page, sortorder=order.upper(), sortfield=field)
            res = {
                "triggers": res,
                "page": page,
                "count": size,
                "total": count,
                "sort": {"field": field, "order": order},
            }
            headers = ["id", "desc", "expression", "type", "state"]
            fields = ["triggerid", "description", "expression", "type", "state"]
            self.app.render(res, key="triggers", headers=headers, fields=fields)

    @ex(
        help=_("delete trigger"),
        description=_("delete trigger"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("trigger id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def trigger_del(self):
        oid = self.app.pargs.id
        self.client.trigger.delete(oid)
        self.app.render({"msg": f"delete trigger {oid}"}, headers=["msg"])

    ############
    # host
    ############

    @ex(
        help=_("add host"),
        description=_("add host"),
        arguments=zabbix_args(
            [
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
                #
                # As a data file example, see beehive-mgmt/configs/test/example/zabbix_host_add.yml
                #
            ]
        ),
    )
    def host_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)

        host = data.get("host")
        name = host.get("name")
        desc = host.get("desc")
        interfaces = host.get("interfaces")
        groups = host.get("groups")
        templates = host.get("templates")

        res = self.client.host.create(name, interfaces, groupids=groups, templateids=templates, description=desc)
        self.app.render({"msg": f"add host {res['hostids']}"})

    @ex(
        help=_("list hosts"),
        description=_("list hosts"),
        arguments=zabbix_pargs(
            [
                (
                    ["-id"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-field"],
                    {
                        "help": _("sort field"),
                        "action": "store",
                        "type": str,
                        "default": "hostid",
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("host name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_get(self):
        project = self.app.pargs.project
        hostgroup_id = None
        if project:
            try:
                hostgroup_id = self.__get_host_group_id_by_name(project)
            except Exception as e:
                self.app.error(f"{e} - Ignoring host group parameter.")

        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.host.get(oid)
            if self.is_output_text():
                self.app.render(res, details=True)
                self.c("\ngroups", "underline")
                res = self.client.host.groups(oid)
                groups = res.get("groups")
                self.app.render(groups, headers=["groupid", "name", "internal", "flags"])
                self.c("\ntemplates", "underline")
                res = self.client.host.templates(oid)
                tmpls = res.get("parentTemplates")
                self.app.render(tmpls, headers=["templateid", "name", "status"])
                self.c("\ninterfaces", "underline")
                res = self.client.host.interfaces(oid)
                interfaces = res.get("interfaces")
                self.app.render(
                    interfaces,
                    headers=[
                        "interfaceid",
                        "main",
                        "type",
                        "useip",
                        "ip",
                        "dns",
                        "port",
                        "bulk",
                    ],
                )
                self.c("\nalerts", "underline")
                alerts = self.client.alert.list(hostids=oid, limit=10, sortorder="DESC", sortfield="clock")
                transform = {"clock": lambda x: datetime.fromtimestamp(int(x))}
                self.app.render(
                    alerts,
                    headers=["alertid", "actionid", "clock", "sendto", "subject"],
                    transform=transform,
                )
            else:
                self.app.render(res, details=True)
        else:
            name = self.app.pargs.name
            page = self.app.pargs.page
            size = self.app.pargs.size
            field = self.app.pargs.field
            order = self.app.pargs.order

            params_dict = {}
            if hostgroup_id:
                params_dict.update(groupids=[hostgroup_id])
            if name:
                params_dict.update(search={"host": name})

            count = self.client.host.list(countOutput=True, **params_dict)
            res = self.client.host.list(
                limit=size,
                offset=page,
                sortorder=order.upper(),
                sortfield=field,
                **params_dict,
            )

            res = {
                "hosts": res,
                "page": page,
                "count": size,
                "total": count,
                "sort": {"field": field, "order": order},
            }
            transform = {
                "status": lambda x: "Enabled" if x == "0" else "Disabled",
                "available": lambda x: "available" if x == "1" else "unavailable",
                "maintenance_status": lambda x: "no maintenance" if x == "0" else "maintenance",
            }
            headers = [
                "id",
                "proxy_hostid",
                "host",
                "name",
                "status",
                "available",
                "maintenance_status",
            ]
            fields = [
                "hostid",
                "proxy_hostid",
                "host",
                "name",
                "status",
                "available",
                "maintenance_status",
            ]
            self.app.render(res, key="hosts", headers=headers, fields=fields, transform=transform)

    @ex(
        help=_("list groups the host belongs to"),
        description=_("list groups the host belongs to"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_get_groups(self):
        oid = self.app.pargs.id
        res = self.client.host.groups(oid)
        headers = ["id", "name", "internal", "flags"]
        fields = ["groupid", "name", "internal", "flags"]
        self.app.render(res, key="groups", headers=headers, fields=fields)

    @ex(
        help=_("list templates linked to the host"),
        description=_("list templates linked to the host"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_get_templates(self):
        oid = self.app.pargs.id
        res = self.client.host.templates(oid)
        headers = ["id", "name", "status"]
        fields = ["templateid", "name", "status"]
        self.app.render(res, key="parentTemplates", headers=headers, fields=fields)

    @ex(
        help=_("list interfaces used by the host"),
        description=_("list interfaces used by the host"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_get_interfaces(self):
        oid = self.app.pargs.id
        res = self.client.host.interfaces(oid)
        print(res)
        headers = ["id", "main", "type", "useip", "ip", "dns", "port", "bulk"]
        fields = ["interfaceid", "main", "type", "useip", "ip", "dns", "port", "bulk"]
        self.app.render(res, key="interfaces", headers=headers, fields=fields)

    @ex(
        help=_("list host items"),
        description=_("list host items"),
        arguments=zabbix_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("host name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-state"],
                    {
                        "help": _("host state"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_item_get(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        state = self.app.pargs.state
        if name is not None:
            host = self.__get_host_by_name(name)
            oid = host.get("hostid")

        res = self.client.host.get_items(oid, filter={"state": state})
        transform = {
            "state": lambda x: self.app.color_error("ko") if x == "1" else self.app.color_error("ok"),
            "type": self.client.host.map_item_to_string,
        }
        headers = [
            "itemid",
            "type",
            "name",
            "delay",
            "units",
            "lastclock",
            "state",
            "lastvalue",
            "prevvalue",
        ]
        fields = [
            "itemid",
            "type",
            "name",
            "delay",
            "units",
            "lastclock",
            "state",
            "lastvalue",
            "prevvalue",
        ]
        self.app.render(res, headers=headers, fields=fields, transform=transform, maxsize=50)

    @ex(
        help=_("add host item"),
        description=_("add host item"),
        arguments=zabbix_args(
            [
                (
                    ["id"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("key name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["desc"],
                    {
                        "help": _("item description/comment"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["agent_type"],
                    {
                        "help": _(
                            "zabbix type. Can be: 0 - Zabbix agent, 1 - SNMPv1 agent, 2 - Zabbix trapper, "
                            "3 - simple check, 4 - SNMPv2 agent, 5 - Zabbix internal, 6 - SNMPv3 agent, "
                            "7 - Zabbix agent (active), 8 - Zabbix aggregate, 9 - web item, "
                            "10 - external check, 11 - database monitor, 12 - IPMI agent, "
                            "13 - SSH agent, 14 - TELNET agent, 15 - calculated, 16 - JMX agent."
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["value_type"],
                    {
                        "help": _(
                            "zabbix value_type. Can be: 0 - numeric float, 1 - character, 2 - log, "
                            "3 - numeric unsigned, 4 - text."
                        ),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["interfaceid"],
                    {
                        "help": _("zabbix host interfaceid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["item_key"],
                    {
                        "help": _("item key"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["delay"],
                    {
                        "help": _("check interval in seconds"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["history"],
                    {
                        "help": _("number of days to keep item history data"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["trends"],
                    {
                        "help": _("number of days to keep item trends data"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_item_add(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        agent_type = self.app.pargs.agent_type
        value_type = self.app.pargs.value_type
        interfaceid = self.app.pargs.interfaceid
        key = self.app.pargs.item_key
        delay = self.app.pargs.delay
        history = self.app.pargs.history
        trends = self.app.pargs.trends

        res = self.client.host.create_item(
            oid,
            name,
            desc,
            agent_type,
            value_type,
            interfaceid,
            key,
            delay,
            history,
            trends,
        )
        self.app.render({"msg": f"add host item {res}"})

    @ex(
        help=_("list host triggers"),
        description=_("list host triggers"),
        arguments=zabbix_args(
            [
                (
                    ["id"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_trigger_get(self):
        oid = self.app.pargs.id
        res = self.client.host.get_triggers(oid)
        headers = ["triggerid", "expression", "description", "state", "value"]
        fields = ["triggerid", "expression", "description", "state", "value"]
        self.app.render(res, headers=headers, fields=fields)

    @ex(
        help=_("enable host"),
        description=_("enable host"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_enable(self):
        oid = self.app.pargs.id
        self.client.host.update(oid, status=0)
        self.app.render({"msg": f"enable host {oid}"}, headers=["msg"])

    @ex(
        help=_("disable host"),
        description=_("disable host"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_disable(self):
        oid = self.app.pargs.id
        self.client.host.update(oid, status=1)
        self.app.render({"msg": f"disable host {oid}"}, headers=["msg"])

    @ex(
        help=_("delete host"),
        description=_("delete host"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_del(self):
        oid = self.app.pargs.id
        self.client.host.delete(oid)
        self.app.render({"msg": f"delete host {oid}"}, headers=["msg"])

    @ex(
        help=_("add group"),
        description=_("add group"),
        arguments=zabbix_pargs(
            [
                (
                    ["name"],
                    {
                        "help": _("group name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def hostgroup_add(self):
        name = self.app.pargs.name
        res = self.client.hostgroup.add(name)
        # self.app.render({"msg": "add group %s" % res["groupid"]})
        self.app.render({"msg": f"add hostgroup {res}"})  # groupids

    @ex(
        help=_("list groups"),
        description=_("list groups"),
        arguments=zabbix_pargs(
            [
                (
                    ["-id"],
                    {
                        "help": _("group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-field"],
                    {
                        "help": _("sort field"),
                        "action": "store",
                        "type": str,
                        "default": "groupid",
                    },
                ),
            ]
        ),
    )
    def hostgroup_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.hostgroup.get(oid)
            if self.is_output_text():
                self.app.render(res, details=True)
                self.c("\nhosts", "underline")
                res = self.client.hostgroup.hosts(oid)
                hosts = res.get("hosts")
                self.app.render(hosts, headers=["hostid", "name", "status"])
                self.c("\ntemplates", "underline")
                res = self.client.hostgroup.templates(oid)
                templates = res.get("templates")
                self.app.render(templates, headers=["templateid", "name", "status"])
            else:
                self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            field = self.app.pargs.field
            order = self.app.pargs.order
            count = self.client.hostgroup.list(countOutput=True)
            res = self.client.hostgroup.list(limit=size, offset=page, sortorder=order.upper(), sortfield=field)
            res = {
                "groups": res,
                "page": page,
                "count": size,
                "total": count,
                "sort": {"field": field, "order": order},
            }
            headers = ["id", "name", "hosts"]
            fields = ["groupid", "name", "hosts"]
            transform = {"hosts": len}
            self.app.render(
                res,
                key="groups",
                headers=headers,
                fields=fields,
                transform=transform,
                maxsize=60,
            )

    @ex(
        help=_("list hosts that belong to a group"),
        description=_("get hosts that belong to a group"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def hostgroup_get_hosts(self):
        oid = self.app.pargs.id
        res = self.client.hostgroup.hosts(oid)
        headers = ["id", "name", "status"]
        fields = ["hostid", "name", "status"]
        self.app.render(res, key="hosts", headers=headers, fields=fields)

    @ex(
        help=_("list templates that belong to a group"),
        description=_("get templates that belong to a group"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def hostgroup_get_templates(self):
        oid = self.app.pargs.id
        res = self.client.hostgroup.templates(oid)
        headers = ["id", "name", "status"]
        fields = ["templateid", "name", "status"]
        self.app.render(res, key="templates", headers=headers, fields=fields)

    @ex(
        help=_("update group"),
        description=_("update group"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("group name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def hostgroup_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        self.client.hostgroup.update(oid, name)
        self.app.render({"msg": f"update group {oid}"}, headers=["msg"])

    @ex(
        help=_("delete group"),
        description=_("delete group"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def hostgroup_del(self):
        oid = self.app.pargs.id
        self.client.hostgroup.delete(oid)
        self.app.render({"msg": f"delete group {oid}"}, headers=["msg"])

    @ex(
        help=_("add template"),
        description=_("add template"),
        arguments=zabbix_args(
            [
                (
                    ["file"],
                    {
                        "help": _("data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def template_add(self):
        data_file = self.app.pargs.file
        import xml.etree.ElementTree as et

        data = load_config(data_file)
        data = ensure_str(et.tostring(data))
        self.client.template.load(data)
        self.app.render({"msg": "add template"})

    @ex(
        help=_("list templates"),
        description=_("list templates"),
        arguments=zabbix_pargs(
            [
                (
                    ["-id"],
                    {
                        "help": _("template id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-field"],
                    {
                        "help": _("sort field"),
                        "action": "store",
                        "type": str,
                        "default": "name",
                    },
                ),
            ]
        ),
    )
    def template_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.template.get(oid)
            if self.is_output_text():
                self.app.render(res, details=True)
                self.c("\ngroups", "underline")
                res = self.client.template.groups(oid)
                groups = res.get("groups")
                self.app.render(groups, headers=["groupid", "name", "internal", "flags"])
                self.c("\nhosts", "underline")
                res = self.client.template.hosts(oid)
                hosts = res.get("hosts")
                self.app.render(hosts, headers=["hostid", "name", "status"])
            else:
                self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            field = self.app.pargs.field
            order = self.app.pargs.order
            count = self.client.template.list(countOutput=True)
            res = self.client.template.list(limit=size, offset=page, sortorder=order.upper(), sortfield=field)
            res = {
                "templates": res,
                "page": page,
                "count": size,
                "total": count,
                "sort": {"field": field, "order": order},
            }
            headers = ["id", "name", "host", "status"]
            fields = ["templateid", "name", "host", "status"]
            self.app.render(res, key="templates", headers=headers, fields=fields, maxsize=60)

    @ex(
        help=_("list hosts linked to the template"),
        description=_("list hosts linked to the template"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def template_get_hosts(self):
        oid = self.app.pargs.id
        res = self.client.template.hosts(oid)
        headers = ["id", "name", "status"]
        fields = ["hostid", "name", "status"]
        self.app.render(res, key="hosts", headers=headers, fields=fields)

    @ex(
        help=_("list groups the template belongs to"),
        description=_("list groups the template belongs to"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def template_get_groups(self):
        oid = self.app.pargs.id
        res = self.client.template.groups(oid)
        headers = ["id", "name", "internal", "flags"]
        fields = ["groupid", "name", "internal", "flags"]
        self.app.render(res, key="groups", headers=headers, fields=fields)

    @ex(
        help=_("delete template"),
        description=_("delete template"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("template id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def template_del(self):
        oid = self.app.pargs.id
        self.client.template.delete(oid)
        self.app.render({"msg": f"delete template {oid}"}, headers=["msg"])

    @ex(
        help=_("list interfaces"),
        description=_("list interfaces"),
        arguments=zabbix_pargs(
            [
                (
                    ["-id"],
                    {
                        "help": _("group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def interface_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.interface.get(oid)
            if self.is_output_text():
                self.app.render(res, details=True)
                self.c("\nhosts", "underline")
                res = self.client.interface.hosts(oid)
                hosts = res.get("hosts")
                self.app.render(hosts, headers=["hostid", "name", "status"])
            else:
                self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            order = self.app.pargs.order
            count = len(self.client.interface.list(countOutput=True))
            res = self.client.interface.list(limit=size, offset=page, sortorder=order.upper())
            res = {
                "interfaces": res,
                "page": page,
                "count": size,
                "total": count,
                "sort": {"order": order},
            }
            headers = [
                "id",
                "hostid",
                "main",
                "type",
                "useip",
                "ip",
                "dns",
                "port",
                "details",
            ]
            fields = [
                "interfaceid",
                "hostid",
                "main",
                "type",
                "useip",
                "ip",
                "dns",
                "port",
                "details",
            ]
            self.app.render(res, key="interfaces", headers=headers, fields=fields, maxsize=60)

    @ex(
        help=_("list hosts that use the interface"),
        description=_("list hosts that use the interface"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def interface_get_hosts(self):
        oid = self.app.pargs.id
        res = self.client.interface.hosts(oid)
        headers = ["hostid", "name", "status"]
        fields = ["hostid", "name", "status"]
        self.app.render(res, key="hosts", headers=headers, fields=fields)

    @ex(
        help=_("delete interface"),
        description=_("delete interface"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def interface_del(self):
        oid = self.app.pargs.id
        self.client.interface.delete(oid)
        self.app.render({"msg": f"delete interface {oid}"}, headers=["msg"])

    @ex(
        help=_("list alerts"),
        description=_("list alerts"),
        arguments=zabbix_pargs(
            [
                (
                    ["-id"],
                    {
                        "help": _("alert id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-field"],
                    {
                        "help": _("sort field"),
                        "action": "store",
                        "type": str,
                        "default": "clock",
                    },
                ),
            ]
        ),
    )
    def alert_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.alert.get(oid)

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            field = self.app.pargs.field
            order = self.app.pargs.order
            count = self.client.alert.list(countOutput=True)
            res = self.client.alert.list(limit=size, sortorder=order.upper(), sortfield=field, selectHosts=True)
            res = {
                "alerts": res,
                "page": page,
                "count": size,
                "total": count,
                "sort": {"field": field, "order": order},
            }
            headers = ["alertid", "actionid", "clock", "sendto", "subject", "hosts"]
            fields = ["alertid", "actionid", "clock", "sendto", "subject", "hosts"]
            transform = {
                "clock": lambda x: datetime.fromtimestamp(int(x)),
                "hosts": lambda x: ",".join([h["hostid"] for h in x]),
            }
            self.app.render(
                res,
                key="alerts",
                headers=headers,
                fields=fields,
                maxsize=30,
                transform=transform,
            )

    @ex(
        help=_("list it services"),
        description=_("list it services"),
        arguments=zabbix_pargs(
            [
                (
                    ["-id"],
                    {
                        "help": _("alert id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sla"],
                    {
                        "help": _("if true pirnt calculated sla"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
            ]
        ),
    )
    def it_service_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.it_service.get(oid)
            sla = self.client.it_service.get_sla(oid)
            for s in sla.get("sla", []):
                s["from"] = format_date(get_date_from_timestamp(s["from"]))
                s["to"] = format_date(get_date_from_timestamp(s["to"]))

            if self.is_output_text():
                dependencies = res.pop("dependencies", [])
                parent = res.pop("parent", {})
                alarms = res.pop("alarms", [])
                trigger = res.pop("trigger", {})
                if isinstance(parent, list):
                    parent = {}
                if isinstance(trigger, list):
                    trigger = {}

                self.app.render(res, details=True)

                self.c("\nsla", "underline")
                self.app.render(sla, details=True)
                self.c("\nparent", "underline")
                self.app.render(parent, details=True)
                self.c("\ndependencies", "underline")
                self.app.render(
                    dependencies,
                    headers=[
                        "linkid",
                        "serviceupid",
                        "servicedownid",
                        "soft",
                        "sortorder",
                        "serviceid",
                    ],
                )
                self.c("\ntrigger", "underline")
                self.app.render(trigger, details=True)
                self.c("\nalarms", "underline")
                self.app.render(alarms, headers=["servicealarmid", "clock", "value"])
            else:
                self.app.render(res, details=True)
        else:
            sla = str2bool(self.app.pargs.sla)
            page = self.app.pargs.page
            size = self.app.pargs.size
            count = self.client.it_service.list(countOutput=True)
            res = self.client.it_service.list(limit=size)
            headers = ["serviceid", "parentid", "name", "status", "trigger", "goodsla"]
            fields = [
                "serviceid",
                "parent.serviceid",
                "name",
                "status",
                "trigger.description",
                "goodsla",
            ]
            if sla is True:
                fields.append("sla")
                headers.append("sla")
                for r in res:
                    r["sla"] = dict_get(self.client.it_service.get_sla(r["serviceid"]), "sla.0.sla")
            for r in res:
                r["status"] = "OK" if r["status"] == "0" else "KO"
            res = {
                "services": res,
                "page": page,
                "count": size,
                "total": count,
                "sort": {"field": "serviceid", "order": "asc"},
            }

            transform = {"services.status": lambda x: "OK" if x == 0 else "KO"}
            self.app.render(
                res,
                key="services",
                headers=headers,
                fields=fields,
                maxsize=60,
                transform=transform,
            )

    @ex(
        help=_("list problems"),
        description=_("list problems"),
        arguments=zabbix_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("action id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def problem_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.problem.get(oid)

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            res = self.client.problem.list()
            headers = ["problemid", "name", "status"]
            fields = ["problemid", "name", "status"]
            self.app.render(res, headers=headers, fields=fields, maxsize=45)

    @ex(
        help=_("list proxys"),
        description=_("list proxys"),
        arguments=zabbix_pargs(
            [
                (
                    ["-id"],
                    {
                        "help": _("proxy id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-field"],
                    {
                        "help": _("sort field"),
                        "action": "store",
                        "type": str,
                        "default": "hostid",
                    },
                ),
            ]
        ),
    )
    def proxy_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.proxy.get(oid)
            if self.is_output_text():
                hosts = res.pop("hosts", [])
                self.app.render(res, details=True)
                self.c("\nhosts", "underline")
                headers = [
                    "id",
                    "proxy_hostid",
                    "host",
                    "name",
                    "status",
                    "maintenance_status",
                ]
                fields = [
                    "hostid",
                    "proxy_hostid",
                    "host",
                    "name",
                    "status",
                    "maintenance_status",
                ]
                self.app.render(hosts, headers=headers, fields=fields)
            else:
                self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            field = self.app.pargs.field
            order = self.app.pargs.order
            count = self.client.proxy.list(countOutput=True)
            res = self.client.proxy.list(limit=size, offset=page, sortorder=order.upper(), sortfield=field)
            res = {
                "proxys": res,
                "page": page,
                "count": size,
                "total": count,
                "sort": {"field": field, "order": order},
            }
            headers = [
                "proxyid",
                "description",
                "proxy_hostid",
                "host",
                "status",
                "available",
            ]
            fields = [
                "proxyid",
                "description",
                "proxy_hostid",
                "host",
                "status",
                "available",
            ]
            self.app.render(res, key="proxys", headers=headers, fields=fields)

    @ex(
        help=_("add proxy"),
        description=_("add proxy"),
        arguments=zabbix_args(
            [
                (
                    ["name"],
                    {
                        "help": _("proxy hostname"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def proxy_add(self):
        name = self.app.pargs.name
        res = self.client.proxy.create(name)
        self.app.render({"msg": f"add proxy {res['proxyids']}"})

    @ex(
        help=_("delete proxy"),
        description=_("delete proxy"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("proxy id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def proxy_del(self):
        oid = self.app.pargs.id
        self.client.proxy.delete(oid)
        self.app.render({"msg": f"delete proxy {oid}"}, headers=["msg"])

    ############
    # user
    ############

    @ex(
        help=_("add user"),
        description=_("add user"),
        arguments=zabbix_pargs(
            [
                (
                    ["username"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["passwd"],
                    {
                        "help": _("password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["usrgrpid"],
                    {
                        "help": _("user group id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["email"],
                    {
                        "help": _("user email"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def user_add(self):
        username = self.app.pargs.username
        passwd = self.app.pargs.passwd
        usrgrpid = self.app.pargs.usrgrpid
        email = self.app.pargs.email

        email_array = email.split(",")
        res = self.client.user.add(username, passwd, usrgrpid, email_array)
        # self.app.render({"msg": "add group %s" % res["userids"]})
        self.app.render({"msg": f"add user {res}"})  # userids

    @ex(
        help=_("update user"),
        description=_("update user"),
        arguments=zabbix_pargs(
            [
                (
                    ["user_id"],
                    {
                        "help": _("user id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["email"],
                    {
                        "help": _("users email - separated by comma"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["severity"],
                    {
                        "help": _("severity - 48 default (32 Disaster + 16 High)"),
                        "action": "store",
                        "type": int,
                        "default": 48,
                    },
                ),
            ]
        ),
    )
    def user_update(self):
        user_id = self.app.pargs.user_id
        email = self.app.pargs.email
        severity = self.app.pargs.severity

        email_array = None
        if email is not None:
            email_array = email.split(",")

        res = self.client.user.update(user_id, email_array, severity)
        # self.app.render({"msg": "add group %s" % res["userids"]})
        self.app.render({"msg": f"update user {res}"})  # userids

    @ex(
        help=_("list users"),
        description=_("list users"),
        arguments=zabbix_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("user id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def user_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.user.get(oid)

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            res = self.client.user.list()

            for user in res:
                if "usrgrps" in user:
                    usrgrps = user["usrgrps"]
                    usrgrps_name = ""
                    for usrgrp in usrgrps:
                        usrgrps_name += ", " + usrgrp["name"]
                    if len(usrgrps_name) > 0:
                        usrgrps_name = usrgrps_name[2:]

                    user["usrgrps_name"] = usrgrps_name

            headers = ["userid", "alias", "name", "surname", "user groups"]
            fields = ["userid", "alias", "name", "surname", "usrgrps_name"]
            self.app.render(res, headers=headers, fields=fields, maxsize=45)

    @ex(
        help=_("delete user"),
        description=_("delete user"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("user id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def user_del(self):
        oid = self.app.pargs.id
        self.client.user.delete(oid)
        self.app.render({"msg": f"delete user {oid}"}, headers=["msg"])

    ############
    # user group
    ############

    @ex(
        help=_("add usergroup"),
        description=_("add usergroup"),
        arguments=zabbix_pargs(
            [
                (
                    ["usergroupname"],
                    {
                        "help": _("usergroup name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["hostgroup_id"],
                    {
                        "help": _("hostgroup id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def usergroup_add(self):
        usergroupname = self.app.pargs.usergroupname
        hostgroup_id = self.app.pargs.hostgroup_id
        res = self.client.usergroup.add(usergroupname, hostgroup_id)
        # self.app.render({"msg": "add group %s" % res["usergroupids"]})
        self.app.render({"msg": f"add usergroup {res}"})  # usergroupids

    @ex(
        help=_("list user groups"),
        description=_("list user groups"),
        arguments=zabbix_pargs(
            [
                (
                    ["-id"],
                    {
                        "help": _("user group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-field"],
                    {
                        "help": _("sort field"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def usergroup_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.usergroup.get(oid)

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            field = self.app.pargs.field
            order = self.app.pargs.order
            count = self.client.usergroup.list(countOutput=True)
            res = self.client.usergroup.list(limit=size, offset=page, sortorder=order.upper(), sortfield=field)

            # list of user names
            for usrgrps in res:
                if "users" in usrgrps:
                    users = usrgrps["users"]
                    users_name = ""
                    for user in users:
                        users_name += ", " + user["alias"]
                    if len(users_name) > 0:
                        users_name = users_name[2:]

                    usrgrps["users_name"] = users_name

            res = {
                "groups": res,
                "page": page,
                "count": size,
                "total": count,
                "sort": {"field": field, "order": order},
            }

            headers = ["id", "name", "users"]
            fields = ["usrgrpid", "name", "users_name"]
            self.app.render(res, key="groups", headers=headers, fields=fields, maxsize=45)

    @ex(
        help=_("delete user group"),
        description=_("delete user group"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("user group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def usergroup_del(self):
        oid = self.app.pargs.id
        self.client.usergroup.delete(oid)
        self.app.render({"msg": f"delete user group {oid}"}, headers=["msg"])

    ############
    # action
    ############

    @ex(
        help=_("list actions"),
        description=_("list actions"),
        arguments=zabbix_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("action id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-eventsource"],
                    {
                        "help": _("eventsource id - 0 = trigger, 2 = auto registration"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def action_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            res = self.client.action.get(oid)
            self.app.render(res, details=True)
        else:
            lfilter = {}
            eventsource = getattr(self.app.pargs, "eventsource", None)
            if eventsource is not None:
                lfilter.update({"eventsource": eventsource})
            res = self.client.action.list(**lfilter)
            headers = ["actionid", "name", "status", "eventsource"]
            fields = ["actionid", "name", "status", "eventsource"]
            self.app.render(res, headers=headers, fields=fields, maxsize=45)

    @ex(
        help=_("add action"),
        description=_("add action"),
        arguments=zabbix_pargs(
            [
                (
                    ["name"],
                    {
                        "help": _("action name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["usrgrp_id"],
                    {
                        "help": _("usrgrp id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["hostgroup_id"],
                    {
                        "help": _("hostgroup id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def action_add(self):
        name = self.app.pargs.name
        usrgrp_id = self.app.pargs.usrgrp_id
        hostgroup_id = self.app.pargs.hostgroup_id
        res = self.client.action.add_trigger(name, usrgrp_id, hostgroup_id)
        self.app.render({"msg": f"add action {res}"})

    @ex(
        help=_("update action trigger"),
        description=_("update action trigger"),
        arguments=zabbix_pargs(
            [
                (
                    ["action_id"],
                    {
                        "help": _("action id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["hostgroup_id"],
                    {
                        "help": _("hostgroup id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["severity"],
                    {
                        "help": _("severity (number)"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def action_update_trigger(self):
        action_id = self.app.pargs.action_id
        hostgroup_id = self.app.pargs.hostgroup_id
        severity = self.app.pargs.severity
        res = self.client.action.update_trigger(action_id, hostgroup_id, severity)
        self.app.render({"msg": f"update action trigger {res}"})

    @ex(
        help=_("update action trigger"),
        description=_("update action trigger"),
        arguments=zabbix_pargs(
            [
                (
                    ["action_id"],
                    {
                        "help": _("action id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["severity"],
                    {
                        "help": _("severity (number)"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def action_update_trigger_severity(self):
        action_id = self.app.pargs.action_id
        severity = self.app.pargs.severity
        res = self.client.action.update_trigger_severity(action_id, severity)
        self.app.render({"msg": f"update action trigger severity {res}"})

    @ex(
        help=_("delete action"),
        description=_("delete action"),
        arguments=zabbix_pargs(
            [
                (
                    ["id"],
                    {
                        "help": _("action id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def action_del(self):
        oid = self.app.pargs.id
        self.client.action.delete(oid)
        self.app.render({"msg": f"delete action {oid}"}, headers=["msg"])
