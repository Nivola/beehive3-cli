# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2023 CSI-Piemonte


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load(app):
    from beehive3_cli.plugins.sshgateway.controllers.resource import (
        SshGatewayResourceController,
    )

    app.handler.register(SshGatewayResourceController)
    app.hook.register("post_setup", add_template_dir)
