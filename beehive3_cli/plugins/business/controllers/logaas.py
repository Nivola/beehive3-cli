# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beecell.types.type_dict import dict_get
from beecell.types.type_string import str2bool
from beehive3_cli.core.controller import ARGS, PARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


class LogaaServiceController(BusinessControllerChild):
    class Meta:
        label = 'logaas'
        description = "logging service management"
        help = "logging service management"

    @ex(
        help='get logging service info',
        description='get logging service info',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def info(self):
        account = self.app.pargs.account
        account = self.get_account(account).get('uuid')
        data = {'owner-id': account}
        uri = '%s/loggingservices' % self.baseuri
        res = self.cmp_get(uri, data=data)

        res = dict_get(res, 'DescribeLoggingResponse', default={})
        if len(res.get('loggingSet')) > 0:
            res = dict_get(res, 'loggingSet.0')
            self.app.render(res, details=True, maxsize=400)

    @ex(
        help='get logging service quotas',
        description='get logging service quotas',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def quotas(self):
        account = self.app.pargs.account
        account = self.get_account(account).get('uuid')
        data = {'owner-id': account}
        uri = '%s/loggingservices/describeaccountattributes' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data))
        res = dict_get(res, 'DescribeAccountAttributesResponse.accountAttributeSet')
        headers = ['name', 'value', 'used']
        fields = ['attributeName', 'attributeValueSet.0.item.attributeValue',
                  'attributeValueSet.0.item.nvl-attributeUsed']
        self.app.render(res, headers=headers, fields=fields)


class LoggingServiceInstanceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'logaas'
        stacked_type = 'nested'
        label = 'instances'
        description = "logging instance service management"
        help = "logging instance service management"

        cmp = {'baseuri': '/v1.0/nws', 'subsystem': 'service'}

    @ex(
        help='get logging module configs',
        description='get logging module configs',
        arguments=ARGS([
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def configs(self):
        data = {'owner-id': self.get_account(self.app.pargs.account)['uuid']}
        uri = '/v1.0/nws/loggingservices/instance/describelogconfig'
        res = self.cmp_get(uri, data=data).get('DescribeLoggingInstanceLogConfigResponse')
        self.app.render(res, headers=['name'], fields=['name'], key='logConfigSet')

    @ex(
        help='list logging instances',
        description='list logging instances',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-name'], {'help': 'list of logging instances id comma separated', 'action': 'store', 'type': str,
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
        uri = '%s/loggingservices/instance/describeinstances' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeLoggingInstancesResponse')

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

        headers = ['id', 'name', 'status', 'creation', 'instance', 'modules']
        fields = ['id', 'name', 'state', 'creationDate', 'computeInstanceId', 'modules']
        transform = {'modules': lambda x: list(x.keys()) if x is not None and isinstance(x, dict) else '' }
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40, transform=transform)

    @ex(
        help='get logging instance',
        description='get logging instance',
        arguments=ARGS([
            (['id'], {'help': 'logging instance id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {'instance-id.N': [oid]}
        elif self.is_name(oid):
            data = {'InstanceName': oid}
        uri = '%s/loggingservices/instance/describeinstances' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeLoggingInstancesResponse', default={})

        if len(res.get('instanceInfo')) > 0:
            res = dict_get(res, 'instanceInfo.0')
            self.app.render(res, details=True, maxsize=400)

    @ex(
        help='create a logging instance',
        description='create a logging instance',
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

        uri = '%s/loggingservices/instance/createinstance' % self.baseuri
        res = self.cmp_post(uri, data={'instance': data}, timeout=600)
        uuid = dict_get(res, 'CreateLoggingInstanceResponse.instanceId')
        self.wait_for_service(uuid)
        self.app.render({'msg': 'Add logging instance %s' % uuid})

    @ex(
        help='delete a logging instance',
        description='delete a logging instance',
        arguments=ARGS([
            (['instance_id'], {'help': 'logging instance id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        logging_instance_id = self.app.pargs.instance_id
        uri = '%s/loggingservices/instance/deleteteinstance' % self.baseuri
        self.cmp_delete(uri, data={'InstanceId': logging_instance_id},
                        entity='logging instance %s' % logging_instance_id)
        self.wait_for_service(logging_instance_id, accepted_state='DELETED')

    #
    # action
    #
    @ex(
        help='enable logging module',
        description='enable logging module',
        arguments=ARGS([
            (['instance_id'], {'help': 'logging instance id', 'action': 'store', 'type': str}),
            (['conf'], {'help': 'module configuration', 'action': 'store', 'type': str}),
        ])
    )
    def enable_module(self):
        instance_id = self.app.pargs.instance_id
        conf = self.app.pargs.conf
        uri = '%s/loggingservices/instance/enablelogconfig' % self.baseuri
        self.cmp_put(uri, data={'InstanceId': instance_id, 'Config': conf})
        self.app.render({'msg': 'enable logging module %s' % conf})

    @ex(
        help='disable logging module',
        description='disable logging module',
        arguments=ARGS([
            (['instance_id'], {'help': 'logging instance id', 'action': 'store', 'type': str}),
            (['conf'], {'help': 'module configuration', 'action': 'store', 'type': str}),
        ])
    )
    def disable_module(self):
        instance_id = self.app.pargs.instance_id
        conf = self.app.pargs.conf
        uri = '%s/loggingservices/instance/disablelogconfig' % self.baseuri
        self.cmp_put(uri, data={'InstanceId': instance_id, 'Config': conf})
        self.app.render({'msg': 'disable logging module %s' % conf})


class LoggingServiceSpaceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'logaas'
        stacked_type = 'nested'
        label = 'spaces'
        description = "logging space service management"
        help = "logging space service management"

        cmp = {'baseuri': '/v1.0/nws', 'subsystem': 'service'}

    @ex(
        help='list logging spaces',
        description='list logging spaces',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-name'], {'help': 'list of logging instances id comma separated', 'action': 'store', 'type': str,
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
        uri = '%s/loggingservices/spaces/describespaces' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeSpacesResponse')

        total = res.get('spaceTotal')
        res = res.get('spaceInfo', [])
        resp = {
            'count': len(res),
            'page': page,
            'total': total,
            'sort': {
                'field': 'date.creation', 
                'order': 'desc'
            },
            'spaces': res
        } 

        headers = ['id', 'name', 'status', 'account', 'template', 'creation', 'endpoint']
        fields = ['id', 'name', 'state', 'ownerAlias', 'templateName', 'creationDate', 'endpoints.home']
        transform = {}
        self.app.render(resp, key='spaces', headers=headers, fields=fields, maxsize=100, transform=transform)

    @ex(
        help='get logging space',
        description='get logging space',
        arguments=ARGS([
            (['id'], {'help': 'space id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {'space-id.N': [oid]}   # logging-space-id
        elif self.is_name(oid):
            data = {'SpaceName': oid}
        uri = '%s/loggingservices/spaces/describespaces' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeSpacesResponse', default={})

        if len(res.get('spaceInfo')) > 0:
            if self.is_output_text():
                res = dict_get(res, 'spaceInfo.0')
                dashboards = res.pop('dashboards', [])
                self.app.render(res, details=True, maxsize=400)

                self.c('\ndashboards', 'underline')
                headers = ['id', 'name', 'endpoint']
                fields = ['dashboardId', 'dashboardName', 'endpoint']
                self.app.render(dashboards, headers=headers, fields=fields, maxsize=400)
            else:
                self.app.render(res, details=True, maxsize=400)

    @ex(
        help='create a logging space',
        description='create a logging space',
        arguments=ARGS([
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['-name'], {'help': 'space name', 'action': 'store', 'type': str, 'default': None}),
            (['-definition'], {'help': 'service definition of the space', 'action': 'store', 'type': str, 'default': None}),
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

        uri = '%s/loggingservices/spaces/createspace' % self.baseuri
        res = self.cmp_post(uri, data={'space': data}, timeout=600)

        createSpaceResponse = dict_get(res, 'CreateSpaceResponse')
        spaceId = dict_get(createSpaceResponse, 'spaceId')
        self.wait_for_service(spaceId)
        self.app.render({'msg': 'Add logging space %s' % spaceId})

    @ex(
        help='delete a logging space',
        description='delete a logging space',
        arguments=ARGS([
            (['logging_space_id'], {'help': 'logging space id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        logging_space_id = self.app.pargs.logging_space_id
        uri = '%s/loggingservices/spaces/deletespace' % self.baseuri
        self.cmp_delete(uri, data={'SpaceId': logging_space_id}, entity='logging space %s' % logging_space_id)
        self.wait_for_service(logging_space_id, accepted_state='DELETED')

    @ex(
        help='synchronize users of logging space',
        description='synchronize users of logging space',
        arguments=ARGS([
            (['logging_space_id'], {'help': 'logging space id', 'action': 'store', 'type': str}),
        ])
    )
    def sync_users(self):
        logging_space_id = self.app.pargs.logging_space_id
        uri = '%s/loggingservices/spaces/syncspaceusers' % (self.baseuri)
        self.cmp_put(uri, data={'SpaceId': logging_space_id})
        self.app.render({'msg': 'sync space %s users' % logging_space_id})
