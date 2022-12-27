# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte
# @Author Nazha Ahmad

import os
from beehive3_cli.plugins.metrics.controllers.metrics import MetricsController


def add_template_dir(app):
    path = os.path.join(os.path.dirname(__file__), 'templates')
    app.add_template_dir(path)


def load(app):
    app.handler.register(MetricsController)
    app.hook.register('post_setup', add_template_dir)
