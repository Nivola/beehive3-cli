# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2023 CSI-Piemonte


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load(app):
    from beehive3_cli.plugins.zabbix.controllers.platform import ZabbixPlatformController
    from beehive3_cli.plugins.zabbix.controllers.resource import ZabbixResourceController

    app.handler.register(ZabbixPlatformController)
    app.handler.register(ZabbixResourceController)
    app.hook.register("post_setup", add_template_dir)
