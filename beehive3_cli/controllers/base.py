# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from base64 import urlsafe_b64decode
from cement import ex

from beecell.crypto_util.fernet import Fernet
from beecell.password import random_password
from beecell.util import ensure_binary, ensure_text
from beecell.types.type_string import str2bool

from beehive3_cli.core.controller import CliController
from beehive3_cli.core.util import list_environments, load_environment_config
from beehive3_cli.core.version import get_version, get_changelog
from beehive3_cli.beenv import set_beenv, reset_env, print_env, unset_beenv
from beehive3_cli.translate import _

VERSION_BANNER = f"""
Beehive3 Console {get_version()}
Copyright (c) 2019-2025 CSI Piemonte
"""


class Base(CliController):
    class Meta: # type: ignore
        label = "base"

        # text displayed at the top of --help output
        description = _("Beehive Console")

        epilog = VERSION_BANNER

        arguments = []

    def _default(self):
        """Default action if no sub-command is passed."""
        self.app.args.print_help()

    @ex(
        help=_("show changelog"),
        description=_("show changelog"),
        arguments=[
            (["-a", "--all"], {"action": "store_true", "dest": "all", "help": _("Show all content")}),
        ],
    )
    def changelog(self):
        all_items = getattr(self.app.pargs, "all", False)
        print(get_changelog(all_items=all_items))

    @ex(
        help=_("merry Nivola"),
        description=_("show merry Nivola"),
        arguments=[],
        hide=True,
    )
    def merry(self):
        from beehive3_cli.snow import merry

        merry()

    @ex(
        help=_("ask command"),
        description=_("search command"),
        arguments=[
            # (
            #     ["command"],
            #     {"help": _("command to search"), "action": "store", "type": str},
            # ),
            (
                ["-eq"],
                {"help": _("search equal command"), "action": "store_true", "dest": "eq"},
            ),
            (
                ["-noparam"],
                {"help": _("search only commands"), "action": "store_true", "dest": "noparam"},
            ),
            (
                ["-a"],
                {"help": _("command to search"), "action": "store", "type": str},
            ),
            (["commands"], {"action": 'store', "nargs": '*'}),
        ],
    )
    def ask(self):
        command_to_search = None
        # command_to_search = self.app.pargs.command
        # print("command_to_search %s" % command_to_search)
        # self.app.log.warning("aaa command_to_search %s", command_to_search)

        query = getattr(self.app.pargs, "a", None)
        #self.app.log.debug("aaa query %s", query)

        commands = getattr(self.app.pargs, "commands", None)
        #self.app.log.debug("aaa commands %s", commands)

        #self.app.log.debug("aaa self.app.pargs %s", %self.app.pargs)

        #ctrl_idx = {}
        fathers = {}
        sep = " "

        eq = True
        if getattr(self.app.pargs, "eq", False) is False:
            eq = False

        noparam = True
        if getattr(self.app.pargs, "noparam", False) is False:
            noparam = False

        command_to_search = query
        if command_to_search is None and len(commands) > 0: # type: ignore
            command_to_search = commands[0] # type: ignore

        results = []

        if command_to_search is None:
            print("specify command to search: [-a] command")
        else:
            for c in self._controllers:
                from cement.core.meta import Meta

                meta: Meta = c._meta
                parent = meta.stacked_on.replace("_", "-")
                label: str = meta.label.replace("_", "-")
                #description = meta.description
                # arguments = meta.arguments # empty list

                # print('label: %s - controller: %s - parent: %s ' % (label, c, parent))
                fathers[label] = parent

                if (eq and label == command_to_search != -1) or (eq is False and label.find(command_to_search) != -1):
                    output = ""
                    father = fathers[parent]
                    if father != "base":
                        output += father + sep

                    if parent != "base":
                        output += parent + sep

                    output += label + sep
                    results.append(f"{output}...")

                commands = c._collect_commands()

                # set child commands
                for command in commands:
                    if isinstance(command, dict):
                        command_label = command["label"]
                        command_arguments = command["arguments"]
                        parser_options = command["parser_options"]
                    else:
                        command_label = command.label
                        command_arguments = command.arguments
                        parser_options = command.parser_options

                    output = ""
                    father = fathers[parent]
                    if father != "base":
                        output += father + sep

                    if parent != "base":
                        output += parent + sep

                    output += label + sep

                    if (eq and command_label == command_to_search != -1) or (
                        eq is False and command_label.find(command_to_search) != -1
                    ):
                        results.append(f"{output}{command_label}")

                    if not noparam:
                        for command_argument in command_arguments:
                            args_sintassi = command_argument[0]
                            # print("args_sintassi: %s" % args_sintassi)

                            sintassi: str = ""
                            for arg_sintassi in args_sintassi:
                                sintassi = sintassi + ", " + arg_sintassi
                            if len(sintassi) > 0:
                                sintassi = sintassi[2::]
                            # print("sintassi: %s" % sintassi)

                            if (eq and sintassi == command_to_search != -1) or (
                                eq is False and sintassi.find(command_to_search) != -1
                            ):
                                results.append(f"{output}{command_label} (param {sintassi})")

                # grandfather = parent

            results.sort()
            for result in results:
                print(result)

    @ex(
        help=_("tree command"),
        description=_("tree command"),
        arguments=[
            (
                ["-f"],
                {
                    "action": "store",
                    "dest": "format",
                    "help": _("Output format: json, html"),
                    "default": "text",
                },
            ),
            (["commands"], {"action": 'store', "nargs": '*'}),
        ],
    )
    def tree(self):
        fathers = {}
        sep = "!"  # char before "-" in ascii chars
        deep = 0

        array_path = []
        array_path.clear()

        for c in self._controllers:
            deep = 0
            from cement.core.meta import Meta

            meta: Meta = c._meta
            controller_parent = meta.stacked_on.replace("_", "-")
            controller_label: str = meta.label.replace("_", "-")
            #controller_description = meta.description
            controller_help = meta.help
            # arguments = meta.arguments # empty list

            # print('label: %s - controller: %s - parent: %s ' % (controller_label, c, controller_parent))
            fathers[controller_label] = controller_parent

            # set child commands
            b_parent = False
            commands = c._collect_commands()

            if len(commands) == 0:
                if controller_parent == "base":
                    path_obj = {
                        "key": sep + controller_label,
                        "array_command": [controller_label],
                        "deep": 1,
                        "type": "folder",
                        "help": controller_help,
                    }
                    array_path.append(path_obj)

            for command in commands:
                if isinstance(command, dict):
                    command_label = command["label"]
                    command_arguments = command["arguments"]
                    parser_options = command["parser_options"]
                else:
                    command_label = command.label
                    command_arguments = command.arguments
                    parser_options = command.parser_options

                deep = deep + 1
                # print("command: %s" % command)
                # command_label: str = command["label"]
                # command_arguments: str = command["arguments"]

                # parser_options: str = command["parser_options"]
                command_help: str = parser_options["help"]
                # command_description: str = parser_options["description"]

                array_command = []
                array_key = []

                father = fathers[controller_parent]

                # if controller_parent != "bu" and father != "bu":
                #     break

                if father != "base":
                    array_command.append(father)
                    array_key.append(father)

                if controller_parent != "base":
                    array_command.append(controller_parent)
                    array_key.append(controller_parent)

                if controller_label != "base":
                    array_command.append(controller_label)
                    array_key.append(controller_label)
                # print('{:>15}{:<20}'.format("", label))

                if not b_parent and len(array_command) > 0:
                    # add folder in tree
                    b_parent = True

                    path_key = ""
                    array_folder = []
                    for path in array_command:
                        # print(path)
                        path_key = path_key + sep + path
                        array_folder.append(path)
                    # print(path_key)

                    key = path_key

                    path_obj = {
                        "key": key,
                        "array_command": array_folder,
                        "deep": len(array_folder),
                        "type": "folder",
                        "help": controller_help,
                    }
                    array_path.append(path_obj)

                array_command.append(command_label)
                array_key.append("aaa" + command_label)  # for sort
                # print('{:>20}{:<20}'.format("", command_label))

                path_key = ""
                if controller_label == "base":
                    # for sort
                    path_key = "!aaa"

                for path in array_key:
                    # print(path)
                    path_key = path_key + sep + path
                # print(path_key)

                command_args = []
                for command_argument in command_arguments:
                    args_sintassi = command_argument[0]
                    # print("args_sintassi: %s" % args_sintassi)

                    sintassi: str = ""
                    for arg_sintassi in args_sintassi:
                        sintassi = sintassi + ", " + arg_sintassi
                    if len(sintassi) > 0:
                        sintassi = sintassi[2::]
                    # print("sintassi: %s" % sintassi)

                    arg_obj = command_argument[1]
                    # print("arg_obj: %s" % arg_obj)
                    if "help" in arg_obj:
                        arg_help = arg_obj["help"]
                        argument = {"sintassi": sintassi, "args_sintassi": args_sintassi, "help": arg_help}
                        command_args.append(argument)

                path_obj = {
                    "key": path_key,
                    "array_command": array_command,
                    "deep": len(array_command),
                    "type": "command",
                    "help": command_help,
                    "command_arguments": command_args,
                }
                array_path.append(path_obj)

        array_path.sort(key=lambda x: x.get("key"))
        # print(array_path)
        # for path in array_path:
        #     print(path)

        self.format = getattr(self.app.pargs, "format", None)
        if self.format == "json":
            self.app.output = self.app._resolve_handler("output", "json_output_handler", raise_error=False) # type: ignore
            self.app.render(array_path)

        elif self.format == "html":
            # from ujson import dumps
            # json_path = dumps(array_path, indent=2)

            # from json2html import json2html
            # html = json2html.convert(json = json_path)
            # print(html)

            from jinja2 import Environment

            environment = Environment()

            # open text file in read mode
            import os

            dirname = os.path.dirname(__file__)

            with open(f"{dirname}/templates/tree_command.html", "r", encoding="utf-8") as text_file:
                data_template = text_file.read()

            results_filename = "BeehiveCLI.html"
            results_template = environment.from_string(data_template)

            context = {
                "array_path": array_path,
            }

            with open(results_filename, mode="w", encoding="utf-8") as results:
                s = results_template.render(context)
                results.write(s)
                print(f"...wrote {results_filename}")

        else:
            prev = []
            for path in array_path:
                # print(path.get("key"))
                l_type = path.get("type")
                if l_type == "command":
                    index_array = 0
                    for array_command in path.get("array_command"):
                        b_print = True
                        if len(prev) > index_array:
                            if prev[index_array] == array_command:
                                b_print = False
                            else:
                                prev[index_array] = array_command
                        else:
                            prev.append(array_command)

                        if b_print:
                            if index_array == 1:
                                print("")

                            l_format = "{:>%s}{:<20}" % (index_array * 5)
                            print(l_format.format("", array_command))

                        index_array = index_array + 1

    @ex(
        help=_("get bash completion script"),
        description=_("get bash completion script"),
        arguments=[],
    )
    def bash_completion(self):
        from cement.core.meta import Meta
        ctrl_idx = {}
        for c in self._controllers:
            meta: Meta = c._meta
            parent = meta.stacked_on.replace("_", "-")
            label = meta.label.replace("_", "-")

            # set child sections
            try:
                ctrl_idx[parent].append(label)
            except:
                ctrl_idx[parent] = [label]
            commands = c._collect_commands()

            # set child commands_
            for command in commands:
                if isinstance(command, dict):
                    command_label = command["label"]
                    command_hide = command["hide"]
                    command_arguments = command.get("arguments", [])
                else:
                    command_label = command.label
                    command_hide = command.hide
                    command_arguments = command.arguments

                if command_hide is True:
                    # print("command_label: %s" % command_label)
                    continue

                try:
                    ctrl_idx[label].append(command_label)
                except:
                    ctrl_idx[label] = [command_label]

                # set command arguments
                for argument in command_arguments:
                    action = argument[1].get("action", None)
                    try:
                        for a in argument[0]:
                            if a[0] != "-":
                                pass
                                # a = '%s..' % a
                            elif action == "store":
                                a = f"{a}"
                                ctrl_idx[label + ":" + command_label].append(a)
                            else:
                                ctrl_idx[label + ":" + command_label].append(a)
                    except:
                        ctrl_idx[label + ":" + command_label] = []
                        for a in argument[0]:
                            if a[0] != "-":
                                pass
                                # a = '%s..' % a
                            elif action == "store":
                                a = f"{a}"
                                ctrl_idx[label + ":" + command_label].append(a)
                            else:
                                ctrl_idx[label + ":" + command_label].append(a)

        script = []
        for k, v in ctrl_idx.items():
            script.append(f"CMDS[{k}]='{' '.join(v)}'")

        print("\n".join(script))

    @ex(
        help=_("get bash completion envs"),
        description=_("get bash completion envs"),
        arguments=[],
    )
    def bash_completion_envs(self):
        envs = list_environments(self.app)
        print(" ".join(envs))

    @ex(
        help=_("list available environments"),
        description=_("list available environments"),
        arguments=[
            (
                ["-maxcolwidth"],
                {
                    "help": _("max column width. default=50"),
                    "action": "store",
                    "type": int,
                    "default": 50,
                },
            ),
            (
                ["-current"],
                {
                    "help": _("show only current environment"),
                    "action": "store_true",
                },
            ),
        ],
    )
    def envs(self):
        envs = list_environments(self.app)
        default_env = self.app.config.get("beehive", "default_env")
        current_env = self.app.env

        max_col_width = self.app.pargs.maxcolwidth
        show_only_current = self.app.pargs.current

        orch_info = {}
        res = []
        headers = ["name", "version", "current", "is_default", "has_cmp"]
        for env in envs:
            if show_only_current and env != current_env:
                continue
            try:
                value = load_environment_config(self.app, env)
                version = value.get("version", None)
                if env == "default":
                    continue
                item = {
                    "name": env,
                    "version": version,
                    "current": False,
                    "is_default": False,
                    "has_cmp": False,
                }
                if env == default_env:
                    item["is_default"] = True
                if env == current_env:
                    item["current"] = True

                cmp = value.get("cmp", {})
                endpoints = cmp.get("endpoints", [])
                if len(cmp.get("endpoint", [])) > 0:  # old endpoint format
                    item["has_cmp"] = True
                elif len(endpoints) > 0:
                    item["has_cmp"] = ",".join(endpoints)

                orchestrators = value.get("orchestrators", {})
                if orchestrators and show_only_current:
                    for k in list(orchestrators.keys()):
                        orch_labels = ",".join(list(orchestrators.get(k, {})))
                        orch_info[k] = orch_labels

                res.append(item)
            except Exception as exc:
                self.app.log.warning("no correct config found for environment %s", env)
                self.app.log.error(exc, exc_info=True)

        self.app.render(res, headers=headers, maxsize=max_col_width)
        if show_only_current:
            print()
            self.app.render(orch_info, details=True)

    @ex(
        help=_("clear local configuration"),
        description=_("clear local configurtion in file under user home directory"),
        arguments=[],
    )
    def clear_config(self):
        """Truncate local configurtion in file under user home directory."""
        reset_env()

    @ex(
        help=_("print local configuration"),
        description=_("print local configuration"),
        arguments=[],
    )
    def get_config(self):
        """Print local confguration."""
        print_env()

    @ex(
        help=_("Set target environment in application configuration."),
        description=_(
            """Set target environment in application configuration.
            You can run like this:
            eval $(beehive set-env -e xxx)
            But your local configuration, if present, will overide environment variable
            - Hint: change variabile PS1 adding ':$NIVOLA_CLI_ENV$ '"""
        ),
        arguments=[
            (
                ["-e"],
                {
                    "help": _("env to set"),
                    "action": "store",
                    "dest": "env",
                    "type": str,
                    "default": None,
                },
            ),
            (
                ["--save", "-s"],
                {
                    "action": "store_true",
                    "dest": "save",
                    "help": _("save env in local configuration"),
                },
            ),
        ],
    )
    def set_env(self):
        env = self.app.pargs.env
        envs = list_environments(self.app)
        if env in envs:
            if getattr(self.app.pargs, "save", False) is True:
                set_beenv("NIVOLA_CLI_ENV", str(env).strip())
            else :
                unset_beenv("NIVOLA_CLI_ENV")
            print(f"export NIVOLA_CLI_ENV={env}")
        else:
            self.app.exit_code = 1
            print(_("Invalid environment. Must be on of ") + ", ".join(envs))

    @ex(
        help=_("run like this: eval $(beehive set-lang xx)"),
        description=_(
            """
            Set language in application configuration.
            You can run like this: eval $(beehive set-lang xx)
            but your local configuration, if present, will overide environment variable"""
        ),
        arguments=[
            (
                ["lang"],
                {
                    "help": _("lang to set: it/en"),
                    "action": "store",
                    "type": str,
                    "default": None,
                },
            ),
            (
                ["--save", "-s"],
                {
                    "action": "store_true",
                    "dest": "save",
                    "help": _("save env in local configuration"),
                },
            ),
        ],
    )
    def set_lang(self):
        lang = self.app.pargs.lang
        if lang not in ('it', 'en'):
            raise Exception(f"lang error: {lang}")
        if getattr(self.app.pargs, "save", False) is True:
            set_beenv("NIVOLA_CLI_LANG", lang)
        else:
            unset_beenv("NIVOLA_CLI_LANG")
        print(f"export NIVOLA_CLI_LANG={lang}")

    @ex(
        help=_("generate password"),
        description=_("generate password"),
        arguments=[
            (
                ["-length"],
                {
                    "help": _("password length"),
                    "action": "store",
                    "type": str,
                    "default": 12,
                },
            ),
            (
                ["-strong"],
                {
                    "help": _("password strong"),
                    "action": "store",
                    "type": str,
                    "default": "true",
                },
            ),
        ],
    )
    def gen_password(self):
        length = self.app.pargs.length
        strong = str2bool(self.app.pargs.strong)
        pwd = random_password(length=int(length), strong=strong)
        self.app.render({"pwd": pwd}, headers=["pwd"], maxsize=500)

    @ex(
        help=_("generate fernet key for symmetric encryption"),
        description=_("generate fernet key for symmetric encryption"),
        arguments=[],
    )
    def gen_key(self):
        """Generate fernet key for symmetric encryption"""
        key = Fernet.generate_key()
        self.app.render({"key": key}, headers=["key"])

    @ex(
        help=_("dev: encrypt data with symmetric encryption"),
        description=_("encrypt data with symmetric encryption"),
        arguments=[
            (["data"], {"help": _("data to encrypt"), "action": "store", "type": str}),
            (
                ["key"],
                {
                    "action": "store",
                    "help": _("secret key to use for encryption/decryption"),
                },
            ),
        ],
        hide=True,
    )
    def encrypt(self):
        # self.check_secret_key()
        data = self.app.pargs.data
        # see API_FERNET_KEY in k8s files
        key = self.app.pargs.key
        key = urlsafe_b64decode(key)
        cipher_suite = Fernet(key)
        cipher_text = cipher_suite.encrypt(ensure_binary(data))
        res = [{"encrypt_data": f"$BEEHIVE_VAULT;AES128 | {ensure_text(cipher_text)}"}]
        self.app.render(res, headers=["encrypt_data"], maxsize=400)

    @ex(
        help=_("dev: decrypt quoted data with symmetric encryption"),
        description=_("decrypt quoted data with symmetric encryption"),
        arguments=[
            (["data"], {"help": _("data to decrypt"), "action": "store", "type": str}),
            (
                ["key"],
                {
                    "action": "store",
                    "help": _("secret key to use for encryption/decryption"),
                },
            ),
        ],
        hide=True,
    )
    def decrypt(self):
        from beecell.crypto import decrypt_data

        # self.check_secret_key()
        data = self.app.pargs.data
        # see API_FERNET_KEY in k8s files
        key = self.app.pargs.key
        key = urlsafe_b64decode(key)
        cipher_suite = Fernet(key)
        cipher_text = cipher_suite.decrypt(ensure_binary(data))
        self.app.render({"decrypt_data": cipher_text}, headers=["decrypt_data"], maxsize=200)
        testp = decrypt_data(key, data)
        print("beecel   :", testp)

    @ex(
        help=_("dev: test dev user"),
        description=_("test dev user"),
        arguments=[],
        hide=True,
    )
    def amidev(self):
        print("Hey dude, you are a dev user!")
