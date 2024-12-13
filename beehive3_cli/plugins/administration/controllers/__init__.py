# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive3_cli.core.controller import CliController

from .compute import ComputeAdminController
from .database import DatabaseAdminController
from .efs import EfsAdminController
from .loadbalancer import LoadBalancerAdminController
from .migrationto5 import MigrationP5p6AdminController

# from .debug_utils import ServiceUtilsAdminController, AccountUtilsAdminController


class AdminController(CliController):
    class Meta:
        label = "mgmt"
        # alias = "mgmt"
        stacked_on = "base"
        stacked_type = "nested"
        description = "Administration and objects management"
        help = "Administration and objects management"

    # def _default(self):
    #     self._parser.print_help()
