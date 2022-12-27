# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive3_cli.core.controller import CliController


class ResourceState(object):
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
        label = 'res'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'resource management'
        help = 'resource management'
