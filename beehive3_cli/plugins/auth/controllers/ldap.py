# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from six import ensure_str
from cement import ex
from beecell.auth import LdapAuth, SystemUser
from beehive3_cli.core.controller import ARGS, BaseController
from beehive3_cli.core.util import load_environment_config


class AuthLdapController(BaseController):
    class Meta:
        stacked_on = "auth"
        stacked_type = "nested"
        label = "ldap"
        description = "ldap management"
        help = "ldap management"

    def pre_command_run(self):
        super(AuthLdapController, self).pre_command_run()

        self.config = load_environment_config(self.app)
        ldaps = self.config.get("ldap", None)
        if ldaps is None:
            raise Exception("no ldap exist in this environment")

        label = self.app.pargs.ldap

        if label is None or label not in ldaps:
            raise Exception("Valid label are: %s" % ", ".join(ldaps.keys()))
        conf = ldaps.get(label)

        self.search_filter = conf.get("search_filter")
        self.client = LdapAuth(
            conf.get("host"),
            SystemUser,
            port=conf.get("port"),
            timeout=conf.get("timeout"),
            ssl=conf.get("ssl"),
            dn=conf.get("dn"),
            search_filter=self.search_filter,
            search_id=conf.get("search_id"),
            bind_user=conf.get("bind_user"),
            bind_pwd=conf.get("bind_pwd"),
        )

    @ex(
        help="login user",
        description="login user",
        arguments=ARGS(
            [
                (["email"], {"help": "user email", "action": "store", "type": str}),
                (["pwd"], {"help": "user password", "action": "store", "type": str}),
                (
                    ["-ldap"],
                    {
                        "help": "ldap reference label",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def login(self):
        name = self.app.pargs.email
        pwd = self.app.pargs.pwd
        user = self.client.login(name, pwd)
        if user is not None:
            user = user.get_dict()
        self.app.render(user, details=True)

    @ex(
        help="search users",
        description="search users",
        arguments=ARGS(
            [
                (
                    ["value"],
                    {"help": "value to search", "action": "store", "type": str},
                ),
                (
                    ["-filter"],
                    {
                        "help": "search filter",
                        "action": "store",
                        "type": str,
                        "default": "mail",
                    },
                ),
                (
                    ["-fields"],
                    {
                        "help": "query fields",
                        "action": "store",
                        "type": str,
                        "default": "cn,mail",
                    },
                ),
                (
                    ["-ldap"],
                    {
                        "help": "ldap reference label",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def search(self):
        value = self.app.pargs.value
        # filter = self.app.pargs.filter
        fields = self.app.pargs.fields
        filter = self.search_filter.format(username=value)
        self.client.authenticate(self.client.bind_user, self.client.bind_pwd)
        users = self.client.search_users(filter)
        self.client.close()
        self.app.render(users, headers=fields)

    def infos(self):
        file = self.get_arg(name="file")
        values = self.load_file(file)

        self.client.authenticate(self.client.bind_user, self.client.bind_pwd)

        for item in values.split("\n"):
            item = item.split(",")
            if len(item) > 1:
                matricola = item[1].split("@")[0]
                filter = "(sAMAccountName=%s)" % matricola
                user = self.client.search_users(filter)[0]
                mail = user["mail"]
                name = mail.split("@")[0].split(".")
                name[0] = name[0][0].upper() + name[0][1:]
                name[1] = name[1][0].upper() + name[1][1:]
                name = "%s %s" % (name[0], name[1])
                # print('%s,%s,%s,%s' % (item[0], item[1], name, user['mail']))
                print("UPDATE `auth`.`user` SET `desc`='%s', `email`='%s' WHERE id=%s;" % (name, user["mail"], item[0]))

        self.client.close()

    @ex(
        help="get user",
        description="get user",
        arguments=ARGS(
            [
                (
                    ["key"],
                    {
                        "help": "user key like user email",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-filter"],
                    {
                        "help": "search filter",
                        "action": "store",
                        "type": str,
                        "default": "(mail={username})",
                    },
                ),
                (
                    ["-ldap"],
                    {
                        "help": "ldap reference label",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        key = self.app.pargs.key
        filter = self.search_filter
        self.client.authenticate(self.client.bind_user, self.client.bind_pwd)
        user = self.client.search_user({"username": key}, filter)
        data = {"name": user[0]}
        for k, v in user[1].items():
            try:
                if len(v) == 1:
                    v = v[0]
                data[ensure_str(k)] = ensure_str(v)
            except:
                data[ensure_str(k)] = ""

        self.app.render(data, details=True)
