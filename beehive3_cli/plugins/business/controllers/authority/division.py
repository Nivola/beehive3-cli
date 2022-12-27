# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from cement import ex
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.business.controllers.authority import AuthorityControllerChild


class DivisionController(AuthorityControllerChild):
    class Meta:
        label = 'divs'
        description = "division management"
        help = "division management"
        
        headers = ['uuid', 'name', 'organization', 'accounts', 'contact', 'email', 'postaladdress', 'status', 'date']
        fields = ['uuid', 'name', 'organization_name', 'accounts', 'contact', 'email', 'postaladdress', 'status', 
                  'date.creation']

    @ex(
        help='get divisions',
        description='get divisions',
        arguments=PARGS([
            (['-id'], {'help': 'division uuid', 'action': 'store', 'type': str, 'default': None}),
            (['-objid'], {'help': 'authorization id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'division name', 'action': 'store', 'type': str, 'default': None}),
            (['-organization-id'], {'help': 'organization uuid', 'action': 'store', 'type': str, 'default': None}),
            (['-contact'], {'help': 'division contact', 'action': 'store', 'type': str, 'default': None}),
            (['-email'], {'help': 'division email', 'action': 'store', 'type': str, 'default': None}),
            (['-postaladdress'], {'help': 'division legalemail', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/divisions/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                data = 'division_id=%s' % oid
                uri = '%s/accounts' % self.baseuri
                accounts = self.cmp_get(uri, data=data).get('accounts', [])
                self.app.render(res, key='division', details=True)
                self.c('\naccounts', 'underline')
                self.app.render(accounts, headers=['id', 'uuid', 'name', 'contact', 'email', 'active', 'date.creation'])
            else:
                self.app.render(res, key='division', details=True)
        else:
            params = ['name', 'objid', 'organization_id', 'contact', 'email', 'postaladdress']
            data = self.format_paginated_query(params)
            uri = '%s/divisions' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='divisions', headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help='add division',
        description='add division',
        arguments=ARGS([
            (['name'], {'help': 'division name', 'action': 'store', 'type': str}),
            (['-desc'], {'help': 'division description', 'action': 'store', 'type': str, 'default': ''}),
            (['organization'], {'help': 'organization uuid', 'action': 'store', 'type': str}),
            (['-contact'], {'help': 'division contact', 'action': 'store', 'type': str, 'default': None}),
            (['-email'], {'help': 'division email', 'action': 'store', 'type': str, 'default': None}),            
            (['-postaladdress'], {'help': 'division postaladdress', 'action': 'store', 'type': str, 'default': None}),
            (['-price_list'], {'help': 'division price list id', 'action': 'store', 'type': int, 'default': None}),
        ])
    )
    def add(self):
        data = {
            'division': {
                'name': self.app.pargs.name,
                'desc': self.app.pargs.desc,
                'organization_id': self.app.pargs.organization,
                'contact': self.app.pargs.contact,
                'email': self.app.pargs.email,
                'postaladdress': self.app.pargs.postaladdress,
                'price_list_id': self.app.pargs.price_list,
            }
         }
        uri = '%s/divisions' % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'Add division %s' % res})

    @ex(
        help='update division',
        description='update division',
        arguments=ARGS([
            (['name'], {'help': 'division name', 'action': 'store', 'type': str}),
            (['-desc'], {'help': 'division description', 'action': 'store', 'type': str, 'default': ''}),
            (['organization'], {'help': 'organization uuid', 'action': 'store', 'type': str, 'default': None}),
            (['-contact'], {'help': 'division contact', 'action': 'store', 'type': str, 'default': None}),
            (['-email'], {'help': 'division email', 'action': 'store', 'type': str, 'default': None}),            
            (['-postaladdress'], {'help': 'division postaladdress', 'action': 'store', 'type': str, 'default': None}),
            (['-price_list_id'], {'help': 'division price list id', 'action': 'store', 'type': int, 'default': None}),
        ])
    )
    def update(self):
        """todo:"""
        oid = self.app.pargs.id
        params = self.app.kvargs
        data = {
            'division': params
        }
        uri = '%s/divisions/%s' % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'Update resource %s with data %s' % (oid, params)})

    @ex(
        help='refresh division',
        description='refresh division',
        arguments=ARGS([
            (['id'], {'help': 'division uuid', 'action': 'store', 'type': str}),
        ])
    )
    def patch(self):
        oid = self.app.pargs.id
        data = {
            'division': {}
        }
        uri = '%s/divisions/%s' % (self.baseuri, oid)
        self.cmp_patch(uri, data=data, timeout=600)
        self.app.render({'msg': 'Refresh division %s' % oid})

    @ex(
        help='delete division',
        description='delete division',
        arguments=ARGS([
            (['id'], {'help': 'division uuid', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = '%s/divisions/%s' % (self.baseuri, oid)
        self.cmp_delete(uri, entity='division %s' % oid)

    # @ex(
    #     help='get division active services info',
    #     description='get division active services info',
    #     arguments=ARGS([
    #         (['id'], {'help': 'division uuid', 'action': 'store', 'type': str}),
    #     ])
    # )
    # def active_services(self):
    #     oid = self.app.pargs.id
    #     uri = '%s/divisions/%s/activeservices' % (self.baseuri, oid)
    #     res = self.cmp_get(uri)
    #     self.app.render(res, key='services', details=True)
    #
    # @ex(
    #     help='get division wallet',
    #     description='get division wallet',
    #     arguments=ARGS([
    #         (['id'], {'help': 'division uuid', 'action': 'store', 'type': str}),
    #         (['-year'], {'help': 'wallet year', 'action': 'store', 'type': str, 'default': None}),
    #     ])
    # )
    # def wallet(self):
    #     oid = self.app.pargs.id
    #     year = self.app.pargs.year
    #     data = {'division_id': oid}
    #     if year is not None:
    #         data['year'] = year
    #     data = urlencode(data)
    #
    #     uri = '%s/wallets' % self.baseuri
    #     wallets = self.cmp_get(uri, data=data).get('wallets')
    #     print('Wallets:')
    #     self.app.render(wallets, headers=['year', 'id', 'uuid', 'name', 'capital_total', 'capital_used', 'active',
    #                                       'status', 'date.creation'])
    #
    #     # get agreements
    #     uri = '%s/divisions/%s/agreements' % (self.baseuri, oid)
    #     res = self.cmp_get(uri, data=data).get('agreements', [])
    #     print('Agreements:')
    #     self.app.render(res, headers=['wallet_id', 'id', 'uuid', 'name', 'amount', 'agreement_date_start', 'active',
    #                                   'date.creation'])


class DivisionAuthController(AuthorityControllerChild):
    class Meta:
        label = 'divs_auth'
        # aliases = ['auth']
        # stacked_on = 'divisions'
        # stacked_type = 'nested'
        description = "division authorization"
        help = "division authorization"

    @ex(
        help='get division roles',
        description='get division roles',
        arguments=ARGS([
            (['id'], {'help': 'division uuid', 'action': 'store', 'type': str}),
        ])
    )
    def role_get(self):
        oid = self.app.pargs.id
        uri = '%s/divisions/%s/roles' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key='roles', headers=['name', 'desc'], maxsize=200)

    @ex(
        help='get division users',
        description='get division users',
        arguments=ARGS([
            (['id'], {'help': 'division uuid', 'action': 'store', 'type': str}),
        ])
    )
    def user_get(self):
        oid = self.app.pargs.id
        uri = '%s/divisions/%s/users' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key='users', headers=['id', 'name', 'desc', 'role'],
                        fields=['uuid', 'name', 'desc', 'role'], maxsize=200)

    @ex(
        help='add division role to a user',
        description='add division role to a user',
        arguments=ARGS([
            (['id'], {'help': 'division uuid', 'action': 'store', 'type': str}),
            (['role'], {'help': 'division role', 'action': 'store', 'type': str}),
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
        uri = '%s/divisions/%s/users' % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({'msg': res})

    @ex(
        help='remove division role from a user',
        description='remove division role from a user',
        arguments=ARGS([
            (['id'], {'help': 'division uuid', 'action': 'store', 'type': str}),
            (['role'], {'help': 'division role', 'action': 'store', 'type': str}),
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
        uri = '%s/divisions/%s/users' % (self.baseuri, oid)
        res = self.cmp_delete(uri, data)
        self.app.render({'msg': res})

    @ex(
        help='get division groups',
        description='get division groups',
        arguments=ARGS([
            (['id'], {'help': 'division uuid', 'action': 'store', 'type': str}),
        ])
    )
    def group_get(self):
        oid = self.app.pargs.id
        uri = '%s/divisions/%s/groups' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key='groups', headers=['id', 'name', 'role'], fields=['uuid', 'name', 'role'], maxsize=200)

    @ex(
        help='add division role to a group',
        description='add division role to a group',
        arguments=ARGS([
            (['id'], {'help': 'division uuid', 'action': 'store', 'type': str}),
            (['role'], {'help': 'division role', 'action': 'store', 'type': str}),
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
        uri = '%s/divisions/%s/groups' % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({'msg': res})

    @ex(
        help='remove division role from a group',
        description='remove division role from a group',
        arguments=ARGS([
            (['id'], {'help': 'division uuid', 'action': 'store', 'type': str}),
            (['role'], {'help': 'division role', 'action': 'store', 'type': str}),
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
        uri = '%s/divisions/%s/groups' % (self.baseuri, oid)
        res = self.cmp_delete(uri, data)
        self.app.render({'msg': res})
