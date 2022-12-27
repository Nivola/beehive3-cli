# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from re import compile
from os import path, listdir
from logging import getLogger
from beecell.types.type_dict import dict_get, dict_set
from beehive3_cli.core.util import load_config
from beehive3_cli.plugins.platform.util.customize_plugins.auth import AuthCustomizePlugin
from beehive3_cli.plugins.platform.util.customize_plugins.resource import ResourceCustomizePlugin
from beehive3_cli.plugins.platform.util.customize_plugins.service import ServiceCustomizePlugin
from beehive3_cli.plugins.platform.util.customize_plugins.ssh import SshCustomizePlugin

logger = getLogger(__name__)


class CostomizeManager(object):
    def __init__(self, controller):
        self.controller = controller
        self.app = controller.app
        self.configs = {}
        self.apply = {}
        self.filter = None
        self.config_path = controller.config_path

        self.plugins = [
            AuthCustomizePlugin,
            SshCustomizePlugin,
            ResourceCustomizePlugin,
            ServiceCustomizePlugin
        ]

    def __check_type(self, config):
        config_path = '%s/%s' % (self.config_path, config)
        if path.isfile(config_path + '.yaml'):
            return 'yaml'
        elif path.isfile(config_path + '.json'):
            return 'json'
        elif path.isfile(config_path + '.yml'):
            return 'yaml'

    def __explore_dir(self, folder, pattern, available_configs, prefix=''):
        for f in listdir(folder):
            if pattern.match(f) is not None:
                available_configs.append(prefix + f.replace('.json', '').replace('.yaml', '').replace('.yml', ''))
            elif path.isdir(folder + '/' + f):
                available_configs = self.__explore_dir(folder + '/' + f, pattern, available_configs,
                                                       prefix=prefix + f + '/')
        return available_configs

    def get_available_configs(self):
        # get configs
        configs = []
        pattern = compile(r".*\.json|.*\.yaml|.*\.yml")
        available_configs = []
        self.__explore_dir(self.config_path, pattern, available_configs)

        for item in available_configs:
            configs.append({'name': item, 'type': self.__check_type(item)})
        logger.debug('Available post install config are: %s' % configs)
        return configs

    def show_configs(self, config):
        config_path = '%s/%s' % (self.config_path, config)
        if path.isfile(config_path + '.yaml'):
            config_path = config_path + '.yaml'
        elif path.isfile(config_path + '.json'):
            config_path = config_path + '.json'
        elif path.isfile(config_path + '.yml'):
            config_path = config_path + '.yml'
        all_configs = load_config(config_path)
        return all_configs

    def load_configs(self, config):
        config_path = '%s/%s' % (self.config_path, config)
        if path.isfile(config_path + '.yaml'):
            config_path = config_path + '.yaml'
        elif path.isfile(config_path + '.json'):
            config_path = config_path + '.json'
        elif path.isfile(config_path + '.yml'):
            config_path = config_path + '.yml'
        all_configs = load_config(config_path)
        # self.apply = all_configs.get('apply')
        self.apply = {}
        self.configs = all_configs.get('configs')

    def load_file(self, config):
        config_path = '%s/%s' % (self.config_path, config)
        data = self.controller.load_file(config_path)
        return data

    def apply_filter(self, config_filter):
        config_filter = config_filter.split(':')
        if len(config_filter) != 3:
            raise Exception('Filter must be <entity list key>:<key to filter>:<value>')
        entity = config_filter[0]
        key = config_filter[1]
        value = config_filter[2]
        configs = dict_get(self.configs, entity, default=[])
        configs = filter(lambda x: x.get(key, None) == value, configs)
        dict_set(self.configs, entity, configs)

    def run(self, sections):
        # replace section values
        new_apply = sections
        if new_apply is not None:
            new_apply = new_apply.split(',')
            for item in new_apply:
                self.apply[item] = True

        for plugin in self.plugins:
            plugin_runner = plugin(self)
            res = plugin_runner.run(self.configs)
