# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import os
from beehive3_cli.plugins.awx.controllers.platform import AwxPlatformController
from beehive3_cli.plugins.awx.controllers.resource import AwxController


def add_template_dir(app):
    path = os.path.join(os.path.dirname(__file__), 'templates')
    app.add_template_dir(path)


def load(app):
    app.handler.register(AwxPlatformController)
    app.handler.register(AwxController)
    app.hook.register('post_setup', add_template_dir)
