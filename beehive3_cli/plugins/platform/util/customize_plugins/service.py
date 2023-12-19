# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beecell.types.type_dict import dict_get
from beehive3_cli.plugins.platform.util.customize_plugins import CustomizePlugin


class ServiceCustomizePlugin(CustomizePlugin):
    def __init__(self, manager):
        super().__init__(manager)

        manager.controller._meta.cmp = {"baseuri": "/v1.0/nws", "subsystem": "service"}
        manager.controller.configure_cmp_api_client()

    def __create_service_types(self, configs):
        if self.has_config(configs, "service.types") is False:
            return None

        self.write("##### SERVICE TYPES")
        BASE_URI = "/v1.0/nws/servicetypes"

        for obj in dict_get(configs, "service.types"):
            OBJ_URI = "%s/%s" % (BASE_URI, obj["name"])
            name = obj["name"]
            exists = self.cmp_exists(OBJ_URI, "Service type %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"servicetype": obj}, "Add service type: %s" % name)

    def __create_service_definitions(self, configs):
        if self.has_config(configs, "service.definitions") is False:
            return None

        self.write("##### SERVICE DEFINITIONS")
        BASE_URI = "/v1.0/nws/servicedefs"

        for obj in dict_get(configs, "service.definitions"):
            OBJ_URI = "%s/%s" % (BASE_URI, obj["name"])
            name = obj["name"]
            def_configs = obj.pop("configs", {})
            exists = self.cmp_exists(OBJ_URI, "Service definition %s already exists" % name)

            if exists is False:
                res = self.cmp_post(BASE_URI, {"servicedef": obj}, "Add service definition: %s" % name)

                data = {
                    "name": "%s-config" % name,
                    "desc": "%s-config" % name,
                    "service_definition_id": res["uuid"],
                    "params": def_configs,
                    "params_type": "JSON",
                    "version": obj.get("version"),
                }
                msg = "Add service definition config %s-config" % name
                self.cmp_post("/v1.0/nws/servicecfgs", {"servicecfg": data}, msg)

    def __create_service_capabilities(self, configs):
        if self.has_config(configs, "service.capabilities") is False:
            return None

        self.write("##### SERVICE CAPABILITIES")
        BASE_URI = "/v1.0/nws/capabilities"

        for obj in dict_get(configs, "service.capabilities"):
            OBJ_URI = "%s/%s" % (BASE_URI, obj["name"])
            name = obj["name"]
            exists = self.cmp_exists(OBJ_URI, "Service capability %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"capability": obj}, "Add service capability: %s" % name)
            else:
                self.cmp_put(OBJ_URI, {"capability": obj}, "Update service capability: %s" % name)

    def __create_service_processes(self, configs):
        if self.has_config(configs, "service.processes") is False:
            return None

        self.write("##### SERVICE PROCESSES")
        BASE_URI = "/v1.0/nws/serviceprocesses"

        for obj in dict_get(configs, "service.processes"):
            OBJ_URI = "%s/%s" % (BASE_URI, obj["name"])
            name = obj["name"]
            exists = self.cmp_exists(OBJ_URI, "Service process %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"process": obj}, "Add service process: %s" % name)
            else:
                self.cmp_put(OBJ_URI, {"process": obj}, "Update service process: %s" % name)

                # type_oid = obj.get("service_type_id", None)
                # method = obj.get("method", None)
                # if method is None:
                #     break
                # if type_oid is None:
                #     break
                # # get service type id
                # res = self.controller.cmp_get('/v1.0/nws/servicetypes/%s' % type_oid, 'GET').get('servicetype', {})
                # type_id = res.get("id", None)
                # if type_id is None:
                #     logger.error('Could not found a type whose oid is %s' % (type_oid))
                #     self.controller.outpu('Could not found a type whose oid is %s' % (type_oid))
                #     break
                #
                # # get serviceprocess for service type and  method
                # res = self.controller.cmp_get('/v1.0/nws/serviceprocesses',
                #                               data='service_type_id=%s&method_key=%s' % (type_id, method))\
                #     .get('serviceprocesses', [])
                #
                # if len(res) >= 1:
                #     prev = res[0]
                #     name = obj.get('name', prev['method_key'])
                #     desc = obj.get('desc', prev['desc'])
                #     process = obj.get('process', prev['process_key'])
                #     template = obj.get('template', '{}')
                # else:
                #     prev = None
                #     name = obj.get('name', '%s-%s' % (method, type_oid))
                #     desc = obj.get('desc', name)
                #     process = obj.get('process', 'invalid_key')
                #     template = obj.get('template', '{}')
                # template, filename = self.controller.file_content(template)
                #
                # data = {
                #     'serviceprocess': {
                #         'name': name,
                #         'desc': desc,
                #         'service_type_id': str(type_id),
                #         'method_key': method,
                #         'process_key': process,
                #         'template': template
                #     }
                # }
                # if prev is None:
                #     res = self.controller.cmp_post('/v1.0/nws/serviceprocesses', data=data)
                # else:
                #     res = self.controller.cmp_put('/v1.0/nws/serviceprocesses/%s' % prev['uuid'], data=data)
                # print('Set process %s for method %s to service type %s' %
                #                        (process, method, type_oid))

    def __create_service_tags(self, configs):
        if self.has_config(configs, "service.tags") is False:
            return None

        self.write("##### SERVICE TAGS")
        BASE_URI = "/v1.0/nws/tags"

        for obj in dict_get(configs, "service.tags"):
            OBJ_URI = "%s/%s" % (BASE_URI, obj["name"])
            name = obj["name"]
            exists = self.cmp_exists(OBJ_URI, "Service tag %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"tag": obj}, "Add service tag: %s" % name)
            else:
                self.cmp_put(OBJ_URI, {"tag": obj}, "Update service tag: %s" % name)

    def __create_service_catalogs(self, configs):
        if self.has_config(configs, "service.catalogs") is False:
            return None

        self.write("##### SERVICE CATALOGS")
        BASE_URI = "/v1.0/nws/srvcatalogs"

        for obj in dict_get(configs, "service.catalogs"):
            OBJ_URI = "%s/%s" % (BASE_URI, obj["name"])
            name = obj["name"]
            defs = obj.pop("definitions", [])
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])
            exists = self.cmp_exists(OBJ_URI, "Service tag %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"catalog": obj}, "Add service catalog: %s" % name)
            else:
                self.cmp_put(OBJ_URI, {"catalog": obj}, "Update service catalog: %s" % name)

            cat = self.cmp_get(OBJ_URI, "").get("catalog")

            msg = "Add service catalog %s definitions %s" % (name, defs)
            self.cmp_put(
                "/v1.0/nws/srvcatalogs/%s/defs" % cat["uuid"],
                {"definitions": {"oids": defs}},
                msg,
            )

            msg = "Refresh service catalog %s" % name
            self.cmp_patch("/v1.0/nws/srvcatalogs/%s" % cat["uuid"], {"catalog": {}}, msg)

            for info in users:
                user, role = info
                data = {"user": {"user_id": user, "role": role}}
                self.cmp_post(
                    OBJ_URI + "/users",
                    data,
                    "Set catalog %s role %s to user %s" % (name, role, user),
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": group, "role": role}}
                self.cmp_post(
                    OBJ_URI + "/groups",
                    data,
                    "Set catalog %s role %s to group %s" % (name, role, group),
                )

    def __create_organizations(self, configs):
        if self.has_config(configs, "authority.organizations") is False:
            return None

        self.write("##### AUTHORITY ORGANIZATIONS")
        BASE_URI = "/v1.0/nws/organizations"

        for obj in dict_get(configs, "authority.organizations"):
            OBJ_URI = "%s/%s" % (BASE_URI, obj["name"])
            name = obj["name"]
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])
            exists = self.cmp_exists(OBJ_URI, "Organizations %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"organization": obj}, "Add organization: %s" % name)
            else:
                self.cmp_put(OBJ_URI, {"organization": obj}, "Update organization: %s" % name)

            res = self.cmp_get(OBJ_URI, "")
            OBJ_URI = "%s/%s" % (BASE_URI, res["uuid"])

            for info in users:
                user, role = info
                data = {"user": {"user_id": user, "role": role}}
                self.cmp_post(
                    OBJ_URI + "/users",
                    data,
                    "Set organization %s role %s to user %s" % (name, role, user),
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": group, "role": role}}
                self.cmp_post(
                    OBJ_URI + "/groups",
                    data,
                    "Set organization %s role %s to group %s" % (name, role, group),
                )

    def __create_divisions(self, configs):
        if self.has_config(configs, "authority.divisions") is False:
            return None

        self.write("##### AUTHORITY DIVISIONS")
        BASE_URI = "/v1.0/nws/divisions"

        for obj in dict_get(configs, "authority.divisions"):
            OBJ_URI = "%s/%s" % (BASE_URI, obj["name"])
            name = obj["name"]
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])
            exists = self.cmp_exists(OBJ_URI, "Division %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"division": obj}, "Add division: %s" % name)
            else:
                self.cmp_put(OBJ_URI, {"division": obj}, "Update division: %s" % name)

            res = self.cmp_get(OBJ_URI, "")
            OBJ_URI = "%s/%s" % (BASE_URI, res["uuid"])

            for info in users:
                user, role = info
                data = {"user": {"user_id": user, "role": role}}
                self.cmp_post(
                    OBJ_URI + "/users",
                    data,
                    "Set division %s role %s to user %s" % (name, role, user),
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": group, "role": role}}
                self.cmp_post(
                    OBJ_URI + "/groups",
                    data,
                    "Set division %s role %s to group %s" % (name, role, group),
                )

    def __create_accounts(self, configs):
        if self.has_config(configs, "authority.accounts") is False:
            return None

        self.write("##### AUTHORITY ACCOUNTS")
        BASE_URI = "/v1.0/nws/accounts"

        for obj in dict_get(configs, "authority.accounts"):
            OBJ_URI = "%s/%s" % (BASE_URI, obj["name"])
            name = obj["name"]
            auth = obj.pop("auth", {})
            users = auth.pop("users", [])
            groups = auth.pop("groups", [])
            exists = self.cmp_exists(OBJ_URI, "Account %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"account": obj}, "Add account: %s" % name)
            else:
                self.cmp_put(OBJ_URI, {"account": obj}, "Update account: %s" % name)

            res = self.cmp_get(OBJ_URI, "")
            OBJ_URI = "%s/%s" % (BASE_URI, res["uuid"])

            for info in users:
                user, role = info
                data = {"user": {"user_id": user, "role": role}}
                self.cmp_post(
                    OBJ_URI + "/users",
                    data,
                    "Set account %s role %s to user %s" % (name, role, user),
                )

            for info in groups:
                group, role = info
                data = {"group": {"group_id": group, "role": role}}
                self.cmp_post(
                    OBJ_URI + "/groups",
                    data,
                    "Set account %s role %s to group %s" % (name, role, group),
                )

    def __create_metric_types(self, configs):
        if self.has_config(configs, "authority.metric-types") is False:
            return None

        self.write("##### AUTHORITY METRIC TYPES")
        BASE_URI = "/v1.0/nws/services/metricstypes"

        for obj in dict_get(configs, "authority.metric-types"):
            OBJ_URI = "%s/%s" % (BASE_URI, obj["name"])
            name = obj["name"]
            exists = self.cmp_exists(OBJ_URI, "Metric type %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"metric_type": obj}, "Add metric type: %s" % name)

    def __create_metric_schedules(self, configs):
        if self.has_config(configs, "authority.metric.schedules") is False:
            return None

        self.write("##### AUTHORITY JOB SCHEDULE")
        BASE_URI = "/v1.0/nws/services/job_schedules"

        for obj in dict_get(configs, "authority.metric.schedules"):
            OBJ_URI = "%s/%s" % (BASE_URI, obj["name"])
            name = obj["name"]
            exists = self.cmp_exists(OBJ_URI, "Metric schedule %s already exists" % name)

            if exists is False:
                self.cmp_post(BASE_URI, {"job_schedule": obj}, "Add metric schedule: %s" % name)

    def run(self, configs):
        self.__create_service_types(configs)
        self.__create_service_definitions(configs)
        self.__create_service_capabilities(configs)
        self.__create_service_processes(configs)
        self.__create_service_tags(configs)
        self.__create_service_catalogs(configs)
        self.__create_organizations(configs)
        self.__create_divisions(configs)
        self.__create_accounts(configs)
        self.__create_metric_types(configs)
        self.__create_metric_schedules(configs)
