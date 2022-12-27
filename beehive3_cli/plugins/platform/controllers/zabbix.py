# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 Regione Piemonte

from datetime import datetime
from json import dumps

from six import ensure_str

from beecell.simple import merge_list
from beecell.types.type_date import get_date_from_timestamp, format_date
from beecell.types.type_dict import dict_get
from beecell.types.type_string import str2bool
from beedrones.zabbix.client import ZabbixManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS
from cement import ex
from beehive3_cli.core.util import load_environment_config, load_config


def ZABBIX_ARGS(*list_args):
    orchestrator_args = [
        (['-O', '--orchestrator'], {'action': 'store', 'dest': 'orchestrator',
                                    'help': 'zabbix platform reference label'}),
        (['-P', '--project'], {'action': 'store', 'dest': 'project', 'help': 'zabbix current project name'}),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


def ZABBIX_PARGS(*list_args):
    orchestrator_args = [
        (['-O', '--orchestrator'], {'action': 'store', 'dest': 'orchestrator',
                                    'help': 'zabbix platform reference label'}),
        (['-P', '--project'], {'action': 'store', 'dest': 'project', 'help': 'zabbix current project name'}),
        (['-size'], {'help': 'list page size [default=20]', 'action': 'store', 'type': int, 'default': 20}),
        (['-page'], {'help': 'list page [default=0]', 'action': 'store', 'type': int, 'default': 0}),
        (['-order'], {'help': 'list sort order [default=DESC]', 'action': 'store', 'type': str, 'default': 'DESC'}),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class ZabbixPlatformController(BaseController):
    class Meta:
        label = 'zabbix'
        stacked_on = 'platform'
        stacked_type = 'nested'
        description = "zabbix platform"
        help = "zabbix platform"

    def pre_command_run(self):
        super(ZabbixPlatformController, self).pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get('orchestrators', {}).get('zabbix', {})
        label = getattr(self.app.pargs, 'orchestrator', None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception('No zabbix default platform is available for this environment. Select '
                                'another environment')

        if label not in orchestrators:
            raise Exception('Valid label are: %s' % ', '.join(orchestrators.keys()))
        conf = orchestrators.get(label)

        uri = '%s://%s:%s%s' % (conf.get('proto'), conf.get('hosts')[0], conf.get('port'), conf.get('path'))
        self.client = ZabbixManager(uri=uri)
        self.client.set_timeout(10.0)
        self.client.authorize(conf.get('user'), conf.get('pwd'))

    def __get_host_by_name(self, name):
        res = self.client.host.list(search={'host': name})
        if len(res) > 0:
            return res[0]
        else:
            raise Exception('no host %s found' % name)

    @ex(
        help='ping zabbix',
        description='ping zabbix',
        arguments=ZABBIX_ARGS()
    )
    def ping(self):
        res = self.client.ping()
        self.app.render({'ping': res}, headers=['ping'])

    @ex(
        help='get zabbix version',
        description='get zabbix version',
        arguments=ZABBIX_ARGS()
    )
    def version(self):
        res = self.client.version()
        self.app.render({'version': res}, headers=['version'])

    @ex(
        help='add trigger',
        description='add trigger',
        arguments=ZABBIX_ARGS([
            (['desc'], {'help': 'trigger description', 'action': 'store', 'type': str, 'default': None}),
            (['comment'], {'help': 'trigger comment', 'action': 'store', 'type': str, 'default': None}),
            (['expression'], {'help': 'trigger expression', 'action': 'store', 'type': str, 'default': None}),
            (['priority'], {'help': 'priority type. Can be: 0 (Default) not classified, 1 information, 2 warning, '
                                    '3 average, 4 high, 5 disaster', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def trigger_add(self):
        desc = self.app.pargs.desc
        comment = self.app.pargs.comment
        expression = self.app.pargs.expression
        priority = self.app.pargs.priority
        res = self.client.trigger.create(desc, comment, expression, priority)
        self.app.render({'msg': 'add trigger %s' % res})

    @ex(
        help='list triggers',
        description='list triggers',
        arguments=ZABBIX_PARGS([
            (['-id'], {'help': 'trigger id', 'action': 'store', 'type': str, 'default': None}),
            (['-field'], {'help': 'sort field', 'action': 'store', 'type': str, 'default': 'triggerid'}),
        ])
    )
    def trigger_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            res = self.client.trigger.get(oid)
            if self.is_output_text():
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            field = self.app.pargs.field
            order = self.app.pargs.order
            count = self.client.trigger.list(countOutput=True)
            res = self.client.trigger.list(limit=size, offset=page, sortorder=order.upper(), sortfield=field)
            res = {
                'triggers': res,
                'page': page,
                'count': size,
                'total': count,
                'sort': {
                    'field': field,
                    'order': order
                }
            }
            headers = ['id', 'desc', 'expression', 'type', 'state']
            fields = ['triggerid', 'description', 'expression', 'type', 'state']
            self.app.render(res, key='triggers', headers=headers, fields=fields)

    @ex(
        help='delete trigger',
        description='delete trigger',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'trigger id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def trigger_del(self):
        oid = self.app.pargs.id
        self.client.trigger.delete(oid)
        self.app.render({'msg': 'delete trigger %s' % oid}, headers=['msg'])

    @ex(
        help='add host',
        description='add host',
        arguments=ZABBIX_ARGS([
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None})
            #
            # As a data file example, see beehive-mgmt/configs/test/example/zabbix_host_add.yml
            #
        ])
    )
    def host_add(self):
        data_file = self.app.pargs.file
        data = load_config(data_file)

        host = data.get('host')
        name = host.get('name')
        desc = host.get('desc')
        interfaces = host.get('interfaces')
        groups = host.get('groups')
        templates = host.get('templates')

        res = self.client.host.create(name, interfaces, groupids=groups, templateids=templates,
                                      description=desc)
        self.app.render({'msg': 'add host %s' % res['hostids']})

    @ex(
        help='list hosts',
        description='list hosts',
        arguments=ZABBIX_PARGS([
            (['-id'], {'help': 'host id', 'action': 'store', 'type': str, 'default': None}),
            (['-field'], {'help': 'sort field', 'action': 'store', 'type': str, 'default': 'hostid'}),
            (['-name'], {'help': 'host name', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def host_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            res = self.client.host.get(oid)
            if self.is_output_text():
                self.app.render(res, details=True)
                self.c('\ngroups', 'underline')
                res = self.client.host.groups(oid)
                groups = res.get('groups')
                self.app.render(groups, headers=['groupid', 'name', 'internal', 'flags'])
                self.c('\ntemplates', 'underline')
                res = self.client.host.templates(oid)
                tmpls = res.get('parentTemplates')
                self.app.render(tmpls, headers=['templateid', 'name', 'status'])
                self.c('\ninterfaces', 'underline')
                res = self.client.host.interfaces(oid)
                interfaces = res.get('interfaces')
                self.app.render(interfaces, headers=['interfaceid', 'main', 'type', 'useip', 'ip', 'dns', 'port',
                                                     'bulk'])
                self.c('\nalerts', 'underline')
                alerts = self.client.alert.list(hostids=oid, limit=10, sortorder='DESC', sortfield='clock')
                transform = {
                    'clock': lambda x: datetime.fromtimestamp(int(x))
                }
                self.app.render(alerts, headers=['alertid', 'actionid', 'clock', 'sendto', 'subject'],
                                transform=transform)
            else:
                self.app.render(res, details=True)
        else:
            name = self.app.pargs.name
            page = self.app.pargs.page
            size = self.app.pargs.size
            field = self.app.pargs.field
            order = self.app.pargs.order
            count = self.client.host.list(countOutput=True)
            res = self.client.host.list(limit=size, offset=page, sortorder=order.upper(), sortfield=field,
                                        search={'host': name})
            res = {
                'hosts': res,
                'page': page,
                'count': size,
                'total': count,
                'sort': {
                    'field': field,
                    'order': order
                }
            }
            transform = {
                'status': lambda x: 'Enabled' if x == '0' else 'Disabled',
                'available': lambda x: 'available' if x == '1' else 'unavailable',
                'maintenance_status': lambda x: 'no maintenance' if x == '0' else 'maintenance',
            }
            headers = ['id', 'proxy_hostid', 'host', 'name', 'status', 'available', 'maintenance_status']
            fields = ['hostid', 'proxy_hostid', 'host', 'name', 'status', 'available', 'maintenance_status']
            self.app.render(res, key='hosts', headers=headers, fields=fields, transform=transform)

    @ex(
        help='list groups the host belongs to',
        description='list groups the host belongs to',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'host id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def host_get_groups(self):
        oid = self.app.pargs.id
        res = self.client.host.groups(oid)
        headers = ['id', 'name', 'internal', 'flags']
        fields = ['groupid', 'name', 'internal', 'flags']
        self.app.render(res, key='groups', headers=headers, fields=fields)

    @ex(
        help='list templates linked to the host',
        description='list templates linked to the host',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'host id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def host_get_templates(self):
        oid = self.app.pargs.id
        res = self.client.host.templates(oid)
        headers = ['id', 'name', 'status']
        fields = ['templateid', 'name', 'status']
        self.app.render(res, key='parentTemplates', headers=headers, fields=fields)

    @ex(
        help='list interfaces used by the host',
        description='list interfaces used by the host',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'host id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def host_get_interfaces(self):
        oid = self.app.pargs.id
        res = self.client.host.interfaces(oid)
        print(res)
        headers = ['id', 'main', 'type', 'useip', 'ip', 'dns', 'port', 'bulk']
        fields = ['interfaceid', 'main', 'type', 'useip', 'ip', 'dns', 'port', 'bulk']
        self.app.render(res, key='interfaces', headers=headers, fields=fields)

    @ex(
        help='list host items',
        description='list host items',
        arguments=ZABBIX_ARGS([
            (['-id'], {'help': 'host id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'host name', 'action': 'store', 'type': str, 'default': None}),
            (['-state'], {'help': 'host state', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def host_item_get(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        state = self.app.pargs.state
        if name is not None:
            host = self.__get_host_by_name(name)
            oid = host.get('hostid')

        res = self.client.host.get_items(oid, filter={'state': state})
        transform = {
            'state': lambda x: self.app.color_error('ko') if x == '1' else self.app.color_error('ok'),
            'type': self.client.host.map_item_to_string
        }
        headers = ['itemid', 'type', 'name', 'delay', 'units', 'lastclock', 'state', 'lastvalue', 'prevvalue']
        fields = ['itemid', 'type', 'name', 'delay', 'units', 'lastclock', 'state', 'lastvalue', 'prevvalue']
        self.app.render(res, headers=headers, fields=fields, transform=transform, maxsize=50)

    @ex(
        help='add host item',
        description='add host item',
        arguments=ZABBIX_ARGS([
            (['id'], {'help': 'host id', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'key name', 'action': 'store', 'type': str, 'default': None}),
            (['desc'], {'help': 'item description/comment', 'action': 'store', 'type': str, 'default': None}),
            (['agent_type'], {'help': 'zabbix type. Can be: 0 - Zabbix agent, 1 - SNMPv1 agent, 2 - Zabbix trapper, '
                                      '3 - simple check, 4 - SNMPv2 agent, 5 - Zabbix internal, 6 - SNMPv3 agent, '
                                      '7 - Zabbix agent (active), 8 - Zabbix aggregate, 9 - web item, '
                                      '10 - external check, 11 - database monitor, 12 - IPMI agent, '
                                      '13 - SSH agent, 14 - TELNET agent, 15 - calculated, 16 - JMX agent.',
                              'action': 'store', 'type': str, 'default': None}),
            (['value_type'], {'help': 'zabbix value_type. Can be: 0 - numeric float, 1 - character, 2 - log, '
                                      '3 - numeric unsigned, 4 - text.', 'action': 'store', 'type': str,
                              'default': None}),
            (['interfaceid'], {'help': 'zabbix host interfaceid', 'action': 'store', 'type': str, 'default': None}),
            (['key'], {'help': 'item key', 'action': 'store', 'type': str, 'default': None}),
            (['delay'], {'help': 'check interval in seconds', 'action': 'store', 'type': str, 'default': None}),
            (['history'], {'help': 'number of days to keep item history data', 'action': 'store', 'type': str,
                           'default': None}),
            (['trends'], {'help': 'number of days to keep item trends data', 'action': 'store', 'type': str,
                          'default': None}),
        ])
    )
    def host_item_add(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        agent_type = self.app.pargs.agent_type
        value_type = self.app.pargs.value_type
        interfaceid = self.app.pargs.interfaceid
        key = self.app.pargs.key
        delay = self.app.pargs.delay
        history = self.app.pargs.history
        trends = self.app.pargs.trends

        res = self.client.host.create_item(oid, name, desc, agent_type, value_type, interfaceid, key, delay, history,
                                           trends)
        self.app.render({'msg': 'add host item %s' % res})

    @ex(
        help='list host triggers',
        description='list host triggers',
        arguments=ZABBIX_ARGS([
            (['id'], {'help': 'host id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def host_trigger_get(self):
        oid = self.app.pargs.id
        res = self.client.host.get_triggers(oid)
        headers = ['triggerid', 'expression', 'description', 'state', 'value']
        fields = ['triggerid', 'expression', 'description', 'state', 'value']
        self.app.render(res, headers=headers, fields=fields)

    @ex(
        help='enable host',
        description='enable host',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'host id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def host_enable(self):
        oid = self.app.pargs.id
        self.client.host.update(oid, status=0)
        self.app.render({'msg': 'enable host %s' % oid}, headers=['msg'])

    @ex(
        help='disable host',
        description='disable host',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'host id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def host_disable(self):
        oid = self.app.pargs.id
        self.client.host.update(oid, status=1)
        self.app.render({'msg': 'disable host %s' % oid}, headers=['msg'])

    @ex(
        help='delete host',
        description='delete host',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'host id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def host_del(self):
        oid = self.app.pargs.id
        self.client.host.delete(oid)
        self.app.render({'msg': 'delete host %s' % oid}, headers=['msg'])

    @ex(
        help='add group',
        description='add group',
        arguments=ZABBIX_PARGS([
            (['name'], {'help': 'group name', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def group_add(self):
        name = self.app.pargs.name
        res = self.client.group.add(name)
        self.app.render({'msg': 'add group %s' % res['groupid']})

    @ex(
        help='list groups',
        description='list groups',
        arguments=ZABBIX_PARGS([
            (['-id'], {'help': 'group id', 'action': 'store', 'type': str, 'default': None}),
            (['-field'], {'help': 'sort field', 'action': 'store', 'type': str, 'default': 'groupid'})
        ])
    )
    def group_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            res = self.client.group.get(oid)
            if self.is_output_text():
                self.app.render(res, details=True)
                self.c('\nhosts', 'underline')
                res = self.client.group.hosts(oid)
                hosts = res.get('hosts')
                self.app.render(hosts, headers=['hostid', 'name', 'status'])
                self.c('\ntemplates', 'underline')
                res = self.client.group.templates(oid)
                templates = res.get('templates')
                self.app.render(templates, headers=['templateid', 'name', 'status'])
            else:
                self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            field = self.app.pargs.field
            order = self.app.pargs.order
            count = self.client.group.list(countOutput=True)
            res = self.client.group.list(limit=size, offset=page, sortorder=order.upper(), sortfield=field)
            res = {
                'groups': res,
                'page': page,
                'count': size,
                'total': count,
                'sort': {
                    'field': field,
                    'order': order
                }
            }
            headers = ['id', 'name', 'hosts']
            fields = ['groupid', 'name', 'hosts']
            transform = {'hosts': lambda x: len(x)}
            self.app.render(res, key='groups', headers=headers, fields=fields, transform=transform, maxsize=60)

    @ex(
        help='list hosts that belong to a group',
        description='get hosts that belong to a group',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'group id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def group_get_hosts(self):
        oid = self.app.pargs.id
        res = self.client.group.hosts(oid)
        headers = ['id', 'name', 'status']
        fields = ['hostid', 'name', 'status']
        self.app.render(res, key='hosts', headers=headers, fields=fields)

    @ex(
        help='list templates that belong to a group',
        description='get templates that belong to a group',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'group id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def group_get_templates(self):
        oid = self.app.pargs.id
        res = self.client.group.templates(oid)
        headers = ['id', 'name', 'status']
        fields = ['templateid', 'name', 'status']
        self.app.render(res, key='templates', headers=headers, fields=fields)

    @ex(
        help='update group',
        description='update group',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'group id', 'action': 'store', 'type': str, 'default': None}),
            (['name'], {'help': 'group name', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def group_update(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        self.client.group.update(oid, name)
        self.app.render({'msg': 'update group %s' % oid}, headers=['msg'])

    @ex(
        help='delete group',
        description='delete group',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'group id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def group_del(self):
        oid = self.app.pargs.id
        self.client.group.delete(oid)
        self.app.render({'msg': 'delete group %s' % oid}, headers=['msg'])

    @ex(
        help='add template',
        description='add template',
        arguments=ZABBIX_ARGS([
            (['file'], {'help': 'data file', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def template_add(self):
        data_file = self.app.pargs.file
        import xml.etree.ElementTree as et
        data = load_config(data_file)
        data = ensure_str(et.tostring(data))
        self.client.template.load(data)
        self.app.render({'msg': 'add template'})

    @ex(
        help='list templates',
        description='list templates',
        arguments=ZABBIX_PARGS([
            (['-id'], {'help': 'template id', 'action': 'store', 'type': str, 'default': None}),
            (['-field'], {'help': 'sort field', 'action': 'store', 'type': str, 'default': 'name'}),
        ])
    )
    def template_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            res = self.client.template.get(oid)
            if self.is_output_text():
                self.app.render(res, details=True)
                self.c('\ngroups', 'underline')
                res = self.client.template.groups(oid)
                groups = res.get('groups')
                self.app.render(groups, headers=['groupid', 'name', 'internal', 'flags'])
                self.c('\nhosts', 'underline')
                res = self.client.template.hosts(oid)
                hosts = res.get('hosts')
                self.app.render(hosts, headers=['hostid', 'name', 'status'])
            else:
                self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            field = self.app.pargs.field
            order = self.app.pargs.order
            count = self.client.template.list(countOutput=True)
            res = self.client.template.list(limit=size, offset=page, sortorder=order.upper(), sortfield=field)
            res = {
                'templates': res,
                'page': page,
                'count': size,
                'total': count,
                'sort': {
                    'field': field,
                    'order': order
                }
            }
            headers = ['id', 'name', 'host', 'status']
            fields = ['templateid', 'name', 'host', 'status']
            self.app.render(res, key='templates', headers=headers, fields=fields, maxsize=60)

    @ex(
        help='list hosts linked to the template',
        description='list hosts linked to the template',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'group id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def template_get_hosts(self):
        oid = self.app.pargs.id
        res = self.client.template.hosts(oid)
        headers = ['id', 'name', 'status']
        fields = ['hostid', 'name', 'status']
        self.app.render(res, key='hosts', headers=headers, fields=fields)

    @ex(
        help='list groups the template belongs to',
        description='list groups the template belongs to',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'group id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def template_get_groups(self):
        oid = self.app.pargs.id
        res = self.client.template.groups(oid)
        headers = ['id', 'name', 'internal', 'flags']
        fields = ['groupid', 'name', 'internal', 'flags']
        self.app.render(res, key='groups', headers=headers, fields=fields)

    @ex(
        help='delete template',
        description='delete template',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'template id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def template_del(self):
        oid = self.app.pargs.id
        self.client.template.delete(oid)
        self.app.render({'msg': 'delete template %s' % oid}, headers=['msg'])

    @ex(
        help='list interfaces',
        description='list interfaces',
        arguments=ZABBIX_PARGS([
            (['-id'], {'help': 'group id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def interface_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            res = self.client.interface.get(oid)
            if self.is_output_text():
                self.app.render(res, details=True)
                self.c('\nhosts', 'underline')
                res = self.client.interface.hosts(oid)
                hosts = res.get('hosts')
                self.app.render(hosts, headers=['hostid', 'name', 'status'])
            else:
                self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            order = self.app.pargs.order
            count = len(self.client.interface.list(countOutput=True))
            res = self.client.interface.list(limit=size, offset=page, sortorder=order.upper())
            res = {
                'interfaces': res,
                'page': page,
                'count': size,
                'total': count,
                'sort': {
                    'order': order
                }
            }
            headers = ['id', 'hostid', 'main', 'type', 'useip', 'ip', 'dns', 'port', 'details']
            fields = ['interfaceid', 'hostid', 'main', 'type', 'useip', 'ip', 'dns', 'port', 'details']
            self.app.render(res, key='interfaces', headers=headers, fields=fields, maxsize=60)

    @ex(
        help='list hosts that use the interface',
        description='list hosts that use the interface',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'group id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def interface_get_hosts(self):
        oid = self.app.pargs.id
        res = self.client.interface.hosts(oid)
        headers = ['hostid', 'name', 'status']
        fields = ['hostid', 'name', 'status']
        self.app.render(res, key='hosts', headers=headers, fields=fields)

    @ex(
        help='delete interface',
        description='delete interface',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'group id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def interface_del(self):
        oid = self.app.pargs.id
        self.client.interface.delete(oid)
        self.app.render({'msg': 'delete interface %s' % oid}, headers=['msg'])

    @ex(
        help='list alerts',
        description='list alerts',
        arguments=ZABBIX_PARGS([
            (['-id'], {'help': 'alert id', 'action': 'store', 'type': str, 'default': None}),
            (['-field'], {'help': 'sort field', 'action': 'store', 'type': str, 'default': 'clock'}),
        ])
    )
    def alert_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            res = self.client.alert.get(oid)

            if self.is_output_text():
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            field = self.app.pargs.field
            order = self.app.pargs.order
            count = self.client.alert.list(countOutput=True)
            res = self.client.alert.list(limit=size, sortorder=order.upper(), sortfield=field, selectHosts=True)
            res = {'alerts': res, 'page': page, 'count': size, 'total': count, 'sort': {'field': field, 'order': order}}
            headers = ['alertid', 'actionid', 'clock', 'sendto', 'subject', 'hosts']
            fields = ['alertid', 'actionid', 'clock', 'sendto', 'subject', 'hosts']
            transform = {
                'clock': lambda x: datetime.fromtimestamp(int(x)),
                'hosts': lambda x: ','.join([h['hostid'] for h in x])
            }
            self.app.render(res, key='alerts', headers=headers, fields=fields, maxsize=30, transform=transform)

    @ex(
        help='list it services',
        description='list it services',
        arguments=ZABBIX_PARGS([
            (['-id'], {'help': 'alert id', 'action': 'store', 'type': str, 'default': None}),
            (['-sla'], {'help': 'if true pirnt calculated sla', 'action': 'store', 'type': str, 'default': 'false'}),
        ])
    )
    def it_service_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            res = self.client.it_service.get(oid)
            sla = self.client.it_service.get_sla(oid)
            for s in sla.get('sla', []):
                s['from'] = format_date(get_date_from_timestamp(s['from']))
                s['to'] = format_date(get_date_from_timestamp(s['to']))

            if self.is_output_text():
                dependencies = res.pop('dependencies', [])
                parent = res.pop('parent', {})
                alarms = res.pop('alarms', [])
                trigger = res.pop('trigger', {})
                if isinstance(parent, list):
                    parent = {}
                if isinstance(trigger, list):
                    trigger = {}

                self.app.render(res, details=True)

                self.c('\nsla', 'underline')
                self.app.render(sla, details=True)
                self.c('\nparent', 'underline')
                self.app.render(parent, details=True)
                self.c('\ndependencies', 'underline')
                self.app.render(dependencies, headers=['linkid', 'serviceupid', 'servicedownid', 'soft', 'sortorder',
                                                       'serviceid'])
                self.c('\ntrigger', 'underline')
                self.app.render(trigger, details=True)
                self.c('\nalarms', 'underline')
                self.app.render(alarms, headers=['servicealarmid', 'clock', 'value'])
            else:
                self.app.render(res, details=True)
        else:
            sla = str2bool(self.app.pargs.sla)
            page = self.app.pargs.page
            size = self.app.pargs.size
            count = self.client.it_service.list(countOutput=True)
            res = self.client.it_service.list(limit=size)
            headers = ['serviceid', 'parentid', 'name', 'status', 'trigger', 'goodsla']
            fields = ['serviceid', 'parent.serviceid', 'name', 'status', 'trigger.description', 'goodsla']
            if sla is True:
                fields.append('sla')
                headers.append('sla')
                for r in res:
                    r['sla'] = dict_get(self.client.it_service.get_sla(r['serviceid']), 'sla.0.sla')
            for r in res:
                r['status'] = 'OK' if r['status'] == '0' else 'KO'
            res = {'services': res, 'page': page, 'count': size, 'total': count,
                   'sort': {'field': 'serviceid', 'order': 'asc'}}

            transform = {
                'services.status': lambda x: 'OK' if x == 0 else 'KO'
            }
            self.app.render(res, key='services', headers=headers, fields=fields, maxsize=60, transform=transform)

    @ex(
        help='list actions',
        description='list actions',
        arguments=ZABBIX_ARGS([
            (['-id'], {'help': 'action id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def action_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            res = self.client.action.get(oid)

            if self.is_output_text():
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            res = self.client.action.list()
            headers = ['actionid', 'name', 'status']
            fields = ['actionid', 'name', 'status']
            self.app.render(res, headers=headers, fields=fields, maxsize=40)

    @ex(
        help='list problems',
        description='list problems',
        arguments=ZABBIX_ARGS([
            (['-id'], {'help': 'action id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def problem_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            res = self.client.problem.get(oid)

            if self.is_output_text():
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            res = self.client.problem.list()
            headers = ['problemid', 'name', 'status']
            fields = ['problemid', 'name', 'status']
            self.app.render(res, headers=headers, fields=fields, maxsize=40)

    @ex(
        help='list proxys',
        description='list proxys',
        arguments=ZABBIX_PARGS([
            (['-id'], {'help': 'proxy id', 'action': 'store', 'type': str, 'default': None}),
            (['-field'], {'help': 'sort field', 'action': 'store', 'type': str, 'default': 'hostid'}),
        ])
    )
    def proxy_get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            res = self.client.proxy.get(oid)
            if self.is_output_text():
                hosts = res.pop('hosts', [])
                self.app.render(res, details=True)
                self.c('\nhosts', 'underline')
                headers = ['id', 'proxy_hostid', 'host', 'name', 'status', 'maintenance_status']
                fields = ['hostid', 'proxy_hostid', 'host', 'name', 'status', 'maintenance_status']
                self.app.render(hosts, headers=headers, fields=fields)
            else:
                self.app.render(res, details=True)
        else:
            page = self.app.pargs.page
            size = self.app.pargs.size
            field = self.app.pargs.field
            order = self.app.pargs.order
            count = self.client.proxy.list(countOutput=True)
            res = self.client.proxy.list(limit=size, offset=page, sortorder=order.upper(), sortfield=field)
            res = {
                'proxys': res,
                'page': page,
                'count': size,
                'total': count,
                'sort': {
                    'field': field,
                    'order': order
                }
            }
            headers = ['proxyid', 'description', 'proxy_hostid', 'host', 'status', 'available']
            fields = ['proxyid', 'description', 'proxy_hostid', 'host', 'status', 'available']
            self.app.render(res, key='proxys', headers=headers, fields=fields)

    @ex(
        help='add proxy',
        description='add proxy',
        arguments=ZABBIX_ARGS([
            (['name'], {'help': 'proxy hostname', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def proxy_add(self):
        name = self.app.pargs.name
        res = self.client.proxy.create(name)
        self.app.render({'msg': 'add proxy %s' % res['proxyids']})

    @ex(
        help='delete proxy',
        description='delete proxy',
        arguments=ZABBIX_PARGS([
            (['id'], {'help': 'proxy id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def proxy_del(self):
        oid = self.app.pargs.id
        self.client.proxy.delete(oid)
        self.app.render({'msg': 'delete proxy %s' % oid}, headers=['msg'])
