# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex

from beecell.types.type_string import truncate
from beehive3_cli.core.controller import StringAction
from beehive3_cli.core.util import load_environment_config
from beehive3_cli.plugins.platforms.controllers import (
    ChildPlatformController,
    PLATFORM_ARGS,
)
from beehive3_cli.translate import _


class MysqlBaseController(ChildPlatformController):
    TMPL_TABLES = "%s.tables"
    TMPL_HOSTS = "Host: %s"
    TMPL_HOSTS2 = "%s.hosts"
    TMPL_ROWS = "%s.rows-inc"

    def get_mysql_engine(self, host, port, user, db):
        from beecell.db import MysqlManager

        db_uri = f"mysql+pymysql://{user['name']}:{user['password']}@{host}:{port}/{db}"
        server = MysqlManager(1, db_uri)
        server.create_simple_engine()
        self.app.log.info(f"Get mysql engine for {db_uri}")
        return server

    def get_mysql_hosts(self):
        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("mariadb", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception("No mariadb default is available for this environment. Select another environment")

        if label not in orchestrators:
            raise Exception(f"Valid label are: {', '.join(orchestrators.keys())}")
        conf = orchestrators.get(label)

        root = {"name": "root", "password": conf.get("users", {}).get("root")}
        return [str(h) for h in conf.get("hosts", [])], root


class MysqlController(MysqlBaseController):
    class Meta:
        label = "mysql"
        description = _("mysql/mariadb management")
        help = _("mysql/mariadb management")

        default_group = "mariadb"

    def dump_db(self, db, filename):
        """Dump mysql db

        :param db: mysql db
        :param filename: input filename
        """
        import sh

        hosts, user_data = self.get_mysql_hosts()
        user = "root"
        pwd = user_data.get("password")

        print(f"export {user}@{hosts[2]}:{db}")
        # filename = '%s.sql' % db
        #'--set-gtid-purged=off',
        sh.mysqldump(
            "-h",
            str(hosts[0]),
            "-u",
            user,
            f"-p{pwd}",
            f"--result-file={filename}",
            db,
        )

    def load_db(self, db, filename):
        """Load mysql db

        :param db: mysql db
        :param filename: input filename
        """
        import sh

        hosts, user_data = self.get_mysql_hosts()
        user = "root"
        pwd = user_data.get("password")

        inp = input(f"import {user}@{hosts[2]}:{db}: ")
        if inp == "y":
            with open(filename, "r", encoding="utf-8") as f:
                sh.mysql(
                    "-h",
                    str(hosts[0]),
                    "-u",
                    user,
                    f"-p{pwd}",
                    "--verbose",
                    db,
                    _in=f,
                )

    def drop_all_tables(self, db, port=3306):
        """Drop all tables in a db

        :param db: mysql db
        :param port: mysql port [default=3306]
        """
        hosts, root = self.get_mysql_hosts()

        # for host in hosts:
        host = hosts[2]
        self.c(self.TMPL_HOSTS % host, "underline")
        server = self.get_mysql_engine(host, port, root, db)
        server.drop_all_tables(db)
        msg = {"msg": f"drop all tables in db {db}"}
        self.app.log.info(msg)
        self.app.render(msg, headers=["msg"])

    @ex(
        help=_("ping mysql instance"),
        description=_("ping mysql instance"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def ping(self):
        port = self.app.pargs.port
        hosts, root = self.get_mysql_hosts()

        resp = []
        db = "mysql"
        for host in hosts:
            server = self.get_mysql_engine(host, port, root, db)
            res = server.ping()
            resp.append({"host": host, "response": res})
            self.app.log.info(f"Ping mysql : {res}")

        self.app.render(resp, headers=["host", "response"])

    @ex(
        help=_("show mysql binary logs"),
        description=_("show mysql binary logs"),
        example="beehive platform mysql binary-log-show -e <env>",
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def binary_log_show(self):
        port = self.app.pargs.port
        hosts, root = self.get_mysql_hosts()

        resp = []
        db = "mysql"
        for host in hosts:
            server = self.get_mysql_engine(host, port, root, db)
            res = server.show_binary_log()
            for k, v in res.items():
                resp.append({"host": host, "log": k, "size": v})
            self.app.log.info(f"get mysql binary log: {res}")

        self.app.render(resp, headers=["host", "log", "size"])

    @ex(
        help=_("purge mysql binary logs"),
        description=_("purge mysql binary logs"),
        example="beehive platform mysql binary-log-purge -e <env>",
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def binary_log_purge(self):
        port = self.app.pargs.port
        hosts, root = self.get_mysql_hosts()

        resp = []
        db = "mysql"
        for host in hosts:
            server = self.get_mysql_engine(host, port, root, db)
            server.purge_binary_log()
            resp.append({"host": host, "purge": True})
            self.app.log.info("purge mysql binary log")

        self.app.render(resp, headers=["host", "purge"])

    @ex(
        help=_("get mariadb galera cluster status"),
        description=_("get mariadb galera cluster status"),
        example="beehive platform mysql galera-cluster-status -e <env>",
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
                (
                    ["-check_host"],
                    {
                        "help": _("list of comma separated host to check"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def galera_cluster_status(self):
        port = self.app.pargs.port
        check_host = self.app.pargs.check_host
        hosts, root = self.get_mysql_hosts()
        if check_host is not None:
            hosts = [check_host]

        resp = []
        db = "mysql"
        cluster_size = len(hosts)
        for host in hosts:
            try:
                server = self.get_mysql_engine(host, port, root, db)
                status = server.get_galera_cluster_status()
                self.app.log.info(f"get mysql cluster status : {status}")
                summary_status = (
                    (status["wsrep_cluster_status"] == "Primary")
                    and int(status["wsrep_cluster_size"]) == cluster_size
                    and (status["wsrep_local_state_comment"] == "Synced")
                )
                status.update({"check_host": host, "status": summary_status})
                resp.append(status)
            except Exception as exc:
                self.app.log.error(exc)
                status = {"check_host": host, "status": False}
                resp.append(status)

        headers = [
            "check_host",
            "wsrep_cluster_status",
            "wsrep_cluster_size",
            "wsrep_local_state_comment",
            "status",
        ]
        self.app.render(resp, headers=headers)

    @ex(
        help=_("get mariadb slave replica status"),
        description=_("get mariadb slave replica status"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def replica_slave_status(self):
        port = self.app.pargs.port
        hosts, root = self.get_mysql_hosts()

        db = "mysql"
        for host in hosts:
            try:
                server = self.get_mysql_engine(host, port, root, db)
                res = server.get_replica_slave_status()[0]
                self.c(f"host: {host}", "underline")
                self.app.render(res, details=True)
            except Exception as exception:
                self.app.log.error(exception)

    @ex(
        help=_("stop replica on slave"),
        description=_("stop replica on slave"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def replica_slave_stop(self):
        port = self.app.pargs.port
        hosts, root = self.get_mysql_hosts()

        db = "mysql"
        for host in hosts:
            try:
                server = self.get_mysql_engine(host, port, root, db)
                server.stop_replica_on_slave()
                self.app.render({"msg": f"stop replica on node {host}"})
            except Exception as exception:
                self.app.log.error(exception)

    @ex(
        help=_("start replica on slave"),
        description=_("start replica on slave"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def replica_slave_start(self):
        port = self.app.pargs.port
        hosts, root = self.get_mysql_hosts()

        db = "mysql"
        for host in hosts:
            try:
                server = self.get_mysql_engine(host, port, root, db)
                server.start_replica_on_slave()
                self.app.render({"msg": f"start replica on node {host}"})
            except Exception as exception:
                self.app.log.error(exception)

    #
    # import export db
    #
    @ex(
        help=_("dump mysql db"),
        description=_("dump mysql db"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["db"],
                    {
                        "help": _("db name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("dump file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dump(self):
        db = self.app.pargs.db
        file = self.app.pargs.file
        self.dump_db(db, file)

    @ex(
        help=_("load mysql db"),
        description=_("load mysql db"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["db"],
                    {
                        "help": _("db name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["file"],
                    {
                        "help": _("dump file"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def load(self):
        db = self.app.pargs.db
        file = self.app.pargs.file
        self.load_db(db, file)

    @ex(
        help=_("drop mysql db"),
        description=_("drop mysql db"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["db"],
                    {
                        "help": _("db name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def drop(self):
        db = self.app.pargs.db
        port = self.app.pargs.port
        self.drop_all_tables(db, port)

    @ex(
        help=_("drop mysql dbs"),
        description=_("drop mysql dbs"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["dbs"],
                    {
                        "help": _("db name comma separated"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def drops(self):
        dbs = self.app.pargs.dbs.split(",")
        for db in dbs:
            self.drop_all_tables(db)


class MysqlSchemaController(MysqlBaseController):
    class Meta:
        label = "dbs"
        stacked_on = "mysql"
        stacked_type = "nested"
        description = _("mysql database management")
        help = _("mysql database management")

    @ex(
        help=_("get mysql database list"),
        description=_("get mysql database list"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def get(self):
        port = self.app.pargs.port
        hosts, root = self.get_mysql_hosts()

        resp = {}
        db = "mysql"
        headers = ["database"]
        for host in hosts:
            headers.append(self.TMPL_TABLES % host)
        for host in hosts:
            server = self.get_mysql_engine(host, port, root, db)
            dbs = server.get_schemas()
            for db_table in dbs:
                db = db_table["db"]
                tables = db_table["tables"]
                if db not in resp:
                    resp[db] = {"database": db}
                    for h in hosts:
                        resp[db][self.TMPL_TABLES % h] = None
                resp[db][self.TMPL_TABLES % host] = tables
            self.app.log.info(f"Get mysql database : {resp}")
        self.app.render(list(resp.values()), headers=headers, separator=",")

    @ex(
        help=_("add mysql database"),
        description=_("add mysql database"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("database name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add(self):
        port = self.app.pargs.port
        db_name = self.app.pargs.name
        hosts, root = self.get_mysql_hosts()

        db = "mysql"
        server = self.get_mysql_engine(hosts[0], port, root, db)
        server.add_schema(db_name)
        self.app.render({"msg": f"add database {db_name}"})

    @ex(
        help=_("delete mysql database"),
        description=_("delete mysql database"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("database name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def drop(self):
        port = self.app.pargs.port
        db_name = self.app.pargs.name
        hosts, root = self.get_mysql_hosts()

        db = "mysql"
        server = self.get_mysql_engine(hosts[0], port, root, db)
        server.drop_schema(db_name)
        self.app.render({"msg": f"drop database {db_name}"})


class MysqlUserController(MysqlBaseController):
    class Meta:
        label = "dbusers"
        stacked_on = "mysql"
        stacked_type = "nested"
        description = _("mysql user management")
        help = _("mysql user management")

    @ex(
        help=_("get mysql user list"),
        description=_("get mysql user list"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def get(self):
        port = self.app.pargs.port
        hosts, root = self.get_mysql_hosts()

        db = "mysql"
        for host in hosts:
            self.c("\n" + self.TMPL_HOSTS % host, "underline")
            server = self.get_mysql_engine(host, port, root, db)
            users = server.get_users()
            self.app.render(users, headers=["user", "host"])

    @ex(
        help=_("add mysql user"),
        description=_("add mysql user"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
                (
                    ["-host"],
                    {
                        "help": _("user host"),
                        "action": "store",
                        "type": str,
                        "default": "%",
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["pwd"],
                    {
                        "help": _("user password"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def add(self):
        port = self.app.pargs.port
        name = self.app.pargs.name
        host = self.app.pargs.host
        pwd = self.app.pargs.pwd
        hosts, root = self.get_mysql_hosts()

        db = "mysql"
        server = self.get_mysql_engine(hosts[0], port, root, db)
        server.add_user(name, host, pwd)
        self.app.render({"msg": f"add user {name}"})

    @ex(
        help=_("delete mysql user"),
        description=_("delete mysql user"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def drop(self):
        port = self.app.pargs.port
        name = self.app.pargs.name
        hosts, root = self.get_mysql_hosts()

        db = "mysql"
        server = self.get_mysql_engine(hosts[0], port, root, db)
        server.drop_user(name)
        self.app.render({"msg": f"drop user {name}"})

    @ex(
        help=_("grant db to user"),
        description=_("grant db to user"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
                (
                    ["-host"],
                    {
                        "help": _("user host"),
                        "action": "store",
                        "type": str,
                        "default": "%",
                    },
                ),
                (
                    ["name"],
                    {
                        "help": _("user name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-db"],
                    {
                        "help": _("db to grant"),
                        "action": "store",
                        "type": str,
                        "default": "mysql",
                    },
                ),
            ]
        ),
    )
    def grant(self):
        port = self.app.pargs.port
        name = self.app.pargs.name
        host = self.app.pargs.host
        db = self.app.pargs.db
        hosts, root = self.get_mysql_hosts()

        # db = 'mysql'
        server = self.get_mysql_engine(hosts[0], port, root, db)
        server.grant_db_to_user(name, host, db)
        self.app.render({"msg": f"grant db {db} to user {name}"})


class MysqlTableController(MysqlBaseController):
    class Meta:
        label = "tables"
        stacked_on = "mysql"
        stacked_type = "nested"
        description = _("mysql table management")
        help = _("mysql table management")

    @ex(
        help=_("check mysql tables"),
        description=_("check mysql tables"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["db"],
                    {
                        "help": _("db name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def check(self):
        db = self.app.pargs.db
        port = self.app.pargs.port
        hosts, root = self.get_mysql_hosts()

        resp = {}
        db = "mysql"
        headers = ["table"]
        for host in hosts:
            headers.append(self.TMPL_ROWS % host)
        for host in hosts:
            # self.c(self.TMPL_HOSTS % host, 'underline')
            server = self.get_mysql_engine(host, port, root, db)
            tables = server.get_db_tables(db)
            for table_row in tables:
                table = table_row["table_name"]
                rows = table_row["table_rows"]
                inc = table_row["auto_increment"]
                if table not in resp:
                    resp[table] = {"table": table}
                    for h in hosts:
                        resp[table][self.TMPL_ROWS % h] = None
                resp[table][self.TMPL_ROWS % host] = f"{rows:8} {inc:8}"
            self.app.log.info(f"Get mysql tables : {resp}")
        self.app.render(list(resp.values()), headers=headers, separator=",")

    @ex(
        help=_("get mysql table list"),
        description=_("get mysql table list"),
        example="beehive platform mysql tables get db",
        arguments=PLATFORM_ARGS(
            [
                (
                    ["db"],
                    {
                        "help": _("db name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def get(self):
        db = self.app.pargs.db
        port = self.app.pargs.port
        hosts, root = self.get_mysql_hosts()

        resp = []
        db = "mysql"
        for host in hosts:
            self.c("\n" + self.TMPL_HOSTS % host, "underline")
            server = self.get_mysql_engine(host, port, root, db)
            resp = server.get_db_tables(db)
            self.app.log.info(f"Get mysql db {db} tables : {resp}")

            self.app.render(
                resp,
                headers=[
                    "table_name",
                    "table_rows",
                    "auto_increment",
                    "data_length",
                    "index_length",
                ],
            )

    @ex(
        help=_("get mysql table description"),
        description=_("get mysql table description"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["db"],
                    {
                        "help": _("db name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["table"],
                    {
                        "help": _("table name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def desc(self):
        db = self.app.pargs.db
        table = self.app.pargs.table
        port = self.app.pargs.port
        hosts, root = self.get_mysql_hosts()

        resp = []
        for host in hosts:
            self.c("\n" + self.TMPL_HOSTS % host, "underline")
            server = self.get_mysql_engine(host, port, root, db)
            resp = server.get_table_description(table)
            self.app.log.info(f"Get mysql db {db} table {table} desc : {resp}")
            self.app.render(
                resp,
                headers=[
                    "name",
                    "type",
                    "default",
                    "index",
                    "is_primary_key",
                    "is_nullable",
                    "is_unique",
                ],
            )

    @ex(
        help=_("query mysql db table"),
        description=_("query mysql db table"),
        arguments=PLATFORM_ARGS(
            [
                (
                    ["db"],
                    {
                        "help": _("db name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["table"],
                    {
                        "help": _("table name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-rows"],
                    {
                        "help": _("query rows number"),
                        "action": "store",
                        "type": int,
                        "default": 20,
                    },
                ),
                (
                    ["-offset"],
                    {
                        "help": _("query rows offset"),
                        "action": "store",
                        "type": int,
                        "default": 0,
                    },
                ),
                (
                    ["-detail"],
                    {
                        "help": _("rotate record output"),
                        "action": "store",
                        "type": bool,
                        "default": False,
                    },
                ),
                (
                    ["-fields"],
                    {
                        "help": _("comma separated list of fields"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-order"],
                    {
                        "help": _("ield used to order records"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-where"],
                    {
                        "help": _("custom where"),
                        "action": StringAction,
                        "type": str,
                        "default": None,
                        "nargs": "+",
                    },
                ),
                (
                    ["-port"],
                    {
                        "help": _("mysql port"),
                        "action": "store",
                        "type": int,
                        "default": 3306,
                    },
                ),
            ]
        ),
    )
    def query(self):
        db = self.app.pargs.db
        table = self.app.pargs.table
        where = self.app.pargs.where
        rows = self.app.pargs.rows
        offset = self.app.pargs.offset
        detail = self.app.pargs.detail
        port = self.app.pargs.port
        fields = self.app.pargs.fields
        order = self.app.pargs.order
        hosts, root = self.get_mysql_hosts()
        for host in hosts:
            self.c("\n" + self.TMPL_HOSTS % host, "underline")
            server = self.get_mysql_engine(host, port, root, db)
            if fields is None:
                fields = "*"
            resp, total = server.query_table(table, where=where, fields=fields, rows=rows, offset=offset, order=order)
            self.app.log.info(f"Get mysql db {db} table {table} query : {truncate(resp)}")
            if detail is True:
                for item in resp:
                    self.app.render(item, details=True)
            else:
                print(f"Offset: {offset}")
                print(f"Count: {rows}")
                print(f"Total: {total}")
                print(f"Order by: {order}")
                self.app.render(resp, headers=list(resp[0].keys()))
