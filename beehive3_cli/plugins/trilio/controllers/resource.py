# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beecell.simple import truncate
from beehive3_cli.core.controller import BaseController, PARGS, ARGS
from cement import ex


class OpenstackTrilioController(BaseController):
    class Meta:
        label = 'res_trilio'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "openstack trilio orchestrator"
        help = "openstack trilio orchestrator"

        cmp = {'baseuri': '/v1.0/nrs/openstack', 'subsystem': 'resource'}

        headers = ['id', 'ext_id', 'name', 'desc', 'parent', 'container', 'state']
        fields = ['id', 'ext_id', 'name', 'desc', 'parent', 'container', 'state']

    def pre_command_run(self):
        super(OpenstackTrilioController, self).pre_command_run()

        self.configure_cmp_api_client()
