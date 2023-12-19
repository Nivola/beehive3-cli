# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load(app):
    from beehive3_cli.plugins.rancher.controllers.platform import RancherPlatformController
    from beehive3_cli.plugins.rancher.controllers.resource import RancherController

    app.handler.register(RancherPlatformController)
    app.handler.register(RancherController)
    app.hook.register("post_setup", add_template_dir)
