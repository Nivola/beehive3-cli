# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from sys import stdout
from time import sleep
from cement import ex
from beecell.types.type_list import merge_list
from beecell.file import read_file
from beecell.types.type_dict import dict_get
from beedrones.awx.client import AwxManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS, PAGINATION_ARGS
from beehive3_cli.core.util import load_environment_config


def AWX_ARGS(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": "awx platform reference label",
            },
        )
    ]
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, orchestrator_args, *list_args)
    return res


class AwxPlatformController(BaseController):
    headers = ["id", "name"]
    entity_class = None

    class Meta:
        stacked_on = "platform"
        stacked_type = "nested"
        label = "awx"
        description = "awx platform management"
        help = "awx platform  management"

    def pre_command_run(self):
        super(AwxPlatformController, self).pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("awx", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No awx default platform is available for this environment. Select " "another environment"
                )

        if label not in orchestrators:
            raise Exception("Valid label are: %s" % ", ".join(orchestrators.keys()))
        self.conf = orchestrators.get(label)

        uri = "%s://%s:%s%s" % (
            self.conf.get("proto"),
            self.conf.get("hosts")[0],
            self.conf.get("port"),
            self.conf.get("path"),
        )

        if self.app.config.get("log.clilog", "verbose_log"):
            transform = {"msg": lambda x: self.color_string(x, "YELLOW")}
            self.app.render(
                {"msg": "Using awx orchestrator: %s (uri: %s)" % (label, uri)},
                transform=transform,
            )
            self.app.log.debug("Using awx orchestrator: %s (uri: %s)" % (label, uri))

        self.client = AwxManager(uri)
        self.client.authorize(self.conf.get("user"), self.conf.get("pwd"), key=self.key)

    def __wait_for_job(self, job_query_func, job_id, maxtime=600, delta=1):
        job = job_query_func(job_id)
        status = job["status"]
        elapsed = 0
        while status not in ["successful", "failed", "error", "canceled"]:
            stdout.write(".")
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

    @ex(help="ping awx", description="ping awx", arguments=AWX_ARGS())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(help="get awx version", description="get awx version", arguments=AWX_ARGS())
    def version(self):
        res = self.client.version()
        self.app.render(res, headers=["version", "ansible_version"])

    @ex(
        help="get organizations",
        description="get organizations",
        arguments=AWX_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "organization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "organization name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def org_get(self):
        oid = self.app.pargs.id
        name = self.app.pargs.name
        res = self.client.organization.list(id=oid, name=name)
        self.app.render(res, headers=["id", "name", "created", "modified"])

    @ex(
        help="get inventories",
        description="get inventories",
        example="beehive platform awx inventory-get;beehive platform awx inventory-get ",
        arguments=AWX_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "inventory id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "inventory name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def inventory_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            res = self.client.inventory.get(oid)

            if self.is_output_text():
                res.pop("related", None)
                res.pop("summary_fields", None)
                self.app.render(res, details=True)

                self.c("\nsources", "underline")
                source_list = self.client.inventory.source_list(oid)
                self.app.render(source_list, headers=["id", "name", "created", "modified"])
                self.c("\ngroups", "underline")
                group_list = self.client.inventory.group_list(oid)
                self.app.render(group_list, headers=["id", "name", "created", "modified"])
                self.c("\nhosts", "underline")
                host_list = self.client.inventory.host_list(oid)
                self.app.render(host_list, headers=["id", "name", "created", "modified"])
            else:
                self.app.render(res, details=True)
        else:
            name = self.app.pargs.name
            size = self.app.pargs.size
            page = self.app.pargs.page
            if page == 0:
                page = 1
            res = self.client.inventory.list(name=name, page_size=size, page=page)
            self.app.render(
                res,
                headers=[
                    "id",
                    "name",
                    "organization",
                    "total_hosts",
                    "total_groups",
                    "total_inventory_sources",
                    "created",
                    "modified",
                ],
            )

    @ex(
        help="add inventory",
        description="add inventory",
        arguments=AWX_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "inventory name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["organization"],
                    {
                        "help": "organization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def inventory_add(self):
        name = self.app.pargs.name
        organization = self.app.pargs.organization
        res = self.client.inventory.add(name, organization)
        self.app.render(res, headers=["id", "name", "created", "modified"])

    @ex(
        help="delete inventory",
        description="delete inventory",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "inventory id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def inventory_del(self):
        oid = self.app.pargs.id
        self.client.inventory.delete(oid)
        self.app.render({"msg": "delete inventory %s" % oid}, headers=["msg"])

    @ex(
        help="sync inventory source",
        description="get inventory source",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "inventory source id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def inventory_source_sync(self):
        oid = self.app.pargs.id
        self.client.inventory.source_sync(oid)

    @ex(
        help="get inventory scripts",
        description="get inventory scripts",
        arguments=AWX_ARGS(
            [
                (
                    ["-inventory"],
                    {
                        "help": "inventory id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": "group id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def inventory_script_get(self):
        inventory_id = self.app.pargs.inventory
        oid = self.app.pargs.id
        res = self.client.inventory_script.list(inventory=inventory_id, id=oid)
        self.app.render(res, headers=["id", "name", "created", "modified"])

    @ex(
        help="add script inventory",
        description="add script inventory",
        arguments=AWX_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "script inventory name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["organization"],
                    {
                        "help": "organization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["script"],
                    {
                        "help": "script. Ex. #!/bin/bash\nsource /opt/beehive/bin/activate\n",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def inventory_script_add(self):
        name = self.app.pargs.name
        organization = self.app.pargs.organization
        script = self.app.pargs.script
        res = self.client.inventory_script.add(name, organization, script)
        self.app.render(res, headers=["id", "name", "created", "modified"])

    @ex(
        help="delete script inventory",
        description="delete script inventory",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "inventory id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def inventory_script_del(self):
        oid = self.app.pargs.id
        self.client.inventory_script.delete(oid)
        self.app.render({"msg": "delete script inventory %s" % oid}, headers=["msg"])

    @ex(
        help="get inventory groups",
        description="get inventory groups",
        arguments=AWX_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "inventory group id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "inventory name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-inventory"],
                    {
                        "help": "inventory id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def inventory_group_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            res = self.client.inventory.group_get(oid)

            if self.is_output_text():
                res.pop("related", None)
                res.pop("summary_fields", None)
                self.app.render(res, details=True)

                self.c("\nhosts", "underline")
                host_list = self.client.inventory.group_host_list(oid)
                self.app.render(host_list, headers=["id", "name", "created", "modified"])
            else:
                self.app.render(res, details=True)
        else:
            inventory = self.app.pargs.inventory
            name = self.app.pargs.name
            size = self.app.pargs.size
            page = self.app.pargs.page
            if page == 0:
                page = 1
            res = self.client.inventory.group_list(inventory, name=name, page_size=size, page=page)
            self.app.render(
                res,
                headers=["id", "name", "inventory", "variables", "created", "modified"],
            )

    @ex(
        help="add inventory group",
        description="add inventory group",
        arguments=AWX_ARGS(
            [
                (
                    ["inventory"],
                    {
                        "help": "inventory id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": "inventory group name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "host description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vars"],
                    {
                        "help": "host variables. ex: k1:v1,k2:v2",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def inventory_group_add(self):
        inventory = self.app.pargs.inventory
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        vars = self.app.pargs.vars
        variables = None
        if vars is not None:
            variables = {}
            if vars is not None:
                for var in vars.split(","):
                    k, v = var.split(":", 1)
                    variables[k] = v
        res = self.client.inventory.group_add(inventory, name, desc=desc, vars=variables)
        self.app.render({"msg": "add group %s" % res["id"]})

    @ex(
        help="delete inventory group",
        description="delete inventory group",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "inventory group id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def inventory_group_del(self):
        oid = self.app.pargs.id
        self.client.inventory.group_del(oid)
        self.app.render({"msg": "delete group %s" % oid}, headers=["msg"])

    @ex(
        help="get inventory hosts",
        description="get inventory hosts",
        arguments=AWX_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "inventory group id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "inventory name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-inventory"],
                    {
                        "help": "inventory id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def inventory_host_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            res = self.client.inventory.host_get(oid)

            # if self.is_output_text():
            #     self.app.render(res, details=True)
            # else:
            self.app.render(res, details=True)
        else:
            inventory = self.app.pargs.inventory
            name = self.app.pargs.name
            size = self.app.pargs.size
            page = self.app.pargs.page
            if page == 0:
                page = 1
            res = self.client.inventory.host_list(inventory, name=name, page_size=size, page=page)
            self.app.render(
                res,
                headers=["id", "name", "inventory", "variables", "created", "modified"],
            )

    @ex(
        help="get add hoc commands",
        description="get add hoc commands",
        arguments=AWX_ARGS(
            [
                (
                    ["-inventory"],
                    {
                        "help": "inventory id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {"help": "job id", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def ad_hoc_command_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            res = self.client.ad_hoc_command.get(oid)

            if self.is_output_text():
                res.pop("related", None)
                res.pop("summary_fields", None)
                job_env = res.pop("job_env", {})
                self.app.render(res, details=True)
                self.c("\nenvironment", "underline")
                self.app.render(job_env, details=True)
            else:
                self.app.render(res, details=True)
        else:
            size = self.app.pargs.size
            page = self.app.pargs.page
            inventory_id = self.app.pargs.inventory
            if page == 0:
                page = 1
            res = self.client.ad_hoc_command.list(page_size=size, page=page, inventory=inventory_id)
            self.app.render(
                res,
                headers=[
                    "id",
                    "name",
                    "module_name",
                    "module_args",
                    "status",
                    "started",
                    "finished",
                    "elapsed",
                ],
            )

    @ex(
        help="add add hoc commands",
        description="add add hoc commands",
        arguments=AWX_ARGS(
            [
                (
                    ["inventory"],
                    {
                        "help": "inventory id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["credential"],
                    {
                        "help": "credential id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-verbosity"],
                    {"help": "verbosity", "action": "store", "type": int, "default": 0},
                ),
            ]
        ),
    )
    def ad_hoc_command_add(self):
        inventory_id = self.app.pargs.inventory
        credential_id = self.app.pargs.credential
        verbosity = self.app.pargs.verbosity
        module_args = "echo 'show databases' | mysqlsh --json=raw --sql --uri 'root:xxx@localhost:3306'"
        extra_vars = {}
        res = self.client.ad_hoc_command.add(
            inventory_id,
            limit="",
            credential=credential_id,
            module_name="shell",
            module_args=module_args,
            verbosity=verbosity,
            extra_vars=extra_vars,
            become_enabled=False,
        )
        self.app.render(res, details=True)

    @ex(
        help="relaunch add hoc command",
        description="relaunch add hoc command",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {"help": "job id", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def ad_hoc_command_relaunch(self):
        oid = self.app.pargs.id
        res = self.client.ad_hoc_command.relaunch(oid)
        self.app.render(res, details=True)

    @ex(
        help="get add hoc command stdout",
        description="get add hoc command stdout",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {"help": "job id", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def ad_hoc_command_stdout(self):
        oid = self.app.pargs.id
        res = self.client.ad_hoc_command.stdout(oid)
        if self.is_output_text():
            content = res.get("content").split("\n")
            for i in content:
                i = (
                    i.replace("\x1b[0;32m", "")
                    .replace("\x1b[0;33m", "")
                    .replace("\x1b[1;31m", "")
                    .replace("\x1b[1;35m", "")
                    .replace("\x1b[0;31m", "")
                    .replace("\x1b[0;36m", "")
                )
                if i == "\x1b[":
                    continue
                print(i.replace("\x1b[", "").replace("0m", ""))
        else:
            self.app.render(res, details=True)

    @ex(
        help="get jobs",
        description="get jobs",
        example="beehive platform awx job-get -id #### -e <env>;beehive platform awx job-get",
        arguments=AWX_ARGS(
            [
                (
                    ["-id"],
                    {"help": "job id", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def job_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            res = self.client.job.get(oid)

            if self.is_output_text():
                res.pop("related", None)
                res.pop("summary_fields", None)
                job_env = res.pop("job_env", {})
                self.app.render(res, details=True)
                self.c("\nenvironment", "underline")
                self.app.render(job_env, details=True)
            else:
                self.app.render(res, details=True)
        else:
            size = self.app.pargs.size
            page = self.app.pargs.page
            if page == 0:
                page = 1
            res = self.client.job.list(page_size=size, page=page)
            self.app.render(
                res,
                headers=[
                    "id",
                    "type",
                    "playbook",
                    "launch_type",
                    "status",
                    "started",
                    "finished",
                    "elapsed",
                    "job_tags",
                ],
            )

    @ex(
        help="relaunch job",
        description="relaunch job",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {"help": "job id", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def job_relaunch(self):
        oid = self.app.pargs.id
        res = self.client.job.relaunch(oid)

    @ex(
        help="get job stdout",
        description="get job stdout",
        example="beehive platform awx job-stdout #### ;beehive platform awx job-stdout #### ",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {"help": "job id", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def job_stdout(self):
        oid = self.app.pargs.id
        res = self.client.job.stdout(oid)
        if self.is_output_text():
            content = res.get("content").split("\n")
            for i in content:
                i = (
                    i.replace("\x1b[0;32m", "")
                    .replace("\x1b[0;33m", "")
                    .replace("\x1b[1;31m", "")
                    .replace("\x1b[1;35m", "")
                    .replace("\x1b[0;31m", "")
                    .replace("\x1b[0;36m", "")
                )
                if i == "\x1b[":
                    continue
                print(i.replace("\x1b[", "").replace("0m", ""))
        else:
            self.app.render(res, details=True)

    @ex(
        help="get job events",
        description="get job events",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {"help": "job id", "action": "store", "type": str, "default": None},
                ),
                (
                    ["-query"],
                    {
                        "help": "job event query. Comma separated k:v",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def job_event_get(self):
        oid = self.app.pargs.id
        query = self.app.pargs.query
        filter = {}
        if query is not None:
            for item in query.split(","):
                k, v = item.split(":")
                filter[k] = v
        res = self.client.job.events(oid, query=filter)
        self.app.render(
            res,
            headers=[
                "id",
                "counter",
                "task",
                "event",
                "event_display",
                "event_data.task_action",
                "failed",
            ],
            maxsize=200,
        )

    @ex(
        help="get job error",
        description="get job error",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {"help": "job id", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def job_event_error_get(self):
        oid = self.app.pargs.id
        res = self.client.job.events(oid, query={"failed": True})
        resp = dict_get(res[1], "event_data.res.msg")
        self.app.error(resp)

    @ex(
        help="get hosts",
        description="get hosts",
        arguments=AWX_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "host id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "host name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            res = self.client.host.get(oid)

            if self.is_output_text():
                res.pop("related", None)
                res.pop("summary_fields", None)
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            name = self.app.pargs.name
            size = self.app.pargs.size
            page = self.app.pargs.page
            if page == 0:
                page = 1
            res = self.client.host.list(name=name, page_size=size, page=page)
            self.app.render(
                res,
                headers=["id", "name", "inventory", "enabled", "created", "modified"],
            )

    @ex(
        help="add host",
        description="add host",
        arguments=AWX_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "host name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["inventory"],
                    {
                        "help": "inventory id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "host description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vars"],
                    {
                        "help": "host variables. ex: k1:v1,k2:v2",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_add(self):
        inventory = self.app.pargs.inventory
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        vars = self.app.pargs.vars
        variables = None
        if vars is not None:
            variables = {}
            if vars is not None:
                for var in vars.split(","):
                    k, v = var.split(":", 1)
                    variables[k] = v
        res = self.client.host.add(name, inventory, desc=desc, vars=variables)
        self.app.render({"msg": "add host %s" % res["id"]})

    @ex(
        help="delete host",
        description="delete host",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "host id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_del(self):
        oid = self.app.pargs.id
        self.client.host.delete(oid)
        self.app.render({"msg": "delete host %s" % oid}, headers=["msg"])

    @ex(
        help="add group to host",
        description="add group to host",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "host id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["group"],
                    {
                        "help": "group id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_group_add(self):
        oid = self.app.pargs.id
        group = self.app.pargs.group
        self.client.host.group_add(oid, int(group))
        self.app.render({"msg": "add group %s to host %s" % (group, oid)}, headers=["msg"])

    @ex(
        help="remove group from host",
        description="remove group from host",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "host id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["group"],
                    {
                        "help": "group id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def host_group_del(self):
        oid = self.app.pargs.id
        group = self.app.pargs.group
        self.client.host.group_del(oid, int(group))
        self.app.render({"msg": "remove group %s from host %s" % (group, oid)}, headers=["msg"])

    @ex(
        help="get credentials",
        description="get credentials",
        arguments=AWX_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "credential id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "credential name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def credential_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            res = self.client.credential.get(oid)

            if self.is_output_text():
                res.pop("related", None)
                res.pop("summary_fields", None)
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            name = self.app.pargs.name
            size = self.app.pargs.size
            page = self.app.pargs.page
            if page == 0:
                page = 1
            res = self.client.credential.list(name=name, page_size=size, page=page)
            self.app.render(
                res,
                headers=["id", "name", "organization", "kind", "created", "modified"],
            )

    @ex(
        help="get credential types",
        description="get credential types",
        arguments=AWX_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "credential type id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def credential_type_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            res = self.client.credential.type_get(oid)

            if self.is_output_text():
                res.pop("related", None)
                res.pop("summary_fields", None)
                inputs = res.pop("inputs", {}).get("fields", [])
                self.app.render(res, details=True)

                self.c("\ninputs", "underline")
                self.app.render(
                    inputs,
                    headers=[
                        "id",
                        "label",
                        "type",
                        "format",
                        "secret",
                        "multiline",
                        "ask_at_runtime",
                        "help_text",
                    ],
                )
            else:
                self.app.render(res, details=True)
        else:
            res = self.client.credential.type_list(order_by="id")
            self.app.render(
                res,
                headers=[
                    "id",
                    "name",
                    "kind",
                    "namespace",
                    "managed_by_tower",
                    "created",
                    "modified",
                ],
            )

    @ex(
        help="add ssh credential",
        description="add ssh credential",
        arguments=AWX_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "credential name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["organization"],
                    {
                        "help": "organization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["username"],
                    {
                        "help": "username",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-password"],
                    {
                        "help": "password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-key_data"],
                    {
                        "help": "ssh key data file",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-key_unlock"],
                    {
                        "help": "ssh key unlock",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-become"],
                    {
                        "help": "become method",
                        "action": "store",
                        "type": str,
                        "default": "no_become",
                    },
                ),
            ]
        ),
    )
    def credential_ssh_add(self):
        name = self.app.pargs.name
        organization = self.app.pargs.organization
        username = self.app.pargs.username
        password = self.app.pargs.password
        ssh_key_data = self.app.pargs.key_data
        ssh_key_unlock = self.app.pargs.key_unlock
        become = self.app.pargs.become
        if ssh_key_data is not None:
            ssh_key_data = read_file(ssh_key_data)
        res = self.client.credential.add_ssh(
            name,
            organization,
            username,
            password=password,
            ssh_key_data=ssh_key_data,
            ssh_key_unlock=ssh_key_unlock,
            become=become,
        )
        self.app.render({"msg": "add ssh credential %s" % res["id"]})

    @ex(
        help="add git credential",
        description="add git credential",
        arguments=AWX_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "credential name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["organization"],
                    {
                        "help": "organization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["username"],
                    {
                        "help": "username",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["password"],
                    {
                        "help": "password",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def credential_git_add(self):
        name = self.app.pargs.name
        organization = self.app.pargs.organization
        username = self.app.pargs.username
        password = self.app.pargs.password
        res = self.client.credential.add_git(name, organization, username, password)
        self.app.render({"msg": "add ssh credential %s" % res["id"]})

    @ex(
        help="delete credential",
        description="delete credential",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "credential id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def credential_del(self):
        oid = self.app.pargs.id
        self.client.credential.delete(oid)
        self.app.render({"msg": "delete credential %s" % oid}, headers=["msg"])

    @ex(
        help="get projects",
        description="get projects",
        example="beehive platform awx project-get ;beehive platform awx project-get ",
        arguments=AWX_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "project name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-search"],
                    {
                        "help": "search",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            res = self.client.project.get(oid)

            if self.is_output_text():
                res.pop("related", None)
                summary_fields = res.pop("summary_fields", None)
                default_environment = summary_fields.pop("default_environment", None)
                self.app.render(res, details=True)

                if default_environment is not None:
                    self.c("\ndefault environment", "underline")
                    self.app.render(default_environment, details=True)

                self.c("\njobs", "underline")
                jobs = self.client.project.job.list(project=oid)
                self.app.render(
                    jobs,
                    headers=[
                        "id",
                        "type",
                        "launch_type",
                        "status",
                        "started",
                        "finished",
                        "elapsed",
                    ],
                )
            else:
                self.app.render(res, details=True)
        else:
            name = self.app.pargs.name
            search = self.app.pargs.search
            size = self.app.pargs.size
            page = self.app.pargs.page
            if page == 0:
                page = 1
            res = self.client.project.list(name=name, page_size=size, page=page, search=search)
            self.app.render(
                res,
                headers=[
                    "id",
                    "name",
                    "organization",
                    "status",
                    "scm_type",
                    "scm_url",
                    "scm_branch",
                    "created",
                    "modified",
                ],
            )

    @ex(
        help="add project",
        description="add project",
        arguments=AWX_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "project name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["organization"],
                    {
                        "help": "organization id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["credential"],
                    {
                        "help": "credential id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["scm_url"],
                    {
                        "help": "scm url",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-scm_type"],
                    {
                        "help": "scm type",
                        "action": "store",
                        "type": str,
                        "default": "git",
                    },
                ),
                (
                    ["-scm_branch"],
                    {
                        "help": "scm branch",
                        "action": "store",
                        "type": str,
                        "default": "master",
                    },
                ),
                (
                    ["-scm_update_on_launch"],
                    {
                        "help": "scm update on launch",
                        "action": "store",
                        "type": bool,
                        "default": True,
                    },
                ),
                (
                    ["-default_environment"],
                    {
                        "help": "default environment",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_add(self):
        name = self.app.pargs.name
        organization = self.app.pargs.organization
        credential = self.app.pargs.credential
        scm_url = self.app.pargs.scm_url
        scm_type = self.app.pargs.scm_type
        scm_branch = self.app.pargs.scm_branch
        scm_update_on_launch = self.app.pargs.scm_update_on_launch
        default_environment = self.app.pargs.default_environment

        params = {
            "organization": organization,
            "scm_type": scm_type,
            "scm_url": scm_url,
            "scm_branch": scm_branch,
            "credential": credential,
            "scm_update_on_launch": scm_update_on_launch,
        }

        if default_environment is not None:
            params.update({"default_environment": default_environment})

        res = self.client.project.add(name, **params)
        project = res["id"]
        self.app.render({"msg": "add project %s" % project})

    @ex(
        help="delete project",
        description="delete project",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_del(self):
        oid = self.app.pargs.id
        self.client.project.delete(oid)
        self.app.render({"msg": "delete project %s" % oid}, headers=["msg"])

    @ex(
        help="sync project",
        description="sync project",
        example="beehive platform awx project-sync ### -e <env>;beehive platform awx project-sync ###",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_sync(self):
        oid = self.app.pargs.id
        job = self.client.project.sync(oid)
        self.__wait_for_job(self.client.project.job.get, job["id"], delta=2)
        self.app.render({"msg": "sync project %s" % oid}, headers=["msg"])

    @ex(
        help="get project job",
        description="get project job",
        arguments=AWX_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "project job id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_job_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            job = self.client.project.job.get(oid)
            job.pop("related", None)
            job.pop("summary_fields", None)
            job_env = job.pop("job_env", {})
            self.app.render(job, details=True)
            self.c("\nenvironment", "underline")
            self.app.render(job_env, details=True)
        else:
            jobs = self.client.project.job.list()
            self.app.render(
                jobs,
                headers=[
                    "id",
                    "name",
                    "type",
                    "status",
                    "job_tags",
                    "created",
                    "elapsed",
                ],
            )

    @ex(
        help="get project job events",
        description="get project job events",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "project job id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_job_event_get(self):
        oid = self.app.pargs.id
        events = self.client.project.job.events(oid)
        self.app.render(
            events,
            headers=["id", "type", "event", "counter", "event_display"],
            maxsize=200,
        )

    @ex(
        help="get project job stdout",
        description="get project job stdout",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "project job id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def project_job_stdout(self):
        oid = self.app.pargs.id
        stdout = self.client.project.job.stdout(oid)
        print(stdout.get("content", ""))

    @ex(
        help="get templates",
        description="get templates",
        arguments=AWX_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "template id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "template name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def template_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            res = self.client.job_template.get(oid)

            if self.is_output_text():
                res.pop("related", None)
                res.pop("summary_fields", None)
                self.app.render(res, details=True)
                self.c("\njobs", "underline")
                jobs = self.client.job_template.list_jobs(oid)
                self.app.render(
                    jobs,
                    headers=[
                        "id",
                        "type",
                        "launch_type",
                        "status",
                        "started",
                        "finished",
                        "elapsed",
                    ],
                )
            else:
                self.app.render(res, details=True)
        else:
            name = self.app.pargs.name
            size = self.app.pargs.size
            page = self.app.pargs.page
            if page == 0:
                page = 1
            res = self.client.job_template.list(name=name, page_size=size, page=page)
            headers = [
                "id",
                "name",
                "inventory",
                "project",
                "job_type",
                "playbook",
                "status",
                "last_job",
                "created",
            ]
            fields = [
                "id",
                "name",
                "inventory",
                "project",
                "job_type",
                "playbook",
                "status",
                "summary_fields.last_job.id",
                "created",
            ]
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help="add template",
        description="add template",
        arguments=AWX_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "template name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["inventory"],
                    {
                        "help": "inventory id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["project"],
                    {
                        "help": "project id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["playbook"],
                    {
                        "help": "playbook",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-verbosity"],
                    {
                        "help": "verbosity: 0 (Normal) (default), 1 (Verbose), 2 (More Verbose), 3 (Debug), "
                        "4 (Connection Debug), 5 (WinRM Debug)",
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
            ]
        ),
    )
    def template_add(self):
        name = self.app.pargs.name
        inventory = self.app.pargs.inventory
        project = self.app.pargs.project
        playbook = self.app.pargs.playbook
        verbosity = self.app.pargs.verbosity
        res = self.client.job_template.add(
            name,
            "run",
            inventory,
            project,
            playbook,
            ask_credential_on_launch=True,
            ask_variables_on_launch=True,
            ask_limit_on_launch=True,
            verbosity=verbosity,
        )
        job_template = res["id"]
        self.app.render({"msg": "add template %s" % job_template})

    @ex(
        help="launch template",
        description="launch template",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "template id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["credentials"],
                    {
                        "help": "comma separated credentials id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-extras"],
                    {
                        "help": "variables used when launching job template, k1:v1;k2:v2",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def template_launch(self):
        oid = self.app.pargs.id
        credentials = self.app.pargs.credentials
        extras = self.app.pargs.extras
        # limit = 'provola-dctest.site03.nivolapiemonte.it'

        # extra_vars = {
        #     'p_mysql_repo_version': '5.7.23',
        #     'p_mysql_basedir': '/data',
        #     'p_mysql_db_type': 'default',
        #     'p_mysql_root_username': 'root',
        #     'p_mysql_root_password': 'nnn',
        #     'p_ip_repository': '###.###.###.###',
        #     'p_proxy_server': 'http://###.###.###.###:3128'
        # }

        extra_vars = {}
        if extras is not None:
            for item in extras.split(";"):
                k, v = item.split(":", 1)
                # remove quotes at the beginning and the end of the string if present
                v = v.strip("'")
                if k == "host_groups" or k == "host_templates":
                    # convert string to list
                    v = v.strip("][").split(", ")
                extra_vars[k] = v

        params = {
            "credentials": credentials.split(","),
            "extra_vars": extra_vars,
            # 'limit': limit
        }
        job = self.client.job_template.launch(oid, **params)
        self.__wait_for_job(self.client.job.get, job["id"], delta=2)
        self.app.render({"msg": "launch template %s" % oid})

    @ex(
        help="delete template",
        description="delete template",
        arguments=AWX_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "template id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def template_del(self):
        oid = self.app.pargs.id
        self.client.job_template.delete(oid)
        self.app.render({"msg": "delete template %s" % oid}, headers=["msg"])

    # Execution Environments
    @ex(
        help="get execution environments",
        description="get execution environments",
        example="",
        arguments=AWX_ARGS(
            [
                (
                    ["-id"],
                    {"help": "job id", "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def execution_environments_get(self):
        oid = self.app.pargs.id
        if oid is not None:
            res = self.client.execution_environments.get(oid)

            if self.is_output_text():
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            size = self.app.pargs.size
            page = self.app.pargs.page
            if page == 0:
                page = 1
            res = self.client.execution_environments.list(page_size=size, page=page)
            self.app.render(
                res,
                headers=[
                    "id",
                    "name",
                    # "type",
                    "image",
                    "managed",
                    "organization",
                    "pull",
                    "created",
                    "modified",
                ],
            )
