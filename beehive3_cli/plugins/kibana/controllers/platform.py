# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2020-2022 Regione Piemonte
# (C) Copyright 2018-2023 CSI-Piemonte

from cement import ex
from beecell.simple import merge_list
from beedrones.elk.client_kibana import KibanaManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS, PAGINATION_ARGS
from beehive3_cli.core.util import load_environment_config


def KIBANA_ARGS(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": "kibana platform reference label",
            },
        )
    ]
    # TODO fv - eliminare pagination args?
    res = merge_list(BASE_ARGS, PAGINATION_ARGS, orchestrator_args, *list_args)
    return res


class KibanaPlatformController(BaseController):
    headers = ["id", "name"]
    entity_class = None

    class Meta:
        stacked_on = "platform"
        stacked_type = "nested"
        label = "kibana"
        description = "kibana platform management"
        help = "kibana platform  management"

    def pre_command_run(self):
        super(KibanaPlatformController, self).pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("kibana", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No kibana default platform is available for this environment. Select " "another environment"
                )

        if label not in orchestrators:
            raise Exception("Valid label are: %s" % ", ".join(orchestrators.keys()))
        self.conf = orchestrators.get(label)

        # print("-+-+- self.conf: " + str(self.conf))
        uri = "%s://%s:%s%s" % (
            self.conf.get("proto"),
            self.conf.get("hosts")[0],
            self.conf.get("port"),
            self.conf.get("path"),
        )
        user = self.conf.get("user")
        password = self.conf.get("pwd")
        self.client = KibanaManager(uri, user, password)

    @ex(help="ping kibana", description="ping kibana", arguments=KIBANA_ARGS())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(
        help="get kibana version",
        description="get kibana version",
        arguments=KIBANA_ARGS(),
    )
    def version(self):
        res = self.client.version()
        self.app.render(res, headers=["version"])

    # -----------------
    # ----- SPACE -----
    # -----------------
    @ex(
        help="add space",
        description="add space",
        arguments=KIBANA_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "space id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": "space name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-description"],
                    {
                        "help": "space description",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-color"],
                    {
                        "help": "space color",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-initials"],
                    {
                        "help": "space initials",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def space_add(self):
        id = self.app.pargs.id
        name = self.app.pargs.name
        description = self.app.pargs.description
        color = self.app.pargs.color
        initials = self.app.pargs.initials
        res = self.client.space.add(id, name, description=description, color=color, initials=initials)
        self.app.render(
            res,
            headers=[
                "id",
                "name",
                "description",
                "color",
                "disabledFeatures",
                "_reserved",
            ],
        )

    @ex(
        help="delete space",
        description="delete space",
        arguments=KIBANA_ARGS(
            [
                (
                    ["id"],
                    {
                        "help": "space id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def space_del(self):
        space_id = self.app.pargs.id
        self.client.space.delete(space_id)
        self.app.render({"msg": "delete space %s" % space_id}, headers=["msg"])

    @ex(
        help="get space",
        description="get space",
        arguments=KIBANA_ARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "space id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def space_get(self):
        space_id = self.app.pargs.id
        if space_id is not None:
            res = self.client.space.get(space_id)

            if self.is_output_text():
                self.app.log.debug("is_output_text")
                # res.pop('related', None)
                # res.pop('summary_fields', None)
                # job_env = res.pop('job_env', {})
                self.app.render(res, details=True)
            else:
                self.app.log.info("not is_output_text")
                self.app.render(res, details=True)
        else:
            res = self.client.space.list()
            self.app.render(
                res,
                headers=[
                    "id",
                    "name",
                    "description",
                    "color",
                    "disabledFeatures",
                    "_reserved",
                ],
            )

    # ----------------
    # ----- ROLE -----
    # ----------------
    @ex(
        help="add role",
        description="add role",
        arguments=KIBANA_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "role name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["indice"],
                    {"help": "indice", "action": "store", "type": str, "default": None},
                ),
                (
                    ["space_id"],
                    {
                        "help": "space_id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def role_add(self):
        role_name = self.app.pargs.name
        indice = self.app.pargs.indice
        space_id = self.app.pargs.space_id
        res = self.client.role.add(role_name, indice, space_id)
        self.app.render(res, headers=["name", "indice", "space_id"])

    @ex(
        help="delete role",
        description="delete role",
        arguments=KIBANA_ARGS(
            [
                (
                    ["name"],
                    {
                        "help": "role name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def role_del(self):
        role_name = self.app.pargs.name
        self.client.role.delete(role_name)
        self.app.render({"msg": "delete role %s" % role_name}, headers=["msg"])

    @ex(
        help="get role",
        description="get role",
        arguments=KIBANA_ARGS(
            [
                (
                    ["-name"],
                    {
                        "help": "role name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def role_get(self):
        role_name = self.app.pargs.name
        if role_name is not None:
            res = self.client.role.get(role_name)

            if self.is_output_text():
                self.app.log.debug("is_output_text")
                # res.pop('related', None)
                # res.pop('summary_fields', None)
                # job_env = res.pop('job_env', {})
                self.app.render(res, details=True)
            else:
                self.app.log.info("not is_output_text")
                self.app.render(res, details=True)
        else:
            res = self.client.role.list()
            self.app.render(res, headers=["name", "indice", "space_id"])
