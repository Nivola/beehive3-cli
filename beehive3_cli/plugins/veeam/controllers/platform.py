# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2026 CSI-Piemonte

from typing import Dict
from cement import ex

from beecell.simple import merge_list
from beedrones.veeam.client_veeam import VeeamManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS, PAGINATION_ARGS
from beehive3_cli.core.util import load_environment_config
from beehive3_cli.translate import _


def veeam_args(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": _("veeam platform reference label"),
            },
        )
    ]
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, orchestrator_args, *list_args)
    return res


class VeeamPlatformController(BaseController):
    headers = ["id", "name"]
    entity_class = None

    class Meta:
        stacked_on = "platform"
        stacked_type = "nested"
        label = "veeam"
        description = _("veeam platform management")
        help = _("veeam platform  management")

    def pre_command_run(self):
        super().pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("veeam", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No veeam default platform is available for this environment. Select another environment"
                )

        if label not in orchestrators:
            raise Exception(f"Valid label are: {', '.join(orchestrators.keys())}")
        self.conf = orchestrators.get(label)

        # print("+++++ self.conf: " + str(self.conf))

        veeam_host = self.conf.get("hosts")[0]
        veeam_port = self.conf.get("port")
        veeam_protocol = self.conf.get("proto", "http")
        veeam_path = self.conf.get("path")
        uri = f"{veeam_protocol}://{veeam_host}:{veeam_port}{veeam_path}"
        self.client = VeeamManager(uri=uri)

        veeam_user = self.conf.get("user")
        veeam_pwd = self.conf.get("pwd")
        self.client.authorize(veeam_user, veeam_pwd, key=self.key)

    def __print_pagination(self, pagination_dict: Dict):
        print(pagination_dict.keys())
        skip = pagination_dict.get("skip")
        limit = pagination_dict.get("limit",self.app.pargs.size)
        if limit:
            # page is 1-based
            page = int(skip/limit)+1
        else:
            page = self.app.pargs.page
        count = pagination_dict.get("count")
        total = pagination_dict.get("total")

        print(f"Page: {page} (skip: {skip})")
        print(f"Count: {count}")
        print(f"Total: {total}")

        """
        print(
            "Order: %s %s"
            % (
                pagination_dict.get("sort").get("field"),
                pagination_dict.get("sort").get("order"),
            )
        )
        """
        print("")

    @ex(help=_("ping veeam"), description=_("ping veeam"), arguments=veeam_args())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(
        help=_("get veeam version"),
        description=_("get veeam version - from Veeam Backup & Replication 12.0"),
        arguments=veeam_args(),
    )
    def version(self):
        res = self.client.version()
        # self.app.render(res, headers=["version"])
        self.app.render(res, details=True)

    @ex(
        help=_("get job"),
        description=_("get job"),
        arguments=veeam_args(
            [
                (
                    ["-uid"],
                    {
                        "help": _("job uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("job name pattern (es. *BCK*)"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def job_get(self):
        job_uid = self.app.pargs.uid
        job_name = self.app.pargs.name

        if job_uid is not None:
            res = self.client.job.get(job_uid)
            self.app.render(res, details=True)

        else:
            size = self.app.pargs.size
            page = self.app.pargs.page
            if page == 0:
                page = 1

            res = self.client.job.list(job_name, page_size=size, page=page)
            self.__print_pagination(res.get("pagination",{}))
            res = res["data"]
            # self.app.render(res, headers=["id", "name", "description", "isDisabled", "virtualMachines.includes"])
            transform = {"description": lambda x: x.replace("\r\n", " ")}
            self.app.render(
                res,
                headers=[
                    "id",
                    "name",
                    "description",
                    "isDisabled",
                    "schedule.daily.isEnabled",
                ],
                transform=transform,
            )

    # ----------------
    # ---  BACKUP  ---
    # ----------------

    @ex(
        help=_("get backup"),
        description=_("get backup"),
        arguments=veeam_args(
            [
                (
                    ["-job_id"],
                    {
                        "help": _("job uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-uid"],
                    {
                        "help": _("backup uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("backup name pattern (es. *BCK*)"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def backup_get(self):
        job_id = self.app.pargs.job_id
        backup_uid = self.app.pargs.uid
        backup_name = self.app.pargs.name

        if backup_uid is not None:
            res = self.client.backup.get(backup_uid)
            self.app.render(res, details=True)

        else:
            size = self.app.pargs.size
            page = self.app.pargs.page
            if page == 0:
                page = 1

            res = self.client.backup.list(job_id, backup_name, page_size=size, page=page)
            self.__print_pagination(res.get("pagination",{}))
            res = res["data"]
            self.app.render(
                res,
                headers=[
                    "id",
                    "jobId",
                    "name",
                    "policyTag",
                    "platformName",
                    "creationTime",
                ],
            )

    # ---------------------
    # --  RESTORE POINT  --
    # ---------------------

    @ex(
        help=_("get restorepoint"),
        description=_("get restorepoint"),
        arguments=veeam_args(
            [
                (
                    ["-backup_id"],
                    {
                        "help": _("backup uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-uid"],
                    {
                        "help": _("restorepoint uid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("restorepoint name pattern (es. *centos*)"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def restorepoint_get(self):
        backup_id = self.app.pargs.backup_id
        restorepoint_uid = self.app.pargs.uid
        restorepoint_name = self.app.pargs.name

        if restorepoint_uid is not None:
            res = self.client.restorepoint.get(restorepoint_uid)
            self.app.render(res, details=True)

        else:
            size = self.app.pargs.size
            page = self.app.pargs.page
            if page == 0:
                page = 1

            res = self.client.restorepoint.list(backup_id, restorepoint_name, page_size=size, page=page)
            self.__print_pagination(res.get("pagination",{}))
            res = res["data"]
            self.app.render(
                res,
                headers=[
                    "id",
                    "backupId",
                    "name",
                    "platformName",
                    "creationTime",
                    "allowedOperations",
                ],
            )
