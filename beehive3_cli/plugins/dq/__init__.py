# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load(app):
    from beehive3_cli.plugins.dq.controllers.resource_link import DqResourceLinkController
    from beehive3_cli.plugins.dq.controllers import (
        DqResourceController,
        DqServiceController,
    )
    from beehive3_cli.plugins.dq.controllers.entity import DqResourceEntityController
    from beehive3_cli.plugins.dq.controllers.service import DqServiceEntityController

    app.handler.register(DqServiceEntityController)
    app.handler.register(DqServiceController)
    app.handler.register(DqResourceLinkController)
    app.handler.register(DqResourceEntityController)
    app.handler.register(DqResourceController)

    # app.hook.register('post_setup', add_template_dir)
