# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte
from cement.ext.ext_argparse import ex
from beehive3_cli.core.controller import BASE_ARGS
from beecell.simple import merge_list
from .child import AdminChildController, AdminError


def EFS_ADMIN_ARGS(*list_args):
    efs_admin_args = [
        (
            ["-Ofb", "--ontap_fallback"],
            {
                "action": "store",
                "dest": "ontap_fallback",
                "help": "ontap platform reference label. Used when no ontap orchestrator found in cmp.",
            },
        ),
        (
            ["-Olab", "--ontap_label"],
            {"action": "store", "dest": "ontap_label", "help": "when multiple ontap orchestrators available."},
        ),
    ]
    res = merge_list(BASE_ARGS, efs_admin_args, *list_args)
    return res


class EfsAdminController(AdminChildController):
    """
    controller of efs admin commands
    """

    class Meta:
        """efs meta"""

        label = "efs-adm"
        description = "efs administartion commands"
        help = "efs administartion commands"

    @ex(
        help="Import volume from netapp into cmp",
        description="""Import volume from netapp into cmp.
        Will attempt to create missing services and will
        ask to update relevant quotas if necessary""",
        example="""INTERACTIVE MODE: ...import-volume-from-netapp -interactive.
        NORMAL MODE: ...import-volume-from-netapp ...params...""",
        arguments=EFS_ADMIN_ARGS(
            [
                (
                    ["-interactive"],
                    {
                        "help": "if specified, provide params as they are asked",
                        "action": "store_false",
                    },
                ),
                (
                    ["-account"],
                    {
                        "help": "account id, uuid or name, in which to import the volume",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-svm"],
                    {
                        "help": "uuid or name of the svm the volume is related to",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-volume"],
                    {
                        "help": "volume uuid or name",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-zone"],
                    {
                        "help": """availability zone the volume is in
                        (SiteTorino01,SiteTorino02,SiteVercelli01).
                        Related to which VpcFiler to use (general case),
                        unless vpc specified explicitly (custom cases).""",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def import_volume_from_netapp(self):
        """
        try import netapp volume into cmp
        """
        print(f"Getting ontap orchestrators from zone {self.app.pargs.zone}...", flush=True)
        uri = f"/v1.0/nrs/provider/sites/{self.app.pargs.zone}"
        try:
            res = self.cmp_get(uri)
        except Exception as exc:
            raise AdminError(f"Invalid zone: {self.app.pargs.zone} - {exc}") from exc

        orchestrators = res.get("site", {}).get("orchestrators", [])
        ontap_orchestrators = [x for x in orchestrators if x["type"] == "ontap"]
        if len(ontap_orchestrators) != 0:
            err_msg = f"No ontap orchestrator found for zone {self.app.pargs.zone}"
            if self.app.pargs.ontap_fallback is None:
                raise AdminError(err_msg + " and no fallback parameter given.")
            else:
                print(err_msg + f". Using fallback orchestrator: {self.app.pargs.ontap_fallback}", flush=True)
            raise Exception("ciao")

        # TODO
        # account = self.get_cmp_account(self.app.pargs.account)
