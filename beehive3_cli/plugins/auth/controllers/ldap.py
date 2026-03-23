# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex

from beehive3_cli.core.controller import ARGS, BaseController
from beehive3_cli.core.util import load_environment_config
from beehive3_cli.translate import _


class AuthLdapController(BaseController):
    class Meta:
        stacked_on = "auth"
        stacked_type = "nested"
        label = "ldap"
        description = _("ldap management")
        help = _("ldap management")

    def pre_command_run(self):
        from beecell.auth import LdapAuth, SystemUser

        super().pre_command_run()

        self.config = load_environment_config(self.app)
        ldaps = self.config.get("ldap", None)
        if ldaps is None:
            raise Exception("no ldap exist in this environment")

        label = self.app.pargs.ldap

        if label is None or label not in ldaps:
            raise Exception(f"Valid label are: {', '.join(ldaps.keys())}")
        conf = ldaps.get(label)

        self.search_filter = conf.get("search_filter")
        self.client = LdapAuth(
            conf.get("host"),
            SystemUser,
            port=conf.get("port"),
            timeout=conf.get("timeout"),
            ssl=conf.get("ssl", True),
            dn=conf.get("dn"),
            search_filter=self.search_filter,
            search_id=conf.get("search_id"),
            bind_user=conf.get("bind_user"),
            bind_pwd=conf.get("bind_pwd"),
            max_retries=0
        )

    @ex(
        help=_("login user"),
        description=_("login user"),
        arguments=ARGS(
            [
                (["email"], {"help": _("user email"), "action": "store", "type": str}),
                (["pwd"], {"help": _("user password"), "action": "store", "type": str}),
                (
                    ["-ldap"],
                    {
                        "help": _("ldap reference label"),
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
        self.client.close()
        if user is not None:
            user = user.get_dict()
        self.app.render(user, details=True)

    @ex(
        help=_("search users"),
        description=_("search users"),
        example="beehive auth ldap search abc.def@ghi.lmno -ldap xxxxx",
        arguments=ARGS(
            [
                (
                    ["value"],
                    {"help": _("value to search"), "action": "store", "type": str},
                ),
                #(
                #    ["-filter"],
                #    {
                #        "help": _("search filter"),
                #        "action": "store",
                #        "type": str,
                #        "default": "mail",
                #    },
                #),
                (
                    ["-fields"],
                    {
                        "help": _("query fields"),
                        "action": "store",
                        "type": str,
                        "default": "cn,mail,uidNumber,uid",
                    },
                ),
                (
                    ["-ldap"],
                    {
                        "help": _("ldap reference label"),
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
        s_filter = self.search_filter.format(username=value)
        self.client.set_admin_credentials()
        ldap_fields = fields.split(",")
        users = self.client.search_users(s_filter, ldap_fields)
        self.client.close()
        self.app.render(users, headers=fields)


    @ex(
        help=_("get user"),
        description=_("get user "),
        example="beehive auth ldap get abc.def@ghi.lmno -e <env> -ldap xxxxx",
        arguments=ARGS(
            [
                (
                    ["user_key"],
                    {
                        "help": _("user key like user email"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-ldap"],
                    {
                        "help": _("ldap reference label"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        key = self.app.pargs.user_key
        self.client.set_admin_credentials()
        user_dict = self.client.search_user(search_params={"username": key}, search_filter=self.search_filter, convert_to_dict=True)
        self.app.render(user_dict, details=True)
