# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte
from typing import List
from beehive3_cli.translate import _


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load_only(app, components: List[str]):
    if components[0] == "platform":
        from beehive3_cli.plugins.openstack.controllers.platform import (
            OpenstackPlatformController,
        )

        app.handler.register(OpenstackPlatformController)
    elif components[0] == "resource":
        from beehive3_cli.plugins.openstack.controllers.resource import OpenstackController

        app.handler.register(OpenstackController)


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
