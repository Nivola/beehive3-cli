# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte
from sys import stdout
from json import loads
from time import sleep
from cement import ex
from beecell.simple import merge_list
from beedrones.winapi.client import WinapiManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS, PAGINATION_ARGS
from beehive3_cli.core.util import load_environment_config, rotating_bar


def WINAPI_ARGS(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": "winapi platform reference label",
            },
        )
    ]
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, orchestrator_args, *list_args)
    return res


class WinAPIPlatformController(BaseController):
    # headers = ['id', 'name']
    # entity_class = None

    class Meta:
        stacked_on = "platform"
        stacked_type = "nested"
        label = "winapi"
        description = "winapi (veeam) platform management"
        help = "winapi platform  management"

    def pre_command_run(self):
        super(WinAPIPlatformController, self).pre_command_run()

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
            raise Exception("Valid label are: %s" % ", ".join(orchestrators.keys()))
        self.conf = orchestrators.get(label)

        # uri = '%s://%s:%s%s' % (self.conf.get('proto'), self.conf.get('hosts')[0], self.conf.get('port'),
        #                         self.conf.get('path'))

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

    def __wait_for_job(self, job_query_func, job_id, maxtime=600, delta=1):
        job = job_query_func(job_id)
        status = job["status"]
        elapsed = 0
        bar = rotating_bar()
        while status not in ["successful", "failed", "error", "canceled"]:
            # stdout.write(".")
            stdout.write(next(bar))
            stdout.flush()
            job = job_query_func(job_id)
            status = job["status"]
            sleep(delta)
            elapsed += delta
            if elapsed >= maxtime:
                raise TimeoutError("job %s query timeout" % job_id)
        if status in ["failed", "error"]:
            self.app.log.error(job["result_traceback"])
            raise Exception("job %s error" % job_id)
        elif status == "cancelled":
            self.app.log.error(job["job %s cancelled" % job_id])
            raise Exception("job %s cancelled" % job_id)
        else:
            self.app.log.info("job %s successful" % job_id)

    @ex(help="ping awx", description="ping awx", arguments=WINAPI_ARGS())
    def ping(self):
        res = self.client.ping()
        # res = {'ping': 'okkk'}
        self.app.render({"ping": res}, headers=["ping"])

    @ex(help="get jobs", description="get veaam jobs", arguments=WINAPI_ARGS())
    def get_jobs(self):
        res = self.client.job.get_jobs()
        res_decoded = res.decode("utf-8")
        res_json = eval(res_decoded)
        self.app.render(res_json["data"], headers=["Name", "Type", "UID"])

    @ex(
        help="get jobs status",
        description="get the status of veeam jobs ",
        arguments=WINAPI_ARGS(),
    )
    def get_jobs_status(self):
        res = self.client.job.get_jobs_status()
        # res_decoded = res.decode('utf-8')
        res_json = eval(res)

        # print(res_json['data'])
        # res_json = eval(res_decoded)

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
        help="get job ID info",
        description="get info of  job ID",
        arguments=WINAPI_ARGS(
            [
                (
                    ["--job_id"],
                    {
                        "help": "job id to retrieve info",
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
        help="get job id includes",
        description="get vms under backup into job ID",
        arguments=WINAPI_ARGS(
            [
                (
                    ["--job_id"],
                    {
                        "help": "job id to retrieve info",
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
        help="start job ID",
        description="start backup og a job with id JOB_ID",
        arguments=WINAPI_ARGS(
            [
                (
                    ["--job_id"],
                    {
                        "help": "job id to retrieve info",
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
        # print(res['data']['data']['Task'])
        self.app.render(data, headers=["@Type", "Operation", "State", "TaskId", "Result"])

    @ex(
        help="stop job ID",
        description="stop backup og a job with id JOB_ID",
        arguments=WINAPI_ARGS(
            [
                (
                    ["--job_id"],
                    {
                        "help": "job id to retrieve info",
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
        # print(res['data']['data']['Task'])
        self.app.render(data, headers=["@Type", "Operation", "State", "TaskId", "Result"])

    @ex(
        help="get the restore points of a vm",
        description="Get ALL the restore points of a vm",
        arguments=WINAPI_ARGS(
            [
                (
                    ["--vm_name"],
                    {
                        "help": "name of the vm to retrieve the restore points",
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
        # self.app.render(str_json['RestorePoints']['Links']['link'], headers=['Href', 'Name', 'Type'])
