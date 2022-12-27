# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from threading import Thread
from beecell.types.type_string import split_string_in_chunks, str2bool, truncate
from beecell.types.type_list import merge_list
from beehive3_cli.core.controller import BaseController, PAGINATION_ARGS, BASE_ARGS
from beehive3_cli.core.exc import CliManagerError
from beehive3_cli.core.util import load_config
from beehive3_cli.plugins.platform.controllers import ChildPlatformController
from cement import ex


def SCHED_ARGS(*list_args):
    scheduler_args = [
        (['subsystem'], {'help': 'cmp subsystem', 'action': 'store', 'type': str}),
        (['--entity'], {'action': 'store', 'dest': 'entity', 'help': 'cmp entity class'}),
    ]
    res = merge_list(BASE_ARGS, scheduler_args, *list_args)
    return res


def SCHED_PARGS(*list_args):
    scheduler_args = [
        (['subsystem'], {'help': 'cmp subsystem', 'action': 'store', 'type': str}),
        (['--entity'], {'action': 'store', 'dest': 'entity', 'help': 'cmp entity class'}),
    ]
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, scheduler_args, *list_args)
    return res


class CmpSchedulerController(BaseController):
    class Meta:
        label = 'scheduler'
        stacked_on = 'platform'
        stacked_type = 'nested'
        description = "cmp scheduler management"
        help = "cmp scheduler management"
        

class CmpSchedulerTaskController(ChildPlatformController):
    class Meta:
        label = 'tasks'
        stacked_on = 'scheduler'
        stacked_type = 'nested'
        description = "cmp scheduler task management"
        help = "cmp scheduler task management"

        cmp_dict = {
            'auth': {'baseuri': '/v2.0/nas', 'subsystem': 'auth'},
            'catalog': {'baseuri': '/v2.0/ncs', 'subsystem': 'catalog'},
            'event': {'baseuri': '/v2.0/nes', 'subsystem': 'event'},
            'resource': {'baseuri': '/v2.0/nrs', 'subsystem': 'resource'},
            'ssh': {'baseuri': '/v2.0/gas', 'subsystem': 'resource'},
            'service': {'baseuri': '/v2.0/nws', 'subsystem': 'resource'},
        }

        headers = ['uuid', 'name', 'parent', 'api_id', 'status', 'worker', 'start_time', 'stop_time', 'duration']
        fields = ['uuid', 'alias', 'parent', 'api_id', 'status', 'worker', 'start_time', 'stop_time', 'duration']

        step_headers = ['uuid', 'name', 'status', 'start_time', 'stop_time', 'duration', 'result']
        step_fields = ['uuid', 'name', 'status', 'start_time', 'stop_time', 'duration', 'result']

        trace_headers = ['date', 'level', 'step', 'message']
        trace_fields = ['date', 'level', 'step_name', 'message']

    def pre_command_run(self):
        super(CmpSchedulerTaskController, self).pre_command_run()
        self.get_susbsytem()
        self.configure_cmp_api_client()

    def get_susbsytem(self):
        """Get subsystem"""
        self._meta.cmp = self._meta.cmp_dict.get(self.app.pargs.subsystem, None)
        if self._meta.cmp is None:
            raise CliManagerError('subsystem is not correct')

    @ex(
        help='list all available tasks you can invoke',
        description='list all available tasks you can invoke',
        arguments=SCHED_ARGS()
    )
    def definitions(self):
        uri = '%s/definitions' % self.baseuri
        res = self.cmp_get(uri)
        resp = []
        for k, v in res.get('task_definitions', {}).items():
            for item in v:
                resp.append({'worker': k, 'task': item})
        self.app.render(resp, headers=['worker', 'task'], maxsize=100)

    @ex(
        help='get task instances',
        description='get task instances',
        arguments=SCHED_PARGS([
            (['-id'], {'help': 'task uuid', 'action': 'store', 'type': str}),
            (['-objid'], {'help': 'task entity objid', 'action': 'store', 'type': str}),
            (['-trace'], {'help': 'task entity objid', 'action': 'store', 'type': str, 'default': 'true'}),
        ])
    )
    def get(self):
        oid = self.app.pargs.id
        trace = str2bool(self.app.pargs.trace)
        if oid is not None:
            uri = '%s/worker/tasks/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)
            task = res.get('task_instance', {})

            if self.is_output_text():
                steps = task.pop('steps', [])
                args = task.pop('args', {})
                if steps is None:
                    steps = []
                if args is None:
                    args = {}

                self.app.render(task, details=True)
                self.c('\nargs', 'underline')
                self.app.render(args, details=True)
                self.c('\nsteps', 'underline')
                self.app.render(steps, headers=self._meta.step_headers, fields=self._meta.step_fields, maxsize=40)

                def __transform(m):
                    nm = split_string_in_chunks(m, pos=150)
                    nm2 = '\n'.join(nm)
                    return nm2
                    # return self.app.colored_text.output(nm2, 'WHITE')

                if trace is True:
                    self.c('\ntrace', 'underline')
                    uri = '%s/worker/tasks/%s/trace' % (self.baseuri, oid)
                    res = self.cmp_get(uri)
                    trace = res.get('task_trace', [])
                    transform = {
                        'message': __transform
                    }
                    self.app.render(trace, headers=self._meta.trace_headers, fields=self._meta.trace_fields,
                                    maxsize=1000, transform=transform)
            else:
                self.app.render(res, details=True)
        else:
            params = ['name', 'objid']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/worker/tasks' % self.baseuri
            res = self.cmp_get(uri, data=data)
            transform = {
                'worker': lambda n: '-'.join(n.split('-')[1:]),
                'parent': lambda n: truncate(n, 20),
                'status': self.color_error,
            }
            self.app.render(res, key='task_instances', headers=self._meta.headers, fields=self._meta.fields, maxsize=80,
                            transform=transform)

    @ex(
        help='display list of related tasks in tree-like format',
        description='display list of related tasks in tree-like format',
        arguments=SCHED_PARGS([
            (['id'], {'help': 'task uuid', 'action': 'store', 'type': str}),
            (['-v'], {'help': 'verbose, if true print task steps as well', 'action': 'store', 'type': str,
                      'default': True}),
        ])
    )
    def tree(self):
        def get_max_len(steps):
            lst = []
            for step in steps:
                lst.append(step.get('name'))
            longest = max(lst, key=len)
            return len(longest)

        def create_filler(s, n):
            return ' ' * (n - len(s) + 2)

        def render_steps(steps, idx):
            max = get_max_len(steps)
            header_name = 'name' + create_filler('name', max)
            # put this condition at the beginning to display properly (no '|') the case of a tasks list of one element
            if idx == len(tasks) - 1:
                offset = filler_long * idx
                print('{}{}steps'.format(offset, filler_long))
                print('{}{}{:<38}{}{}'.format(offset, filler_long, 'uuid', header_name, 'status'))
                for step in steps:
                    uuid = step.get('uuid')
                    name = step.get('name')
                    name = name + create_filler(name, max)
                    status = step.get('status')
                    print('{}{}{:<38}{}{}'.format(offset, filler_long, uuid, name, status))
            elif idx == 0:
                print('{}{}steps'.format(v_conn, filler_short))
                print('{}{}{:<38}{}{}'.format(v_conn, filler_short, 'uuid', header_name, 'status'))
                for step in steps:
                    uuid = step.get('uuid')
                    name = step.get('name')
                    name = name + create_filler(name, max)
                    status = step.get('status')
                    print('{}{}{:<38}{}{}'.format(v_conn, filler_short, uuid, name, status))
                print(v_conn)
            else:
                offset = filler_long * idx
                print('{}{}{}steps'.format(offset, v_conn, filler_short))
                print('{}{}{}{:<38}{}{}'.format(offset, v_conn, filler_short, 'uuid', header_name, 'status'))
                for step in steps:
                    uuid = step.get('uuid')
                    name = step.get('name')
                    name = name + create_filler(name, max)
                    status = step.get('status')
                    print('{}{}{}{:<38}{}{}'.format(offset, v_conn, filler_short, uuid, name, status))
                print('{}{}{}'.format(offset, v_conn, filler_short))

        def render():
            for item in enumerate(reversed(tasks)):
                idx = item[0]
                task_id = item[1].get('task_id')
                alias = item[1].get('alias')
                steps = item[1].get('steps')
                if idx == 0:
                    print('task : {}'.format(task_id))
                    print('alias: {}'.format(alias))
                else:
                    offset = filler_long * (idx - 1)
                    print('{}{}task : {}'.format(offset, h_conn, task_id))
                    print('{}{}alias: {}'.format(offset, filler_long, alias))
                if verbose == 'True' or verbose == 'true':
                    render_steps(steps, idx)

        def get_parent(oid):
            if oid is None:
                return
            oid = oid.split(':')[0]
            uri = '%s/worker/tasks/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)
            task = res.get('task_instance', {})
            alias = task.get('alias')
            steps = task.pop('steps', [])
            item = {
                'task_id': oid,
                'alias': alias,
                'steps': steps
            }
            tasks.append(item)
            parent = task.pop('parent')
            get_parent(parent)

        # rendering elements
        # - horizontal tree connector
        h_conn = '└── '
        # - vertical tree connector
        v_conn = '|'
        # - scale factor
        mul = len(h_conn)
        # - blanks strings of different length
        filler_short = ' ' * (mul - 1)
        filler_long = filler_short + ' '

        tasks = []
        oid = getattr(self.app.pargs, 'id', None)
        verbose = self.app.pargs.v
        verbose = str(verbose)
        get_parent(oid)
        render()

    @ex(
        help='get task instance status',
        description='get task instance status',
        arguments=SCHED_PARGS([
            (['task'], {'help': 'task uuid', 'action': 'store', 'type': str}),
        ])
    )
    def status(self):
        oid = self.app.pargs.task
        uri = '%s/worker/tasks/%s/status' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        task = res.get('task_instance', {})
        self.app.render(task, details=True, maxsize=100)

    @ex(
        help='get task instance execution trace',
        description='get task instance execution trace',
        arguments=SCHED_PARGS([
            (['task'], {'help': 'task uuid', 'action': 'store', 'type': str}),
        ])
    )
    def trace(self):
        oid = self.app.pargs.task
        uri = '%s/worker/tasks/%s/trace' % (self.baseuri, oid)
        res = self.cmp_get(uri)
        trace = res.get('task_trace', [])
        self.app.render(trace, headers=self._meta.trace_headers, fields=self._meta.trace_fields, maxsize=1000)

    @ex(
        help='show log for worker instances',
        description='show log for worker instances',
        arguments=SCHED_PARGS([
            (['task'], {'help': 'task uuid', 'action': 'store', 'type': str}),
            (['-index'], {'help': 'index name', 'action': 'store', 'type': str, 'default': None}),
            (['-sort'], {'help': 'sort field. Ex. date:desc', 'action': 'store', 'type': str, 'default': 'date:desc'}),
            (['-pretty'], {'help': 'if true show pretty logs', 'action': 'store', 'type': bool, 'default': True}),
            (['-server'], {'help': 'server ip', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def log(self):
        index = self.app.pargs.index
        app = self.app.pargs.subsystem
        server = self.app.pargs.server
        task = self.app.pargs.task
        sort = self.app.pargs.sort
        page = self.app.pargs.page
        size = self.app.pargs.size
        pretty = self.app.pargs.pretty

        if index is None:
            index = self.get_current_elastic_index()

        match = [
            {'match': {'app': {'query': app, 'operator': 'and'}}},
            {'match': {'component': {'query': 'task', 'operator': 'and'}}},
            {'match': {'task_id': {'query': task, 'operator': 'and'}}}
        ]

        if server is not None:
            match.append({'match': {'server': {'query': server, 'operator': 'and'}}})

        query = {
            'bool': {
                'must': match
            }
        }
        self.app.log.debug(query)

        header = '{date} [{server}] {task_id} {levelname:7} {func}:{lineno} - {message}'
        self._query(index, query, page, size, sort, pretty=pretty, header=header)

    @ex(
        help='run test task',
        description='run test task',
        arguments=SCHED_PARGS([
            (['-number'], {'help': 'number of iteration to run', 'action': 'store', 'type': int, 'default': 1}),
            (['-concurrent'], {'help': 'number of concurrent task to run', 'action': 'store', 'type': int,
                               'default': 1}),
        ])
    )
    def test(self):
        number = self.app.pargs.number
        concurrent = self.app.pargs.concurrent
        uri = '%s/worker/tasks/test' % self.baseuri
        data = {'x': 2, 'y': 234, 'numbers': [2, 78, 45, 90], 'mul_numbers': []}

        def inner_test(n):
            print('start task test %s' % n)
            res = self.cmp_post(uri, data=data)

        for i in range(0, number):
            threads = list()
            for n in range(0, concurrent):
                t = Thread(target=inner_test, args=('%s.%s' % (i, n),))
                threads.append(t)
                t.start()
            for index, thread in enumerate(threads):
                thread.join()


    @ex(
        help='run test scheduled action',
        description='run test scheduled action',
        arguments=SCHED_PARGS()
    )
    def test2(self):
        uri = '%s/worker/tasks/test2' % self.baseuri
        data = {}
        res = self.cmp_post(uri, data=data)


class CmpSchedulerSchedController(BaseController):
    class Meta:
        label = 'schedules'
        stacked_on = 'scheduler'
        stacked_type = 'nested'
        description = "cmp scheduler schedule management"
        help = "cmp scheduler schedule management"

        cmp_dict = {
            'auth': {'baseuri': '/v2.0/nas/scheduler', 'subsystem': 'auth'},
            'catalog': {'baseuri': '/v2.0/ncs/scheduler', 'subsystem': 'catalog'},
            'event': {'baseuri': '/v2.0/nes/scheduler', 'subsystem': 'event'},
            'resource': {'baseuri': '/v2.0/nrs/scheduler', 'subsystem': 'resource'},
            'ssh': {'baseuri': '/v2.0/gas/scheduler', 'subsystem': 'resource'},
            'service': {'baseuri': '/v2.0/nws/scheduler', 'subsystem': 'resource'},
        }

        headers = ['name', 'task', 'schedule', 'args', 'kwargs', 'options', 'last_run_at', 'total_run_count']
        fields = ['name', 'task', 'schedule', 'args', 'kwargs', 'options', 'last_run_at', 'total_run_count']

    def get_susbsytem(self):
        """Get subsystem"""
        self._meta.cmp = self._meta.cmp_dict.get(self.app.pargs.subsystem, None)
        if self._meta.cmp is None:
            raise CliManagerError('subsystem is not correct')

    def pre_command_run(self):
        super(CmpSchedulerSchedController, self).pre_command_run()
        self.get_susbsytem()
        self.configure_cmp_api_client()

    @ex(
        help='get schedules',
        description='get schedules',
        arguments=SCHED_PARGS([
            (['-name'], {'help': 'schedule name', 'action': 'store', 'type': str}),
        ])
    )
    def get(self):
        oid = getattr(self.app.pargs, 'name', None)
        if oid is not None:
            oid = self.app.pargs.schedule
            uri = '%s/entries/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)
            trace = res.get('task_trace', [])
            self.app.render(trace, details=True, maxsize=200)
        else:
            params = ['name']
            mappings = {'name': lambda n: '%' + n + '%'}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/entries' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='schedules', headers=self._meta.headers, fields=self._meta.fields, maxsize=80)

    @ex(
        help='create schedule reading data from a json file',
        description='create schedule reading data from a json file',
        arguments=SCHED_PARGS([
            (['schedule'], {'help': 'schedule config in json file', 'action': 'store', 'type': str}),
        ])
    )
    def add(self):
        data = self.app.pargs.schedule
        data = load_config(data)
        uri = '%s/entries' % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({'msg': 'add schedule %s' % res.get('name')}, headers=['msg'])

    @ex(
        help='delete schedule by name',
        description='delete schedule by name',
        arguments=SCHED_PARGS([
            (['schedule'], {'help': 'schedule name', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.schedule
        uri = '%s/entries/%s' % (self.baseuri, oid)
        res = self.cmp_delete(uri)
