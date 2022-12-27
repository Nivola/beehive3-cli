# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte

from beehive3_cli.core.controller import BaseController, PARGS
from cement import ex


class GrafanaResourceController(BaseController):
    class Meta:
        label = 'res_grafana'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'grafana orchestrator'
        help = 'grafana orchestrator'

        cmp = {'baseuri': '/v1.0/nrs/grafana', 'subsystem': 'resource'}

        headers = ['id', 'uuid', 'name', 'desc', 'ext_id', 'parent', 'container', 'state']
        fields = ['id', 'uuid', 'name', 'desc', 'ext_id', 'parent', 'container', 'state']

    def pre_command_run(self):
        super(GrafanaResourceController, self).pre_command_run()
        self.configure_cmp_api_client()


    # -----------------
    # ----- FOLDER -----
    # -----------------
    @ex(
        help='get folders',
        description='get folders',
        arguments=PARGS([
            (['-id'], {'help': 'folder id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def folder_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/folders/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('folder')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/folders' % self.baseuri
            self.app.log.debug("+++++ folder_get '%s' " % uri)
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='folders', headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help='add folders',
        description='add folders',
        arguments=PARGS([
            (['container'], {'help': 'container', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'folder name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'folder desc', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def folder_add(self):
        container = self.app.pargs.container
        name = self.app.pargs.name
        desc = self.app.pargs.desc

        uri = '%s/folders' % (self.baseuri)
        self.app.log.debug("+++++ folder_add '%s' " % uri)

        data_folder = {
            'container': container,
            'name': name,
        }

        if desc is not None:
            data_folder.update({
			    'desc': desc
            })

        data = {
            'folder': data_folder
        }
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)
   
    @ex(
        help='delete folders',
        description='delete folders',
        arguments=PARGS([
            (['id'], {'help': 'resource folder id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def folder_delete(self):
        oid = self.app.pargs.id

        uri = '%s/folders/%s' % (self.baseuri, oid)
        self.app.log.debug("+++++ folder_delete '%s' " % uri)

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)


    # -----------------
    # ----- TEAM -----
    # -----------------
    @ex(
        help='get teams',
        description='get teams',
        arguments=PARGS([
            (['-id'], {'help': 'team id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def team_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/teams/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('team')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/teams' % self.baseuri
            self.app.log.debug("+++++ team_get '%s' " % uri)
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='teams', headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help='add teams',
        description='add teams',
        arguments=PARGS([
            (['container'], {'help': 'container', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'team name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'team desc', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def team_add(self):
        container = self.app.pargs.container
        name = self.app.pargs.name
        desc = self.app.pargs.desc

        uri = '%s/teams' % (self.baseuri)
        self.app.log.debug("+++++ team_add '%s' " % uri)

        data_team = {
            'container': container,
            'name': name,
        }

        if desc is not None:
            data_team.update({
			    'desc': desc
            })

        data = {
            'team': data_team
        }
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)
   
    @ex(
        help='delete teams',
        description='delete teams',
        arguments=PARGS([
            (['id'], {'help': 'resource team id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def team_delete(self):
        oid = self.app.pargs.id

        uri = '%s/teams/%s' % (self.baseuri, oid)
        self.app.log.debug("+++++ team_delete '%s' " % uri)

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)


    # ------------------------------
    # ----- ALERT NOTIFICATION -----
    # ------------------------------
    @ex(
        help='get alert_notifications',
        description='get alert_notifications',
        arguments=PARGS([
            (['-id'], {'help': 'alert_notification id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def alert_notification_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/alert_notifications/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('alert_notification')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/alert_notifications' % self.baseuri
            self.app.log.debug("+++++ alert_notification_get '%s' " % uri)
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='alert_notifications', headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help='add alert_notifications',
        description='add alert_notifications',
        arguments=PARGS([
            (['container'], {'help': 'container', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'alert_notification name', 'action': 'store', 'type': str, 'default': None}),
            (['email'], {'help': 'alert_notification email', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'alert_notification desc', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def alert_notification_add(self):
        container = self.app.pargs.container
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        email = self.app.pargs.email

        uri = '%s/alert_notifications' % (self.baseuri)
        self.app.log.debug("+++++ alert_notification_add '%s' " % uri)

        data_alert_notification = {
            'container': container,
            'name': name,
            'email': email,
        }

        if desc is not None:
            data_alert_notification.update({
			    'desc': desc
            })

        data = {
            'alert_notification': data_alert_notification
        }
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)
   
    @ex(
        help='delete alert_notifications',
        description='delete alert_notifications',
        arguments=PARGS([
            (['id'], {'help': 'resource alert_notification id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def alert_notification_delete(self):
        oid = self.app.pargs.id

        uri = '%s/alert_notifications/%s' % (self.baseuri, oid)
        self.app.log.debug("+++++ alert_notification_delete '%s' " % uri)

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)
