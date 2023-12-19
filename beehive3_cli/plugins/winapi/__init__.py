# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load(app):
    from beehive3_cli.plugins.winapi.controllers.platform import WinAPIPlatformController

    # from beehive3_cli.plugins.winapi.controllers.resource import WinAPIController
    app.handler.register(WinAPIPlatformController)
    # app.handler.register(WinAPIController)
    app.hook.register("post_setup", add_template_dir)
