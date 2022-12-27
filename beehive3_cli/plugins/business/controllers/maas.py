# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beecell.types.type_dict import dict_get
from beecell.types.type_string import str2bool
from beehive3_cli.core.controller import ARGS, PARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


class MonitoraaServiceController(BusinessControllerChild):
    class Meta:
        label = 'maas'
        description = "monitoring service management"
        help = "monitoring service management"

    @ex(
        help='get monitoring service info',
        description='get monitoring service info',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def info(self):
        account = self.app.pargs.account
        account = self.get_account(account).get('uuid')
        data = {'owner-id': account}
        uri = '%s/monitoringservices' % self.baseuri
        res = self.cmp_get(uri, data=data)

        res = dict_get(res, 'DescribeMonitoringResponse', default={})
        if len(res.get('monitoringSet')) > 0:
            res = dict_get(res, 'monitoringSet.0')
            self.app.render(res, details=True, maxsize=400)

    @ex(
        help='get monitoring service quotas',
        description='get monitoring service quotas',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def quotas(self):
        account = self.app.pargs.account
        account = self.get_account(account).get('uuid')
        data = {'owner-id': account}
        uri = '%s/monitoringservices/describeaccountattributes' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data))
        res = dict_get(res, 'DescribeAccountAttributesResponse.accountAttributeSet')
        headers = ['name', 'value', 'used']
        fields = ['attributeName', 'attributeValueSet.0.item.attributeValue',
                  'attributeValueSet.0.item.nvl-attributeUsed']
        self.app.render(res, headers=headers, fields=fields)


class MonitoringServiceInstanceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'maas'
        stacked_type = 'nested'
        label = 'monitor-instances'
        description = "monitoring instance service management"
        help = "monitoring instance service management"

        cmp = {'baseuri': '/v1.0/nws', 'subsystem': 'service'}

    # @ex(
    #     help='get monitoring module configs',
    #     description='get monitoring module configs',
    #     arguments=ARGS([
    #         (['account'], {'help': 'parent account id', 'action': 'store', 'type': str, 'default': None})
    #     ])
    # )
    # def configs(self):
    #     data = {'owner-id': self.get_account(self.app.pargs.account)['uuid']}
    #     uri = '/v1.0/nws/monitoringservices/instance/describemonitorconfig'
    #     res = self.cmp_get(uri, data=data).get('DescribeMonitoringInstanceMonitorConfigResponse')
    #     self.app.render(res, headers=['name'], fields=['name'], key='monitorConfigSet')

    @ex(
        help='list monitoring instances',
        description='list monitoring instances',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-name'], {'help': 'list of monitoring instances id comma separated', 'action': 'store', 'type': str,
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
            'name': 'name',
            'tags': 'tag-key.N',
            'size': 'MaxItems',
            'page': 'Marker'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        page = self.app.pargs.page
        uri = '%s/monitoringservices/instance/describeinstances' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeMonitoringInstancesResponse')

        total = res.get('nvl-instanceTotal')
        res = res.get('instanceInfo', [])
        resp = {
            'count': len(res),
            'page': page,
            'total': total,
            'sort': {
                'field': 'date.creation', 
                'order': 'desc'
            },
            'instances': res
        } 

        headers = ['id', 'name', 'status', 'creation', 'instance'] #, 'modules']
        fields = ['id', 'name', 'state', 'creationDate', 'computeInstanceId'] #, 'modules']
        transform = {'modules': lambda x: list(x.keys()) if x is not None and isinstance(x, dict) else '' }
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40, transform=transform)

    @ex(
        help='get monitoring instance',
        description='get monitoring instance',
        arguments=ARGS([
            (['id'], {'help': 'monitoring instance id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {'instance-id.N': [oid]}
        elif self.is_name(oid):
            data = {'InstanceName': oid}
        uri = '%s/monitoringservices/instance/describeinstances' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeMonitoringInstancesResponse', default={})

        if len(res.get('instanceInfo')) > 0:
            res = dict_get(res, 'instanceInfo.0')
            self.app.render(res, details=True, maxsize=400)

    @ex(
        help='create a monitoring instance',
        description='create a monitoring instance',
        arguments=ARGS([
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['instance'], {'help': 'instance', 'action': 'store', 'type': str}),
            (['-definition'], {'help': 'definition', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get('uuid')
        instance = self.app.pargs.instance
        definition = self.app.pargs.definition

        data = {
            'owner-id': account,
            'ComputeInstanceId': instance
        }

        if definition is not None:
            definition = self.get_service_definition(definition)
            data['InstanceType'] = definition.uuid

        uri = '%s/monitoringservices/instance/createinstance' % self.baseuri
        res = self.cmp_post(uri, data={'instance': data}, timeout=600)
        uuid = dict_get(res, 'CreateMonitoringInstanceResponse.instanceId')
        self.wait_for_service(uuid)
        self.app.render({'msg': 'Add monitoring instance %s' % uuid})

    @ex(
        help='delete a monitoring instance',
        description='delete a monitoring instance',
        arguments=ARGS([
            (['instance_id'], {'help': 'monitoring instance id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        monitoring_instance_id = self.app.pargs.instance_id
        uri = '%s/monitoringservices/instance/deleteteinstance' % self.baseuri
        self.cmp_delete(uri, data={'InstanceId': monitoring_instance_id},
                        entity='monitoring instance %s' % monitoring_instance_id)
        self.wait_for_service(monitoring_instance_id, accepted_state='DELETED')

    #
    # action
    #
    # @ex(
    #     help='enable monitoring module',
    #     description='enable monitoring module',
    #     arguments=ARGS([
    #         (['instance_id'], {'help': 'monitoring instance id', 'action': 'store', 'type': str}),
    #         (['conf'], {'help': 'module configuration', 'action': 'store', 'type': str}),
    #     ])
    # )
    # def enable_module(self):
    #     instance_id = self.app.pargs.instance_id
    #     conf = self.app.pargs.conf
    #     uri = '%s/monitoringservices/instance/enablemonitorconfig' % self.baseuri
    #     self.cmp_put(uri, data={'InstanceId': instance_id, 'Config': conf})
    #     self.app.render({'msg': 'enable monitoring module %s' % conf})

    # @ex(
    #     help='disable monitoring module',
    #     description='disable monitoring module',
    #     arguments=ARGS([
    #         (['instance_id'], {'help': 'monitoring instance id', 'action': 'store', 'type': str}),
    #         (['conf'], {'help': 'module configuration', 'action': 'store', 'type': str}),
    #     ])
    # )
    # def disable_module(self):
    #     instance_id = self.app.pargs.instance_id
    #     conf = self.app.pargs.conf
    #     uri = '%s/monitoringservices/instance/disablemonitorconfig' % self.baseuri
    #     self.cmp_put(uri, data={'InstanceId': instance_id, 'Config': conf})
    #     self.app.render({'msg': 'disable monitoring module %s' % conf})


class MonitoringServiceFolderController(BusinessControllerChild):
    class Meta:
        stacked_on = 'maas'
        stacked_type = 'nested'
        label = 'folders'
        description = "monitoring folder service management"
        help = "monitoring folder service management"

        cmp = {'baseuri': '/v1.0/nws', 'subsystem': 'service'}

    @ex(
        help='list monitoring folders',
        description='list monitoring folders',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-name'], {'help': 'list of monitoring instances id comma separated', 'action': 'store', 'type': str,
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
            'name': 'name',
            'tags': 'tag-key.N',
            'size': 'MaxItems',
            'page': 'Marker'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        page = self.app.pargs.page
        uri = '%s/monitoringservices/folders/describefolders' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeFoldersResponse')

        total = res.get('folderTotal')
        res = res.get('folderInfo', [])
        resp = {
            'count': len(res),
            'page': page,
            'total': total,
            'sort': {
                'field': 'date.creation', 
                'order': 'desc'
            },
            'folders': res
        } 

        headers = ['id', 'name', 'status', 'account', 'template', 'creation', 'endpoint']
        fields = ['id', 'name', 'state', 'ownerAlias', 'templateName', 'creationDate', 'endpoints.home']
        transform = {}
        self.app.render(resp, key='folders', headers=headers, fields=fields, maxsize=100, transform=transform)

    @ex(
        help='get monitoring folder',
        description='get monitoring folder',
        arguments=ARGS([
            (['id'], {'help': 'folder id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {'folder-id.N': [oid]}   # monitoring-folder-id
        elif self.is_name(oid):
            data = {'FolderName': oid}
        uri = '%s/monitoringservices/folders/describefolders' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeFoldersResponse', default={})

        if len(res.get('folderInfo')) > 0:
            if self.is_output_text():
                res = dict_get(res, 'folderInfo.0')
                dashboards = res.pop('dashboards', [])
                permissions = res.pop('permissions', [])
                self.app.render(res, details=True, maxsize=400)

                self.c('\ndashboards', 'underline')
                headers = ['id', 'name', 'endpoint']
                fields = ['dashboardId', 'dashboardName', 'endpoint']
                self.app.render(dashboards, headers=headers, fields=fields, maxsize=400)

                self.c('\npermissions', 'underline')
                headers = ['name', 'teamName', 'modificationDate']
                fields = ['permissionName', 'teamName', 'modificationDate']
                self.app.render(permissions, headers=headers, fields=fields, maxsize=400)
            else:
                self.app.render(res, details=True, maxsize=400)

    @ex(
        help='create a monitoring folder',
        description='create a monitoring folder',
        arguments=ARGS([
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['-name'], {'help': 'folder name', 'action': 'store', 'type': str, 'default': None}),
            (['-definition'], {'help': 'service definition of the folder', 'action': 'store', 'type': str, 'default': None}),
            (['-norescreate'], {'help': 'don\'t create physical resource of the folder', 'action': 'store', 'type': str, 'default': False}),
        ])
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get('uuid')
        name = self.app.pargs.name
        definition = self.app.pargs.definition
        norescreate = self.app.pargs.norescreate

        data = {
            'owner-id': account,
        }

        if name is not None:
            data.update({'Name': name})
        if definition is not None:
            data.update({'definition': definition})
        if norescreate is not None:
            data.update({'norescreate': norescreate})

        # print('data: %s' % data)

        uri = '%s/monitoringservices/folders/createfolder' % self.baseuri
        res = self.cmp_post(uri, data={'folder': data}, timeout=600)

        createFolderResponse = dict_get(res, 'CreateFolderResponse')
        folderId = dict_get(createFolderResponse, 'folderId')
        self.wait_for_service(folderId)
        self.app.render({'msg': 'Add monitoring folder %s' % folderId})

    @ex(
        help='delete a monitoring folder',
        description='delete a monitoring folder',
        arguments=ARGS([
            (['monitoring_folder_id'], {'help': 'monitoring folder id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        monitoring_folder_id = self.app.pargs.monitoring_folder_id
        uri = '%s/monitoringservices/folders/deletefolder' % self.baseuri
        self.cmp_delete(uri, data={'FolderId': monitoring_folder_id}, entity='monitoring folder %s' % monitoring_folder_id)
        self.wait_for_service(monitoring_folder_id, accepted_state='DELETED')

    @ex(
        help='synchronize users of monitoring folder',
        description='synchronize users of monitoring folder',
        arguments=ARGS([
            (['monitoring_folder_id'], {'help': 'monitoring folder id', 'action': 'store', 'type': str}),
        ])
    )
    def sync_users(self):
        monitoring_folder_id = self.app.pargs.monitoring_folder_id
        uri = '%s/monitoringservices/folders/syncfolderusers' % (self.baseuri)
        self.cmp_put(uri, data={'FolderId': monitoring_folder_id})
        self.app.render({'msg': 'sync folder %s users' % monitoring_folder_id})
