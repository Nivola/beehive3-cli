# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load(app):
    from beehive3_cli.plugins.ssh.controllers.dbms import SshDbmsController
    from beehive3_cli.plugins.ssh.controllers.group import (
        SshGroupController,
        SshGroupAuthController,
        SshGroupActionController,
    )
    from beehive3_cli.plugins.ssh.controllers.key import (
        SshKeyController,
        SshKeyAuthController,
    )
    from beehive3_cli.plugins.ssh.controllers.node import (
        SshNodeController,
        SshNodeAuthController,
        SshNodeActionController,
        SshNodeFileController,
        SshNodeAnsibleController,
    )
    from beehive3_cli.plugins.ssh.controllers.operations import SshOperationController
    from beehive3_cli.plugins.ssh.controllers.ssh import SshController
    from beehive3_cli.plugins.ssh.controllers.user import SshUserController

    app.handler.register(SshController)
    app.handler.register(SshOperationController)
    app.handler.register(SshKeyAuthController)
    app.handler.register(SshKeyController)
    app.handler.register(SshUserController)
    app.handler.register(SshDbmsController)
    app.handler.register(SshNodeAnsibleController)
    app.handler.register(SshNodeFileController)
    app.handler.register(SshNodeActionController)
    app.handler.register(SshNodeAuthController)
    app.handler.register(SshNodeController)
    app.handler.register(SshGroupActionController)
    app.handler.register(SshGroupAuthController)
    app.handler.register(SshGroupController)
    app.hook.register("post_setup", add_template_dir)
