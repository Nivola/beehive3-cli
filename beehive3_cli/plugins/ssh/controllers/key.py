# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from base64 import b64decode, b64encode
from beehive3_cli.core.controller import PARGS, ARGS
from cement import ex
from beehive3_cli.core.util import load_config
from beehive3_cli.plugins.ssh.controllers.ssh import SshControllerChild


class SshKeyController(SshControllerChild):
    class Meta:
        stacked_on = 'ssh'
        stacked_type = 'nested'
        label = 'keys'
        description = "ssh key management [DEPRECATED]"
        help = "ssh key management [DEPRECATED]"

        headers = ['id', 'name', 'desc', 'date', 'pub_key']
        fields = ['uuid', 'name', 'desc', 'date.creation', 'pub_key']

    def pre_command_run(self):
        super(SshKeyController, self).pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help='get ssh keys',
        description='get ssh keys',
        arguments=PARGS([
            (['-id'], {'help': 'ssh key uuid', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/keys/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)
            self.app.render(res, key='key', details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/keys' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='keys', headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help='export key private and public key as string',
        description='export key private and public key as string',
        arguments=ARGS([
            (['id'], {'help': 'ssh key uuid', 'action': 'store', 'type': str}),
        ])
    )
    def export(self):
        oid = self.app.pargs.id
        uri = '%s/keys/%s' % (self.baseuri, oid)
        res = self.cmp_get(uri).get('key')
        print('Private key:')
        print(b64decode(res.get('priv_key')).decode('utf-8'))
        print('Public key:')
        print(b64decode(res.get('pub_key')).decode('utf-8'))

    @ex(
        help='load an existing ssh key',
        description='load an existing ssh key',
        arguments=PARGS([
            (['name'], {'help': 'ssh key uuid', 'action': 'store', 'type': str}),
            (['priv-key'], {'help': 'file where is located private key', 'action': 'store', 'type': str}),
            (['pub-key'], {'help': 'file where is located the public key', 'action': 'store', 'type': str, 
                           'default': None}),
            (['-desc'], {'help': 'key description', 'action': 'store', 'type': str, 'default': ''}),
            (['-attrib'], {'help': 'key attribute', 'action': 'store', 'type': str, 'default': ''}),
        ])
    )
    def load(self):
        name = self.app.pargs.name
        priv_key = self.app.pargs.priv_key
        pub_key = self.app.pargs.pub_key
        desc = self.app.pargs.desc
        attribute = self.app.pargs.attrib

        priv_key = load_config(priv_key)
        if pub_key is not None:
            pub_key = load_config(pub_key)
        else:
            pub_key = ''
        data = {
            'key': {
                'name': name,
                'priv_key': b64encode(priv_key),
                'pub_key': b64encode(pub_key),
                'desc': desc,
                'attribute': attribute
            }
        }
        uri = '%s/keys' % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': res})

    @ex(
        help='add ssh key',
        description='add ssh key',
        arguments=ARGS([
            (['name'], {'help': 'ssh key uuid', 'action': 'store', 'type': str}),
            (['-type'], {'help': 'key type like dsa, rsa, ecda [default=rsa]', 'action': 'store', 'type': str,
                         'default': 'rsa'}),
            (['-bits'], {'help': 'key length [default=2048]', 'action': 'store', 'type': str, 'default': 2048}),
            (['-desc'], {'help': 'key description', 'action': 'store', 'type': str, 'default': ''}),
            (['-attrib'], {'help': 'key attribute', 'action': 'store', 'type': str, 'default': ''}),
        ])
    )
    def add(self):
        name = self.app.pargs.name
        key_type = self.app.pargs.type
        bits = self.app.pargs.bits
        desc = self.app.pargs.desc
        attribute = self.app.pargs.attrib
        if key_type not in ['rsa']:
            raise Exception('Only rsa key are supported')
        data = {
            'key': {
                'name': name,
                'type': key_type,
                'bits': bits,
                'desc': desc,
                'attribute': attribute
            }
        }
        uri = '%s/keys' % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add key %s with uuid: %s' % (name, res.get('uuid'))})

    @ex(
        help='delete ssh key',
        description='delete key',
        arguments=ARGS([
            (['id'], {'help': 'ssh key uuid', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = '%s/keys/%s' % (self.baseuri, oid)
        res = self.cmp_delete(uri, data='', entity='ssh key %s' % oid)


class SshKeyAuthController(SshControllerChild):
    class Meta:
        label = 'keys_auth'
        description = "manage key authorization"
        help = "manage key authorization"

    @ex(
        help='get key roles',
        description='get key roles',
        arguments=ARGS([
            (['id'], {'help': 'key uuid', 'action': 'store', 'type': str})
        ])
    )
    def role_get(self):
        oid = self.app.pargs.id
        uri = '%s/keys/%s/roles' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key='roles', headers=['name', 'desc'], maxsize=200)

    @ex(
        help='get key users',
        description='get key users',
        arguments=ARGS([
            (['id'], {'help': 'key uuid', 'action': 'store', 'type': str})
        ])
    )
    def user_get(self):
        oid = self.app.pargs.id
        uri = '%s/keys/%s/users' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key='users', headers=['id', 'name', 'desc', 'role'],
                        fields=['uuid', 'name', 'desc', 'role'], maxsize=200)

    @ex(
        help='add key role to a user',
        description='add key role to a user',
        arguments=ARGS([
            (['id'], {'help': 'key uuid', 'action': 'store', 'type': str}),
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
        uri = '%s/keys/%s/users' % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({'msg': res})

    @ex(
        help='remove key role from a user',
        description='remove key role from a user',
        arguments=ARGS([
            (['id'], {'help': 'key uuid', 'action': 'store', 'type': str}),
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
        uri = '%s/keys/%s/users' % (self.baseuri, oid)
        res = self.cmp_delete(uri, data, entity='role %s from user %s' % (role, user))
        self.app.render({'msg': res})

    @ex(
        help='get key groups',
        description='get key groups',
        arguments=ARGS([
            (['id'], {'help': 'key uuid', 'action': 'store', 'type': str})
        ])
    )
    def group_get(self):
        oid = self.app.pargs.id
        uri = '%s/keys/%s/groups' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key='groups', headers=['id', 'name', 'desc', 'role'],
                        fields=['uuid', 'name', 'desc', 'role'], maxsize=200)

    @ex(
        help='add key role to a group',
        description='add key role to a group',
        arguments=ARGS([
            (['id'], {'help': 'key uuid', 'action': 'store', 'type': str}),
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
        uri = '%s/keys/%s/groups' % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({'msg': res})

    @ex(
        help='remove key role from a group',
        description='remove key role from a group',
        arguments=ARGS([
            (['id'], {'help': 'key uuid', 'action': 'store', 'type': str}),
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
        uri = '%s/keys/%s/groups' % (self.baseuri, oid)
        res = self.cmp_delete(uri, data, entity='role %s from group %s' % (role, group))
        self.app.render({'msg': res})
