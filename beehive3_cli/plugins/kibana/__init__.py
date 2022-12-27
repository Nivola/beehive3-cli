# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte

import os
from beehive3_cli.plugins.kibana.controllers.platform import KibanaPlatformController
from beehive3_cli.plugins.kibana.controllers.resource import ElkResourceController


def add_template_dir(app):
    path = os.path.join(os.path.dirname(__file__), 'templates')
    app.add_template_dir(path)


def load(app):
    app.handler.register(KibanaPlatformController)
    app.handler.register(ElkResourceController)
    app.hook.register('post_setup', add_template_dir)
