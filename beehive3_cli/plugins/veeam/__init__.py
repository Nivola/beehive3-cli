# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2023 CSI-Piemonte


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load(app):
    from beehive3_cli.plugins.veeam.controllers.platform import VeeamPlatformController

    # from beehive3_cli.plugins.veeam.controllers.resource import VeeamResourceController

    app.handler.register(VeeamPlatformController)
    # app.handler.register(VeeamResourceController)
    app.hook.register("post_setup", add_template_dir)
