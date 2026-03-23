# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from json import dumps, loads
from time import sleep, time
from cement import ex
from beecell.types.type_list import merge_list
from beecell.types.type_id import id_gen
from beehive3_cli.core.controller import BASE_ARGS
from beehive3_cli.core.util import load_environment_config
from beehive3_cli.plugins.platforms.controllers.k8s import BaseK8sController
from beehive3_cli.translate import _


def redis_args(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": _("redis cluster or single node reference label"),
            },
        ),
        (
            ["-D", "--database"],
            {
                "action": "store",
                "dest": "database",
                "help": _("redis database number"),
                "default": 0,
            },
        ),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class RedisController(BaseK8sController):
    class Meta:
        label = "redis"
        description = _("redis management")
        help = _("redis management")

        default_group = "redis"

    def pre_command_run(self):
        # use same label for k8s
        label = getattr(self.app.pargs, "orchestrator", None)
        # print("label: %s" % label)
        super().pre_command_run_inner()

        self.sentinel_conf = None
        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("redis", {})

        # label = getattr(self.app.pargs, "orchestrator", None)
        self.db = getattr(self.app.pargs, "database", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No redis default platform is available for this environment. Select another environment"
                )

        if label not in orchestrators:
            raise Exception(f"Valid label are: {', '.join(orchestrators.keys())}")
        self.conf = orchestrators.get(label)

        self.sentinel_conf = self.conf.get("sentinel", None)

        services = self.list_service(self.default_namespace, name="redis")
        self.redis_service = services[0]

    def run_cmd(self, func, dbs=None, print_res=True, format_res=True):
        """Run command on redis instances"""
        from beecell.db.manager import RedisManager

        if dbs is None:
            dbs=[0]

        if self.sentinel_conf is None:
            print("redis NO sentinel")
            host = self.conf.get("host")
            port = self.conf.get("port")
            if port is None:
                port = self.redis_service.spec.ports[0].node_port
            pwd = self.conf.get("pwd")
            print(f"redis host: {host} - port: {port}")
        else:
            print("redis sentinel")
            sentinels = self.sentinel_conf.get("host")
            sentinel_name = self.sentinel_conf.get("group")
            sentinel_pwd = self.sentinel_conf.get("pwd")
            sentinel_port = self.sentinel_conf.get("port")
            pwd = self.conf.get("pwd")

        try:
            resp = []
            if self.sentinel_conf is not None:
                server = RedisManager(
                    None,
                    sentinels=[(s, sentinel_port) for s in sentinels],
                    sentinel_name=sentinel_name,
                    sentinel_pwd=sentinel_pwd,
                    pwd=pwd,
                    db=self.db,
                )
                res = func(server)
            else:
                if pwd is not None:
                    uri = f"redis://:{pwd}@{host}:{port}/{self.db}"
                else:
                    uri = f"redis://{host}:{port}/{self.db}"
                server = RedisManager(uri)
                res = func(server)

            if format_res:
                if isinstance(res, dict):
                    for k, v in res.items():
                        resp.append({"response": f"{k} = {v}"})
                elif isinstance(res, list):
                    for v in res:
                        resp.append({"response": v})
                else:
                    resp.append({"response": res})
            else:
                resp.append({"response": res})
            if print_res:
                self.app.render(resp, headers=["response"], maxsize=1000)
                # self.app.render(resp, headers=['host', 'db', 'response'], maxsize=1000)
        except Exception:
            self.app.error("redis runcmd error")
            raise

        return resp

    @ex(
        help=_("ping redis instances"),
        description=_("ping redis instances"),
        arguments=redis_args([(["-port"], {"help": _("redis port"), "action": "store", "default": 443})]),
    )
    def ping(self):
        def func(server):
            return server.ping()

        self.run_cmd(func)

    @ex(
        help=_("ping redis sentinel instances"),
        description=_("ping redis sentinel instances"),
        arguments=redis_args([(["-port"], {"help": _("redis port"), "action": "store", "default": 443})]),
    )
    def sentinel_ping(self):
        if self.sentinel_conf is not None:

            def func(server):
                return server.sentinel_ping()

            self.run_cmd(func)

    @ex(
        help=_("discover redis sentinel status"),
        description=_("discover redis sentinel status"),
        arguments=redis_args([(["-port"], {"help": _("redis port"), "action": "store", "default": 443})]),
    )
    def sentinel_status(self):
        if self.sentinel_conf is not None:

            def func(server):
                return server.sentinel_status()

            res = self.run_cmd(func, print_res=False)
            self.app.render(res, headers=["response"], maxsize=200)

    @ex(
        help=_("test redis cluster"),
        description=_("test redis cluster"),
        arguments=redis_args([(["-port"], {"help": _("redis port"), "action": "store", "default": 443})]),
    )
    def test(self):
        def test_case(server):
            key = f"key-{id_gen()}"
            start = time()
            try:
                value = {"prova": "test"}
                res = server.set(key, dumps(value))
                elapsed = round(time() - start, 4)
                print(f"  set: {res} - server: {server.sentinel_discover()} [{elapsed}]")
            except Exception as exception:
                self.app.error(f"  get: {exception}")

            start = time()
            try:
                res = server.get(key)
                res = loads(res)
                res = res.get("prova", None) == "test"
                elapsed = round(time() - start, 4)
                print(f"  get: {res} - server: {server.sentinel_discover()} [{elapsed}]")
            except Exception as exception:
                self.app.error(f"  get: {exception}")

            start = time()
            try:
                res = server.delete_key(key)
                res = res is None
                elapsed = round(time() - start, 4)
                print(f"  del: {res} - server: {server.sentinel_discover()} [{elapsed}]")
            except Exception as exception:
                self.app.error(f"  get: {exception}")

            start = time()
            try:
                res = server.get(key)
                res = res is None
                elapsed = round(time() - start, 4)
                print(f"  get: {res} - server: {server.sentinel_discover()} [{elapsed}]")
            except Exception as exception:
                self.app.error(f"  get: {exception}")

        def func(server):
            for i in range(100):
                print(f"test case - {i}")
                test_case(server)
                sleep(2)

        self.run_cmd(func, print_res=False)

    @ex(
        help=_("info from redis instances"),
        description=_("info from redis instances"),
        arguments=redis_args([(["-port"], {"help": _("redis port"), "action": "store", "default": 443})]),
    )
    def info(self):
        def func(server):
            return server.info()

        self.run_cmd(func)

    @ex(
        help=_("config of redis instances"),
        description=_("config of redis instances"),
        arguments=redis_args([(["-port"], {"help": _("redis port"), "action": "store", "default": 443})]),
    )
    def confs(self):
        def func(server):
            return server.config()

        res = self.run_cmd(func, print_res=False)[0]["response"]
        self.app.render(res, details=True)

    @ex(
        help=_("summary of redis instances"),
        description=_("summary of redis instances"),
        arguments=redis_args([(["-port"], {"help": _("redis port"), "action": "store", "default": 443})]),
    )
    def summary(self):
        def func(server):
            res = server.info()
            resp = {}
            for k, v in res.items():
                raw = {}
                for k1 in [
                    "role",
                    "redis_version",
                    "process_id",
                    "uptime_in_seconds",
                    "os",
                    "connected_clients",
                    "total_commands_processed",
                    "pubsub_channels",
                    "total_system_memory_human",
                    "used_memory_rss_human",
                    "used_memory_human",
                    "used_cpu_sys",
                    "used_cpu_user",
                    "instantaneous_output_kbps",
                ]:
                    raw[k1] = v[k1]
                resp[k] = raw
            return resp

        self.run_cmd(func)

    @ex(
        help=_("size of redis instances"),
        description=_("size of redis instances"),
        arguments=redis_args([(["-port"], {"help": _("redis port"), "action": "store", "default": 443})]),
    )
    def size(self):
        def func(server):
            return server.size()

        self.run_cmd(func, dbs=range(0, 8))

    @ex(
        help=_("client list  of redis instances"),
        description=_("client list  of redis instances"),
        arguments=redis_args([(["-port"], {"help": _("redis port"), "action": "store", "default": 443})]),
    )
    def client_list(self):
        def func(server):
            return server.server.client_list()

        self.run_cmd(func)

    @ex(
        help=_("flush redis instances"),
        description=_("flush redis instances"),
        arguments=redis_args([(["-port"], {"help": _("redis port"), "action": "store", "default": 443})]),
    )
    def flush(self):
        def func(server):
            return server.server.flushall()

        self.run_cmd(func)

    @ex(
        help=_("inspect redis instances"),
        description=_("inspect redis instances"),
        arguments=redis_args(
            [
                (["-port"], {"help": _("redis port"), "action": "store", "default": 443}),
                (
                    ["-pattern"],
                    {
                        "help": _("keys search pattern [default=*]"),
                        "action": "store",
                        "default": "*",
                    },
                ),
            ]
        ),
    )
    def inspect(self):
        pattern = self.app.pargs.pattern

        def func(server):
            res = server.inspect(pattern=pattern, debug=False)
            print(type(res))
            return res

        self.run_cmd(func, dbs=range(0, 8))

    @ex(
        help=_("scan redis instances"),
        description=_("scan redis instances"),
        arguments=redis_args(
            [
                (["-port"], {"help": _("redis port"), "action": "store", "default": 443}),
                (
                    ["-db"],
                    {"help": _("redis db [default=0]"), "action": "store", "default": 0},
                ),
                (
                    ["-pattern"],
                    {
                        "help": _("keys search pattern [default=*]"),
                        "action": "store",
                        "default": "*",
                    },
                ),
                (
                    ["-cursor"],
                    {"help": _("cursor [default=0]"), "action": "store", "default": 0},
                ),
                (
                    ["-count"],
                    {"help": _("cursor [default=10]"), "action": "store", "default": 1000},
                ),
            ]
        ),
    )
    def scan(self):
        pattern = self.app.pargs.pattern
        #cursor = self.app.pargs.cursor
        count = self.app.pargs.count
        db = self.app.pargs.db

        def func(server):
            def get_data(cursor):
                res = server.scan(pattern=pattern, cursor=cursor, count=count)
                res1 = {"cursor": res[0], "data": []}
                for key in res[1]:
                    try:
                        val = server.get(key)
                    except:
                        val = b""
                    res1["data"].append({"key": key, "val": val})
                return res1

            final_data = []
            data = get_data(0)
            final_data.extend(data.get("data"))
            while data.get("cursor") != 0:
                data = get_data(data.get("cursor"))
                final_data.extend(data.get("data"))
            return final_data

        resp = self.run_cmd(func, dbs=[db], print_res=False, format_res=False)
        if len(resp) > 0:
            resp = resp[0]
            print(f"host: {resp.get('host')}")
            print(f"db: {resp.get('db')}")

            for item in resp.get("response"):
                print("--------------------------------------------")
                print(f"key:   {self.app.colored_text.blue(item.get('key').decode('utf-8'))}")
                value = item.get("val")
                if value is None:
                    print("value: None")
                else:
                    print(f"value: {self.app.colored_text.blue(value.decode('utf-8'))}")

    @ex(
        help=_("get redis records by pattern"),
        description=_("get redis records by pattern"),
        example="beehive platform redis get -pattern cmp.ServiceModule*",
        arguments=redis_args(
            [
                (["-port"], {"help": _("redis port"), "action": "store", "default": 443}),
                (
                    ["-pattern"],
                    {
                        "help": _("keys search pattern [default=*]"),
                        "action": "store",
                        "default": "*",
                    },
                ),
            ]
        ),
    )
    def get(self):
        pattern = self.app.pargs.pattern

        def func(server):
            keys = server.inspect(pattern=pattern, debug=False)
            resp = []
            for key in keys:
                if key[1] == b"string":
                    res = server.get(key[0])
                    try:
                        res = res.decode("utf-8")
                    except:
                        pass
                elif key[1] == b"list":
                    res = server.server.lrange(key[0], 0, -1)
                else:
                    res = None
                k = key[0].decode("utf-8")
                kt = key[1].decode("utf-8")
                resp.append({"key": k, "type": kt, "ttl": key[2], "value": res})
            self.app.render(resp, headers=["key", "type", "ttl", "value"], maxsize=100)

            return resp

        self.run_cmd(func, dbs=range(0, 8), print_res=False, format_res=False)

    @ex(
        help=_("set redis record"),
        description=_("set redis record"),
        arguments=redis_args(
            [
                (["-port"], {"help": _("redis port"), "action": "store", "default": 443}),
                (["record_key"], {"help": _("record key"), "action": "store"}),
                (["value"], {"help": _("record value"), "action": "store"}),
            ]
        ),
    )
    def set(self):
        key = self.app.pargs.record_key
        value = self.app.pargs.value

        def func(server):
            resp = server.set(key=key, value=value)
            return resp

        self.run_cmd(func, dbs=range(0, 8))

    @ex(
        help=_("delete redis records"),
        description=_("delete redis records"),
        arguments=redis_args(
            [
                (["-port"], {"help": _("redis port"), "action": "store", "default": 443}),
                (
                    ["-pattern"],
                    {
                        "help": _("keys search pattern [default=*]"),
                        "action": "store",
                        "default": "*",
                    },
                ),
            ]
        ),
    )
    def delete(self):
        pattern = self.app.pargs.pattern

        def func(server):
            return server.delete(pattern=pattern)

        self.run_cmd(func, dbs=range(0, 8))

    @ex(
        help=_("delete redis keys older than a value in seconds"),
        description=_("delete redis keys older than a value in seconds"),
        arguments=redis_args(
            [
                (
                    ["seconds"],
                    {
                        "help": _("min ttl accepted"),
                        "action": "store",
                        "default": 443,
                        "type": int,
                    },
                ),
                (["-port"], {"help": _("redis port"), "action": "store", "default": 443}),
                (
                    ["-db"],
                    {"help": _("redis db [default=0]"), "action": "store", "default": 0},
                ),
                (
                    ["-pattern"],
                    {
                        "help": _("keys search pattern [default=*]"),
                        "action": "store",
                        "default": "*",
                    },
                ),
                (
                    ["-cursor"],
                    {"help": _("cursor [default=0]"), "action": "store", "default": 0},
                ),
                (
                    ["-count"],
                    {"help": _("cursor [default=10]"), "action": "store", "default": 50},
                ),
            ]
        ),
    )
    def deletes(self):
        seconds = self.app.pargs.seconds
        pattern = self.app.pargs.pattern
        #cursor = self.app.pargs.cursor
        count = self.app.pargs.count
        db = self.app.pargs.db

        def func(server):
            def get_data(cursor):
                res = server.scan(pattern=pattern, cursor=cursor, count=count)
                res1 = {"cursor": res[0], "data": []}
                for key in res[1]:
                    ttl = server.ttl(key)
                    res1["data"].append({"key": key, "ttl": ttl})

                    # check and delete old key
                    if ttl < seconds:
                        server.delete_key(key)
                        print(key)
                return res1

            data = get_data(0)
            while data.get("cursor") != 0:
                print(f"cursor: {data.get('cursor')}")
                data = get_data(data.get("cursor"))
            return data

        resp = self.run_cmd(func, dbs=[db], print_res=False, format_res=False)
        if len(resp) > 0:
            resp = resp[0]
            print(f"host: {resp.get('host')}")
            print(f"db: {resp.get('db')}")

    @ex(
        help=_("get cache"),
        description=_("get cache"),
        example="beehive platform redis cache-get -e <env>",
        arguments=redis_args(
            [
                (["-port"], {"help": _("redis port"), "action": "store", "default": 443}),
                (
                    ["-db"],
                    {"help": _("redis db [default=0]"), "action": "store", "default": 0},
                ),
                (
                    ["-pattern"],
                    {
                        "help": _("keys search pattern [default=*]"),
                        "action": "store",
                        "default": "*",
                    },
                ),
                (
                    ["-cursor"],
                    {"help": _("cursor [default=0]"), "action": "store", "default": 0},
                ),
                (
                    ["-count"],
                    {"help": _("count [default=10]"), "action": "store", "default": 1000},
                ),
                (
                    ["-value"],
                    {
                        "help": _("if True show cache value"),
                        "action": "store",
                        "default": False,
                        "type": bool,
                    },
                ),
            ]
        ),
    )
    def cache_get(self):
        pattern = self.app.pargs.pattern
        #cursor = self.app.pargs.cursor
        count = self.app.pargs.count
        db = self.app.pargs.db
        value = self.app.pargs.value

        pattern = "cache." + pattern

        def func(server):
            def get_data(cursor):
                res = server.scan(pattern=pattern, cursor=cursor, count=count)
                res1 = {"cursor": res[0], "data": []}
                for key in res[1]:
                    try:
                        val = server.get(key)
                    except:
                        val = b""
                    res1["data"].append({"key": key, "val": val})
                return res1

            final_data = []
            data = get_data(0)
            final_data.extend(data.get("data"))
            while data.get("cursor") != 0:
                data = get_data(data.get("cursor"))
                final_data.extend(data.get("data"))
            return final_data

        resp = self.run_cmd(func, dbs=[db], print_res=False, format_res=False)
        if len(resp) > 0:
            resp = resp[0]
            # print("host: %s" % resp.get("host"))
            # print("db: %s" % resp.get("db"))

            for item in resp.get("response"):
                print(f"key:   {self.app.colored_text.blue(item.get('key').decode('utf-8'))}")
                if value is True:
                    print(f"value: {self.app.colored_text.blue(item.get('val').decode('utf-8'))}")
                    print("--------------------------------------------")

    @ex(
        help=_("delete cache item"),
        description=_("delete cache item"),
        arguments=redis_args(
            [
                (["-port"], {"help": _("redis port"), "action": "store", "default": 443}),
                (
                    ["-pattern"],
                    {
                        "help": _("keys search pattern [default=*]"),
                        "action": "store",
                        "default": "*",
                    },
                ),
            ]
        ),
    )
    def cache_del(self):
        pattern = self.app.pargs.pattern
        pattern = "cache." + pattern

        def func(server):
            return server.delete(pattern=pattern)

        self.run_cmd(func, dbs=range(0, 8))
