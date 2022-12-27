# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
import json
import sys
from time import sleep
from beecell.simple import merge_list, read_file, dict_get
from beedrones.grafana.client_grafana import GrafanaManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS, PAGINATION_ARGS
from cement import ex
from beehive3_cli.core.util import load_environment_config


def GRAFANA_ARGS(*list_args):
    orchestrator_args = [
        (['-O', '--orchestrator'], {'action': 'store', 'dest': 'orchestrator',
                                    'help': 'grafana platform reference label'})
    ]
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, orchestrator_args, *list_args)
    return res


class GrafanaPlatformController(BaseController):
    headers = ['id', 'name']
    entity_class = None

    class Meta:
        stacked_on = 'platform'
        stacked_type = 'nested'
        label = 'grafana'
        description = "grafana platform management"
        help = "grafana platform  management"

    def pre_command_run(self):
        super(GrafanaPlatformController, self).pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get('orchestrators', {}).get('grafana', {})
        label = getattr(self.app.pargs, 'orchestrator', None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception('No grafana default platform is available for this environment. Select '
                                'another environment')

        if label not in orchestrators:
            raise Exception('Valid label are: %s' % ', '.join(orchestrators.keys()))
        self.conf = orchestrators.get(label)

        # print("-+-+- self.conf: " + str(self.conf))
        grafana_host = self.conf.get('hosts')[0]
        grafana_port = self.conf.get('port')
        grafana_user = self.conf.get('user')
        grafana_pwd = self.conf.get('pwd')
        grafana_protocol = self.conf.get('proto', 'http')
        self.client = GrafanaManager(host=grafana_host, port=grafana_port, protocol=grafana_protocol, username=grafana_user, pwd=grafana_pwd)

    @ex(
        help='ping grafana',
        description='ping grafana',
        arguments=GRAFANA_ARGS()
    )
    def ping(self):
        res = self.client.ping()
        self.app.render({'ping': res}, headers=['ping'])


    @ex(
        help='get grafana version',
        description='get grafana version',
        arguments=GRAFANA_ARGS()
    )
    def version(self):
        res = self.client.version()
        self.app.render(res, headers=['version'])


    # -----------------
    # ---- FOLDER -----
    # -----------------  
    @ex(
        help='add folder',
        description='add folder',
        arguments=GRAFANA_ARGS([
            (['name'], {'help': 'folder name', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def folder_add(self):
        name = self.app.pargs.name
        res = self.client.folder.add(folder_name=name)
        self.app.render(res, headers=['id', 'uid', 'title'])


    @ex(
        help='delete folder',
        description='delete folder',
        arguments=GRAFANA_ARGS([
            (['uid'], {'help': 'folder uid', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def folder_del(self):
        folder_uid = self.app.pargs.uid
        self.client.folder.delete(folder_uid)
        self.app.render({'msg': 'delete folder %s' % folder_uid}, headers=['msg'])

    
    @ex(
        help='get folder',
        description='get folder',
        arguments=GRAFANA_ARGS([
            (['-uid'], {'help': 'folder uid', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'folder name', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def folder_get(self):
        folder_uid = self.app.pargs.uid
        folder_name = self.app.pargs.name
        if folder_uid is not None:
            res = self.client.folder.get(folder_uid)
            self.app.render(res, details=True)

        elif folder_name is not None:
            res = self.client.folder.search(folder_name)
            self.app.render(res, headers=['id', 'uid', 'title'])

        else:
            res = self.client.folder.list()
            self.app.render(res, headers=['id', 'uid', 'title'])


    @ex(
        help='get folder dashboard',
        description='get folder dashboard',
        arguments=GRAFANA_ARGS([
            (['id'], {'help': 'folder uid or "general" for general folder', 'action': 'store', 'type': str, 'default': None}),
            (['-search'], {'help': 'dashboard search query', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def folder_dashboard_get(self):
        folder_uid = self.app.pargs.id
        search = self.app.pargs.search
        if folder_uid == 'general':
            folder_id = '0'
        else:
            res_folder = self.client.folder.get(folder_uid)
            folder_id = res_folder['id']
        res = self.client.dashboard.list(folder_id, search)        
        self.app.render(res['dashboards'], headers=['id', 'uid', 'title', 'uri', 'url', 'type', 'tags', 'isStarred'])
        

    @ex(
        help='add folder permission',
        description='add folder permission',
        arguments=GRAFANA_ARGS([
            (['uid'], {'help': 'folder uid', 'action': 'store', 'type': str, 'default': None}),
            (['-team_viewer'], {'help': 'team id viewer', 'action': 'store', 'type': int, 'default': None}),
            (['-team_editor'], {'help': 'team id editor', 'action': 'store', 'type': int, 'default': None}),
        ])
    )
    def folder_permission_add(self):
        uid = self.app.pargs.uid
        team_viewer = self.app.pargs.team_viewer
        team_editor = self.app.pargs.team_editor
        res = self.client.folder.add_permission(folder_uid=uid, team_id_viewer=team_viewer, team_id_editor=team_editor)
        self.app.render(res, details=True)

    
    @ex(
        help='add folder permission',
        description='add folder permission',
        arguments=GRAFANA_ARGS([
            (['uid'], {'help': 'folder uid', 'action': 'store', 'type': str, 'default': None}),
            (['-team_viewer'], {'help': 'team id viewer', 'action': 'store', 'type': int, 'default': None}),
            (['-team_editor'], {'help': 'team id editor', 'action': 'store', 'type': int, 'default': None}),
        ])
    )
    def folder_permission_get(self):
        uid = self.app.pargs.uid
        res = self.client.folder.get_permissions(folder_uid=uid)
        self.app.render(res, headers=['team', 'permissionName', 'updated'])


    # ---------------
    # ---- TEAM -----
    # ---------------  
    @ex(
        help='add team',
        description='add team',
        arguments=GRAFANA_ARGS([
            (['name'], {'help': 'team name', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def team_add(self):
        name = self.app.pargs.name
        res = self.client.team.add(team_name=name)
        self.app.render(res, headers=['teamId'])


    @ex(
        help='delete team',
        description='delete team',
        arguments=GRAFANA_ARGS([
            (['id'], {'help': 'team id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def team_del(self):
        team_id = self.app.pargs.id
        self.client.team.delete(team_id)
        self.app.render({'msg': 'delete team %s' % team_id}, headers=['msg'])

    
    @ex(
        help='get team',
        description='get team',
        arguments=GRAFANA_ARGS([
            (['-id'], {'help': 'team id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'team name', 'action': 'store', 'type': str, 'default': None}),
        ])
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
            self.app.render(res, headers=['id', 'name', 'memberCount'])
        else:
            res = self.client.team.list(page=page, size=size)
            self.app.render(res, headers=['id', 'name', 'memberCount'])
            # self.app.render(res, details=True)


    @ex(
        help='get user of team',
        description='get user of team',
        arguments=GRAFANA_ARGS([
            (['id'], {'help': 'team id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def team_user_get(self):
        team_id = self.app.pargs.id
        res = self.client.team.get_users(team_id)
        self.app.render(res, headers=['teamId', 'userId', 'email', 'login'])


    @ex(
        help='add user to team',
        description='add user to team',
        arguments=GRAFANA_ARGS([
            (['team_id'], {'help': 'team id', 'action': 'store', 'type': int, 'default': None}),
            (['user_id'], {'help': 'user id', 'action': 'store', 'type': int, 'default': None}),
        ])
    )
    def team_user_add(self):
        team_id = self.app.pargs.team_id
        user_id = self.app.pargs.user_id
        message = self.client.team.add_user(team_id, user_id)
        self.app.render({'msg': '%s' % message}, headers=['message'])


    @ex(
        help='delete user from team',
        description='delete user from team',
        arguments=GRAFANA_ARGS([
            (['team_id'], {'help': 'team id', 'action': 'store', 'type': int, 'default': None}),
            (['user_id'], {'help': 'user id', 'action': 'store', 'type': int, 'default': None}),
        ])
    )
    def team_user_del(self):
        team_id = self.app.pargs.team_id
        user_id = self.app.pargs.user_id
        message = self.client.team.del_user(team_id, user_id)
        self.app.render({'msg': '%s' % message}, headers=['message'])


    # ---------------
    # ---- USER -----
    # ---------------  
    @ex(
        help='add user',
        description='add user',
        arguments=GRAFANA_ARGS([
            (['-name'], {'help': 'user name', 'action': 'store', 'type': str, 'default': None}),
            (['-email'], {'help': 'email', 'action': 'store', 'type': str, 'default': None}),
            (['-login'], {'help': 'user login', 'action': 'store', 'type': str, 'default': None}),
            (['-password'], {'help': 'password', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def user_add(self):
        name = self.app.pargs.name
        email = self.app.pargs.email
        login = self.app.pargs.login
        password = self.app.pargs.password
        res = self.client.user.add(name=name, email=email, login=login, password=password)
        self.app.render(res, headers=['id'])


    @ex(
        help='delete user',
        description='delete user',
        arguments=GRAFANA_ARGS([
            (['id'], {'help': 'user id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def user_del(self):
        user_id = self.app.pargs.id
        self.client.user.delete(user_id)
        self.app.render({'msg': 'delete user %s' % user_id}, headers=['msg'])

    
    @ex(
        help='get user',
        description='get user',
        arguments=GRAFANA_ARGS([
            (['-id'], {'help': 'user uid', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'user name', 'action': 'store', 'type': str, 'default': None}),
        ])
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
            self.app.render(res, headers=['id', 'name', 'login', 'email', 'isAdmin'])
            # self.app.render(res, details=True)


    # -----------------------------
    # ---- ALERT NOTIFICATION -----
    # -----------------------------
    @ex(
        help='add alert notification',
        description='add alert notification',
        arguments=GRAFANA_ARGS([
            (['name'], {'help': 'alert notification name', 'action': 'store', 'type': str, 'default': None}),
            (['email'], {'help': 'alert notification email', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def alert_notification_add(self):
        name = self.app.pargs.name
        email = self.app.pargs.email
        res = self.client.alert_notification.add(alert_name=name, email=email)
        self.app.render(res, headers=['uid'])

    
    @ex(
        help='update alert notification',
        description='update alert notification',
        arguments=GRAFANA_ARGS([
            (['id'], {'help': 'alert notification uid', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'alert notification name', 'action': 'store', 'type': str, 'default': None}),
            (['email'], {'help': 'alert notification email', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def alert_notification_update(self):
        alert_notification_uid = self.app.pargs.id
        name = self.app.pargs.name
        email = self.app.pargs.email
        res = self.client.alert_notification.update(alert_notification_uid, account_name=name, email=email)
        self.app.render(res, headers=['uid'])


    @ex(
        help='delete alert notification',
        description='delete alert notification',
        arguments=GRAFANA_ARGS([
            (['id'], {'help': 'alert notification uid', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def alert_notification_del(self):
        alert_notification_uid = self.app.pargs.id
        self.client.alert_notification.delete(alert_notification_uid)
        self.app.render({'msg': 'delete alert_notification %s' % alert_notification_uid}, headers=['message'])

    
    @ex(
        help='get alert notification',
        description='get alert notification',
        arguments=GRAFANA_ARGS([
            (['-id'], {'help': 'alert notification uid', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'alert notification name', 'action': 'store', 'type': str, 'default': None}),
        ])
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
            self.app.render(res, headers=['id', 'name', 'uid', 'type', 'isDefault', 'updated'])

    # --------------------
    # ---- DASHBOARD -----
    # --------------------
    @ex(
        help='add dashboard',
        description='add dashboard',
        arguments=GRAFANA_ARGS([
            (['data_dashboard'], {'help': 'dashboard data', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def dashboard_add(self):
        data_dashboard = self.app.pargs.data_dashboard
        json_dashboard = json.loads(data_dashboard)
        res = self.client.dashboard.add(data_dashboard=json_dashboard)
        self.app.render(res, headers=['uid'])

    
    @ex(
        help='copy dashboard',
        description='copy dashboard',
        arguments=GRAFANA_ARGS([
            (['name'], {'help': 'dashboard name to search', 'action': 'store', 'type': str, 'default': None}),
            (['folder_uid'], {'help': 'folder uid where add dashboard', 'action': 'store', 'type': str, 'default': None}),
            (['organization'], {'help': 'organization name', 'action': 'store', 'type': str}),
            (['division'], {'help': 'division name', 'action': 'store', 'type': str}),
            (['account'], {'help': 'account name', 'action': 'store', 'type': str}),
        ])
    )
    def dashboard_copy(self):
        dashboard_to_search = self.app.pargs.name
        folder_uid_to = self.app.pargs.folder_uid

        organization = self.app.pargs.organization
        division = self.app.pargs.division
        account = self.app.pargs.account

        res_folder = self.client.folder.get(folder_uid_to)
        folder_id_to = res_folder['id']

        res = self.client.dashboard.add_dashboard(dashboard_to_search, folder_id_to, organization, division, account)
        # self.app.render(res, headers=['uid'])
        self.app.render(res, details=True)


    @ex(
        help='delete dashboard',
        description='delete dashboard',
        arguments=GRAFANA_ARGS([
            (['id'], {'help': 'dashboard id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def dashboard_del(self):
        dashboard_uid = self.app.pargs.id
        self.client.dashboard.delete(dashboard_uid)
        self.app.render({'msg': 'delete dashboard %s' % dashboard_uid}, headers=['message'])

    
    @ex(
        help='get dashboard',
        description='get dashboard',
        arguments=GRAFANA_ARGS([
            (['-id'], {'help': 'dashboard uid', 'action': 'store', 'type': str, 'default': None}),
            (['-search'], {'help': 'dashboard search query', 'action': 'store', 'type': str, 'default': None}),
            (['-folder'], {'help': 'folder id - 0 for General', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def dashboard_get(self):
        dashboard_id = self.app.pargs.id

        if dashboard_id is not None:
            res = self.client.dashboard.get(dashboard_id)
            self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            search = self.app.pargs.search
            folder = self.app.pargs.folder
            res = self.client.dashboard.list(search=search, folder_id=folder, size=size, page=page)
            self.app.render(res['dashboards'], headers=['id', 'uid', 'title', 'tags', 'folderUid'])

