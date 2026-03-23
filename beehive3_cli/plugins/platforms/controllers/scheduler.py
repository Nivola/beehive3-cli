# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from threading import Thread
from cement import ex
from beecell.types.type_dict import dict_set, dict_get

from beecell.types.type_string import split_string_in_chunks, str2bool, truncate
from beecell.types.type_list import merge_list
from beehive3_cli.core.controller import BaseController, PAGINATION_ARGS, BASE_ARGS
from beehive3_cli.core.exc import CliManagerError
from beehive3_cli.core.util import load_config
from beehive3_cli.plugins.platforms.controllers import ChildPlatformController
from beehive3_cli.translate import _


def scheed_args(*list_args):
    scheduler_args = [
        (["subsystem"], {"help": _("cmp subsystem"), "action": "store", "type": str}),
        (
            ["--entity"],
            {"action": "store", "dest": "entity", "help": _("cmp entity class")},
        ),
    ]
    res = merge_list(BASE_ARGS, scheduler_args, *list_args)
    return res


def sched_pargs(*list_args):
    scheduler_args = [
        (["subsystem"], {"help": _("cmp subsystem"), "action": "store", "type": str}),
        (
            ["--entity"],
            {"action": "store", "dest": "entity", "help": _("cmp entity class")},
        ),
    ]
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, scheduler_args, *list_args)
    return res


class CmpSchedulerController(BaseController):
    class Meta:
        label = "scheduler"
        stacked_on = "platform"
        stacked_type = "nested"
        description = _("cmp scheduler management")
        help = _("cmp scheduler management")


class CmpSchedulerTaskController(ChildPlatformController):
    class Meta:
        label = "tasks"
        stacked_on = "scheduler"
        stacked_type = "nested"
        description = _("cmp scheduler task management")
        help = _("cmp scheduler task management")

        cmp_dict = {
            "auth": {"baseuri": "/v2.0/nas", "subsystem": "auth"},
            "catalog": {"baseuri": "/v2.0/ncs", "subsystem": "catalog"},
            "event": {"baseuri": "/v2.0/nes", "subsystem": "event"},
            "resource": {"baseuri": "/v2.0/nrs", "subsystem": "resource"},
            "ssh": {"baseuri": "/v2.0/gas", "subsystem": "resource"},
            "service": {"baseuri": "/v2.0/nws", "subsystem": "resource"},
        }

        headers = [
            "uuid",
            "name",
            "parent",
            "api_id",
            "status",
            "worker",
            "start_time",
            "stop_time",
            "duration",
        ]
        fields = [
            "uuid",
            "alias",
            "parent",
            "api_id",
            "status",
            "worker",
            "start_time",
            "stop_time",
            "duration",
        ]

        step_headers = [
            "uuid",
            "name",
            "status",
            "start_time",
            "stop_time",
            "duration",
            "result",
        ]
        step_fields = [
            "uuid",
            "name",
            "status",
            "start_time",
            "stop_time",
            "duration",
            "result",
        ]

        trace_headers = ["date", "level", "step", "message"]
        trace_fields = ["date", "level", "step_name", "message"]

    def pre_command_run(self):
        super().pre_command_run()
        self.get_susbsytem()
        self.configure_cmp_api_client()

    def get_susbsytem(self):
        """Get subsystem"""
        self._meta.cmp = self._meta.cmp_dict.get(self.app.pargs.subsystem, None)
        if self._meta.cmp is None:
            raise CliManagerError("subsystem is not correct")

    @ex(
        help=_("list all available tasks you can invoke"),
        description=_("list all available tasks you can invoke"),
        arguments=scheed_args(),
    )
    def definitions(self):
        uri = f"{self.baseuri}/definitions"
        res = self.cmp_get(uri)
        resp = []
        for k, v in res.get("task_definitions", {}).items():
            for item in v:
                resp.append({"worker": k, "task": item})
        self.app.render(resp, headers=["worker", "task"], maxsize=100)

    @ex(
        help=_("get task instances"),
        description=_("get task instances"),
        example="beehive platform scheduler tasks get service -id <uuid>",
        arguments=sched_pargs(
            [
                (["-id"], {"help": _("task uuid"), "action": "store", "type": str}),
                (
                    ["-objid"],
                    {"help": _("task entity objid"), "action": "store", "type": str},
                ),
                (
                    ["-trace"],
                    {
                        "help": _("task entity objid"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
                (
                    ["-parent"],
                    {
                        "help": _("parent task uuid and optional step"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-parentonly"],
                    {
                        "help": _("task has a parent task or not (True/False)"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-api_id"],
                    {
                        "help": _("api_id"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        trace = str2bool(self.app.pargs.trace)
        if oid is not None:
            uri = f"{self.baseuri}/worker/tasks/{oid}"
            res = self.cmp_get(uri)
            task = res.get("task_instance", {})

            if self.is_output_text():
                steps = task.pop("steps", [])
                args = task.pop("args", {})
                if steps is None:
                    steps = []
                if args is None:
                    args = {}

                self.app.render(task, details=True)
                self.c("\nargs", "underline")
                self.app.render(args, details=True)
                self.c("\nsteps", "underline")
                self.app.render(
                    steps,
                    headers=self._meta.step_headers,
                    fields=self._meta.step_fields,
                    maxsize=40,
                )

                def __transform(m):
                    nm = split_string_in_chunks(m, pos=150)
                    nm2 = "\n".join(nm)
                    return nm2
                    # return self.app.colored_text.output(nm2, 'WHITE')

                if trace is True:
                    self.c("\ntrace", "underline")
                    uri = f"{self.baseuri}/worker/tasks/{oid}/trace"
                    res = self.cmp_get(uri)
                    trace = res.get("task_trace", [])
                    transform = {}  # {"message": __transform}
                    self.app.render(
                        trace,
                        headers=self._meta.trace_headers,
                        fields=self._meta.trace_fields,
                        maxsize=10000,
                        transform=transform,
                    )
            else:
                self.app.render(res, details=True)
        else:
            params = ["name", "objid", "parent", "api_id", "parentonly"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/worker/tasks"
            res = self.cmp_get(uri, data=data)
            transform = {
                # "worker": lambda n: "-".join(n.split("-")[1:]),
                "worker": self.worker_format,
                "parent": lambda n: truncate(n, 36, append_dots=False),
                "status": self.color_error,
            }

            headers_tasks = [
                "uuid",
                "name",
                "parent",
                "api_id",
                "status",
                "pod - worker",
                "start_time",
                "stop_time",
                "duration",
            ]

            self.app.render(
                res,
                key="task_instances",
                # headers=self._meta.headers,
                headers=headers_tasks,
                fields=self._meta.fields,
                maxsize=80,
                transform=transform,
            )


    @ex(
        help=_("tree task instances"),
        description=_("tree task instances"),
        example="beehive platform scheduler tasks tree service id <uuid>",
        arguments=sched_pargs(
            [
                (["id"], {"help": _("task uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def subtree(self):
        oid = self.app.pargs.id
        # get selected task
        uri = f"{self.baseuri}/worker/tasks/{oid}"
        res = self.cmp_get(uri, data={})
        task_instance = res.get("task_instance")
        api_id = task_instance.get("api_id")
        uuid = task_instance.get("uuid")
        alias = task_instance.get("alias")
        print(f"{uuid} - {alias}")

        # get tasks with the same api_id
        uri = f"{self.baseuri}/worker/tasks"
        data_filter = {
            "api_id": api_id,
            "size": -1,
            "field": "id",
            "order": "ASC",
        }
        res = self.cmp_get(uri, data=data_filter)
        task_instances = res.get("task_instances")

        # count childs
        task_dict = {task_instance.get("uuid"): task_instance for task_instance in task_instances}

        for task_instance in task_instances:
            child_parent:str = task_instance.get("parent")
            #child_uuid = task_instance.get("uuid")

            if child_parent is not None:
                parent_uuid = child_parent.split(":")[0]
                parent = task_dict.get(parent_uuid)
                if parent is not None:
                    num_childs = dict_get(parent, "num_childs", default=0)
                    num_childs += 1
                    dict_set(parent, "num_childs", num_childs)

        # print(task_dict)

        self.print_subtree(task_instances, task_dict, uuid)

    def print_subtree(self, task_instances, task_dict, uuid, tab=""):
        # rendering elements
        # - horizontal tree connector
        h_conn = "└── "
        # - vertical tree connector
        v_conn = "|"

        current_tab = None
        next_tab = None

        for task_instance in task_instances:
            child_parent:str = task_instance.get("parent")
            child_uuid = task_instance.get("uuid")
            #child_name = task_instance.get("name")
            child_alias = task_instance.get("alias")
            child_status = task_instance.get("status")
            child_duration = task_instance.get("duration")

            # check task parent
            if child_parent is not None and child_parent.startswith(uuid):
                parent_uuid = child_parent.split(":")[0]
                parent = task_dict.get(parent_uuid)

                spaces = 4
                if parent is not None:
                    num_childs = dict_get(parent, "num_childs", default=0)
                    if num_childs > 1:
                        if current_tab is None:
                            next_tab = tab + v_conn.ljust(spaces, " ")

                        # decrease num_childs
                        num_childs -= 1
                        dict_set(parent, "num_childs", num_childs)
                        current_tab = tab + h_conn
                    else:
                        next_tab = tab + "".ljust(spaces, " ")
                        current_tab = tab + h_conn

                print(
                    f"{current_tab}{child_uuid} - "
                    f"{self.app.colored_text.bold_2(child_alias)} - "
                    f"{self.color_error(child_status)} "
                    f"{child_duration} {self.awx_detail(child_uuid, child_alias)}"
                )

                self.print_subtree(task_instances, task_dict, child_uuid, next_tab)

    def awx_detail(self, uuid, alias):
        if alias == "AppliedComputeCustomization.create":
            uri = f"{self.baseuri}/worker/tasks/{uuid}"
            res = self.cmp_get(uri, data={})
            task_instance = res.get("task_instance")
            args = task_instance.get("args")
            playbook = args.get("playbook")
            compute_customization_id = args.get("compute_customization_id")

            uri = f"{self.baseuri}/entities/{compute_customization_id}"
            res = self.cmp_get(uri, data={})
            resource = res.get("resource")
            name = resource.get("name")

            return f"({name} - {playbook})"

        return ""


    def worker_format(self, val: str):
        pod = ""
        ret = "-"
        if val is not None:
            index_to = val.index("@")
            index_from = val.rindex(".") + 1
            pod = val[index_from:index_to]
            ret = "-".join(val.split("-")[1:])
        return f"{pod.ljust(11, ' ')} {ret}"

    @ex(
        help=_("display list of related tasks in tree-like format"),
        description=_("display list of related tasks in tree-like format"),
        arguments=sched_pargs(
            [
                (["id"], {"help": _("task uuid"), "action": "store", "type": str}),
                (
                    ["-v"],
                    {
                        "help": _("verbose, if true print task steps as well"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
            ]
        ),
    )
    def tree(self):
        def get_max_len(steps):
            lst = []
            for step in steps:
                lst.append(step.get("name"))
            longest = max(lst, key=len)
            return len(longest)

        def create_filler(s, n):
            return " " * (n - len(s) + 2)

        def render_steps(steps, idx):
            l_max = get_max_len(steps)
            header_name = "name" + create_filler("name", l_max)
            # put this condition at the beginning to display properly (no '|') the case of a tasks list of one element
            if idx == len(tasks) - 1:
                offset = filler_long * idx
                print(f"{offset}{filler_long}steps")
                print(f"{offset}{filler_long}{'uuid':<38}{header_name}status")
                for step in steps:
                    uuid = step.get("uuid")
                    name = step.get("name")
                    name = name + create_filler(name, l_max)
                    status = step.get("status")
                    print(f"{offset}{filler_long}{uuid:<38}{name}{status}")
            elif idx == 0:
                print(f"{v_conn}{filler_short}steps")
                print(f"{v_conn}{filler_short}{'uuid':<38}{header_name}status")
                for step in steps:
                    uuid = step.get("uuid")
                    name = step.get("name")
                    name = name + create_filler(name, l_max)
                    status = step.get("status")
                    print(f"{v_conn}{filler_short}{uuid:<38}{name}{status}")
                print(v_conn)
            else:
                offset = filler_long * idx
                print(f"{offset}{v_conn}{filler_short}steps")
                print(f"{offset}{v_conn}{filler_short}{'uuid':<38}{header_name}status")
                for step in steps:
                    uuid = step.get("uuid")
                    name = step.get("name")
                    name = name + create_filler(name, l_max)
                    status = step.get("status")
                    print(f"{offset}{v_conn}{filler_short}{uuid:<38}{name}{status}")
                print(f"{offset}{v_conn}{filler_short}")

        def render():
            for item in enumerate(reversed(tasks)):
                idx = item[0]
                task_id = item[1].get("task_id")
                alias = item[1].get("alias")
                steps = item[1].get("steps")
                if idx == 0:
                    print(f"task : {task_id}")
                    print(f"alias: {alias}")
                else:
                    offset = filler_long * (idx - 1)
                    print(f"{offset}{h_conn}task : {task_id}")
                    print(f"{offset}{filler_long}alias: {alias}")
                if verbose in ("True", "true"):
                    render_steps(steps, idx)

        def get_parent(oid):
            if oid is None:
                return
            oid = oid.split(":")[0]
            uri = f"{self.baseuri}/worker/tasks/{oid}"
            res = self.cmp_get(uri)
            task = res.get("task_instance", {})
            alias = task.get("alias")
            steps = task.pop("steps", [])
            item = {"task_id": oid, "alias": alias, "steps": steps}
            tasks.append(item)
            parent = task.pop("parent")
            get_parent(parent)

        # rendering elements
        # - horizontal tree connector
        h_conn = "└── "
        # - vertical tree connector
        v_conn = "|"
        # - scale factor
        mul = len(h_conn)
        # - blanks strings of different length
        filler_short = " " * (mul - 1)
        filler_long = filler_short + " "

        tasks = []
        oid = getattr(self.app.pargs, "id", None)
        verbose = self.app.pargs.v
        verbose = str(verbose)
        get_parent(oid)
        render()

    @ex(
        help=_("get task instance status"),
        description=_("get task instance status"),
        arguments=sched_pargs(
            [
                (["task"], {"help": _("task uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def status(self):
        oid = self.app.pargs.task
        uri = f"{self.baseuri}/worker/tasks/{oid}/status"
        res = self.cmp_get(uri)
        task = res.get("task_instance", {})
        self.app.render(task, details=True, maxsize=100)

    @ex(
        help=_("get task instance execution trace"),
        description=_("get task instance execution trace"),
        arguments=sched_pargs(
            [
                (["task"], {"help": _("task uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def trace(self):
        oid = self.app.pargs.task
        uri = f"{self.baseuri}/worker/tasks/{oid}/trace"
        res = self.cmp_get(uri)
        trace = res.get("task_trace", [])
        self.app.render(
            trace,
            headers=self._meta.trace_headers,
            fields=self._meta.trace_fields,
            maxsize=1000,
        )

    @ex(
        help=_("show log for worker instances"),
        description=_("show log for worker instances"),
        arguments=sched_pargs(
            [
                (["task"], {"help": _("task uuid"), "action": "store", "type": str}),
                (
                    ["-index"],
                    {
                        "help": _("index name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-sort"],
                    {
                        "help": _("sort field. Ex. date:desc"),
                        "action": "store",
                        "type": str,
                        "default": "date:desc",
                    },
                ),
                (
                    ["-pretty"],
                    {
                        "help": _("if true show pretty logs"),
                        "action": "store",
                        "type": str,
                        "default": True,
                    },
                ),
                (
                    ["-server"],
                    {
                        "help": _("server ip"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def log(self):
        index = self.app.pargs.index
        #app = self.app.pargs.subsystem
        server = self.app.pargs.server
        task = self.app.pargs.task
        sort = self.app.pargs.sort
        page = self.app.pargs.page
        size = self.app.pargs.size
        pretty = self.app.pargs.pretty

        if index is None:
            # index = self.get_current_elastic_index()
            index = self.get_current_elastic_event_index()

        match = [
            # {"match": {"app": {"query": app, "operator": "and"}}},
            # {"match": {"component": {"query": "task", "operator": "and"}}},
            # {"match": {"task_id": {"query": task, "operator": "and"}}},
            # {"match": {"data.api_id": {"query": task, "operator": "and"}}},
            {"match": {"data.opid": {"query": task, "operator": "and"}}},
        ]

        if server is not None:
            match.append({"match": {"server": {"query": server, "operator": "and"}}})

        query = {"bool": {"must": match}}
        self.app.log.debug(query)

        header = "{date} [{server}] {task_id} {levelname:7} {func}:{lineno} - {message}"
        header = ["id", "type", "date", "data.response", "dest.pod", "data.op"]
        self._query(index, query, page, size, sort, pretty=pretty, header=header)

    @ex(
        help=_("run test task"),
        description=_("run test task"),
        arguments=sched_pargs(
            [
                (
                    ["-number"],
                    {
                        "help": _("number of iteration to run"),
                        "action": "store",
                        "type": int,
                        "default": 1,
                    },
                ),
                (
                    ["-concurrent"],
                    {
                        "help": _("number of concurrent task to run"),
                        "action": "store",
                        "type": int,
                        "default": 1,
                    },
                ),
            ]
        ),
    )
    def test(self):
        number = self.app.pargs.number
        concurrent = self.app.pargs.concurrent
        uri = f"{self.baseuri}/worker/tasks/test"
        data = {"x": 2, "y": 234, "numbers": [2, 78, 45, 90], "mul_numbers": []}

        def inner_test(n):
            print(f"start task test {n}")
            self.cmp_post(uri, data=data)

        for i in range(0, number):
            threads = []
            for n in range(0, concurrent):
                t = Thread(target=inner_test, args=(f"{i}.{n}",))
                threads.append(t)
                t.start()
            for __, thread in enumerate(threads):
                thread.join()

    @ex(
        help=_("run test scheduled action"),
        description=_("run test scheduled action"),
        arguments=sched_pargs(),
    )
    def test2(self):
        uri = f"{self.baseuri}/worker/tasks/test2"
        data = {}
        self.cmp_post(uri, data=data)


class CmpSchedulerSchedController(BaseController):
    class Meta:
        label = "schedules"
        stacked_on = "scheduler"
        stacked_type = "nested"
        description = _("cmp scheduler schedule management")
        help = _("cmp scheduler schedule management")

        cmp_dict = {
            "auth": {"baseuri": "/v2.0/nas/scheduler", "subsystem": "auth"},
            "catalog": {"baseuri": "/v2.0/ncs/scheduler", "subsystem": "catalog"},
            "event": {"baseuri": "/v2.0/nes/scheduler", "subsystem": "event"},
            "resource": {"baseuri": "/v2.0/nrs/scheduler", "subsystem": "resource"},
            "ssh": {"baseuri": "/v2.0/gas/scheduler", "subsystem": "resource"},
            "service": {"baseuri": "/v2.0/nws/scheduler", "subsystem": "resource"},
        }

        headers = [
            "name",
            "task",
            "schedule",
            "args",
            "kwargs",
            "options",
            "last_run_at",
            "total_run_count",
        ]
        fields = [
            "name",
            "task",
            "schedule",
            "args",
            "kwargs",
            "options",
            "last_run_at",
            "total_run_count",
        ]

    def get_susbsytem(self):
        """Get subsystem"""
        self._meta.cmp = self._meta.cmp_dict.get(self.app.pargs.subsystem, None)
        if self._meta.cmp is None:
            raise CliManagerError("subsystem is not correct")

    def pre_command_run(self):
        super().pre_command_run()
        self.get_susbsytem()
        self.configure_cmp_api_client()

    @ex(
        help=_("get schedules"),
        description=_("get schedules"),
        example="beehive platform scheduler schedules get service -e <env>",
        arguments=sched_pargs(
            [
                (["-name"], {"help": _("schedule name"), "action": "store", "type": str}),
            ]
        ),
    )
    def get(self):
        oid = getattr(self.app.pargs, "name", None)
        if oid is not None:
            oid = self.app.pargs.schedule
            uri = f"{self.baseuri}/entries/{oid}"
            res = self.cmp_get(uri)
            trace = res.get("task_trace", [])
            self.app.render(trace, details=True, maxsize=200)
        else:
            params = ["name"]
            mappings = {"name": lambda n: "%" + n + "%"}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/entries"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="schedules",
                headers=self._meta.headers,
                fields=self._meta.fields,
                maxsize=80,
            )

    @ex(
        help=_("create schedule reading data from a json file"),
        description=_("create schedule reading data from a json file"),
        arguments=sched_pargs(
            [
                (
                    ["schedule"],
                    {
                        "help": _("schedule config in json file"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def add(self):
        data = self.app.pargs.schedule
        data = load_config(data)
        uri = f"{self.baseuri}/entries"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add schedule {res.get('name')}"}, headers=["msg"])

    @ex(
        help=_("delete schedule by name"),
        description=_("delete schedule by name"),
        arguments=sched_pargs(
            [
                (
                    ["schedule"],
                    {"help": _("schedule name"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.schedule
        uri = f"{self.baseuri}/entries/{oid}"
        self.cmp_delete(uri)
