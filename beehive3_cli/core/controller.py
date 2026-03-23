# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from __future__ import annotations
import os
import sys
from argparse import Action, SUPPRESS
from pprint import PrettyPrinter
from tempfile import NamedTemporaryFile
from time import time
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING, Union
from urllib.parse import urlencode
from cement import Controller, FrameworkError
from cement.ext.ext_argparse import _clean_func

from beecell.file import read_file
from beecell.types.type_dict import dict_get, dict_set
from beecell.types.type_list import merge_list
from beecell.util import ensure_binary
from beehive3_cli.core.argument import CliHelpFormatter
from beehive3_cli.core.cmp_api_client import CmpApiClient
from beehive3_cli.core.exc import CliManagerError
from beehive3_cli.core.util import CmpUtils, ColoredText
from beehive3_cli.translate import _

if TYPE_CHECKING:
    from beehive3_cli.main import CliManager

BASE_ARGS = [
    (["--dry-run"], {"action": "store_true", "dest": "dryrun", "help": _("simulate without calling cmp")}),
    (["-y"], {"action": "store_true", "dest": "assumeyes", "help": _("Assume yes")}),
    (
        ["-e", "--env"],
        {
            "action": "store",
            "dest": "env",
            "help": _("Execution environment"),
            "default": None,
        },
    ),
    (
        ["-f"],
        {
            "action": "store",
            "dest": "format",
            "help": _("Output format: text, json, colortext, yaml"),
            "default": None,
        },
    ),
    (
        ["-k", "--key"],
        {
            "action": "store",
            "dest": "key",
            "help": _("Secret key file to use for encryption/decryption"),
            "default": None,
        },
    ),
    (
        ["--vault"],
        {
            "action": "store",
            "dest": "vault",
            "help": _("Ansible vault password to use for inventory decryption"),
            "default": None,
        },
    ),
    # (['--time'], {'action': 'store_true', 'dest': 'time', 'help': 'Print command execution time'}),
    (
        ["--notruncate"],
        {
            "action": "store_true",
            "dest": "notruncate",
            "help": _("Disable truncate of output"),
        },
    ),
    (
        ["--curl"],
        {
            "action": "store_true",
            "dest": "curl",
            "help": _("Print api request as curl command in console log"),
        },
    ),
    (
        ["--raw-response"],
        {
            "action": "store_true",
            "dest": "raw_response",
            "help": _("Print api response"),
        },
    ),
    (
        ["--fake-response"], 
        {
            "action": "store_true", 
            "dest": "fake_response", 
            "help": _("call cmp, check params but no action is made, response is fake")
        }
    ),
]


PAGINATION_ARGS = [
    (
        ["-size"],
        {
            "help": _("list page size [default=20]"),
            "action": "store",
            "type": int,
            "default": 20,
        },
    ),
    (
        ["-page"],
        {"help": _("list page [default=0]"), "action": "store", "type": int, "default": 0},
    ),
    (
        ["-field"],
        {
            "help": _("list sort field [default=id]"),
            "action": "store",
            "type": str,
            "default": "id",
        },
    ),
    (
        ["-order"],
        {
            "help": _("list sort order [default=DESC]"),
            "action": "store",
            "type": str,
            "default": "DESC",
        },
    ),
]


def ARGS(*list_args) -> list:
    res = merge_list(BASE_ARGS, *list_args)
    return res


def PARGS(*list_args) -> list:
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, *list_args)
    return res


class StringAction(Action):
    def __init__(self, option_strings, dest, **kwargs):
        kwargs["nargs"] = "+"
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        values = map(lambda x: x.replace("/", ""), values) # type: ignore
        setattr(namespace, self.dest, " ".join(values))


class CliController(Controller):
    app: 'CliManager'

    _ct: ColoredText = None  # a ColoredText singleton

    class Meta: # type: ignore
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
            # Pop platform; prevents sys.platform from being overwritten by
            # by a platform.py. This occurs on alpine cli
            # (hivetool/docker/cli/py-alpine.env)
            sys.modules.pop("platform", None)
            contr.pre_command_run()

        func = getattr(contr, func_name)
        # mem_usage()
        res = func()
        # mem_usage()
        return res

    def _process_commands(self, controller):
        label = controller._meta.label
        self.app.log.debug(f"processing commands for '{label}' controller namespace")

        commands = controller._collect_commands()
        for command in commands:
            kwargs = self._get_command_parser_options(command)
            # compatibility for cement 3.0.12 command are no more dict but ComandMeta instance
            if isinstance(command, dict):
                func_name = command["func_name"]
                label = command["label"]
                ctr_label = command["controller"]._meta.label
                cmd_args = command["arguments"]
            else:
                label = command.label
                func_name = command.func_name
                ctr_label = command.controller._meta.label
                cmd_args = command.arguments

            # self.app.log.debug("adding command '%s' " % command['label'] + "(controller=%s, func=%s)" %
            #                    (controller._meta.label, func_name))

            cmd_parent = self._get_parser_parent_by_controller(controller)

            # handle optional example parameter to show example after help message
            example = kwargs.pop("example", None)
            if example:
                epilog = kwargs.get("epilog", "")
                kwargs["epilog"] = _("Example: ") + example + "\n" + epilog

            command_parser = cmd_parent.add_parser(label, **kwargs)
            # add an invisible dispatch option so we can figure out what to
            # call later in self._dispatch
            default_contr_func = f"{ctr_label}.{func_name}"
            command_parser.add_argument(
                self._dispatch_option,
                action="store",
                default=default_contr_func,
                help=SUPPRESS,
                dest="__dispatch__",
            )

            # add additional arguments to the sub-command namespace
            # self.app.log.debug("processing arguments for '%s' " % command['label'] + "command namespace")
            for arg, kw in cmd_args:
                # self.app.log.debug('adding argument (args=%s, kwargs=%s)' % (arg, kw))
                command_parser.add_argument(*arg, **kw)

    def _dispatch(self):
        """dispatch the command to apropriate controller
        TODO  generate event for Audit log


        Raises:
            FrameworkError: _description_

        Returns:
            _type_: _description_
        """
        self.app.log.info("########### PRE COMMAND ########### - start")
        start = time()

        self.app.log.debug(f"controller dispatch passed off to {self}")
        self._setup_controllers()
        self._setup_parsers()


        ctrl_idx = {c._meta.label: c for c in self._controllers}

        pre_params = sys.argv[1:]
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
        self.app.log.info(f"########### PRE COMMAND ########### - stop [{elapsed}]")
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
            # self.app.log.info("+++++ contr: %s" % contr)
            # self.app.log.info("+++++ func_name: %s" % func_name)
            func = getattr(contr, func_name)
            # self.app.log.info("+++++ func: %s" % func)

            if hasattr(func, "__cement_meta__"):
                func_meta = func.__cement_meta__
                # self.app.log.info("+++++ func_meta: %s" % func_meta)
                if isinstance(func_meta, dict):
                    parser_options = func_meta["parser_options"]
                else:
                    parser_options = func_meta.parser_options
                help_str: str = parser_options["help"]
                if help_str.startswith("dev:"):
                    if not self.is_developer_user():
                        print(self.app.colored_text.output("ERROR: command for developers", "RED"))
                        sys.exit()

            res = self._cmd(contr, func_name)
            elapsed = round(time() - start, 3)
            elapsed2 = round(time() - start2, 3)
            if getattr(self.app.pargs, "time", False):
                print(f"\nexecution time [s]: {elapsed}")

            self.app.log.info(f"########### COMMAND ########### - stop [{elapsed2}]")
            return res
        else:
            # only time that we'd get here is if Controller.Meta.default_func
            # is pointing to something that doesn't exist
            #
            # We never get here on Python < 3 as Argparse would have already
            # complained about too few arguments
            raise FrameworkError(  # pragma: nocover
                f"Controller function does not exist {contr.__class__.__name__}.{func_name}()"
            )  # pragma: nocover
        return None

    def is_developer_user(self):
        user = os.environ.get("USER", None)  # console no docker es. USER=73338
        kubeconfig = os.environ.get("KUBECONFIG", None)  # in locale es. .../beehive-mgmt/configs/k8s/podto1
        beehive_user = os.environ.get("BEEHIVE_USER", None)  # docker CLI es. BEEHIVE_USER=73338

        dev_users = [
            "73338",  # Filippo
            "72386",  # Gianni
            "gianni",  # Gianni
            "2162",  # Davide
            "73852",  # Ale
            "74008",  # Pietro
            "70838",  # Paolo
        ]

        # print("user: %s" % user)
        # print("kubeconfig: %s" % kubeconfig)
        # print("beehive_user: %s" % beehive_user)

        is_dev = False
        if user is not None and user in dev_users:
            self.app.log.debug(f"user is dev: {user}")
            is_dev = True
        elif beehive_user is not None and beehive_user in dev_users:
            self.app.log.debug(f"beehive_user is dev: {beehive_user}")
            is_dev = True
        elif kubeconfig is not None and kubeconfig.find("/beehive-mgmt/configs/k8s/podto1") > 1:
            self.app.log.debug("kubeconfig is dev")
            is_dev = True

        return is_dev

    def pre_command_run(self):
        """Use to run post parsing action for only the command and not all the controller"""
        pass

    # TODO move these print output functions in base output handler to extend from, or abstract class
    def c(self, data, style, end="\n"):
        if self.app.config.get("beehive", "colored") is True:
            fn = getattr(self.styler, style)
            print(fn(data), end=end)
        else:
            print(str(data), end=end)

    def print_section_heading(self, heading_text: str, style="underline", start="\n", end="\n", dnt=False):
        """print section heading

        :param heading_text: string to print
        :type heading_text: str
        :param style: formatting to apply, defaults to "underline"
        :type style: str, optional
        :param start: heading text prefix, defaults to "\n"
        :type start: str, optional
        :param end: final newline or custom, defaults to "\n"
        :type end: str, optional
        :param dnt: do not translate, defaults to False
        if True will not attempt to translate text
        :type dnt: bool, optional
        """
        #if not dnt:
        #    heading_text = _(heading_text)
        self.c(f"{start}{heading_text}", style=style, end=end)

    def color_error(self, val):
        if self.app.config.get("beehive", "colored") is True and isinstance(val, str):
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
        if self.app.config.get("beehive", "colored") is True:
            val = self.app.colored_text.output(val, color)
        return val

    def create_temp_file(self, data):
        fp = NamedTemporaryFile()
        fp.write(ensure_binary(data))
        fp.seek(0)
        return fp

    def close_temp_file(self, fp):
        fp.close()

    def interactive_parameters(self, parameters: Dict[str, Union[str, None]]) -> Dict[str, str]:
        """get a parameters  value asking the user for values

        Args:
            parameters (Dict[str,str]): _description_

        Returns:
            Dict[str,str]: _description_
        """
        for param, value in parameters:
            parameters[param] = self.interactive_parameter(param, value)
        return parameters

    def interactive_parameter(self, parameter: str, default: Optional[str] = None) -> str:
        """get a parameter value asking the user for value

        Args:
            parameter (str): the parameter as miningful for the user
            default (str):  default value empty string by default

        Returns:
            str: the value
        """
        if default is None:
            resp = input(self.app.colored_text.yellow(f"{parameter} :"))
            return resp
        resp = input(self.app.colored_text.yellow(f"{parameter} [{default}]:"))
        if len(resp) > 0:
            return resp
        return default

    def confirm(self, msg: str, suffix: str = ". Are you sure [y/n]?", yes: str = "y") -> bool:
        """ask for confirm

        Args:
            msg (str): mesage to display

        Returns:
            bool: true if user confirmed
        """
        msg = self.app.colored_text.yellow(f"{msg}{suffix}")
        i = input(msg)[0].lower()
        return i == yes


class BaseController(CliController):
    api: CmpApiClient
    config_path: str
    aliases = None

    class Meta: # type: ignore
        # controller level arguments. ex: 'beehive --version'
        # arguments = BASE_ARGS

        cmp = {"baseuri": None, "subsystem": None}

    @property
    def baseuri(self):
        return self._meta.cmp.get("baseuri")

    def is_output_text(self):
        # print("+++++ is_output_text - self.format: %s" % self.format)
        if self.format in ('text', 'colortext'):
            return True
        return False

    def is_output_dynamic(self):
        if self.format == "dynamic":
            return True
        return False

    def pre_command_run(self):
        self.env: Optional[str] = getattr(self.app.pargs, "env", None)
        self.format: Optional[str] = getattr(self.app.pargs, "format", None)
        self.key: Optional[str] = getattr(self.app.pargs, "key", None)
        self.curl: Optional[bool] = getattr(self.app.pargs, "curl", None)

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

        force_no_color = False
        if not os.isatty(1):
            # stdout is being piped to. e.g. beehive... | grep ...
            # unless -f json or -f yaml, force "text" format
            force_no_color = True

        if self.format is None:
            self.format = self.app.format

        if self.format == "json":
            self.app.output = self.app._resolve_handler(
                "output", "json_output_handler", raise_error=False
            ) # type: ignore
        elif self.format == "yaml":
            self.app.output = self.app._resolve_handler(
                "output", "yaml_output_handler", raise_error=False
            ) # type: ignore
        elif self.format == "text" or force_no_color:
            self.app.output = self.app._resolve_handler(
                "output", "tabular_output_handler", raise_error=False
            ) # type: ignore
        elif self.format == "colortext":
            self.app.output = self.app._resolve_handler(
                "output", "tabular_color_output_handler", raise_error=False
            ) # type: ignore
        elif self.format == "dynamic":
            self.app.output = self.app._resolve_handler(
                "output", "dynamic_output_handler", raise_error=False
            ) # type: ignore
        else:
            raise Exception("Invalid format")

    def format_paginated_query(self, params: List, mappings=None, aliases=None) -> str:
        params.extend(["page", "size", "field", "order"])
        return self.format_query(params, mappings, aliases)

    def format_query(self, params: List, mappings=None, aliases=None) -> str:
        if mappings is None:
            mappings = {}
        if aliases is None:
            aliases = {}
        self.aliases = aliases

        data = {}
        for item in params:
            mapping = mappings.get(item, None)
            value = getattr(self.app.pargs, item, None)
            # print("item value %s - %s" % (item, value))
            if value is not None:
                if mapping is not None:
                    value = mapping(value)
                item = aliases.get(item, item)
                data[item] = value

        data = urlencode(data, doseq=True)
        self.app.log.info(f"query data: {data}")
        return data

    def interactive_add_field_from_pargs_to_data(
        self, field_name: str, data: Dict, data_key: str, default_value=None,
        reject_value=None, format: Optional[Callable]=None
    ) -> Dict:
        """Get a parameters from parsed argument and use as default prompt to interactive confirmation.

        Args:
            field_name (str): filde name in parsed arguments pargs
            data (dict): dictionary in which store values
            data_key (str): key name in data
            prompt (str, optional): prompt message. Defaults to None. inf NOne use data_key as  prompt
            default_value (any, optional): defult value Defaults to None.
            reject_value (_type_, optional): _description_. Defaults to None.
            format (_type_, optional): _description_. Defaults to None.

        Returns:
            dict: data dictionary in whch data_key has been set
        """
        field_value = getattr(self.app.pargs, field_name)
        if field_value == reject_value:
            if default_value is not None:
                field_value = default_value
            else:
                # Do not set if there is no value from parameter and no default value
                return data

        if format is not None:
            field_value = format(field_value)

        field_value = self.interactive_parameter(data_key, field_value)

        if format is not None:
            field_value = format(field_value)

        data[data_key] = field_value
        return data

    def add_field_from_pargs_to_data(
        self, field_name: str, data: Dict, data_key: str,
        reject_value=None, default_value=None, format: Optional[Callable]=None
    ) -> Dict:
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
        else:
            if default_value is not None:
                data[data_key] = default_value

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

    def __wait_task(self, res, task_timeout, delta, task_key=None, output=True):
        if isinstance(res, dict):
            jobid = res.get("jobid", None)
            if jobid is not None:
                msg = "The 'wait_job' method is not implemented by CmpApiClient for job ID."
                raise NotImplementedError(msg)
                #self.api.wait_job(jobid, maxtime=task_timeout, delta=delta)
            taskid = res.get("taskid", None)
            if taskid is not None:
                self.api.wait_task(taskid, maxtime=task_timeout, delta=delta, output=output)
            taskid = res.get("nvl_TaskId", None)
            if taskid is not None:
                self.api.wait_task(taskid, maxtime=task_timeout, delta=delta)
            taskid = dict_get(res, f"{task_key}.nvl-activeTask")
            if taskid is not None:
                self.api.wait_task(taskid, maxtime=task_timeout, delta=delta)

    def debug(self, s):
        # return
        if False:
            print(f"debug... {s}")

    def cmp_get(self, uri, data="", headers=None, timeout=240):
        res = self.api.call(uri, "GET", data=data, headers=headers, timeout=timeout)
        return res

    def cmp_get_pages(
        self,
        uri: str,
        data: Union[Dict, List, str]="",
        headers: Optional[Dict]=None,
        timeout=240,
        pagesize: int = 100,
        key_total_name: Optional[str] = None,
        key_list_name: Optional[str] = None,
        fn_render: Optional[Callable]=None,
    ):
        """calls cmp apis in a paginated transparent way, when needed

        :param uri: cmp service uri
        :type uri: str
        :param data: query string
        :type data: str, optional
        :param headers: headers, defaults to None
        :type headers: Dict, optional
        :param timeout: timeout, defaults to 240
        :type timeout: int, optional
        :param pagesize: page size, defaults to 100
        :type pagesize: int, optional
        :param key_total_name: the name of the dictionary key in the result dict
        containing the total number of elements, defaults to None
        :type key_total_name: Optional[str], optional
        :param key_list_name: the name of the dictionary key in the result dict
        containing the list of elements, defaults to None
        :type key_list_name: Optional[str], optional
        :param fn_render: function to call to render the data, defaults to None
        :type fn_render: Optional[Callable], optional
        :return: None in all cases except when fn_render is None and size is positive.
        In that case the result of the single call is returned.
        :rtype: Optional[Dict]
        """
        self.debug(f"self.app.pargs: {self.app.pargs}")
        self.debug(f"self.format: {self.format}")

        render_output = True
        if self.format not in ('text', 'colortext'):
            render_output = False
        if fn_render is None:
            render_output = False

        size = None
        if hasattr(self.app.pargs, "size"):
            size = getattr(self.app.pargs, "size")
            self.debug(f"size: {size}")
            if size < -2:
                pagesize = abs(size)

        if size is not None and size < -1:
            # if size is negative, "paginated mode" is triggered
            # i.e. divide big size call into several smaller calls
            param_size = "size"
            param_page = "page"
            self.debug(f"self.aliases: {self.aliases}")
            if self.aliases is not None:
                if "size" in self.aliases:
                    param_size = self.aliases["size"]
                if "page" in self.aliases:
                    param_page = self.aliases["page"]

            # self.debug(data)
            size_param = f"{param_size}={size}"
            if isinstance(data, str) and data.find(size_param) > 0:
                # size parameter was specified and it's negative

                self.debug("loop get pages")

                # negative size: convert to request with positive size i.e. -200 = 200
                data_step = data.replace(size_param, f"{param_size}={pagesize}")
                self.debug(f"data_step: {data_step}")

                # first call
                res: Dict[str, Any] = self.api.call(uri, "GET", data=data_step, headers=headers, timeout=timeout)
                self.debug(f"res first: {res}")

                # get total from first call
                total = None
                if key_total_name is not None:
                    total = dict_get(res, key_total_name)
                    self.debug(f"total: {total}")
                elif "total" in res:
                    total = res["total"]

                self.debug(f"total: {total}")
                if total is not None and isinstance(total, int):
                    # limit number of elements to obtain through paginated calls to MAX_RECORDS
                    max_records = 10000
                    if total > max_records:
                        self.app.error(f"total record > {max_records} - use filters")
                        return None

                    key_list: Optional[str] = None
                    data_key: List = []

                    # find key with results
                    if key_list_name is not None:
                        # if key provided, use the provided one
                        key_list = key_list_name

                        if render_output:
                            fn_render(self, res) # type: ignore

                            print("---")
                            print("")
                        else:
                            data_key += dict_get(res, key_list) # type: ignore
                    else:
                        # otherwise try to determine key by process of exclusion
                        self.debug(f"keys... {res.keys()}")
                        for key in res.keys():
                            if key not in ("count", "page", "total", "sort"):
                                # self.debug("key: %s" % key)
                                key_list = key
                                self.debug(f"key_list: {key_list}")

                                if render_output:
                                    fn_render(self, res) # type: ignore

                                    print("---")
                                    print("")
                                else:
                                    data_key += res[key]

                    # calculate number of pages
                    pages = total // pagesize
                    if total % pagesize > 0:
                        pages += 1
                    self.debug(f"pages: {pages}")

                    # paginated mode: call once per page
                    for page in range(1, pages):
                        data_step = data.replace(size_param, f"{param_size}={pagesize}").replace(
                            f"{param_page}=0", f"{param_page}={page}"
                        )
                        self.debug(data_step)
                        res = self.api.call(uri, "GET", data=data_step, headers=headers, timeout=timeout)
                        self.debug(f"page {page} - res: {res}")

                        if render_output:
                            fn_render(self, res, page=page) # type: ignore

                            print("---")
                            print("")
                        else:
                            data_key += dict_get(res, key_list) # type: ignore

                    if render_output:
                        return None

                    # if the render function wasn't given or the output format is json/yaml
                    # print everything accumulated at once as if only a single call had been made

                    # res[key_list] = data_key
                    dict_set(res, key_list, data_key) # type: ignore

                    res["count"] = len(data_key)
                    res["page"] = 0
                    # self.debug(res)
                    if fn_render is not None:
                        fn_render(self, res, page=0)
                    return None

        # default
        self.debug(f"default - data: {data}")
        res = self.api.call(uri, "GET", data=data, headers=headers, timeout=timeout)
        if fn_render:
            fn_render(self, res)
        else:
            return res
        return None

    def cmp_post(
        self,
        uri,
        data: Union[Dict, List, str]="",
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
        data: Union[Dict, List, str]="",
        headers=None,
        timeout=120,
        task_timeout=600,
        delta=2,
        task_key=None,
        output=True,
    ):
        res = self.api.call(uri, "PUT", data=data, headers=headers, timeout=timeout)
        self.__wait_task(res, task_timeout, delta, task_key, output)
        return res

    def cmp_patch(
        self,
        uri,
        data: Union[Dict, List, str]="",
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
        data: Union[Dict, List, str]="",
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
        if assumeyes is False:
            confirm = self.confirm(msg=f"You are about to delete {entity}")
        if confirm:
            res = self.api.call(uri, "DELETE", data=data, headers=headers, timeout=timeout)
            self.__wait_task(res, task_timeout, delta, task_key)
            if output is True:
                print(f"{entity} deleted")
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
        task_key_path: Optional[List[str]] = None,
        task_key: Optional[str] = None,
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
                    print(self.app.colored_text.green(f"{action} {entity} success."))
            return res
        sys.exit()
