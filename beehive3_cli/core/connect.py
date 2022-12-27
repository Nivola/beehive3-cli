# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from base64 import b64decode
from logging import getLogger
from time import time
from urllib.parse import urlencode
from beecell.paramiko_shell.shell import ParamikoShell
from beecell.simple import id_gen, dict_get

logger = getLogger(__name__)


class SshConnectionManager(object):
    def __init__(self, controller):
        self.ctrl = controller
    
    def __node_pre_login(self, ssh_session_id, node, user, key):
        data = {
            'action': 'login',
            'action_id': ssh_session_id,
            'params': {
                'user': '%s.%s' % (user, key.get('uuid', '')),
            }
        }
        uri = '/v1.0/gas/nodes/%s/action' % node['id']
        action = self.ctrl.cmp_put(uri, data=data)
        logger.debug('Send action: %s' % action)

    def __node_post_logout(self, ssh_session_id, start_time, node, user, key, status=None):
        elapsed = round(time() - start_time, 2)

        data = {
            'action': 'logout',
            'action_id': ssh_session_id,
            'status': status,
            'params': {
                'user': '%s.%s' % (user, key.get('uuid', '')),
                'elapsed': elapsed
            }
        }
        uri = '/v1.0/gas/nodes/%s/action' % node['id']
        action = self.ctrl.cmp_put(uri, data=data)
        logger.debug('Send action: %s' % action)

    def __node_post_action(self, ssh_session_id, node, user, key, status=None, cmd='', elapsed=0):
        data = {
            'action': 'cmd: %s' % cmd,
            'action_id': ssh_session_id,
            'status': status,
            'params': {
                'user': '%s.%s' % (user, key.get('uuid', '')),
                'elapsed': elapsed
            }
        }
        uri = '/v1.0/gas/nodes/%s/action' % node['id']
        action = self.ctrl.cmp_put(uri, data=data)
        logger.debug('Send action: %s' % action)

    def __get_ipaddress(self, node):
        ip_address = node['ip_address'].split(':')
        if len(ip_address) == 2:
            port = ip_address[1]
            ip_address = ip_address[0]
        else:
            ip_address = ip_address[0]
            port = 22
        return ip_address, port

    def __get_gateway(self, node, user='gateway'):
        gateway_node_id = None
        if isinstance(node.get('attributes', None), dict):
            gateway_node_id = dict_get(node, 'attributes.gateway')

        if gateway_node_id is None:
            return None

        # fetch node
        uri = '/v1.0/gas/nodes/%s' % gateway_node_id
        try:
            node = self.ctrl.cmp_get(uri).get('node', {})
            ip_address, port = node['ip_address'].split(':')
        except:
            raise Exception('no gateway found')

        # fetch node user
        data = {
            'node_id': node['id'],
            'username': user
        }
        uri = '/v1.0/gas/users'
        users = self.ctrl.cmp_get(uri, data=urlencode(data, doseq=True)).get('users', [])
        if len(users) < 1:
            raise Exception('no gateway user found')
        uri = '/v1.0/gas/users/%s/password' % users[0]['id']
        user = self.ctrl.cmp_get(uri)
        password = user.get('password')

        tunnel = {
            'host': ip_address,
            'port': int(port),
            'user': 'gateway',
            'pwd': password
        }
        return tunnel

    def __ssh2node(self, host_id=None, host_ip=None, host_name=None, user=None, key_file=None, key_string=None,
                   action=None, passwd=None):
        """ssh to a node

        :param host: host ip address
        :param user: ssh user
        :param key_file: private ssh key file [optional]
        :param key_string: private ssh key string [optional]
        :param passwd: user password [optional]
        :return:
        """
        # subsystem = self.subsystem
        # self.subsystem = 'ssh'

        # get ssh node
        # if group_id is not None:
        #     data = {'group_id': group_id}
        data = {}
        uri = '/v1.0/gas/nodes'
        if host_ip is not None:
            data['ip_address'] = host_ip
        elif host_name is not None:
            uri = '/v1.0/gas/nodes/%s' % host_name
        elif host_id is not None:
            uri = '/v1.0/gas/nodes/%s' % host_id
        node = self.ctrl.cmp_get(uri, data=urlencode(data, doseq=True))
        if host_id is not None or host_name is not None:
            node = node.get('node', None)
        else:
            node = node.get('nodes', [])
            if len(node) == 0:
                name = host_ip
                if name is None:
                    name = host_name
                raise Exception('Host %s not found in managed ssh nodes' % name)
            node = node[0]

        # get ssh user
        data = {
            'node_id': node['id'],
            'username': user
        }
        uri = '/v1.0/gas/users'
        users = self.ctrl.cmp_get(uri, data=urlencode(data, doseq=True)).get('users', [])
        if len(users) == 0:
            raise Exception('Host %s user %s not found' % (node['name'], user))

        user = users[0]

        if passwd is not None:
            key_string = None
            key_file = None
            key = {}
        else:
            # get ssh key
            if key_file is None and key_string is None:
                data = {
                    'user_id': user['id']
                }
                uri = '/v1.0/gas/keys'
                key = self.ctrl.cmp_get(uri, data=urlencode(data, doseq=True)).get('keys', [])
                if len(key) == 0:
                    raise Exception('You are not authorized to use key %s' % key)

                key = key[0]

                try:
                    priv_key = key.get('priv_key')
                    key_string = b64decode(priv_key)
                except:
                    raise Exception('private key %s is malformed' % key.get('uuid', ''))

        ssh_session_id = id_gen()
        start_time = time()
        user = user['username']

        def pre_login():
            self.__node_pre_login(ssh_session_id, node, user, key)

        def post_logout(status=None):
            self.__node_post_logout(ssh_session_id, start_time, node, user, key, status=status)

        def post_action(status='OK', cmd='', elapsed=0):
            self.__node_post_action(ssh_session_id, node, user, key, status=status, cmd=cmd, elapsed=elapsed)

        ip_address, port = self.__get_ipaddress(node)
        gateway = self.__get_gateway(node)
        client = ParamikoShell(ip_address, user, port=port, pwd=passwd, keyfile=key_file, keystring=key_string,
                               pre_login=pre_login, post_logout=post_logout, post_action=post_action, tunnel=gateway)

        if action is not None:
            res = action(client)
            logger.debug('Exec action %s' % action)
        else:
            logger.debug('No action defined')

        return res

    def __ssh2node2(self, node=None, user=None, key_file=None, key_string=None, action=None):
        """ssh to a node

        :param host: host ip address
        :param user: ssh user
        :param key_file: private ssh key file [optional]
        :param key_string: private ssh key string [optional]
        :return:
        """
        # get ssh ksy
        if key_file is None and key_string is None:
            data = {'node_id': node['id'], 'username': user}
            uri = '/v1.0/gas/users'
            res = self.ctrl.cmp_get(uri, data=urlencode(data, doseq=True)).get('users')
            res_users = {i['username']: i for i in res}
            if res_users == {}:
                raise Exception('no valid user found')

            data = {'user_id': res[0]['id']}
            uri = '/v1.0/gas/keys'
            key = self.ctrl.cmp_get(uri, data=urlencode(data, doseq=True)).get('keys', [])
            if len(key) == 0:
                raise Exception('You are not authorized to use key %s' % key)

            key = key[0]

            try:
                priv_key = key.get('priv_key')
                key_string = b64decode(priv_key)
            except:
                raise Exception('private key %s is malformed' % key.get('uuid', ''))

        ssh_session_id = id_gen()
        start_time = time()

        def pre_login():
            pass
            # self.__node_pre_login(ssh_session_id, node, user, key)

        def post_logout(status=None):
            pass
            # self.__node_post_logout(ssh_session_id, start_time, node, user, key, status=status)

        def post_action(status='OK', cmd='', elapsed=0):
            self.__node_post_action(ssh_session_id, node, user, key, status=status, cmd=cmd, elapsed=elapsed)

        ip_address, port = self.__get_ipaddress(node)
        gateway = self.__get_gateway(node)
        client = ParamikoShell(ip_address, user, port=port, keyfile=key_file, keystring=key_string,
                               pre_login=pre_login, post_logout=post_logout, post_action=post_action, tunnel=gateway)
        client.timeout = 5.0

        if action is not None:
            res = action(client)
            logger.debug('Exec action %s' % action)
        else:
            logger.debug('No action defined')

        # self.subsystem = subsystem

        return res

    def open_sshnode_file(self, node=None, user=None, key_file=None, key_string=None, filename=None):
        """ssh to a node

        :param host: host ip address
        :param user: ssh user
        :param key_file: private ssh key file [optional]
        :param key_string: private ssh key string [optional]
        :return:
        """
        # subsystem = self.subsystem
        # self.subsystem = 'ssh'

        # get ssh ksy
        if key_file is None and key_string is None:
            data = {
                'user_id': '%s-%s' % (node.get('name'), user)
            }
            uri = '/v1.0/gas/keys'
            key = self.ctrl.cmp_get(uri, data=urlencode(data, doseq=True)).get('keys', [])
            if len(key) == 0:
                raise Exception('You are not authorized to use key %s' % key)

            key = key[0]

            priv_key = key.get('priv_key')
            key_string = b64decode(priv_key)

        ssh_session_id = id_gen()
        start_time = time()

        def pre_login():
            pass
            # self.__node_pre_login(ssh_session_id, node, user, key)

        def post_logout(status=None):
            pass
            # self.__node_post_logout(ssh_session_id, start_time, node, user, key, status=status)

        def post_action(status=None, cmd='', elapsed=0):
            self.__node_post_action(ssh_session_id, node, user, key, status=status, cmd=cmd, elapsed=elapsed)

        ip_address, port = self.__get_ipaddress(node)
        client = ParamikoShell(ip_address, user, port=port, keyfile=key_file, keystring=key_string,
                               pre_login=pre_login, post_logout=post_logout, post_action=post_action)

        client.open_file(filename)

        # self.subsystem = subsystem

        return True

    def ssh2node(self, host_id=None, host_ip=None, host_name=None, user=None, key_file=None, key_string=None,
                 passwd=None):
        """ssh to a node

        :param host: host ip address
        :param user: ssh user
        :param key_file: private ssh key file [optional]
        :param key_string: private ssh key string [optional]
        :param passwd: user password [optional]
        :return:
        """
        def connect(client):
            client.run()
            return None

        return self.__ssh2node(host_id, host_ip, host_name, user, key_file, key_string, action=connect, passwd=passwd)

    def sshcmd2node(self, node=None, user=None, key_file=None, key_string=None, cmd=None, timeout=5.0):
        """ssh to a node

        :param node: node instance
        :param user: ssh user
        :param key_file: private ssh key file [optional]
        :param key_string: private ssh key string [optional]
        :return:
        """
        def runcmd(client):
            if cmd is not None:
                res = client.cmd(cmd, timeout=timeout)
                return res

        return self.__ssh2node2(node, user, key_file, key_string, action=runcmd)

    def sshfile2node(self, node=None, user=None, key_file=None, key_string=None, cmd=None, source=None, dest=None,
                     timeout=1.0):
        """Put or get a file to/from a node

        :param node: node instance
        :param user: ssh user
        :param key_file: private ssh key file [optional]
        :param key_string: private ssh key string [optional]
        :param cmd: can be put or get
        :param source: source file
        :param dest: destination file
        :param timeout: connection timeout
        :return:
        """
        def runcmd(client):
            if cmd is not None and cmd == 'put':
                res = client.file_put(source, dest)
                return res
            elif cmd is not None and cmd == 'get':
                res = client.file_get(source, dest)
                return res
            elif cmd is not None and cmd == 'list':
                res = client.file_list_dir(source)
                return res

        return self.__ssh2node2(node, user, key_file, key_string, action=runcmd)
