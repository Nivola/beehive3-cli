# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from time import time


start = time()

from base64 import b64decode, b64encode
from six import ensure_binary, ensure_text, ensure_binary
from cryptography.fernet import Fernet
from cement import ex
from beecell.types.type_string import str2bool
from beecell.password import random_password
from beehive3_cli.core.controller import CliController
from beehive3_cli.core.util import list_environments, load_environment_config
from beehive3_cli.core.version import get_version

VERSION_BANNER = """
Beehive3 Console %s
Copyright (c) 2019-2023 CSI Piemonte
""" % (
    get_version()
)


class Base(CliController):
    class Meta:
        label = "base"

        # text displayed at the top of --help output
        description = "Beehive Console"

        # text displayed at the bottom of --help output
        epilog = "Usage: beehive command1 --foo bar"

        # controller level arguments. ex: 'beehive --version'
        arguments = [
            (["-v", "--version"], {"action": "version", "version": VERSION_BANNER}),
            (
                ["--time"],
                {
                    "action": "store_true",
                    "dest": "time",
                    "help": "Print command execution time",
                },
            ),
        ]

    def _default(self):
        """Default action if no sub-command is passed."""
        self.app.args.print_help()

    @ex(
        help="ask command",
        description="search command",
        arguments=[
            # (
            #     ["command"],
            #     {"help": "command to search", "action": "store", "type": str},
            # ),
            (
                ["-eq"],
                {"help": "search equal command", "action": "store_true", "dest": "eq"},
            ),
            (
                ["-a"],
                {"help": "command to search", "action": "store", "type": str},
            ),
            (["commands"], dict(action="store", nargs="*")),
        ],
    )
    def ask(self):
        command_to_search = None
        # command_to_search = self.app.pargs.command
        # print("command_to_search %s" % command_to_search)
        # self.app.log.warning("aaa command_to_search %s" % command_to_search)

        query = getattr(self.app.pargs, "a", None)
        self.app.log.debug("aaa query %s" % query)

        commands = getattr(self.app.pargs, "commands", None)
        self.app.log.debug("aaa commands %s" % commands)

        self.app.log.debug("aaa self.app.pargs %s" % self.app.pargs)

        ctrl_idx = {}
        fathers = {}
        # SEP = " -> "
        SEP = " "

        eq = True
        if getattr(self.app.pargs, "eq", False) is False:
            eq = False

        # if command_to_search is None:
        command_to_search = query
        if command_to_search is None and len(commands) > 0:
            command_to_search = commands[0]

        if command_to_search is None:
            print("specify command to search: [-a] command")
        else:
            if b64encode(ensure_binary(command_to_search)) == b"ZmlsaXBwbw==":
                print(b64decode(b"Li4uaGVyZSBJIGFtIQ==").decode("utf-8"))
            for c in self._controllers:
                from cement.core.meta import Meta

                meta: Meta = c._meta
                parent = c._meta.stacked_on.replace("_", "-")
                label: str = c._meta.label.replace("_", "-")
                description = c._meta.description
                # arguments = meta.arguments # empty list

                # print('label: %s - controller: %s - parent: %s ' % (label, c, parent))
                fathers[label] = parent

                if (eq and label == command_to_search != -1) or (eq is False and label.find(command_to_search) != -1):
                    output = ""
                    father = fathers[parent]
                    if father != "base":
                        output += father + SEP

                    if parent != "base":
                        output += parent + SEP

                    output += label + SEP
                    print("%s..." % (output))

                # print('{}'.format(c._meta))
                # for a in meta.__dict__.items():
                #     print(a)

                # set child sections
                # try:
                #     ctrl_idx[parent].append(label)
                # except:
                #     ctrl_idx[parent] = [label]
                commands = c._collect_commands()

                # set child commands
                for command in commands:
                    command_label: str = command["label"]

                    if (eq and command_label == command_to_search != -1) or (
                        eq is False and command_label.find(command_to_search) != -1
                    ):
                        output = ""
                        father = fathers[parent]
                        if father != "base":
                            output += father + SEP

                        if parent != "base":
                            output += parent + SEP

                        output += label + SEP
                        print("%s%s" % (output, command_label))

                        # for argument in command.get('arguments', []):
                        #     action = argument[1].get('action', None)
                        #     try:
                        #         for a in argument[0]:
                        #             if a[0] != '-':
                        #                 pass
                        #                 # a = '%s..' % a
                        #             elif action == 'store':
                        #                 a = '%s' % a
                        #             print(a)
                        #     except:
                        #         ctrl_idx[label+':'+command_label] = []
                        #         for a in argument[0]:
                        #             if a[0] != '-':
                        #                 pass
                        #                 # a = '%s..' % a
                        #             elif action == 'store':
                        #                 a = '%s' % a
                        #             print('except ' + a)

                # grandfather = parent

    @ex(
        help="tree command",
        description="tree command",
        arguments=[
            (
                ["-f"],
                {
                    "action": "store",
                    "dest": "format",
                    "help": "Output format: json, html",
                    "default": "text",
                },
            ),
            (["commands"], dict(action="store", nargs="*")),
        ],
    )
    def tree(self):
        command_to_search = None
        query = getattr(self.app.pargs, "a", None)
        # self.app.log.debug("aaa query %s" % query)

        commands = getattr(self.app.pargs, "commands", None)
        # self.app.log.debug("aaa commands %s" % commands)

        # self.app.log.debug("aaa self.app.pargs %s" % self.app.pargs)

        ctrl_idx = {}
        fathers = {}
        SEP = "!"  # char before "-" in ascii chars
        deep = 0

        # if command_to_search is None:
        command_to_search = query
        if command_to_search is None and len(commands) > 0:
            command_to_search = commands[0]

        array_path = []
        array_path.clear()

        for c in self._controllers:
            deep = 0
            from cement.core.meta import Meta

            meta: Meta = c._meta
            controller_parent = meta.stacked_on.replace("_", "-")
            controller_label: str = meta.label.replace("_", "-")
            controller_description = meta.description
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
                        "key": SEP + controller_label,
                        "array_command": [controller_label],
                        "deep": 1,
                        "type": "folder",
                        "help": controller_help,
                    }
                    array_path.append(path_obj)

            for command in commands:
                deep = deep + 1
                # print("command: %s" % command)
                command_label: str = command["label"]
                command_arguments: str = command["arguments"]

                parser_options: str = command["parser_options"]
                command_help: str = parser_options["help"]
                command_description: str = parser_options["description"]

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
                        path_key = path_key + SEP + path
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
                    path_key = path_key + SEP + path
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
            self.app.output = self.app._resolve_handler("output", "json_output_handler", raise_error=False)
            self.app.render(array_path)

        elif self.format == "html":
            # from ujson import dumps
            # json_path = dumps(array_path, indent=2)

            # from json2html import json2html
            # html = json2html.convert(json = json_path)
            # print(html)

            from jinja2 import Environment, FileSystemLoader

            environment = Environment()

            # open text file in read mode
            import os

            dirname = os.path.dirname(__file__)

            text_file = open(dirname + "/templates/tree_command.html", "r")
            data_template = text_file.read()
            text_file.close()

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
                type = path.get("type")
                if type == "command":
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

                            format = "{:>%s}{:<20}" % (index_array * 5)
                            print(format.format("", array_command))

                        index_array = index_array + 1

    @ex(
        help="get bash completion script",
        description="get bash completion script",
        arguments=[],
    )
    def bash_completion(self):
        ctrl_idx = {}
        for c in self._controllers:
            parent = c._meta.stacked_on.replace("_", "-")
            label = c._meta.label.replace("_", "-")

            # set child sections
            try:
                ctrl_idx[parent].append(label)
            except:
                ctrl_idx[parent] = [label]
            commands = c._collect_commands()

            # set child commands
            for command in commands:
                command_label = command["label"]

                try:
                    ctrl_idx[label].append(command_label)
                except:
                    ctrl_idx[label] = [command_label]

                # set command arguments
                for argument in command.get("arguments", []):
                    action = argument[1].get("action", None)
                    try:
                        for a in argument[0]:
                            if a[0] != "-":
                                pass
                                # a = '%s..' % a
                            elif action == "store":
                                a = "%s" % a
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
                                a = "%s" % a
                                ctrl_idx[label + ":" + command_label].append(a)
                            else:
                                ctrl_idx[label + ":" + command_label].append(a)

        script = []
        for k, v in ctrl_idx.items():
            script.append("CMDS[{key}]='{values}'".format(key=k, values=" ".join(v)))

        print("\n".join(script))

    @ex(
        help="get bash completion envs",
        description="get bash completion envs",
        arguments=[],
    )
    def bash_completion_envs(self):
        envs = list_environments(self.app)
        print(" ".join(envs))

    @ex(
        help="list available environments",
        description="list available environments",
        arguments=[
            (
                ["-maxcolwidth"],
                {
                    "help": "max column width. default=50",
                    "action": "store",
                    "type": int,
                    "default": 50,
                },
            ),
            (
                ["-multichunks"],
                {
                    "help": "split the output in chunks",
                    "action": "store",
                    "type": int,
                    "default": None,
                },
            ),
            (
                ["-current"],
                {
                    "help": "list only current environment",
                    "action": "store_true",
                },
            ),
            (
                ["-orchestrator_type_name"],
                {
                    "help": "Filter by orchestrator type name. e.g. zabbix",
                    "action": "store",
                    "type": str,
                    "default": None,
                },
            ),
        ],
    )
    def envs(self):
        envs = list_environments(self.app)
        defualt_env = self.app.config.get("beehive", "default_env")
        current_env = self.app.env

        chunk_size = self.app.pargs.multichunks
        max_col_width = self.app.pargs.maxcolwidth
        otn = self.app.pargs.orchestrator_type_name
        if otn:
            chunk_size = 1
            max_col_width = 100

        res = []
        headers = ["name", "version", "current", "is_default", "has_cmp"]
        headers_orch = []
        for env in envs:
            if self.app.pargs.current and env != current_env:
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
                    "|": "|",  # vertical divider
                }
                if env == defualt_env:
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
                for k in list(orchestrators.keys()):
                    if otn and otn != k:
                        continue
                    v = orchestrators.get(k, {})
                    if v is None:
                        v = {}
                    item[k] = ",".join(v.keys())
                    if k not in headers_orch:
                        headers_orch.append(k)

                res.append(item)
            except:
                self.app.log.warning("no correct config found for environment %s" % env)

        if chunk_size:
            headers_chunks = [headers_orch[i : i + chunk_size] for i in range(0, len(headers_orch), chunk_size)]
            for headers_i in headers_chunks:
                self.app.render(res, headers=headers + ["|"] + headers_i, maxsize=max_col_width)
                print("")  # empty line
        else:
            self.app.render(res, headers=headers + headers_orch, maxsize=max_col_width)

    @ex(
        help="generate password",
        description="generate password",
        arguments=[
            (
                ["-length"],
                {
                    "help": "password length",
                    "action": "store",
                    "type": str,
                    "default": 12,
                },
            ),
            (
                ["-strong"],
                {
                    "help": "password strong",
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
        help="generate fernet key for symmetric encryption",
        description="generate fernet key for symmetric encryption",
        arguments=[],
    )
    def gen_key(self):
        """Generate fernet key for symmetric encryption"""
        key = Fernet.generate_key()
        self.app.render({"key": key}, headers=["key"])

    @ex(
        help="encrypt data with symmetric encryption",
        description="encrypt data with symmetric encryption",
        arguments=[
            (["data"], {"help": "data to encrypt", "action": "store", "type": str}),
            (
                ["key"],
                {
                    "action": "store",
                    "help": "secret key to use for encryption/decryption",
                },
            ),
        ],
    )
    def encrypt(self):
        # self.check_secret_key()
        data = self.app.pargs.data
        # see API_FERNET_KEY in k8s files
        key = self.app.pargs.key

        # similar to
        # from beecell.simple import encrypt_data as simple_encrypt_data
        # res = simple_encrypt_data(key, data)

        key = ensure_binary(key)
        cipher_suite = Fernet(key)
        cipher_text = cipher_suite.encrypt(ensure_binary(data))
        res = [{"encrypt_data": "$BEEHIVE_VAULT;AES128 | %s" % ensure_text(cipher_text)}]
        self.app.render(res, headers=["encrypt_data"], maxsize=400)

    @ex(
        help="decrypt quoted data with symmetric encryption",
        description="decrypt quoted data with symmetric encryption",
        arguments=[
            (["data"], {"help": "data to decrypt", "action": "store", "type": str}),
            (
                ["key"],
                {
                    "action": "store",
                    "help": "secret key to use for encryption/decryption",
                },
            ),
        ],
    )
    def decrypt(self):
        from beecell.crypto import decrypt_data

        # self.check_secret_key()
        data = self.app.pargs.data
        # see API_FERNET_KEY in k8s files
        key = self.app.pargs.key
        key = ensure_binary(key)
        cipher_suite = Fernet(key)
        cipher_text = cipher_suite.decrypt(ensure_binary(data))
        self.app.render({"decrypt_data": cipher_text}, headers=["decrypt_data"], maxsize=200)
        testp = decrypt_data(key, data)
        print("beecel   :", testp)
