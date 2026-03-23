# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex
from beecell.simple import merge_list
from beedrones.elk.client_kibana import KibanaManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS, PAGINATION_ARGS
from beehive3_cli.core.util import load_environment_config
from beehive3_cli.main import CliManager
from beehive3_cli.translate import _


def kibana_args(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": _("kibana platform reference label"),
            },
        )
    ]
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, orchestrator_args, *list_args)
    return res


class KibanaPlatformController(BaseController):
    headers = ["id", "name"]
    entity_class = None

    class Meta:
        stacked_on = "platform"
        stacked_type = "nested"
        label = "kibana"
        description = _("kibana platform management")
        help = _("kibana platform  management")

    def pre_command_run(self):
        super().pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("kibana", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No kibana default platform is available for this environment. Select another environment"
                )

        if label not in orchestrators:
            raise Exception(f"Valid label are: {', '.join(orchestrators.keys())}")
        self.conf = orchestrators.get(label)


        proto = self.conf.get("proto")
        host = self.conf.get("hosts")[0]
        port = self.conf.get("port")
        path = self.conf.get("path")
        uri = f"{proto}://{host}:{port}{path}"

        self.app.log.debug(f"pre_command_run - uri: {uri}")

        user = self.conf.get("user")
        password = self.conf.get("pwd")
        self.client = KibanaManager(uri, user, password)

    @ex(help=_("ping kibana"), description=_("ping kibana"), arguments=kibana_args())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(
        help=_("get kibana version"),
        description=_("get kibana version"),
        arguments=kibana_args(),
    )
    def version(self):
        res = self.client.version()
        self.app.render(res, headers=["version"])

    # -----------------
    # ----- SPACE -----
    # -----------------
    @ex(
        help=_("add space"),
        description=_("add space"),
        arguments=kibana_args(
            [
                (
                    ["id"],
                    {
                        "help": _("space id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("space name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-description"],
                    {
                        "help": _("space description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-color"],
                    {
                        "help": _("space color"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-initials"],
                    {
                        "help": _("space initials"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def space_add(self):
        l_id = self.app.pargs.id
        name = self.app.pargs.name
        description = self.app.pargs.description
        color = self.app.pargs.color
        initials = self.app.pargs.initials
        res = self.client.space.add(l_id, name, description=description, color=color, initials=initials)
        self.app.render(
            res,
            headers=[
                "id",
                "name",
                "description",
                "color",
                "disabledFeatures",
                "_reserved",
            ],
        )

    @ex(
        help=_("delete space"),
        description=_("delete space"),
        arguments=kibana_args(
            [
                (
                    ["id"],
                    {
                        "help": _("space id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def space_del(self):
        space_id = self.app.pargs.id
        self.client.space.delete(space_id)
        self.app.render({"msg": f"delete space {space_id}"}, headers=["msg"])

    @ex(
        help=_("get space"),
        description=_("get space"),
        arguments=kibana_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("space id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def space_get(self):
        space_id = self.app.pargs.id
        if space_id is not None:
            res = self.client.space.get(space_id)

            if self.is_output_text():
                self.app.log.debug("is_output_text")
                # res.pop('related', None)
                # res.pop('summary_fields', None)
                # job_env = res.pop('job_env', {})
                self.app.render(res, details=True)
            else:
                self.app.log.info("not is_output_text")
                self.app.render(res, details=True)
        else:
            res = self.client.space.list()
            self.app.render(
                res,
                headers=[
                    "id",
                    "name",
                    "description",
                    "color",
                    "disabledFeatures",
                    "_reserved",
                ],
            )

    # ----------------
    # ----- ROLE -----
    # ----------------
    @ex(
        help=_("add role"),
        description=_("add role"),
        arguments=kibana_args(
            [
                (
                    ["name"],
                    {
                        "help": _("role name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["indice"],
                    {"help": _("indice"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["space_id"],
                    {
                        "help": _("space_id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def role_add(self):
        role_name = self.app.pargs.name
        indice = self.app.pargs.indice
        space_id = self.app.pargs.space_id
        res = self.client.role.add(role_name, indice, space_id)
        self.app.render(res, headers=["name", "indice", "space_id"])

    @ex(
        help=_("delete role"),
        description=_("delete role"),
        arguments=kibana_args(
            [
                (
                    ["name"],
                    {
                        "help": _("role name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def role_del(self):
        role_name = self.app.pargs.name
        self.client.role.delete(role_name)
        self.app.render({"msg": f"delete role {role_name}"}, headers=["msg"])

    @ex(
        help=_("get role"),
        description=_("get role"),
        arguments=kibana_args(
            [
                (
                    ["-name"],
                    {
                        "help": _("role name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def role_get(self):
        role_name = self.app.pargs.name
        if role_name is not None:
            res = self.client.role.get(role_name)

            if self.is_output_text():
                self.app.log.debug("is_output_text")
                # res.pop('related', None)
                # res.pop('summary_fields', None)
                # job_env = res.pop('job_env', {})
                self.app.render(res, details=True)
            else:
                self.app.log.info("not is_output_text")
                self.app.render(res, details=True)
        else:
            res = self.client.role.list()
            self.app.render(res, headers=["name", "indice", "space_id"])

    # -----------------
    # --- DASHBOARD ---
    # -----------------
    @ex(
        help=_("get space dashboard"),
        description=_("get space dashboard"),
        arguments=kibana_args(
            [
                (
                    ["id"],
                    {
                        "help": _("space id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def space_dashboard_get(self):
        space_id = self.app.pargs.id
        res = self.client.space.get_dashboard(space_id)
        self.app.render(
            res["dashboards"],
            headers=[
                "id",
                "namespaces",
                "attributes.title",
                "updated_at",
            ],
        )

    @ex(
        help=_("get dashboard"),
        description=_("get dashboard"),
        arguments=kibana_args(
            [
                (
                    ["-search"],
                    {
                        "help": _("dashboard to search"),
                        "action": "store",
                        "type": str,
                        "default": "*",
                    },
                ),
                (
                    ["-spaceid"],
                    {
                        "help": _("space id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dashboard_get(self):
        dashboard_to_search = self.app.pargs.search
        space_id = self.app.pargs.spaceid
        size = self.app.pargs.size

        headers = ["id", "title", "namespaces", "updated_at"]
        fields = [
            "id",
            "attributes.title",
            "namespaces",
            "updated_at",
        ]

        if dashboard_to_search is not None:
            from urllib.parse import unquote_plus

            dashboard_to_search = unquote_plus(dashboard_to_search)

        res = self.client.space.get_dashboard(space_id, dashboard_to_search, size)
        self.app.render(
            res,
            key="dashboards",
            headers=headers,
            fields=fields,
            maxsize=40,
        )

    @ex(
        help=_("add dashboard"),
        description=_("add dashboard"),
        arguments=kibana_args(
            [
                (
                    ["search"],
                    {
                        "help": _("dashboard to search"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["space_id_from"],
                    {
                        "help": _("space id from"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["space_id_to"],
                    {
                        "help": _("space id to"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def dashboard_add(self):
        dashboard_to_search = self.app.pargs.search
        space_id_from = self.app.pargs.space_id_from
        space_id_to = self.app.pargs.space_id_to

        if dashboard_to_search is not None:
            from urllib.parse import unquote_plus

            dashboard_to_search = unquote_plus(dashboard_to_search)

        res = self.client.space.add_dashboard(space_id_from, dashboard_to_search, space_id_to, index_pattern=None)
        self.app.render(res)

    @ex(
        help=_("del space dashboard"),
        description=_("del space dashboard"),
        arguments=kibana_args(
            [
                (
                    ["search"],
                    {
                        "help": _("dashboard to search"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["space_id"],
                    {
                        "help": _("space id"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def space_dashboard_del(self):
        dashboard_to_search = self.app.pargs.search
        space_id = self.app.pargs.space_id

        if dashboard_to_search is not None:
            from urllib.parse import unquote_plus

            dashboard_to_search = unquote_plus(dashboard_to_search)

        self.client.space.delete_space_dashboard(dashboard_to_search, space_id)

    @ex(
        help=_("get dashboard for definition"),
        description=_("get dashboard for definition"),
        arguments=kibana_args([]),
    )
    def dashboard_for_definition_get(self):
        dashboard_to_search = "*"
        space_id = "template"
        size = 100

        title_list = []
        res = self.client.space.get_dashboard(space_id, dashboard_to_search, size)
        dashboards = res["dashboards"]
        for dashboard in dashboards:
            title: str = dashboard["attributes"]["title"]
            filebeat = title[1 : title.index("]")]
            if filebeat not in title_list:
                title_list.append(filebeat)

        title_list.sort()
        self.app.render(title_list)

        defs = []
        for title in title_list:
            name = title.lower().replace(" ", "-")
            logtype = title[title.index(" ") + 1 :].lower().replace(" ", "-")
            obj = {"name": name, "title": title, "logtype": logtype}
            defs.append(obj)

        # self.app.format = "yaml"
        cli_manager: CliManager = self.app
        cli_manager.render(defs)

    @ex(
        help=_("delete dashboard"),
        description=_("delete dashboard"),
        arguments=kibana_args(
            [
                (
                    ["space_id"],
                    {
                        "help": _("space id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["dashboard_id"],
                    {
                        "help": _("dashboard id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dashboard_del(self):
        space_id = self.app.pargs.space_id
        dashboard_id = self.app.pargs.dashboard_id
        self.client.space.delete_dashboard(space_id, dashboard_id)
        self.app.render({"msg": f"delete dashboard {dashboard_id}"}, headers=["msg"])
