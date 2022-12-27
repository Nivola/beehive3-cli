# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import os
from beehive3_cli.plugins.dq.controllers.resource_link import DqResourceLinkController
from beehive3_cli.plugins.dq.controllers import DqResourceController, DqServiceController
from beehive3_cli.plugins.dq.controllers.entity import DqResourceEntityController
from beehive3_cli.plugins.dq.controllers.service import DqServiceEntityController


def add_template_dir(app):
    path = os.path.join(os.path.dirname(__file__), 'templates')
    app.add_template_dir(path)


def load(app):
    app.handler.register(DqServiceEntityController)
    app.handler.register(DqServiceController)
    app.handler.register(DqResourceLinkController)
    app.handler.register(DqResourceEntityController)
    app.handler.register(DqResourceController)

    # app.hook.register('post_setup', add_template_dir)
