#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


from cement import ex

from beehive3_cli.core.controller import BaseController, PARGS, ARGS
from beehive3_cli.translate import _


class OntapResourceController(BaseController):
    class Meta: # type: ignore
        label = "res_ontap"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("ontap orchestrator")
        help = _("ontap orchestrator")

        cmp = {"baseuri": "/v1.0/nrs/ontap", "subsystem": "resource"}

        headers = [
            "id",
            "uuid",
            "name",
            "desc",
            "ext_id",
            "parent",
            "container",
            "state",
        ]
        fields = [
            "id",
            "uuid",
            "name",
            "desc",
            "ext_id",
            "parent",
            "container",
            "state",
        ]

    def pre_command_run(self):
        super().pre_command_run()
        self.configure_cmp_api_client()
        self.api.client.set_print_curl(self.app.curl)

    @ex(
        help=_("get deletable snaplock volumes"),
        description=_("get snaplock volumes which can be deleted at the current date"),
        arguments=PARGS([])
    )
    def get_deletable_snaplocks(self):
        headers=["id","uuid","name","delete_after"]
        fields=["id","uuid","name","attributes.delete_after"]
        res = self.api.resource.ontap.volume.list(
            filter_deletable_snaplocks=True,
            size=self.app.pargs.size,
            page=self.app.pargs.page
        )
        self.app.render(res, key="volumes", headers=headers, fields=fields)

    @ex(
        help=_("update physical resource attributes with awx params"),
        description="update physical resource attributes with awx params",
        arguments=ARGS(
            [
                (
                    ["volume"],
                    {
                        "help": _("volume id"),
                        "action": "store",
                        "type": str,
                    }
                ),
            ]
        ),
    )
    def vol_awx_params_update(self):
        volume_id = self.app.pargs.volume
        volume = self.api.resource.ontap.volume.get(volume_id).get("volume")

        container_id = volume.get("container")

        volume_site = None
        site_awx_orchestrator = None

        sites_uri = self.api.resource.provider.site.get_uri("provider/sites", preferred_version="v1.0")
        sites = self.api.resource.provider.site.api_get(sites_uri).get("sites")
        for site in sites:
            site_orchestrators = site.get("orchestrators")
            for site_orchestrator in site_orchestrators:
                if int(site_orchestrator.get("id"))==container_id:
                    # site trovato. qui c'è l'orchestratore fas del volume
                    volume_site = site
                if site_orchestrator.get("type") == "awx" and site_orchestrator.get("tag") == "02":
                    # trovato orchestratore awx del site
                    site_awx_orchestrator = site_orchestrator
            if volume_site is not None and site_awx_orchestrator is not None:
                break

        if site_awx_orchestrator is None:
            raise Exception("site awx orchestrator not found")
        if volume_site is None:
            raise Exception("unable to derive site from container")

        print(_("Current site:") + f"\n{volume_site.get("name")}")
        print(_("Current awx orchestrator:") + f"\n{site_awx_orchestrator.get("name")}")

        # get awx params from physical resource attributes
        curr_awx_params = volume.get("attributes").get("awx_params", {})
        print(_("Current physical resource awx params:") + f"\n{curr_awx_params}")

        # determine awx params
        awx_orchestrator_id = site_awx_orchestrator.get("id")
        awx_organization_id = site_awx_orchestrator.get("config", {}).get("organization")
        awx_vault_cred_id = site_awx_orchestrator.get("config", {}).get("vault_cred_id")
        awx_projects = self.api.resource.awx.project.list(container=awx_orchestrator_id, name="staas")
        awx_projects = awx_projects.get("projects", [])
        if not awx_projects or len(awx_projects) > 1:
            raise Exception(_("Staas project not found in orchestrator") + f" {awx_orchestrator_id}")
        awx_project = awx_projects[0]
        awx_project_id = awx_project.get("id")

        calc_awx_params = {
            "awx_orchestrator_id": awx_orchestrator_id,
            "awx_organization_id": awx_organization_id,
            "awx_vault_cred_id": awx_vault_cred_id,
            "awx_project_id": awx_project_id,
        }
        print(_("Calculated awx params:") + f"\n{calc_awx_params}")

        msg = _("If current params and calculated ones differ, you are advised to update current params")
        yes = self.app.pargs.assumeyes
        if yes or self.confirm(msg=msg, suffix=_(". Proceed with update? [y/N]")):
            # update physical resource attributes with awx params
            self.api.resource.entity.set_config(volume_id, key="awx_params.awx_orchestrator_id",
                                                value=awx_orchestrator_id)
            self.api.resource.entity.set_config(volume_id, key="awx_params.awx_organization_id",
                                                value=awx_organization_id)
            self.api.resource.entity.set_config(volume_id, key="awx_params.awx_project_id",
                                                value=str(awx_project_id))
            self.api.resource.entity.set_config(volume_id, key="awx_params.awx_vault_cred_id",
                                                value=awx_vault_cred_id)
            print(_("Awx params updated"))
