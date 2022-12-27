# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beecell.simple import truncate, read_file
from beehive3_cli.core.controller import BaseController, PARGS, ARGS
from cement import ex


class DnsController(BaseController):
    class Meta:
        label = 'res_dns'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "dns orchestrator"
        help = "dns orchestrator"

        cmp = {'baseuri': '/v1.0/nrs/dns', 'subsystem': 'resource'}

        headers = ['id', 'uuid', 'ext_id', 'name', 'desc', 'parent', 'container', 'state']
        fields = ['id', 'uuid', 'ext_id', 'name', 'desc', 'parent', 'container', 'state']

    def pre_command_run(self):
        super(DnsController, self).pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help='get zones',
        description='get zones',
        arguments=PARGS([
            (['-id'], {'help': 'project id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def zone_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/zones/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('zone')
                self.app.render(res, details=True)

                self.c('\nnameservers', 'underline')
                uri = '%s/zones/%s/nameservers' % (self.baseuri, oid)
                res = self.cmp_get(uri, data='')
                self.app.render(res, key='nameservers', headers=['ip_addr', 'fqdn', 'start_nameserver'])
    
                self.c('\nauthority', 'underline')
                uri = '%s/zones/%s/authority' % (self.baseuri, oid)
                res = self.cmp_get(uri, data='')
                headers = ['rname', 'retry', 'start_nameserver', 'mname', 'refresh', 'minimum', 'expire', 'serial']
                self.app.render(res, key='authority', headers=headers)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/zones' % self.baseuri
            res = self.cmp_get(uri, data=data)
            headers = ['id', 'name', 'state', 'container', 'creation']
            fields = ['uuid', 'name', 'state', 'container', 'date.creation']
            self.app.render(res, key='zones', headers=headers, fields=fields)

    @ex(
        help='fetch a zone record',
        description='fetch a zone record',
        arguments=PARGS([
            (['id'], {'help': 'zone id', 'action': 'store', 'type': str, 'default': None}),
            (['record'], {'help': 'record name', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def zone_query(self):
        oid = self.app.pargs.id
        record = self.app.pargs.record
        uri = '%s/zones/%s/query' % (self.baseuri, oid)
        res = self.cmp_get(uri, data={'name': record})
        self.app.render(res, key='records', headers=['type', 'start_nameserver', 'ip_address', 'base_fqdn'],
                        maxsize=200)

    @ex(
        help='import record in a zone reading from a file',
        description='import record in a zone reading from a file',
        arguments=PARGS([
            (['id'], {'help': 'zone id', 'action': 'store', 'type': str, 'default': None}),
            (['filename'], {'help': 'file name', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def zone_records_import(self):
        """
        ---------------------------------------------
        $TTL 30 ; 30 seconds
        prova123                A       10.11.12.13
        $TTL 60 ; 1 minute
        prova123_               CNAME   prova123
        $TTL 30 ; 30 seconds
        prova456                A       10.11.12.14
        prova890                A       10.11.12.15
        ---------------------------------------------
        """
        oid = self.app.pargs.id
        file_name = self.app.pargs.filename

        records = []
        file = read_file(file_name)
        for row in file.split('\n'):
            if row.find('$') == 0:
                continue
            m = re.findall(r'([\w\.]+)\s*', row)
            if len(m) > 0:
                records.append({'name': m[0], 'type': m[1], 'value': m[2]})

        uri = '%s/zones/%s/import' % (self.baseuri, oid)
        res = self.cmp_put(uri, data={'records': records})
        self.app.render({'msg': 'import records: %s' % records})

    @ex(
        help='get dns recordas',
        description='get dns recordas',
        arguments=PARGS([
            (['-id'], {'help': 'project id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'dns name', 'action': 'store', 'type': str, 'default': None}),
            (['-ip_addr'], {'help': 'ip address', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'zone name', 'action': 'store', 'type': str, 'default': None}),
            (['-show_expired'], {'help': 'if True show record DELETED', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def recorda_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/recordas/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('recorda')
                resolution = res.pop('details')
                self.app.render(res, details=True)

                self.c('\nresolution', 'underline')
                self.app.render(resolution, headers=['start_nameserver', 'ip_address'], maxsize=200)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'ip_addr', 'parent', 'show_expired']
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/recordas' % self.baseuri
            res = self.cmp_get(uri, data=data)
            headers = ['id', 'name', 'ip_address', 'state', 'zone', 'container', 'creation']
            fields = ['uuid', 'name', 'ip_address', 'state', 'parent', 'container', 'date.creation']
            self.app.render(res, key='recordas', headers=headers, fields=fields)

    @ex(
        help='create new record A (ip address -> hostname.zone)',
        description='create new record A (ip address -> hostname.zone)',
        arguments=PARGS([
            (['ipaddress'], {'help': 'ip address', 'action': 'store', 'type': str, 'default': None}),
            (['hostname'], {'help': 'host name', 'action': 'store', 'type': str, 'default': None}),
            (['zone'], {'help': 'zone name', 'action': 'store', 'type': str, 'default': None}),
            (['-ttl'], {'help': 'time to livee', 'action': 'store', 'type': int, 'default': 86400})
        ])
    )
    def recorda_add(self):
        ip_addr = self.app.pargs.ipaddress
        host_name = self.app.pargs.hostname
        zone = self.app.pargs.zone
        ttl = self.app.pargs.ttl

        # get zone
        uri = '%s/zones/%s' % (self.baseuri, zone)
        zone = self.cmp_get(uri,data='').get('zone', {})

        uri = '%s/recordas' % self.baseuri
        data = {
            'container': str(zone.get('container')),
            'zone': zone.get('name'),
            'ip_addr': ip_addr,
            'name': host_name,
            'ttl': ttl
        }
        self.cmp_post(uri, data={'recorda': data})
        resp = {'msg': 'Create new record A (%s, %s, %s)' % (ip_addr, host_name, zone.get('name'))}
        self.app.render(resp, headers=['msg'])

    @ex(
        help='delete an existing record A (ip address -> hostname.zone)',
        description='delete an existing record A (ip address -> hostname.zone)',
        arguments=PARGS([
            (['id'], {'help': 'record id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def recorda_delete(self):
        record_id = self.app.pargs.id
        uri = '%s/recordas/%s' % (self.baseuri, record_id)
        self.cmp_delete(uri, data='', entity='record A %s' % record_id)

    @ex(
        help='get dns record cnames',
        description='get dns record cnames',
        arguments=PARGS([
            (['-id'], {'help': 'project id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'dns name', 'action': 'store', 'type': str, 'default': None}),
            (['-host_name'], {'help': 'host name', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'zone name', 'action': 'store', 'type': str, 'default': None}),
            (['-show_expired'], {'help': 'if True show record DELETED', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def record_cname_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/record_cnames/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('record_cname')
                resolution = res.pop('details')
                self.app.render(res, details=True)

                self.c('\nresolution', 'underline')
                self.app.render(resolution, headers=['start_nameserver', 'base_fqdn'], maxsize=200)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'base_fqdn', 'parent', 'show_expired']
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/record_cnames' % self.baseuri
            res = self.cmp_get(uri, data=data)
            headers = ['id', 'name', 'host_name', 'state', 'zone', 'container', 'creation']
            fields = ['uuid', 'name', 'host_name', 'state', 'parent', 'container', 'date.creation']
            self.app.render(res, key='record_cnames', headers=headers, fields=fields)

    @ex(
        help='create new record CNAME (alias -> hostname.zone)',
        description='create new record CNAME (alias -> hostname.zone)',
        arguments=PARGS([
            (['name'], {'help': 'alias to set', 'action': 'store', 'type': str, 'default': None}),
            (['hostname'], {'help': 'host name', 'action': 'store', 'type': str, 'default': None}),
            (['zone'], {'help': 'zone name', 'action': 'store', 'type': str, 'default': None}),
            (['-ttl'], {'help': 'time to live', 'action': 'store', 'type': int, 'default': 86400})
        ])
    )
    def record_cname_add(self):
        name = self.app.pargs.name
        host_name = self.app.pargs.hostname
        zone = self.app.pargs.zone
        ttl = self.app.pargs.ttl

        # get zone
        uri = '%s/zones/%s' % (self.baseuri, zone)
        zone = self.cmp_get(uri, data='').get('zone', {})

        uri = '%s/record_cnames' % self.baseuri
        data = {
            'container': str(zone.get('container')),
            'zone': zone.get('name'),
            'name': name,
            'host_name': host_name,
            'ttl': ttl
        }
        self.cmp_post(uri, data={'record_cname': data})
        resp = {'msg': 'Create new record cname (%s, %s, %s)' % (name, host_name, zone.get(u'name'))}
        self.app.render(resp, headers=['msg'])

    @ex(
        help='delete an existing record CNAME',
        description='delete an existing record CNAME',
        arguments=PARGS([
            (['id'], {'help': 'record id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def record_cname_delete(self):
        record_id = self.app.pargs.id
        uri = '%s/record_cnames/%s' % (self.baseuri, record_id)
        self.cmp_delete(uri, data='', entity='record cname %s' % record_id)
