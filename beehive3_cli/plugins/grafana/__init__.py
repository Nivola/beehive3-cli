# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte

import os
from beehive3_cli.plugins.grafana.controllers.platform import GrafanaPlatformController
from beehive3_cli.plugins.grafana.controllers.resource import GrafanaResourceController


def add_template_dir(app):
    path = os.path.join(os.path.dirname(__file__), 'templates')
    app.add_template_dir(path)


def load(app):
    app.handler.register(GrafanaPlatformController)
    app.handler.register(GrafanaResourceController)
    app.hook.register('post_setup', add_template_dir)
