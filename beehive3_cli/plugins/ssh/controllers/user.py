# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from base64 import b64decode
from urllib.parse import urlencode
from six import ensure_text
from cement import ex
from passlib.handlers.sha2_crypt import sha512_crypt
from beecell.types.type_string import str2bool
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.ssh.controllers.ssh import SshControllerChild


class SshUserController(SshControllerChild):
    class Meta:
        stacked_on = "ssh"
        stacked_type = "nested"
        label = "node_users"
        description = "node user management"
        help = "node user management"

        headers = ["id", "name", "date", "node", "key"]
        fields = ["uuid", "username", "date.creation", "node_name", "key_name"]

    def pre_command_run(self):
        super(SshUserController, self).pre_command_run()

        self.configure_cmp_api_client()

    def __get_user_and_node(self, user):
        """Get user and node

        :param user: user uuid
        :return: (user, node)
        """
        # get user
        uri = "%s/users/%s" % (self.baseuri, user)
        user = self.cmp_get(uri).get("user")

        # get node
        uri = "%s/nodes/%s" % (self.baseuri, user["node_id"])
        node = self.cmp_get(uri).get("node")

        return user, node

    @ex(
        help="get node users",
        description="get node users",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "node user uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-username"],
                    {
                        "help": "node user name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-node"],
                    {
                        "help": "node uuid",
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
            uri = "%s/users/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)
            self.app.render(res, key="user", details=True)
        elif node is not None and username is None:
            uri = "%s/nodes/%s" % (self.baseuri, node)
            node = self.cmp_get(uri).get("node")["id"]

            data = {"node_id": node}
            uri = "%s/users" % self.baseuri
            res = self.cmp_get(uri, data=urlencode(data, doseq=True)).get("users")
            res_users = {i["username"]: i for i in res}

            # get info from node
            users = self.run_cmd("cat /etc/passwd", node=node).values()
            users = list(users)[0].get("stdout", [])

            resp = []
            for item in users:
                # 'centos:x:1001:1001:Cloud User:/home/centos:/bin/bash'
                name, t1, uid, gid, desc, home, shell = item.split(":")
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
            uri = "%s/users" % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="users", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help="get node user password",
        description="get node user password",
        arguments=PARGS([(["id"], {"help": "user uuid", "action": "store", "type": str})]),
    )
    def get_password(self):
        oid = self.app.pargs.id
        uri = "%s/users/%s/password" % (self.baseuri, oid)
        res = self.cmp_get(uri).get("password", None)
        self.app.render({"msg": "get node user %s password: %s" % (oid, res)})

    @ex(
        help="set node user password",
        description="set node user password",
        arguments=ARGS(
            [
                (["id"], {"help": "user uuid", "action": "store", "type": str}),
                (["pwd"], {"help": "user password", "action": "store", "type": str}),
                (
                    ["-propagate"],
                    {
                        "help": "propagate user password set on vm",
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
        # enc_pwd = sha512_crypt.using(rounds=5000).hash(pwd)
        if propagate is True:
            res = self.run_cmd(
                'echo -e "%s\n%s" | passwd %s' % (pwd, pwd, user["username"]),
                node=node["id"],
            ).values()
            self.app.log.debug(res)

        # ansible_pwd = sha512_crypt.using(rounds=5000).hash(pwd)
        # self.ansible_user_change_password(user['username'], ansible_pwd, group=None, node=node['name'])

        # remove user via api
        data = {"user": {"password": pwd}}
        uri = "%s/users/%s" % (self.baseuri, oid)
        self.cmp_put(uri, data=data)
        self.app.render({"msg": "set node %s user %s password" % (node["uuid"], user["username"])})

    # @ex(
    #     help='add ssh key to user',
    #     description='add ssh key to user',
    #     arguments=ARGS([
    #         (['id'], {'help': 'node uuid', 'action': 'store', 'type': str}),
    #         (['key-file '], {'help': 'file that contains private ssh key', 'action': 'store', 'type': str}),
    #     ])
    # )
    # def add_sshkey(self):
    #     oid = self.app.pargs.id
    #     key_file = self.app.pargs.key_file
    #
    #     user, node = self.__get_user_and_node(oid)
    #
    #     self.ansible_user_set_ssh_key(user['username'], key_file, node=node['name'])
    #     self.app.render({'msg': 'Set node %s user %s ssh key' % (node['uuid'], user['username'])})
    #
    # @ex(
    #     help='remove ssh key from user',
    #     description='remove ssh key from user',
    #     arguments=ARGS([
    #         (['id'], {'help': 'user uuid', 'action': 'store', 'type': str}),
    #         (['key-file '], {'help': 'file that contains private ssh key', 'action': 'store', 'type': str}),
    #     ])
    # )
    # def del_sshkey(self):
    #     oid = self.app.pargs.id
    #     key_file = self.app.pargs.key_file
    #
    #     user, node = self.__get_user_and_node(oid)
    #
    #     self.ansible_user_unset_ssh_key(user['username'], key_file, node=node['name'])
    #     self.app.render({'msg': 'Unset node %s user %s ssh key' % (node['uuid'], user['username'])})

    def __set_public_key(self, user, node, key_string):
        res = self.run_cmd(
            "echo {key} >> /home/{name}/.ssh/authorized_keys".format(name=user, key=key_string),
            node=node,
        ).values()
        self.app.log.debug(res)

    @ex(
        help="add new ssh user",
        description="add new ssh user",
        arguments=PARGS(
            [
                (["name"], {"help": "user name", "action": "store", "type": str}),
                (
                    ["-pwd"],
                    {
                        "help": "user password",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (["node"], {"help": "node uuid", "action": "store", "type": str}),
                (
                    ["-sshkey"],
                    {
                        "help": "ssh key uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "user description",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-attrib"],
                    {
                        "help": "user attributes",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-propagate"],
                    {
                        "help": "if True create user also in node",
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
        uri = "%s/nodes/%s" % (self.baseuri, node_id)
        node = self.cmp_get(uri, data="").get("node")

        # check user already exists
        data = {"node_id": node_id, "username": name}
        uri = "%s/users" % self.baseuri
        count = self.cmp_get(uri, data=urlencode(data)).get("count")
        if count > 0:
            raise Exception("node %s user %s already exist" % (node["uuid"], name))

        # get key
        if key_id is not None:
            uri = "%s/keys/%s" % (self.baseuri, key_id)
            key = self.cmp_get(uri, data="").get("key", {})
            pub_key = key.get("pub_key", "")
            if pub_key != "":
                pub_key = ensure_text(b64decode(pub_key))

        # add user using ansible
        if propagate:
            enc_pwd = sha512_crypt.using(rounds=5000).hash(password)
            res = self.run_cmd("useradd -m -p '%s' -s /bin/bash %s" % (enc_pwd, name), node=node["id"]).values()
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

            # ansible_pwd = sha512_crypt.using(rounds=5000).hash(password)
            # self.ansible_user_create(name, desc, name, ansible_pwd, pub_key, group=None, node=node['name'])

        data = {
            "user": {
                "name": "%s-%s" % (node.get("name"), name),
                "desc": desc,
                "attribute": attribute,
                "node_id": node_id,
                "key_id": key_id,
                "username": name,
                "password": password,
            }
        }
        uri = "%s/users" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "add user %s" % res["uuid"]})

    @ex(
        help="delete node user",
        description="delete node user",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "node user uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-propagate"],
                    {
                        "help": "if True create user also in node",
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
            res = self.run_cmd("userdel -rf %s" % user["username"], node=node["id"]).values()
            self.app.log.debug(res)

        # remove node from cmp
        uri = "%s/users/%s" % (self.baseuri, oid)
        self.cmp_delete(uri, data="", entity="node user %s" % oid)
