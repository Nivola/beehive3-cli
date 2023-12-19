# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2023 CSI-Piemonte
from cement import ex
from beecell.simple import merge_list
from beedrones.veeam.client_veeam import VeeamManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS, PAGINATION_ARGS
from beehive3_cli.core.util import load_environment_config


def VEEAM_ARGS(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": "veeam platform reference label",
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
        description = "veeam platform management"
        help = "veeam platform  management"

    def pre_command_run(self):
        super(VeeamPlatformController, self).pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("veeam", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No veeam default platform is available for this environment. Select " "another environment"
                )

        if label not in orchestrators:
            raise Exception("Valid label are: %s" % ", ".join(orchestrators.keys()))
        self.conf = orchestrators.get(label)

        # print("+++++ self.conf: " + str(self.conf))

        veeam_host = self.conf.get("hosts")[0]
        veeam_port = self.conf.get("port")
        veeam_protocol = self.conf.get("proto", "http")
        veeam_path = self.conf.get("path")
        uri = "%s://%s:%s%s" % (veeam_protocol, veeam_host, veeam_port, veeam_path)
        self.client = VeeamManager(uri=uri)

        veeam_user = self.conf.get("user")
        veeam_pwd = self.conf.get("pwd")
        self.client.authorize(veeam_user, veeam_pwd, key=self.key)

    @ex(help="ping veeam", description="ping veeam", arguments=VEEAM_ARGS())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(
        help="get veeam version",
        description="get veeam version - from Veeam Backup & Replication 12.0",
        arguments=VEEAM_ARGS(),
    )
    def version(self):
        res = self.client.version()
        # self.app.render(res, headers=["version"])
        self.app.render(res, details=True)

    # ----------------
    # ----  JOB  -----
    # ----------------
    # @ex(
    #     help="add job",
    #     description="add job",
    #     arguments=VEEAM_ARGS(
    #         [
    #             (
    #                 ["name"],
    #                 {
    #                     "help": "job name",
    #                     "action": "store",
    #                     "type": str,
    #                     "default": None,
    #                 },
    #             ),
    #         ]
    #     ),
    # )
    # def job_add(self):
    #     name = self.app.pargs.name
    #     res = self.client.job.add(job_name=name)
    #     self.app.render(res, headers=["id", "uid", "title"])

    # @ex(
    #     help="delete job",
    #     description="delete job",
    #     arguments=VEEAM_ARGS(
    #         [
    #             (
    #                 ["uid"],
    #                 {
    #                     "help": "job uid",
    #                     "action": "store",
    #                     "type": str,
    #                     "default": None,
    #                 },
    #             ),
    #         ]
    #     ),
    # )
    # def job_del(self):
    #     job_uid = self.app.pargs.uid
    #     self.client.job.delete(job_uid)
    #     self.app.render({"msg": "delete job %s" % job_uid}, headers=["msg"])

    @ex(
        help="get job",
        description="get job",
        arguments=VEEAM_ARGS(
            [
                (
                    ["-uid"],
                    {
                        "help": "job uid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "job name pattern (es. *BCK*)",
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
            res = res["data"]
            # self.app.render(res, headers=["id", "name", "description", "isDisabled", "virtualMachines.includes"])
            self.app.render(
                res,
                headers=[
                    "id",
                    "name",
                    "description",
                    "isDisabled",
                    "schedule.daily.isEnabled",
                ],
            )

    # ----------------
    # ---  BACKUP  ---
    # ----------------

    @ex(
        help="get backup",
        description="get backup",
        arguments=VEEAM_ARGS(
            [
                (
                    ["-job_id"],
                    {
                        "help": "job uid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-uid"],
                    {
                        "help": "backup uid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "backup name pattern (es. *BCK*)",
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
        help="get restorepoint",
        description="get restorepoint",
        arguments=VEEAM_ARGS(
            [
                (
                    ["-backup_id"],
                    {
                        "help": "backup uid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-uid"],
                    {
                        "help": "restorepoint uid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "restorepoint name pattern (es. *centos*)",
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
