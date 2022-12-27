# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from beecell.types.type_dict import dict_get
from beehive3_cli.core.controller import ARGS
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild


class NetaaServiceController(BusinessControllerChild):
    class Meta:
        label = 'netaas'
        description = "network service management"
        help = "network service management"

    @ex(
        help='get network service info',
        description='get network service info',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def info(self):
        account = self.app.pargs.account
        account = self.get_account(account).get('uuid')
        data = {'owner-id': account}
        uri = '%s/networkservices' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, 'DescribeNetworkResponse.networkSet.0')
        self.app.render(res, details=True, maxsize=100)

    @ex(
        help='get network service quotas',
        description='get network service quotas',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def quotas(self):
        account = self.app.pargs.account
        account = self.get_account(account).get('uuid')
        data = {'owner-id': account}
        uri = '%s/networkservices/describeaccountattributes' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, 'DescribeAccountAttributesResponse.accountAttributeSet')
        headers = ['name', 'value', 'used']
        fields = ['attributeName', 'attributeValueSet.0.item.attributeValue',
                  'attributeValueSet.0.item.nvl-attributeUsed']
        self.app.render(res, headers=headers, fields=fields)

    @ex(
        help='get network service availibility zones',
        description='get network service availibility zones',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
        ])
    )
    def availability_zones(self):
        account = self.app.pargs.account
        account = self.get_account(account).get('uuid')
        data = {'owner-id': account}
        # uri = '%s/networkservices/describeavailabilityzones' % self.baseuri
        uri = '%s/computeservices/describeavailabilityzones' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = dict_get(res, 'DescribeAvailabilityZonesResponse.availabilityZoneInfo')
        headers = ['name', 'state', 'region', 'message']
        fields = ['zoneName', 'zoneState', 'regionName', 'messageSet.0.message']
        self.app.render(res, headers=headers, fields=fields)


class VpcNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'netaas'
        stacked_type = 'nested'
        label = 'vpcs'
        description = "virtual private cloud network service management"
        help = "virtual private cloud network service management"

    @ex(
        help='get private cloud networks',
        description='get private cloud networks',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-ids'], {'help': 'list of private cloud network id comma separated', 'action': 'store', 'type': str,
                        'default': None}),
            (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['accounts', 'ids', 'tags']
        mappings = {
            'accounts': self.get_account_ids,
            'tags': lambda x: x.split(','),
            'ids': lambda x: x.split(',')
        }
        aliases = {
            'accounts': 'owner-id.N',
            'ids': 'vpc-id.N',
            'tags': 'tag-value.N',
            'size': 'Nvl-MaxResults',
            'page': 'Nvl-NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '%s/computeservices/vpc/describevpcs' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeVpcsResponse')
        page = self.app.pargs.page
        for item in res.get('vpcSet'):
            item['cidr'] = ['%s' % (i['cidrBlock']) for i in item['cidrBlockAssociationSet']]
            item['cidr'] = ', '.join(item['cidr'])
        resp = {
            'count': len(res.get('vpcSet')),
            'page': page,
            'total': res.get('nvl-vpcTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'instances': res.get('vpcSet')
        }

        headers = ['id', 'name', 'state',  'account', 'cidr', 'subnet_cidrs', 'tenancy']
        fields = ['vpcId', 'nvl-name', 'state', 'nvl-vpcOwnerAlias', 'cidrBlock', 'cidr', 'instanceTenancy']
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=60)

    @ex(
        help='add virtual private cloud',
        description='add virtual private cloud',
        arguments=ARGS([
            (['name'], {'help': 'vpc name', 'action': 'store', 'type': str}),
            (['account'], {'help': 'account id', 'action': 'store', 'type': str}),
            (['cidr_block'], {'help': 'vpc cidr block', 'action': 'store', 'type': str}),
            (['-template'], {'help': 'vpc template', 'action': 'store', 'type': str, 'default': None}),
            (['-tenancy'], {'help': 'allowed tenancy of instances launched into the VPC. Use default for shared vpc. '
                                    'Use dedicated for private vpc. default is dedicated', 'action': 'store',
                            'type': str, 'default': 'dedicated'})
        ])
    )
    def add(self):
        data = {
            'VpcName': self.app.pargs.name,
            'owner_id': self.get_account(self.app.pargs.account).get('uuid'),
            'VpcType': self.app.pargs.template,
            'CidrBlock': self.app.pargs.cidr_block,
            'InstanceTenancy': self.app.pargs.tenancy
        }
        uri = '%s/computeservices/vpc/createvpc' % self.baseuri
        res = self.cmp_post(uri, data={'vpc': data}, timeout=600)
        res = res.get('CreateVpcResponse').get('vpc').get('vpcId')
        self.wait_for_service(res)
        self.app.render({'msg': 'add vpc %s' % res})

    @ex(
        help='delete a vpc',
        description='delete a vpc',
        arguments=ARGS([
            (['vpc'], {'help': 'vpc id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.vpc
        data = {
            'force': False,
            'propagate': True
        }
        uri = '/v2.0/nws/serviceinsts/%s' % oid
        self.wait_for_service(oid, accepted_state='DELETED')
        self.cmp_delete(uri, data=data, timeout=180, entity='vpc %s' % oid)

    @ex(
        help='get vpc templates',
        description='get vpc templates',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str, 'default': None}),
            (['-id'], {'help': 'template id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def templates(self):
        self.get_service_definitions('ComputeVPC')


class SubnetNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'netaas'
        stacked_type = 'nested'
        label = 'subnets'
        description = "vpc subnet service management"
        help = "vpc subnet service management"

    @ex(
        help='get vpc subnets',
        description='get vpc subnets',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-ids'], {'help': 'list of subnet id comma separated', 'action': 'store', 'type': str,
                        'default': None}),
            (['-vpcs'], {'help': 'list of vpc id comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['accounts', 'ids', 'tags', 'vpcs']
        mappings = {
            'accounts': self.get_account_ids,
            'tags': lambda x: x.split(','),
            'ids': lambda x: x.split(','),
            'vpcs': lambda x: x.split(',')
        }
        aliases = {
            'accounts': 'owner-id.N',
            'ids': 'subnet-id.N',
            'vpcs': 'vpc-id.N',
            'size': 'Nvl-MaxResults',
            'page': 'Nvl-NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '%s/computeservices/subnet/describesubnets' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeSubnetsResponse')
        page = self.app.pargs.page
        resp = {
            'count': len(res.get('subnetSet')),
            'page': page,
            'total': res.get('nvl-subnetTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'instances': res.get('subnetSet')
        }

        headers = ['id', 'name', 'state',  'account', 'availabilityZone', 'vpc', 'cidr']
        fields = ['subnetId', 'nvl-name', 'state', 'nvl-subnetOwnerAlias', 'availabilityZone', 'nvl-vpcName',
                  'cidrBlock']
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40)

    @ex(
        help='add virtual private cloud subnet',
        description='add virtual private cloud subnet',
        arguments=ARGS([
            (['name'], {'help': 'subnet name', 'action': 'store', 'type': str}),
            (['vpc'], {'help': 'vpc id', 'action': 'store', 'type': str}),
            (['cidr_block'], {'help': 'subnet cidr block', 'action': 'store', 'type': str}),
            (['zone'], {'help': 'availability zone', 'action': 'store', 'type': str}),
            (['-template'], {'help': 'subnet template', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def add(self):
        data = {
            'SubnetName': self.app.pargs.name,
            'VpcId': self.app.pargs.vpc,
            'Nvl_SubnetType': self.app.pargs.template,
            'CidrBlock': self.app.pargs.cidr_block,
            'AvailabilityZone': self.app.pargs.zone
        }
        uri = '%s/computeservices/subnet/createsubnet' % self.baseuri
        res = self.cmp_post(uri, data={'subnet': data}, timeout=600)
        res = res.get('CreateSubnetResponse').get('subnet').get('subnetId')
        self.wait_for_service(res)
        self.app.render({'msg': 'add subnet %s' % res})

    @ex(
        help='delete a subnet',
        description='delete a subnet',
        arguments=ARGS([
            (['subnet'], {'help': 'subnet id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.subnet
        data = {
            'force': False,
            'propagate': True
        }
        uri = '/v2.0/nws/serviceinsts/%s' % oid
        self.wait_for_service(oid, accepted_state='DELETED')
        self.cmp_delete(uri, data=data, timeout=180, entity='vpc subnet %s' % oid)

    @ex(
        help='get vpc templates',
        description='get vpc templates',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str, 'default': None}),
            (['-id'], {'help': 'template id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def templates(self):
        self.get_service_definitions('ComputeSubnet')


class SecurityGroupNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'netaas'
        stacked_type = 'nested'
        label = 'securitygroups'
        description = "security groups service management"
        help = "security groups service management"

    @ex(
        help='get security group templates',
        description='get security group templates',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str, 'default': None}),
            (['-id'], {'help': 'template id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def templates(self):
        self.get_service_definitions('ComputeSecurityGroup')

    @ex(
        help='create a security group',
        description='create a security group',
        arguments=ARGS([
            (['name'], {'help': 'security group name', 'action': 'store', 'type': str}),
            (['vpc'], {'help': 'parent vpc', 'action': 'store', 'type': str}),
            (['-template'], {'help': 'template id', 'action': 'store', 'type': str}),
        ])
    )
    def add(self):
        data = {
            'GroupName': self.app.pargs.name,
            'VpcId': self.app.pargs.vpc
        }
        sg_type = self.app.pargs.template
        if sg_type is not None:
            data['GroupType'] = sg_type
        uri = '%s/computeservices/securitygroup/createsecuritygroup' % self.baseuri
        res = self.cmp_post(uri, data={'security_group': data}, timeout=600)
        res = dict_get(res, 'CreateSecurityGroupResponse.groupId')
        self.wait_for_service(res)
        self.app.render({'msg': 'Add securitygroup %s' % res})

    @ex(
        help='get security groups',
        description='get security groups',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-ids'], {'help': 'list of security group id comma separated', 'action': 'store', 'type': str,
                        'default': None}),
            (['-vpcs'], {'help': 'list of vpc id comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['accounts', 'ids', 'tags', 'vpcs']
        mappings = {
            'accounts': self.get_account_ids,
            'tags': lambda x: x.split(','),
            'vpcs': lambda x: x.split(','),
            'ids': lambda x: x.split(',')
        }
        aliases = {
            'accounts': 'owner-id.N',
            'ids': 'group-id.N',
            'tags': 'tag-key.N',
            'vpcs': 'vpc-id.N',
            'size': 'MaxResults',
            'page': 'NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '%s/computeservices/securitygroup/describesecuritygroups' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeSecurityGroupsResponse', {})
        page = self.app.pargs.page

        for item in res.get('securityGroupInfo'):
            item['egress_rules'] = len(item['ipPermissionsEgress'])
            item['ingress_rules'] = len(item['ipPermissions'])

        resp = {
            'count': len(res.get('securityGroupInfo')),
            'page': page,
            'total': res.get('nvl-securityGroupTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'instances': res.get('securityGroupInfo')
        }

        headers = ['id', 'name', 'state',  'account', 'vpc', 'egress_rules', 'ingress_rules']
        fields = ['groupId', 'groupName', 'nvl-state', 'nvl-sgOwnerAlias', 'nvl-vpcName', 'egress_rules',
                  'ingress_rules']
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40)

    def __format_rule(self, rules):
        for rule in rules:
            if rule['ipProtocol'] == '-1':
                rule['ipProtocol'] = '*'
            if rule.get('fromPort', None) is None or rule['fromPort'] == '-1':
                rule['fromPort'] = '*'
            if rule.get('toPort', None) is None or rule['toPort'] == '-1':
                rule['toPort'] = '*'
            if len(rule.get('groups', None)) > 0:
                group = rule['groups'][0]
                rule['groups'] = '%s:%s [%s]' % (group.get('nvl-userName', None), group['groupName'], group['groupId'])
            else:
                rule['groups'] = ''
            if len(rule.get('ipRanges', None)) > 0:
                cidr = rule['ipRanges'][0]
                rule['ipRanges'] = '%s' % cidr['cidrIp']
            else:
                rule['ipRanges'] = ''
        return rules

    @ex(
        help='get security group with rules',
        description='get security group with rules',
        arguments=ARGS([
            (['securitygroup'], {'help': 'securitygroup id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        securitygroup = self.app.pargs.securitygroup
        data = {'GroupName.N': [securitygroup]}
        uri = '%s/computeservices/securitygroup/describesecuritygroups' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeSecurityGroupsResponse.securityGroupInfo', default={})
        if len(res) == 0:
            raise Exception('security group %s does not exist' % securitygroup)
        res = res[0]
        if self.is_output_text():
            egress_rules = self.__format_rule(res.pop('ipPermissionsEgress'))
            ingress_rules = self.__format_rule(res.pop('ipPermissions'))
            fields = ['groups', 'ipRanges', 'ipProtocol', 'fromPort', 'toPort', 'nvl-reserved', 'nvl-state']
            self.app.render(res, details=True, maxsize=200)
            self.c('\negress rules', 'underline')
            headers = ['toSecuritygroup', 'toCidr', 'protocol', 'fromPort', 'toPort', 'reserved', 'state']
            self.app.render(egress_rules, headers=headers, fields=fields, maxsize=80)
            self.c('\ningress rules', 'underline')
            headers = ['fromSecuritygroup', 'fromCidr', 'protocol', 'fromPort', 'toPort', 'reserved', 'state']
            self.app.render(ingress_rules, headers=headers, fields=fields, maxsize=80)
        else:
            self.app.render(res, details=True, maxsize=200)

    @ex(
        help='patch a security group',
        description='patch a security group',
        arguments=ARGS([
            (['securitygroup'], {'help': 'securitygroup id', 'action': 'store', 'type': str}),
        ])
    )
    def patch(self):
        securitygroup = self.app.pargs.securitygroup
        data = {'GroupName': securitygroup}
        uri = '%s/computeservices/securitygroup/patchsecuritygroup' % self.baseuri
        res = self.cmp_patch(uri,  data={'security_group': data}, timeout=600)
        res = dict_get('PatchSecurityGroupResponse.instancesSet.0.groupId')
        self.app.render({'msg': 'Patch securitygroup %s' % res})

    @ex(
        help='delete a security group',
        description='delete a security group',
        arguments=ARGS([
            (['securitygroup'], {'help': 'securitygroup id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.securitygroup
        data = {'GroupName': oid}
        uri = '%s/computeservices/securitygroup/deletesecuritygroup' % self.baseuri
        self.cmp_delete(uri, data={'security_group': data}, timeout=600, entity='securitygroup %s' % oid)
        self.wait_for_service(oid, accepted_state='DELETED')

    @ex(
        help='add a security group rule',
        description='add a security group rule',
        arguments=ARGS([
            (['type'], {'help': 'egress or ingress. For egress rule the destination. For ingress rule specify the '
                                'source', 'action': 'store', 'type': str}),
            (['securitygroup'], {'help': 'securitygroup id', 'action': 'store', 'type': str}),
            (['-proto'], {'help': 'protocol. can be tcp, udp, icmp or -1 for all', 'action': 'store',
                          'type': str, 'default': None}),
            (['-port'], {'help': 'can be an integer between 0 and 65535 or a range with start and end in the same '
                                 'interval. Range format is <start>-<end>. Use -1 for all ports. Set subprotocol if '
                                 'proto is icmp (8 for ping)',
                         'action': 'store', 'type': str, 'default': None}),
            (['-dest'], {'help': 'rule destination. Syntax <type>:<value>. Destination type can be SG, CIDR. For SG '
                                 'value must be <sg_id>. For CIDR value should like 10.102.167.0/24.',
                         'action': 'store', 'type': str, 'default': None}),
            (['-source'], {'help': 'rule source. Syntax <type>:<value>. Source type can be SG, CIDR. For SG '
                                   'value must be <sg_id>. For CIDR value should like 10.102.167.0/24.',
                           'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def add_rule(self):
        rule_type = self.app.pargs.type
        group_id = self.app.pargs.securitygroup
        dest = self.app.pargs.dest
        source = self.app.pargs.source
        port = self.app.pargs.port
        proto = self.app.pargs.proto
        from_port = -1
        to_port = -1
        if port is not None:
            port = str(port)
            port = port.split('-')
            if len(port) == 1:
                from_port = to_port = port[0]
            else:
                from_port, to_port = port

        if proto is None:
            proto = '-1'

        if rule_type not in ['ingress', 'egress']:
            raise Exception('rule type must be ingress or egress')
        if rule_type == 'ingress':
            if source is None:
                raise Exception('ingress rule require source')
            dest = source.split(':')
        elif rule_type == 'egress':
            if dest is None:
                raise Exception('egress rule require destination')
            dest = dest.split(':')
        if dest[0] not in ['SG', 'CIDR']:
            raise Exception('source/destination type must be SG or CIDR')
        data = {
            'GroupName': group_id,
            'IpPermissions.N': [
                {
                    'FromPort': from_port,
                    'ToPort': to_port,
                    'IpProtocol': proto
                }
            ]
        }
        if dest[0] == 'SG':
            data['IpPermissions.N'][0]['UserIdGroupPairs'] = [{
                'GroupName': dest[1]
            }]
        elif dest[0] == 'CIDR':
            data['IpPermissions.N'][0]['IpRanges'] = [{
                'CidrIp': dest[1]
            }]
        else:
            raise Exception('Wrong rule type')

        if rule_type == 'egress':
            uri = '%s/computeservices/securitygroup/authorizesecuritygroupegress' % self.baseuri
            key = 'AuthorizeSecurityGroupEgressResponse'
        elif rule_type == 'ingress':
            uri = '%s/computeservices/securitygroup/authorizesecuritygroupingress' % self.baseuri
            key = 'AuthorizeSecurityGroupIngressResponse'
        res = self.cmp_post(uri, data={'rule': data}, timeout=600, task_key=key)
        res = res.get(key).get('Return')
        self.app.render('create securitygroup rule %s' % res)

    @ex(
        help='delete a security group rule',
        description='delete a security group rule',
        arguments=ARGS([
            (['type'], {'help': 'egress or ingress. For egress rule the destination. For ingress rule specify the '
                                'source', 'action': 'store', 'type': str}),
            (['securitygroup'], {'help': 'securitygroup id', 'action': 'store', 'type': str}),
            (['-proto'], {'help': 'protocol. can be tcp, udp, icmp or -1 for all', 'action': 'store',
                          'type': str, 'default': None}),
            (['-port'], {'help': 'can be an integer between 0 and 65535 or a range with start and end in the same '
                                 'interval. Range format is <start>-<end>. Use -1 for all ports. Set subprotocol if '
                                 'proto is icmp (8 for ping)',
                         'action': 'store', 'type': str, 'default': None}),
            (['-dest'], {'help': 'rule destination. Syntax <type>:<value>. Destination type can be SG, CIDR. For SG '
                                 'value must be <sg_id>. For CIDR value should like 10.102.167.0/24.',
                         'action': 'store', 'type': str, 'default': None}),
            (['-source'], {'help': 'rule source. Syntax <type>:<value>. Source type can be SG, CIDR. For SG '
                                   'value must be <sg_id>. For CIDR value should like 10.102.167.0/24.',
                           'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def del_rule(self):
        rule_type = self.app.pargs.type
        group_id = self.app.pargs.securitygroup
        dest = self.app.pargs.dest
        source = self.app.pargs.source
        port = self.app.pargs.port
        proto = self.app.pargs.proto
        from_port = -1
        to_port = -1
        if port is not None:
            port = str(port)
            port = port.split('-')
            if len(port) == 1:
                from_port = to_port = port[0]
            else:
                from_port, to_port = port

        if proto is None:
            proto = '-1'

        if rule_type not in ['ingress', 'egress']:
            raise Exception('rule type must be ingress or egress')
        if rule_type == 'ingress':
            if source is None:
                raise Exception('ingress rule require source')
            dest = source.split(':')
        elif rule_type == 'egress':
            if dest is None:
                raise Exception('egress rule require destination')
            dest = dest.split(':')
        if dest[0] not in ['SG', 'CIDR']:
            raise Exception('source/destination type must be SG or CIDR')
        data = {
            'GroupName': group_id,
            'IpPermissions.N': [
                {
                    'FromPort': from_port,
                    'ToPort': to_port,
                    'IpProtocol': proto
                }
            ]
        }
        if dest[0] == 'SG':
            data['IpPermissions.N'][0]['UserIdGroupPairs'] = [{'GroupName': dest[1]}]
        elif dest[0] == 'CIDR':
            data['IpPermissions.N'][0]['IpRanges'] = [{'CidrIp': dest[1]}]
        else:
            raise Exception('wrong rule type')

        if rule_type == 'egress':
            uri = '%s/computeservices/securitygroup/revokesecuritygroupegress' % self.baseuri
            key = 'RevokeSecurityGroupEgressResponse'
        elif rule_type == 'ingress':
            uri = '%s/computeservices/securitygroup/revokesecuritygroupingress' % self.baseuri
            key = 'RevokeSecurityGroupIngressResponse'
        res = self.cmp_delete(uri, data={'rule': data}, timeout=600, entity='securitygroup rule', task_key=key)


class GatewayNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'netaas'
        stacked_type = 'nested'
        label = 'internet_gateways'
        description = "gateways service management"
        help = "gateways service management"

    @ex(
        help='get gateway templates',
        description='get gateway templates',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str, 'default': None}),
            (['-id'], {'help': 'template id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def templates(self):
        self.get_service_definitions('NetworkGateway')

    @ex(
        help='create a gateway',
        description='create a gateway',
        arguments=ARGS([
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['-template'], {'help': 'template id', 'action': 'store', 'type': str}),
        ])
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get('uuid')
        data = {
            'owner-id': account
        }
        gateway_type = self.app.pargs.template
        if gateway_type is not None:
            data['Nvl_GatewayType'] = gateway_type
        uri = '%s/networkservices/gateway/createinternetgateway' % self.baseuri
        res = self.cmp_post(uri, data={'gateway': data}, timeout=600)
        res = dict_get(res, 'CreateInternetGatewayResponse.internetGateway.internetGatewayId')
        self.app.render({'msg': 'add gateway %s' % res})

    @ex(
        help='get gateways',
        description='get gateways',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-ids'], {'help': 'list of gateway id comma separated', 'action': 'store', 'type': str,
                        'default': None}),
            (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['accounts', 'ids', 'tags']
        mappings = {
            'accounts': self.get_account_ids,
            'tags': lambda x: x.split(','),
            'ids': lambda x: x.split(',')
        }
        aliases = {
            'accounts': 'owner-id.N',
            'ids': 'InternetGatewayId.N',
            'tags': 'tag-key.N',
            'size': 'MaxResults',
            'page': 'NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '%s/networkservices/gateway/describeinternetgateways' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeInternetGatewaysResponse', {})
        page = self.app.pargs.page

        resp = {
            'count': len(res.get('internetGatewaySet')),
            'page': page,
            'total': res.get('nvl-internetGatewayTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'instances': res.get('internetGatewaySet')
        }

        headers = ['id', 'name', 'state',  'account', 'internal-vpc', 'external-ip-address', 'bastion']
        fields = ['internetGatewayId', 'nvl-name', 'nvl-state', 'nvl-ownerAlias',
                  'attachmentSet.0.VpcSecurityGroupMembership.nvl-vpcName', 'nvl-external_ip_address', 'nvl-bastion']
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40)

    @ex(
        help='get gateway',
        description='get gateway',
        arguments=ARGS([
            (['gateway'], {'help': 'gateway id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        gateway = self.app.pargs.gateway
        data = {'InternetGatewayId.N': [gateway]}
        uri = '%s/networkservices/gateway/describeinternetgateways' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeInternetGatewaysResponse.internetGatewaySet', default={})

        if len(res) == 0:
            raise Exception('gateway %s does not exist' % gateway)
        res = res[0]
        vpcs = res.pop('attachmentSet')
        self.app.render(res, details=True, maxsize=200)
        self.c('\nattached vpcs', 'underline')
        headers = ['id', 'name', 'state']
        fields = ['VpcSecurityGroupMembership.vpcId', 'VpcSecurityGroupMembership.nvl-vpcName',
                  'VpcSecurityGroupMembership.state']
        self.app.render(vpcs, headers=headers, fields=fields, maxsize=80)

    @ex(
        help='patch a gateway',
        description='patch a gateway',
        arguments=ARGS([
            (['gateway'], {'help': 'gateway id', 'action': 'store', 'type': str}),
        ])
    )
    def patch(self):
        gateway = self.app.pargs.gateway
        data = {'GroupName': gateway}
        uri = '%s/networkservices/gateway/patchgateway' % self.baseuri
        res = self.cmp_patch(uri,  data={'gateway': data}, timeout=600)
        res = dict_get(res, 'PatchSecurityGroupResponse.instancesSet.0.groupId')
        self.app.render({'msg': 'Patch gateway %s' % res})

    @ex(
        help='delete a gateway',
        description='delete a gateway',
        arguments=ARGS([
            (['gateway'], {'help': 'gateway id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.gateway
        data = {'InternetGatewayId': oid}
        uri = '%s/networkservices/gateway/deleteinternetgateway' % self.baseuri
        self.cmp_delete(uri, data=data, timeout=600, entity='gateway %s' % oid)

    @ex(
        help='attach vpc from gateway',
        description='attach vpc from gateway',
        arguments=ARGS([
            (['gateway'], {'help': 'gateway id', 'action': 'store', 'type': str}),
            (['vpc'], {'help': 'vpc id', 'action': 'store', 'type': str}),
        ])
    )
    def vpc_attach(self):
        gateway_id = self.app.pargs.gateway
        vpc_id = self.app.pargs.vpc

        data = {
            'InternetGatewayId': gateway_id,
            'VpcId': vpc_id
        }
        uri = '%s/networkservices/gateway/attachinternetgateway' % self.baseuri
        self.cmp_put(uri, data={'gateway': data}, timeout=600)
        self.app.render('attach vpc %s to gateway %s' % (vpc_id, gateway_id))

    @ex(
        help='detach vpc from gateway',
        description='detach vpc from gateway',
        arguments=ARGS([
            (['gateway'], {'help': 'gateway id', 'action': 'store', 'type': str}),
            (['vpc'], {'help': 'vpc id', 'action': 'store', 'type': str}),
        ])
    )
    def vpc_detach(self):
        gateway_id = self.app.pargs.gateway
        vpc_id = self.app.pargs.vpc

        data = {
            'InternetGatewayId': gateway_id,
            'VpcId': vpc_id
        }
        uri = '%s/networkservices/gateway/detachinternetgateway' % self.baseuri
        self.cmp_put(uri, data={'gateway': data}, timeout=600)
        self.app.render('detach vpc %s from gateway %s' % (vpc_id, gateway_id))

    @ex(
        help='get gateway bastion',
        description='get gateway bastion',
        arguments=ARGS([
            (['gateway'], {'help': 'gateway id', 'action': 'store', 'type': str}),
        ])
    )
    def bastion_get(self):
        gateway = self.app.pargs.gateway
        data = {'InternetGatewayId': gateway}
        uri = '%s/networkservices/gateway/describinternetgatewayebastion' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeInternetGatewayBastionResponse.internetGatewayBastion', default={})
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help='create a gateway bastion',
        description='create a gateway bastion',
        arguments=ARGS([
            (['gateway'], {'help': 'gateway id', 'action': 'store', 'type': str}),
        ])
    )
    def bastion_add(self):
        gateway = self.app.pargs.gateway
        data = {'InternetGatewayId': gateway}
        uri = '%s/networkservices/gateway/createinternetgatewaybastion' % self.baseuri
        self.cmp_post(uri, data={'bastion': data}, timeout=600, task_key='CreateInternetGatewayBastionResponse')
        self.app.render({'msg': 'add gateway %s bastion' % gateway})

    @ex(
        help='delete a gateway bastion',
        description='delete a gateway bastion',
        arguments=ARGS([
            (['gateway'], {'help': 'gateway id', 'action': 'store', 'type': str}),
        ])
    )
    def bastion_del(self):
        gateway = self.app.pargs.gateway
        data = {'InternetGatewayId': gateway}
        uri = '%s/networkservices/gateway/deleteinternetgatewaybastion' % self.baseuri
        self.cmp_delete(uri, data={'bastion': data}, timeout=600, task_key='DeleteInternetGatewayBastionResponse',
                        entity='gateway %s bastion' % gateway)


class HealthMonitorNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'netaas'
        stacked_type = 'nested'
        label = 'health_monitors'
        description = "health monitor service management"
        help = "health monitor service management"

    @ex(
        help='get health monitor templates',
        description='get health monitor templates',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str, 'default': None}),
            (['-id'], {'help': 'template id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def templates(self):
        self.get_service_definitions('NetworkHealthMonitor')

    @ex(
        help='list health monitors',
        description='list health monitors',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of comma separated account ids', 'action': 'store', 'type': str,
                             'default': None}),
            (['-ids'], {'help': 'list of comma separated health monitor ids', 'action': 'store', 'type': str,
                        'default': None}),
            (['-tags'], {'help': 'list of comma separated tags', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['accounts', 'ids', 'tags']
        mappings = {
            'accounts': self.get_account_ids,
            'ids': lambda x: x.split(','),
            'tags': lambda x: x.split(',')
        }
        aliases = {
            'accounts': 'owner-id.N',
            'ids': 'HealthMonitorId.N',
            'tags': 'tag-key.N',
            'size': 'MaxResults',
            'page': 'Nvl-NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '%s/networkservices/loadbalancer/healthmonitor/describehealthmonitors' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeHealthMonitorsResponse', {})
        page = self.app.pargs.page

        resp = {
            'count': len(res.get('healthMonitorSet')),
            'page': page,
            'total': res.get('healthMonitorTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'instances': res.get('healthMonitorSet')
        }

        headers = ['uuid', 'name', 'state', 'type', 'account', 'protocol', 'interval', 'timeout', 'max_retries',
                   'method', 'uri', 'expected']
        fields = ['healthMonitorId', 'name', 'state', 'type', 'nvl-ownerAlias', 'protocol', 'interval', 'timeout',
                  'maxRetries', 'method', 'requestURI', 'expected']
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40)

    @ex(
        help='get health monitor',
        description='get health monitor',
        arguments=ARGS([
            (['id'], {'help': 'health monitor id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {'HealthMonitorId.N': [oid]}
        elif self.is_name(oid):
            data = {'HealthMonitorName': oid}
        uri = '%s/networkservices/loadbalancer/healthmonitor/describehealthmonitors' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeHealthMonitorsResponse.healthMonitorSet', default={})
        if len(res) == 0:
            raise Exception('Health monitor %s does not exist' % oid)
        res = res[0]
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help='create health monitor',
        description='create health monitor',
        arguments=ARGS([
            (['name'], {'help': 'monitor name', 'action': 'store', 'type': str}),
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['protocol'], {'metavar': 'protocol', 'help': 'protocol used to perform health checks {http,https,tcp,'
                            'imcp,udp}', 'choices': ['http', 'https', 'tcp', 'imcp', 'udp'], 'action': 'store',
                            'type': str}),
            (['-interval'], {'help': 'interval in seconds in which a server is to be tested', 'action': 'store',
                             'type': int}),
            (['-timeout'], {'help': 'maximum time in seconds in which a response from the server must be received',
                            'action': 'store', 'type': int}),
            (['-max_retries'], {'help': 'maximum number of times the server is tested before it is declared down',
                                'action': 'store', 'type': int}),
            (['-method'], {'metavar': 'method', 'help': 'method to send the health check request to the server',
                           'choices': ['get', 'post', 'options'], 'action': 'store', 'type': str}),
            (['-url'], {'help': 'URL to GET or POST', 'action': 'store', 'type': str}),
            (['-expected'], {'help': 'expected string', 'action': 'store', 'type': str}),
        ])
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get('uuid')
        protocol = self.app.pargs.protocol
        method = self.app.pargs.method
        if method is not None:
            method = method.upper()

        data = {
            'owner-id': account,
            'Name': self.app.pargs.name,
            'Protocol': protocol.upper()
        }

        params = [
            {'key': 'Interval', 'value': self.app.pargs.interval},
            {'key': 'Timeout', 'value': self.app.pargs.timeout},
            {'key': 'MaxRetries', 'value': self.app.pargs.max_retries},
            {'key': 'Method', 'value': method},
            {'key': 'RequestURI', 'value': self.app.pargs.url},
            {'key': 'Expected', 'value': self.app.pargs.expected},
        ]
        for param in params:
            if param.get('value') is not None:
                data[param.get('key')] = param.get('value')

        uri = '%s/networkservices/loadbalancer/healthmonitor/createhealthmonitor' % self.baseuri
        res = self.cmp_post(uri, data={'health_monitor': data}, timeout=600)
        res = dict_get(res, 'CreateHealthMonitorResponse.HealthMonitor.healthMonitorId')
        self.app.render({'msg': 'Add health monitor %s' % res})

    @ex(
        help='delete health monitors',
        description='delete health monitors',
        arguments=ARGS([
            (['ids'], {'help': 'comma separated health monitor ids', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oids = self.app.pargs.ids.split(',')
        for oid in oids:
            data = {'healthMonitorId': oid}
            uri = '%s/networkservices/loadbalancer/healthmonitor/deletehealthmonitor' % self.baseuri
            self.cmp_delete(uri, data=data, timeout=600, entity='Health monitor %s' % oid)


class TargetGroupNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'netaas'
        stacked_type = 'nested'
        label = 'target_groups'
        description = "target group service management"
        help = "target group service management"

    balancing_algorithms = [
        'round-robin',
        'ip-hash',
        'leastconn',
        'uri'
    ]

    target_types = [
        'vm',
        'container'
    ]

    @ex(
        help='get target group templates',
        description='get target group templates',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str, 'default': None}),
            (['-id'], {'help': 'template id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def templates(self):
        self.get_service_definitions('NetworkTargetGroup')

    @ex(
        help='list target groups',
        description='list target groups',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of comma separated account ids', 'action': 'store', 'type': str,
                             'default': None}),
            (['-ids'], {'help': 'list of comma separated target group ids', 'action': 'store', 'type': str,
                        'default': None}),
            (['-tags'], {'help': 'list of comma separated tags', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['accounts', 'ids', 'tags']
        mappings = {
            'accounts': self.get_account_ids,
            'ids': lambda x: x.split(','),
            'tags': lambda x: x.split(',')
        }
        aliases = {
            'accounts': 'owner-id.N',
            'ids': 'TargetGroupId.N',
            'tags': 'tag-key.N',
            'size': 'MaxResults',
            'page': 'Nvl-NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '%s/networkservices/loadbalancer/targetgroup/describetargetgroups' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeTargetGroupsResponse', {})
        page = self.app.pargs.page

        resp = {
            'count': len(res.get('targetGroupSet')),
            'page': page,
            'total': res.get('targetGroupTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'instances': res.get('targetGroupSet')
        }

        headers = ['uuid', 'name', 'state', 'account', 'balancing_algorithm', 'target_type', 'N.targets',
                   'health_monitor']
        fields = ['targetGroupId', 'name', 'state', 'nvl-ownerAlias', 'balancingAlgorithm', 'targetType',
                  'attachmentSet.TargetSet.totalTargets', 'attachmentSet.HealthMonitor.name']
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40)

    @ex(
        help='get target group',
        description='get target group',
        arguments=ARGS([
            (['id'], {'help': 'target group id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {'TargetGroupId.N': [oid]}
        elif self.is_name(oid):
            data = {'TargetGroupName': oid}
        uri = '%s/networkservices/loadbalancer/targetgroup/describetargetgroups' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeTargetGroupsResponse.targetGroupSet', default={})
        if len(res) == 0:
            raise Exception('Target group %s does not exist' % oid)
        res = res[0]
        attachments = res.pop('attachmentSet')
        targets = dict_get(attachments, 'TargetSet.Targets', default=None)
        health_monitor = dict_get(attachments, 'HealthMonitor', default=None)
        self.app.render(res, details=True, maxsize=200)
        self.c('\nattached targets', 'underline')
        if targets is not None and len(targets) > 0:
            headers = ['uuid', 'name', 'state', 'lb_port', 'hm_port', 'site']
            fields = ['id', 'name', 'state', 'lb_port', 'hm_port', 'site']
            self.app.render(targets, headers=headers, fields=fields, maxsize=80)
        self.c('\nattached health monitor', 'underline')
        if health_monitor is not None:
            headers = ['uuid', 'name', 'state', 'type', 'protocol', 'interval', 'timeout', 'max_retries', 'method',
                       'uri', 'expected']
            fields = ['healthMonitorId', 'name', 'state', 'type', 'protocol', 'interval', 'timeout', 'maxRetries',
                      'method', 'requestURI', 'expected']
            self.app.render(health_monitor, headers=headers, fields=fields, maxsize=80)

    @ex(
        help='create empty target group',
        description='create empty target group',
        arguments=ARGS([
            (['name'], {'help': 'target group name', 'action': 'store', 'type': str}),
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['balancing_algorithm'], {'metavar': 'balancing_algorithm', 'help': 'algorithm used to load balance '
                                       'targets {round-robin,ip-hash,leastconn,uri}', 'choices': balancing_algorithms,
                                       'action': 'store', 'type': str}),
            (['target_type'], {'metavar': 'target_type', 'help': 'target type {vm,container}', 'choices': target_types,
                               'action': 'store', 'type': str}),
            (['-desc'], {'help': 'target group description', 'action': 'store', 'type': str}),
            (['-health_monitor'], {'help': 'id of the custom monitor to perform health checks on targets',
                                   'action': 'store', 'type': str})
        ])
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get('uuid')
        data = {
            'owner-id': account,
            'Name': self.app.pargs.name,
            'Description': self.app.pargs.desc,
            'BalancingAlgorithm': self.app.pargs.balancing_algorithm,
            'TargetType': self.app.pargs.target_type,
            'HealthMonitor': self.app.pargs.health_monitor
        }

        uri = '%s/networkservices/loadbalancer/targetgroup/createtargetgroup' % self.baseuri
        res = self.cmp_post(uri, data={'target_group': data}, timeout=600)
        res = dict_get(res, 'CreateTargetGroupResponse.TargetGroup.targetGroupId')
        self.app.render({'msg': 'Add target group %s' % res})

    @ex(
        help='delete target groups',
        description='delete target groups',
        arguments=ARGS([
            (['ids'], {'help': 'comma separated target group ids', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oids = self.app.pargs.ids.split(',')
        for oid in oids:
            data = {'targetGroupId': oid}
            uri = '%s/networkservices/loadbalancer/targetgroup/deletetargetgroup' % self.baseuri
            self.cmp_delete(uri, data=data, timeout=600, entity='Target group %s' % oid)

    @ex(
        help='register targets with target group',
        description='register targets with target group',
        arguments=ARGS([
            (['id'], {'help': 'target group id', 'action': 'store', 'type': str}),
            (['targets'], {'help': 'comma separated list of couples <target_id>:<lb_port> or triplets '
                           '<target_id>:<lb_port>:<hm_port>', 'action': 'store', 'type': str}),
        ])
    )
    def targets_register(self):
        oid = self.app.pargs.id
        targets = self.app.pargs.targets

        data = {
            'TargetGroupId': oid,
            'Targets': []
        }

        # parse targets
        targets = targets.split(',')
        for item in targets:
            target = item.split(':')
            # remove white spaces
            target = [x for x in target if x.strip()]
            if 2 <= len(target) <= 3:
                target_id = target[0]
                target_lb_port = target[1]
                d = {
                    'Id': target_id,
                    'LbPort': int(target_lb_port)
                }
                if len(target) == 3:
                    target_hm_port = target[2]
                    d.update({
                        'HmPort': int(target_hm_port)
                    })
                data['Targets'].append(d)
            else:
                raise Exception('Bad target format: %s' % item)

        uri = '%s/networkservices/loadbalancer/targetgroup/registertargets' % self.baseuri
        self.cmp_put(uri, data={'target_group': data}, timeout=600)
        targets_str = ', '.join(item.get('Id') for item in data['Targets'])
        self.app.render({'msg': 'Register targets %s with target group %s' % (targets_str, oid)})

    @ex(
        help='deregister targets from target group',
        description='deregister targets from target group',
        arguments=ARGS([
            (['id'], {'help': 'target group id', 'action': 'store', 'type': str}),
            (['targets'], {'help': 'comma separated list of target ids', 'action': 'store', 'type': str}),
        ])
    )
    def targets_deregister(self):
        oid = self.app.pargs.id
        targets = self.app.pargs.targets

        data = {
            'TargetGroupId': oid,
            'Targets': [],
        }

        # parse targets
        target_ids = targets.strip().split(',')
        for target_id in target_ids:
            if target_id == '':
                raise Exception('Target ID cannot be empty')
            data['Targets'].append({'TargetId': target_id})

        uri = '%s/networkservices/loadbalancer/targetgroup/deregistertargets' % self.baseuri
        self.cmp_put(uri, data={'target_group': data}, timeout=600)
        targets_str = ', '.join(item.get('TargetId') for item in data['Targets'])
        self.app.render({'msg': 'Deregister targets %s from target group %s' % (targets_str, oid)})

    @ex(
        help='register health monitor with target group',
        description='register health monitor with target group',
        arguments=ARGS([
            (['id'], {'help': 'target group id', 'action': 'store', 'type': str}),
            (['monitor'], {'help': 'health monitor id', 'action': 'store', 'type': str}),
        ])
    )
    def health_monitor_register(self):
        oid = self.app.pargs.id
        monitor_id = self.app.pargs.monitor

        data = {
            'TargetGroupId': oid,
            'HealthMonitorId': monitor_id,
        }

        uri = '%s/networkservices/loadbalancer/targetgroup/registerhealthmonitor' % self.baseuri
        self.cmp_put(uri, data={'target_group': data}, timeout=600)
        self.app.render({'msg': 'Register health monitor %s with target group %s' % (monitor_id, oid)})

    @ex(
        help='deregister health monitor from target group',
        description='deregister health monitor from target group',
        arguments=ARGS([
            (['id'], {'help': 'target group id', 'action': 'store', 'type': str})
        ])
    )
    def health_monitor_deregister(self):
        oid = self.app.pargs.id
        data = {'TargetGroupId': oid}
        uri = '%s/networkservices/loadbalancer/targetgroup/deregisterhealthmonitor' % self.baseuri
        self.cmp_put(uri, data={'target_group': data}, timeout=600)
        self.app.render({'msg': 'Deregister health monitor from target group %s' % oid})


class ListenerNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'netaas'
        stacked_type = 'nested'
        label = 'listeners'
        description = 'listener service management'
        help = 'listener service management'

    traffic_types = [
        'tcp',
        'http',
        'ssl-passthrough',
        'https-offloading',
        'https-end-to-end'
    ]

    persistence_methods = [
        'sourceip',
        'cookie',
        'ssl-sessionid'
    ]

    cookie_modes = [
        'insert',
        'prefix',
        'app-session'
    ]

    cipher_suites = [
        'DEFAULT',
        'ECDHE-RSA-AES128-GCM-SHA256',
        'ECDHE-RSA-AES256-GCM-SHA384',
        'ECDHE-RSA-AES256-SHA',
        'ECDHE-ECDSA-AES256-SHA',
        'ECDH-ECDSA-AES256-SHA',
        'ECDH-RSA-AES256-SHA',
        'AES256-SHA',
        'AES128-SHA',
        'DES-CBC3-SHA'
    ]

    @ex(
        help='get listener templates',
        description='get listener templates',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str, 'default': None}),
            (['-id'], {'help': 'template id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def templates(self):
        self.get_service_definitions('NetworkListener')

    @ex(
        help='list listeners',
        description='list listeners',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of comma separated account ids', 'action': 'store', 'type': str,
                             'default': None}),
            (['-ids'], {'help': 'list of comma separated listener ids', 'action': 'store', 'type': str,
                        'default': None}),
            (['-tags'], {'help': 'list of comma separated tags', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['accounts', 'ids', 'tags']
        mappings = {
            'accounts': self.get_account_ids,
            'ids': lambda x: x.split(','),
            'tags': lambda x: x.split(',')
        }
        aliases = {
            'accounts': 'owner-id.N',
            'ids': 'ListenerId.N',
            'tags': 'tag-key.N',
            'size': 'MaxResults',
            'page': 'Nvl-NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '%s/networkservices/loadbalancer/listener/describelisteners' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeListenersResponse', {})
        page = self.app.pargs.page

        resp = {
            'count': len(res.get('listenerSet')),
            'page': page,
            'total': res.get('listenerTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'instances': res.get('listenerSet')
        }

        headers = ['uuid', 'name', 'state', 'type', 'account', 'traffic_type', 'persistence']
        fields = ['listenerId', 'name', 'state', 'type', 'nvl-ownerAlias', 'trafficType', 'persistence.method']
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40)

    @ex(
        help='get listener',
        description='get listener',
        arguments=ARGS([
            (['id'], {'help': 'listener id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {'ListenerId.N': [oid]}
        elif self.is_name(oid):
            data = {'ListenerName': oid}
        uri = '%s/networkservices/loadbalancer/listener/describelisteners' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeListenersResponse.listenerSet', default={})
        if len(res) == 0:
            raise Exception('Listener %s does not exist' % oid)
        res = res[0]
        self.app.render(res, details=True, maxsize=200)

    @ex(
        help='create listener',
        description='create listener',
        arguments=ARGS([
            (['name'], {'help': 'listener name', 'action': 'store', 'type': str}),
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['traffic_type'], {'metavar': 'traffic_type', 'help': 'incoming traffic typology {tcp,http,'
                                'ssl-passthrough,https-offloading,https-end-to-end}', 'choices': traffic_types,
                                'action': 'store', 'type': str}),
            (['-desc'], {'help': 'listener description', 'action': 'store', 'type': str}),
            (['-persistence'], {'help': 'persistence type', 'choices': persistence_methods, 'action': 'store',
                                'type': str}),
            (['-cookie_name'], {'help': 'cookie name', 'action': 'store', 'type': str}),
            (['-cookie_mode'], {'help': 'cookie mode', 'choices': cookie_modes, 'action': 'store', 'type': str}),
            (['-expire'], {'help': 'expire time in seconds', 'action': 'store', 'type': int}),
            (['-client_cert_path'], {'help': 'client certificate path', 'action': 'store', 'type': str}),
            (['-server_cert_path'], {'help': 'server certificate path', 'action': 'store', 'type': str}),
            (['-client_cipher'], {'help': 'cipher suite used by client', 'choices': cipher_suites, 'action': 'store',
                                  'type': str}),
            (['-server_cipher'], {'help': 'cipher suite used by server', 'choices': cipher_suites, 'action': 'store',
                                  'type': str}),
            (['-insert_x_forwarded_for'], {'help': 'insert X-Forwarded-For HTTP header', 'choices': [True, False],
                                           'action': 'store', 'type': bool}),
            (['-redirect_to'], {'help': 'url to redirect client requests', 'action': 'store', 'type': str}),
        ])
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get('uuid')
        traffic_type = self.app.pargs.traffic_type
        persistence = self.app.pargs.persistence
        expire = self.app.pargs.expire
        redirect_to = self.app.pargs.redirect_to
        insert_x_forwarded_for = self.app.pargs.insert_x_forwarded_for

        data = {
            'owner-id': account,
            'Name': self.app.pargs.name,
            'Description': self.app.pargs.desc,
            'TrafficType': traffic_type,
        }

        # input params validation:
        # - certificates and ciphering
        if traffic_type in ['https-offloading', 'https-end-to-end']:
            client_cert_path = self.app.pargs.client_cert_path
            server_cert_path = self.app.pargs.server_cert_path
            client_cipher = self.app.pargs.client_cipher
            server_cipher = self.app.pargs.server_cipher

            if traffic_type == 'https-offloading':
                if client_cert_path is None:
                    raise Exception('Client certificate is mandatory with %s traffic profile' % traffic_type)
                client_cert = self.load_file(client_cert_path)
                data.update({
                    'ClientCertificate': client_cert,
                    'ClientCipher': client_cipher
                })

            if traffic_type == 'https-end-to-end':
                if client_cert_path is None:
                    raise Exception('Client certificate is mandatory with %s traffic profile' % traffic_type)
                if server_cert_path is None:
                    raise Exception('Server certificate is mandatory with %s traffic profile' % traffic_type)
                client_cert = self.load_file(client_cert_path)
                server_cert = self.load_file(server_cert_path)
                data.update({
                    'ClientCertificate': client_cert,
                    'ClientCipher': client_cipher,
                    'ServerCertificate': server_cert,
                    'ServerCipher': server_cipher
                })

        # - persistence
        if persistence is not None:
            if traffic_type == 'ssl-passthrough' and persistence not in ['sourceip', 'ssl-sessionid']:
                raise Exception('Persistence options for SSL passthrough are: %s' %
                                self.__join(['sourceip', 'ssl-sessionid']))
            if traffic_type != 'ssl-passthrough' and persistence == 'ssl-sessionid':
                raise Exception('%s persistence can only be applied in conjunction with SSL passthrough profile'
                                % persistence)
            data.update({'Persistence': persistence})

            if persistence == 'cookie':
                cookie_name = self.app.pargs.cookie_name
                if cookie_name is None:
                    raise Exception('Cookie name is mandatory with %s persistence type' % persistence)
                cookie_mode = self.app.pargs.cookie_mode
                if cookie_mode is None:
                    raise Exception('Cookie mode is mandatory with %s persistence type' % persistence)
                if cookie_mode in ['insert', 'app-session'] and expire is None:
                    raise Exception('Expiration time cannot be null when cookie mode is insert or app-session')
                data.update({
                    'CookieName': cookie_name,
                    'CookieMode': cookie_mode
                })
            data.update({'ExpireTime': expire})

        # - URL redirection
        if redirect_to is not None and traffic_type == 'ssl-passthrough':
            raise Exception('URL redirection not available with %s traffic profile' % traffic_type)
        data.update({'URLRedirect': redirect_to})

        # - X-Forwarded-For HTTP header
        if insert_x_forwarded_for is not None and traffic_type in ['tcp', 'ssl-passthrough']:
            raise Exception('X-Forwarded-For header not available with %s traffic profiles' % traffic_type)
        data.update({'InsertXForwardedFor': insert_x_forwarded_for})

        uri = '%s/networkservices/loadbalancer/listener/createlistener' % self.baseuri
        res = self.cmp_post(uri, data={'listener': data}, timeout=600)
        res = dict_get(res, 'CreateListenerResponse.Listener.listenerId')
        self.app.render({'msg': 'Add listener %s' % res})

    @ex(
        help='delete listeners',
        description='delete listeners',
        arguments=ARGS([
            (['ids'], {'help': 'comma separated listener ids', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oids = self.app.pargs.ids.split(',')
        for oid in oids:
            data = {'listenerId': oid}
            uri = '%s/networkservices/loadbalancer/listener/deletelistener' % self.baseuri
            self.cmp_delete(uri, data=data, timeout=600, entity='Listener %s' % oid)


class LoadBalancerNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'netaas'
        stacked_type = 'nested'
        label = 'load_balancers'
        description = "load balancer service management"
        help = "load balancer service management"

    protocols = [
        'http',
        'https'
    ]

    @ex(
        help='get load balancer templates',
        description='get load balancer templates',
        arguments=ARGS([
            (['account'], {'help': 'account id', 'action': 'store', 'type': str, 'default': None}),
            (['-id'], {'help': 'template id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def templates(self):
        self.get_service_definitions('NetworkLoadBalancer')

    @ex(
        help='list load balancers',
        description='list load balancers',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of comma separated account ids', 'action': 'store', 'type': str,
                             'default': None}),
            (['-ids'], {'help': 'list of comma separated load balancer ids', 'action': 'store', 'type': str,
                        'default': None}),
            (['-tags'], {'help': 'list of comma separated tags', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def list(self):
        params = ['accounts', 'ids', 'tags']
        mappings = {
            'accounts': self.get_account_ids,
            'ids': lambda x: x.split(','),
            'tags': lambda x: x.split(',')
        }
        aliases = {
            'accounts': 'owner-id.N',
            'ids': 'LoadBalancerId.N',
            'tags': 'tag-key.N',
            'size': 'MaxResults',
            'page': 'Nvl-NextToken'
        }
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '%s/networkservices/loadbalancer/describeloadbalancers' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res.get('DescribeLoadBalancersResponse', {})
        page = self.app.pargs.page

        resp = {
            'count': len(res.get('loadBalancerSet')),
            'page': page,
            'total': res.get('loadBalancerTotal'),
            'sort': {'field': 'id', 'order': 'asc'},
            'instances': res.get('loadBalancerSet')
        }

        headers = ['uuid', 'name', 'state', 'account', 'vip', 'protocol', 'port', 'listener', 'target_group']
        fields = ['loadBalancerId', 'name', 'state', 'nvl-ownerAlias', 'virtualIP', 'protocol', 'port',
                  'attachmentSet.Listener.name', 'attachmentSet.TargetGroup.name']
        self.app.render(resp, key='instances', headers=headers, fields=fields, maxsize=40)

    @ex(
        help='get load balancer',
        description='get load balancer',
        arguments=ARGS([
            (['id'], {'help': 'load balancer id', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        oid = self.app.pargs.id
        if self.is_uuid(oid):
            data = {'LoadBalancerId.N': [oid]}
        elif self.is_name(oid):
            data = {'LoadBalancerName': oid}
        uri = '%s/networkservices/loadbalancer/describeloadbalancers' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'DescribeLoadBalancersResponse.loadBalancerSet', default={})
        if len(res) == 0:
            raise Exception('Load balancer %s does not exist' % oid)
        res = res[0]
        attachments = res.pop('attachmentSet')
        listener = dict_get(attachments, 'Listener', default=None)
        target_group = dict_get(attachments, 'TargetGroup', default=None)
        self.app.render(res, details=True, maxsize=200)
        self.c('\nattached listener', 'underline')
        if listener is not None:
            headers = ['uuid', 'name', 'state', 'type', 'traffic_type', 'persistence']
            fields = ['listenerId', 'name', 'state', 'type', 'trafficType', 'persistence.method']
            self.app.render(listener, headers=headers, fields=fields, maxsize=80)
        self.c('\nattached target group', 'underline')
        if target_group is not None:
            headers = ['uuid', 'name', 'state', 'balancing_algorithm', 'target_type']
            fields = ['targetGroupId', 'name', 'state', 'balancingAlgorithm', 'targetType']
            self.app.render(target_group, headers=headers, fields=fields, maxsize=80)

    @ex(
        help='create load balancer',
        description='create load balancer',
        arguments=ARGS([
            (['name'], {'help': 'load balancer name', 'action': 'store', 'type': str}),
            (['account'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['subnet'], {'help': 'subnet id', 'action': 'store', 'type': str}),
            (['protocol'], {'metavar': 'protocol', 'help': 'protocol for connections from clients to load balancer '
                            '{http,https}', 'action': 'store', 'type': str, 'choices': protocols}),
            (['port'], {'help': 'port number', 'action': 'store', 'type': int}),
            (['listener'], {'help': 'listener id', 'action': 'store', 'type': str}),
            (['target_group'], {'help': 'target group id', 'action': 'store', 'type': str}),
            (['-desc'], {'help': 'load balancer description', 'action': 'store', 'type': str}),
            (['-max_conn'], {'help': 'maximum concurrent connections', 'action': 'store', 'type': int}),
            (['-max_conn_rate'], {'help': 'maximum connections per second', 'action': 'store', 'type': int}),
        ])
    )
    def add(self):
        account = self.get_account(self.app.pargs.account).get('uuid')
        protocol = self.app.pargs.protocol
        data = {
            'owner-id': account,
            'Name': self.app.pargs.name,
            'SubnetId': self.app.pargs.subnet,
            'Protocol': protocol.upper(),
            'Port': self.app.pargs.port,
            'Listener': self.app.pargs.listener,
            'TargetGroup': self.app.pargs.target_group,
        }

        params = [
            {'key': 'Description', 'value': self.app.pargs.desc},
            {'key': 'MaxConnections', 'value': self.app.pargs.max_conn},
            {'key': 'MaxConnectionRate', 'value': self.app.pargs.max_conn_rate},
        ]
        for param in params:
            if param.get('value') is not None:
                data[param.get('key')] = param.get('value')

        uri = '%s/networkservices/loadbalancer/createloadbalancer' % self.baseuri
        res = self.cmp_post(uri, data={'load_balancer': data}, timeout=600)
        uuid = dict_get(res, 'CreateLoadBalancerResponse.LoadBalancer.loadBalancerId')
        self.wait_for_service(uuid)
        self.app.render({'msg': 'Add load balancer %s' % uuid})

    @ex(
        help='delete load balancer',
        description='delete load balancer',
        arguments=ARGS([
            (['id'], {'help': 'load balancer id', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        uuid = self.app.pargs.id
        data = {'loadBalancerId': uuid}
        uri = '%s/networkservices/loadbalancer/deleteloadbalancer' % self.baseuri
        self.cmp_delete(uri, data=data, timeout=600, entity='Load balancer %s' % uuid)
        self.wait_for_service(uuid, accepted_state='DELETED')

class SshGatewayNetServiceController(BusinessControllerChild):
    class Meta:
        stacked_on = 'netaas'
        stacked_type = 'nested'
        label = 'sshgw'
        description = "ssh gateway service management"
        help = "ssh gateway service management"

    
    @ex(
        help='get ssh gateway configurations',
        description='get ssh gateway configurations',
        arguments=ARGS([
            (['-accounts'], {'help': 'list of account id comma separated', 'action': 'store', 'type': str,
                             'default': None}),
            (['-ids'], {'help': 'list of ssh gateway configurations id comma separated', 'action': 'store', 'type': str,
                        'default': None}),
            (['-names'], {'help': 'list of ssh gateway configurations names comma separated', 'action': 'store', 'type': str,
                        'default': None}),
            (['-tags'], {'help': 'list of tag comma separated', 'action': 'store', 'type': str, 'default': None}),
            (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
            (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        ])
    )
    def conf_list(self):
        params = ['accounts', 'ids', 'tags', 'gw_type', 'names']
        mappings = {
            'accounts': self.get_account_ids,
            'tags': lambda x: x.split(','),
            'ids': lambda x: x.split(','),
            'names': lambda x: x.split(',')
        }
        
        aliases = {
            'accounts': 'owner-id.N',
            'ids': 'sshgwconf-id.N',
            'names': 'sshgwconf-name.N',
            'tags': 'tag.N'
        }
        
        data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
        uri = '%s/networkservices/sshgateway/configuration/list' % self.baseuri
        res = self.cmp_get(uri, data=data)
        
        res = res.get('list_response', {})
        page = self.app.pargs.page

        resp = {
            'count': len(res.get('sshgatewaySet')),
            'page': page,
            'total': res.get('total'),
            'sort': {'field': 'id', 'order': 'asc'},
            'instances': res.get('sshgatewaySet')
        }

        transform = {'nvl-state': self.color_error}
        headers = ['id', 'name', 'status',  'account', 'gw_type','resource_id']
        fields = ['sshGatewayConfId', 'nvl-name', 'nvl-state', 'nvl-ownerAlias', 'gwType', 'resourceId']
        self.app.render(resp, key='instances', headers=headers, fields=fields, transform=transform, maxsize=40)


    @ex(
        help='get ssh gateway configuration',
        description='get ssh gateway configuration',
        arguments=ARGS([
            (['id'], {'help': 'ssh gateway configuration id', 'action': 'store', 'type': str}),
        ])
    )
    def conf_get(self):
        id = self.app.pargs.id
        data = {'sshgwconf-id.N': [id],'size':1}
        uri = '%s/networkservices/sshgateway/configuration/list' % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data, doseq=True))
        res = dict_get(res, 'list_response.sshgatewaySet', default={})

        if len(res) == 0:
            raise Exception('ssh gateway configuration %s does not exist' % id)
        res = res[0]
        self.app.render(res, details=True, maxsize=200)
        #TODO other info
        #self.c('\nport specs', 'underline')

    @ex(
        help='add ssh gateway configuration',
        description='add ssh gateway configuration',
        arguments=ARGS([
            (['account_id'], {'help': 'parent account id', 'action': 'store', 'type': str}),
            (['name'], {'help': 'configuration name', 'action': 'store', 'type': str, 'default': None}),
            (['gw_type'], {'metavar':'gw_type','help': 'ssh gateway type (gw_dbaas,gw_vm,gw_ext)', 'choices':['gw_dbaas','gw_vm','gw_ext'],'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'configuration description', 'action': 'store', 'type': str, 'default': None}),
            (['-dest_id'], {'help': 'service uuid of the destination cli object','action':'store','type':str,'default':None}),
            (['-ip'], {'help': 'destination ip address. only if gw_type=gw_ext','action':'store','type':str,'default':None})
        ])
    )
    def conf_add(self):
        if self.app.pargs.gw_type != 'gw_ext' and self.app.pargs.dest_id is None:
            self.app.pargs.ip = None
            self.app.error('you need to specify -dest_id for the chosen value of gw_type')
            return
        
        if self.app.pargs.gw_type == 'gw_ext' and self.app.pargs.ip is None:
            self.app.pargs.dest_id = None
            self.app.error('you need to specify -ip for the chosen value of gw_type')
            return
        
        from beecell.simple import set_request_params
        configuration = {}
        configuration.update(set_request_params(self.app.pargs, ['account_id','name','desc','gw_type','dest_id','ip']))
        data = {
            "configuration":configuration
        }
        uri = '%s/networkservices/sshgateway/configuration/create' %self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)


    @ex(
        help='delete a ssh gateway configuration',
        description='delete a ssh gateway configuration',
        arguments=ARGS([
            (['id'], {'help': 'ssh gateway conf id', 'action': 'store', 'type': str}),
        ])
    )
    def conf_delete(self):
        data = {'ssh_gateway_id': self.app.pargs.id}
        uri = '%s/networkservices/sshgateway/configuration/delete' % self.baseuri
        self.cmp_delete(uri, data=data, timeout=600, entity='ssh gateway conf %s' % self.app.pargs.id)