# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex
from beehive3_cli.core.controller import PARGS
from beehive3_cli.plugins.ssh.controllers.ssh import SshControllerChild
from beehive3_cli.translate import _


class SshDbmsController(SshControllerChild):
    class Meta:
        label = "dbms"
        description = _("dbms management")
        help = _("dbms management")

        headers = ["id", "name", "desc", "ip_address", "date"]
        fields = ["uuid", "name", "desc", "ip_address", "date.creation"]

    @ex(
        help=_("ping dbms"),
        description=_("ping dbms"),
        arguments=PARGS(
            [
                (
                    ["host"],
                    {
                        "help": _("node name or uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": _("node group name or uuid"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": _("node group name or uuid"),
                        "action": "store",
                        "type": str,
                        "default": "mysql",
                    },
                ),
                (
                    ["-user"],
                    {
                        "help": _("node group name or uuid"),
                        "action": "store",
                        "type": str,
                        "default": "root",
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": _("node group name or uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-db"],
                    {
                        "help": _("node group name or uuid"),
                        "action": "store",
                        "type": str,
                        "default": "mysql",
                    },
                ),
            ]
        ),
    )
    def ping(self):
        from beecell.db import MysqlManager

        host = self.app.pargs.host
        port = self.app.pargs.port
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        dbms_type = self.app.pargs.type
        db = self.app.pargs.db
        db_uri = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}"
        if dbms_type == "mysql":
            server = MysqlManager(1, db_uri)
            server.create_simple_engine()
            res = server.ping()
        self.app.render({"ping": res}, headers=["ping"])
