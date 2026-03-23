# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from beehive3_cli.plugins.business.controllers.ecaas import (
    ContainerServiceNamespaceController,
    ContaineraaServiceController
)

from beehive3_cli.translate import _

from beehive3_cli.plugins.business.controllers.service import ServiceStatusController


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load(app):
    from beehive3_cli.plugins.business.controllers.appengaas import (
        AppEngineServiceController,
        AppEngineInstanceController,
    )
    from beehive3_cli.plugins.business.controllers.authority.user import UserController
    from beehive3_cli.plugins.business.controllers.authority.account import (
        AccountController,
        AccountAuthController,
        AccountCapabilityController,
        AccountTagController,
    )
    from beehive3_cli.plugins.business.controllers.authority.capability import (
        AccountCapabilitiesController,
    )
    from beehive3_cli.plugins.business.controllers.authority.catalog import (
        CatalogAuthController,
        CatalogController,
    )
    from beehive3_cli.plugins.business.controllers.authority.division import (
        DivisionController,
        DivisionAuthController,
    )
    from beehive3_cli.plugins.business.controllers.authority.organization import (
        OrganizationController,
        OrganizationAuthController,
    )
    from beehive3_cli.plugins.business.controllers.business import BusinessController
    from beehive3_cli.plugins.business.controllers.cpaas import (
        CPaaServiceController,
        ImageServiceController,
        VolumeServiceController,
        VmServiceController,
        KeyPairServiceController,
        TagServiceController,
        CustomizationServiceController,
    )
    from beehive3_cli.plugins.business.controllers.dbaas import (
        DBaaServiceController,
        DBServiceInstanceController,
    )
    from beehive3_cli.plugins.business.controllers.logaas import (
        LogaaServiceController,
        LoggingServiceInstanceController,
        LoggingServiceSpaceController,
    )
    from beehive3_cli.plugins.business.controllers.maas import (
        MonitoraaServiceController,
        MonitoringServiceInstanceController,
        MonitoringServiceFolderController,
        MonitoringServiceAlertController,
    )
    from beehive3_cli.plugins.business.controllers.netaas import (
        NetaaServiceController,
        DeprecatedServiceController,
        VpcNetServiceController,
        SubnetNetServiceController,
        SecurityGroupNetServiceController,
        GatewayNetServiceController,
        HealthMonitorNetServiceController,
        TargetGroupNetServiceController,
        ListenerNetServiceController,
        LoadBalancerNetServiceController,
        SshGatewayNetServiceController,
        LbaasController,
    )
    from beehive3_cli.plugins.business.controllers.service import (
        ServiceTypeController,
        ServiceDefinitionController,
        ServiceInstanceController,
        ServiceLinkController,
        ServiceTagController,
        ServiceMetricsController,
        ServiceJobSchedulerController,
        ServiceAggregateConsumesController,
    )
    from beehive3_cli.plugins.business.controllers.staas import (
        STaaServiceController,
        STaaServiceEfsController,
    )
    #general
    app.handler.register(TagServiceController)
    app.handler.register(DeprecatedServiceController)

    app.handler.register(BusinessController)
    # cpaas
    app.handler.register(CPaaServiceController)
    app.handler.register(ImageServiceController)
    app.handler.register(VolumeServiceController)
    app.handler.register(VmServiceController)
    app.handler.register(CustomizationServiceController)
    app.handler.register(KeyPairServiceController)
    # app.handler.register(VpcServiceController)
    # app.handler.register(SubnetServiceController)
    # app.handler.register(SecurityGroupServiceController)
    app.handler.register(DBServiceInstanceController)
    app.handler.register(STaaServiceController)
    app.handler.register(STaaServiceEfsController)
    app.handler.register(AppEngineServiceController)
    app.handler.register(AppEngineInstanceController)
    # app.handler.register(ServiceController)
    app.handler.register(ServiceAggregateConsumesController)
    app.handler.register(ServiceJobSchedulerController)
    app.handler.register(ServiceMetricsController)
    app.handler.register(ServiceTagController)
    app.handler.register(ServiceLinkController)
    app.handler.register(ServiceInstanceController)
    app.handler.register(ServiceDefinitionController)
    app.handler.register(ServiceTypeController)
    app.handler.register(ServiceStatusController)
    app.handler.register(CatalogAuthController)
    app.handler.register(CatalogController)
    app.handler.register(AccountCapabilitiesController)
    app.handler.register(AccountTagController)
    app.handler.register(AccountCapabilityController)
    app.handler.register(AccountAuthController)
    app.handler.register(AccountController)
    app.handler.register(DivisionAuthController)
    app.handler.register(DivisionController)
    app.handler.register(OrganizationAuthController)
    app.handler.register(OrganizationController)
    app.handler.register(UserController)
    # netaas
    app.handler.register(NetaaServiceController)
    app.handler.register(VpcNetServiceController)
    app.handler.register(SubnetNetServiceController)
    app.handler.register(SecurityGroupNetServiceController)
    app.handler.register(GatewayNetServiceController)
    app.handler.register(HealthMonitorNetServiceController)
    app.handler.register(TargetGroupNetServiceController)
    app.handler.register(ListenerNetServiceController)
    app.handler.register(LoadBalancerNetServiceController)
    app.handler.register(DBaaServiceController)
    app.handler.register(SshGatewayNetServiceController)
    app.handler.register(LbaasController)
 
    # logaas
    app.handler.register(LogaaServiceController)
    app.handler.register(LoggingServiceInstanceController)
    app.handler.register(LoggingServiceSpaceController)
    # maas
    app.handler.register(MonitoraaServiceController)
    app.handler.register(MonitoringServiceInstanceController)
    app.handler.register(MonitoringServiceFolderController)
    app.handler.register(MonitoringServiceAlertController)
    # ecaas
    app.handler.register(ContaineraaServiceController)
    app.handler.register(ContainerServiceNamespaceController)
    #

    app.hook.register("post_setup", add_template_dir)
