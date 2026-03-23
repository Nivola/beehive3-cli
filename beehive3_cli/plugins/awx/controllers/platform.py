# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from sys import stdout
from time import sleep
from cement import ex

from beecell.types.type_list import merge_list
from beecell.file import read_file
from beecell.types.type_dict import dict_get

from beedrones.awx.client import AwxManager

from beehive3_cli.core.controller import BaseController, BASE_ARGS, PAGINATION_ARGS
from beehive3_cli.core.util import load_environment_config
from beehive3_cli.translate import _


def awx_args(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": _("awx platform reference label"),
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
        description = _("awx platform management")
        help = _("awx platform  management")

    def pre_command_run(self):
        super().pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("awx", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No awx default platform is available for this environment. Select another environment"
                )

        if label not in orchestrators:
            raise Exception(f"Valid label are: {', '.join(orchestrators.keys())}")
        self.conf = orchestrators.get(label)

        proto = self.conf.get("proto")
        host = self.conf.get("hosts")[0]
        port = self.conf.get("port")
        path = self.conf.get("path")
        uri = f"{proto}://{host}:{port}{path}"

        if self.app.config.get("log.clilog", "verbose_log"):
            transform = {"msg": lambda x: self.color_string(x, "YELLOW")}
            self.app.render(
                {"msg": f"Using awx orchestrator: {label} (uri: {uri})"},
                transform=transform,
            )
            self.app.log.debug("Using awx orchestrator: %s (uri: %s)", label, uri)

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
                raise TimeoutError(f"job {job_id} query timeout")
        if status in ["failed", "error"]:
            self.app.log.error(job["result_traceback"])
            raise Exception(f"job {job_id} error")
        if status == "cancelled":
            self.app.log.error("job %s cancelled", job_id)
            raise Exception(f"job {job_id} cancelled")
        self.app.log.info("job %s successful", job_id)

    @ex(help=_("ping awx"), description=_("ping awx"), arguments=awx_args())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(help=_("get awx version"), description=_("get awx version"), arguments=awx_args())
    def version(self):
        res = self.client.version()
        self.app.render(res, headers=["version", "ansible_version"])

    @ex(
        help=_("get organizations"),
        description=_("get organizations"),
        arguments=awx_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("organization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("organization name"),
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
        help=_("get inventories"),
        description=_("get inventories"),
        example="beehive platform awx inventory-get",
        arguments=awx_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("inventory id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("inventory name"),
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
        help=_("add inventory"),
        description=_("add inventory"),
        arguments=awx_args(
            [
                (
                    ["name"],
                    {
                        "help": _("inventory name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["organization"],
                    {
                        "help": _("organization id"),
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
        help=_("delete inventory"),
        description=_("delete inventory"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("inventory id"),
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
        self.app.render({"msg": f"delete inventory {oid}"}, headers=["msg"])

    @ex(
        help=_("sync inventory source"),
        description=_("get inventory source"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("inventory source id"),
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
        help=_("get inventory scripts"),
        description=_("get inventory scripts"),
        arguments=awx_args(
            [
                (
                    ["-inventory"],
                    {
                        "help": _("inventory id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {
                        "help": _("group id"),
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
        help=_("add script inventory"),
        description=_("add script inventory"),
        arguments=awx_args(
            [
                (
                    ["name"],
                    {
                        "help": _("script inventory name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["organization"],
                    {
                        "help": _("organization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["script"],
                    {
                        "help": _("script. Ex. #!/bin/bash\nsource /opt/beehive/bin/activate\n"),
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
        help=_("delete script inventory"),
        description=_("delete script inventory"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("inventory id"),
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
        self.app.render({"msg": f"delete script inventory {oid}"}, headers=["msg"])

    @ex(
        help=_("get inventory groups"),
        description=_("get inventory groups"),
        arguments=awx_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("inventory group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("inventory name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-inventory"],
                    {
                        "help": _("inventory id"),
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
        help=_("add inventory group"),
        description=_("add inventory group"),
        arguments=awx_args(
            [
                (
                    ["inventory"],
                    {
                        "help": _("inventory id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("inventory group name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("host description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vars"],
                    {
                        "help": _("host variables. ex: k1:v1,k2:v2"),
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
        lvars = self.app.pargs.vars
        variables = None
        if lvars is not None:
            variables = {}
            if lvars is not None:
                for var in lvars.split(","):
                    k, v = var.split(":", 1)
                    variables[k] = v
        res = self.client.inventory.group_add(inventory, name, desc=desc, vars=variables)
        self.app.render({"msg": f"add group {res['id']}"})

    @ex(
        help=_("delete inventory group"),
        description=_("delete inventory group"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("inventory group id"),
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
        self.app.render({"msg": f"delete group {oid}"}, headers=["msg"])

    @ex(
        help=_("get inventory hosts"),
        description=_("get inventory hosts"),
        arguments=awx_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("inventory group id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("inventory name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-inventory"],
                    {
                        "help": _("inventory id"),
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
        help=_("get add hoc commands"),
        description=_("get add hoc commands"),
        arguments=awx_args(
            [
                (
                    ["-inventory"],
                    {
                        "help": _("inventory id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-id"],
                    {"help": _("job id"), "action": "store", "type": str, "default": None},
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
        help=_("add add hoc commands"),
        description=_("add add hoc commands"),
        arguments=awx_args(
            [
                (
                    ["inventory"],
                    {
                        "help": _("inventory id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["credential"],
                    {
                        "help": _("credential id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-verbosity"],
                    {"help": _("verbosity"), "action": "store", "type": int, "default": 0},
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
        help=_("relaunch add hoc command"),
        description=_("relaunch add hoc command"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {"help": _("job id"), "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def ad_hoc_command_relaunch(self):
        oid = self.app.pargs.id
        res = self.client.ad_hoc_command.relaunch(oid)
        self.app.render(res, details=True)

    @ex(
        help=_("get add hoc command stdout"),
        description=_("get add hoc command stdout"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {"help": _("job id"), "action": "store", "type": str, "default": None},
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
        help=_("get jobs"),
        description=_("get jobs"),
        example="beehive platform awx job-get -id #### -e <env>; beehive platform awx job-get",
        arguments=awx_args(
            [
                (
                    ["-id"],
                    {"help": _("job id"), "action": "store", "type": str, "default": None},
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
                    "name",
                    "type",
                    "playbook",
                    # "launch_type",
                    "status",
                    "started",
                    "finished",
                    "elapsed",
                    "job_tags",
                ],
            )

    @ex(
        help=_("relaunch job"),
        description=_("relaunch job"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {"help": _("job id"), "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def job_relaunch(self):
        oid = self.app.pargs.id
        res = self.client.job.relaunch(oid)
        print(f"new job id {res}")

    @ex(
        help=_("get job stdout"),
        description=_("get job stdout"),
        example="beehive platform awx job-stdout ####; beehive platform awx job-stdout ####",
        arguments=awx_args(
            [
                (
                    ["id"],
                    {"help": _("job id"), "action": "store", "type": str, "default": None},
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
        help=_("get job events"),
        description=_("get job events"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {"help": _("job id"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-query"],
                    {
                        "help": _("job event query. Comma separated k:v"),
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
        lfilter = {}
        if query is not None:
            for item in query.split(","):
                k, v = item.split(":")
                lfilter[k] = v
        res = self.client.job.events(oid, query=lfilter)
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
        help=_("get job error"),
        description=_("get job error"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {"help": _("job id"), "action": "store", "type": str, "default": None},
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
        help=_("get hosts"),
        description=_("get hosts"),
        arguments=awx_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("host name"),
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
        help=_("add host"),
        description=_("add host"),
        arguments=awx_args(
            [
                (
                    ["name"],
                    {
                        "help": _("host name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["inventory"],
                    {
                        "help": _("inventory id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("host description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-vars"],
                    {
                        "help": _("host variables. ex: k1:v1,k2:v2"),
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
        lvars = self.app.pargs.vars
        variables = None
        if lvars is not None:
            variables = {}
            if lvars is not None:
                for var in lvars.split(","):
                    k, v = var.split(":", 1)
                    variables[k] = v
        res = self.client.host.add(name, inventory, desc=desc, vars=variables)
        self.app.render({"msg": f"add host {res['id']}"})

    @ex(
        help=_("delete host"),
        description=_("delete host"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("host id"),
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
        self.app.render({"msg": f"delete host {oid}"}, headers=["msg"])

    @ex(
        help=_("add group to host"),
        description=_("add group to host"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["group"],
                    {
                        "help": _("group id"),
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
        self.app.render({"msg": f"add group {group} to host {oid}"}, headers=["msg"])

    @ex(
        help=_("remove group from host"),
        description=_("remove group from host"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("host id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["group"],
                    {
                        "help": _("group id"),
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
        self.app.render({"msg": f"remove group {group} from host {oid}"}, headers=["msg"])

    @ex(
        help=_("get credentials"),
        description=_("get credentials"),
        arguments=awx_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("credential id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("credential name"),
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
        help=_("get credential types"),
        description=_("get credential types"),
        arguments=awx_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("credential type id"),
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
        help=_("add ssh credential"),
        description=_("add ssh credential"),
        arguments=awx_args(
            [
                (
                    ["name"],
                    {
                        "help": _("credential name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["organization"],
                    {
                        "help": _("organization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["username"],
                    {
                        "help": _("username"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-password"],
                    {
                        "help": _("password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-key_data"],
                    {
                        "help": _("ssh key data file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-key_unlock"],
                    {
                        "help": _("ssh key unlock"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-become"],
                    {
                        "help": _("become method"),
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
        self.app.render({"msg": f"add ssh credential {res['id']}"})

    @ex(
        help=_("add git credential"),
        description=_("add git credential"),
        arguments=awx_args(
            [
                (
                    ["name"],
                    {
                        "help": _("credential name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["organization"],
                    {
                        "help": _("organization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["username"],
                    {
                        "help": _("username"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["password"],
                    {
                        "help": _("password"),
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
        self.app.render({"msg": f"add ssh credential {res['id']}"})

    @ex(
        help=_("delete credential"),
        description=_("delete credential"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("credential id"),
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
        self.app.render({"msg": f"delete credential {oid}"}, headers=["msg"])

    @ex(
        help=_("get projects"),
        description=_("get projects"),
        example="beehive platform awx project-get",
        arguments=awx_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("project name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-search"],
                    {
                        "help": _("search"),
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
        help=_("add project"),
        description=_("add project"),
        arguments=awx_args(
            [
                (
                    ["name"],
                    {
                        "help": _("project name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["organization"],
                    {
                        "help": _("organization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["credential"],
                    {
                        "help": _("credential id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["scm_url"],
                    {
                        "help": _("scm url"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-scm_type"],
                    {
                        "help": _("scm type"),
                        "action": "store",
                        "type": str,
                        "default": "git",
                    },
                ),
                (
                    ["-scm_branch"],
                    {
                        "help": _("scm branch"),
                        "action": "store",
                        "type": str,
                        "default": "master",
                    },
                ),
                (
                    ["-scm_update_on_launch"],
                    {
                        "help": _("scm update on launch"),
                        "action": "store",
                        "type": bool,
                        "default": True,
                    },
                ),
                (
                    ["-default_environment"],
                    {
                        "help": _("default environment"),
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
        self.app.render({"msg": f"add project {project}"})

    @ex(
        help=_("delete project"),
        description=_("delete project"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("project id"),
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
        self.app.render({"msg": f"delete project {oid}"}, headers=["msg"])

    @ex(
        help=_("sync project"),
        description=_("sync project"),
        example="beehive platform awx project-sync ### -e <env>; beehive platform awx project-sync ###",
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("project id"),
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
        self.app.render({"msg": f"sync project {oid}"}, headers=["msg"])

    @ex(
        help=_("get project job"),
        description=_("get project job"),
        arguments=awx_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("project job id"),
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
        help=_("get project job events"),
        description=_("get project job events"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("project job id"),
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
        help=_("get project job stdout"),
        description=_("get project job stdout"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("project job id"),
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
        lstdout = self.client.project.job.stdout(oid)
        print(lstdout.get("content", ""))

    @ex(
        help=_("get templates"),
        description=_("get templates"),
        arguments=awx_args(
            [
                (
                    ["-id"],
                    {
                        "help": _("template id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("template name"),
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
        help=_("add template"),
        description=_("add template"),
        arguments=awx_args(
            [
                (
                    ["name"],
                    {
                        "help": _("template name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["inventory"],
                    {
                        "help": _("inventory id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["project"],
                    {
                        "help": _("project id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["playbook"],
                    {
                        "help": _("playbook"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-verbosity"],
                    {
                        "help": _(
                            "verbosity: 0 (Normal) (default), 1 (Verbose), 2 (More Verbose), 3 (Debug), "
                            "4 (Connection Debug), 5 (WinRM Debug)"
                        ),
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
        self.app.render({"msg": f"add template {job_template}"})

    @ex(
        help=_("launch template"),
        description=_("launch template"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("template id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["credentials"],
                    {
                        "help": _("comma separated credentials id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-extras"],
                    {
                        "help": _("variables used when launching job template, k1:v1;k2:v2"),
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

        extra_vars = {}
        if extras is not None:
            for item in extras.split(";"):
                k, v = item.split(":", 1)
                # remove quotes at the beginning and the end of the string if present
                v = v.strip("'")
                if k in ('host_groups', 'host_templates'):
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
        self.app.render({"msg": f"launch template {oid}"})

    @ex(
        help=_("delete template"),
        description=_("delete template"),
        arguments=awx_args(
            [
                (
                    ["id"],
                    {
                        "help": _("template id"),
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
        self.app.render({"msg": f"delete template {oid}"}, headers=["msg"])

    # Execution Environments
    @ex(
        help=_("get execution environments"),
        description=_("get execution environments"),
        example="",
        arguments=awx_args(
            [
                (
                    ["-id"],
                    {"help": _("job id"), "action": "store", "type": str, "default": None},
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
