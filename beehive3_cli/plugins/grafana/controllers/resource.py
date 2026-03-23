# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex
from beehive3_cli.translate import _
from beehive3_cli.core.controller import BaseController, PARGS


class GrafanaResourceController(BaseController):
    class Meta:
        label = "res_grafana"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("grafana orchestrator")
        help = _("grafana orchestrator")

        cmp = {"baseuri": "/v1.0/nrs/grafana", "subsystem": "resource"}

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
    # ----- FOLDER -----
    # -----------------
    @ex(
        help=_("get folders"),
        description=_("get folders"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("folder id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def folder_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/folders/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("folder")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/folders"
            self.app.log.debug(f"+++++ folder_get '{uri}' ")
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="folders", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("add folders"),
        description=_("add folders"),
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
                        "help": _("folder name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("folder desc"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def folder_add(self):
        container = self.app.pargs.container
        name = self.app.pargs.name
        desc = self.app.pargs.desc

        uri = f"{self.baseuri}/folders"
        self.app.log.debug(f"+++++ folder_add '{uri}' ")

        data_folder = {
            "container": container,
            "name": name,
        }

        if desc is not None:
            data_folder.update({"desc": desc})

        data = {"folder": data_folder}
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help=_("delete folders"),
        description=_("delete folders"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("resource folder id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def folder_delete(self):
        oid = self.app.pargs.id

        uri = f"{self.baseuri}/folders/{oid}"
        self.app.log.debug(f"+++++ folder_delete '{uri}' ")

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)

    # -----------------
    # ----- TEAM -----
    # -----------------
    @ex(
        help=_("get teams"),
        description=_("get teams"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("team id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def team_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/teams/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("team")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/teams"
            self.app.log.debug(f"+++++ team_get '{uri}' ")
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="teams", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("add teams"),
        description=_("add teams"),
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
                        "help": _("team name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("team desc"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def team_add(self):
        container = self.app.pargs.container
        name = self.app.pargs.name
        desc = self.app.pargs.desc

        uri = f"{self.baseuri}/teams"
        self.app.log.debug(f"+++++ team_add '{uri}' ")

        data_team = {
            "container": container,
            "name": name,
        }

        if desc is not None:
            data_team.update({"desc": desc})

        data = {"team": data_team}
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help=_("delete teams"),
        description=_("delete teams"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("resource team id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def team_delete(self):
        oid = self.app.pargs.id

        uri = f"{self.baseuri}/teams/{oid}"
        self.app.log.debug(f"+++++ team_delete '{uri}' ")

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)

    # ------------------------------
    # ----- ALERT NOTIFICATION -----
    # ------------------------------
    @ex(
        help=_("get alert_notifications"),
        description=_("get alert_notifications"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("alert_notification id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def alert_notification_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/alert_notifications/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("alert_notification")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/alert_notifications"
            self.app.log.debug(f"+++++ alert_notification_get '{uri}' ")
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="alert_notifications",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    @ex(
        help=_("add alert_notifications"),
        description=_("add alert_notifications"),
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
                        "help": _("alert_notification name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["email"],
                    {
                        "help": _("alert_notification email"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("alert_notification desc"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def alert_notification_add(self):
        container = self.app.pargs.container
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        email = self.app.pargs.email

        uri = f"{self.baseuri}/alert_notifications"
        self.app.log.debug(f"+++++ alert_notification_add '{uri}' ")

        data_alert_notification = {
            "container": container,
            "name": name,
            "email": email,
        }

        if desc is not None:
            data_alert_notification.update({"desc": desc})

        data = {"alert_notification": data_alert_notification}
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help=_("delete alert_notifications"),
        description=_("delete alert_notifications"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("resource alert_notification id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def alert_notification_delete(self):
        oid = self.app.pargs.id

        uri = f"{self.baseuri}/alert_notifications/{oid}"
        self.app.log.debug(f"+++++ alert_notification_delete '{uri}' ")

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)
