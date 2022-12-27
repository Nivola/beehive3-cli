# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import os
from beehive3_cli.plugins.rancher.controllers.platform import RancherPlatformController
from beehive3_cli.plugins.rancher.controllers.resource import RancherController


def add_template_dir(app):
    path = os.path.join(os.path.dirname(__file__), 'templates')
    app.add_template_dir(path)


def load(app):
    app.handler.register(RancherPlatformController)
    app.handler.register(RancherController)
    app.hook.register('post_setup', add_template_dir)
