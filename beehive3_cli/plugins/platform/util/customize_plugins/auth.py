# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beecell.types.type_dict import dict_get
from beehive3_cli.plugins.platform.util.customize_plugins import CustomizePlugin


class AuthCustomizePlugin(CustomizePlugin):
    def __init__(self, manager):
        super().__init__(manager)

        manager.controller._meta.cmp = {"baseuri": "/v1.0/nas", "subsystem": "auth"}
        manager.controller.configure_cmp_api_client()

    def __create_roles(self, configs):
        if self.has_config(configs, "auth.roles") is False:
            return None

        self.write("##### AUTH ROLES")
        BASE_URI = "/v1.0/nas/roles"

        for obj in dict_get(configs, "auth.roles"):
            ROLE_URI = "%s/%s" % (BASE_URI, obj["name"])

            name = obj["name"]
            perms = obj.pop("perms", {})
            perms_add = dict_get(perms, "add")
            perms_del = dict_get(perms, "del")

            exists = self.cmp_exists(ROLE_URI, "Role %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"role": obj}, "Add role: %s" % name)

            if perms_add is not None:
                data = {"role": {"perms": {"append": perms_add}}}
                self.cmp_put(ROLE_URI, data, "Add role %s perms: %s" % (name, perms_add))
            if perms_del is not None:
                data = {"role": {"perms": {"remove": perms_add}}}
                self.cmp_put(ROLE_URI, data, "Delete role %s perms: %s" % (name, perms_del))

    def __create_users(self, configs):
        if self.has_config(configs, "auth.users") is False:
            return None

        self.write("##### AUTH USERS")
        BASE_URI = "/v1.0/nas/users"

        for obj in dict_get(configs, "auth.users"):
            USER_URI = "%s/%s" % (BASE_URI, obj["name"])

            name = obj["name"]
            roles = obj.pop("roles", [])

            exists = self.cmp_exists(USER_URI, "User %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"user": obj}, "Add user: %s" % name)

            data = {
                "roles": {"append": roles, "remove": []},
                "desc": obj.get("desc"),
                "password": obj.get("password"),
                # 'expirydate': obj.get('expirydate'),
                "active": obj.get("active"),
            }
            self.cmp_put(USER_URI, {"user": data}, "Update user: %s" % name)

    def __create_groups(self, configs):
        if self.has_config(configs, "auth.groups") is False:
            return None

        self.write("##### AUTH GROUPS")
        BASE_URI = "/v1.0/nas/groups"

        for obj in dict_get(configs, "auth.groups"):
            USER_URI = "%s/%s" % (BASE_URI, obj["name"])

            name = obj["name"]
            roles = obj.pop("roles", [])
            users = obj.pop("users", [])

            exists = self.cmp_exists(USER_URI, "User %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"group": obj}, "Add group: %s" % name)

            data = {
                "roles": {"append": roles, "remove": []},
                "users": {"append": users, "remove": []},
            }
            self.cmp_put(USER_URI, {"group": data}, "Update group: %s" % name)

    def __create_schedules(self, configs):
        if self.has_config(configs, "auth.schedules") is False:
            return None

        self.write("##### AUTH SCHEDULES")
        BASE_URI = "/v1.0/nas/scheduler/entries"

        for obj in dict_get(configs, "auth.schedules"):
            name = obj["name"]
            res = self.cmp_post(BASE_URI, {"schedule": obj}, "Add schedule: %s" % name)

    def __create_oauth2(self, configs):
        if self.has_config(configs, "oauth2.scopes") is False and self.has_config(configs, "oauth2.clients") is False:
            return None

        self.write("##### OAUTH2")
        BASE_URI = "/v1.0/oauth2"

        for obj in dict_get(configs, "oauth2.scopes"):
            name = obj["name"]
            SCOPE_URI = "%s/scopes/%s" % (BASE_URI, name)
            exists = self.cmp_exists(SCOPE_URI, "Scope %s already exists" % name)

            if exists is False:
                self.cmp_post("%s/scopes" % BASE_URI, {"scope": obj}, "Add scope: %s" % name)
        for obj in dict_get(configs, "oauth2.clients"):
            name = obj["name"]
            CLIENT_URI = "%s/clients/%s" % (BASE_URI, name)
            exists = self.cmp_exists(CLIENT_URI, "Client %s already exists" % name)

            if exists is False:
                self.cmp_post("%s/clients" % BASE_URI, {"client": obj}, "Add client: %s" % name)

    def run(self, configs):
        self.__create_roles(configs)
        self.__create_users(configs)
        self.__create_groups(configs)
        self.__create_schedules(configs)
        self.__create_oauth2(configs)
