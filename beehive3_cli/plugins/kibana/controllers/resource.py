# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte

from beehive3_cli.core.controller import BaseController, PARGS
from cement import ex


class ElkResourceController(BaseController):
    class Meta:
        label = 'res_elk'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'elk orchestrator'
        help = 'elk orchestrator'

        cmp = {'baseuri': '/v1.0/nrs/elk', 'subsystem': 'resource'}

        headers = ['id', 'uuid', 'name', 'desc', 'ext_id', 'parent', 'container', 'state']
        fields = ['id', 'uuid', 'name', 'desc', 'ext_id', 'parent', 'container', 'state']

    def pre_command_run(self):
        super(ElkResourceController, self).pre_command_run()
        self.configure_cmp_api_client()

    # -----------------
    # ----- SPACE -----
    # -----------------
    @ex(
        help='get spaces',
        description='get spaces',
        arguments=PARGS([
            (['-id'], {'help': 'space id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def space_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/spaces/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('space')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/spaces' % self.baseuri
            self.app.log.debug("-+-+- space_get '%s' " % uri)
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='spaces', headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help='add spaces',
        description='add spaces',
        arguments=PARGS([
            (['container'], {'help': 'container', 'action': 'store', 'type': str, 'default': None}),
            (['id'], {'help': 'space id', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'space name', 'action': 'store', 'type': str, 'default': None}),
            (['-description'], {'help': 'space description', 'action': 'store', 'type': str, 'default': None}),
            (['-color'], {'help': 'space color', 'action': 'store', 'type': str, 'default': None}),
            (['-initials'], {'help': 'space initials', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def space_add(self):
        container = self.app.pargs.container
        id = self.app.pargs.id
        name = self.app.pargs.name
        description = self.app.pargs.description
        color = self.app.pargs.color
        initials = self.app.pargs.initials

        uri = '%s/spaces' % (self.baseuri)
        self.app.log.debug("-+-+- space_add '%s' " % uri)

        data_space = {
            'container': container,
            'space_id': id,
            'name': name
        }

        if description is not None:
            data_space.update({
			    'desc': description
            })
        if color is not None:
            data_space.update({
			    'color': color
            })
        if initials is not None:
            data_space.update({
			    'initials': initials
            })

        data = {
            'space': data_space
        }
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)
   
    @ex(
        help='delete spaces',
        description='delete spaces',
        arguments=PARGS([
            (['id'], {'help': 'resource space id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def space_delete(self):
        oid = self.app.pargs.id

        uri = '%s/spaces/%s' % (self.baseuri, oid)
        self.app.log.debug("-+-+- space_delete '%s' " % uri)

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)
        
    # ----------------
    # ----- ROLE -----
    # ----------------
    @ex(
        help='get roles',
        description='get roles',
        arguments=PARGS([
            (['-id'], {'help': 'role id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def role_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/roles/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('role')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/roles' % self.baseuri
            self.app.log.debug("-+-+- role_get '%s' " % uri)
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='roles', headers=self._meta.headers, fields=self._meta.fields)
    
    @ex(
        help='add roles',
        description='add roles',
        arguments=PARGS([
            (['container'], {'help': 'container', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'role name', 'action': 'store', 'type': str, 'default': None}),
            (['indice'], {'help': 'indice', 'action': 'store', 'type': str, 'default': None}),
            (['space_id'], {'help': 'space id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def role_add(self):
        container = self.app.pargs.container
        # id = self.app.pargs.id
        name = self.app.pargs.name
        desc = 'Desc %s' % name
        indice = self.app.pargs.indice
        space_id = self.app.pargs.space_id

        uri = '%s/roles' % (self.baseuri)
        self.app.log.debug("-+-+- role_add '%s' " % uri)

        data_role = {
            'container': container,
            'name': name,
            'desc': desc,
            'indice': indice,
            'space_id': space_id,
        }
        data = {
            'role': data_role
        }
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help='delete roles',
        description='delete roles',
        arguments=PARGS([
            (['id'], {'help': 'resource role id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def role_delete(self):
        oid = self.app.pargs.id

        uri = '%s/roles/%s' % (self.baseuri, oid)
        self.app.log.debug("-+-+- role_delete '%s' " % uri)

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)

    # ------------------
    # -- ROLE MAPPING --
    # ------------------
    @ex(
        help='get role_mappings',
        description='get role_mappings',
        arguments=PARGS([
            (['-id'], {'help': 'role_mapping id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def role_mapping_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/role_mappings/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('role_mapping')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/role_mappings' % self.baseuri
            self.app.log.debug("-+-+- role_mapping_get '%s' " % uri)
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='role_mappings', headers=self._meta.headers, fields=self._meta.fields)
    
    @ex(
        help='add role_mappings',
        description='add role_mappings',
        arguments=PARGS([
            (['container'], {'help': 'container', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'role_mapping name', 'action': 'store', 'type': str, 'default': None}),
            (['role_name'], {'help': 'role name', 'action': 'store', 'type': str, 'default': None}),
            (['users_email'], {'help': 'users email', 'action': 'store', 'type': str, 'default': None}),
            (['realm_name'], {'help': 'realm name', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def role_mapping_add(self):
        container = self.app.pargs.container
        # id = self.app.pargs.id
        name = self.app.pargs.name
        desc = 'Desc %s' % name
        role_name = self.app.pargs.role_name
        users_email = self.app.pargs.users_email
        realm_name = self.app.pargs.realm_name

        uri = '%s/role_mappings' % (self.baseuri)
        self.app.log.debug("-+-+- role_mapping_add '%s' " % uri)

        data_role_mapping = {
            'container': container,
            'name': name,
            'desc': desc,
            'role_name': role_name,
            'users_email': users_email,
            'realm_name': realm_name
        }
        data = {
            'role_mapping': data_role_mapping
        }
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help='delete role_mappings',
        description='delete role_mappings',
        arguments=PARGS([
            (['id'], {'help': 'resource role_mapping id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def role_mapping_delete(self):
        oid = self.app.pargs.id

        uri = '%s/role_mappings/%s' % (self.baseuri, oid)
        self.app.log.debug("-+-+- role_mapping_delete '%s' " % uri)

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)
