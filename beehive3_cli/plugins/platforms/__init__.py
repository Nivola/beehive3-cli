# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from typing import List


def add_template_dir(app):
    import os

    app.add_template_dir(os.path.join(os.path.dirname(__file__), "templates"))


def load_only(app, subplugin_labels: List[str]):
    from .controllers.platform import CliPlatformController

    app.handler.register(CliPlatformController)
    for lab in subplugin_labels:
        if lab in ('vsphere', 'openstack'):
            continue
        if lab == "console":
            from .controllers.console import ConsoleController

            app.handler.register(ConsoleController)
        elif lab == "cmp":
            from beehive3_cli.plugins.platforms.controllers.cmp import (
                CmpController,
                CmpPostInstallController,
                CmpTestController,
                CmpSubsystemController,
                CmpCustomizeController,
                CmpLog2Controller,
            )

            app.handler.register(CmpController)
            app.handler.register(CmpCustomizeController)
            app.handler.register(CmpPostInstallController)
            app.handler.register(CmpLog2Controller)
            app.handler.register(CmpTestController)
            app.handler.register(CmpSubsystemController)


def load(app):
    from beehive3_cli.plugins.platforms.controllers.cmp import (
        CmpController,
        CmpPostInstallController,
        CmpTestController,
        CmpSubsystemController,
        CmpCustomizeController,
        CmpLog2Controller,
    )
    from beehive3_cli.plugins.platforms.controllers.nginx import NginxController
    from beehive3_cli.plugins.platforms.controllers.scheduler import (
        CmpSchedulerController,
        CmpSchedulerTaskController,
        CmpSchedulerSchedController,
    )
    from beehive3_cli.plugins.platforms.controllers.elastic import ElkController
    from beehive3_cli.plugins.platforms.controllers.console import ConsoleController
    from beehive3_cli.plugins.platforms.controllers.datadomain import DataDomainController
    from beehive3_cli.plugins.platforms.controllers.firewall import FirewallLogController
    from beehive3_cli.plugins.platforms.controllers.graphite import GraphiteController
    from beehive3_cli.plugins.platforms.controllers.k8s import K8sController
    from beehive3_cli.plugins.platforms.controllers.mariadb import (
        MysqlController,
        MysqlTableController,
        MysqlSchemaController,
        MysqlUserController,
    )
    from beehive3_cli.plugins.platforms.controllers.platform import CliPlatformController
    from beehive3_cli.plugins.platforms.controllers.redis import RedisController

    # from .controllers.zabbix import ZabbixPlatformController
    from beehive3_cli.plugins.platforms.controllers.ontap import OntapController

    app.handler.register(DataDomainController)
    # app.handler.register(ZabbixPlatformController)
    app.handler.register(CliPlatformController)
    app.handler.register(FirewallLogController)
    app.handler.register(ElkController)
    app.handler.register(NginxController)
    app.handler.register(RedisController)
    app.handler.register(MysqlTableController)
    app.handler.register(MysqlUserController)
    app.handler.register(MysqlSchemaController)
    app.handler.register(MysqlController)
    app.handler.register(K8sController)
    app.handler.register(CmpController)
    app.handler.register(CmpCustomizeController)
    app.handler.register(CmpPostInstallController)
    app.handler.register(CmpLog2Controller)
    app.handler.register(CmpTestController)
    # app.handler.register(CmpApiTestController)
    app.handler.register(CmpSubsystemController)
    # app.handler.register(CmpInstanceController)
    app.handler.register(CmpSchedulerController)
    app.handler.register(CmpSchedulerTaskController)
    app.handler.register(CmpSchedulerSchedController)
    app.handler.register(ConsoleController)
    app.handler.register(GraphiteController)
    app.handler.register(OntapController)
    app.hook.register("post_setup", add_template_dir)
