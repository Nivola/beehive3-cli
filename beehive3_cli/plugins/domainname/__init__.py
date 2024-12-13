# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load(app):
    from beehive3_cli.plugins.domainname.controllers.platform import DnsPlatformController
    from beehive3_cli.plugins.domainname.controllers.resource import DnsController

    app.handler.register(DnsPlatformController)
    app.handler.register(DnsController)
    app.hook.register("post_setup", add_template_dir)
