# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive3_cli.core.controller import CliController


class DqResourceState(object):
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
        description = "resource data quality"
        help = "resource data quality"


class DqServiceController(CliController):
    class Meta:
        label = "dq_service"
        stacked_on = "base"
        stacked_type = "nested"
        description = "service data quality"
        help = "service data quality"
