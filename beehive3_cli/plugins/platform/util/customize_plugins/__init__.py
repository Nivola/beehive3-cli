# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from logging import getLogger
from beecell.types.type_dict import dict_get

logger = getLogger(__name__)


class CustomizePlugin(object):
    def __init__(self, manager):
        self.manager = manager

    def error(self, msg):
        if self.manager.app.config.get("beehive", "colored") is True:
            msg = self.manager.app.colored_text.error(msg)
        print(msg)

    def write(self, msg):
        # if self.self.manager.app.config.get('beehive', 'colored') is True:
        #     msg = self.self.manager.app.colored_text.error(msg)
        print("OUT   : %s" % msg)

    def has_config(self, configs, config):
        return dict_get(configs, config, default=False)

    def cmp_invoke(self, func, uri, data, msg):
        res = None

        try:
            res = func(uri, data=data)
            if msg is not None:
                logger.info(msg)
                self.write(msg)
        except Exception as ex:
            self.manager.app.error(ex)

        return res

    def cmp_exists(self, uri, msg):
        try:
            self.manager.controller.cmp_get(uri, data="")
            self.error(msg)
            exists = True
        except:
            exists = False

        return exists

    def cmp_exists2(self, uri, msg, data=None, key="volumetypes.0.uuid"):
        res = self.manager.controller.cmp_get(uri, data=data)
        if res.get("count", 0) == 0:
            exists = None
        else:
            exists = dict_get(res, key)

        if exists is not None:
            self.error(msg)

        return exists

    def cmp_get(self, uri, data="", msg=None):
        return self.cmp_invoke(self.manager.controller.cmp_get, uri, data, msg)

    def cmp_post(self, uri, data, msg):
        return self.cmp_invoke(self.manager.controller.cmp_post, uri, data, msg)

    def cmp_put(self, uri, data, msg):
        return self.cmp_invoke(self.manager.controller.cmp_put, uri, data, msg)

    def cmp_patch(self, uri, data, msg):
        return self.cmp_invoke(self.manager.controller.cmp_patch, uri, data, msg)

    def cmp_delete(self, uri, data, msg):
        return self.cmp_invoke(self.manager.controller.cmp_delete, uri, data, msg)

    def run(self, configs):
        pass
