# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from cement import ex
from beecell.file import read_file
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.business.controllers.authority import AuthorityControllerChild


class AccountCapabilitiesController(AuthorityControllerChild):
    class Meta:
        label = 'capabilities'
        description = "capabilities management"
        help = "capabilities management"

        headers = ['uuid', 'name', 'desc', 'status', 'date']
        fields = ['uuid', 'name', 'desc', 'status', 'date.creation']

    @ex(
        help='get capabilities',
        description='get capabilities',
        arguments=PARGS([
            (['-id'], {'help': 'account uuid', 'action': 'store', 'type': str, 'default': None}),
            (['-objid'], {'help': 'authorization id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/capabilities/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri).get('capability', {})

            if self.is_output_text():
                params = res.pop('params', {})
                services = params.get('services', [])
                definitions = [{'name': d} for d in params.get('definitions', [])]
                self.app.render(res, details=True)
                print('\nservices:')
                self.app.render(services, maxsize=200, headers=['type', 'name', 'template', 'require.name', 'params'])
                print('\ndefinitions:')
                self.app.render(definitions, maxsize=200, headers=['name'])
            else:
                self.app.render(res, key='capability', details=True)
        else:
            params = []
            data = self.format_paginated_query(params)
            uri = '%s/capabilities' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='capabilities', headers=self._meta.headers, fields=self._meta.fields, maxsize=200)

    @ex(
        help='add capability',
        description='add capability',
        arguments=ARGS([
            (['config'], {'help': 'capability config', 'action': 'store', 'type': str}),
        ])
    )
    def add(self):
        config = self.app.pargs.config
        params = read_file(config).get('capability')
        data = {
            'capability': {
                'name': params.get('name'),
                'desc': params.get('desc', None),
                'version': params.get('version', '1.0'),
                'services': params.get('services', None),
            }
        }
        uri = '%s/accounts' % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'Add capability %s' % res})

    @ex(
        help='delete capability',
        description='delete capability',
        arguments=ARGS([
            (['id'], {'help': 'capability uuid', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = '%s/capabilities/%s' % (self.baseuri, oid)
        self.cmp_delete(uri, entity='capability %s' % oid)
