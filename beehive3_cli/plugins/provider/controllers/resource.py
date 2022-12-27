# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from datetime import datetime
from time import time

from beecell.file import read_file
from beecell.types.type_id import id_gen
from beehive3_cli.core.controller import BaseController, PARGS, ARGS
from beecell.types.type_string import truncate, bool2str,str2bool
from beecell.types.type_dict import dict_get
from six.moves.urllib.parse import urlencode
from cement.ext.ext_argparse import ex
from beehive3_cli.core.util import load_config


class ResourceProviderController(BaseController):
    class Meta:
        label = 'res_provider'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'provider management'
        help = 'provider management'

        cmp = {'baseuri': '/v1.0/nrs/provider', 'subsystem': 'resource'}

        headers = ['id', 'uuid', 'name', 'parent', 'state', 'creation', 'modified']
        fields = ['id', 'uuid', 'name', 'parent', 'state', 'date.creation', 'date.modified']
        region_headers = ['id', 'uuid', 'name', 'parent', 'state', 'creation', 'modified']
        region_fields = ['id', 'uuid', 'name', 'parent', 'state', 'date.creation', 'date.modified']
        site_headers = ['id', 'uuid', 'name', 'parent', 'state', 'creation', 'modified', 'orchestrators']
        site_fields = ['id', 'uuid', 'name', 'parent', 'state', 'date.creation', 'date.modified',
                       'orchestrators']
        site_network_headers = ['uuid', 'name', 'desc', 'state', 'creation', 'vlan', 'subnets', 'zabbix_proxy']
        site_network_fields = ['uuid', 'name', 'desc', 'state', 'date.creation',
                               'attributes.configs.vlan', 'attributes.configs.subnets',
                               'attributes.configs.zabbix_proxy']
        compute_zones_headers = ['id', 'name', 'desc', 'state', 'availability_zones', 'creation', 'modified']
        compute_zones_fields = ['uuid', 'name', 'desc', 'state', 'availability_zones', 'date.creation', 'date.modified']
        vpc_headers = ['id', 'uuid', 'name', 'parent', 'state', 'type', 'cidr', 'creation', 'modified']
        vpc_fields = ['id', 'uuid', 'name', 'parent', 'state', 'attributes.configs.type', 'attributes.configs.cidr',
                      'date.creation', 'date.modified']
        security_group_headers = ['id', 'uuid', 'name', 'parent', 'compute_zone', 'state', 'creation', 'modified',
                                  'rules']
        security_group_fields = ['id', 'uuid', 'name', 'parent', 'compute_zone', 'state', 'date.creation',
                                 'date.modified', 'rules']
        rule_headers = ['id', 'uuid', 'name', 'parent', 'state', 'creation', 'modified']
        rule_fields = ['id', 'uuid', 'name', 'parent', 'state', 'date.creation', 'date.modified']
        instance_fields = ['id', 'parent', 'name', 'availability_zone.name', 'hypervisor', 'attributes.host', 'state',
                           'runstate', 'os', 'vpcs.0.name', 'security_groups.0.name', 'flavor.vcpus', 'flavor.memory',
                           'volume.size', 'volume.num', 'vpcs.0.fixed_ip.ip',
                           'attributes.backup_enabled', 'attributes.monitoring_enabled', 'attributes.logging_enabled']
        instance_headers = ['id', 'parent', 'name', 'av_zone', 'type', 'host', 'state', 'runstate', 'os',
                            'vpc', 'sg', 'cpu', 'ram', 'disk', 'disk #', 'ip', 'bck', 'monit', 'logfw']
        flavor_headers = ['id', 'uuid', 'name', 'parent', 'state', 'creation', 'vcpus', 'memory', 'disk']
        flavor_fields = ['id', 'uuid', 'name', 'parent', 'state', 'date.creation', 'attributes.configs.vcpus',
                         'attributes.configs.memory', 'attributes.configs.disk']
        image_headers = ['id', 'name', 'parent', 'state', 'os', 'os-ver', 'min-disk-size', 'modified', 'hypervisors']
        image_fields = ['uuid', 'name', 'parent', 'state', 'attributes.configs.os', 'attributes.configs.os_ver',
                        'attributes.configs.min_disk_size', 'date.modified', 'availability_zones.0.hypervisors']
        share_headers = ['id', 'name', 'parent', 'state', 'type', 'proto', 'size', 'vpc', 'export', 'creation']
        share_fields = ['uuid', 'name', 'parent', 'state', 'details.type', 'details.proto', 'details.size',
                        'vpcs.0.name', 'details.export', 'date.creation']
        volume_fields = ['id', 'name', 'parent', 'availability_zone.name', 'flavor.name', 'hypervisor', 'bootable',
                         'encrypted', 'state', 'size', 'used', 'instance.uuid']
        volume_headers = ['id', 'name', 'parent', 'av_zone', 'flavor', 'hypervisor', 'bootable', 'encrypted', 'state',
                          'size', 'used', 'instance']
        volumeflavor_fields = ['id', 'name', 'desc', 'parent', 'state', 'attributes.configs.disk_iops']
        volumeflavor_headers = ['id', 'name', 'desc', 'parent', 'state', 'disk_iops']
        customization_headers = ['id', 'name', 'parent', 'state', 'creation', 'modified', 'orchestrators']
        customization_fields = ['id', 'name', 'parent', 'state', 'date.creation', 'date.modified']
        gateway_headers = ['id', 'name', 'parent', 'state', 'type', 'flavor', 'external_ip_address', 'vpcs',
                           'bastion', 'creation']
        gateway_fields = ['id', 'name', 'parent_desc', 'state', 'attributes.type', 'attributes.flavor',
                          'external_ip_address', 'vpcs', 'bastion', 'date.creation']

    def get_container(self):
        """Get container provider"""
        data = urlencode({'container_type': 'Provider'})
        uri = '/v1.0/nrs/containers'
        res = self.cmp_get(uri, data=data)['resourcecontainers'][0]['id']
        self.app.log.info('Get resource container: %s' % truncate(res))
        return str(res)

    def pre_command_run(self):
        super(ResourceProviderController, self).pre_command_run()

        self.configure_cmp_api_client()

    #
    # region
    #
    @ex(
        help='get region(s)',
        description='get region(s)',
        arguments=PARGS([
            (['-id'], {'help': 'region id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def region_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = self.baseuri + '/regions/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('region')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            uri = '%s/regions' % self.baseuri
            res = self.cmp_get(uri)
            self.app.render(res, key='regions', headers=self._meta.region_headers, fields=self._meta.region_fields)

    @ex(
        help='add region',
        description='add region',
        arguments=ARGS([
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def region_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + '/regions'
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add region %s' % res['uuid']})

    @ex(
        help='delete region',
        description='delete region',
        arguments=ARGS([
            (['id'], {'help': 'region id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def region_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = self.baseuri + '/regions/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='region %s' % oid)

    @ex(
        help='update region',
        description='update region',
        arguments=ARGS([
            (['id'], {'help': 'region id', 'action': 'store', 'type': str, 'default': None}),
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def region_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + '/regions/%s' % oid
        res = self.cmp_put(uri, data=data)
        self.app.log.info('Update %s: %s' % (self._meta.alias, truncate(res)))
        self.app.render({'msg': 'update region %s' % res['uuid']})

    #
    # site
    #
    @ex(
       help='get site(s)',
       description='get site(s)',
       arguments=PARGS([
           (['-id'], {'help': 'site id', 'action': 'store', 'type': str, 'default': None})
       ])
    )
    def site_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/sites/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('site')
                attributes = res.pop('attributes')
                orchestrators = res.pop('orchestrators')
                limits = attributes.pop('limits')
                attributes.pop('orchestrators')
                self.app.render(res, details=True)
                self.c('\n\nattributes', 'underline')
                self.app.render(attributes, details=True)
                self.c('\n\norchestrators', 'underline')
                self.app.render(orchestrators, headers=['id', 'name', 'type', 'tag', 'ping', 'config'], maxsize=100)
                self.c('\n\nlimits', 'underline')
                self.app.render(limits, details=True)
            else:
                self.app.render(res, details=True)
        else:
            uri = '%s/sites' % self.baseuri
            res = self.cmp_get(uri)
            transform = {
                'orchestrators': lambda x: '\n'.join(['%-18s%s' % (o['name'], o['ping']) for o in x])}
            self.app.render(res, key='sites', headers=self._meta.site_headers, fields=self._meta.site_fields,
                            transform=transform, maxsize=400)

    @ex(
        help='add site',
        description='add site',
        arguments=ARGS([
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def site_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + '/sites'
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add site %s' % res['uuid']})

    @ex(
        help='delete site',
        description='delete site',
        arguments=ARGS([
            (['id'], {'help': 'site id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def site_delete(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = self.baseuri + '/sites/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='site %s' % oid)

    @ex(
        help='update site',
        description='update site',
        arguments=ARGS([
            (['id'], {'help': 'site id', 'action': 'store', 'type': str, 'default': None}),
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def site_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + '/sites/%s' % oid
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'update site %s' % res['uuid']})

    @ex(
       help='get site orchestrators',
       description='get site orchestrators',
       arguments=ARGS([
           (['id'], {'help': 'site id', 'action': 'store', 'type': str, 'default': None})
       ])
    )
    def site_orchestrator_get(self):
        oid = self.app.pargs.id
        uri = '%s/sites/%s' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        res = res.get('site')
        attributes = res.pop('attributes')
        orchestrators = attributes.pop('orchestrators')

        if self.is_output_text():
            for orchestrator in orchestrators:
                self.c('\n\n' + orchestrator['id'], 'underline')
                self.app.render(orchestrator, details=True)
        else:
            self.app.render(res, details=True)

    @ex(
       help='add site orchestrator',
       description='add site orchestrator',
       arguments=ARGS([
           (['id'], {'help': 'site id', 'action': 'store', 'type': str, 'default': None}),
           (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
       ])
    )
    def site_orchestrator_add(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '%s/sites/%s/orchestrators' % (self.baseuri, oid)
        self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add orchestrator to site %s' % oid})

    @ex(
       help='delete site orchestrator',
       description='delete site orchestrator',
       arguments=ARGS([
           (['id'], {'help': 'site id', 'action': 'store', 'type': str, 'default': None}),
           (['orchestrator'], {'help': 'orchestrator id', 'action': 'store', 'type': str, 'default': None}),
       ])
    )
    def site_orchestrator_del(self):
        oid = self.app.pargs.id
        orchestrator = self.app.pargs.orchestrator
        data = {'orchestrator': {'id': orchestrator}}
        uri = '%s/sites/%s/orchestrators' % (self.baseuri, oid)
        self.cmp_delete(uri, data=data)
        self.app.render({'msg': 'delete orchestrator from site %s' % oid})

    #
    # site network
    #
    @ex(
       help='get site network(s)',
       description='get site network(s)',
       arguments=PARGS([
           (['-id'], {'help': 'site network id', 'action': 'store', 'type': str, 'default': None}),
           (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
           (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
           (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
           (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
           (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
       ])
    )
    def site_network_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v2.0/nrs/provider/site_networks/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('site_network')
                attributes = res.pop('attributes').pop('configs')
                subnets = attributes.pop('subnets')
                self.app.render(res, details=True)
                self.c('\n\nattributes', 'underline')
                self.app.render(attributes, details=True)
                self.c('\n\nsubnets', 'underline')
                self.app.render(subnets, headers=['cidr', 'allocable', 'enable_dhcp', 'gateway', 'dns_nameservers',
                                                  'allocation_pools', 'vsphere_id', 'openstack_id'])
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v2.0/nrs/provider/site_networks'
            res = self.cmp_get(uri, data=data)
            transform = {'attributes.configs.subnets': lambda x: ','.join([s['cidr'] for s in x if x is not None])}
            self.app.render(res, key='site_networks', headers=self._meta.site_network_headers,
                            fields=self._meta.site_network_fields, transform=transform, maxsize=100)

    @ex(
        help='add site network',
        description='add site network',
        arguments=ARGS([
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def site_network_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '/v2.0/nrs/provider/site_networks'
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add site network %s' % res['uuid']})

    @ex(
        help='delete site network',
        description='delete site network',
        arguments=ARGS([
            (['id'], {'help': 'site network id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def site_network_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = '/v2.0/nrs/provider/site_networks/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='site network %s' % oid)

    @ex(
        help='update site network',
        description='update site network',
        arguments=ARGS([
            (['id'], {'help': 'site network id', 'action': 'store', 'type': str, 'default': None}),
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def site_network_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '/v2.0/nrs/provider/site_networks/%s' % oid
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'update site network %s' % res['uuid']})

    @ex(
        help='add site network subnet',
        description='add site network subnet',
        arguments=ARGS([
            (['id'], {'help': 'site network id', 'action': 'store', 'type': str, 'default': None}),
            (['cidr'], {'help': 'subnet cidr', 'action': 'store', 'type': str, 'default': None}),
            (['pools'], {'help': 'allocation pools. Syntax: openstack:<start-ip>:<stop-ip>,vmware:<start-ip>:<stop-ip>',
                         'action': 'store', 'type': str, 'default': None}),
            (['-gw'], {'help': 'default gateway', 'action': 'store', 'type': str, 'default': None}),
            (['-enable_dhcp'], {'help': 'if true enable dhcp', 'action': 'store', 'type': str, 'default': 'false'}),
            (['-allocable'], {'help': 'if true subnet is allocable', 'action': 'store', 'type': str, 'default':
                'false'}),
        ])
    )
    def site_network_subnet_add(self):
        oid = self.app.pargs.id
        cidr = self.app.pargs.cidr
        pools = self.app.pargs.pools
        gw = self.app.pargs.gw
        enable_dhcp = str2bool(self.app.pargs.enable_dhcp)
        allocable = str2bool(self.app.pargs.allocable)
        uri = '/v2.0/nrs/provider/site_networks/%s/subnets' % oid
        allocation_pools = {}
        for pool in pools.split(','):
            pool = pool.split(':')
            allocation_pools[pool[0]] = [{'start': pool[1], 'end': pool[2]}]
        data = {
            'cidr': cidr,
            'allocation_pools': allocation_pools,
            'enable_dhcp': enable_dhcp,
            'allocable': allocable
        }
        if gw is not None:
            data['gateway'] = gw

        '''
              - cidr: 10.103.52.0/24
                allocation_pools:
                  openstack:
                    - start: 10.103.52.2
                      end: 10.103.52.253
                enable_dhcp: false
                allocable: false
        '''

        self.cmp_post(uri, data={'subnets': [data]})
        self.app.render({'msg': 'delete subnet %s' % cidr})

    @ex(
        help='delete site network subnet',
        description='delete site network subnet',
        arguments=ARGS([
            (['id'], {'help': 'site network id', 'action': 'store', 'type': str, 'default': None}),
            (['cidr'], {'help': 'subnet cidr', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def site_network_subnet_del(self):
        oid = self.app.pargs.id
        cidr = self.app.pargs.cidr
        uri = '/v2.0/nrs/provider/site_networks/%s/subnets' % oid
        data = {'subnets': [{'cidr': cidr}]}
        self.cmp_delete(uri, data=data, entity='subnet %s' % cidr)

    #
    # compute zone
    #
    def __is_managed(self, oid):
        # get ssh management status
        uri = self.baseuri + '/compute_zones/%s/manage' % oid
        mgt = self.cmp_get(uri, 'GET').get('is_managed', [])
        res = {
            'is-managed': bool2str(mgt),
            'has-backup': 'false',
            'has-monitor': 'false',
        }
        return res

    def __get_availability_zones(self, oid):
        # get ssh management status
        uri = self.baseuri + '/compute_zones/%s/availability_zones' % oid
        res = self.cmp_get(uri, 'GET').get('availability_zones', [])
        return res

    @ex(
        help='get provider computes zone',
        description='get provider computes zone(s)',
        arguments=PARGS([
            (['-id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'compute zone name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'compute zone description', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def compute_zone_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = self.baseuri + '/compute_zones/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('compute_zone')
                res.pop('availability_zones', None)
                self.app.render(res, details=True)
                avz = self.__get_availability_zones(oid)
                self.c('\n\navailability_zones', 'underline')
                self.app.render(avz, fields=['id', 'name', 'state', 'site.id', 'site.name'],
                                headers=['id', 'name', 'state', 'site-id', 'site-name'])
                self.c('\n\nconfigs', 'underline')
                config = self.__is_managed(oid)
                self.app.render(config, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'tags']
            mappings = {
                'name': lambda n: '%' + n + '%',
                'desc': lambda n: '%' + n + '%'
            }
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/compute_zones' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='compute_zones', headers=self._meta.compute_zones_headers,
                            fields=self._meta.compute_zones_fields)

    @ex(
        help='add compute zone',
        description='add compute zone',
        arguments=ARGS([
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def compute_zone_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + '/compute_zones'
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add compute zone %s' % res['uuid']})

    @ex(
        help='delete compute zone',
        description='delete compute zone',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def compute_zone_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = self.baseuri + '/compute_zones/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='compute zone %s' % oid)

    @ex(
        help='update compute zone',
        description='update compute zone',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def compute_zone_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + '/compute_zones/%s' % oid
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'update compute zone %s' % res['uuid']})

    @ex(
        help='enable provider computes zone management by ssh module',
        description='enable provider computes zone management by ssh module',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def compute_zone_manage(self):
        oid = getattr(self.app.pargs, 'id', None)
        uri = self.baseuri + '/compute_zones/%s/manage' % oid
        res = self.cmp_post(uri).get('manage', [])
        msg = 'Enable compute zone %s management with ssh group: %s' % (oid, res)
        self.app.log.info(msg)
        self.app.render({'msg': msg}, headers=['msg'], maxsize=200)

    @ex(
        help='disable provider computes zone management by ssh module',
        description='disable provider computes zone management by ssh module',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def compute_zone_unmanage(self):
        oid = getattr(self.app.pargs, 'id', None)
        uri = self.baseuri + '/compute_zones/%s/manage' % oid
        res = self.cmp_delete(uri)
        msg = 'Disable compute zone %s management with ssh group: %s' % (oid, res)
        self.app.log.info(msg)
        self.app.render({'msg': msg}, headers=['msg'], maxsize=200)

    @ex(
        help='list compute zone ssh keys available',
        description='list compute zone ssh keys available',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def compute_zone_sshkeys(self):
        oid = getattr(self.app.pargs, 'id', None)
        uri = self.baseuri + '/compute_zones/%s/sshkeys' % oid
        res = self.cmp_get(uri).get('sshkeys', [])
        self.app.log.info('Get compute zone %s sshkeys: %s' % (oid, truncate(res)))
        self.app.render(res, key='compute_zones', headers=['id', 'name', 'desc', 'date'],
                        fields=['uuid', 'name', 'desc', 'date.creation'])

    @ex(
        help='get compute zone metrics',
        description='get compute zone metrics',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def compute_zone_metric_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        uri = self.baseuri + '/compute_zones/%s/metrics' % oid
        res = self.cmp_get(uri).get('compute_zone')
        resp = []
        for item in res:
            for m in item.get('metrics'):
                resp.append({
                    'id': item.get('uuid'),
                    'type': item.get('type'),
                    'extraction-date': item.get('extraction_date'),
                    'metric': m.get('key'),
                    'metric-value': m.get('value'),
                    'metric-type': m.get('type'),
                    'metric-unit': m.get('unit'),
                })
        self.app.render(resp, headers=['id', 'type', 'extraction-date', 'metric', 'metric-value', 'metric-unit',
                                       'metric-type'])

    @ex(
        help='pre load compute zones metrics',
        description='pre load compute zones metrics',
        arguments=ARGS()
    )
    def compute_zone_metric_preload(self):
        uri = self.baseuri + '/compute_zones'
        css = self.cmp_get(uri, data={'size': -1}).get('compute_zones')
        for cs in css:
            start = time()
            uri = self.baseuri + '/compute_zones/%s/metrics' % cs['id']
            res = self.cmp_get(uri).get('compute_zone')
            elapsed = time() - start
            print(cs['name'], elapsed)

    @ex(
        help='get provider childs',
        description='get provider childs',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def compute_zone_child_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        uri = self.baseuri + '/compute_zones/%s/childs' % oid
        res = self.cmp_get(uri).get('resources')
        s = sorted(res, key=lambda i: i['name'])
        resp = sorted(s, key=lambda i: i['__meta__']['definition'])
        headers = ['id', 'uuid', 'type', 'name', 'state', 'runstate', 'date']
        fields = ['id', 'uuid', '__meta__.definition', 'name', 'state', 'runstate', 'date.creation']
        self.app.render(resp, headers=headers, fields=fields)

    @ex(
       help='add compute zone availability zone',
       description='add compute zone availability zone',
       arguments=ARGS([
           (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
           (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
       ])
    )
    def compute_zone_availability_zone_add(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '%s/compute_zones/%s/availability_zones' % (self.baseuri, oid)
        self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add availability zone to compute zone %s' % oid})

    @ex(
       help='delete compute zone availability zone',
       description='delete compute zone availability zone',
       arguments=ARGS([
           (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
           (['zone'], {'help': 'availability zone name', 'action': 'store', 'type': str, 'default': None}),
       ])
    )
    def compute_zone_availability_zone_del(self):
        oid = self.app.pargs.id
        zone = self.app.pargs.zone
        data = {'availability_zone': {'id': zone}}
        uri = '%s/compute_zones/%s/availability_zones' % (self.baseuri, oid)
        self.cmp_delete(uri, data=data, entity='availability zone %s from compute zone %s' % (zone, oid))

    @ex(
       help='disable compute zone availability zone',
       description='disable compute zone availability zone',
       arguments=ARGS([
           (['id'], {'help': 'availability zone id', 'action': 'store', 'type': str, 'default': None})
       ])
    )
    def compute_zone_availability_zone_disable(self):
        oid = self.app.pargs.id
        data = {'state': 'DISABLED'}
        uri = '/v1.0/nrs/entities/%s/state' % oid
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'disable availability zone %s' % oid})

    @ex(
       help='enable compute zone availability zone',
       description='enable compute zone availability zone',
       arguments=ARGS([
           (['id'], {'help': 'availability zone id', 'action': 'store', 'type': str, 'default': None})
       ])
    )
    def compute_zone_availability_zone_enable(self):
        oid = self.app.pargs.id
        data = {'state': 'ACTIVE'}
        uri = '/v1.0/nrs/entities/%s/state' % oid
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'enable availability zone %s' % oid})

    @ex(
        help='get compute zone quotas',
        description='get compute zone quotas',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def compute_zone_quota_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        uri = self.baseuri + '/compute_zones/%s/quotas' % oid
        res = self.cmp_get(uri).get('quotas')
        self.app.render(res, headers=['quota', 'value', 'allocated', 'unit'])

    @ex(
        help='get compute zone quotas classes',
        description='get compute zone quotas classes',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def compute_zone_default_quota_get(self):
        oid = self.app.pargs.id
        uri = self.baseuri + '/compute_zones/%s/quotas/classes' % oid
        res = self.cmp_get(uri, 'GET').get('quota_classes', [])
        self.app.render(res, headers=['quota', 'default', 'unit'])

    @ex(
        help='check provider computes zone quota',
        description='check provider computes zone quota',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['quotas'], {'help': 'compute zone quota ex. database.instances', 'action': 'store', 'type': str,
                          'default': None}),
            (['value'], {'help': 'compute zone quota value ex. 3', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def compute_zone_quota_check(self):
        oid = self.app.pargs.id
        quota = self.app.pargs.quota
        value = self.app.pargs.value
        uri = self.baseuri + '/compute_zones/%s/quotas/check' % oid
        res = self.cmp_put(uri, {'quotas': {quota: value}}).get('quotas', [])
        self.app.render(res, headers=['quota', 'default', 'unit'], details=True)

    @ex(
        help='set provider computes zone quota',
        description='set provider computes zone quota',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['quota'], {'help': 'compute zone quota ex. database.instances', 'action': 'store', 'type': str,
                         'default': None}),
            (['value'], {'help': 'compute zone quota value ex. 3', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def compute_zone_quota_set(self):
        oid = self.app.pargs.id
        quota = self.app.pargs.quota
        value = self.app.pargs.value
        try:
            value = int(value)
        except:
            pass
        uri = self.baseuri + '/compute_zones/%s/quotas' % oid
        res = self.cmp_put(uri, {'quotas': {quota: value}}).get('quotas', [])
        self.app.render({'msg': 'set compute zone %s quota %s: %s' % (oid, quota, value)}, maxsize=200)

    @ex(
        help='get compute zone configured backup jobs',
        description='get compute zone configured backup jobs',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['-job'], {'help': 'backup job id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def compute_zone_backup_job_get(self):
        oid = self.app.pargs.id
        job_id = self.app.pargs.job
        if job_id is not None:
            uri = '%s/compute_zones/%s/backup/jobs/%s' % (self.baseuri, oid, job_id)
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('job')
                instances = res.pop('instances', [])
                self.app.render(res, details=True)
                avz = self.__get_availability_zones(oid)
                self.c('\ninstances', 'underline')
                self.app.render(instances, fields=['id', 'name', 'state'],
                                headers=['id', 'name', 'state'])
            else:
                self.app.render(res, details=True)
        else:
            # params = ['name', 'desc', 'tags']
            # mappings = {
            #     'name': lambda n: '%' + n + '%',
            #     'desc': lambda n: '%' + n + '%'
            # }
            # data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/compute_zones/%s/backup/jobs' % (self.baseuri, oid)
            res = self.cmp_get(uri)
            jobs = res.get('jobs')
            headers = ['id', 'name', 'site', 'hypervisor', 'resource_type', 'created', 'updated',
                       'instances', 'usage', 'status', 'schedule']
            fields = ['id', 'name', 'site', 'hypervisor', 'resource_type', 'created', 'updated', 'instances', 'usage',
                      'status', 'schedule.enabled']
            self.app.render(jobs, headers=headers, fields=fields)

    @ex(
        help='add compute zone backup job',
        description='add compute zone backup job',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'job name', 'action': 'store', 'type': str, 'default': None}),
            (['site'], {'help': 'availability zone name', 'action': 'store', 'type': str, 'default': None}),
            (['instances'], {'help': 'comma separated list of instance id', 'action': 'store', 'type': str,
                             'default': None}),
            (['-hypervisor'], {'help': 'hypervisor like openstack or vsphere [openstack]', 'action': 'store',
                               'type': str, 'default': 'openstack'}),
            (['-hypervisor_tag'], {'help': 'hypervisor tag [default]', 'action': 'store', 'type': str,
                                   'default': 'default'}),
            (['-resource_type'], {'help': 'type of resource managed by job. Can be: ComputeInstance [ComputeInstance]',
                                  'action': 'store', 'type': str, 'default': 'ComputeInstance'}),
            (['-fullbackup_interval'], {'help': 'interval between full backup [2]', 'action': 'store', 'type': int,
                                        'default': 2}),
            (['-restore_points'], {'help': 'number of restore points to retain [4]', 'action': 'store', 'type': int,
                                   'default': 4}),
            (['-start_date'], {'help': 'start date like dd/mm/yyyy [now]', 'action': 'store', 'type': str,
                               'default': None}),
            (['-end_date'], {'help': 'end date like dd/mm/yyyy [empty]', 'action': 'store', 'type': str,
                             'default': None}),
            (['-start_time'], {'help': 'start time like 0:00 AM [00:00 AM]', 'action': 'store', 'type': str,
                               'default': '0:00 AM'}),
            (['-interval'], {'help': 'job interval like 24hrs [24hrs]', 'action': 'store', 'type': str,
                             'default': '24hrs'}),
            (['-timezone'], {'help': 'job timezone [Europe/Rome]', 'action': 'store', 'type': str,
                             'default': 'Europe/Rome'}),
            (['-job_type'], {'help': 'job type. Can be: Parallel or Serial [Parallel]', 'action': 'store', 'type': str,
                             'default': 'Parallel'}),
        ])
    )
    def compute_zone_backup_job_add(self):
        oid = self.app.pargs.id
        start_date = self.app.pargs.start_date
        uri = '%s/compute_zones/%s/backup/jobs' % (self.baseuri, oid)
        if start_date is None:
            now = datetime.today()
            start_date = '%s/%s/%s' % (now.day, now.month, now.year)
        data = {
            'name': self.app.pargs.name,
            'site': self.app.pargs.site,
            'hypervisor': self.app.pargs.hypervisor,
            'hypervisor_tag': self.app.pargs.hypervisor_tag,
            'resource_type': self.app.pargs.resource_type,
            'fullbackup_interval': self.app.pargs.fullbackup_interval,
            'restore_points': self.app.pargs.restore_points,
            'start_date': start_date,
            'end_date': self.app.pargs.end_date,
            'start_time': self.app.pargs.start_time,
            'interval': self.app.pargs.interval,
            'timezone': self.app.pargs.timezone,
            'job_type': self.app.pargs.job_type,
            'instances': self.app.pargs.instances.split(','),
        }
        res = self.cmp_post(uri, data=data)
        job = res.get('job')
        self.app.render({'msg': 'add backup job %s' % job})

    @ex(
        help='update compute zone backup job',
        description='update compute zone backup job',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['job'], {'help': 'job id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'job name', 'action': 'store', 'type': str, 'default': None}),
            (['-instances'], {'help': 'comma separated list of <instance id>:<add/del>', 'action': 'store', 'type': str,
                              'default': None}),
            (['-fullbackup_interval'], {'help': 'interval between full backup', 'action': 'store', 'type': int,
                                        'default': None}),
            (['-restore_points'], {'help': 'number of restore points to retain', 'action': 'store', 'type': int,
                                   'default': None}),
            (['-start_date'], {'help': 'start date like dd/mm/yyyy', 'action': 'store', 'type': str, 'default': None}),
            (['-end_date'], {'help': 'end date like dd/mm/yyyy', 'action': 'store', 'type': str, 'default': None}),
            (['-start_time'], {'help': 'start time like 0:00 AM', 'action': 'store', 'type': str,
                               'default': None}),
            (['-interval'], {'help': 'job interval like 24hrs', 'action': 'store', 'type': str,
                             'default': None}),
            (['-timezone'], {'help': 'job timezone', 'action': 'store', 'type': str, 'default': None}),
            (['-job_type'], {'help': 'job type. Can be: Parallel or Serial', 'action': 'store', 'type': str,
                             'default': None}),
            (['-enabled'], {'help': 'if true enable job', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def compute_zone_backup_job_update(self):
        oid = self.app.pargs.id
        job = self.app.pargs.job
        uri = '%s/compute_zones/%s/backup/jobs/%s' % (self.baseuri, oid, job)
        data = {}
        keys = ['name', 'fullbackup_interval', 'restore_points', 'start_date', 'end_date', 'start_time', 'interval',
                'timezone', 'job_type', 'enabled']
        for key in keys:
            self.add_field_from_pargs_to_data(key, data, key, reject_value=None, format=None)
        instances = self.app.pargs.instances
        if instances is not None:
            inst = []
            instances = instances.split(',')
            for instance in instances:
                instance_id, action = instance.split(':')
                if action not in ['add', 'del']:
                    raise Exception('action %s is not permitted' % action)
                inst.append({'instance': instance_id, 'action': action})
            data['instances'] = inst

        res = self.cmp_put(uri, data=data)
        job = res.get('job')
        self.app.render({'msg': 'update backup job %s' % job})

    @ex(
        help='delete compute zone backup job',
        description='delete compute zone backup job',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['job'], {'help': 'job id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def compute_zone_backup_job_del(self):
        oid = self.app.pargs.id
        job = self.app.pargs.job
        uri = '%s/compute_zones/%s/backup/jobs/%s' % (self.baseuri, oid, job)
        res = self.cmp_delete(uri, entity='backup job %s' % job)


    @ex(
        help='get compute zone backup job restore points',
        description='get compute zone backup job restore points',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['job'], {'help': 'backup job id', 'action': 'store', 'type': str, 'default': None}),
            (['-restore_point'], {'help': 'backup restore point id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def compute_zone_backup_restore_point_get(self):
        oid = self.app.pargs.id
        job_id = self.app.pargs.job
        restore_point_id = self.app.pargs.restore_point
        if restore_point_id is not None:
            uri = '%s/compute_zones/%s/backup/restore_points' % (self.baseuri, oid)
            res = self.cmp_get(uri, data={'job_id': job_id, 'restore_point_id': restore_point_id})

            if self.is_output_text():
                res = res.get('restore_points')
                if len(res) > 0:
                    res = res[0]
                    metadata = res.pop('metadata', [])
                    instances = res.pop('instances', [])
                    self.app.render(res, details=True)

                    self.c('\nmetadata', 'underline')
                    fields = ['id', 'created', 'key', 'value']
                    headers = ['id', 'created', 'key', 'value']
                    self.app.render(metadata, fields=fields, headers=headers)

                    self.c('\ninstances', 'underline')
                    self.app.render(instances, fields=['id', 'name', 'state'], headers=['id', 'name', 'state'])
            else:
                self.app.render(res, details=True)
        else:
            uri = '%s/compute_zones/%s/backup/restore_points' % (self.baseuri, oid)
            res = self.cmp_get(uri, data={'job_id': job_id})
            restore_points = res.get('restore_points')
            headers = ['id', 'name', 'site', 'hypervisor', 'resource_type', 'created', 'type', 'status']
            fields = ['id', 'name', 'site', 'hypervisor', 'resource_type', 'created', 'type', 'status']
            self.app.render(restore_points, headers=headers, fields=fields)

    @ex(
        help='add compute zone backup job restore point',
        description='add compute zone backup job restore point',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['job'], {'help': 'backup job id', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'restore point name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'restore point description', 'action': 'store', 'type': str, 'default': None}),
            (['-full'], {'help': 'if true create a full restore point, otherwise make an incremental',
                         'action': 'store', 'type': str, 'default': 'true'}),
        ])
    )
    def compute_zone_backup_restore_point_add(self):
        oid = self.app.pargs.id
        job_id = self.app.pargs.job
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        full = str2bool(self.app.pargs.full)
        if desc is None:
            desc = name
        uri = '%s/compute_zones/%s/backup/restore_points' % (self.baseuri, oid)
        data = {
            'job_id': job_id,
            'name': name,
            'desc': desc,
            'full': full
        }
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add backup job %s restore point' % job_id})

    @ex(
        help='delete compute zone backup job restore point',
        description='delete compute zone backup job restore point',
        arguments=ARGS([
            (['id'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['job'], {'help': 'backup job id', 'action': 'store', 'type': str, 'default': None}),
            (['restore_point'], {'help': 'restore point id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def compute_zone_backup_restore_point_del(self):
        oid = self.app.pargs.id
        job_id = self.app.pargs.job
        restore_point_id = self.app.pargs.restore_point
        uri = '%s/compute_zones/%s/backup/restore_points' % (self.baseuri, oid)
        data = {
            'job_id': job_id,
            'restore_point_id': restore_point_id
        }
        res = self.cmp_delete(uri, data=data)
        self.app.render({'msg': 'delete backup job %s restore point' % job_id})

    #
    # vpc
    #
    @ex(
        help='get provider vpc',
        description='get provider vpc(s)',
        arguments=PARGS([
            (['-id'], {'help': 'vpc id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def vpc_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v2.0/nrs/provider/vpcs/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('vpc')
                networks = res.pop('networks', [])
                self.app.render(res, details=True)

                for i in networks:
                    i['subnets'] = []
                    configs = i.get('attributes').get('configs')
                    subnets = configs.get('subnets', None)
                    i['subnets'] = ''
                    for s in subnets:
                        i['subnets'] += '- cidr=%s\n' % s.get('cidr', None)
                        i['subnets'] += '  allocable=%s\n' % s.get('allocable', False)
                        i['subnets'] += '  hypervisor\n'
                        for h in s.get('hypervisor', []):
                            i['subnets'] += '  - %s: vxlan=%s, cidr=%s, gateway=%s, pool=%s\n' % \
                                    (h.get('type'), h.get('vxlan'), h.get('cidr'), h.get('gateway'), h.get('pool'))

                self.c('\n\nnetworks', 'underline')
                headers = ['id', 'name', 'avz', 'vlan', 'reuse', 'state', 'subnets']
                fields = ['id', 'name', 'availabilty_zone.name', 'attributes.configs.vlan', 'reuse', 'state',
                          'subnets']
                self.app.render(networks, headers=headers, fields=fields, maxsize=1000)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v2.0/nrs/provider/vpcs'
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='vpcs', headers=self._meta.vpc_headers, fields=self._meta.vpc_fields)

    @ex(
        help='add vpc',
        description='add vpc',
        arguments=ARGS([
            (['name'], {'help': 'vpc name', 'action': 'store', 'type': str, 'default': None}),
            (['container'], {'help': 'vpc container id', 'action': 'store', 'type': str, 'default': None}),
            (['compute_zone'], {'help': 'vpc compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['cidr'], {'help': 'vpc cidr', 'action': 'store', 'type': str, 'default': None}),
            (['-type'], {'help': 'vpc type. Can shared or private', 'action': 'store', 'type': str,
                         'default': 'shared'})
        ])
    )
    def vpc_add(self):
        name = self.app.pargs.name
        data = {
            'name': name,
            'desc': name,
            'container': self.app.pargs.container,
            'compute_zone': self.app.pargs.compute_zone,
            'cidr': self.app.pargs.cidr,
            'type': self.app.pargs.type,
        }

        uri = '/v2.0/nrs/provider/vpcs'
        res = self.cmp_post(uri, data={'vpc': data})
        self.app.render({'msg': 'add vpc %s' % res['uuid']})

    @ex(
        help='delete vpc',
        description='delete vpc',
        arguments=ARGS([
            (['id'], {'help': 'vpc id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def vpc_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = '/v2.0/nrs/provider/vpcs/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='vpc %s' % oid)

    @ex(
        help='update vpc',
        description='update vpc',
        arguments=ARGS([
            (['id'], {'help': 'vpc id', 'action': 'store', 'type': str, 'default': None}),
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def vpc_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '/v2.0/nrs/provider/vpcs/%s' % oid
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'update vpc %s' % res['uuid']})

    @ex(
        help='add vpc network',
        description='add vpc network',
        arguments=ARGS([
            (['id'], {'help': 'vpc id', 'action': 'store', 'type': str, 'default': None}),
            (['type'], {'help': 'network type. Can be private or site', 'action': 'store', 'type': str}),
            (['-networks'], {'help': 'comma separated list of site network id', 'action': 'store',
                             'type': str, 'default': None}),
            (['-cidr'], {'help': 'private network cidr', 'action': 'store', 'type': str, 'default': None}),
            (['-avz'], {'help': 'private network availability zone', 'action': 'store', 'type': str, 'default': None}),
            (['-zone'], {'help': 'dns zone', 'action': 'store', 'type': str, 'default': None}),
            (['-dns'], {'help': 'dns list', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def vpc_network_add(self):
        oid = self.app.pargs.id
        net_type = self.app.pargs.type
        if net_type == 'site':
            networks = self.app.pargs.networks.split(',')
            data = {'site': [{'network': n} for n in networks]}
        elif net_type == 'private':
            cidr = self.app.pargs.cidr
            avz = self.app.pargs.avz
            dns = self.app.pargs.dns
            zone = self.app.pargs.zone
            data = {'private': [{
                'cidr': cidr,
                'availability_zone': avz,
                'dns_search': zone,
                'dns_nameservers': dns.split(',')
            }]}
        uri = '/v2.0/nrs/provider/vpcs/%s/network' % oid
        self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add %s networks to vpc %s' % (net_type, oid)})

    @ex(
        help='delete vpc network',
        description='delete vpc network',
        arguments=ARGS([
            (['id'], {'help': 'vpc id', 'action': 'store', 'type': str, 'default': None}),
            (['type'], {'help': 'network type. Can be private or site', 'action': 'store', 'type': str}),
            (['-networks'], {'help': 'comma separated list of site network id', 'action': 'store',
                             'type': str, 'default': None}),
            (['-cidr'], {'help': 'private network cidr', 'action': 'store', 'type': str, 'default': None}),
            (['-avz'], {'help': 'private network availability zone', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def vpc_network_del(self):
        oid = self.app.pargs.id
        net_type = self.app.pargs.type
        if net_type == 'site':
            networks = self.app.pargs.networks.split(',')
            data = {'site': [{'network': n} for n in networks]}
        elif net_type == 'private':
            cidr = self.app.pargs.cidr
            avz = self.app.pargs.avz
            data = {'private': [{'cidr': cidr, 'availability_zone': avz}]}
        else:
            raise Exception('network type can be only private or site')
        uri = '/v2.0/nrs/provider/vpcs/%s/network' % oid
        self.cmp_delete(uri, data=data, entity='%s network' % net_type)
        self.app.render({'msg': 'delete %s networks to vpc %s' % (net_type, oid)})

    #
    # security group
    #
    @ex(
        help='get provider security group',
        description='get provider security group(s)',
        arguments=PARGS([
            (['-id'], {'help': 'security_group id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-vpc'], {'help': 'vpc id', 'action': 'store', 'type': str, 'default': None}),
            (['-instance'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def sg_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = self.baseuri + '/security_groups/%s' % oid
            res = self.cmp_get(uri).get('security_group')

            if self.is_output_text():
                rules = res.pop('rules', [])
                instances = res.pop('instances', [])
                self.app.render(res, details=True)

                self.c('\nrules', 'underline')
                headers = ['id', 'name', 'proto', 'subproto', 'port', 'src-type', 'src', 'dst-type', 'dst', 'state',
                           'reserved']
                fields = ['uuid', 'name', 'attributes.configs.service.protocol', 'attributes.configs.service.subprotocol',
                          'attributes.configs.service.port',
                          'attributes.configs.source.type', 'attributes.configs.source.value',
                          'attributes.configs.destination.type', 'attributes.configs.destination.value', 'state',
                          'attributes.reserved']
                self.app.render(rules, headers=headers, fields=fields, maxsize=400)

                self.c('\ninstances', 'underline')
                self.app.render(instances, headers=self._meta.instance_headers, fields=self._meta.instance_fields,
                                maxsize=400)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags', 'instance', 'vpc']
            mappings = {'name': lambda n: '%' + n + '%'}
            aliases = {'parent': 'parent_list'}
            data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
            uri = '%s/security_groups' % self.baseuri
            res = self.cmp_get(uri, data=data)
            transform = {'rules': lambda x: len(x)}
            self.app.render(res, key='security_groups', headers=self._meta.security_group_headers,
                            fields=self._meta.security_group_fields, transform=transform)

    @ex(
        help='check security groups contain ingress rule from zabbix proxy',
        description='check security groups contain ingress rule from zabbix proxy',
        arguments=PARGS([
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def sg_zabbix_is_enabled(self):
        params = ['name', 'desc', 'parent', 'state', 'tags', 'instance', 'vpc']
        mappings = {'name': lambda n: '%' + n + '%'}
        aliases = {'parent': 'parent_list'}
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '%s/security_groups' % self.baseuri
        res = self.cmp_get(uri, data=data)
        transform = {'rules': lambda x: len(x)}
        headers = ['id', 'uuid', 'name', 'state', 'SiteTorino01', 'SiteTorino02', 'SiteVercelli01']
        fields = ['id', 'uuid', 'name', 'state', 'zabbix_rules.SiteTorino01', 'zabbix_rules.SiteTorino02',
                  'zabbix_rules.SiteVercelli01']
        self.app.render(res, key='security_groups', headers=headers, fields=fields, transform=transform)

    # def __add_rule(self, name, zone, source, dest, proto='*', subproto=None, port='*'):
    #     if proto == '*':
    #         port = '*'
    #     source = source.split(':')
    #     dest = dest.split(':')
    #     data = {
    #         'rule': {
    #             'container': self.get_container(),
    #             'name': name,
    #             'desc': name,
    #             'compute_zone': zone,
    #             'source': {
    #                 'type': source[0],
    #                 'value': source[1]
    #             },
    #             'destination': {
    #                 'type': dest[0],
    #                 'value': dest[1]
    #             },
    #             'service': {
    #                 'protocol': proto
    #             }
    #         }
    #     }
    #     if port is not None:
    #         data['rule']['service']['port'] = port
    #     if proto == '1' and subproto is not None:
    #         data['rule']['service']['subprotocol'] = subproto
    #
    #     uri = '%s/rules' % self.baseuri
    #     res = self.cmp_post(uri, data=data)
    #     print('add rule %s' % res['uuid'])

    @ex(
        help='enable security group ingress from zabbix proxy',
        description='enable security group ingress from zabbix proxy',
        arguments=PARGS([
            (['id'], {'help': 'security group id', 'action': 'store', 'type': str}),
            (['availability_zone'], {'help': 'availability zone name. Es. SiteTorino01', 'action': 'store',
                                     'type': str}),
        ])
    )
    def sg_zabbix_enable(self):
        oid = self.app.pargs.id
        availability_zone = self.app.pargs.availability_zone
        data = {'availability_zone': availability_zone}
        uri = '%s/security_groups/%s/zabbix' % (self.baseuri, oid)
        res = self.cmp_post(uri, data=data)

    @ex(
        help='disable security group ingress from zabbix proxy',
        description='disable security group ingress from zabbix proxy',
        arguments=PARGS([
            (['id'], {'help': 'security group id', 'action': 'store', 'type': str}),
            (['availability_zone'], {'help': 'availability zone name. Es. SiteTorino01', 'action': 'store',
                                     'type': str}),
        ])
    )
    def sg_zabbix_disable(self):
        oid = self.app.pargs.id
        availability_zone = self.app.pargs.availability_zone
        data = {'availability_zone': availability_zone}
        uri = '%s/security_groups/%s/zabbix' % (self.baseuri, oid)
        res = self.cmp_delete(uri, data=data, entity='sg zabbix rule for availability zone %s' % availability_zone)

    @ex(
        help='check provider security group',
        description='check provider security group(s)',
        arguments=PARGS()
    )
    def sg_check(self):
        # get rules
        data = {'parent': 'f2716a97-97a1-4cb8-bce3-7a411326bcf6', 'size': -1}
        uri = '%s/rules' % self.baseuri
        res = self.cmp_get(uri, data=data).get('rules')
        rule_idx = {r['id']: r for r in res}
        # print(rule_list)

        # self.app.render(res, key='rules', headers=self._meta.rule_headers, fields=self._meta.rule_fields)

        sg_rule_idx = {}
        oids = [146984, 145866, 143148, 143138, 143056, 142853, 142758, 142702, 142075, 141988, 141393, 141300]
        for oid in oids:
            uri = self.baseuri + '/security_groups/%s' % oid
            res = self.cmp_get(uri).get('security_group')
            rules = res.pop('rules', [])
            for rule in rules:
                sg_rule_idx[rule['id']] = None
        # print(list(rule_idx.keys()))

        old_rules = set(list(rule_idx.keys())) - set(list(sg_rule_idx.keys()))

        check_sgs = {}
        for old_rule_id in old_rules:
            old_rule = rule_idx.get(old_rule_id)
            # print(rule_idx.get(old_rule))
            source = dict_get(old_rule, 'attributes.configs.source')
            destination = dict_get(old_rule, 'attributes.configs.destination')
            if source.get('type') == 'SecurityGroup':
                check_sgs[source.get('value')] = None
            if destination.get('type') == 'SecurityGroup':
                check_sgs[destination.get('value')] = None
        print(list(check_sgs.keys()))

    @ex(
        help='add security group',
        description='add security group',
        arguments=ARGS([
            (['name'], {'help': 'security group name', 'action': 'store', 'type': str, 'default': None}),
            (['vpc'], {'help': 'parent vpc id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def sg_add(self):
        name = self.app.pargs.name
        vpc = self.app.pargs.vpc
        data = {
            'security_group': {
                'container': self.get_container(),
                'name': name,
                'desc': name,
                'vpc': vpc
            }
        }
        uri = self.baseuri + '/security_groups'
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add security_group %s' % res['uuid']})

    @ex(
        help='delete security group',
        description='delete security group',
        arguments=ARGS([
            (['id'], {'help': 'security_group id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def sg_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = self.baseuri + '/security_groups/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='security_group %s' % oid)

    # @ex(
    #     help='update security group',
    #     description='update security group',
    #     arguments=ARGS([
    #         (['id'], {'help': 'security_group id', 'action': 'store', 'type': str, 'default': None}),
    #         (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
    #     ])
    # )
    # def sg_update(self):
    #     oid = self.app.pargs.id
    #     data_file = self.app.pargs.file
    #     data = load_config(data_file)
    #     uri = self.baseuri + '/security_groups/%s' % oid
    #     res = self.cmp_put(uri, data=data)
    #     self.app.render({'msg': 'update security_group %s' % res['uuid']})

    #
    # rule
    #
    @ex(
        help='get provider rule',
        description='get provider rule(s)',
        arguments=PARGS([
            (['-id'], {'help': 'rule id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-source'], {'help': 'rule source', 'action': 'store', 'type': str, 'default': None}),
            (['-destination'], {'help': 'rule destination', 'action': 'store', 'type': str, 'default': None}),
            (['-security_groups'], {'help': 'search rule by security group', 'action': 'store', 'type': str,
                                    'default': None})
        ])
    )
    def rule_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = self.baseuri + '/rules/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('rule')
                attributes = res.get('attributes', [])
                configs = attributes.pop('configs', [])
                source = configs.pop('source', [])
                dest = configs.pop('destination', [])
                service = configs.pop('service', [])
                self.app.render(res, details=True)

                fromto = []
                if not isinstance(source, list):
                    source = [source]
                for i in source:
                    i['fromto'] = 'source'
                fromto.extend(source)
                if not isinstance(dest, list):
                    dest = [dest]
                for i in dest:
                    i['fromto'] = 'destination'
                fromto.extend(dest)
                self.c('\n\nsource - destination', 'underline')
                self.app.render(fromto, headers=['fromto', 'type', 'value'], maxsize=200)
                self.c('\n\nservice', 'underline')
                self.app.render(service, headers=['protocol', 'subprotocol', 'port'], maxsize=200)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'source', 'destination', 'state', 'security_groups']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/rules' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='rules', headers=self._meta.rule_headers, fields=self._meta.rule_fields)

    @ex(
        help='add rule',
        description='add rule',
        arguments=ARGS([
            (['name'], {'help': 'rule id', 'action': 'store', 'type': str}),
            (['compute_zone'], {'help': 'compute zone id', 'action': 'store', 'type': str}),
            (['source'], {'help': 'rule source. Syntax <type>:<value>. type can be SecurityGroup, Cidr. value can be '
                                  'security group id, cidr like 10.102.167.0/24', 'action': 'store', 'type': str}),
            (['dest'], {'help': 'rule destination. Syntax <type>:<value>. type can be SecurityGroup, Cidr. value can be'
                                ' security group id, cidr like 10.102.167.0/24', 'action': 'store', 'type': str}),
            (['-proto'], {'help': 'ca be  6 [tcp], 17 [udp], 1 [icmp], * [all]. If use icmp specify also subprotocol. '
                                  '[default=*]', 'action': 'store', 'type': str, 'default': '*'}),
            (['-port'], {'help': 'can be an integer between 0 and 65535 or a range with start and end in the same '
                                 'interval. Range format is <start>-<end>. Use * for all ports. [default=*]',
                         'action': 'store', 'type': str, 'default': None}),
            (['-subproto'], {'help': 'icmp subprotocol. ex. 8 for echo request', 'action': 'store', 'type': str,
                             'default': None}),
        ])
    )
    def rule_add(self):
        name = self.app.pargs.name
        zone = self.app.pargs.compute_zone
        source = self.app.pargs.source.split(':')
        dest = self.app.pargs.dest.split(':')
        port = self.app.pargs.port
        proto = self.app.pargs.proto
        subproto = self.app.pargs.subproto
        if proto == '*':
            port = '*'
        data = {
            'rule': {
                'container': self.get_container(),
                'name': name,
                'desc': name,
                'compute_zone': zone,
                'source': {
                    'type': source[0],
                    'value': source[1]
                },
                'destination': {
                    'type': dest[0],
                    'value': dest[1]
                },
                'service': {
                    'protocol': proto
                }
            }
        }
        if port is not None:
            data['rule']['service']['port'] = port
        if proto == '1' and subproto is not None:
            data['rule']['service']['subprotocol'] = subproto

        uri = '%s/rules' % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add rule %s' % res['uuid']})

    @ex(
        help='delete rule',
        description='delete rule',
        arguments=ARGS([
            (['-id'], {'help': 'rule id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def rule_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        parent = self.app.pargs.parent

        if parent is not None:
            data = urlencode({'parent': parent, 'size': -1}, doseq=True)
            uri = '%s/rules' % self.baseuri
            res = self.cmp_get(uri, data=data)
            # self.app.render(res, key='rules', headers=self._meta.rule_headers, fields=self._meta.rule_fields)

            for item in res.get('rules'):
                uri = self.baseuri + '/rules/%s' % item['id']
                if force is True:
                    uri += '?force=true'
                self.cmp_delete(uri, entity='rule %s' % item['id'])
        elif oid is not None:
            uri = self.baseuri + '/rules/%s' % oid
            if force is True:
                uri += '?force=true'
            self.cmp_delete(uri, entity='rule %s' % oid)

    # @ex(
    #     help='update rule',
    #     description='update rule',
    #     arguments=ARGS([
    #         (['id'], {'help': 'rule id', 'action': 'store', 'type': str, 'default': None}),
    #         (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
    #     ])
    # )
    # def rule_update(self):
    #     oid = self.app.pargs.id
    #     data_file = self.app.pargs.file
    #     data = load_config(data_file)
    #     uri = self.baseuri + '/rules/%s' % oid
    #     res = self.cmp_put(uri, data=data)
    #     self.app.render({'msg': 'update rule %s' % res['uuid']})

    #
    # bastion
    #
    @ex(
        help='get provider bastion host(s)',
        description='get provider bastion host(s)',
        arguments=PARGS([
            (['-id'], {'help': 'bastion id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'bastion name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'bastion description', 'action': 'store', 'type': str, 'default': None}),
            (['-compute_zone'], {'help': 'bastion zone', 'action': 'store', 'type': str, 'default': None}),
            # (['-state'], {'help': 'instance state', 'action': 'store', 'type': str, 'default': None}),
            # (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
            # (['-hypervisor'], {'help': 'instance hypervisor', 'action': 'store', 'type': str, 'default': None}),
            # (['-tags'], {'help': 'instance tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def bastion_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = self.baseuri + '/bastions/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                data = res.get('bastion')
                avz = data.pop('availability_zone', None)
                flavor = data.pop('flavor', {})
                image = data.pop('image', {})
                vpcs = data.pop('vpcs', [])
                sgs = data.pop('security_groups', [])
                storage = data.pop('block_device_mapping', [])
                self.app.render(data, details=True)

                self.c('\nAvailability zone', 'underline')
                self.app.render(avz, headers=['uuid', 'name', 'state'])
                self.c('\nFlavor', 'underline')
                self.app.render(flavor, headers=['vcpus', 'memory', 'disk', 'disk_iops', 'bandwidth'])
                self.c('\nImage', 'underline')
                self.app.render(image, headers=['os', 'os_ver'])
                self.c('\nSecurity groups', 'underline')
                self.app.render(sgs, headers=['uuid', 'name'])
                self.c('\nNetworks', 'underline')
                self.app.render(vpcs, headers=['uuid', 'name', 'fixed_ip.ip'])
                self.c('\nBlock device mapping', 'underline')
                self.app.render(storage, headers=['id', 'name', 'boot_index', 'bootable', 'encrypted', 'volume_size'])
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'compute_zone']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/bastions' % self.baseuri
            res = self.cmp_get(uri, data=data)
            if self.is_output_text():
                for item in res.get('bastions'):
                    image = item.get('image', {})
                    item['os'] = '%s %s' % (image.get('os', ''), image.get('os_ver', ''))
                    block_device_mapping = item.get('block_device_mapping', [])
                    item['volume'] = {'num': len(block_device_mapping)}
                    if item['volume']['num'] > 0:
                        item['volume']['size'] = sum([i.get('volume_size', None) for i in block_device_mapping])

            self.app.render(res, key='bastions', headers=self._meta.instance_headers,
                            fields=self._meta.instance_fields)

    @ex(
        help='add provider bastion host',
        description='add provider bastion host',
        arguments=ARGS([
            (['name'], {'help': 'bastion name', 'action': 'store', 'type': str, 'default': None}),
            (['compute_zone'], {'help': 'bastion name', 'action': 'store', 'type': str, 'default': None}),
            (['-availability_zone'], {'help': 'bastion name', 'action': 'store', 'type': str,
                                      'default': 'SiteVercelli01'}),
            (['-pwd'], {'help': 'bastion admin password', 'action': 'store', 'type': str, 'default': None}),
            (['-key_name'], {'help': 'bastion admin ssh key', 'action': 'store', 'type': str, 'default': None}),
            (['-flavor'], {'help': 'bastion flavor', 'action': 'store', 'type': str, 'default': 'vm.s1.micro'}),
            (['-volume_flavor'], {'help': 'bastion volume flavor', 'action': 'store', 'type': str,
                                  'default': 'vol.default'}),
            (['-image'], {'help': 'bastion image', 'action': 'store', 'type': str, 'default': 'Centos7'}),
            (['-acl'], {'help': 'comma separated list of network acl', 'action': 'store', 'type': str, 'default': ''}),
        ])
    )
    def bastion_add(self):
        name = self.app.pargs.name
        compute_zone = self.app.pargs.compute_zone
        availability_zone = self.app.pargs.availability_zone
        flavor = self.app.pargs.flavor
        volume_flavor = self.app.pargs.volume_flavor
        image = self.app.pargs.image
        pwd = self.app.pargs.pwd
        key_name = self.app.pargs.key_name
        acl = self.app.pargs.acl.split(',')
        data = {
            'container': 'ResourceProvider01',
            'name': name,
            'desc': name,
            'compute_zone': compute_zone,
            'availability_zone': availability_zone,
            'flavor': flavor,
            'volume_flavor': volume_flavor,
            'image': image
        }
        if pwd is not None:
            data['admin_pass'] = pwd
        if key_name is not None:
            data['key_name'] = key_name
        if acl is not None:
            data['acl'] = [{'subnet': a} for a in acl]

        uri = self.baseuri + '/bastions'
        res = self.cmp_post(uri, data={'bastion': data})
        self.app.render({'msg': 'add bastion %s' % res['uuid']})

    @ex(
        help='patch bastion',
        description='patch bastion',
        arguments=ARGS([
            (['id'], {'help': 'bastion id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def bastion_patch(self):
        oid = self.app.pargs.id
        uri = self.baseuri + '/bastions/%s' % oid
        res = self.cmp_patch(uri, data='')
        self.app.render({'msg': 'patch bastion %s' % res['uuid']})

    @ex(
        help='delete bastion',
        description='delete bastion',
        arguments=ARGS([
            (['id'], {'help': 'bastion id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def bastion_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = self.baseuri + '/bastions/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='bastion %s' % oid)

    @ex(
        help='start bastion',
        description='start bastion',
        arguments=ARGS([
            (['id'], {'help': 'bastion id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def bastion_start(self):
        oid = self.app.pargs.id
        uri = '%s/bastions/%s/actions' % (self.baseuri, oid)
        data = {'action': {'start': True}}
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'start bastion %s' % oid})

    @ex(
        help='stop bastion',
        description='stop bastion',
        arguments=ARGS([
            (['id'], {'help': 'bastion id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def bastion_stop(self):
        oid = self.app.pargs.id
        uri = '%s/bastions/%s/actions' % (self.baseuri, oid)
        data = {'action': {'stop': True}}
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'stop bastion %s' % oid})

    @ex(
        help='set bastion flavor',
        description='set bastion flavor',
        arguments=ARGS([
            (['id'], {'help': 'bastion id', 'action': 'store', 'type': str, 'default': None}),
            (['flavor'], {'help': 'flavor id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def bastion_flavor_set(self):
        oid = self.app.pargs.id
        flavor = self.app.pargs.flavor
        uri = '%s/bastions/%s/actions' % (self.baseuri, oid)
        data = {'action': {'set_flavor': {'flavor': flavor}}}
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'set bastion %s flavor %s' % (oid, flavor)})

    @ex(
        help='add bastion security group',
        description='add bastion security group',
        arguments=ARGS([
            (['id'], {'help': 'bastion id', 'action': 'store', 'type': str, 'default': None}),
            (['security_group'], {'help': 'security group id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def bastion_sg_add(self):
        oid = self.app.pargs.id
        security_group = self.app.pargs.security_group
        uri = '%s/bastions/%s/actions' % (self.baseuri, oid)
        data = {'action': {'add_security_group': {'security_group': security_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'add bastion %s security group %s' % (oid, security_group)})

    @ex(
        help='remove bastion security group',
        description='remove bastion security group',
        arguments=ARGS([
            (['id'], {'help': 'bastion id', 'action': 'store', 'type': str, 'default': None}),
            (['security_group'], {'help': 'security group id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def bastion_sg_del(self):
        oid = self.app.pargs.id
        security_group = self.app.pargs.security_group
        uri = '%s/bastions/%s/actions' % (self.baseuri, oid)
        data = {'action': {'del_security_group': {'security_group': security_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'remove bastion %s security group %s' % (oid, security_group)})

    @ex(
        help='install bastion zabbix proxy',
        description='install bastion zabbix proxy',
        arguments=ARGS([
            (['id'], {'help': 'bastion id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def bastion_zabbix_proxy_install(self):
        oid = self.app.pargs.id
        uri = '%s/bastions/%s/actions' % (self.baseuri, oid)
        data = {'action': {'install_zabbix_proxy': True}}
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'install zabbix proxy on bastion %s' % oid})

    @ex(
        help='register bastion zabbix proxy',
        description='register bastion zabbix proxy',
        arguments=ARGS([
            (['id'], {'help': 'bastion id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def bastion_zabbix_proxy_register(self):
        oid = self.app.pargs.id
        uri = '%s/bastions/%s/actions' % (self.baseuri, oid)
        data = {'action': {'register_zabbix_proxy': True}}
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'register zabbix proxy on bastion %s' % oid})

    @ex(
        help='install shipper on bastion to enable resource monitoring',
        description='install shipper on bastion to enable resource monitoring',
        arguments=ARGS([
            (['id'], {'help': 'bastion id', 'action': 'store', 'type': str, 'default': None}),
            (['-hostgroup'], {'help': 'account hostgroup written as Org.Div.Acc', 'action': 'store', 'type': str,
                              'default': None})
        ])
    )
    def bastion_monit_enable(self):
        oid = self.app.pargs.id
        host_group = self.app.pargs.hostgroup
        uri = '%s/bastions/%s/actions' % (self.baseuri, oid)
        data = {'action': {'enable_monitoring': {'host_group': host_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'shipper installed, resource monitoring enabled on bastion %s' % oid})

    @ex(
        help='install shipper on bastion to forward and centralize log data',
        description='install shipper on bastion to forward and centralize log data',
        arguments=ARGS([
            (['id'], {'help': 'bastion id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def bastion_log_enable(self):
        oid = self.app.pargs.id
        uri = '%s/bastions/%s/actions' % (self.baseuri, oid)
        data = {'action': {'enable_logging': True}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'shipper installed, log forwarding enabled on bastion %s' % oid})

    #
    # instance
    #
    @ex(
        help='get provider instance',
        description='get provider instance(s)',
        arguments=PARGS([
            (['-id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'instance name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'instance description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'instance parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'instance state', 'action': 'store', 'type': str, 'default': None}),
            # (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
            (['-hypervisor'], {'help': 'instance hypervisor', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'instance tags', 'action': 'store', 'type': str, 'default': None}),
            (['-image'], {'help': 'instance image', 'action': 'store', 'type': str, 'default': None}),
            (['-flavor'], {'help': 'instance flavor', 'action': 'store', 'type': str, 'default': None}),
            (['-vpc'], {'help': 'instance vpc', 'action': 'store', 'type': str, 'default': None}),
            (['-security_group'], {'help': 'instance security group', 'action': 'store', 'type': str, 'default': None}),
            (['-hostinfo'], {'help': 'print list with hypervisor info', 'action': 'store', 'type': str,
                             'default': False}),
            (['-availability_zone'], {'help': 'instance availability zone', 'action': 'store', 'type': str,
                                      'default': None}),
        ])
    )
    def instance_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = self.baseuri + '/instances/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                data = res.get('instance')
                avz = data.pop('availability_zone', [])
                flavor = data.pop('flavor', {})
                image = data.pop('image', {})
                vpcs = data.pop('vpcs', [])
                sgs = data.pop('security_groups', [])
                storage = data.pop('block_device_mapping', [])
                attributes = data.pop('attributes', [])
                self.app.render(data, details=True)

                self.c('\nConfig', 'underline')
                uri = '%s/instances/%s/manage' % (self.baseuri, data.get('uuid'))
                mgt = self.cmp_get(uri).get('is_managed', [])
                config = {
                    'is-managed': bool2str(mgt),
                    'backup-enabled': attributes.get('backup_enabled', False),
                    'monitoring-enabled': attributes.get('monitoring_enabled', False),
                    'logging-enabled': attributes.get('logging_enabled', False),
                }
                self.app.render(config, headers=['is-managed', 'backup-enabled', 'monitoring-enabled',
                                                 'logging-enabled'])

                self.c('\nAvailability zone', 'underline')
                self.app.render(avz, headers=['uuid', 'name', 'state'])
                self.c('\nFlavor', 'underline')
                self.app.render(flavor, headers=['name', 'vcpus', 'memory', 'disk', 'disk_iops', 'bandwidth'])
                self.c('\nImage', 'underline')
                self.app.render(image, headers=['os', 'os_ver'])
                self.c('\nSecurity groups', 'underline')
                self.app.render(sgs, headers=['uuid', 'name'])
                self.c('\nNetworks', 'underline')
                self.app.render(vpcs, headers=['uuid', 'name', 'fixed_ip.ip'])
                self.c('\nBlock device mapping', 'underline')
                self.app.render(storage, headers=['id', 'name', 'boot_index', 'bootable', 'encrypted', 'volume_size'])
            else:
                self.app.render(res, details=True)
        else:
            hostinfo = str2bool(self.app.pargs.hostinfo)
            params = ['name', 'desc', 'parent', 'state', 'tags', 'hypervisor', 'image', 'flavor', 'vpc',
                      'security_group', 'availability_zone']
            mappings = {
                'name': lambda n: '%' + n + '%',
                'desc': lambda n: '%' + n + '%'
            }
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/instances' % self.baseuri
            res = self.cmp_get(uri, data=data)
            if self.is_output_text():
                for item in res.get('instances'):
                    image = item.get('image', {})
                    item['os'] = '%s %s' % (image.get('os', ''), image.get('os_ver', ''))
                    block_device_mapping = item.get('block_device_mapping', [])
                    item['volume'] = {'num': len(block_device_mapping)}
                    if item['volume']['num'] > 0:
                        item['volume']['size'] = sum([i.get('volume_size', None) for i in block_device_mapping])

            headers = self._meta.instance_headers
            fields = self._meta.instance_fields
            if hostinfo is True:
                fields = ['id', 'parent', 'name', 'availability_zone.name', 'hypervisor', 'attributes.host',
                          'attributes.host_group', 'runstate', 'os', 'vpcs.0.fixed_ip.ip']
                headers = ['id', 'parent', 'name', 'av_zone', 'type', 'host', 'host_group', 'runstate', 'os', 'ip']
            self.app.render(res, key='instances', headers=headers, fields=fields)
    
    @ex(
        help='add instance',
        description='add instance',
        arguments=ARGS([
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + '/instances'
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add instance %s' % res['uuid']})

    @ex(
        help='import instance',
        description='import instance',
        arguments=ARGS([
            (['name'], {'help': 'instance name', 'action': 'store', 'type': str, 'default': None}),
            (['physical_id'], {'help': 'physical resource id', 'action': 'store', 'type': str, 'default': None}),
            (['pwd'], {'help': 'instance password', 'action': 'store', 'type': str, 'default': None}),
            (['image'], {'help': 'image id', 'action': 'store', 'type': str, 'default': None}),
            (['key_name'], {'help': 'ssh key name', 'action': 'store', 'type': str, 'default': None}),
            (['-resolve'], {'help': 'if true add hostname in dns', 'action': 'store', 'type': str, 'default': 'false'}),
            (['-manage'], {'help': 'if true add node in ssh', 'action': 'store', 'type': str, 'default': 'false'}),
        ])
    )
    def instance_import(self):
        name = self.app.pargs.name
        physical_id = self.app.pargs.physical_id
        pwd = self.app.pargs.pwd
        image = self.app.pargs.image
        key_name = self.app.pargs.key_name
        resolve = str2bool(self.app.pargs.resolve)
        manage = str2bool(self.app.pargs.manage)

        config = {
            'container': 'ResourceProvider01',
            'name': name,
            'desc': name,
            'physical_id': physical_id,
            'attribute': {},
            'resclass': 'beehive_resource.plugins.provider.entity.instance.ComputeInstance',
            'configs': {
                'multi_avz': True,
                'admin_pass': pwd,
                'image': image,
                'key_name': key_name,
                'resolve': resolve,
                'manage': manage,
            }
        }
        uri = '/v1.0/nrs/entities/import'
        res = self.cmp_post(uri, data={'resource': config})
        self.app.render({'msg': 'import instance %s' % name})

    @ex(
        help='patch instance',
        description='patch instance',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_patch(self):
        oid = self.app.pargs.id
        uri = self.baseuri + '/instances/%s' % oid
        res = self.cmp_patch(uri, data='')
        self.app.render({'msg': 'patch instance %s' % res['uuid']})

    @ex(
        help='delete instance',
        description='delete instance',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def instance_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = self.baseuri + '/instances/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='instance %s' % oid)

    @ex(
        help='update instance',
        description='update instance',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def instance_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = self.baseuri + '/instances/%s' % oid
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'update instance %s' % res['uuid']})

    @ex(
        help='check provider computes instance is managed by ssh module, has backup active, has monitor active',
        description='check provider computes instance is managed by ssh module, has backup active, has monitor active',
        arguments=ARGS([
            (['-id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_config(self):
        oid = self.app.pargs.id

        if oid is None:
            data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
            uri = self.baseuri + '/instances'
            czs = self.cmp_get(uri, data=data)
        else:
            uri = self.baseuri + '/instances/%s' % oid
            czs = self.cmp_get(uri).get('instance', None)
            if czs is not None:
                czs = {
                    'instances': [czs],
                    'page': 0,
                    'count': 1,
                    'total': 1,
                    'sort': {'field': 'id', 'order': 'DESC'}
                }
            print(czs)

        def query_item(cz):
            # get ssh management status
            uri = '%s/instances/%s/manage' % (self.baseuri, cz.get('id'))
            mgt = self.cmp_get(uri).get('is_managed', [])
            res = {
                'is-managed': bool2str(mgt),
                'has-backup': 'false',
                'has-monitor': 'false',
            }
            return res

        tmpl = '{uuid:36.36} {name:40.40} {desc:40.40} {is-managed:20.20} {has-backup:20.20} {has-monitor:20.20}'
        headers = {'uuid': 'id', 'name': 'name', 'desc': 'desc', 'is-managed': 'is-managed',
                   'has-backup': 'has-backup', 'has-monitor': 'has-monitor'}
        self.app.render(czs, 'instances', query_item, tmpl=tmpl, headers=headers)

    @ex(
        help='enable provider computes instance management by ssh module',
        description='enable provider computes instance management by ssh module',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['key'], {'help': 'instance ssh key', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_manage(self):
        oid = self.app.pargs.id
        key = self.app.pargs.key

        data = {
            'manage': {
                'key': key
            }
        }
        uri = '%s/instances/%s/manage' % (self.baseuri, oid)
        res = self.cmp_post(uri, data=data).get('manage', [])
        self.app.render({'msg': 'enable compute instance %s management with ssh node: %s' % (oid, res)})

    @ex(
        help='disable provider computes instance management by ssh module',
        description='disable provider computes instance management by ssh module',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_unmanage(self):
        oid = self.app.pargs.id

        uri = '%s/instances/%s/manage' % (self.baseuri, oid)
        res = self.cmp_delete(uri)
        self.app.render({'msg': 'disable compute instance %s management' % oid})

    @ex(
        help='run command on provider instance',
        description='run command on provider instance(s)',
        arguments=PARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['command'], {'help': 'file name where is saved the command to run', 'action': 'store', 'type': str,
                           'default': None}),
        ])
    )
    def instance_command_run(self):
        oid = self.app.pargs.id
        command = self.app.pargs.command
        command = load_config(command)
        #command = "mysql -e 'show user;' --xml=true"
        #command = "mysql -e 'select Host, User from mysql.user;' --xml=true"
        #command = "mysqlsh --json=raw --sql --uri 'root:xxx@localhost:3306' -e 'show databases;' | head -2 | tail -1"
        # command = "mysqlsh --json=raw --sql --uri 'root:xxx@localhost:3306' -e 'select Host, User from mysql.user;' | head -2 | tail -1"
        data = {'command': command}
        uri = self.baseuri + '/instances/%s/command' % oid
        res = self.cmp_put(uri, data=data)
        res = dict_get(res, 'output')
        self.app.render(res, details=True)

    @ex(
        help='get compute instance console',
        description='get compute instance console',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_console_get(self):
        oid = self.app.pargs.id
        uri = '%s/instances/%s/console' % (self.baseuri, oid)
        res = self.cmp_get(uri).get('console', {})
        self.app.render(res, details=True)
        # sh.firefox(res.get('url'))

    @ex(
        help='get compute instance backup info',
        description='get compute instance backup info',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_backup_get(self):
        oid = self.app.pargs.id
        uri = '%s/instances/%s/backup/restore_points' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        restore_points = res.pop('restore_points')
        self.app.render(res, details=True)
        self.c('\nrestore points', 'underline')
        self.app.render(restore_points, headers=['id', 'name', 'desc', 'type', 'status', 'created'])

    @ex(
        help='get compute instance backup restores',
        description='get compute instance backup restores',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['restore_point'], {'help': 'restore point id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def instance_backup_restore_get(self):
        oid = self.app.pargs.id
        sid = self.app.pargs.restore_point
        uri = '%s/instances/%s/backup/restore_points/%s/restores' % (self.baseuri, oid, sid)
        res = self.cmp_get(uri).get('restores', [])
        self.app.render(res, headers=['id', 'name', 'time_taken', 'size', 'uploaded_size', 'status',
                                      'progress_percent', 'created'])

    @ex(
        help='restore compute instance from backup restore point',
        description='restore compute instance from backup restore point',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['restore_point'], {'help': 'restore point id', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'restored instance name', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_backup_restore(self):
        oid = self.app.pargs.id
        restore_point = self.app.pargs.restore_point
        name = self.app.pargs.name
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'restore_from_backup': {'restore_point': restore_point, 'instance_name': name}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'restore compute instance %s from backup restore point %s' % (oid, restore_point)})

    @ex(
        help='add user to instance',
        description='add user to instance',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'user name', 'action': 'store', 'type': str, 'default': None}),
            (['pwd'], {'help': 'user password', 'action': 'store', 'type': str, 'default': None}),
            (['key'], {'help': 'ssh key id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def instance_user_add(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        pwd = self.app.pargs.pwd
        key = self.app.pargs.key
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'add_user': {'user_name': name, 'user_pwd': pwd, 'user_ssh_key': key}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'add user %s to instance %s' % (name, oid)})

    @ex(
        help='delete user to instance',
        description='delete user to instance',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'user name', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def instance_user_del(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'del_user': {'user_name': name}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'delete user %s to instance %s' % (name, oid)})

    @ex(
        help='delete user to instance',
        description='delete user to instance',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'user name', 'action': 'store', 'type': str, 'default': None}),
            (['pwd'], {'help': 'user password', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def instance_user_password_set(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        pwd = self.app.pargs.pwd
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'set_user_pwd': {'user_name': name, 'user_pwd': pwd}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'set user %s password to instance %s' % (name, oid)})

    @ex(
        help='start instance',
        description='start instance',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['-schedule'], {'help': 'schedule definition. Pass as json file using crontab or timedelta syntax. '
                                     'Ex. {\"type\": \"timedelta\", \"minutes\": 1}',
                             'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def instance_start(self):
        oid = self.app.pargs.id
        schedule = self.app.pargs.schedule
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        if schedule is None:
            data = {'action': {'start': True}}
            res = self.cmp_put(uri, data=data)
            self.app.render({'msg': 'start instance %s' % oid})
        else:
            schedule = load_config(schedule)
            data = {'action': {'start': True}, 'schedule': schedule}
            res = self.cmp_put(uri, data=data)
            self.app.render({'msg': 'schedule start instance %s' % oid})

    @ex(
        help='stop instance',
        description='stop instance',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['-schedule'], {'help': 'schedule definition. Pass as json file using crontab or timedelta syntax. '
                                     'Ex. {\"type\": \"timedelta\", \"minutes\": 1}',
                             'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def instance_stop(self):
        oid = self.app.pargs.id
        schedule = self.app.pargs.schedule
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        if schedule is None:
            data = {'action': {'stop': True}}
            res = self.cmp_put(uri, data=data)
            self.app.render({'msg': 'stop instance %s' % oid})
        else:
            schedule = load_config(schedule)
            data = {'action': {'stop': True}, 'schedule': schedule}
            res = self.cmp_put(uri, data=data)
            self.app.render({'msg': 'schedule stop instance %s' % oid})

    @ex(
        help='reboot instance',
        description='reboot instance',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['-schedule'], {'help': 'schedule definition. Pass as json file using crontab or timedelta syntax. '
                                     'Ex. {\"type\": \"timedelta\", \"minutes\": 1}',
                             'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def instance_reboot(self):
        oid = self.app.pargs.id
        schedule = self.app.pargs.schedule
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        if schedule is None:
            data = {'action': {'reboot': True}}
            res = self.cmp_put(uri, data=data)
            self.app.render({'msg': 'reboot instance %s' % oid})
        else:
            schedule = load_config(schedule)
            data = {'action': {'reboot': True}, 'schedule': schedule}
            res = self.cmp_put(uri, data=data)
            self.app.render({'msg': 'schedule reboot instance %s' % oid})

    @ex(
        help='migrate instance',
        description='migrate instance',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_migrate(self):
        oid = self.app.pargs.id
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'migrate': {'live': True}}}
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'migrate instance %s' % oid})

    @ex(
        help='set instance flavor',
        description='set instance flavor',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['flavor'], {'help': 'flavor id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def instance_flavor_set(self):
        oid = self.app.pargs.id
        flavor = self.app.pargs.flavor
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'set_flavor': {'flavor': flavor}}}
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'set instance %s flavor %s' % (oid, flavor)})

    @ex(
        help='set instance volume flavor',
        description='set instance volume flavor',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['-volume'], {'help': 'volume id', 'action': 'store', 'type': str, 'default': None}),
            (['-flavor'], {'help': 'flavor id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def instance_volume_flavor_set(self):
        oid = self.app.pargs.id
        flavor = self.app.pargs.flavor
        volume = self.app.pargs.volume

        # list volumes
        uri = self.baseuri + '/instances/%s' % oid
        res = self.cmp_get(uri)
        data = res.get('instance')
        storage = data.pop('block_device_mapping', [])
        resp = []
        for block in storage:
            uri = self.baseuri + '/volumes/%s' % block['id']
            res = self.cmp_get(uri).get('volume', {})
            block['flavor'] = dict_get(res, 'flavor.name')
            block['state'] = dict_get(res, 'state')
        self.app.render(storage, headers=['id', 'name', 'flavor', 'state', 'boot_index', 'volume_size', 'bootable'])

        if volume is not None and flavor is not None:
            uri = '%s/volumes/%s/actions' % (self.baseuri, volume)
            data = {'action': {'set_flavor': {'flavor': flavor}}}
            res = self.cmp_put(uri, data=data)
            self.app.render({'msg': 'set volume %s flavor %s' % (volume, flavor)})

    @ex(
        help='add instance volume',
        description='add instance volume',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['volume'], {'help': 'volume id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_volume_add(self):
        oid = self.app.pargs.id
        volume = self.app.pargs.volume
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'add_volume': {'volume': volume}}}
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'add instance %s volume %s' % (oid, volume)})

    @ex(
        help='remove instance volume',
        description='remove instance volume',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['volume'], {'help': 'volume id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_volume_del(self):
        oid = self.app.pargs.id
        volume = self.app.pargs.volume
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'del_volume': {'volume': volume}}}
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'remove instance %s volume %s' % (oid, volume)})

    @ex(
        help='get compute instance dns resolution',
        description='get compute instance dns resolution',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_dns_get(self):
        oid = self.app.pargs.id
        uri = '%s/instances/%s/dns' % (self.baseuri, oid)
        res = self.cmp_get(uri).get('dns', [])
        headers = ['id', 'name', 'ip_address', 'zone', 'container', 'fqdn']
        fields = ['id', 'name', 'ip_address', 'parent', 'container', 'fqdn']
        self.app.render(res, headers=headers, fields=fields, maxsize=200)

    @ex(
        help='add compute instance dns resolution',
        description='add compute instance dns resolution',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_dns_add(self):
        oid = self.app.pargs.id
        uri = '%s/instances/%s/dns' % (self.baseuri, oid)
        res = self.cmp_post(uri)
        self.app.render({'msg': 'add instance %s dns resolution %s' % (oid, res.get('uuid'))})

    @ex(
        help='delete compute instance dns resolution',
        description='selete compute instance dns resolution',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_dns_del(self):
        oid = self.app.pargs.id
        uri = '%s/instances/%s/dns' % (self.baseuri, oid)
        res = self.cmp_delete(uri)
        self.app.render({'msg': 'delete instance %s dns resolution %s' % (oid, res.get('uuid'))})

    @ex(
        help='add instance security group',
        description='add instance security group',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['security_group'], {'help': 'security group id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_sg_add(self):
        oid = self.app.pargs.id
        security_group = self.app.pargs.security_group
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'add_security_group': {'security_group': security_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'add instance %s security group %s' % (oid, security_group)})

    @ex(
        help='remove instance security group',
        description='remove instance security group',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['security_group'], {'help': 'security group id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_sg_del(self):
        oid = self.app.pargs.id
        security_group = self.app.pargs.security_group
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'del_security_group': {'security_group': security_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'remove instance %s security group %s' % (oid, security_group)})

    @ex(
        help='get instance snapshot',
        description='get instance snapshot',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_snapshot_get(self):
        oid = self.app.pargs.id
        uri = '%s/instances/%s/snapshots' % (self.baseuri, oid)
        res = self.cmp_get(uri).get('snapshots')
        self.app.render(res, headers=['id', 'name', 'status', 'created_at'])

    @ex(
        help='add instance snapshot',
        description='add instance snapshot',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['snapshot'], {'help': 'snapshot name', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_snapshot_add(self):
        oid = self.app.pargs.id
        snapshot = self.app.pargs.snapshot
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'add_snapshot': {'snapshot': snapshot}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'add instance %s snapshot %s' % (oid, snapshot)})

    @ex(
        help='remove instance snapshot',
        description='remove instance snapshot',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['snapshot'], {'help': 'snapshot id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_snapshot_del(self):
        oid = self.app.pargs.id
        snapshot = self.app.pargs.snapshot
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'del_snapshot': {'snapshot': snapshot}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'remove instance %s snapshot %s' % (oid, snapshot)})

    @ex(
        help='revert instance to snapshot',
        description='revert instance to snapshot',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['snapshot'], {'help': 'snapshot id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def instance_snapshot_revert(self):
        oid = self.app.pargs.id
        snapshot = self.app.pargs.snapshot
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'revert_snapshot': {'snapshot': snapshot}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'revert instance %s to snapshot %s' % (oid, snapshot)})

    @ex(
        help='install shipper on instance to enable resource monitoring',
        description='install shipper on instance to enable resource monitoring',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['-hostgroup'], {'help': 'account hostgroup written as Org.Div.Acc', 'action': 'store', 'type': str,
                              'default': None})
        ])
    )
    def instance_monit_enable(self):
        oid = self.app.pargs.id
        host_group = self.app.pargs.hostgroup
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'enable_monitoring': {'host_group': host_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'shipper installed, resource monitoring enabled on instance %s' % oid})

    @ex(
        help='remove shipper on instance to disable resource monitoring',
        description='remove shipper on instance to disable resource monitoring',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['-hostgroup'], {'help': 'account hostgroup written as Org.Div.Acc', 'action': 'store', 'type': str,
                              'default': None})
        ])
    )
    def instance_monit_disable(self):
        oid = self.app.pargs.id
        host_group = self.app.pargs.hostgroup
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'enable_monitoring': {'host_group': host_group}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'shipper installed, resource monitoring enabled on instance %s' % oid})

    @ex(
        help='install shipper on instance to forward and centralize log data',
        description='install shipper on instance to forward and centralize log data',
        arguments=ARGS([
            (['id'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def instance_log_enable(self):
        oid = self.app.pargs.id
        uri = '%s/instances/%s/actions' % (self.baseuri, oid)
        data = {'action': {'enable_logging': True}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'shipper installed, log forwarding enabled on instance %s' % oid})

    #
    # flavor
    #
    @ex(
        help='get provider flavor',
        description='get provider flavor(s)',
        arguments=PARGS([
            (['-id'], {'help': 'flavor id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def flavor_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v1.0/nrs/provider/flavors/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                data = res.get('flavor')
                attributes = data.get('attributes', [])
                configs = attributes.pop('configs', [])
                data.pop('flavors', [])
                self.app.render(data, details=True)

                self.c('\nconfigs', 'underline')
                self.app.render(configs, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v1.0/nrs/provider/flavors'
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='flavors', headers=self._meta.flavor_headers, fields=self._meta.flavor_fields)

    @ex(
        help='add flavor',
        description='add flavor',
        arguments=ARGS([
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def flavor_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '/v1.0/nrs/provider/flavors'
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add flavor %s' % res['uuid']})

    @ex(
        help='delete flavor',
        description='delete flavor',
        arguments=ARGS([
            (['id'], {'help': 'flavor id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def flavor_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = '/v1.0/nrs/provider/flavors/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='flavor %s' % oid)

    @ex(
        help='update flavor',
        description='update flavor',
        arguments=ARGS([
            (['id'], {'help': 'flavor id', 'action': 'store', 'type': str, 'default': None}),
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def flavor_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '/v1.0/nrs/provider/flavors/%s' % oid
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'update flavor %s' % res['uuid']})

    #
    # image
    #
    @ex(
        help='get provider image',
        description='get provider image(s)',
        arguments=PARGS([
            (['-id'], {'help': 'image id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def image_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v1.0/nrs/provider/images/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                data = res.get('image')
                attributes = data.get('attributes', [])
                configs = attributes.pop('configs', [])
                images = data.pop('images', [])
                self.app.render(data, details=True)

                self.c('\nconfigs', 'underline')
                self.app.render(configs, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v1.0/nrs/provider/images'
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='images', headers=self._meta.image_headers, fields=self._meta.image_fields)

    @ex(
        help='add image',
        description='add image',
        arguments=ARGS([
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def image_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '/v1.0/nrs/provider/images'
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add image %s' % res['uuid']})

    @ex(
        help='delete image',
        description='delete image',
        arguments=ARGS([
            (['id'], {'help': 'image id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def image_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = '/v1.0/nrs/provider/images/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='image %s' % oid)

    @ex(
        help='update image',
        description='update image',
        arguments=ARGS([
            (['id'], {'help': 'image id', 'action': 'store', 'type': str, 'default': None}),
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def image_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '/v1.0/nrs/provider/images/%s' % oid
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'update image %s' % res['uuid']})

    #
    # share
    #
    @ex(
        help='get provider share',
        description='get provider share(s)',
        arguments=PARGS([
            (['-id'], {'help': 'share id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def share_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v1.0/nrs/provider/shares/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('share')
                grants = res.get('details').pop('grants')
                self.app.render(res, details=True)

                for site, grants in grants.items():
                    self.c('\ngrants site: %s' % site, 'underline')
                    self.app.render(grants, headers=['id', 'access_type', 'access_level', 'access_to', 'state'])
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v1.0/nrs/provider/shares'
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='shares', headers=self._meta.share_headers, fields=self._meta.share_fields,
                            maxsize=200)

    @ex(
        help='add share',
        description='add share',
        arguments=ARGS([
            (['name'], {'help': 'share name', 'action': 'store', 'type': str}),
            (['container'], {'help': 'resource container id', 'action': 'store', 'type': str}),
            (['compute_zone'], {'help': 'compute zone id', 'action': 'store', 'type': str}),
            (['availability_zone'], {'help': 'share availability zone', 'action': 'store', 'type': str}),
            (['vpc'], {'help': 'share vpc', 'action': 'store', 'type': str}),
            (['size'], {'help': 'share size', 'action': 'store', 'type': str, 'default': None}),
            (['-proto'], {'help': 'share proto like nfs, cifs', 'action': 'store', 'type': str, 'default': 'nfs'}),
            (['-subnet'], {'help': 'share subnet cidr', 'action': 'store', 'type': str, 'default': None}),
            (['-label'], {'help': 'custom label to be used when you want to use a labelled share type',
                          'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def share_add(self):
        data = {
            'name': self.app.pargs.name,
            'desc': self.app.pargs.name,
            'container': self.app.pargs.container,
            'compute_zone': self.app.pargs.compute_zone,
            'network': self.app.pargs.vpc,
            'availability_zone': self.app.pargs.availability_zone,
            'size': self.app.pargs.size,
            'share_proto': self.app.pargs.proto,
            'subnet': self.app.pargs.subnet,
        }
        label = self.app.pargs.label
        if label is not None:
            data['share_label'] = label
        uri = '/v1.0/nrs/provider/shares'
        res = self.cmp_post(uri, data={'share': data})
        self.app.render({'msg': 'add share %s' % res['uuid']})

    @ex(
        help='delete share',
        description='delete share',
        arguments=ARGS([
            (['id'], {'help': 'share id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def share_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = '/v1.0/nrs/provider/shares/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='share %s' % oid)

    @ex(
        help='update share',
        description='update share',
        arguments=ARGS([
            (['id'], {'help': 'share id', 'action': 'store', 'type': str, 'default': None}),
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def share_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '/v1.0/nrs/provider/shares/%s' % oid
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'update share %s' % res['uuid']})

    @ex(
        help='extend share size',
        description='extend share size',
        arguments=ARGS([
            (['id'], {'help': 'share id', 'action': 'store', 'type': str, 'default': None}),
            (['size'], {'help': 'new size to assign', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def share_size_extend(self):
        oid = self.app.pargs.id
        size = self.app.pargs.size
        params = {
            'new_size': size,
        }
        uri = '%s/%s/extend' % (self.baseuri, oid)
        self.cmp_put(uri, data={'share': params})
        self.app.render({'msg': 'extend share %s size: %s' % (oid, size)})

    @ex(
        help='shrink share size',
        description='shrink share size',
        arguments=ARGS([
            (['id'], {'help': 'share id', 'action': 'store', 'type': str, 'default': None}),
            (['size'], {'help': 'new size to assign', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def share_size_shrink(self):
        oid = self.app.pargs.id
        size = self.app.pargs.size
        params = {
            'new_size': size,
        }
        uri = '%s/%s/shrink' % (self.baseuri, oid)
        self.cmp_put(uri, data={'share': params})
        self.app.render({'msg': 'shrink share %s size: %s' % (oid, size)})

    @ex(
        help='list share grants',
        description='list share grants',
        arguments=ARGS([
            (['id'], {'help': 'share id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def share_grant_get(self):
        data = {}
        oid = self.app.pargs.id
        uri = '%s/%s/grants' % (self.baseuri, oid)
        res = self.cmp_get(uri, data=data).get('shares')
        for item in res:
            self.app.render(item, headers=self.headers, fields=self.fields)
            self.c('\ngrants', 'underline')
            self.app.render(item.get('grants', []), headers=['id', 'state', 'level', 'type', 'to'],
                            fields=['uuid', 'state', 'access_level', 'access_type', 'access_to'],
                            maxsize=200, table_style='simple')

    @ex(
        help='add share grant',
        description='add share grant',
        arguments=ARGS([
            (['id'], {'help': 'share id', 'action': 'store', 'type': str, 'default': None}),
            (['-access_level'], {'help': 'RW or RO', 'action': 'store', 'type': str, 'default': 'RW'}),
            (['-access_type'], {'help': 'access type like IP or USER or CERT', 'action': 'store', 'type': str,
                                'default': 'IP'}),
            (['access_to'], {'help': 'access to like 10.102.185.0/24 or admin/user or TLS identity', 'action': 'store',
                             'type': str, 'default': 'RW'}),
        ])
    )
    def share_grant_add(self):
        oid = self.app.pargs.id
        access_level = self.app.pargs.access_level
        access_type = self.app.pargs.access_type
        access_to = self.app.pargs.access_to

        data = {
            'share_grant': {
                'access_level': access_level,
                'access_type': access_type,
                'access_to': access_to
            }
        }
        uri = '%s/%s/grants' % (self.baseuri, oid)
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add share grant'})

    @ex(
        help='delete file share grant',
        description='delete file share grant',
        arguments=ARGS([
            (['id'], {'help': 'share id', 'action': 'store', 'type': str, 'default': None}),
            (['access_id'], {'help': 'access grant id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def share_grant_del(self):
        oid = self.app.pargs.id
        access_id = self.app.pargs.access_id

        uri = self.baseuri + '/%s/grants' % oid
        res = self.cmp_delete(uri, data={'share_grant': {'access_id': access_id}})

    #
    # volume
    #
    @ex(
        help='get provider volume',
        description='get provider volume(s)',
        arguments=PARGS([
            (['-id'], {'help': 'volume id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def volume_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v1.0/nrs/provider/volumes/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('volume')
                attribs = res.pop('attributes', [])
                flavor = res.pop('flavor', [])
                instance = res.pop('instance', [])
                self.app.render(res, details=True)

                self.c('\nattributes', 'underline')
                self.app.render(attribs, details=True)
                self.c('\nflavor', 'underline')
                self.app.render(flavor, details=True)
                self.c('\ninstance', 'underline')
                self.app.render(instance, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v1.0/nrs/provider/volumes'
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='volumes', headers=self._meta.volume_headers, fields=self._meta.volume_fields)

    @ex(
        help='add volume',
        description='add volume',
        arguments=ARGS([
            (['file'], {'help': 'data file. Ex. volume: container: ResourceProvider01  name: provettina-volume01 '
                                'desc: provettina-volume01 compute_zone: ComputeService-44ff4cf3 '
                                'availability_zone: SiteVercelli01 size: 5 type: openstack '
                                'flavor: vol.default', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def volume_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '/v1.0/nrs/provider/volumes'
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add volume %s' % res['uuid']})

    @ex(
        help='import volume',
        description='import volume',
        arguments=ARGS([
            (['name'], {'help': 'instance name', 'action': 'store', 'type': str, 'default': None}),
            (['physical_id'], {'help': 'physical resource id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def volume_import(self):
        name = self.app.pargs.name
        physical_id = self.app.pargs.physical_id

        config = {
            'container': 'ResourceProvider01',
            'name': name,
            'desc': name,
            'physical_id': physical_id,
            'attribute': {},
            'resclass': 'beehive_resource.plugins.provider.entity.instance.ComputeVolume',
            'configs': {}
        }
        uri = '/v1.0/nrs/entities/import'
        res = self.cmp_post(uri, data={'resource': config})
        self.app.render({'msg': 'import volume %s' % name})

    @ex(
        help='delete volume',
        description='delete volume',
        arguments=ARGS([
            (['id'], {'help': 'volume id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def volume_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = '/v1.0/nrs/provider/volumes/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='volume %s' % oid)

    @ex(
        help='update volume',
        description='update volume',
        arguments=ARGS([
            (['id'], {'help': 'volume id', 'action': 'store', 'type': str, 'default': None}),
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def volume_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '/v1.0/nrs/provider/volumes/%s' % oid
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'update volume %s' % res['uuid']})

    @ex(
        help='set volume flavor',
        description='set volume flavor',
        arguments=ARGS([
            (['id'], {'help': 'volume id', 'action': 'store', 'type': str, 'default': None}),
            (['flavor'], {'help': 'volume flavor id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def volume_flavor_set(self):
        oid = self.app.pargs.id
        flavor = self.app.pargs.flavor
        uri = '%s/volumes/%s/actions' % (self.baseuri, oid)
        data = {'action': {'set_flavor': {'flavor': flavor}}}
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'set volume %s flavor %s' % (oid, flavor)})

    #
    # volumeflavor
    #
    @ex(
        help='get provider volumeflavor',
        description='get provider volumeflavor(s)',
        arguments=PARGS([
            (['-id'], {'help': 'volumeflavor id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def volumeflavor_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v1.0/nrs/provider/volumeflavors/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('volumeflavor')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v1.0/nrs/provider/volumeflavors'
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='volumeflavors', headers=self._meta.volumeflavor_headers,
                            fields=self._meta.volumeflavor_fields)

    @ex(
        help='add volumeflavor',
        description='add volumeflavor',
        arguments=ARGS([
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def volumeflavor_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '/v1.0/nrs/provider/volumeflavors'
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add volumeflavor %s' % res['uuid']})

    @ex(
        help='delete volumeflavor',
        description='delete volumeflavor',
        arguments=ARGS([
            (['id'], {'help': 'volumeflavor id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def volumeflavor_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = '/v1.0/nrs/provider/volumeflavors/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='volumeflavor %s' % oid)

    @ex(
        help='update volumeflavor',
        description='update volumeflavor',
        arguments=ARGS([
            (['id'], {'help': 'volumeflavor id', 'action': 'store', 'type': str, 'default': None}),
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def volumeflavor_update(self):
        oid = self.app.pargs.id
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '/v1.0/nrs/provider/volumeflavors/%s' % oid
        res = self.cmp_put(uri, data=data)
        self.app.render({'msg': 'update volumeflavor %s' % res['uuid']})
    
    #
    # customization
    #
    @ex(
        help='get customization(s)',
        description='get customization(s)',
        arguments=PARGS([
            (['-id'], {'help': 'customization id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def customization_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v1.0/nrs/provider/customizations/%s' % oid
            res = self.cmp_get(uri).get('customization')
            if self.is_output_text():
                applied_customs = res.pop('applied', [])
                self.app.render(res, details=True)
                self.c('\n\napplied customizations', 'underline')
                headers = ['id', 'uuid', 'name', 'state']
                fields = ['id', 'uuid', 'name', 'state']
                self.app.render(applied_customs, headers=headers, fields=fields, maxsize=400)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v1.0/nrs/provider/customizations'
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='customizations', headers=self._meta.customization_headers,
                            fields=self._meta.customization_fields)

    @ex(
        help='add customization',
        description='add customization',
        arguments=ARGS([
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None})
            #
            # As a data file example, see beehive-mgmt/configs/test/example/provider_customization_add.yml
            #
        ])
    )
    def customization_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)
        uri = '/v1.0/nrs/provider/customizations'
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add customization %s' % res['uuid']})

    @ex(
        help='delete customization',
        description='delete customization',
        arguments=ARGS([
            (['id'], {'help': 'customization id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def customization_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = '/v1.0/nrs/provider/customizations/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='customization %s' % oid)

    #
    # applied customization
    #
    @ex(
        help='get applied customizations',
        description='get applied customizations',
        arguments=PARGS([
            (['-id'], {'help': 'applied customization uuid', 'action': 'store', 'type': str, 'default': None}),
            (['-uuids'], {'help': 'comma separated list of applied customization uuid', 'action': 'store', 'type': str,
                          'default': None}),
            (['-instance'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def applied_customization_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            uri = '/v1.0/nrs/provider/applied_customizations/%s' % oid
            res = self.cmp_get(uri).get('applied_customization')
            if self.is_output_text():
                job_template = res.pop('job_template', {})
                last_job = job_template.pop('last_job', {})
                related = last_job.pop('related', {})
                summary_fields = last_job.pop('summary_fields', {})
                job_env = last_job.pop('job_env', {})
                stdout = last_job.pop('stdout', {}).get('content')
                self.app.render(res, details=True)
                self.c('\njob template', 'underline')
                self.app.render(job_template, details=True)
                self.c('\njob %s stdout' % last_job['id'], 'underline')
                print(stdout)
            else:
                self.app.render(res, details=True)
        else:
            uri = '/v1.0/nrs/provider/applied_customizations'
            params = ['instance', 'uuids']
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='applied_customizations', headers=self._meta.customization_headers,
                            fields=self._meta.customization_fields)

    @ex(
        help='add applied customization',
        description='add applied customization',
        arguments=ARGS([
            (['container'], {'help': 'container id', 'action': 'store', 'type': str, 'default': None}),
            (['compute_zone'], {'help': 'compute zone id', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'description', 'action': 'store', 'type': str, 'default': None}),
            (['customization'], {'help': 'customization id', 'action': 'store', 'type': str, 'default': None}),
            (['instance'], {'help': 'instance id', 'action': 'store', 'type': str, 'default': None}),
            (['-extra_vars'], {'help': 'extra vars passed as json file', 'action': 'store', 'type': str, 'default': None}),
            (['-playbook'], {'help': 'container id', 'action': 'store', 'type': str, 'default': 'main.yml'}),
            (['-verbosity'], {'help': 'container id', 'action': 'store', 'type': int, 'default': 0}),
        ])
    )
    def applied_customization_add(self):
        container = self.app.pargs.container
        compute_zone = self.app.pargs.compute_zone
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        customization = self.app.pargs.customization
        extra_vars = self.app.pargs.extra_vars
        if desc is None:
            desc = name
        if extra_vars is not None:
            extra_vars = load_config(extra_vars)
        else:
            extra_vars = {}
        data = {
            'container': container,
            'compute_zone': compute_zone,
            'name': name,
            'desc': desc,
            'customization': customization,
            'instances': [{'id': self.app.pargs.instance}],
            'extra_vars': extra_vars,
            'playbook': self.app.pargs.playbook,
            'verbosity': self.app.pargs.verbosity,
        }
        uri = '/v1.0/nrs/provider/applied_customizations'
        res = self.cmp_post(uri, data={'applied_customization': data})
        self.app.render({'msg': 'add applied customization %s' % res['uuid']})

    @ex(
        help='delete applied customization. It removes customization entities from CMP and AWX platforms but do not '
             'uninstall software from hosts where customization was applied',
        description='delete applied customization. It removes customization entities from CMP and AWX platforms but do '
                    'not uninstall software from hosts where customization was applied',
        arguments=ARGS([
            (['id'], {'help': 'applied customization id', 'action': 'store', 'type': str, 'default': None}),
            (['-force'], {'help': 'if true force the delete', 'action': 'store', 'type': str, 'default': True}),
        ])
    )
    def applied_customization_del(self):
        oid = self.app.pargs.id
        force = self.app.pargs.force
        uri = '/v1.0/nrs/provider/applied_customizations/%s' % oid
        if force is True:
            uri += '?force=true'
        self.cmp_delete(uri, entity='applied customization %s' % oid)

    #
    # stack
    #
    @ex(
        help='get stack',
        description='get stack',
        arguments=PARGS([
            (['-id'], {'help': 'stack id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def stack_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v2.0/nrs/provider/stacks/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('stack')
                actions = res.pop('actions')
                resources = res.pop('resources')
                inputs = res.pop('inputs', {})
                outputs = res.pop('outputs')
                self.app.render(res, details=True)

                self.c('\ninputs', 'underline')
                self.app.render(inputs, details=True)
                self.c('\nactions', 'underline')
                headers = ['id', 'name', 'state', 'creation', 'modified']
                fields = ['uuid', 'name', 'state', 'date.creation', 'date.modified']
                self.app.render(actions, headers=headers, fields=fields, showindex='always')
                self.c('\nresources', 'underline')
                headers = ['id', 'name', 'state', 'active']
                fields = ['uuid', 'name', 'state', 'active']
                self.app.render(resources, headers=headers, fields=fields)
                self.c('\noutputs', 'underline')
                self.app.render(outputs, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v2.0/nrs/provider/stacks'
            res = self.cmp_get(uri, data=data)
            headers = ['id', 'name', 'parent', 'state', 'type', 'actions', 'resources', 'creation']
            fields = ['uuid', 'name', 'parent', 'state', 'attributes.stack_type', 'actions', 'resources',
                      'date.creation']
            self.app.render(res, key='stacks', headers=headers, fields=fields)

    @ex(
        help='get stack action',
        description='get stack action',
        arguments=PARGS([
            (['id'], {'help': 'stack id', 'action': 'store', 'type': str, 'default': None}),
            (['action'], {'help': 'action index', 'action': 'store', 'type': int, 'default': None}),
        ])
    )
    def stack_action_get(self):
        oid = self.app.pargs.id
        action_index = self.app.pargs.action
        uri = '/v2.0/nrs/provider/stacks/%s' % oid
        res = self.cmp_get(uri)
        actions = dict_get(res, 'stack.actions')
        try:
            action = actions[action_index]
        except:
            raise Exception('action %s with index does note exist' % action_index)

        if self.is_output_text():
            attributes = action.pop('attributes')
            resource = attributes.pop('resource')
            params = attributes.pop('params')
            self.app.render(action, details=True)
            self.c('\nresource', 'underline')
            self.app.render(resource, details=True)
            self.c('\nparams', 'underline')
            self.app.render(params, details=True)
        else:
            self.app.render(res, details=True)

    #
    # sql stack
    #
    @ex(
        help='get stack sql',
        description='get stack sql',
        arguments=PARGS([
            (['-id'], {'help': 'stack id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def stack_sql_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v2.0/nrs/provider/sql_stacks/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('sql_stack')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v2.0/nrs/provider/sql_stacks'
            res = self.cmp_get(uri, data=data)
            headers = ['id', 'name', 'parent', 'state', 'runstate', 'engine', 'version', 'storage',
                       'charset', 'timezone', 'license', 'listener',
                       'vpc', 'security_groups', 'date']
            fields = ['id', 'name', 'parent', 'state', 'runstate', 'attributes.engine',
                      'attributes.version', 'allocated_storage',
                      'attributes.charset', 'attributes.timezone', 'attributes.license',
                      'listener', 'vpc.name', 'security_groups.0.name', 'date.creation']
            self.app.render(res, key='sql_stacks', headers=headers, fields=fields)

    @ex(
        help='import stack sql',
        description='import stack sql',
        arguments=ARGS([
            (['name'], {'help': 'sql stack name', 'action': 'store', 'type': str, 'default': None}),
            (['physical_id'], {'help': 'compute instance id', 'action': 'store', 'type': str, 'default': None}),
            (['engine'], {'help': 'sql stack engine', 'action': 'store', 'type': str, 'default': None}),
            (['version'], {'help': 'sql stack engine version', 'action': 'store', 'type': str, 'default': None}),
            (['pwd'], {'help': 'sql stack admin password', 'action': 'store', 'type': str, 'default': None}),
            (['-charset'], {'help': 'sql stack charset', 'action': 'store', 'type': str, 'default': 'latin1'}),
            (['-timezone'], {'help': 'sql stack charset', 'action': 'store', 'type': str, 'default': 'Europe/Rome'}),

        ])
    )
    def stack_sql_import(self):
        name = self.app.pargs.name
        physical_id = self.app.pargs.physical_id
        engine = self.app.pargs.engine
        version = self.app.pargs.version
        pwd = self.app.pargs.pwd
        charset = self.app.pargs.charset
        timezone = self.app.pargs.timezone

        config = {
            'container': 'ResourceProvider01',
            'name': name,
            'desc': name,
            'physical_id': physical_id,
            'attribute': {},
            'resclass': 'beehive_resource.plugins.provider.entity.sql_stack_v2.SqlComputeStackV2',
            'configs': {
                'charset': charset,
                'timezone': timezone,
                'engine': engine,
                'version': version,
                'pwd': {'admin': pwd, 'db_superuser': '', 'db_appuser_pwd': ''},
                'user': {'db_superuser': 'system', 'db_appuser_pwd': 'test'}
            }
        }
        uri = '/v1.0/nrs/entities/import'
        res = self.cmp_post(uri, data={'resource': config})
        self.app.render({'msg': 'import sql stack %s' % name})

    @ex(
        help='get stack sql engines',
        description='get stack sql engines',
        arguments=ARGS([
        ])
    )
    def stack_sql_engine_get(self):
        uri = '/v2.0/nrs/provider/sql_stacks/engines'
        res = self.cmp_get(uri, data='')
        self.app.render(res, headers=['engine', 'version'], key='engines')

    @ex(
        help='get database credentials',
        description='get database credentials',
        arguments=ARGS([
            (['id'], {'help': 'sql stack id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def stack_sql_credential_get(self):
        oid = self.app.pargs.id
        uri = '/v2.0/nrs/provider/sql_stacks/%s/credentials' % oid
        res = self.cmp_get(uri, data='')
        self.app.render(res, headers=['name', 'password'], key='sql_stack_credentials')

    @ex(
        help='set database credentials. Only root support for the moment',
        description='set database credentials. Only root support for the moment',
        arguments=ARGS([
            (['id'], {'help': 'sql stack id', 'action': 'store', 'type': str, 'default': None}),
            (['user'], {'help': 'user name', 'action': 'store', 'type': str, 'default': None}),
            (['pwd'], {'help': 'user password. If pwd start with @ pwd is the name of a file that contains password',
                       'action': 'store', 'type': str, 'default': None})
        ])
    )
    def stack_sql_credential_set(self):
        oid = self.app.pargs.id
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        if pwd.find('@') == 0:
            pwd = read_file(pwd.lstrip('@'))
        uri = '/v2.0/nrs/provider/sql_stacks/%s/credentials' % oid
        self.cmp_put(uri, data={'user': user, 'password': pwd})
        self.app.render({'msg': 'set %s password' % user})

    @ex(
        help='get stack sql dbs',
        description='get stack sql dbs',
        arguments=PARGS([
            (['id'], {'help': 'stack id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def stack_sql_db_get(self):
        oid = self.app.pargs.id
        uri = '/v2.0/nrs/provider/sql_stacks/%s/action' % oid
        data = {'action': {'get_dbs': True}}
        res = self.cmp_put(uri, data=data)
        res = res.get('dbs')
        self.app.render(res, headers=['db_name', 'charset', 'collation'])

    @ex(
        help='get stack sql dbs',
        description='get stack sql dbs',
        arguments=PARGS([
            (['id'], {'help': 'stack id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def stack_sql_user_get(self):
        oid = self.app.pargs.id
        uri = '/v2.0/nrs/provider/sql_stacks/%s/action' % oid
        data = {'action': {'get_users': True}}
        res = self.cmp_put(uri, data=data)
        res = res.get('users')
        self.app.render(res, headers=['user', 'host', 'account_locked', 'max_connections', 'plugin'])

    @ex(
        help='enable mailx',
        description='enable mailx',
        arguments=PARGS([
            (['id'], {'help': 'stack id', 'action': 'store', 'type': str, 'default': None}),
            (['-relayhost'], {'help': 'remote relay mail server, default is xxx.csi.it', 'action': 'store',
                              'type': str, 'default': 'xxx.csi.it'}),
        ])
    )
    def stack_sql_mailx_enable(self):
        oid = self.app.pargs.id
        relayhost = self.app.pargs.relayhost
        uri = '/v2.0/nrs/provider/sql_stacks/%s/action' % oid
        data = {'action': {'enable_mailx': {'relayhost': relayhost}}}
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'enable mailx'})

    @ex(
        help='register db server on haproxy',
        description='register db server on haproxy',
        arguments=PARGS([
            (['id'], {'help': 'stack id', 'action': 'store', 'type': str, 'default': None}),
            (['-ports'], {'help': 'range of haproxy ports that clients can connect to [default=10100:10999]',
                          'action': 'store', 'type': str, 'default': '10100:10999'})
        ])
    )
    def stack_sql_haproxy_register(self):
        oid = self.app.pargs.id
        ports = self.app.pargs.ports
        ports = ports.strip().split(':')
        port_ini = ports[0]
        port_fin = ports[1]
        uri = '/v2.0/nrs/provider/sql_stacks/%s/action' % oid
        data = {'action': {'haproxy_register': {'port_ini': port_ini, 'port_fin': port_fin}}}
        self.cmp_put(uri, data=data)
        msg = 'register db server %s on haproxy' % oid
        self.app.render({'msg': msg})

    @ex(
        help='deregister db server from haproxy',
        description='deregister db server from haproxy',
        arguments=PARGS([
            (['id'], {'help': 'stack id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def stack_sql_haproxy_deregister(self):
        oid = self.app.pargs.id
        uri = '/v2.0/nrs/provider/sql_stacks/%s/action' % oid
        data = {'action': {'haproxy_deregister': True}}
        self.cmp_put(uri, data=data)
        msg = 'deregister db server %s from haproxy' % oid
        self.app.render({'msg': msg})

    #
    # oldstack
    #
    @ex(
        help='get provider old stack',
        description='get provider old stack',
        arguments=PARGS([
            (['-id'], {'help': 'old stack id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def oldstack_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v1.0/nrs/provider/stacks/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('stack')
                self.app.render(res, details=True)

                # get ssh management status
                self.c('\nmanagement status', 'underline')
                uri = '/v1.0/nrs/provider/stacks/%s/manage' % oid
                mgt = self.cmp_get(uri).get('is_managed', [])
                res = {
                    'is-managed': bool2str(mgt),
                    'has-backup': 'false',
                    'has-monitor': 'false',
                }
                self.app.render(res, details=True)

                # get dns
                self.c('\ndns resolution', 'underline')
                uri = '/v1.0/nrs/provider/stacks/%s/dns' % oid
                res = self.cmp_get(uri).get('dns', {})
                headers = ['id', 'name', 'ip_address', 'zone', 'container', 'fqdn']
                fields = ['id', 'name', 'ip_address', 'parent', 'container', 'fqdn']
                self.app.render(res, headers=headers, fields=fields)

                # get resources
                uri = '/v1.0/nrs/provider/stacks/%s/resources' % oid
                res = self.cmp_get(uri, data='').get('stack_resources')
                for item in res:
                    self.c('\nAvailability zone: %s' % item.get('availability_zone'), 'underline')
                    self.c('resources', 'underline')
                    self.app.render(item.get('resources', []), headers=['id', 'name', 'type'],
                                    fields=['uuid', 'name', '__meta__.definition'], maxsize=200, table_style='simple')
                    self.c('internal resources', 'underline')
                    headers = ['id', 'logical_id', 'name', 'type', 'creation', 'status', 'reason', 'required']
                    fields = ['physical_resource_id', 'logical_resource_id', 'resource_name', 'resource_type',
                              'creation_time', 'resource_status', 'resource_status_reason', 'required_by']
                    self.app.render(item.get('internal_resources', []), headers=headers, fields=fields, maxsize=40, 
                                    table_style='simple')

                # get inputs
                self.c('\ninputs', 'underline')
                uri = '/v1.0/nrs/provider/stacks/%s/inputs' % oid
                res = self.cmp_get(uri, data='').get('stack_inputs')
                for item in res:
                    self.c('availability zone: %s' % item.get('availability_zone'), 'underline')
                    resp = []
                    for k, v in item.get('inputs').items():
                        resp.append({'key': k, 'value': v})
                    self.app.render(resp, headers=['key', 'value'], maxsize=200)

                # get outputs
                self.c('\noutputs', 'underline')
                uri = '/v1.0/nrs/provider/stacks/%s/outputs' % oid
                res = self.cmp_get(uri, data='').get('stack_outputs')
                for item in res:
                    self.c('availability zone: %s' % item.get('availability_zone'), 'underline')
                    for out in item.get('outputs'):
                        print('----------------------------------------------------------')
                        print('output_key:')
                        print(out.get('output_key', None))
                        print('description:')
                        print(out.get('description', None))
                        print('output_value:')
                        print(out.get('output_value', None))
                        print('output_error:')
                        print(out.get('output_error', None))
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v1.0/nrs/provider/stacks'
            res = self.cmp_get(uri, data=data)
            headers = ['id', 'name', 'parent', 'state', 'runstate', 'type', 'engine', 'creation']
            fields = ['uuid', 'name', 'parent', 'state', 'runstate', 'attributes.stack_type', 'attributes.engine',
                      'date.creation']
            self.app.render(res, key='stacks', headers=headers, fields=fields)

    @ex(
        help='enable provider old stack management by ssh module',
        description='enable provider old stack management by ssh module',
        arguments=ARGS([
            (['id'], {'help': 'old stack id', 'action': 'store', 'type': str, 'default': None}),
            (['key'], {'help': 'server stack ssh key', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def oldstack_manage(self):
        """Enable provider computes instance management by ssh module
        """
        oid = self.app.pargs.id
        key = self.app.pargs.key

        data = {
            'manage': {
                'key': key
            }
        }
        uri = '/v1.0/nrs/provider/stacks/%s/manage' % oid
        res = self.cmp_post(uri, data=data).get('manage', [])
        self.app.render({'msg': 'enable old stack %s management with ssh node: %s' % (oid, res)})

    @ex(
        help='disable provider old stack management by ssh module',
        description='disable provider old stack management by ssh module',
        arguments=ARGS([
            (['id'], {'help': 'old stack id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def oldstack_unmanage(self):
        oid = self.app.pargs.id
        uri = '/v1.0/nrs/provider/stacks/%s/manage' % oid
        self.cmp_delete(uri, entity='compute old stack %s' % oid)

    @ex(
        help='add compute old stack dns resolution',
        description='add compute old stack dns resolution',
        arguments=ARGS([
            (['id'], {'help': 'old sql stack id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def oldstack_dns_add(self):
        oid = self.app.pargs.id
        uri = '/v1.0/nrs/provider/stacks/%s/dns' % oid
        res = self.cmp_post(uri)
        self.app.render({'msg': 'add old stack %s dns resolution' % oid})

    @ex(
        help='delete compute old stack dns resolution',
        description='delete compute old stack dns resolution',
        arguments=ARGS([
            (['id'], {'help': 'old sql stack id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def oldstack_dns_del(self):
        oid = self.app.pargs.id
        uri = '/v1.0/nrs/provider/stacks/%s/dns' % oid
        res = self.cmp_delete(uri, entity='old stack %s dns resolution' % oid)

    #
    # old sql stack
    #
    @ex(
        help='get provider old stack sql',
        description='get provider old stack sql',
        arguments=PARGS([
            (['-id'], {'help': 'old stack id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def oldstack_sql_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v1.0/nrs/provider/sql_stacks/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('sql_stack')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v1.0/nrs/provider/sql_stacks'
            res = self.cmp_get(uri, data=data)
            headers = ['id', 'name', 'parent', 'state', 'listener', 'vpc', 'security_group', 'creation', 'modified']
            fields = ['uuid', 'name', 'parent', 'state', 'stacks.0.listener', 'vpcs.0.name',
                      'security_groups.0.name', 'date.creation', 'date.modified']
            self.app.render(res, key='sql_stacks', headers=headers, fields=fields)

    @ex(
        help='get provider old stack sql engines',
        description='get provider old stack sql engines',
        arguments=ARGS([
            (['id'], {'help': 'old sql stack id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def oldstack_sql_engine_get(self):
        uri = '/v1.0/nrs/provider/sql_stacks/engines'
        res = self.cmp_get(uri, data='')
        self.app.render(res, headers=['engine', 'version'], key='engines')

    @ex(
        help='get database credentials',
        description='get database credentials',
        arguments=ARGS([
            (['id'], {'help': 'old sql stack id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def oldstack_sql_credential_get(self):
        oid = self.app.pargs.id
        uri = '/v1.0/nrs/provider/sql_stacks/%s/credentials' % oid
        res = self.cmp_get(uri, data='')
        self.app.render(res, headers=['name', 'pwd'], key='sql_stack_credentials')

    @ex(
        help='set database credentials. Only root support for the moment',
        description='set database credentials. Only root support for the moment',
        arguments=ARGS([
            (['id'], {'help': 'old sql stack id', 'action': 'store', 'type': str, 'default': None}),
            (['pwd'], {'help': 'old sql stack password', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def oldstack_sql_credential_set(self):
        oid = self.app.pargs.id
        pwd = self.app.pargs.pwd
        uri = '/v1.0/nrs/provider/sql_stacks/%s/credentials' % oid
        self.cmp_put(uri, data={'sql_stack_credentials': [{'user': 'root', 'pwd': pwd}]})
        self.app.render({'msg': 'set root password'})

    #
    # old app stack
    #
    @ex(
        help='get provider old stack app',
        description='get provider old stack app',
        arguments=PARGS([
            (['-id'], {'help': 'old stack id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def oldstack_app_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v1.0/nrs/provider/app_stacks/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('app_stack')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v1.0/nrs/provider/app_stacks'
            res = self.cmp_get(uri, data=data)
            headers = ['id', 'name', 'parent', 'state', 'listener', 'vpc', 'security_group', 'creation', 'modified']
            fields = ['uuid', 'name', 'parent', 'state', 'stacks.0.listener', 'vpcs.0.name',
                      'security_groups.0.name', 'date.creation', 'date.modified']
            self.app.render(res, key='app_stacks', headers=headers, fields=fields)

    #
    # gateway
    #
    @ex(
        help='get provider gateway',
        description='get provider gateway(s)',
        arguments=PARGS([
            (['-id'], {'help': 'gateway id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-attributes'], {'help': 'entity attributes', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def gateway_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v1.0/nrs/provider/gateways/%s' % oid
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('gateway')
                vpc = res.pop('vpc', {})
                internal_routers = res.pop('details', {}).get('internal_router', [])
                self.app.render(res, details=True)

                uplinks = vpc.get('uplinks', [])
                for uplink in uplinks:
                    uplink['type'] = 'uplink'
                internals = vpc.get('internals', [])
                for internal in internals:
                    internal['type'] = 'internal'
                transport = vpc.get('transport', [])
                transport['type'] = 'transport'
                vpcs = [transport]
                vpcs.extend(uplinks)
                vpcs.extend(internals)

                self.c('\n\nvpcs', 'underline')
                headers = ['id', 'uuid', 'name', 'parent', 'cidr', 'type']
                fields = ['id', 'uuid', 'name', 'parent', 'cidr', 'type']
                self.app.render(vpcs, headers=headers, fields=fields, maxsize=100)

                self.c('\n\nnat rules', 'underline')
                uri = '/v1.0/nrs/provider/gateways/%s/nat' % oid
                nats = self.cmp_get(uri).get('nat_rules')
                headers = ['role', 'id', 'action', 'desc', 'vnic', 'orig-address', 'orig-port', 'translate-address',
                           'translate-port', 'proto']
                fields = ['role', 'ruleId', 'action', 'description', 'vnic', 'originalAddress', 'originalPort',
                          'translatedAddress', 'translatedPort', 'protocol']
                self.app.render(nats, headers=headers, fields=fields, maxsize=100)

                self.c('\n\nfirewall rules', 'underline')
                uri = '/v1.0/nrs/provider/gateways/%s/firewall' % oid
                fws = self.cmp_get(uri).get('firewall_rules')
                for r in fws:
                    source = r.get('source', {})
                    new_source = []
                    for k, v in source.items():
                        if isinstance(v, list):
                            for v1 in v:
                                new_source.append('%s:%s' % (k, v1))
                        else:
                            new_source.append('%s:%s' % (k, v))
                    r['source'] = '\n'.join(new_source)

                    dest = r.get('destination', {})
                    new_dest = []
                    for k, v in dest.items():
                        if isinstance(v, list):
                            for v1 in v:
                                new_dest.append('%s:%s' % (k, v1))
                        else:
                            new_dest.append('%s:%s' % (k, v))
                    r['destination'] = '\n'.join(new_dest)

                    application = r.get('application', {})
                    new_application = []
                    for k, v in application.items():
                        if isinstance(v, list):
                            for v1 in v:
                                new_application.append('%s:%s' % (k, v1))
                        if isinstance(v, dict):
                            new_application.append('%s:' % k)
                            for k1, v1 in v.items():
                                new_application.append('  %s:%s' % (k1, v1))
                        else:
                            new_application.append('%s:%s' % (k, v))
                    r['application'] = '\n'.join(new_application)
                headers = ['role', 'id', 'name', 'type', 'action', 'enabled', 'source', 'destination', 'application']
                fields = ['role', 'id', 'name', 'ruleType', 'action', 'enabled', 'source', 'destination', 'application']
                self.app.render(fws, headers=headers, fields=fields, maxsize=100)

                self.c('\n\ninternal routers', 'underline')
                headers = ['id', 'name', 'container', 'parent', 'state', 'role', 'type', 'vnics', 'routes']
                fields = ['id', 'name', 'container', 'parent', 'state', 'role', '__meta__.definition',
                          'attributes.vnics', 'attributes.routes']
                transform = {
                    'attributes.vnics':
                        lambda ii:
                          '\n'.join(['%s:%s:%s' % (i.get('name', ''), i.get('type', ''), i.get('primary_address', ''))
                                     for i in ii if isinstance(i, dict)]),
                    'attributes.routes':
                        lambda ii: '\n'.join(['%s:%s' % (i.get('network', ''), i.get('next_hop', ''))
                                              for i in ii if isinstance(i, dict)])
                }
                self.app.render(internal_routers, headers=headers, fields=fields, maxsize=300, transform=transform)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v1.0/nrs/provider/gateways'
            res = self.cmp_get(uri, data=data)
            for item in res.get('gateways'):
                item['vpcs'] = '\n'.join([
                    'uplink:    %s' % dict_get(item, 'vpc.uplinks.0.cidr'),
                    'transport: %s' % dict_get(item, 'vpc.transport.cidr'),
                    'internal:  %s' % dict_get(item, 'vpc.internals.0.cidr'),
                ])
                item['external_ip_address'] = '\n'.join(['%s:%s' % (k, v) for k, v in
                                                         item.get('external_ip_address', {}).items()])

            self.app.render(res, key='gateways', headers=self._meta.gateway_headers, fields=self._meta.gateway_fields,
                            maxsize=200)

    @ex(
        help='get provider gateway credentials',
        description='get provider gateway credentials',
        arguments=PARGS([
            (['id'], {'help': 'gateway id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def gateway_credentials_get(self):
        oid = self.app.pargs.id
        uri = '/v1.0/nrs/provider/gateways/%s/credentials' % oid
        res = self.cmp_get(uri)
        res = res.get('credentials')
        self.app.render(res, headers=['user', 'password'])

    @ex(
        help='set provider gateway default route',
        description='set provider gateway default route',
        arguments=PARGS([
            (['id'], {'help': 'gateway id', 'action': 'store', 'type': str, 'default': None}),
            (['-role'], {'help': 'gateway role. Can be default [default], primary or secondary', 'action': 'store',
                         'type': str, 'default': 'default'}),
        ])
    )
    def gateway_default_route_set(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        uri = '/v1.0/nrs/provider/gateways/%s/route/default' % oid
        res = self.cmp_put(uri, data={'role': role})
        self.app.render({'msg': 'set gateway %s deafult route with role %s' % (oid, role)})

    @ex(
        help='add provider gateway firewall rule',
        description='add provider gateway firewall rule',
        arguments=PARGS([
            (['id'], {'help': 'gateway id', 'action': 'store', 'type': str, 'default': None}),
            (['-role'], {'help': 'gateway role. Can be default [default], primary or secondary', 'action': 'store',
                         'type': str, 'default': 'default'}),
            (['-action'], {'help': 'firewall rule action. Can be accept [default], deny', 'action': 'store',
                           'type': str, 'default': 'accept'}),
            (['-enabled'], {'help': 'firewall rule status', 'action': 'store', 'type': bool, 'default': True}),
            (['-logged'], {'help': 'firewall rule logged', 'action': 'store', 'type': bool, 'default': False}),
            (['-direction'], {'help': 'firewall rule direction. Can be: in, out, inout [deafult]', 'action': 'store',
                              'type': str, 'default': None}),
            (['-source'], {'help': 'rule source. list of comma separated item like: ip:<ipAddress>, '
                                   'grp:<groupingObjectId>, vnic:<vnicGroupId>', 'action': 'store', 'type': str,
                           'default': None}),
            (['-dest'], {'help': 'rule destination. list of comma separated item like: ip:<ipAddress>, '
                                 'grp:<groupingObjectId>, vnic:<vnicGroupId>', 'action': 'store', 'type': str,
                         'default': None}),
            (['-appl'], {'help': 'rule application. list of comma separated item like: app:<applicationId>, '
                                 'ser:proto+port+source_port', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def gateway_firewall_rule_add(self):
        oid = self.app.pargs.id
        data = {
            'role': self.app.pargs.role,
            'action': self.app.pargs.action,
            'enabled': self.app.pargs.enabled,
            'logged': self.app.pargs.logged,
            'direction': self.app.pargs.direction,
            'source': self.app.pargs.source,
            'dest': self.app.pargs.dest,
            'appl': self.app.pargs.appl
        }
        uri = '/v1.0/nrs/provider/gateways/%s/firewall' % oid
        self.cmp_post(uri, data={'firewall_rule': data})
        self.app.render({'msg': 'add gateway %s firewall rule' % oid})

    @ex(
        help='delete provider gateway firewall rule',
        description='delete provider gateway firewall rule',
        arguments=PARGS([
            (['id'], {'help': 'gateway id', 'action': 'store', 'type': str, 'default': None}),
            (['-role'], {'help': 'gateway role. Can be default [default], primary or secondary', 'action': 'store',
                         'type': str, 'default': 'default'}),
            (['-action'], {'help': 'firewall rule action. Can be accept [default], deny', 'action': 'store',
                           'type': str, 'default': 'accept'}),
            (['-enabled'], {'help': 'firewall rule status', 'action': 'store', 'type': bool, 'default': True}),
            (['-logged'], {'help': 'firewall rule logged', 'action': 'store', 'type': bool, 'default': False}),
            (['-direction'], {'help': 'firewall rule direction. Can be: in, out, inout [deafult]', 'action': 'store',
                              'type': str, 'default': None}),
            (['-source'], {'help': 'rule source. list of comma separated item like: ip:<ipAddress>, '
                                   'grp:<groupingObjectId>, vnic:<vnicGroupId>', 'action': 'store', 'type': str,
                           'default': None}),
            (['-dest'], {'help': 'rule destination. list of comma separated item like: ip:<ipAddress>, '
                                 'grp:<groupingObjectId>, vnic:<vnicGroupId>', 'action': 'store', 'type': str,
                         'default': None}),
            (['-appl'], {'help': 'rule application. list of comma separated item like: app:<applicationId>, '
                                 'ser:proto+port+source_port', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def gateway_firewall_rule_del(self):
        oid = self.app.pargs.id
        data = {
            'role': self.app.pargs.role,
            'action': self.app.pargs.action,
            'direction': self.app.pargs.direction,
            'source': self.app.pargs.source,
            'dest': self.app.pargs.dest,
            'appl': self.app.pargs.appl
        }
        uri = '/v1.0/nrs/provider/gateways/%s/firewall' % oid
        self.cmp_delete(uri, data={'firewall_rule': data}, entity='gateway %s firewall rule' % oid)

    @ex(
        help='add provider gateway nat rule',
        description='add provider gateway nat rule',
        arguments=PARGS([
            (['id'], {'help': 'gateway id', 'action': 'store', 'type': str, 'default': None}),
            (['-role'], {'help': 'gateway role. Can be default [default], primary or secondary', 'action': 'store',
                         'type': str, 'default': 'default'}),
            (['action'], {'help': 'nat rule action. Can be snat e dnat', 'action': 'store', 'type': str}),
            (['-enabled'], {'help': 'nat rule status', 'action': 'store', 'type': bool, 'default': True}),
            (['-logged'], {'help': 'nat rule logged', 'action': 'store', 'type': bool, 'default': False}),
            (['-original_address'], {'help': 'original address', 'action': 'store', 'type': str, 'default': None}),
            (['-translated_address'], {'help': 'translated address', 'action': 'store', 'type': str, 'default': None}),
            (['-original_port'], {'help': 'original port', 'action': 'store', 'type': int, 'default': None}),
            (['-translated_port'], {'help': 'translated port', 'action': 'store', 'type': int, 'default': None}),
            (['-protocol'], {'help': 'nat protocol. Ex. tcp', 'action': 'store', 'type': str, 'default': None}),
            (['-vnic'], {'help': 'nat vnic index. Ex. 0', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def gateway_nat_rule_add(self):
        oid = self.app.pargs.id
        data = {
            'role': self.app.pargs.role,
            'action': self.app.pargs.action,
            'enabled': self.app.pargs.enabled,
            'logged': self.app.pargs.logged,
            'original_address': self.app.pargs.original_address,
            'translated_address': self.app.pargs.translated_address,
            'original_port': self.app.pargs.original_port,
            'translated_port': self.app.pargs.translated_port,
            'protocol': self.app.pargs.protocol,
            'vnic': self.app.pargs.vnic
        }
        uri = '/v1.0/nrs/provider/gateways/%s/nat' % oid
        self.cmp_post(uri, data={'nat_rule': data})
        self.app.render({'msg': 'add gateway %s nat rule' % oid})

    @ex(
        help='delete provider gateway nat rule',
        description='delete provider gateway nat rule',
        arguments=PARGS([
            (['id'], {'help': 'gateway id', 'action': 'store', 'type': str, 'default': None}),
            (['-role'], {'help': 'gateway role. Can be default [default], primary or secondary', 'action': 'store',
                         'type': str, 'default': 'default'}),
            (['action'], {'help': 'nat rule action. Can be snat e dnat', 'action': 'store', 'type': str}),
            (['-original_address'], {'help': 'original address', 'action': 'store', 'type': str, 'default': None}),
            (['-translated_address'], {'help': 'translated address', 'action': 'store', 'type': str, 'default': None}),
            (['-original_port'], {'help': 'original port', 'action': 'store', 'type': int, 'default': None}),
            (['-translated_port'], {'help': 'translated port', 'action': 'store', 'type': int, 'default': None}),
            (['-protocol'], {'help': 'nat protocol. Ex. tcp', 'action': 'store', 'type': str, 'default': None}),
            (['-vnic'], {'help': 'nat vnic. eEx. vinc0', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def gateway_nat_rule_del(self):
        oid = self.app.pargs.id
        data = {
            'role': self.app.pargs.role,
            'action': self.app.pargs.action,
            'original_address': self.app.pargs.original_address,
            'translated_address': self.app.pargs.translated_address,
            'original_port': self.app.pargs.original_port,
            'translated_port': self.app.pargs.translated_port,
            'protocol': self.app.pargs.protocol,
            'vnic': self.app.pargs.vnic
        }
        uri = '/v1.0/nrs/provider/gateways/%s/nat' % oid
        self.cmp_delete(uri, data={'nat_rule': data}, entity='gateway %s nat rule' % oid)

    @ex(
        help='get provider ssh gateway',
        description='get provider ssh gateway',
        arguments=PARGS([
            (['-id'], {'help': 'entity id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'entity name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'entity description', 'action': 'store', 'type': str, 'default': None}),
            (['-parent'], {'help': 'entity parent', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'entity state', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'entity tags', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def ssh_gw_conf_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '/v1.0/nrs/provider/sshgw/configuration/%s' % oid
            res = self.cmp_get(uri)
            if self.is_output_text():
                res = res.get('configuration')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'desc', 'parent', 'state', 'tags']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '/v1.0/nrs/provider/sshgw/configuration'
            res = self.cmp_get(uri, data=data)
            headers = ['id', 'name', 'parent', 'state', 'creation', 'modified']
            fields = ['uuid', 'name', 'parent', 'state', 'date.creation', 'date.modified']
            self.app.render(res, key='configurations', headers=headers, fields=fields)

    @ex(
        help='add ssh gw configuration',
        description='add ssh gw configuration',
        arguments=ARGS([
            (['container'], {'help': 'container uuid', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'configuration name', 'action': 'store', 'type': str, 'default': None}),
            (['gw_type'], {'metavar':'gw_type','help': 'ssh gateway type (gw_dbaas,gw_cpaas,gw_ext)', 'choices':['gw_dbaas','gw_cpaas','gw_ext'],'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'configuration description', 'action': 'store', 'type': str, 'default': None}),
            (['-res_id'], {'help': 'resource uuid of the destination cli object','action':'store','type':str,'default':None}),
            (['-ip'], {'help': 'ip and port. only if gw_type=gw_ext','action':'store','type':str,'default':None})
        ])
    )
    def ssh_gw_conf_add(self):
        if self.app.pargs.gw_type != 'gw_ext' and self.app.pargs.res_id is None:
            self.app.pargs.ip = None
            self.app.error('you need to specify -res_id for the chosen value of gw_type')
            return
        
        if self.app.pargs.gw_type == 'gw_ext' and self.app.pargs.ip is None:
            self.app.pargs.res_id = None
            self.app.error('you need to specify -ip for the chosen value of gw_type')
            return
        
        configuration = {}
        from beecell.simple import set_request_params
        configuration.update(set_request_params(self.app.pargs, ['container','name','desc','gw_type','res_id','ip']))
        data = {
            "configuration":configuration
        }
        uri = '/v1.0/nrs/provider/sshgw/configuration'
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)