# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from beehive3_cli.core.controller import CliController
from beehive3_cli.translate import _


class DqResourceState():
    PENDING = 0
    BUILDING = 1
    ACTIVE = 2
    UPDATING = 3
    ERROR = 4
    DELETING = 5
    DELETED = 6
    EXPUNGING = 7
    EXPUNGED = 8
    UNKNOWN = 9

    @staticmethod
    def get(state):
        return str(getattr(DqResourceState, state))


class DqResourceController(CliController):
    class Meta:
        label = "dq_res"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("resource data quality")
        help = _("resource data quality")


class DqServiceController(CliController):
    class Meta:
        label = "dq_service"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("service data quality")
        help = _("service data quality")
