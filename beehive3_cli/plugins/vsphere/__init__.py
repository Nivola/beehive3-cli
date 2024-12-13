# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte


def add_template_dir(app):
    from os import path

    app.add_template_dir(path.join(path.dirname(__file__), "templates"))


def load(app):
    from beehive3_cli.plugins.vsphere.controllers.platform import VspherePlatformController
    from beehive3_cli.plugins.vsphere.controllers.resource import VsphereController

    app.handler.register(VspherePlatformController)
    # app.handler.register(VspherePlatformCoreController)
    # app.handler.register(VspherePlatformDatacenterController)
    # app.handler.register(VspherePlatformClusterController)
    # app.handler.register(VspherePlatformHostController)
    # app.handler.register(VspherePlatformResourcePoolController)
    # app.handler.register(VspherePlatformDatastoreController)
    # app.handler.register(VspherePlatformFolderController)
    # app.handler.register(VspherePlatformServerController)
    # app.handler.register(VspherePlatformVappController)
    # app.handler.register(VspherePlatformNetworkDvsController)
    # app.handler.register(VspherePlatformNetworkDvpController)
    #
    # app.handler.register(VspherePlatformNetworkSecurityGroupController)
    # app.handler.register(VspherePlatformNetworkDfwController)
    # app.handler.register(VspherePlatformNetworkLgController)
    # app.handler.register(VspherePlatformIppoolController)
    # app.handler.register(VspherePlatformNetworkIpsetController)
    # app.handler.register(VspherePlatformNetworkEdgeController)
    # app.handler.register(VspherePlatformNetworkEdgeRoutingController)
    # app.handler.register(VspherePlatformNetworkEdgeNatController)
    # app.handler.register(VspherePlatformNetworkEdgeL2VpnController)
    # app.handler.register(VspherePlatformNetworkEdgeSslVpnController)
    # app.handler.register(VspherePlatformNetworkEdgeHighAvailabilityController)
    # app.handler.register(VspherePlatformNetworkEdgeDnsController)
    # app.handler.register(VspherePlatformNetworkEdgeDhcpController)
    # app.handler.register(VspherePlatformNetworkEdgeIpsecController)
    # app.handler.register(VspherePlatformNetworkEdgeGslbController)
    # app.handler.register(VspherePlatformNetworkEdgeLoadBalancerController)
    # app.handler.register(VspherePlatformNetworkDlrController)

    app.handler.register(VsphereController)
    app.hook.register("post_setup", add_template_dir)
