# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive3_cli.core.controller import BaseController, PARGS
from cement import ex


class ZabbixResourceController(BaseController):
    class Meta:
        label = "res_zabbix"
        stacked_on = "base"
        stacked_type = "nested"
        description = "zabbix orchestrator"
        help = "zabbix orchestrator"

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
        super(ZabbixResourceController, self).pre_command_run()
        self.configure_cmp_api_client()

    # -----------------
    # --- HOST GROUP --
    # -----------------
    @ex(
        help="get hostgroups",
        description="get hostgroups",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "hostgroup id",
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
            uri = "%s/hostgroups/%s" % (self.baseuri, oid)
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
            uri = "%s/hostgroups" % self.baseuri
            self.app.log.debug("+++++ hostgroup_get '%s' " % uri)
            res = self.cmp_get(uri, data=data)

            headers = self._meta.headers
            fields = self._meta.fields
            self.app.render(res, key="hostgroups", headers=headers, fields=fields)

    @ex(
        help="add hostgroups",
        description="add hostgroups",
        arguments=PARGS(
            [
                (
                    ["container"],
                    {
                        "help": "container",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": "hostgroup name",
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

        uri = "%s/hostgroups" % (self.baseuri)
        self.app.log.debug("+++++ hostgroup_add '%s' " % uri)

        data_hostgroup = {
            "container": container,
            "name": name,
            "desc": "Zabbix hostgroup",
        }

        data = {"hostgroup": data_hostgroup}
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help="delete hostgroups",
        description="delete hostgroups",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "resource hostgroup id",
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

        uri = "%s/hostgroups/%s" % (self.baseuri, oid)
        self.app.log.debug("+++++ hostgroup_delete '%s' " % uri)

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)

    # -----------------
    # ----- HOST ------
    # -----------------
    @ex(
        help="get hosts",
        description="get hosts",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "host id",
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
            uri = "%s/hosts/%s" % (self.baseuri, oid)
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
            uri = "%s/hosts" % self.baseuri
            self.app.log.debug("+++++ host_get '%s' " % uri)
            res = self.cmp_get(uri, data=data)

            headers = self._meta.headers
            fields = self._meta.fields
            self.app.render(res, key="hosts", headers=headers, fields=fields)

    @ex(
        help="add hosts",
        description="add hosts",
        arguments=PARGS(
            [
                (
                    ["container"],
                    {
                        "help": "container",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": "host name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["hostgroup_id"],
                    {
                        "help": "hostgroup id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["ip_addr"],
                    {
                        "help": "ip addr",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["port"],
                    {
                        "help": "port",
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

        uri = "%s/hosts" % (self.baseuri)
        self.app.log.debug("+++++ host_add '%s' " % uri)

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
        help="delete hosts",
        description="delete hosts",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "resource host id",
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

        uri = "%s/hosts/%s" % (self.baseuri, oid)
        self.app.log.debug("+++++ host_delete '%s' " % uri)

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)

    # -----------------
    # --- USER GROUP --
    # -----------------
    @ex(
        help="get usergroups",
        description="get usergroups",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "usergroup id",
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
            uri = "%s/usergroups/%s" % (self.baseuri, oid)
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
            uri = "%s/usergroups" % self.baseuri
            self.app.log.debug("+++++ usergroup_get '%s' " % uri)
            res = self.cmp_get(uri, data=data)

            headers = self._meta.headers + ["users_email", "user_severities"]
            fields = self._meta.fields + ["users_email", "user_severities"]
            self.app.render(res, key="usergroups", headers=headers, fields=fields)

    @ex(
        help="add usergroups",
        description="add usergroups",
        arguments=PARGS(
            [
                (
                    ["container"],
                    {
                        "help": "container",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": "usergroup name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["hostgroup_id"],
                    {
                        "help": "hostgroup id",
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

        uri = "%s/usergroups" % (self.baseuri)
        self.app.log.debug("+++++ usergroup_add '%s' " % uri)

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
        help="delete usergroups",
        description="delete usergroups",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "resource usergroup id",
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

        uri = "%s/usergroups/%s" % (self.baseuri, oid)
        self.app.log.debug("+++++ usergroup_delete '%s' " % uri)

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)

    # -----------------
    # ----- ACTION ----
    # -----------------
    @ex(
        help="get actions",
        description="get actions",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "action id",
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
            uri = "%s/actions/%s" % (self.baseuri, oid)
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
            uri = "%s/actions" % self.baseuri
            self.app.log.debug("+++++ action_get '%s' " % uri)
            res = self.cmp_get(uri, data=data)

            headers = self._meta.headers + ["severity"] + ["eventsource"]
            fields = self._meta.fields + ["severity"] + ["attributes.eventsource"]
            transform = {"attributes.eventsource": lambda x: self.desc_event_source(x)}
            self.app.render(res, key="actions", headers=headers, fields=fields, transform=transform)

    def desc_event_source(self, val):
        # self.app.log.debug("+++++ desc_event_source '%s' " % val)
        if val == "0":
            return "trigger"
        elif val == "1":
            return "discovery rule"
        elif val == "2":
            return "autoregistration"
        elif val == "3":
            return "internal event"
        elif val == "4":
            return "status update"
        return val

    @ex(
        help="add actions",
        description="add actions",
        arguments=PARGS(
            [
                (
                    ["container"],
                    {
                        "help": "container",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": "action name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["usrgrp_id"],
                    {
                        "help": "usrgrp id",
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["hostgroup_id"],
                    {
                        "help": "hostgroup id",
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

        uri = "%s/actions" % (self.baseuri)
        self.app.log.debug("+++++ action_add '%s' " % uri)

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
        help="delete actions",
        description="delete actions",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "resource action id",
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

        uri = "%s/actions/%s" % (self.baseuri, oid)
        self.app.log.debug("+++++ action_delete '%s' " % uri)

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)
