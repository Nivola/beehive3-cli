# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load(app):
    from beehive3_cli.plugins.openstack.controllers.platform import (
        OpenstackPlatformController,
    )
    from beehive3_cli.plugins.openstack.controllers.resource import OpenstackController
    from beehive3_cli.plugins.openstack.controllers.virt import VirshPlatformController

    app.handler.register(VirshPlatformController)
    app.handler.register(OpenstackPlatformController)
    app.handler.register(OpenstackController)
    app.hook.register("post_setup", add_template_dir)
