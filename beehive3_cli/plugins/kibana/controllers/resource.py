# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex
from beehive3_cli.core.controller import BaseController, PARGS
from beehive3_cli.translate import _


class ElkResourceController(BaseController):
    class Meta:
        label = "res_elk"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("elk orchestrator")
        help = _("elk orchestrator")

        cmp = {"baseuri": "/v1.0/nrs/elk", "subsystem": "resource"}

        headers = [
            "id",
            "uuid",
            "name",
            "desc",
            "ext_id",
            "parent",
            "container",
            "state",
        ]
        fields = [
            "id",
            "uuid",
            "name",
            "desc",
            "ext_id",
            "parent",
            "container",
            "state",
        ]

    def pre_command_run(self):
        super().pre_command_run()
        self.configure_cmp_api_client()

    # -----------------
    # ----- SPACE -----
    # -----------------
    @ex(
        help=_("get spaces"),
        description=_("get spaces"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("space id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def space_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/spaces/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("space")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/spaces"
            self.app.log.debug(f"-+-+- space_get '{uri}' ")
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="spaces", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("add spaces"),
        description=_("add spaces"),
        arguments=PARGS(
            [
                (
                    ["container"],
                    {
                        "help": _("container"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["id"],
                    {
                        "help": _("space id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("space name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-description"],
                    {
                        "help": _("space description"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-color"],
                    {
                        "help": _("space color"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-initials"],
                    {
                        "help": _("space initials"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def space_add(self):
        container = self.app.pargs.container
        space_id = self.app.pargs.id
        name = self.app.pargs.name
        description = self.app.pargs.description
        color = self.app.pargs.color
        initials = self.app.pargs.initials

        uri = f"{self.baseuri}/spaces"
        self.app.log.debug(f"-+-+- space_add '{uri}' ")

        data_space = {"container": container, "space_id": space_id, "name": name}

        if description is not None:
            data_space.update({"desc": description})
        if color is not None:
            data_space.update({"color": color})
        if initials is not None:
            data_space.update({"initials": initials})

        data = {"space": data_space}
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help=_("delete spaces"),
        description=_("delete spaces"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("resource space id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def space_delete(self):
        oid = self.app.pargs.id

        uri = f"{self.baseuri}/spaces/{oid}"
        self.app.log.debug(f"-+-+- space_delete '{uri}' ")

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)

    # ----------------
    # ----- ROLE -----
    # ----------------
    @ex(
        help=_("get roles"),
        description=_("get roles"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("role id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def role_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/roles/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("role")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/roles"
            self.app.log.debug(f"-+-+- role_get '{uri}' ")
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="roles", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("add roles"),
        description=_("add roles"),
        arguments=PARGS(
            [
                (
                    ["container"],
                    {
                        "help": _("container"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("role name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["indice"],
                    {"help": _("indice"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["space_id"],
                    {
                        "help": _("space id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def role_add(self):
        container = self.app.pargs.container
        # id = self.app.pargs.id
        name = self.app.pargs.name
        desc = f"Desc {name}"
        indice = self.app.pargs.indice
        space_id = self.app.pargs.space_id

        uri = f"{self.baseuri}/roles"
        self.app.log.debug(f"-+-+- role_add '{uri}' ")

        data_role = {
            "container": container,
            "name": name,
            "desc": desc,
            "indice": indice,
            "space_id": space_id,
        }
        data = {"role": data_role}
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help=_("delete roles"),
        description=_("delete roles"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("resource role id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def role_delete(self):
        oid = self.app.pargs.id

        uri = f"{self.baseuri}/roles/{oid}"
        self.app.log.debug(f"-+-+- role_delete '{uri}' ")

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)

    # ------------------
    # -- ROLE MAPPING --
    # ------------------
    @ex(
        help=_("get role_mappings"),
        description=_("get role_mappings"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("role_mapping id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def role_mapping_get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/role_mappings/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                res = res.get("role_mapping")
                self.app.render(res, details=True)
            else:
                self.app.render(res, details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/role_mappings"
            self.app.log.debug(f"-+-+- role_mapping_get '{uri}' ")
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="role_mappings",
                headers=self._meta.headers,
                fields=self._meta.fields,
            )

    @ex(
        help=_("add role_mappings"),
        description=_("add role_mappings"),
        arguments=PARGS(
            [
                (
                    ["container"],
                    {
                        "help": _("container"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("role_mapping name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["role_name"],
                    {
                        "help": _("role name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["users_email"],
                    {
                        "help": _("users email"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["realm_name"],
                    {
                        "help": _("realm name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def role_mapping_add(self):
        container = self.app.pargs.container
        # id = self.app.pargs.id
        name = self.app.pargs.name
        desc = f"Desc {name}"
        role_name = self.app.pargs.role_name
        users_email = self.app.pargs.users_email
        realm_name = self.app.pargs.realm_name

        uri = f"{self.baseuri}/role_mappings"
        self.app.log.debug(f"-+-+- role_mapping_add '{uri}' ")

        data_role_mapping = {
            "container": container,
            "name": name,
            "desc": desc,
            "role_name": role_name,
            "users_email": users_email,
            "realm_name": realm_name,
        }
        data = {"role_mapping": data_role_mapping}
        res = self.cmp_post(uri, data=data)
        self.app.render(res, details=True)

    @ex(
        help=_("delete role_mappings"),
        description=_("delete role_mappings"),
        arguments=PARGS(
            [
                (
                    ["id"],
                    {
                        "help": _("resource role_mapping id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                )
            ]
        ),
    )
    def role_mapping_delete(self):
        oid = self.app.pargs.id

        uri = f"{self.baseuri}/role_mappings/{oid}"
        self.app.log.debug(f"-+-+- role_mapping_delete '{uri}' ")

        res = self.cmp_delete(uri)
        if res is not None:
            self.app.render(res, details=True)
