# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load(app):
    from beehive3_cli.plugins.resource.controllers.container import (
        ResourceOrchestratorController,
    )
    from beehive3_cli.plugins.resource.controllers.entity import ResourceEntityController
    from beehive3_cli.plugins.resource.controllers.link import ResourceLinkController
    from beehive3_cli.plugins.resource.controllers.resource import ResourceController
    from beehive3_cli.plugins.resource.controllers.tag import ResourceTagController

    app.handler.register(ResourceController)
    app.handler.register(ResourceTagController)
    app.handler.register(ResourceLinkController)
    app.handler.register(ResourceEntityController)
    app.handler.register(ResourceOrchestratorController)
    app.hook.register("post_setup", add_template_dir)
