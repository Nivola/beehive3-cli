# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from base64 import b64decode
from urllib.parse import urlencode
from cement import ex
from beecell.util import ensure_text
from beecell.types.type_string import str2bool
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.ssh.controllers.ssh import SshControllerChild
from beehive3_cli.translate import _


class SshUserController(SshControllerChild):
    class Meta:
        stacked_on = "ssh"
        stacked_type = "nested"
        label = "node_users"
        description = _("node user management")
        help = _("node user management")

        headers = ["id", "name", "date", "node", "key"]
        fields = ["uuid", "username", "date.creation", "node_name", "key_name"]

    def pre_command_run(self):
        super().pre_command_run()

        self.configure_cmp_api_client()

    def __get_user_and_node(self, user):
        """Get user and node

        :param user: user uuid
        :return: (user, node)
        """
        # get user
        uri = f"{self.baseuri}/users/{user}"
        user = self.cmp_get(uri).get("user")

        # get node
        uri = f"{self.baseuri}/nodes/{user['node_id']}"
        node = self.cmp_get(uri).get("node")

        return user, node

    @ex(
        help=_("get node users"),
        description=_("get node users"),
        example="beehive ssh node-users get -id <uuid>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("node user uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-username"],
                    {
                        "help": _("node user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-node"],
                    {
                        "help": _("node uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        oid = getattr(self.app.pargs, "id", None)
        node = getattr(self.app.pargs, "node", None)
        username = getattr(self.app.pargs, "username", None)
        if oid is not None:
            uri = f"{self.baseuri}/users/{oid}"
            res = self.cmp_get(uri)
            self.app.render(res, key="user", details=True)

            # uncomment to check if all permissions are present:
            # uri = f"{self.baseuri}/users/{oid}/perms"
            # perms = self.cmp_get(uri).get("perms")
            # self.c("\nperms", "underline")
            # self.app.render(perms, headers=["oid","objid","subsystem","type","id", "aid", "action","desc"])
        elif node is not None and username is None:
            uri = f"{self.baseuri}/nodes/{node}"
            node = self.cmp_get(uri).get("node")["id"]

            data = {"node_id": node}
            uri = f"{self.baseuri}/users"
            res = self.cmp_get(uri, data=urlencode(data, doseq=True)).get("users")
            res_users = {i["username"]: i for i in res}

            # get info from node
            users = self.run_cmd("cat /etc/passwd", node=node).values()
            users = list(users)[0].get("stdout", [])

            resp = []
            for item in users:
                # 'centos:x:1001:1001:Cloud User:/home/centos:/bin/bash'
                name, __, uid, gid, desc, home, shell = item.split(":")
                res_user = res_users.get(name, {})
                resp.append(
                    {
                        "id": res_user.get("uuid", None),
                        "name": name,
                        "date": res_user.get("date", None),
                        "key": res_user.get("key_name", None),
                        "uid": uid,
                        "gid": gid,
                        "desc": desc,
                        "home": home,
                        "shell": shell,
                    }
                )

            headers = [
                "id",
                "name",
                "date",
                "key",
                "uid",
                "gid",
                "desc",
                "home",
                "shell",
            ]
            fields = [
                "id",
                "name",
                "date.creation",
                "key",
                "uid",
                "gid",
                "desc",
                "home",
                "shell",
            ]

            self.app.render(resp, headers=headers, fields=fields)
        else:
            params = ["username", "node"]
            aliases = {"node": "node_id"}
            data = self.format_paginated_query(params, aliases=aliases)
            uri = f"{self.baseuri}/users"
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="users", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("get node user password"),
        description=_("get node user password"),
        example="beehive ssh node-users get-password filippo-win01.site01.nivolapiemonte.it -e <env> ",
        arguments=PARGS([(["id"], {"help": _("user uuid"), "action": "store", "type": str})]),
    )
    def get_password(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/users/{oid}/password"
        res = self.cmp_get(uri).get("password", None)
        self.app.render({"msg": f"get node user {oid} password: {res}"})

    @ex(
        help=_("set node user password"),
        description=_("set node user password"),
        arguments=ARGS(
            [
                (["id"], {"help": _("user uuid"), "action": "store", "type": str}),
                (["pwd"], {"help": _("user password"), "action": "store", "type": str}),
                (
                    ["-propagate"],
                    {
                        "help": _("propagate user password set on vm"),
                        "action": "store",
                        "type": str,
                        "default": "true",
                    },
                ),
            ]
        ),
    )
    def set_password(self):
        oid = self.app.pargs.id
        pwd = self.app.pargs.pwd
        propagate = str2bool(self.app.pargs.propagate)

        user, node = self.__get_user_and_node(oid)

        # add user using paramiko
        if propagate is True:
            res = self.run_cmd(
                f"echo -e \"{pwd}\n{pwd}\" | passwd {user['username']}",
                node=node["id"],
            ).values()
            self.app.log.debug(res)

        # remove user via api
        data = {"user": {"password": pwd}}
        uri = f"{self.baseuri}/users/{oid}"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"set node {node['uuid']} user {user['username']} password"})

    def __set_public_key(self, user, node, key_string):
        res = self.run_cmd(
            f"echo {key_string} >> /home/{user}/.ssh/authorized_keys",
            node=node,
        ).values()
        self.app.log.debug(res)

    @ex(
        help=_("add new ssh user"),
        description=_("add new ssh user"),
        example="beehive ssh node-users add ansible <uuid> -sshkey cmp-key",
        arguments=PARGS(
            [
                (["name"], {"help": _("user name"), "action": "store", "type": str}),
                (
                    ["-pwd"],
                    {
                        "help": _("user password"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (["node"], {"help": _("node uuid"), "action": "store", "type": str}),
                (
                    ["-sshkey"],
                    {
                        "help": _("ssh key uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("user description"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-attrib"],
                    {
                        "help": _("user attributes"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-propagate"],
                    {
                        "help": _("if True create user also in node"),
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
            ]
        ),
    )
    def add(self):
        name = self.app.pargs.name
        password = self.app.pargs.pwd
        desc = self.app.pargs.desc
        node_id = self.app.pargs.node
        key_id = self.app.pargs.sshkey
        attribute = self.app.pargs.attrib
        propagate = str2bool(self.app.pargs.propagate)

        # get node
        uri = f"{self.baseuri}/nodes/{node_id}"
        node = self.cmp_get(uri, data="").get("node")

        # check user already exists
        data = {"node_id": node_id, "username": name}
        uri = f"{self.baseuri}/users"
        count = self.cmp_get(uri, data=urlencode(data)).get("count")
        if count > 0:
            raise Exception(f"node {node['uuid']} user {name} already exist")

        # get key
        if key_id is not None:
            uri = f"{self.baseuri}/keys/{key_id}"
            key = self.cmp_get(uri, data="").get("key", {})
            pub_key = key.get("pub_key", "")
            if pub_key != "":
                pub_key = ensure_text(b64decode(pub_key))

        # add user using ansible
        if propagate:
            cmd = f"useradd -m -p $(echo '{password}' | openssl passwd -6 -stdin) -s /bin/bash {name}"
            res = self.run_cmd(cmd, node=node["id"]).values()
            self.app.log.debug(res)
            res = self.run_cmd(
                "mkdir -p /home/{name}/.ssh && chmod -R 700 /home/{name}/.ssh".format(name=name),
                node=node["id"],
            ).values()
            self.app.log.debug(res)
            res = self.run_cmd(
                "echo "
                " > /home/{name}/.ssh/authorized_keys && chown -R {name}:{name} /home/{name}/.ssh"
                " && chmod -R 600 /home/{name}/.ssh/authorized_keys".format(name=name),
                node=node["id"],
            ).values()
            self.app.log.debug(res)
            if key_id is not None and pub_key != "":
                self.__set_public_key(name, node["id"], pub_key)

        data = {
            "user": {
                "name": f"{node.get('name')}-{name}",
                "desc": desc,
                "attribute": attribute,
                "node_id": node_id,
                "key_id": key_id,
                "username": name,
                "password": password,
            }
        }
        uri = f"{self.baseuri}/users"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add user {res['uuid']}"})

    @ex(
        help=_("delete node user"),
        description=_("delete node user"),
        example="beehive ssh node-users delete <uuid>",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("node user uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-propagate"],
                    {
                        "help": _("if True create user also in node"),
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        propagate = self.app.pargs.propagate

        user, node = self.__get_user_and_node(oid)

        # remove user using ansible
        if propagate:
            # self.ansible_user_remove(user['username'], group=None, node=node['name'])
            res = self.run_cmd(f"userdel -rf {user['username']}", node=node["id"]).values()
            self.app.log.debug(res)

        # remove node from cmp
        uri = f"{self.baseuri}/users/{oid}"
        self.cmp_delete(uri, data="", entity=f"node user {oid}")
