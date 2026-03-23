# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex
from beehive3_cli.core.connect import SshConnectionManager
from beehive3_cli.core.controller import PARGS, ARGS, StringAction
from beehive3_cli.plugins.ssh.controllers.ssh import SshControllerChild
from beehive3_cli.translate import _


class SshGroupController(SshControllerChild):
    class Meta:
        stacked_on = "ssh"
        stacked_type = "nested"
        label = "node_groups"
        description = _("node group management")
        help = _("node group management")

        headers = ["id", "name", "desc", "date", "objid"]
        fields = ["uuid", "name", "desc", "date.creation", "__meta__.objid"]

    def pre_command_run(self):
        super().pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help=_("get node groups"),
        description=_("get node groups"),
        example="beehive ssh node-groups get -field NAME xxxx; beehive ssh node-groups get -e <env>",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("nodegroup uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/groups/{oid}"
            res = self.cmp_get(uri)
            self.app.render(res, key="group", details=True)
        else:
            params = []
            data = self.format_paginated_query(params)
            uri = f"{self.baseuri}/groups"
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="groups", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("add node group"),
        description=_("add node group"),
        example="beehive ssh node-groups add",
        arguments=ARGS(
            [
                (["name"], {"help": _("nodegroup name"), "action": "store", "type": str}),
                (
                    ["-desc"],
                    {
                        "help": _("nodegroup description"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-attrib"],
                    {
                        "help": _("nodegroup attributes"),
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
        desc = self.app.pargs.desc
        attribute = self.app.pargs.attrib
        data = {"group": {"name": name, "desc": desc, "attribute": attribute}}
        uri = f"{self.baseuri}/groups"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add nodegroup {res.get('uuid')}"})

    @ex(
        help=_("delete node group"),
        description=_("delete node group"),
        arguments=ARGS([(["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str})]),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/groups/{oid}"
        self.cmp_delete(uri, entity=f"nodegroup {oid}")

    @ex(
        help=_("add node to node group"),
        description=_("add node to node group"),
        example="beehive ssh node-groups node-add",
        arguments=ARGS(
            [
                (["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str}),
                (["node"], {"help": _("node uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def node_add(self):
        oid = self.app.pargs.id
        node = self.app.pargs.node
        data = {"node": node}
        uri = f"{self.baseuri}/groups/{oid}/node"
        self.cmp_put(uri, data=data)
        self.app.render({"msg": f"add node {node} to nodegroup {oid}"})

    @ex(
        help=_("delete node from node group"),
        description=_("delete node from node group"),
        arguments=ARGS(
            [
                (["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str}),
                (["node"], {"help": _("node uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def node_del(self):
        oid = self.app.pargs.id
        node = self.app.pargs.node
        data = {"node": node}
        uri = f"{self.baseuri}/groups/{oid}/node"
        self.cmp_delete(uri, data=data, entity=f"node {node} from nodegroup {oid}")


class SshGroupAuthController(SshControllerChild):
    class Meta:
        label = "node_groups_auth"
        description = _("manage node group authorization")
        help = _("manage node group authorization")

    def pre_command_run(self):
        super(SshControllerChild, self).pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help=_("get node group roles"),
        description=_("get node group roles"),
        arguments=ARGS([(["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str})]),
    )
    def role_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/groups/{oid}/roles"
        res = self.cmp_get(uri)
        self.app.render(res, key="roles", headers=["name", "desc"], maxsize=200)

    @ex(
        help=_("get node group users"),
        description=_("get node group users"),
        example="beehive ssh node-groups-auth user-get <uuid> -e <env>",
        arguments=ARGS([(["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str})]),
    )
    def user_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/groups/{oid}/users"
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="users",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            maxsize=200,
        )

    @ex(
        help=_("add node group role to a user"),
        description=_("add node group role to a user"),
        example="beehive ssh node-groups-auth user-add <uuid> <uuid> <uuid> -e <env>",
        arguments=ARGS(
            [
                (["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": _("authorization role"), "action": "store", "type": str},
                ),
                (
                    ["user"],
                    {"help": _("authorization user"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = f"{self.baseuri}/groups/{oid}/users"
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help=_("remove node group role from a user"),
        description=_("remove node group role from a user"),
        example="beehive ssh node-groups-auth user-del <uuid> connect 2021",
        arguments=ARGS(
            [
                (["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": _("authorization role"), "action": "store", "type": str},
                ),
                (
                    ["user"],
                    {"help": _("authorization user"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = f"{self.baseuri}/groups/{oid}/users"
        res = self.cmp_delete(uri, data, entity=f"role {role} from user {user}")
        self.app.render({"msg": res})

    @ex(
        help=_("get node group groups"),
        description=_("get node group groups"),
        example="beehive ssh node-groups-auth group-get <uuid>",
        arguments=ARGS([(["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str})]),
    )
    def group_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/groups/{oid}/groups"
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="groups",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            maxsize=200,
        )

    @ex(
        help=_("add node group role to a group"),
        description=_("add node group role to a group"),
        example="beehive ssh node-groups-auth group-add <uuid> connect GR-devops",
        arguments=ARGS(
            [
                (["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": _("authorization role"), "action": "store", "type": str},
                ),
                (
                    ["group"],
                    {"help": _("authorization group"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = f"{self.baseuri}/groups/{oid}/groups"
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help=_("remove node group role from a group"),
        description=_("remove node group role from a group"),
        example="beehive ssh node-groups-auth group-del <uuid> connect GR-sdptoolc-jv-sdpqueryapi",
        arguments=ARGS(
            [
                (["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": _("authorization role"), "action": "store", "type": str},
                ),
                (
                    ["group"],
                    {"help": _("authorization group"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = f"{self.baseuri}/groups/{oid}/groups"
        res = self.cmp_delete(uri, data, entity=f"role {role} from group {group}")
        self.app.render({"msg": res})


class SshGroupActionController(SshControllerChild):
    class Meta:
        label = "node_groups_action"
        # aliases = ['actions']
        # stacked_on = 'nodegroups'
        # stacked_type = 'nested'
        description = _("manage node group action")
        help = _("manage node group action")

        headers = [
            "id",
            "date",
            "user",
            "user-ip",
            "action-id",
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
            "node_user.name",
            "status",
        ]

    @ex(
        help=_("get node groups actions"),
        description=_("get node groups actions"),
        arguments=ARGS(
            [
                (
                    ["-node"],
                    {
                        "help": _("node filter"),
                        "action": "store",
                        "type": str,
                        "default": "*",
                    },
                ),
                (
                    ["-datefrom"],
                    {
                        "help": _("date from. Syntax dd-mm-yyyy"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-dateto"],
                    {
                        "help": _("date to. Syntax dd-mm-yyyy"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        node = self.app.pargs.node
        params = ["datefrom", "dateto"]
        mappings = {}
        data = self.format_paginated_query(params, mappings=mappings)
        uri = f"{self.baseuri}/nodes/{node}/actions"
        res = self.cmp_get(uri, data=data)
        self.app.render(res, key="actions", headers=self._meta.headers, fields=self._meta.fields)

    def __info(self, cmd, size=40, user="root"):
        """Get some info from the nodes"""
        oid = self.app.pargs.id
        data = self.format_paginated_query([])
        if oid is not None:
            data += f"&group_id={oid}"

        uri = f"{self.baseuri}/nodes"
        res = self.cmp_get(uri, data=data)

        # print paging
        if "page" in res:
            print(f"Page: {res['page']}")
            print(f"Count: {res['count']}")
            print(f"Total: {res['total']}")
            print(f"Order: {res.get('sort').get('field')} {res.get('sort').get('order')}")

        tmpl = "{uuid:36.36} {name:40.40} {desc:40.40} {ip_address:15.15} {info:%s.%s}" % (size, size)
        line = "".join(["-" for i in range(40)])
        headers = {
            "uuid": "id",
            "name": "name",
            "desc": "desc",
            "ip_address": "ip_address",
            "info": "info",
        }
        separators = {
            "uuid": line,
            "name": line,
            "desc": line,
            "ip_address": line,
            "info": line,
        }
        print(tmpl.format(**headers))
        print(tmpl.format(**separators))

        scm = SshConnectionManager(self)
        for item in res.get("nodes"):
            item["info"] = None
            try:
                info = scm.sshcmd2node(node=item, user=user, cmd=cmd, timeout=1)
                if len(info["stdout"]) > 0:
                    item["info"] = "\n".join(info["stdout"])
                    print(tmpl.format(**item))
                else:
                    self.app.log.warning(info["stderr"])
            except Exception as exc:
                self.app.log.warning(exc)

    @ex(
        help=_("get version of operating system"),
        description=_("get version of operating system"),
        arguments=PARGS([(["id"], {"help": _("node group uuid"), "action": "store", "type": str})]),
    )
    def sysinfo(self):
        self.__info("cat /etc/redhat-release")

    @ex(
        help=_("get version of the kernel"),
        description=_("get version of the kernel"),
        arguments=PARGS([(["id"], {"help": _("node group uuid"), "action": "store", "type": str})]),
    )
    def kernelinfo(self):
        self.__info("uname -sr")

    @ex(
        help=_("get uptime"),
        description=_("get uptime"),
        arguments=PARGS([(["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str})]),
    )
    def uptime(self):
        self.__info("uptime", size=40)

    @ex(
        help=_("get date"),
        description=_("get date"),
        arguments=PARGS([(["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str})]),
    )
    def date(self):
        self.__info("date", size=40)

    @ex(
        help=_("get ntpd status"),
        description=_("get ntpd status"),
        arguments=PARGS([(["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str})]),
    )
    def ntpd(self):
        self.__info("systemctl status ntpd |grep Active", size=60)

    @ex(
        help=_("ping nodes"),
        description=_("ping nodes"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("nodegroup uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def ping(self):
        import sh

        oid = self.app.pargs.id
        data = self.format_paginated_query([])
        if oid is not None:
            data += f"&group_id={oid}"

        uri = f"{self.baseuri}/nodes"
        res = self.cmp_get(uri, data=data)

        # print paging
        if "page" in res:
            print(f"Page: {res['page']}")
            print(f"Count: {res['count']}")
            print(f"Total: {res['total']}")
            print(f"Order: {res.get('sort').get('field')} {res.get('sort').get('order')}")

        tmpl = "{uuid:36.36} {name:40.40} {desc:40.40} {ip_address:15.15} {info:40.40}"
        line = "".join(["-" for i in range(40)])
        headers = {
            "uuid": "id",
            "name": "name",
            "desc": "desc",
            "ip_address": "ip_address",
            "info": "info",
        }
        separators = {
            "uuid": line,
            "name": line,
            "desc": line,
            "ip_address": line,
            "info": line,
        }
        print(tmpl.format(**headers))
        print(tmpl.format(**separators))
        for item in res.get("nodes"):
            if item["name"].find("site01") > 0:
                try:
                    info = sh.ping(item["ip_address"], "-c 3", "-qn", "-i 0.3", "-W 1")
                    if info.find("3 received") > 0:
                        item["info"] = self.app.color_error("OK")
                    else:
                        item["info"] = self.app.color_error("KO")
                except Exception as exception:
                    self.app.log.warning(exception)
                    item["info"] = self.app.color_error("KO")

                print(tmpl.format(**item))

    @ex(
        help=_("ultra ping nodes"),
        description=_("ultra ping nodes"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("nodegroup uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def ultra_ping(self):
        import sh

        oid = self.app.pargs.id
        data = self.format_paginated_query([])
        if oid is not None:
            data += f"&group_id={oid}"

        uri = f"{self.baseuri}/nodes"
        res = self.cmp_get(uri, data=data)

        # print paging
        if "page" in res:
            print(f"Page: {res['page']}")
            print(f"Count: {res['count']}")
            print(f"Total: {res['total']}")
            print(f"Order: {res.get('sort').get('field')} {res.get('sort').get('order')}")

        tmpl = "{uuid:36.36} {name:45.45} {desc:40.40} {ip_address:15.15} {info:40.40}"
        line = "".join(["-" for i in range(50)])
        headers = {
            "uuid": "id",
            "name": "name",
            "desc": "desc",
            "ip_address": "ip_address",
            "info": "info",
        }
        separators = {
            "uuid": line,
            "name": line,
            "desc": line,
            "ip_address": line,
            "info": line,
        }
        print(tmpl.format(**headers))
        print(tmpl.format(**separators))

        scm = SshConnectionManager(self)

        def check(node, name, cmd, response, user="root"):
            error = None
            try:
                info = scm.sshcmd2node(node=node, user=user, cmd=cmd, timeout=1)
                if len(info["stdout"]) > 0 and info["stdout"][0] == response:
                    self.app.log.debug(info)
                    res = True
                    msg.append(f"{name}: {self.app.color_error('OK')}")
                else:
                    self.app.log.warning(info)
                    res = False
                    error = info["stderr"]
                    msg.append(f"{name}: {self.app.color_error('KO')}")
            except Exception as exc:
                self.app.log.warning(exc)
                error = str(exc)
                res = False
                msg.append(f"{name}: {self.app.color_error('KO')}")

            return res, error

        for item in res.get("nodes"):
            msg = []
            error = None

            # ping node
            try:
                info = sh.ping(item["ip_address"], "-c 3", "-qn", "-i 0.3", "-W 1")
                if info.find("3 received") > 0:
                    res = True
                    msg.append("ping: " + self.app.color_error("OK"))
                else:
                    res = False
                    msg.append("ping: " + self.app.color_error("KO"))
            except Exception as exc:
                res = False
                self.app.log.warning(exc)
                msg.append("ping: " + self.app.color_error("KO"))

            # exec command on node
            if res is True:
                res, error = check(
                    item,
                    "touch",
                    "touch /tmp/xxxx && ls /tmp/xxxx && rm /tmp/xxxx",
                    "/tmp/xxxx",
                )

            item["info"] = " ".join(msg)

            if error is not None:
                error = error.replace("\n", "")
                print(tmpl.format(**item) + " - " + self.app.colored_text.output(str(error), "RED"))
            else:
                print(tmpl.format(**item))

    @ex(
        help=_("execute command on group of nodes"),
        description=_("execute command on group of nodes"),
        arguments=PARGS(
            [
                (["id"], {"help": _("nodegroup uuid"), "action": "store", "type": str}),
                (
                    ["cmd"],
                    {
                        "help": _(
                            "shell command, Syntax: delimit command with. Write /- when use - char. Example: ls /-l"
                        ),
                        "action": StringAction,
                        "type": str,
                        "nargs": "+",
                    },
                ),
                (
                    ["-user"],
                    {
                        "help": _("node user name"),
                        "action": "store",
                        "type": str,
                        "default": "root",
                    },
                ),
            ]
        ),
    )
    def cmd(self):
        cmd = self.app.pargs.cmd
        user = self.app.pargs.user
        self.__info(cmd, user=user)
