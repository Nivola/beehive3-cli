# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from beehive3_cli.core.controller import CliController
from beehive3_cli.translate import _


class ResourceState():
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
        return str(getattr(ResourceState, state))


class ResourceController(CliController):
    class Meta:
        label = "res"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("resource management")
        help = _("resource management")
