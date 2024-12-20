# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load(app):
    from .controllers import (
        AdminController,
        ComputeAdminController,
        DatabaseAdminController,
        LoadBalancerAdminController,
        MigrationP5p6AdminController,
    )

    app.handler.register(AdminController)
    app.handler.register(ComputeAdminController)
    app.handler.register(DatabaseAdminController)
    # app.handler.register(EfsAdminController) TODO add back when finished
    app.handler.register(LoadBalancerAdminController)
    # app.handler.register(ServiceUtilsAdminController) # TODO add back when finished
    # app.handler.register(AccountUtilsAdminController) # TODO add back when finished
    # app.hook.register("post_setup", add_template_dir)
    app.handler.register(MigrationP5p6AdminController)
