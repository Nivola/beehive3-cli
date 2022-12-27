# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from re import match
from urllib.parse import urlencode
from cement import ex
from beecell.password import random_password
from beecell.types.type_dict import dict_get
from beecell.types.type_id import id_gen
from beecell.types.type_string import str2bool
from beehive3_cli.core.controller import ARGS
from beehive3_cli.core.util import load_config
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


class CPaaServiceController(BusinessControllerChild):
    class Meta:
        label = 'cpaas'
        description = "compute service management"
        help = "compute service management"

    @ex(
        help='get compute service info',
        description='get compute service info',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def info(self):
        account = self.app.pargs.account
        account = self.get_account(account).get('uuid')
        data = {'owner-id': account}
        uri = '%s/computeservices' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, 'DescribeComputeResponse.computeSet.0')
        # limits = res.pop('limits')
        self.app.render(res, details=True, maxsize=100)
        # self.output('Limits:')
        # self.app.render(limits, headers=['quota', 'value', 'allocated', 'unit'], maxsize=40)

    @ex(
        help='get compute service quotas',
        description='get compute service quotas',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def quotas(self):
        account = self.app.pargs.account
        account = self.get_account(account).get('uuid')
        data = {'owner-id': account}
        uri = '%s/computeservices/describeaccountattributes' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, 'DescribeAccountAttributesResponse.accountAttributeSet')
        headers = ['name', 'value', 'used']
        fields = ['attributeName', 'attributeValueSet.0.item.attributeValue',
                  'attributeValueSet.0.item.nvl-attributeUsed']
        self.app.render(res, headers=headers, fields=fields)

    @ex(
        help='get compute service availibility zones',
        description='get compute service availibility zones',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def availability_zones(self):
        account = self.app.pargs.account
        account = self.get_account(account).get('uuid')
        data = {'owner-id': account}
        uri = '%s/computeservices/describeavailabilityzones' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, 'DescribeAvailabilityZonesResponse.availabilityZoneInfo')
        headers = ['name', 'state', 'region', 'message']
        fields = ['zoneName', 'zoneState', 'regionName', 'messageSet.0.message']
        self.app.render(res, headers=headers, fields=fields)


class ImageServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'cpaas'
        stacked_type = 'nested'
        label = 'images'
        description = "image service management"
        help = "image service management"

    @ex(
        help='list images',
        description='list images',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-images'], {'help': 'list of image id comma separated', 'action': 'store', 'type': str,
                           'default': None}),
            (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['accounts', 'images']
        mappings = {
            'accounts': self.get_account_ids,
            'tags': lambda x: x.split(','),
            'images': lambda x: x.split(',')
        }
        aliases = {
            'accounts': 'owner-id.N',
            'images': 'image-id.N',
            'tags': 'tag-key.N',
            'size': 'Nvl-MaxResults',
            'page': 'Nvl-NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)

        uri = '%s/computeservices/image/describeimages' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeImagesResponse')
        page = self.app.pargs.page
        resp = {
            'count': len(res.get('imagesSet')),
            'page': page,
            'total': res.get('nvl-imageTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'instances': res.get('imagesSet')
        }

        headers = ['id', 'name', 'state', 'type', 'account', 'platform', 'hypervisor']
        fields = ['imageId', 'name', 'imageState', 'imageType', 'imageOwnerAlias', 'platform', 'hypervisor']
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40)

    @ex(
        help='get image',
        description='get image',
        arguments=ARGS([
            (['image'], {'help': 'image id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        image_id = self.app.pargs.image
        if self.is_uuid(image_id):
            data = {'ImageId.N': [image_id]}
        elif self.is_name(image_id):
            data = {'name.N': [image_id]}

        uri = '%s/computeservices/image/describeimages' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeImagesResponse.imagesSet', default={})
        if len(res) > 0:
            res = res[0]
            if self.is_output_text():
                self.app.render(res, details=True, maxsize=100)
            else:
                self.app.render(res, details=True, maxsize=100)
        else:
            raise Exception('image %s was not found' % image_id)

    @ex(
        help='get image templates',
        description='get image templates',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str, 'default': None}),
            (['-id'], {'help': 'template id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def types(self):
        self.get_service_definitions('ComputeImage')

    @ex(
        help='create an image',
        description='create an image',
        arguments=ARGS([
            (['name'], {'help': 'image name', 'action': 'store', 'type': str}),
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['desc'], {'help': 'image description', 'action': 'store', 'type': str}),
            (['type'], {'help': 'image type', 'action': 'store', 'type': str})
        ])
    )
    def add(self):
        name = self.app.pargs.name
        account = self.get_account(self.app.pargs.account).get('uuid')
        itype = self.get_service_definition(self.app.pargs.type)
        desc = self.app.pargs.desc

        data = {
            'ImageName': name,
            'owner_id': account,
            'ImageDescription': desc,
            'ImageType': itype
        }
        uri = '%s/computeservices/image/createimage' % self.baseuri
        res = self.cmp_post(uri, data={'image': data}, timeout=600)
        res = dict_get(res, 'CreateImageResponse.imageId')
        self.app.render({'msg': 'add image: %s' % res})

    @ex(
        help='delete an image',
        description='delete an image',
        arguments=ARGS([
            (['image'], {'help': 'image id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.image
        data = {
            'force': False,
            'propagate': True
        }
        uri = '/v2.0/nws/serviceinsts/%s' % oid
        self.cmp_delete(uri, data=data, timeout=180, entity='image %s' % oid)


class VolumeServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'cpaas'
        stacked_type = 'nested'
        label = 'volumes'
        description = "volume service management"
        help = "volume service management"

        cmp = {'baseuri': '/v1.0/nws', 'subsystem': 'service'}

    @ex(
        help='load volumes from resources',
        description='load volumes from resources',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-volumes'], {'help': 'list of volume id comma separated', 'action': 'store', 'type': str,
                            'default': None}),
            (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def load(self):
        params = []
        mappings = {
        }
        aliases = {
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)

        self._meta.cmp = {'baseuri': '/v1.0/nrs', 'subsystem': 'resource'}
        uri = '/v1.0/nrs/provider/volumes'
        #res = self.cmp_get(uri, data=data)
        #print(res)

        self._meta.cmp = {'baseuri': '/v1.0/nws', 'subsystem': 'service'}
        uri = '/v2.0/nws/serviceinsts'
        data = {'size': 2, 'plugintype': 'ComputeInstance', 'order': 'asc'}
        res = self.cmp_get(uri, data=data).get('serviceinsts')
        for i in res:
            print(i['id'], i['uuid'], i['name'], i['account']['uuid'], i['account']['name'], i['resource_uuid'],
                  i['date']['creation'])

    @ex(
        help='list volumes',
        description='list volumes',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-volumes'], {'help': 'list of volume id comma separated', 'action': 'store', 'type': str,
                            'default': None}),
            (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['accounts', 'volumes']
        mappings = {
            'accounts': self.get_account_ids,
            'tags': lambda x: x.split(','),
            'volumes': lambda x: x.split(',')
        }
        aliases = {
            'accounts': 'owner-id.N',
            'volumes': 'volume-id.N',
            'tags': 'tag-key.N',
            'size': 'MaxResults',
            'page': 'NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)

        uri = '%s/computeservices/volume/describevolumes' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeVolumesResponse')
        page = self.app.pargs.page
        resp = {
            'count': len(res.get('volumesSet')),
            'page': page,
            'total': res.get('nvl-volumeTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'volumes': res.get('volumesSet')
        }

        headers = ['id', 'name', 'state', 'size', 'type', 'account', 'platform', 'creation', 'instance']
        fields = ['volumeId', 'nvl-name', 'status', 'size', 'volumeType', 'nvl-volumeOwnerAlias', 'nvl-hypervisor',
                  'createTime', 'attachmentSet.0.instanceId']
        self.app.render(resp, key='volumes', headers=headers, fields=fields, maxsize=40)

    @ex(
        help='get volume',
        description='get volume',
        arguments=ARGS([
            (['volume'], {'help': 'volume id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        volume_id = self.app.pargs.volume
        if self.is_uuid(volume_id):
            data = {'VolumeId.N': [volume_id]}
        elif self.is_name(volume_id):
            data = {'Nvl_Name.N': [volume_id]}

        uri = '%s/computeservices/volume/describevolumes' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeVolumesResponse.volumesSet', default={})
        if len(res) > 0:
            res = res[0]
            if self.is_output_text():
                self.app.render(res, details=True, maxsize=100)
            else:
                self.app.render(res, details=True, maxsize=100)
        else:
            raise Exception('volume %s was not found' % volume_id)

    @ex(
        help='get volumes types',
        description='get volumes types',
        arguments=ARGS([
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def types(self):
        params = ['account']
        mappings = {
            'account': lambda x: self.get_account(x)['uuid'],
        }
        aliases = {
            'account': 'owner-id',
            'size': 'MaxResults',
            'page': 'NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '/v2.0/nws/computeservices/volume/describevolumetypes'
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeVolumeTypesResponse')
        page = self.app.pargs.page
        resp = {
            'count': len(res.get('volumeTypesSet')),
            'page': page,
            'total': res.get('volumeTypesTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'types': res.get('volumeTypesSet')
        }
        headers = ['id', 'volume_type', 'desc']
        fields = ['uuid', 'name', 'description']
        self.app.render(resp, key='types', headers=headers, fields=fields)

    @ex(
        help='create a volume',
        description='create a volume',
        arguments=ARGS([
            (['name'], {'help': 'volume name', 'action': 'store', 'type': str}),
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['availability_zone'], {'help': 'volume availability_zone', 'action': 'store', 'type': str}),
            (['type'], {'help': 'volume type', 'action': 'store', 'type': str}),
            (['size'], {'help': 'volume sise', 'action': 'store', 'type': str}),
            (['-iops'], {'help': 'volume iops', 'action': 'store', 'type': int, 'default': -1}),
            (['-snapshot'], {'help': 'volume snapshot', 'action': 'store', 'type': str, 'default': None}),
            (['-hypervisor'], {'help': 'volume hypervisor. Can be: openstack or vsphere [default=openstack]',
                               'action': 'store', 'type': str, 'default': 'openstack'}),
        ])
    )
    def add(self):
        name = self.app.pargs.name
        account = self.get_account(self.app.pargs.account).get('uuid')
        itype = self.get_service_definition(self.app.pargs.type)
        snapshot = self.app.pargs.snapshot
        size = self.app.pargs.size
        iops = self.app.pargs.iops
        zone = self.app.pargs.availability_zone
        hypervisor = self.app.pargs.hypervisor

        data = {
            'Nvl_Name': name,
            'owner-id': account,
            # 'SnapshotId': snapshot,
            'VolumeType': itype,
            'Size': size,
            'Iops': iops,
            'AvailabilityZone': zone,
            'MultiAttachEnabled': False,
            'Encrypted': False,
            'Nvl_Hypervisor': hypervisor
        }
        uri = '%s/computeservices/volume/createvolume' % self.baseuri
        res = self.cmp_post(uri, data={'volume': data}, timeout=600)
        res = dict_get(res, 'CreateVolumeResponse.volumeId')
        self.wait_for_service(res)
        self.app.render({'msg': 'add volume: %s' % res})

    # @ex(
    #     help='update a volume',
    #     description='update a volume',
    #     arguments=ARGS([
    #         (['vm'], {'help': 'volume id', 'action': 'store', 'type': str}),
    #         (['-type'], {'help': 'volume type', 'action': 'store', 'type': str, 'default': None}),
    #     ])
    # )
    # def update(self):
    #     value = self.app.pargs.vm
    #     vmtype = self.app.pargs.type
    #     data = {
    #         'InstanceId': value,
    #         'InstanceType': vmtype,
    #     }
    #     data = {'instance': data}
    #     uri = '%s/computeservices/instance/modifyinstanceattribute' % self.baseuri
    #     res = self.cmp_put(uri, data=data, timeout=600).get('ModifyInstanceAttributeResponse')
    #     self.app.render('update volume %s' % value)

    @ex(
        help='delete a volume',
        description='delete a volume',
        arguments=ARGS([
            (['volume'], {'help': 'volume id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        volume_id = self.app.pargs.volume
        if self.is_name(volume_id):
            raise Exception('only volume id is supported')
        data = {'VolumeId': volume_id}
        uri = '%s/computeservices/volume/deletevolume' % self.baseuri
        self.cmp_delete(uri, data=data, timeout=600, entity='volume %s' % volume_id)
        self.wait_for_service(volume_id, accepted_state='DELETED')

    @ex(
        help='attach a volume to an instance',
        description='attach a volume to an instance',
        arguments=ARGS([
            (['volume'], {'help': 'volume id', 'action': 'store', 'type': str}),
            (['instance'], {'help': 'instance id', 'action': 'store', 'type': str}),
        ])
    )
    def attach(self):
        volume = self.app.pargs.volume
        instance = self.app.pargs.instance
        data = {'InstanceId': instance, 'VolumeId': volume, 'Device': '/dev/sda'}
        uri = '%s/computeservices/volume/attachvolume' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(volume)
        self.app.render({'msg': 'attach volume %s to instance %s' % (volume, instance)})

    @ex(
        help='detach a volume to an instance',
        description='detach a volume to an instance',
        arguments=ARGS([
            (['volume'], {'help': 'volume id', 'action': 'store', 'type': str}),
            (['instance'], {'help': 'instance id', 'action': 'store', 'type': str}),
        ])
    )
    def detach(self):
        volume = self.app.pargs.volume
        instance = self.app.pargs.instance
        data = {'InstanceId': instance, 'VolumeId': volume, 'Device': '/dev/sda'}
        uri = '%s/computeservices/volume/detachvolume' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(volume)
        self.app.render({'msg': 'detach volume %s to instance %s' % (volume, instance)})


class VmServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'cpaas'
        stacked_type = 'nested'
        label = 'vms'
        description = "virtual machine service management"
        help = "virtual machine service management"

        cmp = {'baseuri': '/v2.0/nws', 'subsystem': 'service'}

    @ex(
        help='list all the virtual machines',
        description='list all the virtual machines',
        arguments=ARGS([
        ])
    )
    def list_all(self):
        def get_instance(page):
            data = {
                'MaxResults': 100,
                'NextToken': page
            }
            uri = '%s/computeservices/instance/describeinstances' % self.baseuri
            res = self.cmp_get(uri, data=urlencode(data, doseq=True))
            res = res.get('DescribeInstancesResponse').get('reservationSet')[0]
            total = res.get('nvl-instanceTotal')
            res = res.get('instancesSet')

            for item in res:
                block_devices = item.pop('blockDeviceMapping', [])
                instance_type = item.pop('nvl-InstanceTypeExt', {})
                item['vcpus'] = instance_type.get('vcpus')
                item['memory'] = instance_type.get('memory')
                item['disk'] = sum([dict_get(b, 'ebs.volumeSize') for b in block_devices])
            return res, total

        total = 1628
        max_page = int(round(total/100, 0))+1
        resp = []
        for page in range(0, max_page):
            resp.extend(get_instance(page)[0])
            print('get vm from %s to %s' % (page*100, (page+1)*100))

        headers = ['name', 'type', 'account', 'image', 'fqdn', 'vcpus', 'memory', 'disk']
        fields = ['nvl-name', 'instanceType', 'nvl-ownerAlias', 'nvl-imageName', 'dnsName', 'vcpus', 'memory', 'disk']
        self.app.render(resp, headers=headers, fields=fields)

    @ex(
        help='get virtual machine',
        description='get virtual machine',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-ids'], {'help': 'list of vm id comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'vm name', 'action': 'store', 'type': str, 'default': None}),
            (['-names'], {'help': 'vm name pattern', 'action': 'store', 'type': str, 'default': None}),
            (['-types'], {'help': 'list of type comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-launch_time'], {'help': 'launch time interval. Ex. 2021-01-30T:2021-01-31T', 'action': 'store',
                                'type': str, 'default': None}),
            (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-states'], {'help': 'list of instance state comma separated', 'action': 'store', 'type': str,
                           'default': None}),
            (['-sg'], {'help': 'list of security group id comma separated. Ex. pending, running, error',
                       'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
            (['-services'], {'help': 'print instance service enabling. Ex. backup, monitoring', 'action': 'store_true'}),
        ])
    )
    def list(self):
        services = self.app.pargs.services
        params = ['accounts', 'ids', 'types', 'tags', 'sg', 'name', 'names', 'launch_time', 'states']
        mappings = {
            'accounts': self.get_account_ids,
            'tags': lambda x: x.split(','),
            'types': lambda x: x.split(','),
            'ids': lambda x: x.split(','),
            'name': lambda x: x.split(','),
            'names': lambda x: '%' + x + '%',
            'sg': lambda x: x.split(','),
            'launch_time': lambda x: x.split(','),
            'states': lambda x: x.split(','),
        }
        aliases = {
            'accounts': 'owner-id.N',
            'ids': 'instance-id.N',
            'types': 'instance-type.N',
            'name': 'name.N',
            'names': 'name-pattern',
            'tags': 'tag-key.N',
            'sg': 'instance.group-id.N',
            'launch_time': 'launch-time.N',
            'states': 'instance-state-name.N',
            'size': 'MaxResults',
            'page': 'NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '%s/computeservices/instance/describeinstances' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeInstancesResponse')
        page = self.app.pargs.page
        res = res.get('reservationSet')[0]
        resp = {
            'count': len(res.get('instancesSet')),
            'page': page,
            'total': res.get('nvl-instanceTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'instances': res.get('instancesSet')
        }

        headers = ['id', 'name', 'account', 'type', 'state', 'availabilityZone', 'privateIp', 'image', 'subnet', 'sg',
                   'hypervisor', 'launchTime']
        fields = ['instanceId', 'nvl-name', 'nvl-ownerAlias', 'instanceType', 'instanceState.name',
                  'placement.availabilityZone', 'privateIpAddress', 'nvl-imageName', 'nvl-subnetName',
                  'groupSet.0.groupId', 'hypervisor', 'launchTime']
        if services is True:
            headers = ['id', 'name', 'account', 'state', 'availabilityZone', 'privateIp', 'backup', 'monitoring',
                       'logging']
            fields = ['instanceId', 'nvl-name', 'nvl-ownerAlias', 'instanceState.name', 'placement.availabilityZone',
                      'privateIpAddress', 'nvl-BackupEnabled', 'nvl-MonitoringEnabled', 'nvl-LoggingEnabled']

        transform = {'instanceState.name': self.color_error}
        self.app.render(resp, key='instances', headers=headers, fields=fields, transform=transform, maxsize=40)

    @ex(
        help='get virtual machine',
        description='get virtual machine',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        vm_id = self.app.pargs.vm
        if self.is_uuid(vm_id):
            data = {'instance-id.N': [vm_id]}
        elif self.is_name(vm_id):
            data = {'name.N': [vm_id]}

        uri = '%s/computeservices/instance/describeinstances' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeInstancesResponse.reservationSet.0.instancesSet', default={})
        if len(res) > 0:
            res = res[0]
            if self.is_output_text():
                network = {}
                block_devices = res.pop('blockDeviceMapping', [])
                instance_type = res.pop('nvl-InstanceTypeExt', {})
                image = {'id':  res.pop('imageId', None), 'name': res.pop('nvl-imageName', None)}
                network['ip_address'] = res.pop('privateIpAddress', None)
                network['subnet'] = '%s - %s' % (res.pop('subnetId', None),
                                                 res.pop('nvl-subnetName', None))
                network['vpc'] = '%s - %s' % (res.pop('vpcId', None), res.pop('nvl-vpcName', None))
                network['dns_name'] = res.pop('dnsName', None)
                network['private_dns_name'] = res.pop('privateDnsName', None)
                sgs = res.pop('groupSet', [])
                self.app.render(res, details=True, maxsize=100)
                self.c('\ninstance type', 'underline')
                headers = ['vcpus', 'bandwidth', 'memory', 'disk_iops', 'disk']
                self.app.render(instance_type, headers=headers)
                self.c('\nimage', 'underline')
                self.app.render(image, details=True)
                self.c('\nnetwork', 'underline')
                self.app.render(network, details=True)
                print()
                self.app.render(sgs, headers=['groupId', 'groupName'])
                self.c('\nblock device', 'underline')
                headers = ['deviceName', 'ebs.status', 'ebs.volumeSize', 'ebs.deleteOnTermination',
                           'ebs.volumeId', 'ebs.attachTime']
                self.app.render(block_devices, headers=headers)
            else:
                self.app.render(res, details=True, maxsize=100)
        else:
            raise Exception('virtual machine %s was not found' % vm_id)

    @ex(
        help='get virtual machine console',
        description='get virtual machine console',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
        ])
    )
    def console_get(self):
        vm_id = self.app.pargs.vm
        data = {'InstanceId': vm_id}
        uri = '/v2.0/nws/computeservices/instance/getconsole'
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'GetConsoleResponse.console', default={})
        self.app.render(res, details=True, maxsize=100)

    @ex(
        help='create a virtual machine',
        description='create a virtual machine',
        arguments=ARGS([
            (['name'], {'help': 'virtual machine name', 'action': 'store', 'type': str}),
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['type'], {'help': 'virtual machine type', 'action': 'store', 'type': str}),
            (['subnet'], {'help': 'virtual machine subnet id', 'action': 'store', 'type': str}),
            (['image'], {'help': 'virtual machine image id', 'action': 'store', 'type': str}),
            (['sg'], {'help': 'virtual machine security group id', 'action': 'store', 'type': str}),
            (['-sshkey'], {'help': 'virtual machine ssh key name', 'action': 'store', 'type': str, 'default': None}),
            (['-pwd'], {'help': 'virtual machine admin/root password', 'action': 'store', 'type': str,
                        'default': None}),
            (['-main-disk'], {'help': 'optional main disk size configuration. Use <size> to set e default volume type.'
                                      '- Use <size>:<volume_type> to set a non default volume type. Ex. 5:vol.oracle'
                                      '- Use <volume_id>:<volume_type> to set a volume to clone',
                              'action': 'store', 'type': str, 'default': None}),
            (['-other-disk'], {'help': 'list of additional disk sizes comma separated. Use <size> to set e default '
                                       'volume type.Use <size>:<volume_type> to set a non default volume type. '
                                       'Ex. 5,10 or 5:vol.oracle,10', 'action': 'store', 'type': str, 'default': None}),
            (['-hypervisor'], {'help': 'virtual machine hypervisor. Can be: openstack or vsphere [default=openstack]',
                               'action': 'store', 'type': str, 'default': 'openstack'}),
            (['-host-group'], {'help': 'virtual machine host group. Ex. oracle', 'action': 'store', 'type': str,
                               'default': None}),
            (['-multi-avz'], {'help': 'if set to False create vm to work only in the selected availability zone '
                                      '[default=True]. Use when subnet cidr is public', 'action': 'store', 'type': str,
                              'default': True}),
            (['-meta'], {'help': 'virtual machine custom metadata', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def add(self):
        name = self.app.pargs.name
        account = self.get_account(self.app.pargs.account).get('uuid')
        itype = self.get_service_definition(self.app.pargs.type)
        subnet = self.get_service_instance(self.app.pargs.subnet, account_id=account)
        image = self.get_service_instance(self.app.pargs.image, account_id=account)
        sg = self.get_service_instance(self.app.pargs.sg, account_id=account)
        sshkey = self.app.pargs.sshkey
        pwd = self.app.pargs.pwd
        boot_disk = self.app.pargs.main_disk
        disks = self.app.pargs.other_disk
        hypervisor = self.app.pargs.hypervisor
        host_group = self.app.pargs.host_group
        multi_avz = self.app.pargs.multi_avz
        meta = self.app.pargs.meta

        if pwd is None:
            pwd = random_password(10)

        data = {
            'Name': name,
            'owner-id': account,
            'AdditionalInfo': '',
            'SubnetId': subnet,
            'InstanceType': itype,
            'AdminPassword': pwd,
            'ImageId': image,
            'SecurityGroupId.N': [sg],
            'Nvl_MultiAvz': multi_avz
        }

        # set disks
        blocks = [{'Ebs': {}}]
        if boot_disk is not None:
            boot_disk = boot_disk.split(':')
            # get obj by uuid
            if match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', boot_disk[0]):
                ebs = {'Nvl_VolumeId': boot_disk[0]}
            # get obj by id
            elif match('^\d+$', boot_disk[0]):
                ebs = {'VolumeSize': int(boot_disk[0])}
            if len(boot_disk) == 2:
                ebs['VolumeType'] = boot_disk[1]
            blocks[0] = {'Ebs': ebs}
        if disks is not None:
            for disk in disks.split(','):
                disk = disk.split(':')
                # get obj by uuid
                if match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', disk[0]):
                    ebs = {'Nvl_VolumeId': disk[0]}
                # get obj by id
                elif match('^\d+$', disk[0]):
                    ebs = {'VolumeSize': int(disk[0])}
                if len(disk) == 2:
                    ebs['VolumeType'] = disk[1]
                blocks.append({'Ebs': ebs})
        data['BlockDeviceMapping.N'] = blocks

        # set sshkey
        if sshkey is not None:
            data['KeyName'] = sshkey

        # set hypervisor
        if hypervisor is not None:
            if hypervisor not in ['openstack', 'vsphere']:
                raise Exception('Supported hypervisor are openstack and vsphere')
            data['Nvl_Hypervisor'] = hypervisor

        # set host_group
        if host_group is not None:
            if hypervisor == 'vsphere' and host_group not in ['oracle']:
                raise Exception('Supported vsphere host group are "oracle"')
            if hypervisor == 'openstack' and host_group not in ['bck', 'nobck']:
                raise Exception('Supported openstack host group are "bck" and "nobck"')
            data['Nvl_HostGroup'] = host_group

        # set meta
        if meta is not None:
            data['Nvl_Metadata'] = {}
            kvs = meta.split(',')
            for kv in kvs:
                k, v = kv.split(':')
                data['Nvl_Metadata'][k] = v

        uri = '%s/computeservices/instance/runinstances' % self.baseuri
        res = self.cmp_post(uri, data={'instance': data}, timeout=600)
        uuid = dict_get(res, 'RunInstanceResponse.instancesSet.0.instanceId')
        self.wait_for_service(uuid)
        self.app.render({'msg': 'add virtual machine: %s' % uuid})

    def _get_instance(self, vm_id):
        if self.is_uuid(vm_id):
            data = {'instance-id.N': [vm_id]}
        elif self.is_name(vm_id):
            data = {'name.N': [vm_id]}

        uri = '%s/computeservices/instance/describeinstances' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeInstancesResponse.reservationSet.0.instancesSet', default={})
        if len(res) != 1:
            raise Exception('no valid vm found for id %s' % vm_id)
        return res[0]

    @ex(
        help='clone a virtual machine',
        description='clone a virtual machine',
        arguments=ARGS([
            (['name'], {'help': 'virtual machine name', 'action': 'store', 'type': str}),
            (['id'], {'help': 'id of the virtual machine to clone', 'action': 'store', 'type': str}),
            (['-account'], {'help': 'parent account id', 'action': 'store', 'type': str, 'default': None}),
            (['-type'], {'help': 'virtual machine type', 'action': 'store', 'type': str, 'default': None}),
            (['-subnet'], {'help': 'virtual machine subnet id', 'action': 'store', 'type': str, 'default': None}),
            (['-sg'], {'help': 'virtual machine security group id', 'action': 'store', 'type': str, 'default': None}),
            (['-sshkey'], {'help': 'virtual machine ssh key name', 'action': 'store', 'type': str, 'default': None}),
            (['-pwd'], {'help': 'virtual machine admin/root password', 'action': 'store', 'type': str,
                        'default': None}),
            (['-multi-avz'], {'help': 'if set to False create vm to work only in the selected availability zone '
                                      '[default=True]. Use when subnet cidr is public', 'action': 'store', 'type': str,
                              'default': True}),
            (['-meta'], {'help': 'virtual machine custom metadata', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def clone(self):
        name = self.app.pargs.name
        vm_id = self.app.pargs.id
        account = self.app.pargs.account
        itype = self.app.pargs.type
        subnet = self.app.pargs.subnet
        sg = self.app.pargs.sg
        sshkey = self.app.pargs.sshkey
        pwd = self.app.pargs.pwd
        multi_avz = self.app.pargs.multi_avz
        meta = self.app.pargs.meta

        # get original vm
        vm = self._get_instance(vm_id)

        image_name = dict_get(vm, 'nvl-imageName')
        hypervisor = dict_get(vm, 'hypervisor')
        if account is None:
            account = dict_get(vm, 'nvl-ownerId')
        else:
            account = self.get_account(self.app.pargs.account).get('uuid')

        image = self.get_service_instance(image_name, account_id=account)
        if itype is None:
            itype = dict_get(vm, 'instanceType')
        itype = self.get_service_definition(itype)
        if subnet is None:
            subnet = dict_get(vm, 'subnetId')
        else:
            subnet = self.get_service_instance(subnet, account_id=account)
        if sg is None:
            sg = dict_get(vm, 'groupSet.0.groupId')
        else:
            sg = self.get_service_instance(sg, account_id=account)
        if sshkey is None:
            sshkey = dict_get(vm, 'keyName')

        if pwd is None:
            pwd = random_password(10)

        # set disks
        blocks = []
        for disk in vm.get('blockDeviceMapping', []):
            block = {
                'Nvl_VolumeId': dict_get(disk, 'ebs.volumeId'),
                'VolumeSize': dict_get(disk, 'ebs.volumeSize'),
            }
            blocks.append({'Ebs': block})

        data = {
            'Name': name,
            'owner-id': account,
            'AdditionalInfo': '',
            'SubnetId': subnet,
            'InstanceType': itype,
            'AdminPassword': pwd,
            'ImageId': image,
            'SecurityGroupId.N': [sg],
            'Nvl_MultiAvz': multi_avz,
            'Nvl_Hypervisor': hypervisor,
            'BlockDeviceMapping.N': blocks,
            'KeyName': sshkey
        }

        # set meta
        if meta is not None:
            data['Nvl_Metadata'] = {}
            kvs = meta.split(',')
            for kv in kvs:
                k, v = kv.split(':')
                data['Nvl_Metadata'][k] = v

        uri = '%s/computeservices/instance/runinstances' % self.baseuri
        res = self.cmp_post(uri, data={'instance': data}, timeout=600)
        uuid = dict_get(res, 'RunInstanceResponse.instancesSet.0.instanceId')
        self.wait_for_service(uuid)
        self.app.render({'msg': 'add virtual machine: %s' % uuid})

    @ex(
        help='import a virtual machine',
        description='import a virtual machine',
        arguments=ARGS([
            (['container'], {'help': 'container id where import virtual machine', 'action': 'store', 'type': str}),
            (['name'], {'help': 'virtual machine name', 'action': 'store', 'type': str}),
            (['vm'], {'help': 'physical id of the virtual machine to import', 'action': 'store', 'type': str}),
            (['image'], {'help': 'provider image id', 'action': 'store', 'type': str}),
            (['pwd'], {'help': 'virtual machine password', 'action': 'store', 'type': str}),
            (['-sshkey'], {'help': 'virtual machine ssh key name', 'action': 'store', 'type': str, 'default': None}),
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str, 'default': None}),


            # (['-type'], {'help': 'virtual machine type', 'action': 'store', 'type': str, 'default': None}),
            # (['-subnet'], {'help': 'virtual machine subnet id', 'action': 'store', 'type': str, 'default': None}),
            # (['-sg'], {'help': 'virtual machine security group id', 'action': 'store', 'type': str, 'default': None}),
            #
            # (['-pwd'], {'help': 'virtual machine admin/root password', 'action': 'store', 'type': str,
            #             'default': None}),
            # (['-multi-avz'], {'help': 'if set to False create vm to work only in the selected availability zone '
            #                           '[default=True]. Use when subnet cidr is public', 'action': 'store', 'type': str,
            #                   'default': True}),
            # (['-meta'], {'help': 'virtual machine custom metadata', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def load(self):
        container_id = self.app.pargs.container
        name = self.app.pargs.name
        ext_id = self.app.pargs.vm
        image_id = self.app.pargs.image
        pwd = self.app.pargs.pwd
        sshkey = self.app.pargs.sshkey
        account_id = self.get_account(self.app.pargs.account).get('uuid')

        # register server as resource
        # - get container type
        container = self.api.resource.container.get(container_id).get('resourcecontainer')
        ctype = dict_get(container, '__meta__.definition')

        # - synchronize container
        resclasses = {
            'Openstack': 'Openstack.Domain.Project.Server',
            'Vsphere': 'Vsphere.DataCenter.Folder.Server'
        }
        resclass = resclasses.get(ctype, None)
        if resclass is not None:
            print('importing physical entity %s as resource...' % resclass)
            self.api.resource.container.synchronize(container_id, resclass, new=True, died=False, changed=False,
                                                    ext_id=ext_id)
            print('imported physical entity %s as resource' % resclass)

        resclasses = {
            'Openstack': 'Openstack.Domain.Project.Volume',
            'Vsphere': None
        }
        resclass = resclasses.get(ctype, None)
        if resclass is not None:
            print('importing physical entity %s as resource...' % resclass)
            self.api.resource.container.synchronize(container_id, resclass, new=True, died=False, changed=False)
            print('imported physical entity %s as resource' % resclass)

        # import physical resource ad provider resource
        # - get resource by ext_id
        physical_resource = self.api.resource.entity.list(ext_id=ext_id).get('resources')[0]['uuid']

        # - patch resource
        print('patch resource %s' % physical_resource)
        self.api.resource.entity.patch(physical_resource)

        # - import physical resource as provider resource
        res_name = '%s-%s' % (name, id_gen())
        print('load resource instance res_name: %s' % res_name)
        self.api.resource.provider.instance.load('ResourceProvider01', res_name, physical_resource, pwd, image_id,
                                                 hostname=name)
        resource = res_name

        # res_name = 'adsspwd-47ef1b776f'

        # - get resource
        res = self.api.resource.provider.instance.get(res_name)
        flavor = dict_get(res, 'flavor.name')
        resource_uuid = res['uuid']

        #print('import physical resource %s as provider resource %s' % (physical_resource, resource))

        # import provider resource as compute instance
        # - get compute service
        # res = self.api.business.service.instance.list(account_id=account_id, flag_container=True,
        #                                               plugintype='ComputeService')
        # cs = res.get('serviceinsts')[0]['uuid']

        # - import service instance
        print('load service instance res_name: %s' % res_name)
        res = self.api.business.service.instance.load(name, account_id, 'ComputeInstance', 'ComputeService',
                                                      resource_uuid, service_definition_id=flavor)
        print('import provider resource as compute instance %s' % res)

    @ex(
        help='update a virtual machine',
        description='update a virtual machine',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['-type'], {'help': 'virtual machine type', 'action': 'store', 'type': str, 'default': None}),
            (['-sg_add'], {'help': 'virtual machine security group id to add', 'action': 'store', 'type': str,
                           'default': None}),
            (['-sg_del'], {'help': 'virtual machine security group id to remove', 'action': 'store', 'type': str,
                           'default': None}),
        ])
    )
    def update(self):
        uuid = self.app.pargs.vm
        vmtype = self.app.pargs.type
        sg_add = self.app.pargs.sg_add
        sg_del = self.app.pargs.sg_del
        sg = None
        data = {
            'InstanceId': uuid,
            'InstanceType': vmtype
        }
        if sg_add is not None:
            sg = '%s:ADD' % sg_add
            data['GroupId.N'] = [sg]
        elif sg_del is not None:
            sg = '%s:DEL' % sg_del
            data['GroupId.N'] = [sg]
        data = {'instance': data}
        uri = '%s/computeservices/instance/modifyinstanceattribute' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600).get('ModifyInstanceAttributeResponse')
        self.wait_for_service(uuid)
        self.app.render({'msg': 'update virtual machine: %s' % uuid})

    @ex(
        help='refresh virtual machine state',
        description='refresh virtual machine state',
        arguments=ARGS([
            (['id'], {'help': 'virtual machine id, uuid or name', 'action': 'store', 'type': str}),
        ])
    )
    def refresh_state(self):
        oid = self.app.pargs.id
        res = self.api.business.cpaas.instance.get(oid)
        resource_uuid = res.get('nvl-resourceId')
        res = self.api.resource.provider.instance.del_cache(resource_uuid)
        print('state refreshed for virtual machine %s' % oid)

    @ex(
        help='delete a virtual machine',
        description='delete a virtual machine',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        vm_id = self.app.pargs.vm
        if self.is_uuid(vm_id):
            data = {'instance-id.N': [vm_id]}
        elif self.is_name(vm_id):
            data = {'name.N': [vm_id]}
        uri = '%s/computeservices/instance/describeinstances' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeInstancesResponse.reservationSet.0.instancesSet')
        if len(res) == 0:
            raise Exception('virtual machine %s was not found' % vm_id)
        uuid = res[0].get('instanceId')

        data = {'InstanceId.N': [uuid]}
        uri = '%s/computeservices/instance/terminateinstances' % self.baseuri
        self.cmp_delete(uri, data=data, timeout=600, output=False, entity='instance %s' % vm_id)
        self.wait_for_service(uuid, accepted_state='DELETED')

    @ex(
        help='start a virtual machine',
        description='start a virtual machine',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['-schedule'], {'help': 'schedule definition. Pass as json file using crontab or timedelta syntax. '
                                     'Ex. {\"type\": \"timedelta\", \"minutes\": 1}',
                             'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def start(self):
        vm_id = self.app.pargs.vm
        schedule = self.app.pargs.schedule
        data = {'InstanceId.N': [vm_id]}
        if schedule is not None:
            schedule = load_config(schedule)
            data['Schedule'] = schedule
        uri = '%s/computeservices/instance/startinstances' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({'msg': 'start virtual machine %s' % vm_id})

    @ex(
        help='stop a virtual machine',
        description='stop a virtual machine',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['-schedule'], {'help': 'schedule definition. Pass as json file using crontab or timedelta syntax. '
                                     'Ex. {\"type\": \"timedelta\", \"minutes\": 1}',
                             'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def stop(self):
        vm_id = self.app.pargs.vm
        schedule = self.app.pargs.schedule
        data = {'InstanceId.N': [vm_id]}
        if schedule is not None:
            schedule = load_config(schedule)
            data['Schedule'] = schedule
        uri = '%s/computeservices/instance/stopinstances' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({'msg': 'stop virtual machine %s' % vm_id})

    @ex(
        help='reboot a virtual machine',
        description='reboot a virtual machine',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['-schedule'], {'help': 'schedule definition. Pass as json file using crontab or timedelta syntax. '
                                     'Ex. {\"type\": \"timedelta\", \"minutes\": 1}',
                             'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def reboot(self):
        vm_id = self.app.pargs.vm
        schedule = self.app.pargs.schedule
        data = {'InstanceId.N': [vm_id]}
        if schedule is not None:
            schedule = load_config(schedule)
            data['Schedule'] = schedule
        uri = '%s/computeservices/instance/rebootinstances' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({'msg': 'reboot virtual machine %s' % vm_id})

    @ex(
        help='enable virtual machine monitoring',
        description='enable virtual machine monitoring',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['-templates'], {'help': 'templates list', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def enable_monitoring(self):
        vm_id = self.app.pargs.vm
        templates = self.app.pargs.templates
        data = {'InstanceId.N': [vm_id], 'Nvl_Templates': templates}
        uri = '%s/computeservices/instance/monitorinstances' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({'msg': 'enable virtual machine %s monitoring' % vm_id})

    @ex(
        help='disable virtual machine monitoring',
        description='disable virtual machine monitoring',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
        ])
    )
    def disable_monitoring(self):
        vm_id = self.app.pargs.vm
        data = {'InstanceId.N': [vm_id]}
        uri = '%s/computeservices/instance/unmonitorinstances' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({'msg': 'disable virtual machine %s monitoring' % vm_id})

    @ex(
        help='enable virtual machine logging',
        description='enable virtual machine logging',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['-files'], {'help': 'files list', 'action': 'store', 'type': str, 'default': None}),
            (['-pipeline'], {'help': 'log collector pipeline port', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def enable_logging(self):
        vm_id = self.app.pargs.vm
        files = self.app.pargs.files
        pipeline = self.app.pargs.pipeline
        data = {'InstanceId.N': [vm_id], 'Files': files, 'Pipeline': pipeline}
        uri = '%s/computeservices/instance/forwardloginstances' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({'msg': 'enable virtual machine %s logging' % vm_id})

    @ex(
        help='list virtual machine snapshots',
        description='list virtual machine snapshots',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
        ])
    )
    def snapshot_get(self):
        vm_id = self.app.pargs.vm
        data = {'InstanceId.N': [vm_id]}
        uri = '%s/computeservices/instance/describeinstancesnapshots' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True), timeout=600)
        res = res.get('DescribeInstanceSnapshotsResponse')
        res = res.get('instancesSet')
        resp = []
        for item in res:
            for snapshot in item['snapshots']:
                snapshot['id'] = item['instanceId']
                resp.append(snapshot)
        headers = ['id', 'name', 'status', 'creation_date']
        fields = ['snapshotId', 'snapshotName', 'snapshotStatus', 'createTime']
        self.app.render(resp, headers=headers, fields=fields, maxsize=40)

    @ex(
        help='add virtual machine snapshot',
        description='add virtual machine snapshot',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['snapshot'], {'help': 'snapshot name', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def snapshot_add(self):
        vm_id = self.app.pargs.vm
        snapshot = self.app.pargs.snapshot
        data = {'InstanceId.N': [vm_id], 'SnapshotName': snapshot}
        uri = '%s/computeservices/instance/createinstancesnapshots' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({'msg': 'add virtual machine %s snapshot %s' % (vm_id, snapshot)})

    @ex(
        help='add virtual machine snapshot',
        description='add virtual machine snapshot',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['snapshot'], {'help': 'snapshot id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def snapshot_del(self):
        vm_id = self.app.pargs.vm
        snapshot = self.app.pargs.snapshot
        data = {'InstanceId.N': [vm_id], 'SnapshotId': snapshot}
        uri = '%s/computeservices/instance/deleteinstancesnapshots' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({'msg': 'delete virtual machine %s snapshot %s' % (vm_id, snapshot)})

    @ex(
        help='revert virtual machine snapshot',
        description='revert virtual machine snapshot',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['snapshot'], {'help': 'snapshot id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def snapshot_revert(self):
        vm_id = self.app.pargs.vm
        snapshot = self.app.pargs.snapshot
        data = {'InstanceId.N': [vm_id], 'SnapshotId': snapshot}
        uri = '%s/computeservices/instance/revertinstancesnapshots' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600)
        self.wait_for_service(vm_id)
        self.app.render({'msg': 'revert virtual machine %s to snapshot %s' % (vm_id, snapshot)})

    def __user_action(self, uuid, action, **user_params):
        params = {'Nvl_Action': action}
        params.update(user_params)
        data = {
            'InstanceId': uuid,
            'Nvl_User': params
        }
        data = {'instance': data}
        uri = '%s/computeservices/instance/modifyinstanceattribute' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600).get('ModifyInstanceAttributeResponse')
        self.wait_for_service(uuid)
        self.app.render({'msg': 'update virtual machine: %s' % uuid})

    @ex(
        help='add virtual machine user',
        description='add virtual machine user',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['name'], {'help': 'user name', 'action': 'store', 'type': str, 'default': None}),
            (['pwd'], {'help': 'user password', 'action': 'store', 'type': str, 'default': None}),
            (['key'], {'help': 'ssh key id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def user_add(self):
        uuid = self.app.pargs.vm
        name = self.app.pargs.name
        pwd = self.app.pargs.pwd
        key = self.app.pargs.key
        self.__user_action(uuid, 'add', Nvl_Name=name, Nvl_Password=pwd, Nvl_SshKey=key)

    @ex(
        help='delete virtual machine user',
        description='delete virtual machine user',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['name'], {'help': 'user name', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def user_del(self):
        uuid = self.app.pargs.vm
        name = self.app.pargs.name
        self.__user_action(uuid, 'delete', Nvl_Name=name)

    @ex(
        help='set virtual machine user password',
        description='set virtual machine user password',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['name'], {'help': 'user name', 'action': 'store', 'type': str, 'default': None}),
            (['pwd'], {'help': 'user password', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def user_password_set(self):
        uuid = self.app.pargs.vm
        name = self.app.pargs.name
        pwd = self.app.pargs.pwd
        self.__user_action(uuid, 'set-password', Nvl_Name=name, Nvl_Password=pwd)

    @ex(
        help='get virtual machine types',
        description='get virtual machine types',
        arguments=ARGS([
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def types(self):
        params = ['account']
        mappings = {
            'account': lambda x: self.get_account(x)['uuid'],
        }
        aliases = {
            'account': 'owner-id',
            'size': 'MaxResults',
            'page': 'NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '/v2.0/nws/computeservices/instance/describeinstancetypes'
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeInstanceTypesResponse')
        page = self.app.pargs.page
        resp = {
            'count': len(res.get('instanceTypesSet')),
            'page': page,
            'total': res.get('instanceTypesTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'types': res.get('instanceTypesSet')
        }
        headers = ['id', 'instance_type', 'desc', 'vcpus', 'disk', 'ram']
        fields = ['uuid', 'name', 'description', 'features.vcpus', 'features.disk', 'features.ram']
        self.app.render(resp, key='types', headers=headers, fields=fields)

    @ex(
        help='get backup job restore points',
        description='get backup job restore points',
        arguments=ARGS([
            (['account'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['-vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str, 'default': None}),
            (['-job'], {'help': 'job id', 'action': 'store', 'type': str, 'default': None}),
            (['-restore_point'], {'help': 'restore point id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def backup_restore_point_get(self):
        params = ['account', 'vm', 'job', 'restore_point']
        mappings = {
            'account': lambda x: self.get_account(x)['uuid'],
        }
        aliases = {
            'account': 'owner-id',
            'vm': 'InstanceId',
            'job': 'JobId',
            'restore_point': 'RestorePointId'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '/v1.0/nws/computeservices/instancebackup/describebackuprestorepoints'
        res = self.cmp_get(uri, data=data, timeout=600)
        if self.is_output_text():
            restore_points = dict_get(res, 'DescribeBackupRestorePointsResponse.restorePointSet')
            if self.app.pargs.restore_point is not None:
                if len(restore_points) > 0:
                    res = restore_points[0]
                    metadata = res.pop('metadata', [])
                    instances = res.pop('instanceSet', [])
                    self.app.render(res, details=True)

                    self.c('\ninstanceSet', 'underline')
                    self.app.render(instances, fields=['uuid', 'name'], headers=['id', 'name'])
            else:
                self.app.render(restore_points, headers=['id', 'name', 'desc', 'type', 'status', 'created'])
        else:
            self.app.render(res, details=True)

    @ex(
        help='add backup job restore point',
        description='add backup job restore point',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
            (['job'], {'help': 'job id', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'restore point name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'restore point description', 'action': 'store', 'type': str, 'default': None}),
            (['-full'], {'help': 'backup type. If true make a full backup otherwise make an incremental backup',
                         'action': 'store', 'type': str, 'default': 'false'}),
        ])
    )
    def backup_restore_point_add(self):
        account = self.get_account(self.app.pargs.account).get('uuid')
        job_id = self.app.pargs.job
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        full = str2bool(self.app.pargs.full)

        data = {
            'owner-id': account,
            'JobId': job_id,
            'Name': name,
            'Desc': desc if desc is not None else name,
            'BackupFull': full
        }

        uri = '/v1.0/nws/computeservices/instancebackup/createbackuprestorepoints'
        res = self.cmp_post(uri, data=data, timeout=600)
        # uuid = dict_get(res, 'CreateBackupRestorePoints.instanceBackupSet.0.instanceId')
        # self.wait_for_service(uuid)
        self.app.render({'msg': 'create new backup job %s restore point' % job_id})

    @ex(
        help='delete backup job restore point',
        description='delete backup job restore point',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
            (['job'], {'help': 'job id', 'action': 'store', 'type': str, 'default': None}),
            (['restore_point'], {'help': 'restore point id', 'action': 'store', 'type': str}),
        ])
    )
    def backup_restore_point_del(self):
        account = self.get_account(self.app.pargs.account).get('uuid')
        job_id = self.app.pargs.job
        restore_point_id = self.app.pargs.restore_point

        data = {
            'owner-id': account,
            'JobId': job_id,
            'RestorePointId': restore_point_id
        }

        uri = '/v1.0/nws/computeservices/instancebackup/deletebackuprestorepoints'
        res = self.cmp_delete(uri, data=data, timeout=600,
                              entity='remove backup job %s restore point %s' % (job_id, restore_point_id))
        # uuid = dict_get(res, vm_id)
        # self.wait_for_service(uuid)

    @ex(
        help='get virtual machine backup restores',
        description='get virtual machine backup restores',
        arguments=ARGS([
            (['vm'], {'help': 'virtual machine id', 'action': 'store', 'type': str}),
            (['restore_point'], {'help': 'restore point id', 'action': 'store', 'type': str}),
        ])
    )
    def backup_restore_get(self):
        vm_id = self.app.pargs.vm
        restore_point_id = self.app.pargs.restore_point
        data = {'InstanceId.N': [vm_id], 'RestorePoint': restore_point_id}
        uri = '/v1.0/nws/computeservices/instancebackup/describebackuprestores'
        res = self.cmp_get(uri, data=urlencode(data, doseq=True), timeout=600)
        res = dict_get(res, 'DescribeBackupRestoresResponse.restoreSet')
        if len(res) > 0:
            res = res[0]['restores']
            headers = ['id', 'name', 'desc', 'time_taken', 'size', 'uploaded_size', 'status', 'progress_percent',
                       'created']
            self.app.render(res, headers=headers)

    @ex(
        help='restore a virtual machine from backup',
        description='restore a virtual machine from backup',
        arguments=ARGS([
            (['name'], {'help': 'restored virtual machine name', 'action': 'store', 'type': str}),
            (['id'], {'help': 'id of the virtual machine to clone', 'action': 'store', 'type': str}),
            (['restore_point'], {'help': 'id of restore point', 'action': 'store', 'type': str}),
            # (['name'], {'help': 'virtual machine name', 'action': 'store', 'type': str}),
            # (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            # (['type'], {'help': 'virtual machine type', 'action': 'store', 'type': str}),
            # (['subnet'], {'help': 'virtual machine subnet id', 'action': 'store', 'type': str}),
            # (['image'], {'help': 'virtual machine image id', 'action': 'store', 'type': str}),
            # (['sg'], {'help': 'virtual machine security group id', 'action': 'store', 'type': str}),
            # (['-sshkey'], {'help': 'virtual machine ssh key name', 'action': 'store', 'type': str, 'default': None}),
            # (['-pwd'], {'help': 'virtual machine admin/root password', 'action': 'store', 'type': str,
            #             'default': None}),
            # (['-main-disk'], {'help': 'optional main disk size configuration. Use <size> to set e default volume type.'
            #                           '- Use <size>:<volume_type> to set a non default volume type. Ex. 5:vol.oracle'
            #                           '- Use <volume_id>:<volume_type> to set a volume to clone',
            #                   'action': 'store', 'type': str, 'default': None}),
            # (['-other-disk'], {'help': 'list of additional disk sizes comma separated. Use <size> to set e default '
            #                            'volume type.Use <size>:<volume_type> to set a non default volume type. '
            #                            'Ex. 5,10 or 5:vol.oracle,10', 'action': 'store', 'type': str, 'default': None}),
            # (['-hypervisor'], {'help': 'virtual machine hypervisor. Can be: openstack or vsphere [default=openstack]',
            #                    'action': 'store', 'type': str, 'default': 'openstack'}),
            # (['-host-group'], {'help': 'virtual machine host group. Ex. oracle', 'action': 'store', 'type': str,
            #                    'default': None}),
            # (['-multi-avz'], {'help': 'if set to False create vm to work only in the selected availability zone '
            #                           '[default=True]. Use when subnet cidr is public', 'action': 'store', 'type': str,
            #                   'default': True}),
            # (['-meta'], {'help': 'virtual machine custom metadata', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def backup_restore_add(self):
        name = self.app.pargs.name
        vm_id = self.app.pargs.id
        restore_point_id = self.app.pargs.restore_point

        # name = self.app.pargs.name
        # account = self.get_account(self.app.pargs.account).get('uuid')
        # itype = self.get_service_definition(self.app.pargs.type)
        # subnet = self.get_service_instance(self.app.pargs.subnet, account_id=account)
        # image = self.get_service_instance(self.app.pargs.image, account_id=account)
        # sg = self.get_service_instance(self.app.pargs.sg, account_id=account)
        # sshkey = self.app.pargs.sshkey
        # pwd = self.app.pargs.pwd
        # boot_disk = self.app.pargs.main_disk
        # disks = self.app.pargs.other_disk
        # hypervisor = self.app.pargs.hypervisor
        # host_group = self.app.pargs.host_group
        # multi_avz = self.app.pargs.multi_avz
        # meta = self.app.pargs.meta

        # if pwd is None:
        #     pwd = random_password(10)
        #
        # data = {
        #     'Name': name,
        #     'owner-id': account,
        #     'AdditionalInfo': '',
        #     'SubnetId': subnet,
        #     'InstanceType': itype,
        #     'AdminPassword': pwd,
        #     'ImageId': image,
        #     'SecurityGroupId.N': [sg],
        #     'Nvl_MultiAvz': multi_avz
        # }
        #
        # # set disks
        # blocks = [{'Ebs': {}}]
        # if boot_disk is not None:
        #     boot_disk = boot_disk.split(':')
        #     # get obj by uuid
        #     if match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', boot_disk[0]):
        #         ebs = {'Nvl_VolumeId': boot_disk[0]}
        #     # get obj by id
        #     elif match('^\d+$', boot_disk[0]):
        #         ebs = {'VolumeSize': int(boot_disk[0])}
        #     if len(boot_disk) == 2:
        #         ebs['VolumeType'] = boot_disk[1]
        #     blocks[0] = {'Ebs': ebs}
        # if disks is not None:
        #     for disk in disks.split(','):
        #         disk = disk.split(':')
        #         # get obj by uuid
        #         if match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', disk[0]):
        #             ebs = {'Nvl_VolumeId': disk[0]}
        #         # get obj by id
        #         elif match('^\d+$', disk[0]):
        #             ebs = {'VolumeSize': int(disk[0])}
        #         if len(disk) == 2:
        #             ebs['VolumeType'] = disk[1]
        #         blocks.append({'Ebs': ebs})
        # data['BlockDeviceMapping.N'] = blocks
        #
        # # set sshkey
        # if sshkey is not None:
        #     data['KeyName'] = sshkey
        #
        # # set hypervisor
        # if hypervisor is not None:
        #     if hypervisor not in ['openstack', 'vsphere']:
        #         raise Exception('Supported hypervisor are openstack and vsphere')
        #     data['Nvl_Hypervisor'] = hypervisor
        #
        # # set host_group
        # if host_group is not None:
        #     if host_group not in ['oracle']:
        #         raise Exception('Supported host group are oracle')
        #     data['Nvl_HostGroup'] = host_group
        #
        # # set meta
        # if meta is not None:
        #     data['Nvl_Metadata'] = {}
        #     kvs = meta.split(',')
        #     for kv in kvs:
        #         k, v = kv.split(':')
        #         data['Nvl_Metadata'][k] = v

        data = {
            'InstanceId': vm_id,
            'RestorePointId': restore_point_id,
            'InstanceName': name,
        }

        uri = '/v1.0/nws/computeservices/instancebackup/createbackuprestores'
        res = self.cmp_post(uri, data={'instance': data}, timeout=600)
        uuid = dict_get(res, 'CreateBackupRestoreResponse.instancesSet.0.instanceId')
        self.wait_for_service(uuid)
        self.app.render({'msg': 'restore virtual machine from backup: %s' % uuid})

    @ex(
        help='get account virtual machine backup jobs',
        description='get account virtual machine backup jobs',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def backup_job_list(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get('uuid')
        data = {'owner-id.N': [account_id]}
        uri = '/v1.0/nws/computeservices/instancebackup/describebackupjobs'
        res = self.cmp_get(uri, data=urlencode(data, doseq=True), timeout=600)
        res = dict_get(res, 'DescribeBackupJobsResponse.jobSet')
        headers = ['id', 'name', 'account', 'hypervisor', 'availabilityZone', 'state', 'enabled', 'instances']
        fields = ['jobId', 'name', 'owner_id', 'hypervisor', 'availabilityZone', 'jobState', 'enabled', 'instanceNum']
        self.app.render(res, headers=headers, fields=fields)

    @ex(
        help='get account virtual machine backup job',
        description='get account virtual machine backup job',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
            (['job'], {'help': 'job id', 'action': 'store', 'type': str}),
        ])
    )
    def backup_job_get(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get('uuid')
        job_id = self.app.pargs.job
        data = {'owner-id.N': [account_id], 'JobId': job_id}
        uri = '/v1.0/nws/computeservices/instancebackup/describebackupjobs'
        res = self.cmp_get(uri, data=urlencode(data, doseq=True), timeout=600)
        res = dict_get(res, 'DescribeBackupJobsResponse.jobSet.0')
        instances = res.pop('instanceSet', [])
        self.app.render(res, details=True)
        self.c('\ninstances', 'underline')
        self.app.render(instances, headers=['uuid', 'name'])

    @ex(
        help='add account virtual machine backup job',
        description='add account virtual machine backup job',
        arguments=ARGS([
            (['name'], {'help': 'job name', 'action': 'store', 'type': str}),
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
            (['zone'], {'help': 'job availability zone', 'action': 'store', 'type': str}),
            (['instance'], {'help': 'comma separated list of instance id to add', 'action': 'store', 'type': str}),
            (['-hypervisor'], {'help': 'job hypervisor [openstack]', 'action': 'store', 'type': str,
                               'default': 'openstack'}),
            (['-policy'], {'help': 'job hypervisor [bk-job-policy-7-7-retention]', 'action': 'store', 'type': str,
                           'default': 'bk-job-policy-7-7-retention'}),
            (['-desc'], {'help': 'job description', 'action': 'store', 'type': str}),
        ])
    )
    def backup_job_add(self):
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        account = self.app.pargs.account
        account_id = self.get_account(account).get('uuid')
        zone = self.app.pargs.zone
        instance = self.app.pargs.instance
        policy = self.app.pargs.policy
        hypervisor = self.app.pargs.hypervisor

        data = {
            'owner-id': account_id,
            'InstanceId.N': instance.split(','),
            'Name': name,
            'Desc': desc,
            'AvailabilityZone': zone,
            'Policy': policy,
            'Hypervisor': hypervisor
        }
        uri = '/v1.0/nws/computeservices/instancebackup/createbackupjob'
        res = self.cmp_post(uri, data=data, timeout=600)
        res = dict_get(res, 'CreateBackupJob.jobsSet.0.jobId')
        self.app.render({'msg': 'add backup job %s' % res}, details=True)

    @ex(
        help='update account virtual machine backup job',
        description='update account virtual machine backup job',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
            (['job'], {'help': 'job id', 'action': 'store', 'type': str}),
            (['-name'], {'help': 'job name', 'action': 'store', 'type': str, 'default': None}),
            (['-enabled'], {'help': 'enable or disable job', 'action': 'store', 'type': str, 'default': None}),
            (['-policy'], {'help': 'job policy ', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def backup_job_update(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get('uuid')
        job_id = self.app.pargs.job
        data = {
            'owner-id': account_id,
            'JobId': job_id
        }
        data = self.add_field_from_pargs_to_data('name', data, 'Name', reject_value=None, format=None)
        data = self.add_field_from_pargs_to_data('enabled', data, 'Enabled', reject_value=None, format=None)
        data = self.add_field_from_pargs_to_data('policy', data, 'Policy', reject_value=None, format=str2bool)
        uri = '/v1.0/nws/computeservices/instancebackup/modifybackupjob'
        res = self.cmp_put(uri, data=data, timeout=600)
        res = dict_get(res, 'ModifyBackupJob.jobsSet.0.jobId')
        self.app.render({'msg': 'update backup job %s' % res}, details=True)

    @ex(
        help='delete account virtual machine backup job',
        description='delete account virtual machine backup job',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
            (['job'], {'help': 'job id', 'action': 'store', 'type': str}),
        ])
    )
    def backup_job_del(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get('uuid')
        job_id = self.app.pargs.job
        data = {
            'owner-id': account_id,
            'JobId': job_id
        }
        uri = '/v1.0/nws/computeservices/instancebackup/deletebackupjob'
        res = self.cmp_delete(uri, data=data, timeout=600, entity='delete backup job %s' % job_id)

    @ex(
        help='add virtual machine to backup job',
        description='add virtual machine to backup job',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
            (['job'], {'help': 'job id', 'action': 'store', 'type': str}),
            (['instance'], {'help': 'instance id to add', 'action': 'store', 'type': str}),
        ])
    )
    def backup_job_instance_add(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get('uuid')
        job_id = self.app.pargs.job
        instance = self.app.pargs.instance
        data = {
            'owner-id': account_id,
            'InstanceId': instance,
            'JobId': job_id,
        }
        uri = '/v1.0/nws/computeservices/instancebackup/addbackupjobinstance'
        res = self.cmp_post(uri, data=data, timeout=600)
        res = dict_get(res, 'AddBackupJobInstance.jobsSet.0.jobId')
        self.app.render({'msg': 'add virtual machine %s to backup job %s' % (instance, job_id)}, details=True)

    @ex(
        help='delete virtual machine from backup job',
        description='delete virtual machine from backup job',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
            (['job'], {'help': 'job id', 'action': 'store', 'type': str}),
            (['instance'], {'help': 'instance id to add', 'action': 'store', 'type': str}),
        ])
    )
    def backup_job_instance_del(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get('uuid')
        job_id = self.app.pargs.job
        instance = self.app.pargs.instance
        data = {
            'owner-id': account_id,
            'InstanceId': instance,
            'JobId': job_id,
        }
        uri = '/v1.0/nws/computeservices/instancebackup/delbackupjobinstance'
        res = self.cmp_delete(uri, data=data, timeout=600,
                              entity='virtual machine %s from backup job %s' % (instance, job_id))
        res = dict_get(res, 'DelBackupJobInstance.jobsSet.0.jobId')

    @ex(
        help='get account virtual machine backup job policies',
        description='get account virtual machine backup policies',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def backup_job_policies(self):
        account = self.app.pargs.account
        account_id = self.get_account(account).get('uuid')
        data = {'owner-id': account_id}
        uri = '/v1.0/nws/computeservices/instancebackup/describebackupjobpolicies'
        res = self.cmp_get(uri, data=urlencode(data, doseq=True), timeout=600)
        res = dict_get(res, 'DescribeBackupJobPoliciesResponse.jobPoliciesSet')
        headers = ['id', 'uuid', 'name', 'fullbackup_interval', 'restore_points', 'start_time_window', 'interval',
                   'timezone']
        fields = ['id', 'uuid', 'name', 'fullbackup_interval', 'restore_points', 'start_time_window', 'interval',
                  'timezone']
        self.app.render(res, headers=headers, fields=fields)


class KeyPairServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'cpaas'
        stacked_type = 'nested'
        label = 'keypairs'
        description = "key pair management"
        help = "key pair management"

    @ex(
        help='get key pairs',
        description='get key pairs',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-name'], {'help': 'list of keypair name comma separated', 'action': 'store', 'type': str,
                         'default': None}),
            (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['accounts', 'ids', 'tags', 'sg']
        mappings = {
            'accounts': self.get_account_ids,
            'names': lambda x: x.split(',')
        }
        aliases = {
            'accounts': 'owner-id.N',
            'names': 'key-name.N',
            'size': 'Nvl-MaxResults',
            'page': 'Nvl-NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '%s/computeservices/keypair/describekeypairs' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeKeyPairsResponse')
        page = self.app.pargs.page
        resp = {
            'count': len(res.get('keySet')),
            'page': page,
            'total': res.get('nvl-keyTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'instances': res.get('keySet')
        }

        headers = ['id', 'name', 'account', 'keyFingerprint']
        fields = ['nvl-keyId', 'keyName', 'nvl-ownerAlias', 'keyFingerprint']
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40)

    @ex(
        help='get key pair',
        description='get key pair',
        arguments=ARGS([
            (['name'], {'help': 'keypair name', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        data = {'key-name.N': self.app.pargs.name}
        uri = '%s/computeservices/keypair/describekeypairs' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeKeyPairsResponse.keySet.0', default={})
        self.app.render(res, details=True, maxsize=100)

    
    # @ex(
    #     help='export key pair',
    #     description='export key pair',
    #     arguments=ARGS([
    #         (['name'], {'help': 'keypair name', 'action': 'store', 'type': str}),
    #     ])
    # )
    # def export(self):
    #     data = {'key-name.N': self.app.pargs.name}
    #     uri = '%s/computeservices/keypair/exportkeypairs' % self.baseuri
    #     res = self.cmp_get(uri, data=urlencode(data, doseq=True))
    #     res = dict_get(res, 'ExportKeyPairsResponse.instance', default={})
    #     self.app.render(res, details=True, maxsize=100)


    @ex(
        help='delete a key pair',
        description='delete a key pair',
        arguments=ARGS([
            (['name'], {'help': 'keypair name', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        name = self.app.pargs.name
        data = {'KeyName': name}
        uri = '%s/computeservices/keypair/deletekeypair' % self.baseuri
        res = self.cmp_delete(uri, data=data, timeout=600, entity='keypair %s' % name)

    @ex(
        help='add new RSA key pair',
        description='add new RSA key pair',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
            (['name'], {'help': 'key pair name', 'action': 'store', 'type': str}),
            (['-type'], {'help': 'key type', 'action': 'store', 'type': str}),
        ])
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get('uuid')
        name = self.app.pargs.name
        key_type = self.app.pargs.type
        data = {
            'owner-id': account,
            'KeyName': name,
            'Nvl-KeyPairType': key_type,
        }
        uri = '%s/computeservices/keypair/createkeypair' % self.baseuri
        res = self.cmp_post(uri, data={'keypair': data})
        res = res.get('CreateKeyPairResponse')
        headers = ['name', 'fingerprint SHA1', 'material PEM']
        fields = ['keyName', 'keyFingerprint', 'keyMaterial']
        self.app.render(res, key=None, headers=headers, fields=fields)

        res = {'msg': 'Add key pair %s' % name}
        self.app.render(res)

    @ex(
        help='import public RSA key',
        description='import public RSA key',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
            (['name'], {'help': 'key pair name', 'action': 'store', 'type': str}),
            (['publickey'], {'help': 'file containing public key base64 encoded', 'action': 'store', 'type': str}),
            (['-type'], {'help': 'key type', 'action': 'store', 'type': str}),
        ])
    )
    def import_public_key(self):
        account = self.get_account(self.app.pargs.account).get('uuid')
        name = self.app.pargs.name
        file_name = self.app.pargs.publickey
        key_type = self.app.pargs.type
        file = load_config(file_name)

        data = {
            'owner-id': account,
            'KeyName': name,
            'PublicKeyMaterial': file,
            'Nvl-KeyPairType': key_type
        }
        uri = '%s/computeservices/keypair/importkeypair' % self.baseuri
        res = self.cmp_post(uri, data={'keypair': data})
        res = res.get('ImportKeyPairResponse')

        headers = ['name', 'fingerprint MD5']
        fields = ['keyName', 'keyFingerprint']
        self.app.render(res, key=None, headers=headers, fields=fields)

        res = {'msg': 'Import key pair %s' % name}
        self.app.render(res)


# class VpcServiceController(BusinessControllerChild):
#     class Meta:
#         stacked_on = 'cpaas'
#         stacked_type = 'nested'
#         label = 'DEPRECATED-vpcs'
#         description = "virtual private cloud network service management [DEPRECATED - moved in netaas]"
#         help = "virtual private cloud network service management [DEPRECATED - moved in netaas]"
#
#     @ex(
#         help='get private cloud networks',
#         description='get private cloud networks',
#         arguments=ARGS([
#             (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
#                              'default': None}),
#             (['-ids'], {'help': 'list of private cloud network id comma separated', 'action': 'store', 'type': str,
#                         'default': None}),
#             (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
#             (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
#             (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
#         ])
#     )
#     def list(self):
#         params = ['accounts', 'ids', 'tags']
#         mappings = {
#             'accounts': self.get_account_ids,
#             'tags': lambda x: x.split(','),
#             'ids': lambda x: x.split(',')
#         }
#         aliases = {
#             'accounts': 'owner-id.N',
#             'ids': 'vpc-id.N',
#             'tags': 'tag-value.N',
#             'size': 'Nvl-MaxResults',
#             'page': 'Nvl-NextToken'
#         }
#         data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
#         uri = '%s/computeservices/vpc/describevpcs' % self.baseuri
#         res = self.cmp_get(uri, data=data)
#         res = res.get('DescribeVpcsResponse')
#         page = self.app.pargs.page
#         for item in res.get('vpcSet'):
#             item['cidr'] = ['%s' % (i['cidrBlock']) for i in item['cidrBlockAssociationSet']]
#             item['cidr'] = ', '.join(item['cidr'])
#         resp = {
#             'count': len(res.get('vpcSet')),
#             'page': page,
#             'total': res.get('nvl-vpcTotal'),
#             'sort': {'field': 'id', 'order': 'asc'},
#             'instances': res.get('vpcSet')
#         }
#
#         headers = ['id', 'name', 'state',  'account', 'cidr']
#         fields = ['vpcId', 'nvl-name', 'state', 'nvl-vpcOwnerAlias', 'cidr']
#         self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=60)


# class SubnetServiceController(BusinessControllerChild):
#     class Meta:
#         stacked_on = 'cpaas'
#         stacked_type = 'nested'
#         label = 'DEPRECATED-subnets'
#         description = "vpc subnet service management [DEPRECATED - moved in netaas]"
#         help = "vpc subnet service management [DEPRECATED - moved in netaas]"
#
#     @ex(
#         help='get vpc subnets',
#         description='get vpc subnets',
#         arguments=ARGS([
#             (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
#                              'default': None}),
#             (['-ids'], {'help': 'list of subnet id comma separated', 'action': 'store', 'type': str,
#                         'default': None}),
#             (['-vpcs'], {'help': 'list of vpc id comma separated', 'action': 'store', 'type': str, 'default': None}),
#             (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
#             (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
#         ])
#     )
#     def list(self):
#         params = ['accounts', 'ids', 'tags', 'vpcs']
#         mappings = {
#             'accounts': self.get_account_ids,
#             'tags': lambda x: x.split(','),
#             'ids': lambda x: x.split(','),
#             'vpcs': lambda x: x.split(',')
#         }
#         aliases = {
#             'accounts': 'owner-id.N',
#             'ids': 'subnet-id.N',
#             'vpcs': 'vpc-id.N',
#             'size': 'Nvl-MaxResults',
#             'page': 'Nvl-NextToken'
#         }
#         data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
#         uri = '%s/computeservices/subnet/describesubnets' % self.baseuri
#         res = self.cmp_get(uri, data=data)
#         res = res.get('DescribeSubnetsResponse')
#         page = self.app.pargs.page
#         resp = {
#             'count': len(res.get('subnetSet')),
#             'page': page,
#             'total': res.get('nvl-subnetTotal'),
#             'sort': {'field': 'id', 'order': 'asc'},
#             'instances': res.get('subnetSet')
#         }
#
#         headers = ['id', 'name', 'state',  'account', 'availabilityZone', 'vpc', 'cidr']
#         fields = ['subnetId', 'nvl-name', 'state', 'nvl-subnetOwnerAlias', 'availabilityZone', 'nvl-vpcName',
#                   'cidrBlock']
#         self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40)


# class SecurityGroupServiceController(BusinessControllerChild):
#     class Meta:
#         stacked_on = 'cpaas'
#         stacked_type = 'nested'
#         label = 'DEPRECATED-securitygroups'
#         description = "security groups service management [DEPRECATED - moved in netaas]"
#         help = "security groups service management [DEPRECATED - moved in netaas]"
#
#     @ex(
#         help='get security group templates',
#         description='get security group templates',
#         arguments=ARGS([
#             (['account'], {'help': 'account id', 'action': 'store', 'type': str, 'default': None}),
#             (['-id'], {'help': 'template id', 'action': 'store', 'type': str, 'default': None}),
#         ])
#     )
#     def templates(self):
#         account = self.get_account(self.app.pargs.account).get('uuid')
#         template = self.app.pargs.id
#         if template is None:
#             data = {'plugintype': 'ComputeImage', 'size': -1}
#             uri = '%s/accounts/%s/definitions' % ('/v2.0/nws', account)
#             res = self.cmp_get(uri, data=urlencode(data, doseq=True))
#             headers = ['id', 'instance_type', 'desc', 'status', 'active', 'creation', 'is_default']
#             fields = ['uuid', 'name', 'desc', 'status', 'active', 'date.creation', 'is_default']
#             self.app.render(res, key='servicedefs', headers=headers, fields=fields)
#         else:
#             uri = '%s/servicedefs/%s' % (self.baseuri, template)
#             res = self.cmp_get(uri).get('servicedef')
#             res.pop('__meta__')
#             res.pop('service_type_id')
#             res.pop('id')
#             res['id'] = res.pop('uuid')
#             self.app.render(res, details=True)
#
#             # get rules
#             uri = '%s/servicecfgs' % self.baseuri
#             res = self.cmp_get(uri, data='service_definition_id=%s' % template).get('servicecfgs', [{}])[0]
#             rules = res.pop('params', {}).get('rules')
#             self.c('\ndefault rules', 'underline')
#             self.app.render(rules, headers=['source', 'destination', 'service'], maxsize=200)
#
#     @ex(
#         help='create a security group',
#         description='create a security group',
#         arguments=ARGS([
#             (['name'], {'help': 'security group name', 'action': 'store', 'type': str}),
#             (['vpc'], {'help': 'parent vpc', 'action': 'store', 'type': str}),
#             (['-template'], {'help': 'template id', 'action': 'store', 'type': str}),
#         ])
#     )
#     def add(self):
#         data = {
#             'GroupName': self.app.pargs.name,
#             'VpcId': self.app.pargs.vpc
#         }
#         sg_type = self.app.pargs.template
#         if sg_type is not None:
#             data['GroupType'] = sg_type
#         uri = '%s/computeservices/securitygroup/createsecuritygroup' % self.baseuri
#         res = self.cmp_post(uri, data={'security_group': data}, timeout=600)
#         res = dict_get(res, 'CreateSecurityGroupResponse.groupId')
#         self.app.render({'msg': 'Add securitygroup %s' % res})
#
#     @ex(
#         help='get security groups',
#         description='get security groups',
#         arguments=ARGS([
#             (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
#                              'default': None}),
#             (['-ids'], {'help': 'list of security group id comma separated', 'action': 'store', 'type': str,
#                         'default': None}),
#             (['-vpcs'], {'help': 'list of vpc id comma separated', 'action': 'store', 'type': str, 'default': None}),
#             (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
#             (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
#             (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
#         ])
#     )
#     def list(self):
#         params = ['accounts', 'ids', 'tags', 'vpcs']
#         mappings = {
#             'accounts': self.get_account_ids,
#             'tags': lambda x: x.split(','),
#             'vpcs': lambda x: x.split(','),
#             'ids': lambda x: x.split(',')
#         }
#         aliases = {
#             'accounts': 'owner-id.N',
#             'ids': 'group-id.N',
#             'tags': 'tag-key.N',
#             'vpcs': 'vpc-id.N',
#             'size': 'MaxResults',
#             'page': 'NextToken'
#         }
#         data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
#         uri = '%s/computeservices/securitygroup/describesecuritygroups' % self.baseuri
#         res = self.cmp_get(uri, data=data)
#         res = res.get('DescribeSecurityGroupsResponse', {})
#         page = self.app.pargs.page
#
#         for item in res.get('securityGroupInfo'):
#             item['egress_rules'] = len(item['ipPermissionsEgress'])
#             item['ingress_rules'] = len(item['ipPermissions'])
#
#         resp = {
#             'count': len(res.get('securityGroupInfo')),
#             'page': page,
#             'total': res.get('nvl-securityGroupTotal'),
#             'sort': {'field': 'id', 'order': 'asc'},
#             'instances': res.get('securityGroupInfo')
#         }
#
#         headers = ['id', 'name', 'state',  'account', 'vpc', 'egress_rules', 'ingress_rules']
#         fields = ['groupId', 'groupName', 'nvl-state', 'nvl-sgOwnerAlias', 'nvl-vpcName', 'egress_rules',
#                   'ingress_rules']
#         self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40)
#
#     def __format_rule(self, rules):
#         for rule in rules:
#             if rule['ipProtocol'] == '-1':
#                 rule['ipProtocol'] = '*'
#             if rule.get('fromPort', None) is None or rule['fromPort'] == '-1':
#                 rule['fromPort'] = '*'
#             if rule.get('toPort', None) is None or rule['toPort'] == '-1':
#                 rule['toPort'] = '*'
#             if len(rule.get('groups', None)) > 0:
#                 group = rule['groups'][0]
#                 rule['groups'] = '%s:%s [%s]' % (group.get('nvl-userName', None), group['groupName'], group['groupId'])
#             else:
#                 rule['groups'] = ''
#             if len(rule.get('ipRanges', None)) > 0:
#                 cidr = rule['ipRanges'][0]
#                 rule['ipRanges'] = '%s' % cidr['cidrIp']
#             else:
#                 rule['ipRanges'] = ''
#         return rules
#
#     @ex(
#         help='get security group with rules',
#         description='get security group with rules',
#         arguments=ARGS([
#             (['securitygroup'], {'help': 'securitygroup id', 'action': 'store', 'type': str}),
#         ])
#     )
#     def get(self):
#         securitygroup = self.app.pargs.securitygroup
#         data = {'GroupName.N': [securitygroup]}
#         uri = '%s/computeservices/securitygroup/describesecuritygroups' % self.baseuri
#         res = self.cmp_get(uri, data=urlencode(data, doseq=True))
#         res = dict_get(res, 'DescribeSecurityGroupsResponse.securityGroupInfo', default={})
#         if len(res) == 0:
#             raise Exception('security group %s does not exist' % securitygroup)
#         res = res[0]
#         egress_rules = self.__format_rule(res.pop('ipPermissionsEgress'))
#         ingress_rules = self.__format_rule(res.pop('ipPermissions'))
#         fields = ['groups', 'ipRanges', 'ipProtocol', 'fromPort', 'toPort', 'nvl-reserved', 'nvl-state']
#         self.app.render(res, details=True, maxsize=200)
#         self.c('\negress rules', 'underline')
#         headers = ['toSecuritygroup', 'toCidr', 'protocol', 'fromPort', 'toPort', 'reserved', 'state']
#         self.app.render(egress_rules, headers=headers, fields=fields, maxsize=80)
#         self.c('\nengress rules', 'underline')
#         headers= ['fromSecuritygroup', 'fromCidr', 'protocol', 'fromPort', 'toPort', 'reserved', 'state']
#         self.app.render(ingress_rules, headers=headers, fields=fields, maxsize=80)
#
#     @ex(
#         help='patch a security group',
#         description='patch a security group',
#         arguments=ARGS([
#             (['securitygroup'], {'help': 'securitygroup id', 'action': 'store', 'type': str}),
#         ])
#     )
#     def patch(self):
#         securitygroup = self.app.pargs.securitygroup
#         data = {'GroupName': securitygroup}
#         uri = '%s/computeservices/securitygroup/patchsecuritygroup' % self.baseuri
#         res = self.cmp_patch(uri,  data={'security_group': data}, timeout=600)
#         res = dict_get('PatchSecurityGroupResponse.instancesSet.0.groupId')
#         self.app.render({'msg': 'Patch securitygroup %s' % res})
#
#     @ex(
#         help='delete a security group',
#         description='delete a security group',
#         arguments=ARGS([
#             (['securitygroup'], {'help': 'securitygroup id', 'action': 'store', 'type': str}),
#         ])
#     )
#     def delete(self):
#         oid = self.app.pargs.securitygroup
#         data = {'GroupName': oid}
#         uri = '%s/computeservices/securitygroup/deletesecuritygroup' % self.baseuri
#         res = self.cmp_delete(uri, data={'security_group': data}, timeout=600, entity='securitygroup %s' % oid)
#
#     @ex(
#         help='add a security group rule',
#         description='add a security group rule',
#         arguments=ARGS([
#             (['type'], {'help': 'egress or ingress. For egress rule the destination. For ingress rule specify the '
#                                 'source', 'action': 'store', 'type': str}),
#             (['securitygroup'], {'help': 'securitygroup id', 'action': 'store', 'type': str}),
#             (['-proto'], {'help': 'protocol. can be tcp, udp, icmp or -1 for all', 'action': 'store',
#                           'type': str, 'default': None}),
#             (['-port'], {'help': 'can be an integer between 0 and 65535 or a range with start and end in the same '
#                                  'interval. Range format is <start>-<end>. Use -1 for all ports',
#                          'action': 'store', 'type': str, 'default': None}),
#             (['-dest'], {'help': 'rule destination. Syntax <type>:<value>. Destination type can be SG, CIDR. For SG '
#                                  'value must be <sg_id>. For CIDR value should like 10.102.167.0/24.',
#                          'action': 'store', 'type': str, 'default': None}),
#             (['-source'], {'help': 'rule source. Syntax <type>:<value>. Source type can be SG, CIDR. For SG '
#                                    'value must be <sg_id>. For CIDR value should like 10.102.167.0/24.',
#                            'action': 'store', 'type': str, 'default': None}),
#         ])
#     )
#     def add_rule(self):
#         rule_type = self.app.pargs.type
#         group_id = self.app.pargs.securitygroup
#         dest = self.app.pargs.dest
#         source = self.app.pargs.source
#         port = self.app.pargs.port
#         proto = self.app.pargs.proto
#         from_port = -1
#         to_port = -1
#         if port is not None:
#             port = str(port)
#             port = port.split('-')
#             if len(port) == 1:
#                 from_port = to_port = port[0]
#             else:
#                 from_port, to_port = port
#
#         if proto is None:
#             proto = '-1'
#
#         if rule_type not in ['ingress', 'egress']:
#             raise Exception('rule type must be ingress or egress')
#         if rule_type == 'ingress':
#             if source is None:
#                 raise Exception('ingress rule require source')
#             dest = source.split(':')
#         elif rule_type == 'egress':
#             if dest is None:
#                 raise Exception('egress rule require destination')
#             dest = dest.split(':')
#         if dest[0] not in ['SG', 'CIDR']:
#             raise Exception('source/destination type must be SG or CIDR')
#         data = {
#             'GroupName': group_id,
#             'IpPermissions.N': [
#                 {
#                     'FromPort': from_port,
#                     'ToPort': to_port,
#                     'IpProtocol': proto
#                 }
#             ]
#         }
#         if dest[0] == 'SG':
#             data['IpPermissions.N'][0]['UserIdGroupPairs'] = [{
#                 'GroupName': dest[1]
#             }]
#         elif dest[0] == 'CIDR':
#             data['IpPermissions.N'][0]['IpRanges'] = [{
#                 'CidrIp': dest[1]
#             }]
#         else:
#             raise Exception('Wrong rule type')
#
#         if rule_type == 'egress':
#             uri = '%s/computeservices/securitygroup/authorizesecuritygroupegress' % self.baseuri
#             key = 'AuthorizeSecurityGroupEgressResponse'
#         elif rule_type == 'ingress':
#             uri = '%s/computeservices/securitygroup/authorizesecuritygroupingress' % self.baseuri
#             key = 'AuthorizeSecurityGroupIngressResponse'
#         res = self.cmp_post(uri, data={'rule': data}, timeout=600)
#         res = res.get(key).get('Return')
#         self.app.render('create securitygroup rule %s' % res)
#
#     @ex(
#         help='delete a security group rule',
#         description='delete a security group rule',
#         arguments=ARGS([
#             (['type'], {'help': 'egress or ingress. For egress rule the destination. For ingress rule specify the '
#                                 'source', 'action': 'store', 'type': str}),
#             (['securitygroup'], {'help': 'securitygroup id', 'action': 'store', 'type': str}),
#             (['-proto'], {'help': 'protocol. can be tcp, udp, icmp or -1 for all', 'action': 'store',
#                           'type': str, 'default': None}),
#             (['-port'], {'help': 'can be an integer between 0 and 65535 or a range with start and end in the same '
#                                  'interval. Range format is <start>-<end>. Use -1 for all ports',
#                          'action': 'store', 'type': str, 'default': None}),
#             (['-dest'], {'help': 'rule destination. Syntax <type>:<value>. Destination type can be SG, CIDR. For SG '
#                                  'value must be <sg_id>. For CIDR value should like 10.102.167.0/24.',
#                          'action': 'store', 'type': str, 'default': None}),
#             (['-source'], {'help': 'rule source. Syntax <type>:<value>. Source type can be SG, CIDR. For SG '
#                                    'value must be <sg_id>. For CIDR value should like 10.102.167.0/24.',
#                            'action': 'store', 'type': str, 'default': None}),
#         ])
#     )
#     def del_rule(self):
#         rule_type = self.app.pargs.type
#         group_id = self.app.pargs.securitygroup
#         dest = self.app.pargs.dest
#         source = self.app.pargs.source
#         port = self.app.pargs.port
#         proto = self.app.pargs.proto
#         from_port = -1
#         to_port = -1
#         if port is not None:
#             port = str(port)
#             port = port.split('-')
#             if len(port) == 1:
#                 from_port = to_port = port[0]
#             else:
#                 from_port, to_port = port
#
#         if proto is None:
#             proto = '-1'
#
#         if rule_type not in ['ingress', 'egress']:
#             raise Exception('rule type must be ingress or egress')
#         if rule_type == 'ingress':
#             if source is None:
#                 raise Exception('ingress rule require source')
#             dest = source.split(':')
#         elif rule_type == 'egress':
#             if dest is None:
#                 raise Exception('egress rule require destination')
#             dest = dest.split(':')
#         if dest[0] not in ['SG', 'CIDR']:
#             raise Exception('source/destination type must be SG or CIDR')
#         data = {
#             'GroupName': group_id,
#             'IpPermissions.N': [
#                 {
#                     'FromPort': from_port,
#                     'ToPort': to_port,
#                     'IpProtocol': proto
#                 }
#             ]
#         }
#         if dest[0] == 'SG':
#             data['IpPermissions.N'][0]['UserIdGroupPairs'] = [{'GroupName': dest[1]}]
#         elif dest[0] == 'CIDR':
#             data['IpPermissions.N'][0]['IpRanges'] = [{'CidrIp': dest[1]}]
#         else:
#             raise Exception('wrong rule type')
#
#         if rule_type == 'egress':
#             uri = '%s/computeservices/securitygroup/revokesecuritygroupegress' % self.baseuri
#         elif rule_type == 'ingress':
#             uri = '%s/computeservices/securitygroup/revokesecuritygroupingress' % self.baseuri
#         res = self.cmp_delete(uri, data={'rule': data}, timeout=600, entity='securitygroup rule')


class TagServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'cpaas'
        stacked_type = 'nested'
        label = 'compute_tags'
        description = "tags service management"
        help = "tags service management"

    @ex(
        help='list resource by tags',
        description='list resource by tags',
        arguments=ARGS([
            (['-account'], {'help': 'account id', 'action': 'store', 'type': str, 'default': None}),
            (['-services'], {'help': 'comma separated list of service instance id', 'action': 'store', 'type': str,
                             'default': None}),
            (['-tags'], {'help': 'comma separated list of tag key', 'action': 'store', 'type': str, 'default': None}),
            (['-types'], {'help': 'comma separated list of service instance types', 'action': 'store', 'type': str,
                          'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['account', 'services', 'tags', 'types']
        mappings = {
            'account': lambda x: x,
            'services': lambda x: x.split(','),
            'tags': lambda x: x.split(','),
            'types': lambda x: x.split(',')
        }
        aliases = {
            'account': 'owner-id.N',
            'services': 'resource-id.N',
            'types': 'resource-type.N',
            'tags': 'key.N',
            'size': 'MaxResults',
            'page': 'NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '%s/computeservices/tag/describetags' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeTagsResponse')
        page = self.app.pargs.page
        resp = {
            'count': len(res.get('tagSet')),
            'page': page,
            'total': res.get('nvl-tagTotal', 0),
            'sort': {'field': 'id', 'order': 'asc'},
            'instances': res.get('tagSet')
        }
        headers = ['service-instance', 'type', 'tag']
        fields = ['resourceId', 'resourceType', 'key']
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40)

    @ex(
        help='add tag to service instance',
        description='add tag to service instance',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
            (['service'], {'help': 'service instance id', 'action': 'store', 'type': str}),
            (['tag'], {'help': 'tag key', 'action': 'store', 'type': str}),
        ])
    )
    def add(self):
        account = self.app.pargs.account
        account = self.get_account(account).get('uuid')
        service = self.app.pargs.service
        tag = self.app.pargs.tag
        data = {
            'owner-id': account,
            'ResourceId.N': [service],
            'Tag.N': [{'Key': tag}],
        }
        uri = '%s/computeservices/tag/createtags' % self.baseuri
        res = self.cmp_post(uri, data={'tags': data}, timeout=600)
        dict_get(res, 'CreateTagsResponse.return')
        res = {'msg': 'add tag %s to %s' % (tag, service)}
        self.app.render(res)

    @ex(
        help='delete tag from service instance',
        description='delete tag from service instance',
        arguments=ARGS([
            (['service'], {'help': 'service instance id', 'action': 'store', 'type': str}),
            (['tag'], {'help': 'tag key', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        service = self.app.pargs.service
        tag = self.app.pargs.tag
        data = {
            'ResourceId.N': [service],
            'Tag.N': [{'Key': tag}],
        }
        uri = '%s/computeservices/tag/deletetags' % self.baseuri
        self.cmp_delete(uri, data={'tags': data}, timeout=600, entity='service %s tag %s' % (service, tag))


class CustomizationServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'cpaas'
        stacked_type = 'nested'
        label = 'customizations'
        description = "customization service management"
        help = "customization service management"

    @ex(
        help='get customizations types',
        description='get customizations types',
        arguments=ARGS([
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str, 'default': None}),
            (['-id'], {'help': 'customization type id', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def types(self):
        oid = self.app.pargs.id
        if oid is not None:
            account = self.get_account(self.app.pargs.account)['uuid']
            data = urlencode({'CustomizationType': oid, 'owner-id': account}, doseq=True)
            uri = '%s/computeservices/customization/describecustomizationtypes' % self.baseuri
            res = self.cmp_get(uri, data=data)
            res = dict_get(res, 'DescribeCustomizationTypesResponse.customizationTypesSet.0')
            params = res.pop('args')
            self.app.render(res, details=True)
            self.c('\nparams', 'underline')
            self.app.render(params, headers=['name', 'desc', 'required', 'type', 'default', 'allowed'])
        else:
            params = ['account']
            mappings = {
                'account': lambda x: self.get_account(x)['uuid'],
            }
            aliases = {
                'account': 'owner-id',
                'size': 'MaxResults',
                'page': 'NextToken'
            }
            data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
            uri = '%s/computeservices/customization/describecustomizationtypes' % self.baseuri
            res = self.cmp_get(uri, data=data)
            res = res.get('DescribeCustomizationTypesResponse')
            page = self.app.pargs.page
            resp = {
                'count': len(res.get('customizationTypesSet')),
                'page': page,
                'total': res.get('customizationTypesTotal'),
                'sort': {'field': 'id', 'order': 'asc'},
                'types': res.get('customizationTypesSet')
            }
            headers = ['id', 'customization_type', 'desc']
            fields = ['uuid', 'name', 'description']
            self.app.render(resp, key='types', headers=headers, fields=fields)

    @ex(
        help='list customizations',
        description='list customizations',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-customizations'], {'help': 'list of customization id comma separated', 'action': 'store', 'type': str,
                                   'default': None}),
            (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['accounts', 'customizations']
        mappings = {
            'accounts': self.get_account_ids,
            'tags': lambda x: x.split(','),
            'customizations': lambda x: x.split(',')
        }
        aliases = {
            'accounts': 'owner-id.N',
            'customizations': 'customization-id.N',
            'tags': 'tag-key.N',
            'size': 'MaxResults',
            'page': 'NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)

        uri = '%s/computeservices/customization/describecustomizations' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeCustomizationsResponse')
        page = self.app.pargs.page
        resp = {
            'count': len(res.get('customizationsSet')),
            'page': page,
            'total': res.get('customizationTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'customizations': res.get('customizationsSet')
        }

        headers = ['id', 'name', 'state', 'type', 'account', 'creation']
        fields = ['customizationId', 'customizationName', 'customizationState.name', 'customizationType', 'ownerAlias',
                  'launchTime']
        self.app.render(resp, key='customizations', headers=headers, fields=fields, maxsize=40)

    @ex(
        help='get customization',
        description='get customization',
        arguments=ARGS([
            (['customization'], {'help': 'customization id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        customization_id = self.app.pargs.customization
        if self.is_uuid(customization_id):
            data = {'customization-id.N': [customization_id]}
        elif self.is_name(customization_id):
            data = {'customization-name.N': [customization_id]}

        uri = '%s/computeservices/customization/describecustomizations' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeCustomizationsResponse.customizationsSet', default={})
        if len(res) > 0:
            res = res[0]
            if self.is_output_text():
                self.app.render(res, details=True, maxsize=100)
            else:
                self.app.render(res, details=True, maxsize=100)
        else:
            raise Exception('customization %s was not found' % customization_id)

    @ex(
        help='create a customization',
        description='create a customization',
        arguments=ARGS([
            (['name'], {'help': 'customization name', 'action': 'store', 'type': str}),
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['type'], {'help': 'customization type', 'action': 'store', 'type': str}),
            (['instances'], {'help': 'comma separated list of compute instance id', 'action': 'store', 'type': str}),
            (['args'], {'help': 'customization params. Use syntax arg1:val1,arg2:val2', 'action': 'store', 'type': str}),
        ])
    )
    def add(self):
        name = self.app.pargs.name
        account = self.get_account(self.app.pargs.account).get('uuid')
        itype = self.get_service_definition(self.app.pargs.type)
        instances = self.app.pargs.instances.split(',')
        args = self.app.pargs.args.split(',')

        params = []
        for arg in args:
            arg = arg.split(':')
            params.append({'Name': arg[0], 'Value': arg[1]})

        data = {
            'Name': name,
            'owner-id': account,
            'CustomizationType': itype,
            'Instances': instances,
            'Args': params,
        }
        uri = '%s/computeservices/customization/runcustomizations' % self.baseuri
        res = self.cmp_post(uri, data={'customization': data}, timeout=600)
        uuid = dict_get(res, 'RunCustomizationResponse.customizationId')
        self.wait_for_service(uuid)
        self.app.render({'msg': 'add customization: %s' % uuid})

    @ex(
        help='delete a customization',
        description='delete a customization',
        arguments=ARGS([
            (['customization'], {'help': 'customization id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        customization_id = self.app.pargs.customization
        if self.is_name(customization_id):
            raise Exception('only customization id is supported')
        data = {'CustomizationId': customization_id}
        uri = '%s/computeservices/customization/terminatecustomizations' % self.baseuri
        self.cmp_delete(uri, data=data, timeout=600, output=False, entity='customization %s' % customization_id)
        self.wait_for_service(customization_id, accepted_state='DELETED')
        self.app.render({'msg': 'delete customization: %s' % customization_id})

    @ex(
        help='update a customization',
        description='update a customization',
        arguments=ARGS([
            (['customization'], {'help': 'customization id', 'action': 'store', 'type': str}),
        ])
    )
    def update(self):
        customization_id = self.app.pargs.customization
        if self.is_name(customization_id):
            raise Exception('only customization id is supported')
        data = {'CustomizationId': customization_id}
        uri = '%s/computeservices/customization/updatecustomizations' % self.baseuri
        self.cmp_put(uri, data=data, timeout=600).get('UpdateCustomizationResponse')
        self.wait_for_service(customization_id)
        self.app.render({'msg': 'update customization: %s' % customization_id})
