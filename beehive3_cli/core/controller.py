# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from time import time
from pprint import PrettyPrinter
from argparse import SUPPRESS, Action
from sys import argv, exit
from typing import List
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from six import ensure_binary
from cement import Controller, FrameworkError
from cement.ext.ext_argparse import _clean_func
from beecell.types.type_list import merge_list
from beecell.types.type_dict import dict_get
from beecell.file import read_file
from beehive3_cli.core.argument import CliHelpFormatter
from beehive3_cli.core.cmp_api_client import CmpApiClient
from beehive3_cli.core.exc import CliManagerError
from beehive3_cli.core.util import ColoredText, CmpUtils

BASE_ARGS = [
    (["-y"], {"action": "store_true", "dest": "assumeyes", "help": "Force delete"}),
    (
        ["-e", "--env"],
        {
            "action": "store",
            "dest": "env",
            "help": "Execution environment",
            "default": None,
        },
    ),
    (
        ["-f"],
        {
            "action": "store",
            "dest": "format",
            "help": "Output format",
            "default": "text",
        },
    ),
    (
        ["-k", "--key"],
        {
            "action": "store",
            "dest": "key",
            "help": "Secret key file to use for encryption/decryption",
            "default": None,
        },
    ),
    (
        ["--vault"],
        {
            "action": "store",
            "dest": "vault",
            "help": "Ansible vault password to use for inventory decryption",
            "default": None,
        },
    ),
    # (['--time'], {'action': 'store_true', 'dest': 'time', 'help': 'Print command execution time'}),
    (
        ["--notruncate"],
        {
            "action": "store_true",
            "dest": "notruncate",
            "help": "Disable truncate of output",
        },
    ),
    (
        ["--curl"],
        {
            "action": "store_true",
            "dest": "curl",
            "help": "Print api request as curl command in console log",
        },
    ),
]


PAGINATION_ARGS = [
    (
        ["-size"],
        {
            "help": "list page size [default=20]",
            "action": "store",
            "type": int,
            "default": 20,
        },
    ),
    (
        ["-page"],
        {"help": "list page [default=0]", "action": "store", "type": int, "default": 0},
    ),
    (
        ["-field"],
        {
            "help": "list sort field [default=id]",
            "action": "store",
            "type": str,
            "default": "id",
        },
    ),
    (
        ["-order"],
        {
            "help": "list sort order [default=DESC]",
            "action": "store",
            "type": str,
            "default": "DESC",
        },
    ),
]


def ARGS(*list_args):
    res = merge_list(BASE_ARGS, *list_args)
    return res


def PARGS(*list_args):
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, *list_args)
    return res


class StringAction(Action):
    def __init__(self, option_strings, dest, **kwargs):
        kwargs["nargs"] = "+"
        super(StringAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        values = map(lambda x: x.replace("/", ""), values)
        setattr(namespace, self.dest, " ".join(values))


class CliController(Controller):
    _ct: ColoredText = None  # a ColoredText singleton

    class Meta:
        argument_formatter = CliHelpFormatter

    @property
    def styler(self) -> ColoredText:
        if self._ct is None:
            self._ct = ColoredText()
        return self._ct

    def print_dict(self, data):
        pp = PrettyPrinter()
        pp.pprint(data)

    def _cmd(self, contr, func_name):
        if func_name != "_default":
            contr.pre_command_run()

        func = getattr(contr, func_name)
        # mem_usage()
        res = func()
        # mem_usage()
        return res

    def _process_commands(self, controller):
        label = controller._meta.label
        self.app.log.debug("processing commands for '%s' " % label + "controller namespace")

        commands = controller._collect_commands()
        for command in commands:
            kwargs = self._get_command_parser_options(command)

            func_name = command["func_name"]
            # self.app.log.debug("adding command '%s' " % command['label'] + "(controller=%s, func=%s)" %
            #                    (controller._meta.label, func_name))

            cmd_parent = self._get_parser_parent_by_controller(controller)

            # handle optional example parameter to show example after help message
            example = kwargs.pop("example", None)
            if example:
                epilog = kwargs.get("epilog", "")
                kwargs["epilog"] = "Example: " + example + "\n" + epilog  # TODO avoid \n being stripped

            command_parser = cmd_parent.add_parser(command["label"], **kwargs)
            # add an invisible dispatch option so we can figure out what to
            # call later in self._dispatch
            default_contr_func = "%s.%s" % (
                command["controller"]._meta.label,
                command["func_name"],
            )
            command_parser.add_argument(
                self._dispatch_option,
                action="store",
                default=default_contr_func,
                help=SUPPRESS,
                dest="__dispatch__",
            )

            # add additional arguments to the sub-command namespace
            # self.app.log.debug("processing arguments for '%s' " % command['label'] + "command namespace")
            for arg, kw in command["arguments"]:
                # self.app.log.debug('adding argument (args=%s, kwargs=%s)' % (arg, kw))
                command_parser.add_argument(*arg, **kw)

    def _dispatch(self):
        self.app.log.info("########### PRE COMMAND ########### - start")
        start = time()

        self.app.log.debug("controller dispatch passed off to %s" % self)
        self._setup_controllers()
        self._setup_parsers()

        ctrl_idx = {c._meta.label: c for c in self._controllers}

        pre_params = argv[1:]
        controller = None
        if len(pre_params) > 0:
            pre_param = pre_params[0].replace("-", "_")
            controller = ctrl_idx.get(pre_param, None)
            for pre_param in pre_params[1:]:
                pre_param = pre_param.replace("-", "_")
                next_controller = ctrl_idx.get(pre_param, None)
                if next_controller is None:
                    break
                controller = next_controller

        if controller is not None:
            self._controllers = [controller]

        for contr in self._controllers:
            self._process_arguments(contr)
            self._process_commands(contr)

        for contr in self._controllers:
            contr._pre_argument_parsing()

        self.app._parse_args()

        for contr in self._controllers:
            contr._post_argument_parsing()
            contr._process_parsed_arguments()

        elapsed = round(time() - start, 3)
        self.app.log.info("########### PRE COMMAND ########### - stop [%s]" % elapsed)
        start2 = time()
        self.app.log.info("########### COMMAND ########### - start")

        if hasattr(self.app.pargs, "__dispatch__"):
            # if __dispatch__ is set that means that we have hit a sub-command
            # of a controller.
            contr_label = self.app.pargs.__dispatch__.split(".")[0]
            func_name = self.app.pargs.__dispatch__.split(".")[1]
        else:
            # if no __dispatch__ is set then that means we have hit a
            # controller with not sub-command (argparse doesn't support
            # default sub-command yet... so we rely on
            # __controller_namespace__ and it's default func

            # We never get here on Python < 3 as Argparse would have already
            # complained about too few arguments
            contr_label = self.app.pargs.__controller_namespace__
            contr = self._controllers_map[contr_label]
            func_name = _clean_func(contr._meta.default_func)

        if contr_label == "base":
            contr = self
        else:
            contr = self._controllers_map[contr_label]

        if func_name is None:
            pass  # pragma: nocover
        elif hasattr(contr, func_name):
            res = self._cmd(contr, func_name)
            elapsed = round(time() - start, 3)
            elapsed2 = round(time() - start2, 3)
            if getattr(self.app.pargs, "time", False):
                print("\nexecution time [s]: %s" % elapsed)

            self.app.log.info("########### COMMAND ########### - stop [%s]" % elapsed2)
            return res
        else:
            # only time that we'd get here is if Controller.Meta.default_func
            # is pointing to something that doesn't exist
            #
            # We never get here on Python < 3 as Argparse would have already
            # complained about too few arguments
            raise FrameworkError(  # pragma: nocover
                "Controller function does not exist %s.%s()" % (contr.__class__.__name__, func_name)
            )  # pragma: nocover

    def pre_command_run(self):
        """Use to run post parsing action for only the command and not all the controller"""
        pass

    def c(self, data, style, end="\n"):
        fn = getattr(self.styler, style)
        print(fn(data), end=end)

    def color_error(self, val):
        exp = val.lower()
        if exp in ["error", "failure"]:
            val = self.app.colored_text.output(val, "RED")
        elif exp in ["active", "success", "running", "available"]:
            val = self.app.colored_text.output(val, "GREEN")
        elif exp in ["stopped"]:
            val = self.app.colored_text.output(val, "GRAY")
        elif exp in ["building"]:
            val = self.app.colored_text.output(val, "CYAN")
        elif exp in ["pending"]:
            val = self.app.colored_text.output(val, "BLUE")
        return val

    def color_string(self, val, color):
        val = self.app.colored_text.output(val, color)
        return val

    def create_temp_file(self, data):
        fp = NamedTemporaryFile()
        fp.write(ensure_binary(data))
        fp.seek(0)
        return fp

    def close_temp_file(self, fp):
        fp.close()


class BaseController(CliController):
    api: CmpApiClient = None

    class Meta:
        # controller level arguments. ex: 'beehive --version'
        # arguments = BASE_ARGS

        cmp = {"baseuri": None, "subsystem": None}

    @property
    def baseuri(self):
        return self._meta.cmp.get("baseuri")

    def is_output_text(self):
        if self.format == "text":
            return True
        return False

    def is_output_dynamic(self):
        if self.format == "dynamic":
            return True
        return False

    def pre_command_run(self):
        self.env = getattr(self.app.pargs, "env", None)
        self.format = getattr(self.app.pargs, "format", None)
        self.key = getattr(self.app.pargs, "key", None)
        self.curl = getattr(self.app.pargs, "curl", None)

        if self.env is None:
            self.env = self.app.env
        else:
            self.app.env = self.env
        if self.key is None:
            self.key = self.app.key
        else:
            self.app.key = self.key
        if self.curl is None:
            self.curl = self.app.curl
        else:
            self.app.curl = self.curl

        # set output hanlder
        if self.format == "json":
            self.app.output = self.app._resolve_handler("output", "json_output_handler", raise_error=False)
        elif self.format == "yaml":
            self.app.output = self.app._resolve_handler("output", "yaml_output_handler", raise_error=False)
        elif self.format == "text":
            self.app.output = self.app._resolve_handler("output", "tabular_output_handler", raise_error=False)
        elif self.format == "dynamic":
            self.app.output = self.app._resolve_handler("output", "dynamic_output_handler", raise_error=False)

    def format_paginated_query(self, params, mappings=None, aliases=None):
        params.extend(["page", "size", "field", "order"])
        return self.format_query(params, mappings, aliases)

    def format_query(self, params, mappings=None, aliases=None):
        if mappings is None:
            mappings = {}
        if aliases is None:
            aliases = {}
        data = {}
        for item in params:
            mapping = mappings.get(item, None)
            value = getattr(self.app.pargs, item, None)
            if value is not None:
                if mapping is not None:
                    value = mapping(value)
                item = aliases.get(item, item)
                data[item] = value
        data = urlencode(data, doseq=True)
        self.app.log.info("query data: %s" % data)
        return data

    def add_field_from_pargs_to_data(self, field_name, data, data_key, reject_value=None, format=None):
        """add field to data dict used in post, put and delete api request

        :param field_name: command line field name
        :param data: data to update
        :param data_key: data key to use when update data
        :param reject_value: value not admitted
        :param format: custom format function to apply to value
        :return:
        """
        field_value = getattr(self.app.pargs, field_name)
        if field_value != reject_value:
            if format is not None:
                field_value = format(field_value)
            data[data_key] = field_value
        return data

    def configure_cmp_api_client(self):
        if self._meta.cmp.get("baseuri") is None or self._meta.cmp.get("subsystem") is None:
            raise CliManagerError("baseuri and subsystem must be defined if you want to connect to cmp api")
        self.api = CmpApiClient(
            self.app,
            self._meta.cmp.get("subsystem"),
            self._meta.cmp.get("baseuri"),
            self.key,
        )

    def __wait_task(self, res, task_timeout, delta, task_key=None):
        if isinstance(res, dict):
            jobid = res.get("jobid", None)
            if jobid is not None:
                self.api.wait_job(jobid, maxtime=task_timeout, delta=delta)
            taskid = res.get("taskid", None)
            if taskid is not None:
                self.api.wait_task(taskid, maxtime=task_timeout, delta=delta)
            taskid = res.get("nvl_TaskId", None)
            if taskid is not None:
                self.api.wait_task(taskid, maxtime=task_timeout, delta=delta)
            taskid = dict_get(res, "%s.nvl-activeTask" % task_key)
            if taskid is not None:
                self.api.wait_task(taskid, maxtime=task_timeout, delta=delta)

    def cmp_get(self, uri, data="", headers=None, timeout=240):
        res = self.api.call(uri, "GET", data=data, headers=headers, timeout=timeout)
        return res

    def cmp_post(
        self,
        uri,
        data="",
        headers=None,
        timeout=120,
        task_timeout=600,
        delta=2,
        task_key=None,
    ):
        res = self.api.call(uri, "POST", data=data, headers=headers, timeout=timeout)
        self.__wait_task(res, task_timeout, delta, task_key)
        return res

    def cmp_put(
        self,
        uri,
        data="",
        headers=None,
        timeout=120,
        task_timeout=600,
        delta=2,
        task_key=None,
    ):
        res = self.api.call(uri, "PUT", data=data, headers=headers, timeout=timeout)
        self.__wait_task(res, task_timeout, delta, task_key)
        return res

    def cmp_patch(
        self,
        uri,
        data="",
        headers=None,
        timeout=120,
        task_timeout=600,
        delta=2,
        task_key=None,
    ):
        res = self.api.call(uri, "PATCH", data=data, headers=headers, timeout=timeout)
        self.__wait_task(res, task_timeout, delta, task_key)
        return res

    def cmp_delete(
        self,
        uri,
        data="",
        headers=None,
        timeout=120,
        confirm=True,
        entity="",
        task_timeout=600,
        delta=2,
        output=True,
        task_key=None,
    ):
        assumeyes = getattr(self.app.pargs, "assumeyes", False)
        if assumeyes is True:
            confirm = False
        if confirm is True:
            msg = self.app.colored_text.yellow("You are about to delete %s. Are you sure [y/n]? " % entity)
            i = input(msg)
        else:
            i = "y"
        if i == "y":
            res = self.api.call(uri, "DELETE", data=data, headers=headers, timeout=timeout)
            self.__wait_task(res, task_timeout, delta, task_key)
            if output is True:
                print("%s deleted" % entity)
            return res
        return None

    @classmethod
    def load_file(cls, file_config):
        config = read_file(file_config)
        return config

    def cmp_request_v2(
        self,
        method,
        uri,
        headers=None,
        data="",
        ask_for_confirmation=True,  # better safe than sorry
        entity="",
        action=None,
        request_timeout=120,
        task_timeout: int = CmpUtils.DEFAULT_TASK_TIMEOUT,
        task_key_path: List[str] = None,
        task_key: str = None,
        output=True,
    ):
        """
        ask for prompt if assumeyes False.
        Then perform api call, and if necessary wait for task result.
        Optionally print message.
        """
        if action is None:
            action = method

        task_keys = CmpUtils.DEFAULT_TASK_KEYS
        if task_key:
            task_keys.add(task_key)

        assumeyes = getattr(self.app.pargs, "assumeyes", False)
        if assumeyes:
            ask_for_confirmation = False

        if ask_for_confirmation:
            choice = self._ct.prompt_choice(prompt_msg=f"You are about to {action} {entity}. Are you sure?")
        else:
            choice = "y"

        res = None
        if choice and choice == "y":
            res = self.api.call(uri, method=method, data=data, headers=headers, timeout=request_timeout)
            if res:
                task_id = CmpUtils.get_task_id_from(res, task_key_path, task_keys)
                if task_id:
                    self.api.wait_task_v2(task_id, maxtime=task_timeout)
                if output is True:
                    self.app.colored_text.green(f"{action} {entity} success.")
            return res
        else:
            exit()
