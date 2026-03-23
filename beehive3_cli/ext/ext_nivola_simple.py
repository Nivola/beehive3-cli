# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


"""
loads only "enabled" plugins
"""

from typing import List

from cement.core.plugin import PluginHandler
from cement.ext.ext_plugin import CementPluginHandler
from cement.utils.fs import abspath


class NivolaSimplePluginHandler(CementPluginHandler):
    class Meta:
        label = "nivolasimple"

    def __init__(self):
        super().__init__()
        self.disable_plugin_load = False

    def _setup(self, app_obj):
        argv_list: List = app_obj.argv
        if len(argv_list) == 0 or argv_list[0] == "-h":
            # i.e. "beehive" or "beehive -h"
            self.disable_plugin_load = True
            PluginHandler._setup(self, app_obj)
            return

        super()._setup(app_obj)
        return

    def load_plugins(self, plugin_list):
        enabled_plugins = self.get_enabled_plugins()
        for plugin_name in plugin_list:
            if plugin_name in enabled_plugins:
                self.load_plugin(plugin_name)

    def get_enabled_plugins(self):
        if self.disable_plugin_load:
            return []

        return super().get_enabled_plugins()

    def load_plugin(self, plugin_name):
        # hack in order to avoid platform overide without modify existing configurations
        if  plugin_name == "platform":
            plugin_name = "platforms"

        # first attempt to load from plugin_dirs
        for load_dir in self.load_dirs:
            load_dir = abspath(load_dir)

            if self._load_plugin_from_dir(plugin_name, load_dir):
                self._loaded_plugins.append(plugin_name)
                break

        # then from a bootstrap module
        if plugin_name not in self._loaded_plugins:
            if self._load_plugin_from_bootstrap(plugin_name, self.bootstrap):
                self._loaded_plugins.append(plugin_name)

        # print warning and continue
        if plugin_name not in self._loaded_plugins:
            print(f"WARNING: Unable to load plugin '{plugin_name}'.")


def load(app):
    app.handler.register(NivolaSimplePluginHandler)
