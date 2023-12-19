# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from cement import ex
from beecell.db import MysqlManager
from beehive3_cli.core.controller import PARGS
from beehive3_cli.plugins.ssh.controllers.ssh import SshControllerChild


class SshDbmsController(SshControllerChild):
    class Meta:
        label = "dbms"
        description = "dbms management"
        help = "dbms management"

        headers = ["id", "name", "desc", "ip_address", "date"]
        fields = ["uuid", "name", "desc", "ip_address", "date.creation"]

    @ex(
        help="ping dbms",
        description="ping dbms",
        arguments=PARGS(
            [
                (
                    ["host"],
                    {
                        "help": "node name or uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": "node group name or uuid",
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
                (
                    ["-type"],
                    {
                        "help": "node group name or uuid",
                        "action": "store",
                        "type": str,
                        "default": "mysql",
                    },
                ),
                (
                    ["-user"],
                    {
                        "help": "node group name or uuid",
                        "action": "store",
                        "type": str,
                        "default": "root",
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": "node group name or uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-db"],
                    {
                        "help": "node group name or uuid",
                        "action": "store",
                        "type": str,
                        "default": "mysql",
                    },
                ),
            ]
        ),
    )
    def ping(self):
        host = self.app.pargs.host
        port = self.app.pargs.port
        user = self.app.pargs.user
        pwd = self.app.pargs.pwd
        dbms_type = self.app.pargs.type
        db = self.app.pargs.db
        db_uri = "mysql+pymysql://%s:%s@%s:%s/%s" % (user, pwd, host, port, db)
        if dbms_type == "mysql":
            server = MysqlManager(1, db_uri)
            server.create_simple_engine()
            res = server.ping()
        self.app.render({"ping": res}, headers=["ping"])
