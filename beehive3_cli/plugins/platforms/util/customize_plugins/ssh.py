# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from base64 import b64encode

from beecell.util import ensure_binary
from beecell.types.type_dict import dict_get
from beehive3_cli.plugins.platforms.util.customize_plugins import CustomizePlugin


class SshCustomizePlugin(CustomizePlugin):
    def __init__(self, manager):
        super().__init__(manager)

        manager.controller._meta.cmp = {"baseuri": "/v1.0/gas", "subsystem": "ssh"}
        manager.controller.configure_cmp_api_client()

    def __create_groups(self, configs):
        if self.has_config(configs, "ssh.groups") is False:
            return

        self.write("##### SSH NODEGROUPS")
        base_uri = "/v1.0/gas/groups"

        for obj in dict_get(configs, "ssh.groups"):
            group_uri = f"{base_uri}/{obj['name']}"

            name = obj["name"]
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])

            exists = self.cmp_exists(group_uri, f"Nodegroup {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"group": obj}, f"Add nodegroup: {name}")

            for info in users:
                user, role = info
                data = {"user": {"user_id": users, "role": role}}
                self.cmp_put(
                    group_uri + "/users",
                    data,
                    f"Set nodegroup {name} role {role} to user {user}",
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": users, "role": role}}
                self.cmp_put(
                    group_uri + "/groups",
                    data,
                    f"Set nodegroup {name} role {role} to group {group}",
                )

    def __create_keys(self, configs):
        if self.has_config(configs, "ssh.keys") is False:
            return

        self.write("##### SSH KEYS")
        base_uri = "/v1.0/gas/keys"

        for obj in dict_get(configs, "ssh.keys"):
            group_uri = f"{base_uri}/{obj['name']}"

            name = obj["name"]
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])

            exists = self.cmp_exists(group_uri, f"Key {name} already exists")

            if not exists:
                obj["priv_key"] = b64encode(ensure_binary(obj["priv_key"]))
                # obj['priv_key'] = b64encode(read_file(obj['priv_key']))
                if obj["pub_key"] is not None:
                    obj["pub_key"] = b64encode(ensure_binary(obj["pub_key"]))
                    # obj['pub_key'] = b64encode(read_file(obj['pub_key']))
                else:
                    obj["pub_key"] = ""
                self.cmp_post(base_uri, {"key": obj}, f"Add key: {name}")

            for info in users:
                user, role = info
                data = {"user": {"user_id": users, "role": role}}
                self.cmp_put(
                    group_uri + "/users",
                    data,
                    f"Set key {name} role {role} to user {user}",
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": users, "role": role}}
                self.cmp_put(
                    group_uri + "/groups",
                    data,
                    f"Set key {name} role {role} to group {group}",
                )

    def __create_nodes(self, configs):
        if self.has_config(configs, "ssh.nodes") is False:
            return

        self.write("##### SSH NODEGROUPS")
        base_uri = "/v1.0/gas/nodes"
        nodeuser_uri = "/v1.0/gas/users"

        for obj in dict_get(configs, "ssh.nodes"):
            node_uri = f"{base_uri}/{obj['name']}"

            name = obj["name"]
            nodeusers = obj.pop("users", [])
            nodegroups = obj.pop("other_groups", [])
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])

            exists = self.cmp_exists(node_uri, f"Node {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"node": obj}, f"Add node: {name}")

            for user in nodeusers:
                user["name"] = f"{obj['name']}-{user['username']}"
                user["node_id"] = obj["name"]
                exists = self.cmp_exists(
                    nodeuser_uri + "/" + user["name"],
                    f"Node user {user['name']} already exists",
                )
                if not exists:
                    self.cmp_post(
                        nodeuser_uri,
                        {"user": user},
                        f"Add node {name} nodeuser {user['username']}",
                    )

            for group in nodegroups:
                group_uri = f"/v1.0/gas/groups/{group}/node"
                self.cmp_put(
                    group_uri,
                    {"node": obj["name"]},
                    f"Add node {name} group {group}",
                )

            for info in users:
                user, role = info
                data = {"user": {"user_id": users, "role": role}}
                self.cmp_put(
                    group_uri + "/users",
                    data,
                    f"Set node {name} role {role} to user {user}",
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": users, "role": role}}
                self.cmp_put(
                    group_uri + "/groups",
                    data,
                    f"Set node {name} role {role} to group {group}",
                )

    def run(self, configs, dry=False):
        if dry:
            return

        self.__create_groups(configs)
        self.__create_keys(configs)
        self.__create_nodes(configs)
