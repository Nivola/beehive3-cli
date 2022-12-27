# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from cement import ex
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.business.controllers.authority import AuthorityControllerChild


class CatalogController(AuthorityControllerChild):
    class Meta:
        label = 'service_catalogs'
        description = "service catalog management"
        help = "service catalog management"
        
        headers = ['id', 'name', 'version', 'active', 'date']
        fields = ['uuid', 'name', 'version', 'active', 'date.creation']

    @ex(
        help='get srvcatalogs',
        description='get srvcatalogs',
        arguments=PARGS([
            (['-id'], {'help': 'service catalog id', 'action': 'store', 'type': str, 'default': None}),
            (['-objid'], {'help': 'authorization id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'service catalog name', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/srvcatalogs/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri).get('catalog')

            if self.is_output_text():
                self.app.render(res, details=True)
                self.c('\nservice definitions', 'underline')
                params = []
                data = self.format_paginated_query(params)
                uri = '%s/srvcatalogs/%s/defs' % (self.baseuri, oid)
                res = self.cmp_get(uri, data=data)
                headers = ['id', 'uuid', 'name', 'version', 'status', 'service_type_id', 'active', 'date.creation']
                self.app.render(res, key='servicedefs', headers=headers)
            else:
                self.app.render(res, key='srvcatalog', details=True)
        else:
            params = ['name', 'objid', 'division_id', 'contact', 'email', 'email_support']
            data = self.format_paginated_query(params)
            uri = '%s/srvcatalogs' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='catalogs', headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help='add service catalog',
        description='add service catalog',
        arguments=ARGS([
            (['name'], {'help': 'service catalog name', 'action': 'store', 'type': str}),
            (['-desc'], {'help': 'service catalog description', 'action': 'store', 'type': str, 'default': ''}),
        ])
    )
    def add(self):
        data = {
            'srvcatalog': {
                'name': self.app.pargs.name,
                'desc': self.app.pargs.desc,
            }
         }
        uri = '%s/srvcatalogs' % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'Add service catalog %s' % res})

    @ex(
        help='update service catalog',
        description='update service catalog',
        arguments=ARGS([
            (['id'], {'help': 'service catalog id', 'action': 'store', 'type': str}),
            (['-name'], {'help': 'service catalog name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'service catalog description', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def update(self):
        oid = self.app.pargs.id
        params = self.app.kvargs
        data = {
            'srvcatalog': params
        }
        uri = '%s/srvcatalogs/%s' % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'update service catalog %s' % oid})

    @ex(
        help='refresh service catalog',
        description='refresh service catalog',
        arguments=ARGS([
            (['id'], {'help': 'service catalog id', 'action': 'store', 'type': str}),
        ])
    )
    def patch(self):
        oid = self.app.pargs.id
        data = {
            'srvcatalog': {}
        }
        uri = '%s/srvcatalogs/%s' % (self.baseuri, oid)
        self.cmp_patch(uri, data=data, timeout=600)
        self.app.render({'msg': 'refresh service catalog %s' % oid})

    @ex(
        help='delete service catalog',
        description='delete service catalog',
        arguments=ARGS([
            (['id'], {'help': 'service catalog id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = '%s/srvcatalogs/%s' % (self.baseuri, oid)
        self.cmp_delete(uri, entity='service catalog %s' % oid)

    @ex(
        help='delete service catalog service definition',
        description='delete service catalog service definition',
        arguments=ARGS([
            (['id'], {'help': 'service catalog id', 'action': 'store', 'type': str}),
            (['definitions'], {'help': 'comma separated list of definition id', 'action': 'store', 'type': str}),
        ])
    )
    def definition_add(self):
        oid = self.app.pargs.id
        definitions = self.app.pargs.definitions
        data = {
            'definitions': {
                'oids': definitions.split(',')
            }
        }
        uri = '%s/srvcatalogs/%s/defs' % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'ddd service definitions %s to catalog %s' % (definitions, oid)})

    @ex(
        help='delete service catalog service definition',
        description='delete service catalog service definition',
        arguments=ARGS([
            (['id'], {'help': 'service catalog id', 'action': 'store', 'type': str}),
            (['definitions'], {'help': 'comma separated list of definition id', 'action': 'store', 'type': str}),
        ])
    )
    def definition_del(self):
        oid = self.app.pargs.id
        definitions = self.app.pargs.definitions
        data = {
            'definitions': {
                'oids': definitions.split(',')
            }
        }
        uri = '%s/srvcatalogs/%s/defs' % (self.baseuri, oid)
        self.cmp_delete(uri, data=data, entity='service definitions %s' % definitions)


class CatalogAuthController(AuthorityControllerChild):
    class Meta:
        label = 'service_catalogs_auth'
        # aliases = ['auth']
        # stacked_on = 'srvcatalogs'
        # stacked_type = 'nested'
        description = "service catalog authorization"
        help = "service catalog authorization"

    @ex(
        help='get service catalog  roles',
        description='get service catalog  roles',
        arguments=ARGS([
            (['id'], {'help': 'service catalog id', 'action': 'store', 'type': str}),
        ])
    )
    def role_get(self):
        oid = self.app.pargs.id
        uri = '%s/srvcatalogs/%s/roles' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key='roles', headers=['name', 'desc'], maxsize=200)

    @ex(
        help='get service catalog  users',
        description='get service catalog  users',
        arguments=ARGS([
            (['id'], {'help': 'service catalog id', 'action': 'store', 'type': str}),
        ])
    )
    def user_get(self):
        oid = self.app.pargs.id
        uri = '%s/srvcatalogs/%s/users' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key='users', headers=['id', 'name', 'desc', 'role'],
                        fields=['uuid', 'name', 'desc', 'role'], maxsize=200)

    @ex(
        help='add service catalog  role to a user',
        description='add service catalog  role to a user',
        arguments=ARGS([
            (['id'], {'help': 'service catalog id', 'action': 'store', 'type': str}),
            (['role'], {'help': 'service catalog role', 'action': 'store', 'type': str}),
            (['user'], {'help': 'authorization user', 'action': 'store', 'type': str}),
        ])
    )
    def user_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {
            'user': {
                'user_id': user,
                'role': role
            }
        }
        uri = '%s/srvcatalogs/%s/users' % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({'msg': res})

    @ex(
        help='remove service catalog  role from a user',
        description='remove service catalog  role from a user',
        arguments=ARGS([
            (['id'], {'help': 'service catalog id', 'action': 'store', 'type': str}),
            (['role'], {'help': 'service catalog role', 'action': 'store', 'type': str}),
            (['user'], {'help': 'authorization user', 'action': 'store', 'type': str}),
        ])
    )
    def user_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {
            'user': {
                'user_id': user,
                'role': role
            }
        }
        uri = '%s/srvcatalogs/%s/users' % (self.baseuri, oid)
        res = self.cmp_delete(uri, data)
        self.app.render({'msg': res})

    @ex(
        help='get service catalog  groups',
        description='get service catalog  groups',
        arguments=ARGS([
            (['id'], {'help': 'service catalog id', 'action': 'store', 'type': str}),
        ])
    )
    def group_get(self):
        oid = self.app.pargs.id
        uri = '%s/srvcatalogs/%s/groups' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key='groups', headers=['id', 'name', 'role'], fields=['uuid', 'name', 'role'], maxsize=200)

    @ex(
        help='add service catalog  role to a group',
        description='add service catalog  role to a group',
        arguments=ARGS([
            (['id'], {'help': 'service catalog id', 'action': 'store', 'type': str}),
            (['role'], {'help': 'service catalog role', 'action': 'store', 'type': str}),
            (['group'], {'help': 'authorization group', 'action': 'store', 'type': str}),
        ])
    )
    def group_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {
            'group': {
                'group_id': group,
                'role': role
            }
        }
        uri = '%s/srvcatalogs/%s/groups' % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({'msg': res})

    @ex(
        help='remove service catalog  role from a group',
        description='remove service catalog  role from a group',
        arguments=ARGS([
            (['id'], {'help': 'service catalog id', 'action': 'store', 'type': str}),
            (['role'], {'help': 'service catalog role', 'action': 'store', 'type': str}),
            (['group'], {'help': 'authorization group', 'action': 'store', 'type': str}),
        ])
    )
    def group_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {
            'group': {
                'group_id': group,
                'role': role
            }
        }
        uri = '%s/srvcatalogs/%s/groups' % (self.baseuri, oid)
        res = self.cmp_delete(uri, data)
        self.app.render({'msg': res})
