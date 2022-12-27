# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from datetime import datetime, timedelta
from urllib.parse import urlencode

from beecell.simple import truncate, format_date
from beehive3_cli.core.controller import PARGS, ARGS, StringAction
from cement import ex
from beehive3_cli.plugins.auth.controllers.auth import AuthChildController


class AuthGroupController(AuthChildController):
    class Meta:
        stacked_on = 'auth'
        stacked_type = 'nested'
        label = 'groups'
        description = "groups management"
        help = "groups management"

    @ex(
        help='get groups',
        description='get groups',
        arguments=PARGS([
            (['-id'], {'help': 'account uuid', 'action': 'store', 'type': str, 'default': None}),
            (['-role'], {'help': 'role id or name', 'action': 'store', 'type': str, 'default': None}),
            (['-user'], {'help': 'user id or name', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'name filter', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'group desc', 'action': 'store', 'type': str, 'default': None}),
            (['-email'], {'help': 'email address', 'action': 'store', 'type': str, 'default': None}),
            (['-expiry-date '], {'help': 'expiry date. Syntax YYYY-MM-DD', 'action': 'store', 'type': str,
                                 'default': None}),
            (['-perms'], {'help': 'rcomma separated list of permissions', 'action': 'store', 'type': str,
                          'default': None}),
        ])
    )
    def get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/groups/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            # get roles
            data = urlencode({'group': oid, 'size': -1})
            uri = '%s/roles' % self.baseuri
            roles = self.cmp_get(uri, data).get('roles')

            # get users
            data = urlencode({'group': oid, 'size': -1})
            uri = '%s/users' % self.baseuri
            users = self.cmp_get(uri, data).get('users')

            if self.is_output_text():
                self.app.render(res, key='group', details=True)
                self.c('\nroles', 'underline')
                self.app.render(roles, headers=self._meta.role_headers, fields=self._meta.role_fields)
                self.c('\nusers', 'underline')
                self.app.render(users, headers=self._meta.user_headers, fields=self._meta.user_fields)
            else:
                self.app.render(res, key='group', details=True)
        else:
            params = ['user', 'role', 'name', 'desc', 'expiry-date']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            if self.app.pargs.perms:
                ndata = {'perms.N': self.app.pargs.perms.split(',')}
                data += urlencode(ndata)
            uri = '%s/groups' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='groups', headers=self._meta.group_headers, fields=self._meta.group_fields)

    @ex(
        help='add group',
        description='add group',
        arguments=ARGS([
            (['name'], {'help': 'group name', 'action': 'store', 'type': str}),
            (['-desc'], {'help': 'group description', 'action': 'store', 'action': StringAction, 'type': str,
                         'nargs': '+', 'default': ''}),
            (['-expirydate'], {'help': 'group expire date. Syntax yyyy-mm-dd', 'action': 'store', 'type': str,
                               'default': None}),
        ])
    )
    def add(self):
        name = self.app.pargs.name

        if self.app.pargs.expirydate is None:
            expirydate = datetime.today() + timedelta(days=365)
        else:
            expirydate = self.app.pargs.expirydate
        expirydate = format_date(expirydate, format='%Y-%m-%d', microsec=False)

        data = {
            'group': {
                'name': name,
                'active': True,
                'desc': self.app.pargs.desc,
                'expirydate': expirydate
            }
        }
        uri = '%s/groups' % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add group %s' % res['uuid']})

    @ex(
        help='update group',
        description='update group',
        arguments=ARGS([
            (['id'], {'help': 'group uuid', 'action': 'store', 'type': str}),
            (['-name'], {'help': 'group name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'group description', 'action': 'store', 'action': StringAction, 'type': str,
                         'nargs': '+', 'default': None}),
            (['-active'], {'help': 'group active', 'action': 'store', 'type': bool, 'default': True}),
        ])
    )
    def update(self):
        oid = self.app.pargs.id

        data = {
            'group': {
                'name': self.app.pargs.name,
                'desc': self.app.pargs.desc,
                'active': self.app.pargs.active
            }
        }
        uri = '%s/groups/%s' % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'update group %s' % oid})

    @ex(
        help='delete group',
        description='delete group',
        arguments=ARGS([
            (['id'], {'help': 'group uuid', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = '%s/groups/%s' % (self.baseuri, oid)
        self.cmp_delete(uri, entity='group %s' % oid)

    @ex(
        help='add role to group',
        description='add role to group',
        arguments=ARGS([
            (['id'], {'help': 'group uuid', 'action': 'store', 'type': str}),
            (['role'], {'help': 'role uuid', 'action': 'store', 'type': str}),
            (['-expirydate'], {'help': 'group expire date. Syntax yyyy-mm-dd', 'action': 'store', 'type': str,
                               'default': None}),
        ])
    )
    def add_role(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role

        if self.app.pargs.expirydate is None:
            expirydate = datetime.today() + timedelta(days=365)
        else:
            expirydate = self.app.pargs.expirydate
        expirydate = format_date(expirydate, format='%Y-%m-%d', microsec=False)

        data = {
            'group': {
                'roles': {
                    'append': [(role, expirydate)],
                    'remove': []
                },
            }
        }
        uri = '%s/groups/%s' % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'add role %s to group %s' % (role, oid)})

    @ex(
        help='delete role from group',
        description='delete role from group',
        arguments=ARGS([
            (['id'], {'help': 'group uuid', 'action': 'store', 'type': str}),
            (['role'], {'help': 'role uuid', 'action': 'store', 'type': str}),
        ])
    )
    def del_role(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        data = {
            'group': {
                'roles': {
                    'append': [],
                    'remove': [role]
                },
            }
        }
        uri = '%s/groups/%s' % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'del role %s from group %s' % (role, oid)})

    @ex(
        help='add user to group',
        description='add user to group',
        arguments=ARGS([
            (['id'], {'help': 'group uuid', 'action': 'store', 'type': str}),
            (['user'], {'help': 'user uuid', 'action': 'store', 'type': str}),
        ])
    )
    def add_user(self):
        oid = self.app.pargs.id
        user = self.app.pargs.user

        data = {
            'group': {
                'users': {
                    'append': [user],
                    'remove': []
                },
            }
        }
        uri = '%s/groups/%s' % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'add user %s to group %s' % (user, oid)})

    @ex(
        help='delete user from group',
        description='delete user from group',
        arguments=ARGS([
            (['id'], {'help': 'group uuid', 'action': 'store', 'type': str}),
            (['user'], {'help': 'user uuid', 'action': 'store', 'type': str}),
        ])
    )
    def del_user(self):
        oid = self.app.pargs.id
        user = self.app.pargs.user
        data = {
            'group': {
                'users': {
                    'append': [],
                    'remove': [user]
                },
            }
        }
        uri = '%s/groups/%s' % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'del user %s from group %s' % (user, oid)})

    @ex(
        help='get permissions of group',
        description='get permissions of group',
        arguments=PARGS([
            (['id'], {'help': 'group uuid', 'action': 'store', 'type': str}),
        ])
    )
    def get_perms(self):
        oid = self.app.pargs.id
        params = []
        data = self.format_paginated_query(params)
        data += '&group=%s' % oid
        uri = '%s/objects/perms' % self.baseuri
        res = self.cmp_get(uri, data=data)
        self.app.render(res, key='perms', headers=self._meta.perm_headers, fields=self._meta.perm_fields)

    @ex(
        help='add permissions to group',
        description='add permissions to group',
        arguments=ARGS([
            (['id'], {'help': 'group uuid', 'action': 'store', 'type': str}),
            (['perms'], {'help': 'comma separated list of permission id', 'action': 'store', 'type': str}),
        ])
    )
    def add_perms(self):
        oid = self.app.pargs.id
        permids = self.app.pargs.perms
        perms = []
        for permid in permids.split(','):
            perms.append({'id': permid})

        data = {
            'group': {
                'perms': {
                    'append': perms,
                    'remove': []
                },
            }
        }
        uri = '%s/groups/%s' % (self.baseuri, oid)
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'add perm %s to group %s' % (res['perm_append'], oid)})

    @ex(
        help='delete permissions from group',
        description='delete permissions from group',
        arguments=ARGS([
            (['id'], {'help': 'group uuid', 'action': 'store', 'type': str}),
            (['perms'], {'help': 'comma separated list of permission id', 'action': 'store', 'type': str}),
        ])
    )
    def del_perms(self):
        oid = self.app.pargs.id
        permids = self.app.pargs.perms
        perms = []
        for permid in permids.split(','):
            perms.append({'id': permid})

        data = {
            'group': {
                'perms': {
                    'append': [],
                    'remove': perms
                },
            }
        }
        uri = '%s/groups/%s' % (self.baseuri, oid)
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'delete perm %s from group %s' % (res['perm_remove'], oid)})

    @ex(
        help='add attribute to group',
        description='add attribute to group',
        arguments=ARGS([
            (['id'], {'help': 'group uuid', 'action': 'store', 'type': str}),
            (['attrib'], {'help': 'attribute name', 'action': 'store', 'type': str}),
            (['value'], {'help': 'attribute value', 'action': 'store', 'type': str}),
            (['desc'], {'help': 'attribute description', 'action': 'store', 'type': str}),
        ])
    )
    def add_attrib(self):
        oid = self.app.pargs.id
        attrib = self.app.pargs.attrib
        data = {
            'group_attribute': {
                'name': attrib,
                'value': self.app.pargs.value,
                'desc': self.app.pargs.desc
            }
        }
        uri = '%s/groups/%s/attributes' % (self.baseuri, oid)
        self.cmp_post(uri, data=data)
        self.app.render({'msg': 'dd/update group %s attrib %s' % (oid, attrib)})

    @ex(
        help='delete attribute from group',
        description='delete attribute from group',
        arguments=ARGS([
            (['id'], {'help': 'group uuid', 'action': 'store', 'type': str}),
            (['attrib'], {'help': 'attribute name', 'action': 'store', 'type': str})
        ])
    )
    def del_attrib(self):
        oid = self.app.pargs.id
        attrib = self.app.pargs.attrib
        uri = '%s/groups/%s/attributes/%s' % (self.baseuri, oid, attrib)
        self.cmp_delete(uri)
        self.app.render({'msg': 'delete group %s attrib %s' % (oid, attrib)})




