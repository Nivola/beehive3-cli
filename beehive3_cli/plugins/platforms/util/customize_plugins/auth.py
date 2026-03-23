# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from beecell.types.type_dict import dict_get
from beehive3_cli.plugins.platforms.util.customize_plugins import CustomizePlugin


class AuthCustomizePlugin(CustomizePlugin):
    def __init__(self, manager):
        super().__init__(manager)

        manager.controller._meta.cmp = {"baseuri": "/v1.0/nas", "subsystem": "auth"}
        manager.controller.configure_cmp_api_client()

    def __create_roles(self, configs):
        if not self.has_config(configs, "auth.roles"):
            return

        self.write("##### AUTH ROLES")
        base_uri = "/v1.0/nas/roles"

        for obj in dict_get(configs, "auth.roles"):
            role_uri = f"{base_uri}/{obj['name']}"

            name = obj["name"]
            perms = obj.pop("perms", {})
            perms_add = dict_get(perms, "add")
            perms_del = dict_get(perms, "del")

            exists = self.cmp_exists(role_uri, f"Role {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"role": obj}, f"Add role: {name}")

            if perms_add is not None:
                data = {"role": {"perms": {"append": perms_add}}}
                self.cmp_put(role_uri, data, f"Add role {name} perms: {perms_add}")
            if perms_del is not None:
                data = {"role": {"perms": {"remove": perms_add}}}
                self.cmp_put(role_uri, data, f"Delete role {name} perms: {perms_del}")

    def __create_users(self, configs):
        if not self.has_config(configs, "auth.users"):
            return

        self.write("##### AUTH USERS")
        base_uri = "/v1.0/nas/users"

        for obj in dict_get(configs, "auth.users"):
            user_uri = f"{base_uri}/{obj['name']}"

            name = obj["name"]
            roles = obj.pop("roles", [])

            exists = self.cmp_exists(user_uri, f"User {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"user": obj}, f"Add user: {name}")

            data = {
                "roles": {"append": roles, "remove": []},
                "desc": obj.get("desc"),
                "password": obj.get("password"),
                # 'expirydate': obj.get('expirydate'),
                "active": obj.get("active"),
            }
            self.cmp_put(user_uri, {"user": data}, f"Update user: {name}")

    def __create_groups(self, configs):
        if not self.has_config(configs, "auth.groups"):
            return

        self.write("##### AUTH GROUPS")
        base_uri = "/v1.0/nas/groups"

        for obj in dict_get(configs, "auth.groups"):
            user_uri = f"{base_uri}/{obj['name']}"

            name = obj["name"]
            roles = obj.pop("roles", [])
            users = obj.pop("users", [])

            exists = self.cmp_exists(user_uri, f"User {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"group": obj}, f"Add group: {name}")

            data = {
                "roles": {"append": roles, "remove": []},
                "users": {"append": users, "remove": []},
            }
            self.cmp_put(user_uri, {"group": data}, f"Update group: {name}")

    def __create_schedules(self, configs):
        if self.has_config(configs, "auth.schedules") is False:
            return

        self.write("##### AUTH SCHEDULES")
        base_uri = "/v1.0/nas/scheduler/entries"

        for obj in dict_get(configs, "auth.schedules"):
            name = obj["name"]
            self.cmp_post(base_uri, {"schedule": obj}, f"Add schedule: {name}")

    def __create_oauth2(self, configs):
        if self.has_config(configs, "oauth2.scopes") is False and self.has_config(configs, "oauth2.clients") is False:
            return

        self.write("##### OAUTH2")
        base_uri = "/v1.0/oauth2"

        for obj in dict_get(configs, "oauth2.scopes"):
            name = obj["name"]
            scope_uri = f"{base_uri}/scopes/{name}"
            exists = self.cmp_exists(scope_uri, f"Scope {name} already exists")

            if not exists is False:
                self.cmp_post(f"{base_uri}/scopes", {"scope": obj}, f"Add scope: {name}")
        for obj in dict_get(configs, "oauth2.clients"):
            name = obj["name"]
            client_uri = f"{base_uri}/clients/{name}"
            exists = self.cmp_exists(client_uri, f"Client {name} already exists")

            if not exists is False:
                self.cmp_post("base_uri/clients", {"client": obj}, f"Add client: {name}")

    def run(self, configs, dry=False):
        if dry:
            return

        self.__create_roles(configs)
        self.__create_users(configs)
        self.__create_groups(configs)
        self.__create_schedules(configs)
        self.__create_oauth2(configs)
