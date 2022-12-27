# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 Regione Piemonte

from beecell.simple import merge_list
from beedrones.dns.client import DnsManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS, StringAction
from cement import ex
from beehive3_cli.core.util import load_environment_config, load_config


def DNS_ARGS(*list_args):
    orchestrator_args = [
        (['-O', '--orchestrator'], {'action': 'store', 'dest': 'orchestrator',
                                    'help': 'dns platform reference label'}),
        (['-P', '--project'], {'action': 'store', 'dest': 'project', 'help': 'dns current project name'}),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class DnsPlatformController(BaseController):
    class Meta:
        label = 'dns'
        stacked_on = 'platform'
        stacked_type = 'nested'
        description = "dns platform"
        help = "dns platform"

    def pre_command_run(self):
        super(DnsPlatformController, self).pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get('orchestrators', {}).get('dns', {})
        label = getattr(self.app.pargs, 'orchestrator', None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception('No dns default platform is available for this environment. Select '
                                'another environment')

        if label not in orchestrators:
            raise Exception('Valid label are: %s' % ', '.join(orchestrators.keys()))
        conf = orchestrators.get(label)

        self.client = DnsManager(conf.get('serverdns'), zones=conf.get('zones'), dnskey=conf.get('key'),
                                 key=self.key)

    @ex(
        help='ping dns',
        description='ping dns',
        arguments=DNS_ARGS()
    )
    def ping(self):
        res = self.client.ping()
        self.app.render({'ping': res}, headers=['ping'])

    @ex(
        help='get dns version',
        description='get dns version',
        arguments=DNS_ARGS()
    )
    def version(self):
        res = self.client.version()
        self.app.render({'version': res}, headers=['version'])

    @ex(
        help='get all the configured orchestrators',
        description='get all the configured orchestrators',
        arguments=DNS_ARGS()
    )
    def zone_orchestrator_get(self):
        orchestrators = self.config.get('orchestrators', {}).get('dns', {})

        # orchestrators = self.configs['environments'][self.env]['orchestrators'].get('dns')
        resp = []
        for k, v in orchestrators.items():
            update = True
            if v.get('key', {}) == {}:
                update = False
            item = {
                'name': k,
                'nameservers': v.get('serverdns', {}).get('resolver', []),
                'zones': v.get('zones', []),
                'support_update': update
            }
            resp.append(item)
        self.app.render(resp, headers=['name', 'nameservers', 'zones', 'support_update'], maxsize=200)

    @ex(
        help='get all the managed zones',
        description='get all the managed zones',
        arguments=DNS_ARGS()
    )
    def zone_get(self):
        zones = self.client.get_managed_zones()
        resp = [{'label': k, 'zone': v} for k, v in zones.items()]
        self.app.render(resp, headers=['label', 'zone'])

    @ex(
        help='get all the nameservers that resolve the zone',
        description='get all the nameservers that resolve the zone',
        arguments=DNS_ARGS([
            (['id'], {'help': 'zone', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def zone_nameserver_get(self):
        zone = self.app.pargs.id
        res = self.client.query_nameservers(zone, timeout=1.0)
        resp = []
        for k, vs in res.items():
            if vs is not None:
                for v in vs:
                    resp.append({
                        'start-nameserver': k,
                        'ip_addr': v[0],
                        'fqdn': v[1]
                    })
        self.app.render(resp, headers=['start-nameserver', 'ip_addr', 'fqdn'])

    @ex(
        help='the SOA (Start of Authority) used to manage the zone',
        description='the SOA (Start of Authority) used to manage the zone',
        arguments=DNS_ARGS([
            (['id'], {'help': 'zone', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def zone_authority_get(self):
        """
        - start-nameserver: dns queried
        - mname: The <domain-name> of the name server that was the original or primary source of data for this zone.
        - rname: A <domain-name> which specifies the mailbox of the person responsible for this zone.
        - serial: The unsigned 32 bit version number of the original copy of the zone. Zone transfers preserve this
            value. This value wraps and should be compared using sequence space arithmetic.
        - refresh: A 32 bit time interval before the zone should be refreshed.
        - retry: A 32 bit time interval that should elapse before a failed refresh should be retried.
        - expire: A 32 bit time value that specifies the upper limit on the time interval that can elapse before the
            zone is no longer authoritative.
        - minimum: The unsigned 32 bit minimum TTL field that should be exported with any RR from this zone.
        All times are in units of seconds.
        """
        zone = self.app.pargs.id
        res = self.client.query_authority(zone)
        resp = []
        for k, v in res.items():
            v['start-nameserver'] = k
            resp.append(v)
        self.app.render(resp, headers=['start-nameserver', 'rname', 'mname', 'retry', 'minimum', 'refresh',
                                       'expire', 'serial'])

    @ex(
        help='get ip address form fqdn',
        description='get ip address form fqdn',
        arguments=DNS_ARGS([
            (['fqdn'], {'help': 'fqdn', 'action': 'store', 'type': str, 'default': None}),
            (['-group'], {'help': 'dns group. Can be resolver or update [default=resolver]', 'action': 'store',
                          'type': str, 'default': 'resolver'}),
        ])
    )
    def zone_fqdn_query(self):
        host = self.app.pargs.fqdn
        group = self.app.pargs.group
        res = self.client.query_record_A(host, timeout=1.0, group=group)
        resp = []
        for k, v in res.items():
            resp.append({
                'start-nameserver': k,
                'ip-address': v
            })
        self.app.render(resp, headers=['start-nameserver', 'ip-address'])

    @ex(
        help='get fqdn address form alias',
        description='get fqdn address form alias',
        arguments=DNS_ARGS([
            (['alias'], {'help': 'alias', 'action': 'store', 'type': str, 'default': None}),
            (['-group'], {'help': 'dns group. Can be resolver or update [default=resolver]', 'action': 'store',
                          'type': str, 'default': 'resolver'}),
        ])
    )
    def zone_alias_query(self):
        alias = self.app.pargs.alias
        group = self.app.pargs.group
        res = self.client.query_record_CNAME(alias, timeout=1.0, group=group)
        resp = []
        for k, v in res.items():
            resp.append({
                'start-nameserver': k,
                'base-fqdn': v
            })
        self.app.render(resp, headers=['start-nameserver', 'base-fqdn'])

    '''
    class DnsRecordAControllerChild(DnsControllerChild):
        baseuri = u'/v1.0/nrs'
        subsystem = u'resource'
    
        class Meta:
            label = 'dns.recordas'
            aliases = ['recordas']
            aliases_only = True
            description = "Dns record A management"
    
        @expose(aliases=[u'list [field=..]'], aliases_only=True)
        @check_error
        def list(self):
            """List all the dns recordas
    
    fields:
      name                  host name [optional]
      ip_addr               ip address [optional]
      zone                  zone name [optional]
      show_expired          if True show record DELETED [optional]
      page                  list page [default=0]
      size                  list page size [default=10]
      field                 list sort field [default=id]
      order                 list sort order [default=DESC]"""
            zone = self.get_arg(name=u'zone', default=None, keyvalue=True)
            data = self.get_list_default_arg()
            data.update(self.app.kvargs)
            if zone is not None:
                data[u'parent'] = zone
            uri = u'%s/dns/recordas' % self.baseuri
            res = self._call(uri, u'GET', data=urllib.urlencode(data))
            headers = [u'id', u'name', u'ip_address', u'state', u'zone', u'container', u'creation']
            fields = [u'uuid', u'name', u'ip_address', u'state', u'parent.name', u'container.name', u'date.creation']
            self.result(res, key=u'recordas', headers=headers, fields=fields)
    
        @expose(aliases=[u'get <recorda>'], aliases_only=True)
        @check_error
        def get(self):
            """Get a dns recorda
    
    fields:
      zone                  zone nome or uuid"""
            zone = self.get_arg(name=u'recorda')
            uri = u'%s/dns/recordas/%s' % (self.baseuri, zone)
            res = self._call(uri, u'GET', data=u'')
            if self.format == u'text':
                resolution = res.get(u'recorda').pop(u'details')
                self.result(res, key=u'recorda', details=True, maxsize=200)
                self.output(u'resolution:')
                self.result(resolution, headers=[u'start_nameserver', u'ip_address'], maxsize=200)
            else:
                self.result(res, key=u'recorda', details=True, maxsize=200)
    
        @expose(aliases=[u'add <ip-address> <host-name> <zone> [ttl=..]'], aliases_only=True)
        @check_error
        def add(self):
            """Create new record A (ip address -> hostname.zone)
    
    fields:
      ip-address            ip address
      host-name             host name
      zone                  zone name
      ttl                   time to live [optional]"""
            ip_addr = self.get_arg(name=u'ip-address')
            host_name = self.get_arg(name=u'host-name')
            zone = self.get_arg(name=u'zone')
            ttl = self.get_arg(name=u'ttl', keyvalue=True, default=86400)
    
            # get zone
            uri = u'%s/dns/zones/%s' % (self.baseuri, zone)
            zone = self._call(uri, u'GET', data=u'').get(u'zone', {})
    
            uri = u'%s/dns/recordas' % self.baseuri
            data = {
                u'container': zone.get(u'container').get(u'uuid'),
                u'zone': zone.get(u'name'),
                u'ip_addr': ip_addr,
                u'name': host_name,
                u'ttl': ttl
            }
            res = self._call(uri, u'POST', data={u'recorda': data})
            resp = {u'msg': u'Create new record A (%s, %s, %s)' % (ip_addr, host_name, zone.get(u'name'))}
            self.result(resp, headers=[u'msg'], maxsize=300)
    
        @expose(aliases=[u'delete <record-id>'], aliases_only=True)
        @check_error
        def delete(self):
            """Delete an existing record A (ip address -> hostname.zone)
    
    fields:
      record-id             dns record id"""
            record_id = self.get_arg(name=u'record-id')
            uri = u'%s/dns/recordas/%s' % (self.baseuri, record_id)
            zone = self._call(uri, u'DELETE', data=u'')
            resp = {u'msg': u'Delete record A (%s, %s)' % (record_id, zone)}
            self.result(resp, headers=[u'msg'], maxsize=300)
    
    
    class DnsRecordCnameControllerChild(DnsControllerChild):
        baseuri = u'/v1.0/nrs'
        subsystem = u'resource'
    
        class Meta:
            label = 'dns.recordcnames'
            aliases = ['recordcnames']
            aliases_only = True
            description = "Dns record A management"
    
        @expose(aliases=[u'list [field=..]'], aliases_only=True)
        @check_error
        def list(self):
            """List all the dns recordcnames
    
    fields:
      host_name                  host name [optional]
      name                  name [optional]
      zone                  zone name [optional]
      show_expired          if True show record DELETED [optional]
      page                  list page [default=0]
      size                  list page size [default=10]
      field                 list sort field [default=id]
      order                 list sort order [default=DESC]"""
            zone = self.get_arg(name=u'zone', default=None, keyvalue=True)
            data = self.get_list_default_arg()
            data.update(self.app.kvargs)
            if zone is not None:
                data[u'parent'] = zone
            uri = u'%s/dns/record_cnames' % self.baseuri
            res = self._call(uri, u'GET', data=urllib.urlencode(data))
            headers = [u'id', u'name', u'host_name', u'state', u'zone', u'container', u'creation']
            fields = [u'uuid', u'name', u'host_name', u'state', u'parent.name', u'container.name', u'date.creation']
            self.result(res, key=u'record_cnames', headers=headers, fields=fields)
    
        @expose(aliases=[u'get <recordcname>'], aliases_only=True)
        @check_error
        def get(self):
            """Get a dns recordcname
    
    fields:
      zone                  zone nome or uuid"""
            zone = self.get_arg(name=u'recordcname')
            uri = u'%s/dns/record_cnames/%s' % (self.baseuri, zone)
            res = self._call(uri, u'GET', data=u'')
            if self.format == u'text':
                resolution = res.get(u'record_cname').pop(u'details')
                self.result(res, key=u'record_cname', details=True, maxsize=200)
                self.output(u'resolution:')
                self.result(resolution, headers=[u'start_nameserver', u'base_fqdn'], maxsize=200)
            else:
                self.result(res, key=u'record_cname', details=True, maxsize=200)
    
        @expose(aliases=[u'add <name> <host-name> <zone> [ttl=..]'], aliases_only=True)
        @check_error
        def add(self):
            """Create new record A (ip address -> hostname.zone)
    
    fields:
      name                  alias to set
      host-name             host name
      zone                  zone name
      ttl                   time to live [optional]"""
            name = self.get_arg(name=u'name')
            host_name = self.get_arg(name=u'host-name')
            zone = self.get_arg(name=u'zone')
            ttl = self.get_arg(name=u'ttl', keyvalue=True, default=86400)
    
            # get zone
            uri = u'%s/dns/zones/%s' % (self.baseuri, zone)
            zone = self._call(uri, u'GET', data=u'').get(u'zone', {})
    
            uri = u'%s/dns/record_cnames' % self.baseuri
            data = {
                u'container': zone.get(u'container').get(u'uuid'),
                u'zone': zone.get(u'name'),
                u'name': name,
                u'host_name': host_name,
                u'ttl': ttl
            }
            res = self._call(uri, u'POST', data={u'record_cname': data})
            resp = {u'msg': u'Create new record cname (%s, %s, %s)' % (name, host_name, zone.get(u'name'))}
            self.result(resp, headers=[u'msg'], maxsize=300)
    
        @expose(aliases=[u'delete <record-id>'], aliases_only=True)
        @check_error
        def delete(self):
            """Delete an existing record A (ip address -> hostname.zone)
    
    fields:
      record-id             dns record id"""
            record_id = self.get_arg(name=u'record-id')
            uri = u'%s/dns/record_cnames/%s' % (self.baseuri, record_id)
            zone = self._call(uri, u'DELETE', data=u'')
            resp = {u'msg': u'Delete record cname (%s, %s)' % (record_id, zone)}
            self.result(resp, headers=[u'msg'], maxsize=300)
    '''