# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from urllib.parse import urlencode
from beecell.types.type_dict import dict_get
from beehive3_cli.plugins.platform.util.customize_plugins import CustomizePlugin


class ResourceCustomizePlugin(CustomizePlugin):
    def __init__(self, manager):
        super().__init__(manager)

        manager.controller._meta.cmp = {'baseuri': '/v1.0/nrs', 'subsystem': 'resource'}
        manager.controller.configure_cmp_api_client()

    def __create_tags(self, configs):
        if self.has_config(configs, 'resource.tags') is False:
            return None

        self.write('##### RESOURCE TAGS')
        BASE_URI = '/v1.0/nrs/tags'

        for obj in dict_get(configs, 'resource.tags'):
            GROUP_URI = '%s/%s' % (BASE_URI, obj['value'])

            name = obj['value']

            exists = self.cmp_exists(GROUP_URI, 'Resource tag %s already exists' % name)

            if exists is False:
                self.cmp_post(BASE_URI, {'resourcetag': obj}, 'Add resource tag: %s' % name)

    def __create_containers(self, configs):
        if self.has_config(configs, 'resource.containers') is False:
            return None

        self.write('##### RESOURCE CONTAINERS')
        BASE_URI = '/v1.0/nrs/containers'

        for obj in dict_get(configs, 'resource.containers'):
            GROUP_URI = '%s/%s' % (BASE_URI, obj['name'])
            name = obj['name']
            exists = self.cmp_exists(GROUP_URI, 'Resource container %s already exists' % name)

            if exists is False:
                self.cmp_post(BASE_URI, {'resourcecontainer': obj}, 'Add resource containers: %s' % name)

    def __sync_containers(self, configs):
        if self.has_config(configs, 'resource.containers-sync') is False:
            return None

        self.write('##### RESOURCE CONTAINERS SYNC')
        BASE_URI = '/v1.0/nrs/containers'

        for obj in dict_get(configs, 'resource.containers-sync'):
            GROUP_URI = '%s/%s' % (BASE_URI, obj['name'])
            name = obj['name']
            container_types = obj['types']
            exists = self.cmp_exists(GROUP_URI, 'Resource container %s exists' % name)

            if exists is False:
                self.write('container %s does not exist' % name)
                continue

            for rtype in container_types:
                data = {'synchronize': {'types': rtype, 'new': True, 'died': False, 'changed': False}}
                res = self.cmp_put(BASE_URI + '/%s/discover' % name, data,
                                   'Sync resource container %s for type %s' % (name, rtype))

    def __create_vsphere_flavors(self, configs):
        if self.has_config(configs, 'resource.vsphere.flavors') is False:
            return None

        self.write('##### RESOURCE VSPHERE FLAVOR')
        BASE_URI = '/v1.0/nrs/vsphere/flavors'

        for obj in dict_get(configs, 'resource.vsphere.flavors'):
            OBJ_URI = '%s/%s' % (BASE_URI, obj['name'])
            name = obj['name']
            #exists = self.cmp_exists(OBJ_URI, 'Vsphere flavor %s already exists' % name)

            #if exists is False:
            self.cmp_post(BASE_URI, {'flavor': obj}, 'Add vsphere flavor: %s' % name)

    def __create_vsphere_volumetypes(self, configs):
        if self.has_config(configs, 'resource.vsphere.volumetypes') is False:
            return None

        self.write('##### RESOURCE VSPHERE VOLUMETYPE')
        BASE_URI = '/v1.0/nrs/vsphere/volumetypes'

        for obj in dict_get(configs, 'resource.vsphere.volumetypes'):
            name = obj['name']
            datastores = obj.pop('datastores', [])
            volumetype = self.cmp_exists2(BASE_URI, 'Vsphere volumetype %s already exists' % name,
                                          data={'container': obj.get('container'), 'name': name})

            if volumetype is None:
                volumetype = self.cmp_post(BASE_URI, {'volumetype': obj}, 'Add vsphere volumetype: %s' % name).\
                    get('uuid')

            for datastore in datastores:
                OBJ_URI = '%s/%s' % (BASE_URI, volumetype)
                uri = OBJ_URI + '/datastores'
                msg = 'Add vsphere volumetype %s datastores: %s' % (volumetype, datastore['uuid'])
                self.cmp_post(uri, {'datastore': datastore}, msg)

    def __create_openstack_flavors(self, configs):
        if self.has_config(configs, 'resource.openstack.flavors') is False:
            return None

        self.write('##### RESOURCE OPENSTACK FLAVOR')
        BASE_URI = '/v1.0/nrs/openstack/flavors'

        for obj in dict_get(configs, 'resource.openstack.flavors'):
            # OBJ_URI = '%s/%s' % (BASE_URI, obj['name'])
            name = obj['name']
            extra_specs = obj.pop('extra_specs', None)
            data = {'name': name, 'container': obj['container']}
            exists = self.cmp_exists2(BASE_URI, 'Openstack flavor %s already exists' % name, data=data,
                                      key='flavors.0.id')
            if exists is None:
                flavor = self.cmp_post(BASE_URI, {'flavor': obj}, 'Add openstack flavor: %s' % name)
                if extra_specs is not None:
                    OBJ_URI = '%s/%s' % (BASE_URI, flavor['uuid'])
                    self.cmp_put(OBJ_URI, {'flavor': {'extra_specs': extra_specs}},
                                 'set openstack flavor %s extra_specs: %s' % (name, extra_specs))

    def __create_dns_zones(self, configs):
        if self.has_config(configs, 'resource.dns.zones') is False:
            return None

        self.write('##### RESOURCE DNS ZONE')
        BASE_URI = '/v1.0/nrs/dns/zones'

        for obj in dict_get(configs, 'resource.dns.zones'):
            OBJ_URI = '%s/%s' % (BASE_URI, obj['name'])
            name = obj['name']
            obj_records = obj.pop('records', '')
            exists = self.cmp_exists(OBJ_URI, 'Dns zone %s already exists' % name)

            if exists is False:
                self.cmp_post(BASE_URI, {'zone': obj}, 'Add dns zone: %s' % name)

            # # append records
            # file = self.manager.load_file(obj_records)
            # for row in file.split('\n'):
            #     if row.find('$') == 0:
            #         continue
            #     m = re.findall(r'([\w\-\.]+)\s*', row)
            #     if len(m) > 0:
            #         name = m[0]
            #         records = [{'name': m[0], 'type': m[1], 'value': m[2]}]
            #         uri = OBJ_URI + '/import'
            #         res = self.cmp_put(uri, {'records': records}, '')
            #         if res.get('records').get(name) is True:
            #             print('Import records in zone %s: %s' % (name, res))
            #         else:
            #             self.error('Records in zone %s already exist: %s' % (name, records))

    def __create_provider_regions(self, configs):
        if self.has_config(configs, 'resource.provider.regions') is False:
            return None

        self.write('##### RESOURCE PROVIDER REGION')
        BASE_URI = '/v1.0/nrs/provider/regions'

        for obj in dict_get(configs, 'resource.provider.regions'):
            OBJ_URI = '%s/%s' % (BASE_URI, obj['name'])
            name = obj['name']
            exists = self.cmp_exists(OBJ_URI, 'Provider region %s already exists' % name)

            if exists is False:
                self.cmp_post(BASE_URI, {'region': obj}, 'Add provider region: %s' % name)

    def __create_provider_sites(self, configs):
        if self.has_config(configs, 'resource.provider.sites') is False:
            return None

        self.write('##### RESOURCE PROVIDER SITES')
        BASE_URI = '/v1.0/nrs/provider/sites'

        for obj in dict_get(configs, 'resource.provider.sites'):
            OBJ_URI = '%s/%s' % (BASE_URI, obj['name'])
            name = obj['name']
            orchestrators = obj.pop('orchestrators', [])
            exists = self.cmp_exists(OBJ_URI, 'Provider site %s already exists' % name)

            if exists is False:
                self.cmp_post(BASE_URI, {'site': obj}, 'Add provider site: %s' % name)

            for orchestrator in orchestrators:
                if orchestrator['type'] == 'openstack':
                    # get domain
                    data = urlencode({'container': orchestrator['id'], 'name': 'Default'})
                    domain = self.cmp_get('/v1.0/nrs/openstack/domains', data=data)
                    orchestrator['config']['domain'] = domain['domains'][0]['id']
                uri = OBJ_URI + '/orchestrators'
                msg = 'Add site %s orchestrator: %s' % (name, orchestrator['id'])
                res = self.cmp_post(uri, {'orchestrator': orchestrator}, msg)

    def __create_provider_compute_zones(self, configs):
        if self.has_config(configs, 'resource.provider.compute_zones') is False:
            return None

        self.write('##### RESOURCE PROVIDER COMPUTE ZONES')
        BASE_URI = '/v1.0/nrs/provider/compute_zones'

        for obj in dict_get(configs, 'resource.provider.compute_zones'):
            OBJ_URI = '%s/%s' % (BASE_URI, obj['name'])
            name = obj['name']
            quota = obj.get('quota', {})
            sites = obj.pop('sites', [])
            exists = self.cmp_exists(OBJ_URI, 'Provider compute_zone %s already exists' % name)

            if exists is False:
                self.cmp_post(BASE_URI, {'compute_zone': obj}, 'Add provider compute_zone: %s' % name)

            for site in sites:
                data = {
                    'availability_zone': {
                        'id': site,
                        'orchestrator_tag': 'default',
                        'quota': quota
                    }
                }
                uri = OBJ_URI + '/availability_zones'
                msg = 'Add compute_zone %s availability_zones: %s' % (name, site)
                self.cmp_post(uri, data, msg)

    def __create_provider_site_networks(self, configs):
        # patch to maintains compatibility with old file syntax
        if self.has_config(configs, 'resource.provider.site_networks') is False and \
                self.has_config(configs, 'resource.entities.site_networks') is False:
            return None

        self.write('##### RESOURCE PROVIDER SITE NETWORK')
        BASE_URI = '/v2.0/nrs/provider/site_networks'

        nets = dict_get(configs, 'resource.provider.site_networks', default=[])
        nets.extend(dict_get(configs, 'resource.entities.site_networks', default=[]))

        for obj in nets:
            OBJ_URI = '%s/%s' % (BASE_URI, obj['name'])
            name = obj['name']
            subnets = obj.pop('subnets', [])
            exists = self.cmp_exists(OBJ_URI, 'Provider site_network %s already exists' % name)

            if exists is False:
                self.cmp_post(BASE_URI, {'site_network': obj}, 'Add provider site_network: %s' % name)

            data = {'subnets': subnets}
            uri = OBJ_URI + '/subnets'
            msg = 'Add site_network %s subnets: %s' % (name, subnets)
            self.cmp_post(uri, data, msg)

    def __create_provider_flavors(self, configs):
        if self.has_config(configs, 'resource.provider.flavors') is False:
            return None

        self.write('##### RESOURCE PROVIDER FLAVORS')
        BASE_URI = '/v1.0/nrs/provider/flavors'

        for obj in dict_get(configs, 'resource.provider.flavors'):
            OBJ_URI = '%s/%s' % (BASE_URI, obj['name'])
            name = obj['name']
            exists = self.cmp_exists(OBJ_URI, 'Provider flavor %s already exists' % name)

            if exists is False:
                self.cmp_post(BASE_URI + '/import', {'flavor': obj}, 'Add provider flavor: %s' % name)

    def __create_provider_volumeflavors(self, configs):
        if self.has_config(configs, 'resource.provider.volumeflavors') is False:
            return None

        self.write('##### RESOURCE PROVIDER VOLUME FLAVORS')
        BASE_URI = '/v1.0/nrs/provider/volumeflavors'

        for obj in dict_get(configs, 'resource.provider.volumeflavors'):
            OBJ_URI = '%s/%s' % (BASE_URI, obj['name'])
            name = obj['name']
            exists = self.cmp_exists(OBJ_URI, 'Provider volumeflavor %s already exists' % name)

            if exists is False:
                self.cmp_post(BASE_URI + '/import', {'volumeflavor': obj}, 'Update provider volumeflavor: %s' % name)
            else:
                obj = {'volume_types': obj.get('volume_types', [])}
                self.cmp_put(OBJ_URI, {'volumeflavor': obj}, 'Update provider volumeflavor: %s' % name)

    def __create_provider_images(self, configs):
        if self.has_config(configs, 'resource.provider.images') is False:
            return None

        self.write('##### RESOURCE PROVIDER IMAGES')
        BASE_URI = '/v1.0/nrs/provider/images'

        for obj in dict_get(configs, 'resource.provider.images'):
            OBJ_URI = '%s/%s' % (BASE_URI, obj['name'])
            name = obj['name']
            exists = self.cmp_exists(OBJ_URI, 'Provider image %s already exists' % name)

            if exists is False:
                self.cmp_post(BASE_URI + '/import', {'image': obj}, 'Add provider image: %s' % name)
            else:
                data = {'templates': obj.get('templates', [])}
                self.cmp_put(OBJ_URI, {'image': data}, msg='Update image %s' % name)

    def __create_provider_customizations(self, configs):
        if self.has_config(configs, 'resource.provider.customizations') is False:
            return None

        self.write('##### RESOURCE PROVIDER CUSTOMIZATIONS')
        BASE_URI = '/v1.0/nrs/provider/customizations'

        for obj in dict_get(configs, 'resource.provider.customizations'):
            OBJ_URI = '%s/%s' % (BASE_URI, obj['name'])
            name = obj['name']
            exists = self.cmp_exists(OBJ_URI, 'Provider customization %s already exists' % name)

            if exists is False:
                self.cmp_post(BASE_URI, {'customization': obj}, 'Add provider customization: %s' % name)
            else:
                data = {'templates': obj.get('templates', [])}
                self.cmp_put(OBJ_URI, {'customization': data}, msg='Update customization %s' % name)

    def run(self, configs):
        self.__create_tags(configs)
        self.__create_containers(configs)
        self.__sync_containers(configs)
        self.__create_vsphere_flavors(configs)
        self.__create_vsphere_volumetypes(configs)
        self.__create_openstack_flavors(configs)
        self.__create_dns_zones(configs)
        self.__create_provider_regions(configs)
        self.__create_provider_sites(configs)
        self.__create_provider_compute_zones(configs)
        self.__create_provider_site_networks(configs)
        self.__create_provider_flavors(configs)
        self.__create_provider_volumeflavors(configs)
        self.__create_provider_images(configs)
        self.__create_provider_customizations(configs)
