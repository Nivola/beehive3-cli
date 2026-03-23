# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from getpass import getpass
from os import path
from sys import stdout
from base64 import b64decode
from cement import ex

from beecell.util import ensure_text
from beecell.types.type_list import merge_list
from beecell.types.type_string import str2bool
from beecell.paramiko_shell.shell import Rsync

from beehive3_cli.core.controller import BASE_ARGS
from beehive3_cli.core.util import load_environment_config, ColoredText
from beehive3_cli.plugins.platforms.controllers import ChildPlatformController
from beehive3_cli.translate import _

try:
    from scp import SCPClient
except:
    pass


def console_args(*list_args):
    orchestrator_args = [
        (
            ["-C", "--console"],
            {"action": "store", "dest": "console", "help": _("console label")},
        )
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class ConsoleController(ChildPlatformController):
    class Meta:
        label = "console"
        description = _("console management")
        help = _("console management")

        cmp = {"baseuri": "/v1.0/nas", "subsystem": "auth"}

    def pre_command_run(self):
        super().pre_command_run()

        self.configure_cmp_api_client()

        self.config_path = self.app.config.get("beehive", "cmp_config_path")

        self.config = load_environment_config(self.app)

        consoles = self.config.get("consoles", {}).get(self.env, {})
        label = getattr(self.app.pargs, "console", None)

        if label is None:
            keys = list(consoles.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception("No default console is available for this environment. Select another environment")

        if label not in list(consoles.keys()):
            raise Exception(f"Valid label are: {', '.join(consoles.keys())}")
        self.conf = consoles.get(label)
        params = self.conf.get("params")

        self.user_config_path = params.get("config_path", ".beehive3")
        self.user_path = params.get("path")
        self.user_domain = params.get("domain")
        self.user_group = params.get("group")
        self.console_type = params.get("type")
        self.user_postfix = params.get("user_postfix")
        self.is_docker = params.get("docker", False)
        if self.user_postfix != "":
            self.user_postfix = "@" + self.user_postfix

    def __get_ssh_client(self):
        from beecell.paramiko_shell.shell import ParamikoShell

        keystring = b64decode(self.conf.get("sshkey", ""))
        user = self.conf.get("user", "")
        host = self.conf.get("host", "")
        client = ParamikoShell(host, user, keystring=keystring)
        return client

    def __scp_progress(self, filename, size, sent):
        """Define progress callback that prints the current percentage completed for the file"""
        status = float(sent) / float(size)
        newline = "\n"
        if status < 1:
            newline = "\r"
        stdout.write(f"{ensure_text(filename)} progress: {status * 100:.2f}% {newline}")

    @ex(
        help=_("connect to console"),
        description=_("connect to console"),
        arguments=console_args(
            [
                (
                    ["-user"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (["-pwd"], {"help": _("user password required"), "action": "store_true"}),
            ]
        ),
    )
    def connect(self):
        from beecell.paramiko_shell.shell import ParamikoShell

        user = self.app.pargs.user
        pwd = self.app.pargs.pwd

        if user is None:
            user = self.conf.get("user", "")
            keystring = b64decode(self.conf.get("sshkey", ""))
        else:
            keystring = None

        if pwd is True:
            pwd = getpass()
        else:
            pwd = None

        host = self.conf.get("host", "")
        ParamikoShell(host, user, pwd=pwd, keystring=keystring).run()

    @ex(
        help=_("get cmp packages version"),
        description=_("get cmp packages version"),
        arguments=console_args(),
    )
    def versions(self):
        client = self.__get_ssh_client()
        cmds = [
            "cd /usr/local/lib/python3.6/site-packages",
            "python3 -c 'import beehive; print(beehive.__version__)'",
            "python3 -c 'import beehive3_cli; print(beehive3_cli.__version__)'",
            "python3 -c 'import beecell; print(beecell.__version__)'",
            "python3 -c 'import beedrones; print(beedrones.__version__)'",
            "python3 -c 'import beehive_ansible; print(beehive_ansible.__version__)'",
        ]
        cmd = "&&".join(cmds)
        res = client.cmd(cmd, timeout=30.0)
        res = res.get("stdout")
        if res is not None and len(res) > 0:
            ver = [
                {"package": "beehive", "version": res[0]},
                {"package": "beehive3_cli", "version": res[1]},
                {"package": "beecell", "version": res[2]},
                {"package": "beedrones", "version": res[3]},
                {"package": "beehive_ansible", "version": res[4]},
            ]
            self.app.render(ver, headers=["package", "version"])

    def __sync(self, pkgs, base_remote_package_path):
        keystring = b64decode(self.conf.get("sshkey", ""))
        user = self.conf.get("user", "")
        host = self.conf.get("host", "")

        rsync_client = Rsync(user=user, keystring=keystring)
        rsync_client.add_exclude("*.pyc")
        rsync_client.add_exclude("*.pyo")
        rsync_client.add_exclude("__pycache__")

        for pkg in pkgs:
            local_package_path = f"{self.local_package_path}/{pkg}"
            remote_package_path = f"{user}@{host}:{base_remote_package_path}"
            rsync_client.run(local_package_path, remote_package_path)
            print(f"sync package {pkg} to {remote_package_path}")

    @ex(
        help=_("update shell console"),
        description=_("update shell console"),
        arguments=console_args(
            [
                (
                    ["-pkgs"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def update(self):
        pkgs = self.app.pargs.pkgs
        if pkgs is not None:
            pkgs = pkgs.split(",")
        if pkgs is None:
            pkgs = [
                "beecell/beecell",
                "beedrones/beedrones",
                "beehive/beehive",
                "beehive3-cli/beehive3_cli",
                # 'beehive_ansible',
            ]
        python_path = "/usr/local/lib/python3.6/site-packages"
        self.__sync(pkgs, python_path)

    def get_cmp_user(self, user):
        # get user from api auth
        uri = f"{self.baseuri}/users/{user}@{self.user_domain}"
        cmp_user = self.cmp_get(uri).get("user", {})
        return cmp_user

    def get_template_env_file_version(self, env):
        env_config_path = self.config_path + "/console/beehive3.env"
        env_config_path = path.expanduser(env_config_path)
        filename = f"{env_config_path}/{env}"
        version = ""

        if path.isfile(filename):
            with open(filename, "r", encoding="utf-8") as f:
                value = f.readline()
                version = value.replace("version: ", "").strip()

        return version

    def get_user_env_file_version(self, client, user, env):
        res = client.cmd(
            f"head -1 {self.user_path}/{user}/{self.user_config_path}/config/env/{env}",
            timeout=30.0,
        )
        l_stdout = res.get("stdout")
        version = ""
        if len(l_stdout) > 0 and l_stdout[0].find("version") == 0:
            version = l_stdout[0].lstrip("version: ")
        return version

    @ex(
        help=_("list user configured"),
        description=_("list user configured"),
        example="beehive platform console user-list",
        arguments=console_args([]),
    )
    def user_list(self):
        tmpl = "{idx:6} {user:20} {cmp_user:20} {envs:50}"
        #line = "".join(["-" for i in range(40)])
        headers = {"idx": "idx", "user": "user", "cmp_user": "cmp_user", "envs": "envs"}
        print(tmpl.format(**headers))

        client = self.__get_ssh_client()
        res = client.cmd(f"ls {self.user_path}", timeout=30.0)
        users = res.get("stdout")
        res = client.cmd("ps -efa |grep python3|grep -v grep|awk '{print($1)}'", timeout=30.0)
        from collections import Counter

        procs = Counter(res.get("stdout"))
        idx = 1
        for user in users:
            res = client.cmd(
                f"ls {self.user_path}/{user}/{self.user_config_path}/config/env/",
                timeout=30.0,
            )
            sessions = procs.get(user, 0)

            # get user from api auth
            cmp_user = self.get_cmp_user(user)
            cmp_user_name = cmp_user.get("desc", "")

            if res.get("stderr") != "":
                item = {"idx": idx, "user": user, "cmp_user": cmp_user_name, "envs": ""}
            else:
                envs = [e.rstrip(".yml") for e in res.get("stdout")]
                final_envs = []

                # check if envs should be updated
                need_update = 0
                for env in envs:
                    colored_env = env
                    env = f"{env}.yml"
                    template_version = self.get_template_env_file_version(env)
                    version = self.get_user_env_file_version(client, user, env)
                    if version != template_version:
                        colored_env = ColoredText().red(colored_env)
                        need_update += 1
                    final_envs.append(colored_env)

                item = {
                    "idx": idx,
                    "user": user,
                    "cmp_user": cmp_user_name,
                    "envs": ",".join(final_envs),
                }

            l_repr = tmpl.format(**item)
            if sessions > 0:
                l_repr = self.app.colored_text.output(l_repr, "GREEN")
            if res.get("stderr") != "":
                l_repr = self.app.colored_text.output(l_repr, "RED")
            print(l_repr)
            idx += 1

    @ex(
        help=_("get user configured"),
        description=_("get user configured"),
        example="beehive platform console user-get 74067",
        arguments=console_args(
            [
                (
                    ["user"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": "user",
                    },
                ),
            ]
        ),
    )
    def user_get(self):
        user = self.app.pargs.user
        client = self.__get_ssh_client()

        # get user from api auth
        cmp_user = self.get_cmp_user(user)

        print(f"console user id  : {user}")
        print(f"console user name: {cmp_user['name']}")
        print(f"console user desc: {cmp_user['desc']}")
        res = client.cmd(
            f"ls {self.user_path}/{user}/{self.user_config_path}/config/env",
            timeout=30.0,
        )
        res_envs = res.get("stdout")
        envs = []
        for res_env in res_envs:
            version = self.get_user_env_file_version(client, user, res_env)
            template_version = self.get_template_env_file_version(res_env)
            need_update = False
            if version != template_version:
                need_update = True
            envs.append(
                {
                    "name": res_env.rstrip(".yml"),
                    "version": version,
                    "template_version": template_version,
                    "need_update": need_update,
                }
            )

        self.c("\nenvironments", "underline")
        self.app.render(envs, headers=["name", "version", "template_version", "need_update"])

        self.c("\nsessions", "underline")
        sessions = client.cmd(
            "ps -efa |grep python3|grep -v grep|awk '{print($1,$5,$7,$13)}'|grep %s" % user,
            timeout=30.0,
        ).get("stdout")
        sessions = [s.split(" ") for s in sessions]
        sessions = [{"date": s[1], "time": s[2], "node": s[3]} for s in sessions]

        self.c("\nconsole management", "underline")
        exists = client.cmd(f"ls {self.user_path}/{user}/beehive-mgmt", timeout=30.0)
        if exists.get("stderr") != "":
            print("is configured: False")
        else:
            print("is configured: True")

    def __add_environment(self, sshclient, env, sshuser):
        env_config_path = self.config_path + "/console/beehive3.env"
        env_config_path = path.expanduser(env_config_path)

        cmpuser = f"{sshuser}@{self.user_domain}"
        remote_filepath = f"{self.user_path}/{sshuser}/{self.user_config_path}/config/env"

        # get auth user secret
        self.app.env = env
        self.configure_cmp_api_client()
        uri = f"{self.baseuri}/users/{cmpuser}/secret"
        user = self.cmp_get(uri)
        secret = user.get("user").get("secret")
        filename = f"{env_config_path}/{env}.yml"

        if path.isfile(filename):
            with open(filename, "r", encoding="utf-8") as f:
                value = f.read()
            value = value.replace("{{ cmp_user }}", cmpuser).replace("{{ cmp_secret }}", secret)
            fp = self.create_temp_file(value)
            # fp.seek(0)
            remote_filename = f"{remote_filepath}/{env}.yml"
            sshclient.file_put(fp.name, remote_filename)
            self.close_temp_file(fp)
            print(f"add env {env} to user {sshuser}")

    @ex(
        help=_("setup user home directory and configuration"),
        description=_("setup user home directory and configuration"),
        example="beehive platform console user-setup name.surname -e <env>",
        arguments=console_args([(["user_ssh"], {"help": _("console user"), "action": "store", "type": str})]),
    )
    def user_setup(self):
        sshuser = self.app.pargs.user_ssh

        client = self.__get_ssh_client()
        tmpl_config_path = self.config_path + "/console/template"
        tmpl_config_path = path.expanduser(tmpl_config_path)

        # create user home directory
        dirname = f"{self.user_path}/{sshuser}/{self.user_config_path}/config/env"
        client.mkdir(dirname)
        print(f"create directory: {dirname}")
        dirname = f"{self.user_path}/{sshuser}/{self.user_config_path}/.tokens"
        client.mkdir(dirname)
        print(f"create directory: {dirname}")
        dirname = f"{self.user_path}/{sshuser}"
        user = f"{sshuser}{self.user_postfix}"
        filename = f"{self.user_path}/{sshuser}/.bashrc"
        client.file_put(f"{tmpl_config_path}/bashrc.j2", filename)
        print(f"put file: {filename}")
        filename = f"{self.user_path}/{sshuser}/.bash_profile"
        client.file_put(f"{tmpl_config_path}/bash_profile.j2", filename)
        print(f"put file: {filename}")
        filename = f"{self.user_path}/{sshuser}/.beehive3.docker.bash_history"
        client.file_put(f"{tmpl_config_path}/bash_history.j2", filename)
        print(f"put file: {filename}")
        self.__add_environment(client, "nivola", sshuser)
        client.chown(dirname, user=user, group=self.user_group)
        print(f"change directory {dirname} owner to: {user}:{self.user_group}")
        client.chmod(dirname, acl="700")
        print(f"change directory {dirname} acl to: 700")
        filename = f"{self.user_path}/{sshuser}/.beehive3.docker.bash_history"
        client.chmod(filename, acl="666")
        print(f"change file {filename} acl to: 666")

        if self.is_docker:
            dirname = f"{self.user_path}/{sshuser}/.beehive3.docker"
            client.chmod(dirname, acl="777")
            print(f"change directory {dirname} acl to: 777")
            filename = f"{self.user_path}/{sshuser}/{self.user_config_path}/config/beehive.yml"

            client.file_put(
                f"{tmpl_config_path}/beehive.docker.yml.{self.console_type}.j2",
                filename,
            )
            print(f"put file: {filename}")
            filename = f"{self.user_path}/{sshuser}/cli-start"
            client.file_put(f"{tmpl_config_path}/cli-start.j2", filename)
            print(f"put file: {filename}")
            client.chmod(filename, acl="755")
            print(f"change file {filename} acl to: 666")
            client.cmd(f"usermod -a -G docker {user}", timeout=30.0).get("stdout")
            print(f"add user {user} to group docker")
        else:
            filename = f"{self.user_path}/{sshuser}/{self.user_config_path}/config/beehive.yml"
            client.file_put(f"{tmpl_config_path}/beehive.yml.{self.console_type}.j2", filename)
            print(f"put file: {filename}")

        # echo -e 'Host *\n   StrictHostKeyChecking no\n   UserKnownHostsFile=/dev/null' > .ssh/config

    @ex(
        help=_("update user base config"),
        description=_("update user base config"),
        arguments=console_args(
            [
                (
                    ["user_ssh"],
                    {"help": _("console user"), "action": "store", "type": str},
                ),
                (
                    ["-isadmin"],
                    {
                        "help": _("console user"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
            ]
        ),
    )
    def user_update(self):
        sshuser = self.app.pargs.user_ssh
        isadmin = str2bool(self.app.pargs.isadmin)

        client = self.__get_ssh_client()
        ssh = client.client
        tmpl_config_path = self.config_path + "/console/template"

        filename = f"{self.user_path}/{sshuser}/{self.user_config_path}/config/beehive.yml"
        client.file_put(f"{tmpl_config_path}/beehive.yml.{self.console_type}.j2", filename)
        print(f"put file: {filename}")

        # echo -e 'Host *\n   StrictHostKeyChecking no\n   UserKnownHostsFile=/dev/null' > .ssh/config

        if isadmin is True:
            dirname = f"{self.user_path}/{sshuser}/beehive-mgmt/configs"
            client.mkdir(dirname)
            print(f"create directory: {dirname}")
            with SCPClient(ssh.get_transport(), progress=self.__scp_progress) as scp:
                for l_path in ["configs/console", "post-install"]:
                    local_package_path = f"{self.local_package_path}/beehive-mgmt/{l_path}"
                    remote_package_path = f"{self.user_path}/{sshuser}/beehive-mgmt/{l_path}"
                    scp.put(
                        local_package_path,
                        recursive=True,
                        remote_path=remote_package_path,
                    )

            dirname = f"{self.user_path}/{sshuser}/beehive-mgmt"
            user = f"{sshuser}{self.user_postfix}"
            client.chown(dirname, user=user, group=self.user_group)
            print(f"change directory {dirname} owner to: {user}:{self.user_group}")

    @ex(
        help=_("setup user additional environment"),
        description=_("setup user additional environment"),
        example="beehive platform console user-env-add ### site1,site2,site3 -e <env> -C cons01",
        arguments=console_args(
            [
                (
                    ["user_ssh"],
                    {"help": _("console user"), "action": "store", "type": str},
                ),
                (
                    ["user_env"],
                    {
                        "help": _("comma separated list of environment to add"),
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def user_env_add(self):
        sshuser = self.app.pargs.user_ssh
        envs = self.app.pargs.user_env.split(",")

        client = self.__get_ssh_client()
        for env in envs:
            if sshuser == "all":
                res = client.cmd(f"ls {self.user_path}", timeout=30.0)
                users = res.get("stdout")
                # users = ['1004', '1019', '1031']
                for sshuser in users:
                    try:
                        self.__add_environment(client, env, sshuser)
                    except:
                        pass
            else:
                self.__add_environment(client, env, sshuser)
