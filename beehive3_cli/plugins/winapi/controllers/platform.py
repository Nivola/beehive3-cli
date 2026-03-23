# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from ujson import loads
from cement import ex
from beecell.simple import merge_list
from beedrones.winapi.client import WinapiManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS, PAGINATION_ARGS
from beehive3_cli.core.util import load_environment_config
from beehive3_cli.translate import _


def winapi_args(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": _("winapi platform reference label"),
            },
        )
    ]
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, orchestrator_args, *list_args)
    return res


class WinAPIPlatformController(BaseController):

    class Meta:
        stacked_on = "platform"
        stacked_type = "nested"
        label = "winapi"
        description = _("winapi (veeam) platform management")
        help = _("winapi platform  management")

    def pre_command_run(self):
        super().pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("winapi", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No winapi (veeam) default platform is available for this environment. Select "
                    "another environment"
                )

        if label not in orchestrators:
            raise Exception(f"Valid label are: {', '.join(orchestrators.keys())}")
        self.conf = orchestrators.get(label)

        winapiconn = {
            "host": self.conf.get("host"),
            "port": self.conf.get("port"),
            "proto": self.conf.get("proto"),
            "user": self.conf.get("user"),
            "pwd": self.conf.get("pwd"),
            "verified": False,
        }
        # TODO: creare connessione per accedere a winapi e passarla al winapimanager
        self.client = WinapiManager(winapiconn)
        # self.jobs = WinapiJob
        # self.client.authorize(self.conf.get('user'), self.conf.get('pwd'), key=self.key)

    @ex(help=_("ping awx"), description=_("ping awx"), arguments=winapi_args())
    def ping(self):
        res = self.client.ping()
        # res = {'ping': 'okkk'}
        self.app.render({"ping": res}, headers=["ping"])

    @ex(help=_("get jobs"), description=_("get veaam jobs"), arguments=winapi_args())
    def get_jobs(self):
        res = self.client.job.get_jobs()
        res_decoded = res.decode("utf-8")
        res_json = loads(res_decoded)
        self.app.render(res_json["data"], headers=["Name", "Type", "UID"])

    @ex(
        help=_("get jobs status"),
        description=_("get the status of veeam jobs "),
        arguments=winapi_args(),
    )
    def get_jobs_status(self):
        res = self.client.job.get_jobs_status()
        res_json = loads(res)

        self.app.render(
            res_json["data"],
            headers=[
                "ID",
                "JobName",
                "Status",
                "Type",
                "State",
                "StartTime",
                "WorkDuration",
            ],
        )

    @ex(
        help=_("get job ID info"),
        description=_("get info of  job ID"),
        arguments=winapi_args(
            [
                (
                    ["--job_id"],
                    {
                        "help": _("job id to retrieve info"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def get_jobs_id(self):
        job_id = self.app.pargs.job_id
        res = self.client.job.get_jobs_id(job_id)
        str_json = loads(res.decode("utf-8"))
        self.app.render(
            str_json["data"]["Job"],
            headers=[
                "Name",
                "Description",
                "JobType",
                "ScheduleConfigured",
                "ScheduleEnabled",
                "NextRun",
            ],
        )

    @ex(
        help=_("get job id includes"),
        description=_("get vms under backup into job ID"),
        arguments=winapi_args(
            [
                (
                    ["--job_id"],
                    {
                        "help": _("job id to retrieve info"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def get_jobs_id_includes(self):
        job_id = self.app.pargs.job_id
        res = self.client.job.get_jobs_id_include(job_id)
        data = res["data"]["ObjectsInJob"]["ObjectInJob"]
        self.app.render(data, headers=["DisplayName", "Name", "@Href", "HierarchyObjRef", "Order"])

    @ex(
        help=_("start job ID"),
        description=_("start backup og a job with id JOB_ID"),
        arguments=winapi_args(
            [
                (
                    ["--job_id"],
                    {
                        "help": _("job id to retrieve info"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def start_job(self):
        job_id = self.app.pargs.job_id
        res = self.client.job.start_job(job_id)
        data = res["data"]["data"]["Task"]
        self.app.render(data, headers=["@Type", "Operation", "State", "TaskId", "Result"])

    @ex(
        help=_("stop job ID"),
        description=_("stop backup og a job with id JOB_ID"),
        arguments=winapi_args(
            [
                (
                    ["--job_id"],
                    {
                        "help": _("job id to retrieve info"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def stop_job(self):
        job_id = self.app.pargs.job_id
        res = self.client.job.stop_job(job_id)
        print(res)
        data = res["data"]["Task"]
        self.app.render(data, headers=["@Type", "Operation", "State", "TaskId", "Result"])

    @ex(
        help=_("get the restore points of a vm"),
        description=_("Get ALL the restore points of a vm"),
        arguments=winapi_args(
            [
                (
                    ["--vm_name"],
                    {
                        "help": _("name of the vm to retrieve the restore points"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def get_vm_restore_points(self):
        vm_name = self.app.pargs.vm_name
        res = self.client.restore.get_vm_restore_points(vm_name)
        str_json = loads(res.decode("utf-8"))
        self.app.render(str_json["RestorePoints"], headers=["UID", "Name"])
