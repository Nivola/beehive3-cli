# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2026 CSI-Piemonte

from json import loads
from cement import ex
from beecell.simple import merge_list
from beedrones.grafana.client_grafana import GrafanaManager
from beehive3_cli.core.util import load_environment_config
from beehive3_cli.core.controller import BaseController, BASE_ARGS, PAGINATION_ARGS
from beehive3_cli.translate import _


def grafana_args(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": _("grafana platform reference label"),
            },
        )
    ]
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, orchestrator_args, *list_args)
    return res


class GrafanaPlatformController(BaseController):
    headers = ["id", "name"]
    entity_class = None

    class Meta:
        stacked_on = "platform"
        stacked_type = "nested"
        label = "grafana"
        description = _("grafana platform management")
        help = _("grafana platform  management")

    def pre_command_run(self):
        super().pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("grafana", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No grafana default platform is available for this environment. Select another environment"
                )

        if label not in orchestrators:
            raise Exception(f"Valid label are: {', '.join(orchestrators.keys())}")
        self.conf = orchestrators.get(label)

        # print("-+-+- self.conf: " + str(self.conf))
        grafana_host = self.conf.get("hosts")[0]
        grafana_port = self.conf.get("port")
        grafana_token = self.conf.get("token")
        grafana_user = self.conf.get("user")
        grafana_pwd = self.conf.get("pwd")
        grafana_protocol = self.conf.get("proto", "http")

        if grafana_token is not None:
            self.client = GrafanaManager(
                host=grafana_host,
                port=grafana_port,
                protocol=grafana_protocol,
                token=grafana_token,
            )
        else:
            self.client = GrafanaManager(
                host=grafana_host,
                port=grafana_port,
                protocol=grafana_protocol,
                username=grafana_user,
                pwd=grafana_pwd,
            )

    @ex(help=_("ping grafana"), description=_("ping grafana"), arguments=grafana_args())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(
        help=_("get grafana version"),
        description=_("get grafana version"),
        arguments=grafana_args(),
    )
    def version(self):
        res = self.client.version()
        self.app.render(res, headers=["version"])

    # -----------------
    # ---- FOLDER -----
    # -----------------
    @ex(
        help=_("add folder"),
        description=_("add folder"),
        arguments=grafana_args(
            [
                (
                    ["name"],
                    {
                        "help": _("folder name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def folder_add(self):
        name = self.app.pargs.name
        res = self.client.folder.add(folder_name=name)
        self.app.render(res, headers=["id", "uid", "title"])

    @ex(
        help=_("delete folder"),
        description=_("delete folder"),
        arguments=grafana_args(
            [
                (
                    ["uid"],
                    {
                        "help": _("folder uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def folder_del(self):
        folder_uid = self.app.pargs.uid
        self.client.folder.delete(folder_uid)
        self.app.render({"msg": f"delete folder {folder_uid}"}, headers=["msg"])

    @ex(
        help=_("get folder"),
        description=_("get folder"),
        arguments=grafana_args(
            [
                (
                    ["-uid"],
                    {
                        "help": _("folder uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("folder name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def folder_get(self):
        folder_uid = self.app.pargs.uid
        folder_name = self.app.pargs.name
        if folder_uid is not None:
            res = self.client.folder.get(folder_uid)
            self.app.render(res, details=True)

        elif folder_name is not None:
            res = self.client.folder.search(folder_name)
            self.app.render(res, headers=["id", "uid", "title"])

        else:
            res = self.client.folder.list()
            self.app.render(res, headers=["id", "uid", "title"])

    @ex(
        help=_("get folder dashboard"),
        description=_("get folder dashboard"),
        arguments=grafana_args(
            [
                (
                    ["id"],
                    {
                        "help": _('folder uid or "general" for general folder'),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-search"],
                    {
                        "help": _("dashboard search query"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def folder_dashboard_get(self):
        folder_uid = self.app.pargs.id
        search = self.app.pargs.search
        if folder_uid == "general":
            folder_id = "0"
        else:
            res_folder = self.client.folder.get(folder_uid)
            folder_id = res_folder["id"]
        res = self.client.dashboard.list(folder_id, search)
        self.app.render(
            res["dashboards"],
            headers=["id", "uid", "title", "uri", "url", "type", "tags", "isStarred"],
        )

    @ex(
        help=_("add folder permission"),
        description=_("add folder permission"),
        arguments=grafana_args(
            [
                (
                    ["uid"],
                    {
                        "help": _("folder uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-team_viewer"],
                    {
                        "help": _("team id viewer"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-team_editor"],
                    {
                        "help": _("team id editor"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def folder_permission_add(self):
        uid = self.app.pargs.uid
        team_viewer = self.app.pargs.team_viewer
        team_editor = self.app.pargs.team_editor
        res = self.client.folder.add_permission(folder_uid=uid, team_id_viewer=team_viewer, team_id_editor=team_editor)
        self.app.render(res, details=True)

    @ex(
        help=_("add folder permission"),
        description=_("add folder permission"),
        arguments=grafana_args(
            [
                (
                    ["uid"],
                    {
                        "help": _("folder uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-team_viewer"],
                    {
                        "help": _("team id viewer"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["-team_editor"],
                    {
                        "help": _("team id editor"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def folder_permission_get(self):
        uid = self.app.pargs.uid
        res = self.client.folder.get_permissions(folder_uid=uid)
        self.app.render(res, headers=["team", "permissionName", "updated"])

    # ---------------
    # ---- TEAM -----
    # ---------------
    @ex(
        help=_("add team"),
        description=_("add team"),
        arguments=grafana_args(
            [
                (
                    ["name"],
                    {
                        "help": _("team name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def team_add(self):
        name = self.app.pargs.name
        res = self.client.team.add(team_name=name)
        self.app.render(res, headers=["teamId"])

    @ex(
        help=_("delete team"),
        description=_("delete team"),
        arguments=grafana_args(
            [
                (
                    ["id"],
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
    def team_del(self):
        team_id = self.app.pargs.id
        self.client.team.delete(team_id)
        self.app.render({"msg": f"delete team {team_id}"}, headers=["msg"])

    @ex(
        help=_("get team"),
        description=_("get team"),
        arguments=grafana_args(
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
                (
                    ["-name"],
                    {
                        "help": _("team name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def team_get(self):
        team_id = self.app.pargs.id
        team_name = self.app.pargs.name
        page = self.app.pargs.page
        size = self.app.pargs.size

        # fix loop requests
        if page == 0:
            page = 1

        if team_id is not None:
            res = self.client.team.get(team_id)
            self.app.render(res, details=True)
        elif team_name is not None:
            res = self.client.team.get_by_name(team_name)
            self.app.render(res, headers=["id", "uid", "name", "memberCount"])
        else:
            res = self.client.team.list(page=page, size=size)
            self.app.render(res, headers=["id", "uid", "name", "memberCount"])
            # self.app.render(res, details=True)

    @ex(
        help=_("get user of team"),
        description=_("get user of team"),
        arguments=grafana_args(
            [
                (
                    ["id"],
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
    def team_user_get(self):
        team_id = self.app.pargs.id
        res = self.client.team.get_users(team_id)
        self.app.render(res, headers=["teamId", "userId", "email", "login"])

    @ex(
        help=_("add user to team"),
        description=_("add user to team"),
        arguments=grafana_args(
            [
                (
                    ["team_id"],
                    {
                        "help": _("team id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["user_id"],
                    {
                        "help": _("user id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def team_user_add(self):
        team_id = self.app.pargs.team_id
        user_id = self.app.pargs.user_id
        message = self.client.team.add_user(team_id, user_id)
        self.app.render({"msg": f"{message}"}, headers=["message"])

    @ex(
        help=_("delete user from team"),
        description=_("delete user from team"),
        arguments=grafana_args(
            [
                (
                    ["team_id"],
                    {
                        "help": _("team id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
                (
                    ["user_id"],
                    {
                        "help": _("user id"),
                        "action": "store",
                        "type": int,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def team_user_del(self):
        team_id = self.app.pargs.team_id
        user_id = self.app.pargs.user_id
        message = self.client.team.del_user(team_id, user_id)
        self.app.render({"msg": f"{message}"}, headers=["message"])

    # ---------------
    # ---- USER -----
    # ---------------
    @ex(
        help=_("add user"),
        description=_("add user"),
        arguments=grafana_args(
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
                (
                    ["-email"],
                    {"help": _("email"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-login"],
                    {
                        "help": _("user login"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-password"],
                    {
                        "help": _("password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def user_add(self):
        name = self.app.pargs.name
        email = self.app.pargs.email
        login = self.app.pargs.login
        password = self.app.pargs.password
        res = self.client.user.add(name=name, email=email, login=login, password=password)
        self.app.render(res, headers=["id"])

    @ex(
        help=_("update user"),
        description=_("update user"),
        arguments=grafana_args(
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
                (
                    ["-name"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-email"],
                    {"help": _("email"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-login"],
                    {
                        "help": _("user login"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def user_update(self):
        user_id = self.app.pargs.id
        name = self.app.pargs.name
        email = self.app.pargs.email
        login = self.app.pargs.login
        res = self.client.user.update(user_id=user_id, name=name, email=email, login=login)
        self.app.render(res, headers=["id"])

    @ex(
        help=_("delete user"),
        description=_("delete user"),
        arguments=grafana_args(
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
        user_id = self.app.pargs.id
        self.client.user.delete(user_id)
        self.app.render({"msg": f"delete user {user_id}"}, headers=["msg"])

    @ex(
        help=_("get user"),
        description=_("get user"),
        arguments=grafana_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("user uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
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
        user_id = self.app.pargs.id
        login_or_email = self.app.pargs.name
        page = self.app.pargs.page
        size = self.app.pargs.size

        if user_id is not None:
            res = self.client.user.get(user_id)
            self.app.render(res, details=True)
        elif login_or_email is not None:
            res = self.client.user.get_by_login_or_email(login_or_email)
            self.app.render(res, details=True)
        else:
            res = self.client.user.list(page=page, size=size)
            self.app.render(res, headers=["id", "name", "login", "email", "isAdmin"])
            # self.app.render(res, details=True)

    # -----------------------------
    # ---- ALERT NOTIFICATION -----
    # -----------------------------
    @ex(
        help=_("add alert notification"),
        description=_("add alert notification"),
        arguments=grafana_args(
            [
                (
                    ["name"],
                    {
                        "help": _("alert notification name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["email"],
                    {
                        "help": _("alert notification email"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def alert_notification_add(self):
        name = self.app.pargs.name
        email = self.app.pargs.email
        res = self.client.alert_notification.add(alert_name=name, email=email)
        self.app.render(res, headers=["uid"])

    @ex(
        help=_("update alert notification"),
        description=_("update alert notification"),
        arguments=grafana_args(
            [
                (
                    ["id"],
                    {
                        "help": _("alert notification uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("alert notification name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["email"],
                    {
                        "help": _("alert notification email"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def alert_notification_update(self):
        alert_notification_uid = self.app.pargs.id
        name = self.app.pargs.name
        email = self.app.pargs.email
        res = self.client.alert_notification.update(alert_notification_uid, account_name=name, email=email)
        self.app.render(res, headers=["uid"])

    @ex(
        help=_("delete alert notification"),
        description=_("delete alert notification"),
        arguments=grafana_args(
            [
                (
                    ["id"],
                    {
                        "help": _("alert notification uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def alert_notification_del(self):
        alert_notification_uid = self.app.pargs.id
        self.client.alert_notification.delete(alert_notification_uid)
        self.app.render(
            {"msg": f"delete alert_notification {alert_notification_uid}"},
            headers=["message"],
        )

    @ex(
        help=_("get alert notification"),
        description=_("get alert notification"),
        arguments=grafana_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("alert notification uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("alert notification name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def alert_notification_get(self):
        alert_notification_uid = self.app.pargs.id
        alert_notification_name = self.app.pargs.name

        if alert_notification_uid is not None:
            res = self.client.alert_notification.get(alert_notification_uid)
            self.app.render(res, details=True)
        elif alert_notification_name is not None:
            res = self.client.alert_notification.get_by_name(alert_notification_name)
            if res is not None:
                self.app.render(res, details=True)
        else:
            res = self.client.alert_notification.list()
            self.app.render(res, headers=["id", "name", "uid", "type", "isDefault", "updated"])

    # --------------------
    # ---- DASHBOARD -----
    # --------------------
    @ex(
        help=_("add dashboard"),
        description=_("add dashboard"),
        arguments=grafana_args(
            [
                (
                    ["data_dashboard"],
                    {
                        "help": _("dashboard data"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dashboard_add(self):
        data_dashboard = self.app.pargs.data_dashboard
        json_dashboard = loads(data_dashboard)
        res = self.client.dashboard.add(data_dashboard=json_dashboard)
        self.app.render(res, headers=["uid"])

    @ex(
        help=_("copy dashboard"),
        description=_("copy dashboard"),
        arguments=grafana_args(
            [
                (
                    ["name"],
                    {
                        "help": _("dashboard name to search"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["folder_uid"],
                    {
                        "help": _("folder uid where add dashboard"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["organization"],
                    {"help": _("organization name"), "action": "store", "type": str},
                ),
                (
                    ["division"],
                    {"help": _("division name"), "action": "store", "type": str},
                ),
                (["account"], {"help": _("account name"), "action": "store", "type": str}),
                (
                    ["-dash_tag"],
                    {
                        "help": _("dash tag to add (comma separated)"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dashboard_folder_from_id"],
                    {
                        "help": _("folder id where search dashboard"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dashboard_copy(self):
        dashboard_to_search = self.app.pargs.name
        folder_uid_to = self.app.pargs.folder_uid

        organization = self.app.pargs.organization
        division = self.app.pargs.division
        account = self.app.pargs.account

        dash_tag = self.app.pargs.dash_tag
        dashboard_folder_from_id = self.app.pargs.dashboard_folder_from_id

        res_folder = self.client.folder.get(folder_uid_to)
        folder_id_to = res_folder["id"]

        res = self.client.dashboard.add_dashboard(
            dashboard_to_search,
            folder_id_to,
            organization,
            division,
            account,
            dash_tag=dash_tag,
            dashboard_folder_from_id=dashboard_folder_from_id,
        )
        # self.app.render(res, headers=['uid'])
        self.app.render(res, details=True)

    @ex(
        help=_("delete dashboard"),
        description=_("delete dashboard"),
        arguments=grafana_args(
            [
                (
                    ["uid"],
                    {
                        "help": _("dashboard uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dashboard_del(self):
        dashboard_uid = self.app.pargs.uid
        self.client.dashboard.delete(dashboard_uid)
        self.app.render({"msg": f"delete dashboard {dashboard_uid}"}, headers=["message"])

    @ex(
        help=_("get dashboard"),
        description=_("get dashboard"),
        arguments=grafana_args(
            [
                (
                    ["-uid"],
                    {
                        "help": _("dashboard uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-search"],
                    {
                        "help": _("dashboard search query"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-folder"],
                    {
                        "help": _("folder id - 0 for General"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dashboard_get(self):
        dashboard_uid = self.app.pargs.uid

        if dashboard_uid is not None:
            res = self.client.dashboard.get(dashboard_uid)
            self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            search = self.app.pargs.search
            folder = self.app.pargs.folder
            res = self.client.dashboard.list(search=search, folder_id=folder, size=size, page=page)
            self.app.render(res["dashboards"], headers=["id", "uid", "title", "tags", "folderUid"])

    @ex(
        help=_("update dashboard"),
        description=_("update dashboard"),
        arguments=grafana_args(
            [
                (
                    ["uid"],
                    {
                        "help": _("dashboard uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["title"],
                    {
                        "help": _("dashboard new title"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dashboard_update(self):
        dashboard_uid = self.app.pargs.uid
        title = self.app.pargs.title
        res = self.client.dashboard.update(dashboard_uid, title)
        self.app.render(res, details=True)
