# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from getpass import getpass
from ujson import dumps
from cement import ex

from beecell.types.type_string import str2bool
from beehive3_cli.core.connect import SshConnectionManager
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.core.util import load_config
from beehive3_cli.plugins.ssh.controllers.ssh import SshControllerChild


class SshNodeController(SshControllerChild):
    class Meta:
        label = "nodes"
        description = "server management"
        help = "server management"

        headers = ["uuid", "name", "desc", "ip_address", "date"]
        fields = ["uuid", "name", "desc", "ip_address", "date.creation"]

    # def pre_command_run(self):
    #     super(SshNodeController, self).pre_command_run()
    #     self.configure_cmp_api_client()

    @ex(
        help="get nodes",
        description="get nodes",
        example="beehive ssh nodes get > mauro01;beehive ssh nodes get -e <env>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "node name or uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-nodegroup"],
                    {
                        "help": "node group name or uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-names"],
                    {
                        "help": "node name like",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ip_address"],
                    {
                        "help": "node ip address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-key"],
                    {
                        "help": "ssh key name or uuid",
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
        if oid is not None:
            uri = "%s/nodes/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri)
            if self.is_output_text():
                res = res.get("node", {})
                users = res.pop("users", [])
                groups = res.pop("groups", [])
                self.app.render(res, details=True)
                print("groups:")
                self.app.render(groups, headers=["id", "name"], maxsize=200)
                print("users:")
                self.app.render(users, headers=["id", "name", "key"])
            else:
                self.app.render(res, key="node", details=True)

        else:
            params = ["nodegroup", "names", "ip_address", "key"]
            aliases = {"nodegroup": "group_id", "key": "key_id"}
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings, aliases=aliases)
            uri = "%s/nodes" % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="nodes", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help="add node",
        description="add node",
        example="beehive ssh nodes add k8sm01-indire-prod01.site02.nivolapiemonte.it podto2 admin-platform ###.###.###.###;beehive ssh nodes add k8s-lb-priv01-csi-prod01.site02.nivolapiemonte.it podto2 admin-platform ###.###.###.###",
        arguments=ARGS(
            [
                (["name"], {"help": "node group name", "action": "store", "type": str}),
                (
                    ["nodegroup"],
                    {"help": "node group name or uuid", "action": "store", "type": str},
                ),
                (["type"], {"help": "node type", "action": "store", "type": str}),
                (
                    ["ip_address"],
                    {"help": "node ip address", "action": "store", "type": str},
                ),
                (
                    ["-desc"],
                    {
                        "help": "node description",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-attrib"],
                    {
                        "help": "node attributes",
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
            ]
        ),
    )
    def add(self):
        name = self.app.pargs.name
        nodegroup = self.app.pargs.nodegroup
        nodetype = self.app.pargs.type
        ip_address = self.app.pargs.ip_address
        desc = self.app.pargs.desc
        attribute = self.app.pargs.attrib
        data = {
            "node": {
                "name": name,
                "desc": desc,
                "attribute": attribute,
                "group_id": nodegroup,
                "node_type": nodetype,
                "ip_address": ip_address,
            }
        }
        uri = "%s/nodes" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "add node %s" % res.get("uuid")})

    @ex(
        help="update node",
        description="update node",
        arguments=ARGS(
            [
                (["id"], {"help": "node name or uuid", "action": "store", "type": str}),
                (
                    ["-name"],
                    {
                        "help": "node group name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "node type",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-ip_address"],
                    {
                        "help": "node ip address",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": "node description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-attribute"],
                    {
                        "help": "node attributes",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def update(self):
        oid = self.app.pargs.id
        data = {}
        self.add_field_from_pargs_to_data("name", data, "name", reject_value=None, format=None)
        self.add_field_from_pargs_to_data("attribute", data, "attribute", reject_value=None, format=None)
        self.add_field_from_pargs_to_data("type", data, "node_type", reject_value=None, format=None)
        self.add_field_from_pargs_to_data("ip_address", data, "ip_address", reject_value=None, format=None)
        uri = "%s/nodes/%s" % (self.baseuri, oid)
        res = self.cmp_put(uri, data={"node": data})
        self.app.render({"msg": "update node %s" % res.get("uuid")})

    @ex(
        help="delete node",
        description="delete node",
        example="beehive ssh nodes delete <uuid>;beehive ssh nodes delete <uuid>",
        arguments=ARGS([(["id"], {"help": "node name or uuid", "action": "store", "type": str})]),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = "%s/nodes/%s" % (self.baseuri, oid)
        self.cmp_delete(uri, entity="node %s" % oid)

    @ex(
        help="set node ssh gateway. Use to access node with private address",
        description="set node ssh gateway. Use to access node with private address",
        arguments=ARGS(
            [
                (["id"], {"help": "node name or uuid", "action": "store", "type": str}),
                (["node"], {"help": "gateway node id", "action": "store", "type": str}),
            ]
        ),
    )
    def gateway_set(self):
        oid = self.app.pargs.id
        node = self.app.pargs.node
        data = {"attribute": dumps({"gateway": node})}
        uri = "%s/nodes/%s" % (self.baseuri, oid)
        res = self.cmp_put(uri, data={"node": data})
        self.app.render({"msg": "update node %s" % res.get("uuid")})

    @ex(
        help="open ssh connection to node",
        description="open ssh connection to node",
        example="beehive ssh nodes connect ###.###.###.###;beehive ssh nodes connect dbs-gamopera-prd-001p.site03.nivolapiemonte.it",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "node group name or uuid", "action": "store", "type": str},
                ),
                (
                    ["-user"],
                    {
                        "help": "node user name, if set use this username",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (["-pwd"], {"help": "if set request password", "action": "store_true"}),
            ]
        ),
    )
    def connect(self):
        oid = self.app.pargs.id
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd

        if pwd is True:
            passwd = getpass()
        else:
            passwd = None

        scm = SshConnectionManager(self)
        data = self.parse_node_id(oid)
        data["user"] = user
        data["passwd"] = passwd
        scm.ssh2node(**data)

    def __node_run_cmd(self, scm: SshConnectionManager, node: dict, user, cmd, timeout=30):
        """[DEPRECATED]"""
        self.app.print("[%s@%s]$ %s" % (user, node["name"], cmd), color="GRAY")
        try:
            res = scm.sshcmd2node(node=node, user="root", cmd=cmd, timeout=timeout)
        except Exception as ex:
            res = {"stderr": str(ex)}

        error = res.get("stderr", "")
        output = res.get("stdout", [])
        if error != "":
            self.app.error(error)
            status = False
        else:
            status = True

        if len(output) > 0:
            self.app.print("\n".join(output))

        return status

    def __node_run_cmds(self, scm: SshConnectionManager, node: dict, user, cmds, timeout=30):
        """[DEPRECATED]"""
        for cmd in cmds:
            status = self.__node_run_cmd(scm, node, user, cmd, timeout=timeout)
            if status is False:
                break

    @ex(
        help="execute command(s) on node",
        description="execute command(s) on node",
        example="beehive ssh nodes cmd $NODE.$ZONE commands;beehive ssh nodes cmd <uuid> script-ssh-test.sh -e <env>",
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": "node group name or uuid", "action": "store", "type": str},
                ),
                (["cmd"], {"help": "file with shell command script", "type": str}),
                (
                    ["-user"],
                    {
                        "help": "node user name",
                        "action": "store",
                        "type": str,
                        "default": "root",
                    },
                ),
            ]
        ),
    )
    def cmd(self):
        oid = self.app.pargs.id
        cmd = self.app.pargs.cmd
        user = self.app.pargs.user
        scm = SshConnectionManager(self)
        uri = "%s/nodes/%s" % (self.baseuri, oid)
        node = self.cmp_get(uri).get("node", {})

        cmds = load_config(cmd).split("\n")
        timeout = None
        self.__node_run_cmds(scm, node, user, cmds, timeout=timeout)

        # for cmd in cmds:
        #     res = scm.sshcmd2node(node=node, user=user, cmd=cmd)
        #     self.c('cmd: %s' % cmd, 'underline')
        #     if len(res['stdout']) > 0:
        #         print('\n'.join(res['stdout']))
        #     if res['stderr'] != '':
        #         self.app.error(res['stderr'])
        #         break

    @ex(
        help="get node admin user password",
        description="get node admin user password",
        example="beehive ssh nodes admin-password-get <uuid>;beehive ssh nodes admin-password-get ",
        arguments=PARGS(
            [
                (["id"], {"help": "node id", "action": "store", "type": str}),
                (
                    ["-admin"],
                    {
                        "help": "node admin name [default=root]",
                        "action": "store",
                        "type": str,
                        "default": "root",
                    },
                ),
            ]
        ),
    )
    def admin_password_get(self):
        oid = self.app.pargs.id
        admin = self.app.pargs.admin

        uri = "%s/nodes/%s" % (self.baseuri, oid)
        res = self.cmp_get(uri).get("node")
        users = [u for u in res.pop("users", []) if u["name"] == admin]

        if len(users) > 0:
            uri = "%s/users/%s/password" % (self.baseuri, users[0]["id"])
            res = self.cmp_get(uri).get("password", None)
            self.app.render({"msg": "get node %s user %s password: %s" % (oid, admin, res)})

    @ex(
        help="set node admin user password",
        description="set node admin user password",
        arguments=ARGS(
            [
                (["id"], {"help": "node id", "action": "store", "type": str}),
                (["pwd"], {"help": "user password", "action": "store", "type": str}),
                (
                    ["-admin"],
                    {
                        "help": "node admin name [default=root]",
                        "action": "store",
                        "type": str,
                        "default": "root",
                    },
                ),
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
    def admin_password_set(self):
        oid = self.app.pargs.id
        pwd = self.app.pargs.pwd
        admin = self.app.pargs.admin
        propagate = str2bool(self.app.pargs.propagate)

        uri = "%s/nodes/%s" % (self.baseuri, oid)
        res = self.cmp_get(uri).get("node")
        users = [u for u in res.pop("users", []) if u["name"] == admin]

        if len(users) > 0:
            # add user using paramiko
            # enc_pwd = sha512_crypt.using(rounds=5000).hash(pwd)
            if propagate is True:
                res = self.run_cmd('echo -e "%s\n%s" | passwd %s' % (pwd, pwd, admin), node=oid).values()
                self.app.log.debug(res)

            "/usr/sbin/usermod --password $(echo '%s' | openssl passwd -1 -stdin) ubuntu"

            # remove user via api
            data = {"user": {"password": pwd}}
            uri = "%s/users/%s" % (self.baseuri, users[0]["id"])
            self.cmp_put(uri, data=data)
            self.app.render({"msg": "set node %s user %s password" % (oid, admin)})

    @ex(
        help="set node user password",
        description="set node user password",
        example="beehive ssh nodes user-password-set",
        arguments=ARGS(
            [
                (["id"], {"help": "node id", "action": "store", "type": str}),
                (["pwd"], {"help": "user password", "action": "store", "type": str}),
                (
                    ["-user"],
                    {
                        "help": "node admin name [default=root]",
                        "action": "store",
                        "type": str,
                        "default": "ubuntu",
                    },
                ),
                (
                    ["-store"],
                    {
                        "help": "store password in cmp",
                        "action": "store",
                        "type": str,
                        "default": "false",
                    },
                ),
                (
                    ["-so"],
                    {
                        "help": "operating system",
                        "action": "store",
                        "type": str,
                        "default": "ubuntu",
                    },
                ),
            ]
        ),
    )
    def user_password_set(self):
        oid = self.app.pargs.id
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        store = str2bool(self.app.pargs.store)
        so = self.app.pargs.so

        if so == "centos":
            res = self.run_cmd('echo -e "%s\n%s" | passwd %s' % (pwd, pwd, user), node=oid).values()
            self.app.log.debug(res)
        elif so == "ubuntu":
            cmd = "/usr/sbin/usermod --password $(echo '%s' | openssl passwd -1 -stdin) %s" % (pwd, user)
            res = self.run_cmd(cmd, node=oid).values()
            self.app.log.debug(res)


class SshNodeAuthController(SshControllerChild):
    class Meta:
        label = "nodes_auth"
        description = "manage node authorization"
        help = "manage node authorization"

    @ex(
        help="get node roles",
        description="get node roles",
        example="beehive ssh nodes-auth role-get <uuid>;beehive ssh nodes-auth role-get <uuid>",
        arguments=ARGS([(["id"], {"help": "node name or uuid", "action": "store", "type": str})]),
    )
    def role_get(self):
        oid = self.app.pargs.id
        uri = "%s/nodes/%s/roles" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(res, key="roles", headers=["name", "desc"], maxsize=200)

    @ex(
        help="get node users",
        description="get node users",
        example="beehive ssh nodes-auth user-get;beehive ssh nodes-auth user-get <uuid>",
        arguments=ARGS([(["id"], {"help": "node name or uuid", "action": "store", "type": str})]),
    )
    def user_get(self):
        oid = self.app.pargs.id
        uri = "%s/nodes/%s/users" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="users",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            maxsize=200,
        )

    @ex(
        help="add node role to a user",
        description="add node role to a user",
        example="beehive ssh nodes-auth user-add <uuid> connect.root abd.def@ghi.lmn -e <env>;beehive ssh nodes-auth user-add <uuid> connect.root abc.def@ghi.lmno",
        arguments=ARGS(
            [
                (["id"], {"help": "node name or uuid", "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": "authorization role", "action": "store", "type": str},
                ),
                (
                    ["user"],
                    {"help": "authorization user", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = "%s/nodes/%s/users" % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="remove node role from a user",
        description="remove node role from a user",
        arguments=ARGS(
            [
                (["id"], {"help": "node name or uuid", "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": "authorization role", "action": "store", "type": str},
                ),
                (
                    ["user"],
                    {"help": "authorization user", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = "%s/nodes/%s/users" % (self.baseuri, oid)
        res = self.cmp_delete(uri, data, entity="role %s from user %s" % (role, user))
        self.app.render({"msg": res})

    @ex(
        help="get node groups",
        description="get node groups",
        example="beehive ssh nodes-auth group-get <uuid>;beehive ssh nodes-auth group-get <uuid>",
        arguments=ARGS([(["id"], {"help": "node name or uuid", "action": "store", "type": str})]),
    )
    def group_get(self):
        oid = self.app.pargs.id
        uri = "%s/nodes/%s/groups" % (self.baseuri, oid)
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="groups",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            maxsize=200,
        )

    @ex(
        help="add node role to a group",
        description="add node role to a group",
        example="beehive ssh nodes-auth group-add <uuid> connect.root GR-sdptoolc-jv-sdpqueryapi;beehive ssh nodes-auth group-add <uuid> connect.root GR-sdptoolc-jv-sdpqueryapi",
        arguments=ARGS(
            [
                (["id"], {"help": "node name or uuid", "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": "authorization role", "action": "store", "type": str},
                ),
                (
                    ["group"],
                    {"help": "authorization group", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = "%s/nodes/%s/groups" % (self.baseuri, oid)
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help="remove node role from a group",
        description="remove node role from a group",
        arguments=ARGS(
            [
                (["id"], {"help": "node name or uuid", "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": "authorization role", "action": "store", "type": str},
                ),
                (
                    ["group"],
                    {"help": "authorization group", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = "%s/nodes/%s/groups" % (self.baseuri, oid)
        res = self.cmp_delete(uri, data, entity="role %s from group %s" % (role, group))
        self.app.render({"msg": res})


class SshNodeActionController(SshControllerChild):
    class Meta:
        label = "nodes_action"
        description = "manage node action"
        help = "manage node action"

        headers = [
            "id",
            "date",
            "user",
            "user-ip",
            "session-id",
            "action",
            "elapsed",
            "node-name",
            "node-user",
            "status",
        ]
        fields = [
            "id",
            "date",
            "user.user",
            "user.ip",
            "action_id",
            "action",
            "elapsed",
            "node_name",
            "node_user",
            "status",
        ]

    @ex(
        help="get nodes actions",
        description="get nodes actions",
        example="beehive ssh nodes-action get <uuid> -date 2021.05.04 -size 100;beehive ssh nodes-action get <uuid> -date 2021.04.31 -size -1",
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": "node name or uuid",
                        "action": "store",
                        "type": str,
                        "default": "any",
                    },
                ),
                (
                    ["-date"],
                    {
                        "help": "date to. Syntax YYYY.MM.DD",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        node = self.app.pargs.id
        params = ["date"]
        mappings = {}
        data = self.format_paginated_query(params, mappings=mappings)
        uri = "%s/nodes/%s/actions" % (self.baseuri, node)
        res = self.cmp_get(uri, data=data)
        self.app.render(res, key="actions", headers=self._meta.headers, fields=self._meta.fields)


class SshNodeFileController(SshControllerChild):
    class Meta:
        label = "nodes_files"
        # aliases = ['files']
        # aliases_only = True
        # stacked_on = 'nodes'
        # stacked_type = 'nested'
        description = "Manage connection manager node files"
        help = "Manage connection manager node files"

    @ex(
        help="copy file to node",
        description="copy file to node",
        example="beehive ssh nodes-files put dbs-reflex-prd-001m.site01.nivolapiemonte.it /home/DOMNT/2067/indire/filebeat.yml /etc/filebeat/filebeat.yml;beehive ssh nodes-files put <uuid> /home/DOMNT/2067/esenzione/filebeat.yml /etc/filebeat/filebeat.yml",
        arguments=ARGS(
            [
                (["id"], {"help": "node uuid", "action": "store", "type": str}),
                (
                    ["-user"],
                    {
                        "help": "connection user [default=root]",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["local_file"],
                    {
                        "help": "full path of local file to copy to node",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["remote_file"],
                    {"help": "ull path of remote file", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def put(self):
        oid = self.app.pargs.id
        local_file = self.app.pargs.local_file
        remote_file = self.app.pargs.remote_file
        user = self.app.pargs.user
        uri = "%s/nodes/%s" % (self.baseuri, oid)
        node = self.cmp_get(uri).get("node", {})
        scm = SshConnectionManager(self)
        scm.sshfile2node(node=node, user=user, cmd="put", source=local_file, dest=remote_file)

    @ex(
        help="copy file from node",
        description="copy file from node",
        example="beehive ssh nodes-files get w22-gw-apimint.site01.nivolapiemonte.it /appserv/wso2carbon/apim-gateway/wso2am-4.1.0/repository/logs/CSI_audit-08-30-2023.log /home/DOMNT/2067/3/2/CSI_audit-08-30-2023.log;beehive ssh nodes-files get jb2-esenzione.site01.nivolapiemonte.it /etc/filebeat/filebeat.yml /home/DOMNT/2067/esenzione/filebeat.yml",
        arguments=ARGS(
            [
                (["id"], {"help": "node uuid", "action": "store", "type": str}),
                (
                    ["-user"],
                    {
                        "help": "connection user [default=root]",
                        "action": "store",
                        "type": str,
                        "default": "root",
                    },
                ),
                (
                    ["local_file"],
                    {
                        "help": "full path of local file to copy to node",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["remote_file"],
                    {"help": "ull path of remote file", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def get(self):
        oid = self.app.pargs.id
        local_file = self.app.pargs.local_file
        remote_file = self.app.pargs.remote_file
        user = self.app.pargs.user
        uri = "%s/nodes/%s" % (self.baseuri, oid)
        node = self.cmp_get(uri).get("node", {})
        scm = SshConnectionManager(self)
        scm.sshfile2node(node=node, user=user, cmd="get", source=local_file, dest=remote_file)

    @ex(
        help="list file in a directory. Return : st_size, st_uid, st_gid, st_mode, st_atime, st_mtime",
        description="list file in a directory. Return : st_size, st_uid, st_gid, st_mode, st_atime, st_mtime",
        arguments=ARGS(
            [
                (["id"], {"help": "node uuid", "action": "store", "type": str}),
                (
                    ["-user"],
                    {
                        "help": "connection user [default=root]",
                        "action": "store",
                        "type": str,
                        "default": "root",
                    },
                ),
                (
                    ["path"],
                    {
                        "help": "full path of remote file or dir to list",
                        "action": "store",
                        "type": str,
                    },
                ),
            ]
        ),
    )
    def ll(self):
        oid = self.app.pargs.id
        path = self.app.pargs.path
        user = self.app.pargs.user
        uri = "%s/nodes/%s" % (self.baseuri, oid)
        node = self.cmp_get(uri).get("node", {})
        scm = SshConnectionManager(self)
        res = scm.sshfile2node(node=node, user=user, cmd="list", source=path)
        for item in res:
            print(item)

    @ex(
        help="tail -f a file o the node",
        description="tail -f a file o the node",
        arguments=ARGS(
            [
                (["id"], {"help": "node uuid", "action": "store", "type": str}),
                (
                    ["-user"],
                    {
                        "help": "connection user [default=root]",
                        "action": "store",
                        "type": str,
                        "default": "root",
                    },
                ),
                (
                    ["file"],
                    {"help": "name of file to tail", "action": "store", "type": str},
                ),
            ]
        ),
    )
    def tailf(self):
        oid = self.app.pargs.id
        file = self.app.pargs.file
        user = self.app.pargs.user
        uri = "%s/nodes/%s" % (self.baseuri, oid)
        node = self.cmp_get(uri).get("node", {})
        scm = SshConnectionManager(self)
        scm.open_sshnode_file(node=node, user=user, filename=file)


class SshNodeAnsibleController(SshControllerChild):
    class Meta:
        label = "nodes_ansible"
        description = "Manage node ansible inventory"
        help = "Manage node ansible inventory"

    @ex(
        help="get inventory",
        description="get inventory",
        example="beehive ssh nodes-ansible inventory-get",
        arguments=ARGS(
            [
                (
                    ["-node_name"],
                    {
                        "help": "node name pattern",
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
                (
                    ["-group"],
                    {
                        "help": "group uuid or name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def inventory_get(self):
        node_name = self.app.pargs.node_name
        node = self.app.pargs.node
        group = self.app.pargs.group
        res = self.get_ansible_inventory(group=group, node=node, node_name=node_name)
        print(dumps(res))
