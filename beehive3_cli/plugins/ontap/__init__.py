# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


def load(app):
    # from beehive3_cli.plugins.ontap.controllers.platform import OntapPlatformController
    from beehive3_cli.plugins.ontap.controllers.resource import OntapResourceController

    # app.handler.register(OntapPlatformController)
    app.handler.register(OntapResourceController)
