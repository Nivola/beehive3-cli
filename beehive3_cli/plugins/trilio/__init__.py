# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import os
from beehive3_cli.plugins.trilio.controllers.platform import TrilioPlatformController
# from beehive3_cli.plugins.trilio.controllers.resource import TrilioController


def add_template_dir(app):
    path = os.path.join(os.path.dirname(__file__), 'templates')
    app.add_template_dir(path)


def load(app):
    app.handler.register(TrilioPlatformController)
    # app.handler.register(TrilioController)
    app.hook.register('post_setup', add_template_dir)
