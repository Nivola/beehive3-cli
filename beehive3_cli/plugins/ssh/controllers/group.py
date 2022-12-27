# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import sh
from beehive3_cli.core.connect import SshConnectionManager
from beehive3_cli.core.controller import PARGS, ARGS, StringAction
from cement import ex
from beehive3_cli.plugins.ssh.controllers.ssh import SshControllerChild


class SshGroupController(SshControllerChild):
    class Meta:
        stacked_on = 'ssh'
        stacked_type = 'nested'
        label = 'node_groups'
        description = "node group management [DEPRECATED]"
        help = "node group management [DEPRECATED]"

        headers = ['id', 'name', 'desc', 'date', 'objid']
        fields = ['uuid', 'name', 'desc', 'date.creation', '__meta__.objid']

    def pre_command_run(self):
        super(SshGroupController, self).pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help='get node groups [DEPRECATED]',
        description='get node groups [DEPRECATED]',
        arguments=PARGS([
            (['-id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/groups/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)
            self.app.render(res, key='group', details=True)
        else:
            params = []
            data = self.format_paginated_query(params)
            uri = '%s/groups' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='groups', headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help='add node group [DEPRECATED]',
        description='add node group [DEPRECATED]',
        arguments=ARGS([
            (['name'], {'help': 'nodegroup name', 'action': 'store', 'type': str}),
            (['-desc'], {'help': 'nodegroup description', 'action': 'store', 'type': str, 'default': ''}),
            (['-attrib'], {'help': 'nodegroup attributes', 'action': 'store', 'type': str, 'default': ''}),
        ])
    )
    def add(self):
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        attribute = self.app.pargs.attrib
        data = {
            'group': {
                'name': name,
                'desc': desc,
                'attribute': attribute
            }
        }
        uri = '%s/groups' % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add nodegroup %s' % res.get('uuid')})

    @ex(
        help='delete node group [DEPRECATED]',
        description='delete node group [DEPRECATED]',
        arguments=ARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str})
        ])
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = '%s/groups/%s' % (self.baseuri, oid)
        self.cmp_delete(uri, entity='nodegroup %s' % oid)

    @ex(
        help='add node to node group [DEPRECATED]',
        description='add node to node group [DEPRECATED]',
        arguments=ARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str}),
            (['node'], {'help': 'node uuid', 'action': 'store', 'type': str})
        ])
    )
    def node_add(self):
        oid = self.app.pargs.id
        node = self.app.pargs.node
        data = {
            'node': node
        }
        uri = '%s/groups/%s/node' % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({'msg': 'add node %s to nodegroup %s' % (node, oid)})

    @ex(
        help='delete node from node group [DEPRECATED]',
        description='delete node from node group [DEPRECATED]',
        arguments=ARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str}),
            (['node'], {'help': 'node uuid', 'action': 'store', 'type': str})
        ])
    )
    def node_del(self):
        oid = self.app.pargs.id
        node = self.app.pargs.node
        data = {
            'node': node
        }
        uri = '%s/groups/%s/node' % (self.baseuri, oid)
        self.cmp_delete(uri, data=data, entity='node %s from nodegroup %s' % (node, oid))


class SshGroupAuthController(SshControllerChild):
    class Meta:
        label = 'node_groups_auth'
        description = "manage node group authorization [DEPRECATED]"
        help = "manage node group authorization [DEPRECATED]"

    def pre_command_run(self):
        super(SshControllerChild, self).pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help='get node group roles [DEPRECATED]',
        description='get node group roles [DEPRECATED]',
        arguments=ARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str})
        ])
    )
    def role_get(self):
        oid = self.app.pargs.id
        uri = '%s/groups/%s/roles' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key='roles', headers=['name', 'desc'], maxsize=200)

    @ex(
        help='get node group users [DEPRECATED]',
        description='get node group users [DEPRECATED]',
        arguments=ARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str})
        ])
    )
    def user_get(self):
        oid = self.app.pargs.id
        uri = '%s/groups/%s/users' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key='users', headers=['id', 'name', 'desc', 'role'], 
                        fields=['uuid', 'name', 'desc', 'role'], maxsize=200)

    @ex(
        help='add node group role to a user [DEPRECATED]',
        description='add node group role to a user [DEPRECATED]',
        arguments=ARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str}),
            (['role'], {'help': 'authorization role', 'action': 'store', 'type': str}),
            (['user'], {'help': 'authorization user', 'action': 'store', 'type': str}),
        ])
    )
    def user_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {
            'user': {
                'user_id': user,
                'role': role
            }
        }
        uri = '%s/groups/%s/users' % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({'msg': res})

    @ex(
        help='remove node group role from a user [DEPRECATED]',
        description='remove node group role from a user [DEPRECATED]',
        arguments=ARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str}),
            (['role'], {'help': 'authorization role', 'action': 'store', 'type': str}),
            (['user'], {'help': 'authorization user', 'action': 'store', 'type': str}),
        ])
    )
    def user_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {
            'user': {
                'user_id': user,
                'role': role
            }
        }
        uri = '%s/groups/%s/users' % (self.baseuri, oid)
        res = self.cmp_delete(uri, data, entity='role %s from user %s' % (role, user))
        self.app.render({'msg': res})

    @ex(
        help='get node group groups [DEPRECATED]',
        description='get node group groups [DEPRECATED]',
        arguments=ARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str})
        ])
    )
    def group_get(self):
        oid = self.app.pargs.id
        uri = '%s/groups/%s/groups' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key='groups', headers=['id', 'name', 'desc', 'role'], 
                        fields=['uuid', 'name', 'desc', 'role'], maxsize=200)

    @ex(
        help='add node group role to a group [DEPRECATED]',
        description='add node group role to a group [DEPRECATED]',
        arguments=ARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str}),
            (['role'], {'help': 'authorization role', 'action': 'store', 'type': str}),
            (['group'], {'help': 'authorization group', 'action': 'store', 'type': str}),
        ])
    )
    def group_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {
            'group': {
                'group_id': group,
                'role': role
            }
        }
        uri = '%s/groups/%s/groups' % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({'msg': res})

    @ex(
        help='remove node group role from a group [DEPRECATED]',
        description='remove node group role from a group [DEPRECATED]',
        arguments=ARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str}),
            (['role'], {'help': 'authorization role', 'action': 'store', 'type': str}),
            (['group'], {'help': 'authorization group', 'action': 'store', 'type': str}),
        ])
    )
    def group_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {
            'group': {
                'group_id': group,
                'role': role
            }
        }
        uri = '%s/groups/%s/groups' % (self.baseuri, oid)
        res = self.cmp_delete(uri, data, entity='role %s from group %s' % (role, group))
        self.app.render({'msg': res})


class SshGroupActionController(SshControllerChild):
    class Meta:
        label = 'node_groups_action'
        # aliases = ['actions']
        # stacked_on = 'nodegroups'
        # stacked_type = 'nested'
        description = "manage node group action [DEPRECATED]"
        help = "manage node group action [DEPRECATED]"

        headers = ['id', 'date', 'user', 'user-ip', 'action-id', 'action', 'elapsed', 'node-name', 'node-user',
                   'status']
        fields = ['id', 'date', 'user.user', 'user.ip', 'action_id', 'action', 'elapsed', 'node_name',
                  'node_user.name', 'status']

    @ex(
        help='get node groups actions [DEPRECATED]',
        description='get node groups actions [DEPRECATED]',
        arguments=ARGS([
            (['-node'], {'help': 'node filter', 'action': 'store', 'type': str, 'default': '*'}),
            (['-datefrom'], {'help': 'date from. Syntax dd-mm-yyyy', 'action': 'store', 'type': str, 'default': None}),
            (['-dateto'], {'help': 'date to. Syntax dd-mm-yyyy', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def get(self):
        node = self.app.pargs.node
        params = ['datefrom', 'dateto']
        mappings = {}
        data = self.format_paginated_query(params, mappings=mappings)
        uri = '%s/nodes/%s/actions' % (self.baseuri, node)
        res = self.cmp_get(uri, data=data)
        self.app.render(res, key='actions', headers=self._meta.headers, fields=self._meta.fields)

    def __info(self, cmd, size=40, user='root'):
        """Get some info from the nodes [DEPRECATED]
        """
        oid = self.app.pargs.id
        data = self.format_paginated_query([])
        if oid is not None:
            data += '&group_id=%s' % oid

        uri = '%s/nodes' % self.baseuri
        res = self.cmp_get(uri, data=data)

        # print paging
        if 'page' in res:
            print('Page: %s' % res['page'])
            print('Count: %s' % res['count'])
            print('Total: %s' % res['total'])
            print('Order: %s %s' % (res.get('sort').get('field'), res.get('sort').get('order')))

        tmpl = '{uuid:36.36} {name:40.40} {desc:40.40} {ip_address:15.15} {info:%s.%s}' % (size, size)
        line = ''.join(['-' for i in range(40)])
        headers = {'uuid': 'id', 'name': 'name', 'desc': 'desc', 'ip_address': 'ip_address', 'info': 'info'}
        separators = {'uuid': line, 'name': line, 'desc': line, 'ip_address': line, 'info': line}
        print(tmpl.format(**headers))
        print(tmpl.format(**separators))

        scm = SshConnectionManager(self)
        for item in res.get('nodes'):
            item['info'] = None
            try:
                info = scm.sshcmd2node(node=item, user=user, cmd=cmd, timeout=1)
                if len(info['stdout']) > 0:
                    item['info'] = '\n'.join(info['stdout'])
                    print(tmpl.format(**item))
                else:
                    self.app.log.warning(info['stderr'])
            except Exception as ex:
                self.app.log.warning(ex)

    @ex(
        help='get version of operating system [DEPRECATED]',
        description='get version of operating system [DEPRECATED]',
        arguments=PARGS([
            (['id'], {'help': 'node group uuid', 'action': 'store', 'type': str})
        ])
    )
    def sysinfo(self):
        self.__info('cat /etc/redhat-release')

    @ex(
        help='get version of the kernel [DEPRECATED]',
        description='get version of the kernel [DEPRECATED]',
        arguments=PARGS([
            (['id'], {'help': 'node group uuid', 'action': 'store', 'type': str})
        ])
    )
    def kernelinfo(self):
        self.__info('uname -sr')

    @ex(
        help='get uptime',
        description='get uptime',
        arguments=PARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str})
        ])
    )
    def uptime(self):
        self.__info('uptime', size=40)

    @ex(
        help='get date [DEPRECATED]',
        description='get date [DEPRECATED]',
        arguments=PARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str})
        ])
    )
    def date(self):
        self.__info('date', size=40)

    @ex(
        help='get ntpd status [DEPRECATED]',
        description='get ntpd status [DEPRECATED]',
        arguments=PARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str})
        ])
    )
    def ntpd(self):
        self.__info('systemctl status ntpd |grep Active', size=60)

    @ex(
        help='ping nodes [DEPRECATED]',
        description='ping nodes [DEPRECATED]',
        arguments=PARGS([
            (['-id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def ping(self):
        oid = self.app.pargs.id
        data = self.format_paginated_query([])
        if oid is not None:
            data += '&group_id=%s' % oid

        uri = '%s/nodes' % self.baseuri
        res = self.cmp_get(uri, data=data)

        # print paging
        if 'page' in res:
            print('Page: %s' % res['page'])
            print('Count: %s' % res['count'])
            print('Total: %s' % res['total'])
            print('Order: %s %s' % (res.get('sort').get('field'), res.get('sort').get('order')))

        tmpl = '{uuid:36.36} {name:40.40} {desc:40.40} {ip_address:15.15} {info:40.40}'
        line = ''.join(['-' for i in range(40)])
        headers = {'uuid': 'id', 'name': 'name', 'desc': 'desc', 'ip_address': 'ip_address', 'info': 'info'}
        separators = {'uuid': line, 'name': line, 'desc': line, 'ip_address': line, 'info': line}
        print(tmpl.format(**headers))
        print(tmpl.format(**separators))
        for item in res.get('nodes'):
            if item['name'].find('site01') > 0:
                try:
                    info = sh.ping(item['ip_address'], '-c 3', '-qn', '-i 0.3', '-W 1')
                    if info.find('3 received') > 0:
                        item['info'] = self.app.color_error('OK')
                    else:
                        item['info'] = self.app.color_error('KO')
                except Exception as ex:
                    self.app.log.warning(ex)
                    item['info'] = self.app.color_error('KO')

                print(tmpl.format(**item))

    @ex(
        help='ultra ping nodes [DEPRECATED]',
        description='ultra ping nodes [DEPRECATED]',
        arguments=PARGS([
            (['-id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def ultra_ping(self):
        oid = self.app.pargs.id
        data = self.format_paginated_query([])
        if oid is not None:
            data += '&group_id=%s' % oid

        uri = '%s/nodes' % self.baseuri
        res = self.cmp_get(uri, data=data)

        # print paging
        if 'page' in res:
            print('Page: %s' % res['page'])
            print('Count: %s' % res['count'])
            print('Total: %s' % res['total'])
            print('Order: %s %s' % (res.get('sort').get('field'), res.get('sort').get('order')))

        tmpl = '{uuid:36.36} {name:45.45} {desc:40.40} {ip_address:15.15} {info:40.40}'
        line = ''.join(['-' for i in range(50)])
        headers = {'uuid': 'id', 'name': 'name', 'desc': 'desc', 'ip_address': 'ip_address', 'info': 'info'}
        separators = {'uuid': line, 'name': line, 'desc': line, 'ip_address': line, 'info': line}
        print(tmpl.format(**headers))
        print(tmpl.format(**separators))

        scm = SshConnectionManager(self)

        def check(node, name, cmd, response, user='root'):
            error = None
            try:
                info = scm.sshcmd2node(node=node, user=user, cmd=cmd, timeout=1)
                if len(info['stdout']) > 0 and info['stdout'][0] == response:
                    self.app.log.debug(info)
                    res = True
                    msg.append('%s: %s' % (name, self.app.color_error('OK')))
                else:
                    self.app.log.warning(info)
                    res = False
                    error = info['stderr']
                    msg.append('%s: %s' % (name, self.app.color_error('KO')))
            except Exception as ex:
                self.app.log.warning(ex)
                error = str(ex)
                res = False
                msg.append('%s: %s' % (name, self.app.color_error('KO')))

            return res, error

        for item in res.get('nodes'):
            msg = []
            error = None

            # ping node
            try:
                info = sh.ping(item['ip_address'], '-c 3', '-qn', '-i 0.3', '-W 1')
                if info.find('3 received') > 0:
                    res = True
                    msg.append('ping: ' + self.app.color_error('OK'))
                else:
                    res = False
                    msg.append('ping: ' + self.app.color_error('KO'))
            except Exception as ex:
                res = False
                self.app.log.warning(ex)
                msg.append('ping: ' + self.app.color_error('KO'))

            # exec command on node
            if res is True:
                res, error = check(item, 'touch', 'touch /tmp/xxxx && ls /tmp/xxxx && rm /tmp/xxxx', '/tmp/xxxx')

            item['info'] = ' '.join(msg)

            if error is not None:
                error = error.replace('\n', '')
                print(tmpl.format(**item) + ' - ' + self.app.colored_text.output(str(error), 'RED'))
            else:
                print(tmpl.format(**item))



    @ex(
        help='execute command on group of nodes [DEPRECATED]',
        description='execute command on group of nodes [DEPRECATED]',
        arguments=PARGS([
            (['id'], {'help': 'nodegroup uuid', 'action': 'store', 'type': str}),
            (['cmd'], {'help': 'shell command, Syntax: delimit command with. Write /- when use - char. Example: ls /-l',
                       'action': StringAction, 'type': str, 'nargs': '+'}),
            (['-user'], {'help': 'node user name', 'action': 'store', 'type': str, 'default': 'root'})
        ])
    )
    def cmd(self):
        cmd = self.app.pargs.cmd
        user = self.app.pargs.user
        self.__info(cmd, user=user)
