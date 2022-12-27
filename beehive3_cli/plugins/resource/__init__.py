# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import os
from beehive3_cli.plugins.resource.controllers.container import ResourceOrchestratorController
from beehive3_cli.plugins.resource.controllers.entity import ResourceEntityController
from beehive3_cli.plugins.resource.controllers.link import ResourceLinkController
from beehive3_cli.plugins.resource.controllers.resource import ResourceController
from beehive3_cli.plugins.resource.controllers.tag import ResourceTagController


def add_template_dir(app):
    path = os.path.join(os.path.dirname(__file__), 'templates')
    app.add_template_dir(path)


def load(app):
    app.handler.register(ResourceController)
    app.handler.register(ResourceTagController)
    app.handler.register(ResourceLinkController)
    app.handler.register(ResourceEntityController)
    app.handler.register(ResourceOrchestratorController)
    app.hook.register('post_setup', add_template_dir)
