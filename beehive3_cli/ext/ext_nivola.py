#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

"""
custom plugin handler that conditionally loads only
what is required by the command being executed
"""

from typing import List

from cement.ext.ext_plugin import CementPluginHandler, LOG
from cement.core.plugin import PluginHandler


class NivolaPluginHandler(CementPluginHandler):
    # mapping between keyword and plugin label (label in controller Meta classes)
    PLUGIN_KW_LAB = {
        "mgmt": "administration",
        "bu": "business",
        "auth": "auth",
        "res": "resource",
        "platform": "platform",
        "vsphere": "vsphere",
        "res-vsphere": "vsphere",
        "console": "console",
        "cmp": "cmp",
    }

    # plugin dependencies not enforced directly by imports
    PLUGIN_LAB_DEPS = {
        "vsphere": "platform",
        "openstack": "platform",
        "console": "platform-nested",
        "cmp": "platform-nested",
    }

    class Meta:
        label = "nivola"

    def __init__(self):
        super().__init__()
        self.disable_plugin_load = False
        self.load_all = False
        self.plugins_to_load = []
        self.plugin_deps = {}

    @staticmethod
    def _determine_label(keyword: str):
        return NivolaPluginHandler.PLUGIN_KW_LAB.get(keyword, None)

    @staticmethod
    def _determine_additional_dependencies(plugin_label: str, item: str):
        """
        plugin_label
        item: cmd item for special cases
        """
        if "res-" in item:
            dep = item.replace("res-", "")
            return dep
        return NivolaPluginHandler.PLUGIN_LAB_DEPS.get(plugin_label, None)

    def _add_only_once(self, plugin_label):
        if plugin_label not in self.plugins_to_load:
            self.plugins_to_load.append(plugin_label)
            self.plugin_deps[plugin_label] = set()

    def _setup(self, app_obj):
        argv_list: List = app_obj.argv
        if len(argv_list) == 0 or argv_list[0] == "-h":
            # i.e. "beehive" or "beehive -h"
            self.disable_plugin_load = True
            PluginHandler._setup(self, app_obj)
            return

        # print(argv_list)
        for item in argv_list:
            nested = False
            # for each param on command line, try to determine if it's a keyword
            label = NivolaPluginHandler._determine_label(item)
            # stop as soon as it isn't one
            if label is None:
                break

            # print(item + ' ' + label)
            if label:
                dep = NivolaPluginHandler._determine_additional_dependencies(label, item)
                if dep is not None:
                    # special case
                    if "nested" in dep:
                        nested = True
                        dep = dep.replace("-nested", "")

                    # if not already present, add it before plugin which depends on it
                    self._add_only_once(dep)
                    # update sub plugins to load
                    if "res-" in item:
                        # i.e. res-vsphere res-openstack res-...
                        self.plugin_deps[label].add("resource")
                    else:
                        self.plugin_deps[dep].add(
                            label
                        )  # i.e. add init dependencies for plugin which has dependency on this

                if not "res-" in item and not nested:
                    # add plugin to plugins to load if not already there
                    self._add_only_once(label)
                    if dep is not None:
                        # add reverse dep for partial load
                        self.plugin_deps[label].add(dep)

        if len(self.plugins_to_load) == 0:
            # assume error or not mapped
            # load all plugins
            self.load_all = True
            LOG.warning("Unable to determine conditional load, loading all plugins")

        super()._setup(app_obj)
        return

    def load_plugin(self, plugin_name):
        # print(plugin_name)
        """
        if plugin_name == self.first_plugin or plugin_name=="platform":
            super().load_plugin(plugin_name)
        """
        if plugin_name in self.plugins_to_load or self.load_all:
            super().load_plugin(plugin_name)
        else:
            LOG.warning(f"plugin {plugin_name} will not be loaded")

    def load_plugins(self, plugin_list):
        # super().load_plugins(plugin_list)
        enabled_plugins = self.get_enabled_plugins()
        for plugin_name in plugin_list:
            if plugin_name in enabled_plugins:
                self.load_plugin(plugin_name)

    def get_enabled_plugins(self):
        if self.disable_plugin_load:
            return []

        if len(self.plugins_to_load) > 0:
            return self.plugins_to_load
        # if here plugins must be loaded
        # but we don't have a list -> load all plugins
        enabled = super().get_enabled_plugins()
        return enabled


def load(app):
    app.handler.register(NivolaPluginHandler)
