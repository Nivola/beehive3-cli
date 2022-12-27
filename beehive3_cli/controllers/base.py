# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from time import time

from beecell.types.type_string import str2bool

start = time()

from cement import ex
from cryptography.fernet import Fernet
from six import ensure_text, ensure_binary
from beecell.password import random_password
from beehive3_cli.core.controller import CliController
from beehive3_cli.core.util import list_environments, load_environment_config
from beehive3_cli.core.version import get_version

VERSION_BANNER = """
Beehive3 Console %s
Copyright (c) 2019-2022 CSI Piemonte
""" % (get_version())


class Base(CliController):
    class Meta:
        label = 'base'

        # text displayed at the top of --help output
        description = 'Beehive Console'

        # text displayed at the bottom of --help output
        epilog = 'Usage: beehive command1 --foo bar'

        # controller level arguments. ex: 'beehive --version'
        arguments = [
            (['-v', '--version'], {'action': 'version', 'version': VERSION_BANNER}),
            (['--time'], {'action': 'store_true', 'dest': 'time', 'help': 'Print command execution time'}),
        ]

    def _default(self):
        """Default action if no sub-command is passed."""
        self.app.args.print_help()

    @ex(
        help='get bash completion script',
        description='get bash completion script',
        arguments=[]
    )
    def bash_completion(self):
        ctrl_idx = {}
        for c in self._controllers:
            parent = c._meta.stacked_on.replace('_', '-')
            label = c._meta.label.replace('_', '-')

            # set child sections
            try:
                ctrl_idx[parent].append(label)
            except:
                ctrl_idx[parent] = [label]
            commands = c._collect_commands()

            # set child commands
            for command in commands:
                command_label = command['label']

                try:
                    ctrl_idx[label].append(command_label)
                except:
                    ctrl_idx[label] = [command_label]

                # set command arguments
                for argument in command.get('arguments', []):
                    action = argument[1].get('action', None)
                    try:
                        for a in argument[0]:
                            if a[0] != '-':
                                pass
                                # a = '%s..' % a
                            elif action == 'store':
                                a = '%s' % a
                                ctrl_idx[label+':'+command_label].append(a)
                            else:
                                ctrl_idx[label + ':' + command_label].append(a)
                    except:
                        ctrl_idx[label+':'+command_label] = []
                        for a in argument[0]:
                            if a[0] != '-':
                                pass
                                # a = '%s..' % a
                            elif action == 'store':
                                a = '%s' % a
                                ctrl_idx[label+':'+command_label].append(a)
                            else:
                                ctrl_idx[label + ':' + command_label].append(a)

        script = [
        ]
        for k, v in ctrl_idx.items():
            script.append('CMDS[{key}]=\'{values}\''.format(key=k, values=' '.join(v)))

        print('\n'.join(script))

    @ex(
        help='get bash completion envs',
        description='get bash completion envs',
        arguments=[]
    )
    def bash_completion_envs(self):
        envs = list_environments(self.app)
        print(' '.join(envs))

    @ex(
        help='list available environments',
        description='list available environments',
        arguments=[]
    )
    def envs(self):
        envs = list_environments(self.app)
        defualt_env = self.app.config.get('beehive', 'default_env')
        current_env = self.app.env

        res = []
        headers = ['name', 'version', 'current', 'is_default', 'has_cmp']
        for env in envs:
            try:
                value = load_environment_config(self.app, env)
                version = value.get('version', None)
                if env == 'default':
                    continue
                item = {'name': env, 'version': version, 'current': False, 'is_default': False, 'has_cmp': False}
                if env == defualt_env:
                    item['is_default'] = True
                if env == current_env:
                    item['current'] = True
                if len(value.get('cmp', {}).get('endpoint', [])) > 0:
                    item['has_cmp'] = True
                orchestrators = value.get('orchestrators', {})
                for k in list(orchestrators.keys()):
                    v = orchestrators.get(k, {})
                    if v is None:
                        v = {}
                    item[k] = ','.join(v.keys())
                    if k not in headers:
                        headers.append(k)

                res.append(item)
            except:
                self.app.log.warning('no correct config found for environment %s' % env)
        self.app.render(res, headers=headers)

    @ex(
        help='generate password',
        description='generate password',
        arguments=[
            (['-length'], {'help': 'password length', 'action': 'store', 'type': str, 'default': 12}),
            (['-strong'], {'help': 'password strong', 'action': 'store', 'type': str, 'default': 'true'}),
        ]
    )
    def gen_password(self):
        length = self.app.pargs.length
        strong = str2bool(self.app.pargs.strong)
        pwd = random_password(length=int(length), strong=strong)
        self.app.render({'pwd': pwd}, headers=['pwd'], maxsize=500)

    @ex(
        help='generate fernet key for symmetric encryption',
        description='generate fernet key for symmetric encryption',
        arguments=[]
    )
    def gen_key(self):
        """Generate fernet key for symmetric encryption
        """
        key = Fernet.generate_key()
        self.app.render({'key': key}, headers=['key'])

    @ex(
        help='encrypt data with symmetric encryption',
        description='encrypt data with symmetric encryption',
        arguments=[
            (['data'], {'help': 'data to encrypt', 'action': 'store', 'type': str}),
            (['key'], {'action': 'store', 'help': 'secret key to use for encryption/decryption'}),
        ]
    )
    def encrypt(self):
        # self.check_secret_key()
        data = self.app.pargs.data
        key = self.app.pargs.key
        key = ensure_binary(key)
        cipher_suite = Fernet(key)
        cipher_text = cipher_suite.encrypt(ensure_binary(data))
        res = [
            {'encrypt_data': '$BEEHIVE_VAULT;AES128 | %s' % ensure_text(cipher_text)}
        ]
        self.app.render(res, headers=['encrypt_data'], maxsize=400)

    @ex(
        help='decrypt quoted data with symmetric encryption',
        description='decrypt quoted data with symmetric encryption',
        arguments=[
            (['data'], {'help': 'data to decrypt', 'action': 'store', 'type': str}),
            (['key'], {'action': 'store', 'help': 'secret key to use for encryption/decryption'}),
        ]
    )
    def decrypt(self):
        # self.check_secret_key()
        data = self.app.pargs.data
        key = self.app.pargs.key
        key = ensure_binary(key)
        cipher_suite = Fernet(key)
        cipher_text = cipher_suite.decrypt(ensure_binary(data))
        self.app.render({'decrypt_data': cipher_text}, headers=['decrypt_data'], maxsize=200)
