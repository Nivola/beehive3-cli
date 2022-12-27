# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import os
from beehive3_cli.plugins.openstack.controllers.platform import OpenstackPlatformController
from beehive3_cli.plugins.openstack.controllers.resource import OpenstackController
from beehive3_cli.plugins.openstack.controllers.virt import VirshPlatformController


def add_template_dir(app):
    path = os.path.join(os.path.dirname(__file__), 'templates')
    app.add_template_dir(path)


def load(app):
    app.handler.register(VirshPlatformController)
    app.handler.register(OpenstackPlatformController)
    app.handler.register(OpenstackController)
    app.hook.register('post_setup', add_template_dir)
