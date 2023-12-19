# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from base64 import b64encode
from six import ensure_binary
from beecell.types.type_dict import dict_get
from beehive3_cli.plugins.platform.util.customize_plugins import CustomizePlugin


class SshCustomizePlugin(CustomizePlugin):
    def __init__(self, manager):
        super().__init__(manager)

        manager.controller._meta.cmp = {"baseuri": "/v1.0/gas", "subsystem": "ssh"}
        manager.controller.configure_cmp_api_client()

    def __create_groups(self, configs):
        if self.has_config(configs, "ssh.groups") is False:
            return None

        self.write("##### SSH NODEGROUPS")
        BASE_URI = "/v1.0/gas/groups"

        for obj in dict_get(configs, "ssh.groups"):
            GROUP_URI = "%s/%s" % (BASE_URI, obj["name"])

            name = obj["name"]
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])

            exists = self.cmp_exists(GROUP_URI, "Nodegroup %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"group": obj}, "Add nodegroup: %s" % name)

            for info in users:
                user, role = info
                data = {"user": {"user_id": users, "role": role}}
                self.cmp_put(
                    GROUP_URI + "/users",
                    data,
                    "Set nodegroup %s role %s to user %s" % (name, role, user),
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": users, "role": role}}
                self.cmp_put(
                    GROUP_URI + "/groups",
                    data,
                    "Set nodegroup %s role %s to group %s" % (name, role, group),
                )

    def __create_keys(self, configs):
        if self.has_config(configs, "ssh.keys") is False:
            return None

        self.write("##### SSH KEYS")
        BASE_URI = "/v1.0/gas/keys"

        for obj in dict_get(configs, "ssh.keys"):
            GROUP_URI = "%s/%s" % (BASE_URI, obj["name"])

            name = obj["name"]
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])

            exists = self.cmp_exists(GROUP_URI, "Key %s already exists" % name)

            if exists is False:
                obj["priv_key"] = b64encode(ensure_binary(obj["priv_key"]))
                # obj['priv_key'] = b64encode(read_file(obj['priv_key']))
                if obj["pub_key"] is not None:
                    obj["pub_key"] = b64encode(ensure_binary(obj["pub_key"]))
                    # obj['pub_key'] = b64encode(read_file(obj['pub_key']))
                else:
                    obj["pub_key"] = ""
                self.cmp_post(BASE_URI, {"key": obj}, "Add key: %s" % name)

            for info in users:
                user, role = info
                data = {"user": {"user_id": users, "role": role}}
                self.cmp_put(
                    GROUP_URI + "/users",
                    data,
                    "Set key %s role %s to user %s" % (name, role, user),
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": users, "role": role}}
                self.cmp_put(
                    GROUP_URI + "/groups",
                    data,
                    "Set key %s role %s to group %s" % (name, role, group),
                )

    def __create_nodes(self, configs):
        if self.has_config(configs, "ssh.nodes") is False:
            return None

        self.write("##### SSH NODEGROUPS")
        BASE_URI = "/v1.0/gas/nodes"
        NODEUSER_URI = "/v1.0/gas/users"

        for obj in dict_get(configs, "ssh.nodes"):
            NODE_URI = "%s/%s" % (BASE_URI, obj["name"])

            name = obj["name"]
            nodeusers = obj.pop("users", [])
            nodegroups = obj.pop("other_groups", [])
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])

            exists = self.cmp_exists(NODE_URI, "Node %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"node": obj}, "Add node: %s" % name)

            for user in nodeusers:
                user["name"] = "%s-%s" % (obj["name"], user["username"])
                user["node_id"] = obj["name"]
                exists = self.cmp_exists(
                    NODEUSER_URI + "/" + user["name"],
                    "Node user %s already exists" % user["name"],
                )
                if exists is False:
                    self.cmp_post(
                        NODEUSER_URI,
                        {"user": user},
                        "Add node %s nodeuser %s" % (name, user["username"]),
                    )

            for group in nodegroups:
                GROUP_URI = "/v1.0/gas/groups/%s/node" % group
                self.cmp_put(
                    GROUP_URI,
                    {"node": obj["name"]},
                    "Add node %s group %s" % (name, group),
                )

            for info in users:
                user, role = info
                data = {"user": {"user_id": users, "role": role}}
                self.cmp_put(
                    GROUP_URI + "/users",
                    data,
                    "Set node %s role %s to user %s" % (name, role, user),
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": users, "role": role}}
                self.cmp_put(
                    GROUP_URI + "/groups",
                    data,
                    "Set node %s role %s to group %s" % (name, role, group),
                )

    def run(self, configs):
        self.__create_groups(configs)
        self.__create_keys(configs)
        self.__create_nodes(configs)
