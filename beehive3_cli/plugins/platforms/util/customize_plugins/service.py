# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from beecell.types.type_dict import dict_get
from beehive3_cli.plugins.platforms.util.customize_plugins import CustomizePlugin


class ServiceCustomizePlugin(CustomizePlugin):
    def __init__(self, manager):
        super().__init__(manager)

        manager.controller._meta.cmp = {"baseuri": "/v1.0/nws", "subsystem": "service"}
        manager.controller.configure_cmp_api_client()

    def __create_service_types(self, configs):
        if not self.has_config(configs, "service.types"):
            return

        self.write("##### SERVICE TYPES")
        base_uri = "/v1.0/nws/servicetypes"

        for obj in dict_get(configs, "service.types"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            exists = self.cmp_exists(obj_uri, f"Service type {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"servicetype": obj}, f"Add service type: {name}")

    def __create_service_definitions(self, configs, dry=False):
        if not self.has_config(configs, "service.definitions"):
            return

        self.write("##### SERVICE DEFINITIONS")
        base_uri = "/v1.0/nws/servicedefs"

        for obj in dict_get(configs, "service.definitions"):
            print("-----")
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            def_configs = obj.pop("configs", {})

            msg = f"Service definition '{name}' already exists"
            # exists = self.cmp_exists(obj_uri, msg)

            exists = None
            try:
                res_servicedef = self.manager.controller.cmp_get(obj_uri, data="")
                # print("res_servicedef: %s" % res_servicedef)
                servicedef = res_servicedef.get("servicedef")
                self.error(msg)
                exists = True
            except:
                exists = False

            # print("exists: %s" % exists)
            if not exists:
                if not dry:
                    res = self.cmp_post(base_uri, {"servicedef": obj}, f"Add service definition: {name}")

                    data = {
                        "name": f"{name}-config",
                        "desc": f"{name}-config",
                        "service_definition_id": res["uuid"],
                        "params": def_configs,
                        "params_type": "JSON",
                        "version": obj.get("version"),
                    }
                    msg = f"Add service definition config {name}-config"
                    self.cmp_post("/v1.0/nws/servicecfgs", {"servicecfg": data}, msg)
                else:
                    print(f"Service definition: {name} to add")
            else:
                if not dry:
                    data = {"desc": obj["desc"], "status": "ACTIVE"}
                    self.cmp_put(
                        f"/v1.0/nws/servicedefs/{name}", {"servicedef": data}, "Update service definition description"
                    )

                # get service definition config
                id_servicedef = servicedef.get("id")
                # print("id_servicedef: %s" % id_servicedef)

                uri = "/v1.0/nws/servicecfgs"
                res = self.cmp_get(uri, data=f"service_definition_id={id_servicedef}").get("servicecfgs", [{}])[0]
                id_servicecfg = res.pop("id")
                params = res.pop("params")

                # print("type params: \n%s" % type(params))
                # print("type def_configs: \n%s" % type(def_configs))
                if params == def_configs:
                    print(f"Definition config {name}-config not changed")
                else:
                    print(f"Updating definition config {name}-config...")

                    print(f"OLD config: \n{params}")
                    print(f"NEW config: \n{def_configs}")

                    if dry is False:
                        confirm = self.manager.controller.confirm(msg="You are about to change config. Continue?")
                        if confirm:
                            # update service definition config
                            data_servicecfgs = {
                                "name": f"{name}-config",
                                "desc": f"{name}-config",
                                "service_definition_id": servicedef["uuid"],
                                "params": def_configs,
                                "params_type": "JSON",
                                "version": obj.get("version"),
                            }
                            # print("data_servicecfgs: %s" % data_servicecfgs)

                            msg = f"Update service definition config {name}-config"
                            self.cmp_put(
                                f"/v1.0/nws/servicecfgs/{id_servicecfg}", {"servicecfg": data_servicecfgs}, msg
                            )

    def __create_service_capabilities(self, configs, dry=False):
        if self.has_config(configs, "service.capabilities") is False:
            return

        self.write("##### SERVICE CAPABILITIES")
        base_uri = "/v1.0/nws/capabilities"

        for obj in dict_get(configs, "service.capabilities"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            print("-----")
            # print(f"capability {name}")

            # exists = self.cmp_exists(obj_uri, "Service capability %s already exists" % name)
            exists = None
            try:
                res_capability = self.manager.controller.cmp_get(obj_uri, data="")
                # print("res_capability: %s" % res_capability)
                capability = res_capability.get("capability")
                params = capability.get("params")
                self.error(f"Service capability {name} already exists")
                exists = True
            except:
                exists = False

            if not exists:
                self.cmp_post(base_uri, {"capability": obj}, f"Add service capability: {name}")
            else:
                params_obj = {
                    "account_type": obj.get("account_type"),
                    "pods": obj.get("pods"),
                }
                if obj.get("definitions") is not None:
                    params_obj.update({"definitions": obj.get("definitions")})
                if obj.get("services") is not None:
                    params_obj.update({"services": obj.get("services")})

                found_changes = False
                try:
                    from dictdiffer import diff

                    result = diff(params, params_obj)
                    list_compare = list(result)
                    if list_compare is None or len(list_compare) == 0:
                        print("no changes")
                    else:
                        found_changes = True
                        print("changes: ")
                        for item_compare in list_compare:
                            print(f"{item_compare}")
                except ModuleNotFoundError:
                    found_changes = True

                if found_changes:
                    if not dry:
                        confirm = self.manager.controller.confirm(msg="You are about to change config. Continue?")
                        if confirm:
                            self.cmp_put(obj_uri, {"capability": obj}, f"Update service capability: {name}")

    def __create_service_processes(self, configs):
        if self.has_config(configs, "service.processes") is False:
            return

        self.write("##### SERVICE PROCESSES")
        base_uri = "/v1.0/nws/serviceprocesses"

        for obj in dict_get(configs, "service.processes"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            exists = self.cmp_exists(obj_uri, f"Service process {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"process": obj}, f"Add service process: {name}")
            else:
                self.cmp_put(obj_uri, {"process": obj}, f"Update service process: {name}")

    def __create_service_tags(self, configs):
        if not self.has_config(configs, "service.tags"):
            return

        self.write("##### SERVICE TAGS")
        base_uri = "/v1.0/nws/tags"

        for obj in dict_get(configs, "service.tags"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            exists = self.cmp_exists(obj_uri, f"Service tag {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"tag": obj}, f"Add service tag: {name}")
            else:
                self.cmp_put(obj_uri, {"tag": obj}, f"Update service tag: {name}")

    def __create_service_catalogs(self, configs):
        if not self.has_config(configs, "service.catalogs"):
            return

        self.write("##### SERVICE CATALOGS")
        base_uri = "/v1.0/nws/srvcatalogs"

        for obj in dict_get(configs, "service.catalogs"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            defs = obj.pop("definitions", [])
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])
            exists = self.cmp_exists(obj_uri, f"Service tag {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"catalog": obj}, f"Add service catalog: {name}")
            else:
                self.cmp_put(obj_uri, {"catalog": obj}, f"Update service catalog: {name}")

            cat = self.cmp_get(obj_uri, "").get("catalog")

            msg = f"Add service catalog {name} definitions {defs}"
            self.cmp_put(
                f"/v1.0/nws/srvcatalogs/{cat['uuid']}/defs",
                {"definitions": {"oids": defs}},
                msg,
            )

            msg = f"Refresh service catalog {name}"
            self.cmp_patch(f"/v1.0/nws/srvcatalogs/{cat['uuid']}", {"catalog": {}}, msg)

            for info in users:
                user, role = info
                data = {"user": {"user_id": user, "role": role}}
                self.cmp_post(
                    obj_uri + "/users",
                    data,
                    f"Set catalog {name} role {role} to user {user}",
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": group, "role": role}}
                self.cmp_post(
                    obj_uri + "/groups",
                    data,
                    f"Set catalog {name} role {role} to group {group}",
                )

    def __create_organizations(self, configs):
        if not self.has_config(configs, "authority.organizations"):
            return

        self.write("##### AUTHORITY ORGANIZATIONS")
        base_uri = "/v1.0/nws/organizations"

        for obj in dict_get(configs, "authority.organizations"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])
            exists = self.cmp_exists(obj_uri, f"Organizations {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"organization": obj}, f"Add organization: {name}")
            else:
                self.cmp_put(obj_uri, {"organization": obj}, f"Update organization: {name}")

            res = self.cmp_get(obj_uri, "")
            obj_uri = f"{base_uri}/{res['uuid']}"

            for info in users:
                user, role = info
                data = {"user": {"user_id": user, "role": role}}
                self.cmp_post(
                    obj_uri + "/users",
                    data,
                    f"Set organization {name} role {role} to user {user}",
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": group, "role": role}}
                self.cmp_post(
                    obj_uri + "/groups",
                    data,
                    f"Set organization {name} role {role} to group {group}",
                )

    def __create_divisions(self, configs):
        if not self.has_config(configs, "authority.divisions"):
            return

        self.write("##### AUTHORITY DIVISIONS")
        base_uri = "/v1.0/nws/divisions"

        for obj in dict_get(configs, "authority.divisions"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])
            exists = self.cmp_exists(obj_uri, f"Division {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"division": obj}, f"Add division: {name}")
            else:
                self.cmp_put(obj_uri, {"division": obj}, f"Update division: {name}")

            res = self.cmp_get(obj_uri, "")
            obj_uri = f"{base_uri}/{res['uuid']}"

            for info in users:
                user, role = info
                data = {"user": {"user_id": user, "role": role}}
                self.cmp_post(
                    obj_uri + "/users",
                    data,
                    f"Set division {name} role {role} to user {user}",
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": group, "role": role}}
                self.cmp_post(
                    obj_uri + "/groups",
                    data,
                    f"Set division {name} role {role} to group {group}",
                )

    def __create_accounts(self, configs):
        if self.has_config(configs, "authority.accounts") is False:
            return

        self.write("##### AUTHORITY ACCOUNTS")
        base_uri = "/v1.0/nws/accounts"

        for obj in dict_get(configs, "authority.accounts"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])
            exists = self.cmp_exists(obj_uri, f"Account {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"account": obj}, f"Add account: {name}")
            else:
                self.cmp_put(obj_uri, {"account": obj}, f"Update account: {name}")

            res = self.cmp_get(obj_uri, "")
            obj_uri = f"{base_uri}/{res['uuid']}"

            for info in users:
                user, role = info
                data = {"user": {"user_id": user, "role": role}}
                self.cmp_post(
                    obj_uri + "/users",
                    data,
                    f"Set account {name} role {role} to user {user}",
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": group, "role": role}}
                self.cmp_post(
                    obj_uri + "/groups",
                    data,
                    f"Set account {name} role {role} to group {group}",
                )

    def __create_metric_types(self, configs):
        if not self.has_config(configs, "authority.metric-types"):
            return

        self.write("##### AUTHORITY METRIC TYPES")
        base_uri = "/v1.0/nws/services/metricstypes"

        for obj in dict_get(configs, "authority.metric-types"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            exists = self.cmp_exists(obj_uri, f"Metric type {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"metric_type": obj}, f"Add metric type: {name}")

    def __create_metric_schedules(self, configs):
        if not self.has_config(configs, "authority.metric.schedules"):
            return

        self.write("##### AUTHORITY JOB SCHEDULE")
        base_uri = "/v1.0/nws/services/job_schedules"

        for obj in dict_get(configs, "authority.metric.schedules"):
            obj_uri = f"{base_uri}/{obj['name']}"
            name = obj["name"]
            exists = self.cmp_exists(obj_uri, f"Metric schedule {name} already exists")

            if not exists:
                self.cmp_post(base_uri, {"job_schedule": obj}, f"Add metric schedule: {name}")

    def run_types(self, configs, dry=False):
        if not dry:
            self.__create_service_types(configs)

    def run_definitions(self, configs, dry=False):
        if not dry:
            self.__create_service_definitions(configs, dry)

    def run_capabilities(self, configs, dry=False):
        if not dry:
            self.__create_service_capabilities(configs, dry)

    def run(self, configs, dry=False):
        self.__create_service_types(configs)
        self.__create_service_definitions(configs, dry)
        self.__create_service_capabilities(configs, dry)
        self.__create_service_processes(configs)
        self.__create_service_tags(configs)
        self.__create_service_catalogs(configs)
        self.__create_organizations(configs)
        self.__create_divisions(configs)
        self.__create_accounts(configs)
        self.__create_metric_types(configs)
        self.__create_metric_schedules(configs)
