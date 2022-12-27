# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import ARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


class STaaServiceController(BusinessControllerChild):
    class Meta:
        label = 'staas'
        description = "storage service management"
        help = "storage service management"

    @ex(
        help='get storage service info',
        description='get storage service info',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def info(self):
        account = self.app.pargs.account
        account = self.get_account(account).get('uuid')
        data = {'owner-id': account}
        uri = '%s/storageservices' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data))
        res = dict_get(res, 'DescribeStorageResponse.storageSet.0')
        self.app.render(res, details=True, maxsize=100)

    @ex(
        help='get storage service quotas',
        description='get storage service quotas',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def quotas(self):
        account = self.app.pargs.account
        account = self.get_account(account).get('uuid')
        data = {'owner-id': account}
        uri = '%s/storageservices/describeaccountattributes' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data))
        res = dict_get(res, 'DescribeAccountAttributesResponse.accountAttributeSet')
        headers = ['name', 'value', 'used']
        fields = ['attributeName', 'attributeValueSet.0.item.attributeValue',
                  'attributeValueSet.0.item.nvl-attributeUsed']
        self.app.render(res, headers=headers, fields=fields)


class STaaServiceEfsController(BusinessControllerChild):
    class Meta:
        stacked_on = 'staas'
        stacked_type = 'nested'
        label = 'efs'
        description = "file share service management"
        help = "file share service management"

    @ex(
        help='get share types',
        description='get share types',
        arguments=ARGS()
    )
    def types(self):
        data = {
            'plugintype': 'StorageEFS',
            'page': 0,
            'size': 100
        }
        uri = '%s/srvcatalogs/all/defs' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data))
        headers = ['id', 'instance_type', 'desc', 'status', 'active', 'creation']
        fields = ['uuid', 'name', 'desc', 'status', 'active', 'date.creation']
        self.app.render(res, key='servicedefs', headers=headers, fields=fields)

    @ex(
        help='list share',
        description='list share',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-name'], {'help': 'list of share id comma separated', 'action': 'store', 'type': str,
                         'default': None}),
            (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['accounts', 'name', 'tags']
        mappings = {
            'accounts': self.get_account_ids,
            'tags': lambda x: x.split(',')
        }
        aliases = {
            'accounts': 'owner-id.N',
            'name': 'CreationToken',
            'tags': 'tag-key.N',
            'size': 'MaxItems',
            'page': 'Marker'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        page = self.app.pargs.page
        uri = '%s/storageservices/efs/file-systems' % self.baseuri
        res = self.cmp_get(uri, data=data)
        total = res.get('nvl-fileSystemTotal')
        res = res.get('FileSystems', [])
        resp = {
            'count': len(res),
            'page': page,
            'total': total,
            'sort': {'field': 'date.creation', 'order': 'desc'},
            'instances': res
        } 

        headers = ['id', 'name', 'status',  'creation', 'account', 'targets', 'size(bytes)', 'mode']
        fields = ['FileSystemId',  'CreationToken',  'LifeCycleState',  'CreationTime', 'OwnerId',
                  'NumberOfMountTargets', 'SizeInBytes.Value', 'PerformanceMode']
        transform = {'LifeCycleState': self.color_error}
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40, transform=transform)

    @ex(
        help='get share',
        description='get share',
        arguments=ARGS([
            (['share'], {'help': 'share id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        uuid = self.app.pargs.share
        data = {
            'FileSystemId': uuid
        }
        uri = '%s/storageservices/efs/file-systems' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = res.get('FileSystems', [])
        if len(res) == 0:
            raise Exception('share %s does not exists' % uuid)
    
        if self.is_output_text():
            self.app.render(res[0], details=True, maxsize=200)

            self.c('\nmount targets', 'underline')
            data = {}
            # data['owner-id.N'] = self.split_arg('owner-id.N')
            data['FileSystemId'] = uuid
            data['MaxItems'] = 10
            data['Marker'] = 0
            uri = '%s/storageservices/efs/mount-targets' % self.baseuri
            res = self.cmp_get(uri, data=urlencode(data, doseq=True))
            res = res.get('MountTargets', [])
            headers = ['status', 'target', 'availability-zone', 'subnet', 'ipaddress', 'proto']
            fields = ['LifeCycleState', 'MountTargetId', 'nvl-AvailabilityZone', 'SubnetId', 'IpAddress',
                      'nvl-ShareProto']
            self.app.render(res, headers=headers, fields=fields, maxsize=200)

            self.c('\ngrants', 'underline')
            uri = '%s/storageservices/efs/mount-targets/%s/grants' % (self.baseuri, uuid)
            res = self.cmp_get(uri, timeout=600)
            resp = []
            for grant in res.get('grants'):
                resp.append({
                    'id': res.get('FileSystemId'),
                    'grant-id': grant.get('id'),
                    'access-level': grant.get('access_level'),
                    'state': grant.get('state'),
                    'access-type': grant.get('access_type'),
                    'access-to': grant.get('access_to')
                })
            self.app.render(resp, headers=['grant-id', 'state', 'access-level', 'access-type', 'access-to'],
                            maxsize=200)
        else:
            self.app.render(res, details=True, maxsize=100)

    @ex(
        help='create a share',
        description='create a share',
        arguments=ARGS([
            (['name'], {'help': 'share name', 'action': 'store', 'type': str}),
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['size'], {'help': 'share size', 'action': 'store', 'type': int}),
            (['-type'], {'help': 'share type', 'action': 'store', 'type': str, 'default': None}),
            (['-mode'], {'help': 'share performance mode. Can be generalPurpose or localPurpose', 'action': 'store',
                         'type': str, 'default': 'generalPurpose'}),
        ])
    )
    def add(self):
        data = {
            'CreationToken': self.app.pargs.name,
            'owner_id': self.get_account(self.app.pargs.account).get('uuid'),
            'Nvl_FileSystem_Size': self.app.pargs.size,
            'PerformanceMode': self.app.pargs.mode
        }
        fs_type = self.app.pargs.type
        if fs_type is not None:
            data['Nvl_FileSystem_Type'] = fs_type
        uri = '%s/storageservices/efs/file-systems' % self.baseuri
        res = self.cmp_post(uri, data=data, timeout=600)

        self.app.render({'msg': 'add storage efs instance share %s' % res.get('FileSystemId', None)})

    @ex(
        help='resize a share',
        description='resize a share',
        arguments=ARGS([
            (['share'], {'help': 'share id', 'action': 'store', 'type': str}),
            (['size'], {'help': 'new share size in GB', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def resize(self):
        oid = self.app.pargs.share
        params = {'Nvl_FileSystem_Size': self.app.pargs.size}
        uri = '%s/storageservices/efs/file-systems/%s' % (self.baseuri, oid)
        self.cmp_put(uri, data=params)
        self.app.render({'msg': 'resize share %s' % oid})

    @ex(
        help='delete a share',
        description='delete a share',
        arguments=ARGS([
            (['share'], {'help': 'share id', 'action': 'store', 'type': str})
        ])
    )
    def delete(self):
        uuid = self.app.pargs.share
        uri = '%s/storageservices/efs/file-systems/%s' % (self.baseuri, uuid)
        self.cmp_delete(uri, timeout=300, entity='share %s' % uuid)

    @ex(
        help='list share mount target',
        description='list share mount target',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-name'], {'help': 'list of share id comma separated', 'action': 'store', 'type': str,
                         'default': None}),
            (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def target_list(self):
        params = ['accounts']
        mappings = {
            'accounts': self.get_account_ids
        }
        aliases = {
            'accounts': 'owner-id.N',
            'size': 'MaxItems',
            'page': 'Marker'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        page = self.app.pargs.page
        uri = '%s/storageservices/efs/mount-targets' % self.baseuri
        res = self.cmp_get(uri, data=data, timeout=600)
        total = res.get('nvl_fileSystemTargetTotal')
        res = dict_get(res, 'MountTargets', default=[])
        resp = {
            'count': len(res),
            'page': page,
            'total': total,
            'sort': {'field': 'date.creation', 'order': 'desc'},
            'instances': res
        }

        headers = ['file-system', 'ipaddress', 'target', 'account', 'availability-zone', 'subnet', 'proto', 'status']
        fields = ['FileSystemId', 'IpAddress', 'MountTargetId', 'OwnerId', 'nvl-AvailabilityZone', 'SubnetId',
                  'nvl-ShareProto', 'LifeCycleState']
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=200)

    @ex(
        help='create share mount target',
        description='create share mount target',
        arguments=ARGS([
            (['share'], {'help': 'share id', 'action': 'store', 'type': str}),
            (['subnet'], {'help': 'share subnet', 'action': 'store', 'type': str, 'default': None}),
            (['protocol'], {'help': 'protocol should be  nfs|cifs', 'action': 'store', 'type': str, 'default': None}),
            (['-label'], {'help': 'custom label to be used when you want to use a labelled share type',
                          'action': 'store', 'type': str, 'default': None}),
            (['-ontap_volume'], {'help': 'ontap netapp volume id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def target_add(self):
        share = self.app.pargs.share
        label = self.app.pargs.label
        ontap_volume = self.app.pargs.ontap_volume
        data = {
            'Nvl_FileSystemId': share,
            'SubnetId': self.app.pargs.subnet,
            'Nvl_shareProto': self.app.pargs.protocol
        }
        if label is not None:
            data['Nvl_shareLabel'] = label
        if ontap_volume is not None:
            data['Nvl_shareVolume'] = ontap_volume

        uri = '%s/storageservices/efs/mount-targets' % self.baseuri
        self.cmp_post(uri, data=data, timeout=600)
        self.app.render({'msg': 'add share %s mount target' % share})

    @ex(
        help='delete share mount target',
        description='delete share mount target',
        arguments=ARGS([
            (['share'], {'help': 'share id', 'action': 'store', 'type': str})
        ])
    )
    def target_delete(self):
        share = self.app.pargs.share
        uri = '%s/storageservices/efs/mount-targets' % self.baseuri
        self.cmp_delete(uri, data={'Nvl_FileSystemId': share}, entity='share %s mount target' % share)
 
    @ex(
        help='create a share grant',
        description='create a share grant',
        arguments=ARGS([
            (['share'], {'help': 'share id', 'action': 'store', 'type': str}),
            (['access_level'], {'help': 'access to grant shld be rw | r', 'action': 'store', 'type': str}),
            (['access_type'], {'help': 'access type should be ip', 'action': 'store', 'type': str}),
            (['access_to'], {'help': 'access to expression', 'action': 'store', 'type': str}),
        ])
    )
    def grant_add(self):
        uuid = self.app.pargs.share
        data = { 
            'access_level': self.app.pargs.access_level,
            'access_type': self.app.pargs.access_type,
            'access_to': self.app.pargs.access_to,
        } 
        uri = '%s/storageservices/efs/mount-targets/%s/grants' % (self.baseuri, uuid)
        res = self.cmp_post(uri, data={'grant': data}, timeout=600)
        self.app.render({'msg': 'add grant share %s' % res})

    @ex(
        help='delete share grant',
        description='delete share grant',
        arguments=ARGS([
            (['share'], {'help': 'share id', 'action': 'store', 'type': str}),
            (['grant'], {'help': 'grant id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def grant_delete(self):
        uuid = self.app.pargs.share
        grant = self.app.pargs.grant
        data = {
            'access_id': grant
        }
        uri = '%s/storageservices/efs/mount-targets/%s/grants' % (self.baseuri, uuid)
        self.cmp_delete(uri, data={'grant': data}, timeout=600, entity='share %s grant %s' % (uuid, grant))
