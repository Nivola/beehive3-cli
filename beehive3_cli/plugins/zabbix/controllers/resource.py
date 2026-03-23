# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex
from beehive3_cli.core.controller import BaseController, PARGS
from beehive3_cli.translate import _


class ZabbixResourceController(BaseController):
    class Meta:
        label = "res_zabbix"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("zabbix orchestrator")
        help = _("zabbix orchestrator")

        cmp = {"baseuri": "/v1.0/nrs/zabbix", "subsystem": "resource"}

        headers = [
            "id",
            "uuid",
            "name",
            "desc",
            "ext_id",
            "parent",
            "container",
            "state",
        ]
        fields = [
            "id",
            "uuid",
            "name",
            "desc",
            "ext_id",
            "parent",
            "container",
            "state",
        ]

    def pre_command_run(self):
        super().pre_command_run()
        self.configure_cmp_api_client()

    # -----------------
    # --- HOST GROUP --
    # -----------------
    @ex(
        help=_("get hostgroups"),
        description=_("get hostgroups"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("hostgroup id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def hostgroup_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/hostgroups/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("hostgroup")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/hostgroups"
            self.app.log.debug(f"+++++ hostgroup_get '{uri}' ")
            res = self.cmp_get(uri, data=data)

            headers = self._meta.headers
            fields = self._meta.fields
            self.app.render(res, key="hostgroups", headers=headers, fields=fields)

    @ex(
        help=_("add hostgroups"),
        description=_("add hostgroups"),
        arguments=PARGS(
            [
                (
                    ["container"],
                    {
                        "help": _("container"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("hostgroup name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def hostgroup_add(self):
        container = self.app.pargs.container
        name = self.app.pargs.name

        uri = f"{self.baseuri}/hostgroups"
        self.app.log.debug(f"+++++ hostgroup_add '{uri}' ")

        data_hostgroup = {
            "container": container,
            "name": name,
            "desc": "Zabbix hostgroup",
        }

        data = {"hostgroup": data_hostgroup}
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help=_("delete hostgroups"),
        description=_("delete hostgroups"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("resource hostgroup id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def hostgroup_delete(self):
        oid = self.app.pargs.id

        uri = f"{self.baseuri}/hostgroups/{oid}"
        self.app.log.debug(f"+++++ hostgroup_delete '{uri}' ")

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)

    # -----------------
    # ----- HOST ------
    # -----------------
    @ex(
        help=_("get hosts"),
        description=_("get hosts"),
        arguments=PARGS(
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
            ]
        ),
    )
    def host_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/hosts/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("host")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/hosts"
            self.app.log.debug(f"+++++ host_get '{uri}' ")
            res = self.cmp_get(uri, data=data)

            headers = self._meta.headers
            fields = self._meta.fields
            self.app.render(res, key="hosts", headers=headers, fields=fields)

    @ex(
        help=_("add hosts"),
        description=_("add hosts"),
        arguments=PARGS(
            [
                (
                    ["container"],
                    {
                        "help": _("container"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("host name"),
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
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ip_addr"],
                    {
                        "help": _("ip addr"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["port"],
                    {
                        "help": _("port"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_add(self):
        container = self.app.pargs.container
        name = self.app.pargs.name
        hostgroup_id = self.app.pargs.hostgroup_id
        ip_addr = self.app.pargs.ip_addr
        port = self.app.pargs.port

        uri = f"{self.baseuri}/hosts"
        self.app.log.debug(f"+++++ host_add '{uri}' ")

        data_host = {
            "container": container,
            "name": name,
            "desc": "Zabbix host",
            "interfaces": [{"ip_addr": ip_addr, "port": port}],
            "groups": [hostgroup_id],
            "templates": [],
        }

        data = {"host": data_host}
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help=_("delete hosts"),
        description=_("delete hosts"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("resource host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def host_delete(self):
        oid = self.app.pargs.id

        uri = f"{self.baseuri}/hosts/{oid}"
        self.app.log.debug(f"+++++ host_delete '{uri}' ")

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)

    # -----------------
    # --- USER GROUP --
    # -----------------
    @ex(
        help=_("get usergroups"),
        description=_("get usergroups"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("usergroup id"),
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
            uri = f"{self.baseuri}/usergroups/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("usergroup")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/usergroups"
            self.app.log.debug(f"+++++ usergroup_get '{uri}' ")
            res = self.cmp_get(uri, data=data)

            headers = self._meta.headers + ["users_email", "user_severities"]
            fields = self._meta.fields + ["users_email", "user_severities"]
            self.app.render(res, key="usergroups", headers=headers, fields=fields)

    @ex(
        help=_("add usergroups"),
        description=_("add usergroups"),
        arguments=PARGS(
            [
                (
                    ["container"],
                    {
                        "help": _("container"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
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
        container = self.app.pargs.container
        name = self.app.pargs.name
        hostgroup_id = self.app.pargs.hostgroup_id

        uri = f"{self.baseuri}/usergroups"
        self.app.log.debug(f"+++++ usergroup_add '{uri}' ")

        data_usergroup = {
            "container": container,
            "name": name,
            "hostgroup_id": hostgroup_id,
            "desc": "Zabbix usergroup",
        }

        data = {"usergroup": data_usergroup}
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help=_("delete usergroups"),
        description=_("delete usergroups"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("resource usergroup id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def usergroup_delete(self):
        oid = self.app.pargs.id

        uri = f"{self.baseuri}/usergroups/{oid}"
        self.app.log.debug(f"+++++ usergroup_delete '{uri}' ")

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)

    # -----------------
    # ----- ACTION ----
    # -----------------
    @ex(
        help=_("get actions"),
        description=_("get actions"),
        arguments=PARGS(
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
    def action_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/actions/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("action")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/actions"
            self.app.log.debug(f"+++++ action_get '{uri}' ")
            res = self.cmp_get(uri, data=data)

            headers = self._meta.headers + ["severity"] + ["eventsource"]
            fields = self._meta.fields + ["severity"] + ["attributes.eventsource"]
            transform = {"attributes.eventsource": self.desc_event_source}
            self.app.render(res, key="actions", headers=headers, fields=fields, transform=transform)

    def desc_event_source(self, val):
        # self.app.log.debug("+++++ desc_event_source '%s' " % val)
        if val == "0":
            return "trigger"
        if val == "1":
            return "discovery rule"
        if val == "2":
            return "autoregistration"
        if val == "3":
            return "internal event"
        if val == "4":
            return "status update"
        return val

    @ex(
        help=_("add actions"),
        description=_("add actions"),
        arguments=PARGS(
            [
                (
                    ["container"],
                    {
                        "help": _("container"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
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
            ]
        ),
    )
    def action_add(self):
        container = self.app.pargs.container
        name = self.app.pargs.name
        usrgrp_id = self.app.pargs.usrgrp_id
        hostgroup_id = self.app.pargs.hostgroup_id

        uri = f"{self.baseuri}/actions"
        self.app.log.debug(f"+++++ action_add '{uri}' ")

        data_action = {
            "container": container,
            "name": name,
            "usrgrp_id": usrgrp_id,
            "hostgroup_id": hostgroup_id,
            "desc": "Zabbix action",
        }

        data = {"action": data_action}
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help=_("delete actions"),
        description=_("delete actions"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("resource action id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def action_delete(self):
        oid = self.app.pargs.id

        uri = f"{self.baseuri}/actions/{oid}"
        self.app.log.debug(f"+++++ action_delete '{uri}' ")

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)
