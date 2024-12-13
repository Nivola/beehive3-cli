# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from os import environ
from re import match
from urllib.parse import urlencode
from beehive3_cli.core.connect import SshConnectionManager
from beehive3_cli.core.controller import CliController, BaseController
from beehive3_cli.core.util import load_environment_config


class SshController(CliController):
    class Meta:
        label = "ssh"
        stacked_on = "base"
        stacked_type = "nested"
        description = "server connection manager"
        help = "server connection manager"

    def _default(self):
        self._parser.print_help()


class SshControllerChild(BaseController):
    class Meta:
        stacked_on = "ssh"
        stacked_type = "nested"

        cmp = {"baseuri": "/v1.0/gas", "subsystem": "ssh"}

    def pre_command_run(self):
        super(SshControllerChild, self).pre_command_run()
        self.configure_cmp_api_client()

        environ["ANSIBLE_HOST_KEY_CHECKING"] = "False"
        self.ansible_path = self.app.config.get("beehive", "ansible_path")
        self.console_playbook = "%s/console.yml" % self.ansible_path

        self.verbosity = 0
        self.new_verbosity = getattr(self.app.pargs, "verbosity", None)
        if self.new_verbosity is not None:
            self.verbosity = int(self.new_verbosity)

        config = load_environment_config(self.app)

        # get vault
        self.vault = getattr(self.app.pargs, "vault", None)
        if self.vault is None:
            self.vault = config.get("cmp", {}).get("ansible_vault", None)

    def get_ansible_inventory(self, group=None, node=None, node_name=None):
        """Create an ansible inventory"""
        data = {}
        if group is not None:
            data["group"] = group
        if node is not None:
            data["node"] = node
        if node_name is not None:
            data["node_name"] = node_name
        uri = "%s/ansible" % self.baseuri
        res = self.cmp_get(uri, data=urlencode(data))
        inventory_dict = res.get("ansible")
        return inventory_dict

    def run_cmd(self, cmd, user="root", group=None, node=None):
        """Execute command on node

        :param cmd: shell command, Syntax: delimit command with \\'. Example: \\'ls -l\\', \\'netstat -nl\\|grep tcp\\'
        :param user: node user [defult=root]
        :param group: group [optional]
        :param node: node [optional]
        :return: {'stderr':.. 'stdout':..}
        """
        scm = SshConnectionManager(self)
        res = {}
        if group is not None:
            data = {"group_id": group}
            uri = "%s/nodes" % self.baseuri
            nodes = self.cmp_get(uri, data=urlencode(data)).get("nodes")
            for node in nodes:
                res[node["uuid"]] = scm.sshcmd2node(node=node, user=user, cmd=cmd)
        elif node is not None:
            uri = "%s/nodes/%s" % (self.baseuri, node)
            node = self.cmp_get(uri).get("node", {})
            res[node["uuid"]] = scm.sshcmd2node(node=node, user=user, cmd=cmd)

        return res

    def parse_node_id(self, node: str) -> dict:
        """Parse node passed and extract name or ip or uuid

        :return: dict like {'host_id': .., 'host_ip': .., 'host_name': ..}
        """
        host_id = None
        host_ip = None
        host_name = None

        # get obj by uuid
        if match("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", str(node)):
            host_id = node
        # get obj by ip
        elif match("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", str(node)):
            host_ip = node
        # get obj by name
        elif match("[\-\w\d]+", str(node)):
            host_name = node

        return {"host_id": host_id, "host_ip": host_ip, "host_name": host_name}
