# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte
# (C) Copyright 2020-2021 CSI-Piemonte

from beecell.simple import set_request_params
from beehive3_cli.core.controller import BaseController, PARGS, ARGS
from cement import ex


class SshGatewayResourceController(BaseController):
    """ controller for the sshgateway resources """
    class Meta:
        """ sshgateway controller meta class """
        label = 'res_sshgateway'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'ssh gateway orchestrator'
        help = 'ssh gateway orchestrator'

        cmp = {'baseuri': '/v1.0/nrs/sshgateway', 'subsystem': 'resource'}

        headers = ['id', 'uuid', 'name', 'desc', 'ext_id', 'parent', 'container', 'state']
        fields = ['id', 'uuid', 'name', 'desc', 'ext_id', 'parent', 'container', 'state']


    def pre_command_run(self):
        super(SshGatewayResourceController, self).pre_command_run()
        self.configure_cmp_api_client()


    @ex(
        help='get configuration',
        description='get configuration',
        arguments=PARGS([
            (['-id'], {'help': 'configuration id', 'action': 'store',
                        'type': str, 'default': None}),
        ])
    )
    def configuration_get(self):
        """ list ssh gateway configurations, or
        get ssh gateway configuration by id """
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = f'{self.baseuri}/configuration/{oid}'
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('configuration')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f'{self.baseuri}/configuration'
            res = self.cmp_get(uri, data=data)
            list_headers = ['id', 'uuid', 'name', 'desc', 'container', 'state',
                        'gateway_type','res_id','ip']
            list_fields = [ 'id', 'uuid', 'name', 'desc', 'container', 'state',
                        'details.gw_type','details.res_id','details.ip']
            self.app.render(res, key='configurations',
                            headers=list_headers,
                            fields=list_fields)


    @ex(
        help='add configuration',
        description='add configuration',
        arguments=ARGS([
            (['container'], {'help': 'container uuid', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'configuration name', 'action': 'store', 'type': str, 'default': None}),
            (['gw_type'], {'metavar':'gw_type','help': 'ssh gateway type (gw_dbaas,gw_cpaas,gw_ext)', 'choices':['gw_dbaas','gw_cpaas','gw_ext'],'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'configuration description', 'action': 'store', 'type': str, 'default': None}),
            (['-res_id'], {'help': 'resource uuid of the destination cli object','action':'store','type':str,'default':None}),
            (['-ip'], {'help': 'ip and port. only if gw_type=gw_ext','action':'store','type':str,'default':None})
        ])
    )
    def configuration_add(self):
        """ create a new sshgw configuration resource """
        if self.app.pargs.gw_type != 'gw_ext' and self.app.pargs.res_id is None:
            self.app.pargs.ip = None
            self.app.error('you need to specify -res_id for the chosen value of gw_type')
            return
        
        if self.app.pargs.gw_type == 'gw_ext' and self.app.pargs.ip is None:
            self.app.pargs.res_id = None
            self.app.error('you need to specify -ip for the chosen value of gw_type')
            return
        
        configuration = {}
        configuration.update(set_request_params(self.app.pargs, ['container','name','desc','gw_type','res_id','ip']))
        data = {
            "configuration":configuration
        }
        uri = f'{self.baseuri}/configuration'
        res = self.cmp_post(uri, data=data)
        transform = {'msg': lambda x: self.color_string(x,'GREEN')}
        self.app.render({'msg': f'Created configuration {res["uuid"]}'},transform=transform)


    @ex(
        help='update configuration',
        description='update configuration',
        arguments=ARGS([
            (['id'], {'help': 'resource entity id', 'action': 'store', 'type': str}),
            (['-name'], {'help': 'resource entity name', 'action': 'store',
                         'type': str, 'default': None}),
            (['-desc'], {'help': 'resource entity description', 'action': 'store',
                         'type': str, 'default': None})
        ])
    )
    def configuration_update(self):
        """ update sshgw configuration (name and/or desc) """
        oid = self.app.pargs.id
        data = set_request_params(self.app.pargs, ['name', 'desc'])
        uri = f'{self.baseuri}/configuration/{oid}'
        res = self.cmp_put(uri, data={'configuration': data})
        transform = {'msg': lambda x: self.color_string(x,'GREEN')}
        if res.get('uuid',None):
            self.app.render({'msg': f'Updated configuration {res["uuid"]}'},transform=transform)
        else:
            self.app.render({'msg': f'Updated configuration {oid}'},transform=transform)

    @ex(
        help='delete configurations',
        description='delete configurations',
        arguments=ARGS([
            (['ids'], {'help': 'comma separated configuration ids', 'action': 'store', 'type': str}),
        ])
    )
    def configuration_delete(self):
        """ delete (expunge) sshgw configuration """
        oids = self.app.pargs.ids.split(',')

        transform = {'msg': lambda x: self.color_string(x,'GREEN')}
        for oid in oids:
            uri = f'{self.baseuri}/configuration/{oid}?'
            res = self.cmp_delete(uri, entity=f'configuration {oid}',output=False)
            if res.get('uuid',None):
                self.app.render({'msg': f'Deleted configuration {res["uuid"]}'},transform=transform)
            else:
                self.app.render({'msg': f'Deleted configuration {oid}'},transform=transform)


    @ex(
        help='add port specification',
        description='add port specification',
        arguments=ARGS([
            (['container'], {'help': 'container uuid', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'port spec name', 'action': 'store', 'type': str, 'default': None}),
            (['desc'], {'help': 'port spec description', 'action': 'store', 'type': str, 'default': None}),
            (['configuration'], {'help': 'ssh gw configuration uuid', 'action': 'store', 'type': str, 'default': None}),
            (['-allowed_ports'], {'help': 'comma separated list of ranges (start-end) or single ports. e.g. 8000-9000,22','action':'store','type':str,'default':None}),
            (['-forbidden_ports'], {'help': 'comma separated list of ranges (start-end) or single ports. e.g. 8000-9000,22','action':'store','type':str,'default':None}),
        ])
    )
    def portspec_add(self):
        """ create a new sshgw port specification resource """
        if self.app.pargs.allowed_ports is None:
            self.app.error('Specify at least one port with the -allowed_ports parameter.')
            return

        portspec = {}
        portspec.update(set_request_params(self.app.pargs, ['container','configuration','name','desc','allowed_ports','forbidden_ports']))

        if portspec.get('allowed_ports',None):
            portspec['allowed_ports'] = portspec['allowed_ports'].split(',')

        if portspec.get('forbidden_ports',None):
            portspec['forbidden_ports'] = portspec['forbidden_ports'].split(',')
            
        data = {
            "portspecification":portspec
        }
        uri = f'{self.baseuri}/portspec'
        res = self.cmp_post(uri, data=data)
        transform = {'msg': lambda x: self.color_string(x,'GREEN')}
        self.app.render({'msg': f'Created port specification {res["uuid"]}'},transform=transform)

    
    @ex(
        help='get port specification',
        description='get port specification',
        arguments=PARGS([
            (['-id'], {'help': 'port specification id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def portspec_get(self):
        """ list ssh gateway port specifications, or
        get ssh gateway port specification by id """
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = f'{self.baseuri}/portspec/{oid}'
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get('portspecification')
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f'{self.baseuri}/portspec'
            res = self.cmp_get(uri, data=data)
            ps_list_headers = [ 'id', 'uuid', 'name', 'desc', 'container', 'state',
                                'allowed_ports','forbidden_ports']
            ps_list_fields = [  'id', 'uuid', 'name', 'desc', 'container', 'state',
                                'details.allowed_ports','details.forbidden_ports']
            self.app.render(res, key='portspecifications', headers=ps_list_headers, fields=ps_list_fields)


    @ex(
        help='delete port specifications',
        description='delete port specifications',
        arguments=ARGS([
            (['ids'], {'help': 'comma separated configuration ids', 'action': 'store', 'type': str}),
        ])
    )
    def portspec_delete(self):
        """ delete (expunge) sshgw port specification """
        oids = self.app.pargs.ids.split(',')

        transform = {'msg': lambda x: self.color_string(x,'GREEN')}
        for oid in oids:
            uri = f'{self.baseuri}/portspecification/{oid}?'
            res = self.cmp_delete(uri, entity=f'portspecification {oid}',output=False)
            if res.get('uuid',None):
                self.app.render({'msg': f'Deleted portspecification {res["uuid"]}'},transform=transform)
            else:
                self.app.render({'msg': f'Deleted portspecification {oid}'},transform=transform)