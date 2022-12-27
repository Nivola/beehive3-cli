# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from urllib.parse import urlencode
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments import format
from pygments.style import Style
from pygments.token import Token
from beecell.simple import truncate, set_request_params, dict_get
from beehive3_cli.core.controller import BaseController, PARGS, ARGS, StringAction
from cement import ex
from tinydb import TinyDB, Query


class DqServiceEntityController(BaseController):
    class Meta:
        stacked_on = 'dq_service'
        stacked_type = 'nested'
        label = 'dq_insts'
        description = "service instance data quality"
        help = "service instance data quality"

        cmp = {'baseuri': '/v2.0/nws', 'subsystem': 'resource'}

        headers = ['id', 'uuid', 'objdef', 'name', 'container', 'parent', 'active', 'state', 'date', 'ext_id']
        fields = ['id', 'uuid', '__meta__.definition', 'name', 'container', 'parent', 'active', 'base_state',
                  'date.creation', 'ext_id']
        link_fields = ['id', 'name', 'active', 'details.type', 'details.start_resource', 'details.end_resource',
                       'details.attributes', 'date.creation', 'date.modified']
        link_headers = ['id', 'name', 'active', 'type', 'start', 'end', 'attributes', 'creation', 'modified']
        task_headers = ['uuid', 'name', 'parent', 'api_id', 'status', 'start_time', 'stop_time', 'duration']
        task_fields = ['uuid', 'alias', 'parent', 'api_id', 'status', 'start_time', 'stop_time', 'duration']

    def pre_command_run(self):
        super(DqServiceEntityController, self).pre_command_run()

        self.configure_cmp_api_client()

        db = TinyDB('./bad_service.json')
        self.table_service = db.table('services')
        db = TinyDB('./bad_link.json')
        self.table_link = db.table('links')
        self.query = Query()

    @ex(
        help='check service instances',
        description='check service instances',
        arguments=PARGS([
            (['-id'], {'help': 'entity id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-container'], {'help': 'container uuid or name', 'action': 'store', 'type': str, 'default': None}),
            (['-type'], {'help': 'entity type', 'action': 'store', 'type': str, 'default': None}),
            (['-objid'], {'help': 'entity authorization id', 'action': 'store', 'type': str, 'default': None}),
            (['-ext_id'], {'help': 'entity physical id', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def check(self):
        oid = self.app.pargs.id
        if oid is not None:
            uri = '%s/serviceinsts/%s/check' % (self.baseuri, oid)
            item = self.cmp_get(uri).get('serviceinst')
            self.app.render(item, details=True)
        else:
            params = ['container', 'type', 'name', 'desc', 'objid', 'ext_id', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/serviceinsts' % self.baseuri
            res = self.cmp_get(uri, data=data)

            if 'page' in res:
                print('Page: %s' % res['page'])
                print('Count: %s' % res['count'])
                print('Total: %s' % res['total'])
                print('From: %s To: %s' % (res['page']*res['count'], (res['page']+1)*res['count']))
                print('Order: %s %s' % (res.get('sort').get('field'), res.get('sort').get('order')))

            tmpl = '{idx:4} {id:6} {name:40.40} {resource_uuid:40.40} {parent:40.40} {active:7} {status:10.10}'
            line = ''.join(['-' for i in range(40)])
            headers = {'idx': 'idx', 'id': 'id', 'name': 'name', 'resource_uuid': 'resource', 'parent': 'parent',
                       'active': 'active', 'status': 'status'}
            print(tmpl.format(**headers))

            idx = res['page']*res['count']+1
            for item in res.get('serviceinsts', []):
                uri = '%s/serviceinsts/%s/check' % (self.baseuri, item['id'])
                item = self.cmp_get(uri).get('serviceinst')

                if item.get('status') != 'ACTIVE':
                    data = self.table_service.search(self.query.id == item['id'])
                    if len(data) == 0:
                        self.table_service.insert(item)

                item['idx'] = idx
                self.app.log.warning(item)
                check = item.pop('check')
                item['parent'] = dict_get(item, 'parent.uuid')
                repr = tmpl.format(**item) + str(check)
                print(repr)
                idx += 1
