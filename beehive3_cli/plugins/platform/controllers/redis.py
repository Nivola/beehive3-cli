# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from json import dumps, loads
from time import sleep, time
from cement import ex
from beecell.db.manager import RedisManager
from beecell.types.type_list import merge_list
from beecell.types.type_id import id_gen
from beehive3_cli.core.controller import BASE_ARGS
from beehive3_cli.core.util import load_environment_config
from beehive3_cli.plugins.platform.controllers.k8s import BaseK8sController


def REDIS_ARGS(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": "redis cluster or single node reference label",
            },
        ),
        (
            ["-D", "--database"],
            {
                "action": "store",
                "dest": "database",
                "help": "redis database number",
                "default": 0,
            },
        ),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class RedisController(BaseK8sController):
    class Meta:
        label = "redis"
        description = "redis management"
        help = "redis management"

        default_group = "redis"

    def pre_command_run(self):
        super(RedisController, self).pre_command_run()

        self.sentinel_conf = None
        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("redis", {})
        label = getattr(self.app.pargs, "orchestrator", None)
        self.db = getattr(self.app.pargs, "database", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No redis default platform is available for this environment. Select " "another environment"
                )

        if label not in orchestrators:
            raise Exception("Valid label are: %s" % ", ".join(orchestrators.keys()))
        self.conf = orchestrators.get(label)

        self.sentinel_conf = self.conf.get("sentinel", None)

        services = self.list_service(self.default_namespace, name="redis")
        self.redis_service = services[0]

    def run_cmd(self, func, dbs=[0], print_res=True, format_res=True):
        """Run command on redis instances"""
        if self.sentinel_conf is None:
            host = self.conf.get("host")
            port = self.redis_service.spec.ports[0].node_port
            pwd = self.conf.get("pwd")
        else:
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
                    uri = "redis://:%s@%s:%s/%s" % (pwd, host, port, self.db)
                else:
                    uri = "redis://%s:%s/%s" % (host, port, self.db)
                server = RedisManager(uri)
                res = func(server)

            if format_res:
                if isinstance(res, dict):
                    for k, v in res.items():
                        resp.append({"response": "%s = %s" % (k, v)})
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
            raise

        return resp

    @ex(
        help="ping redis instances",
        description="ping redis instances",
        arguments=REDIS_ARGS([(["-port"], {"help": "redis port", "action": "store", "default": 443})]),
    )
    def ping(self):
        def func(server):
            return server.ping()

        self.run_cmd(func)

    @ex(
        help="ping redis sentinel instances",
        description="ping redis sentinel instances",
        arguments=REDIS_ARGS([(["-port"], {"help": "redis port", "action": "store", "default": 443})]),
    )
    def sentinel_ping(self):
        if self.sentinel_conf is not None:

            def func(server):
                return server.sentinel_ping()

            self.run_cmd(func)

    @ex(
        help="discover redis sentinel status",
        description="discover redis sentinel status",
        arguments=REDIS_ARGS([(["-port"], {"help": "redis port", "action": "store", "default": 443})]),
    )
    def sentinel_status(self):
        if self.sentinel_conf is not None:

            def func(server):
                return server.sentinel_status()

            res = self.run_cmd(func, print_res=False)
            self.app.render(res, headers=["response"], maxsize=200)

    @ex(
        help="test redis cluster",
        description="test redis cluster",
        arguments=REDIS_ARGS([(["-port"], {"help": "redis port", "action": "store", "default": 443})]),
    )
    def test(self):
        def test_case(server):
            key = "key-%s" % id_gen()
            start = time()
            try:
                value = {"prova": "test"}
                res = server.set(key, dumps(value))
                elapsed = round(time() - start, 4)
                print("  set: %s - server: %s [%s]" % (res, server.sentinel_discover(), elapsed))
            except Exception as ex:
                self.app.error("  get: %s" % ex)

            start = time()
            try:
                res = server.get(key)
                res = loads(res)
                if res.get("prova", None) == "test":
                    res = True
                else:
                    res = False
                elapsed = round(time() - start, 4)
                print("  get: %s - server: %s [%s]" % (res, server.sentinel_discover(), elapsed))
            except Exception as ex:
                self.app.error("  get: %s" % ex)

            start = time()
            try:
                res = server.delete_key(key)
                if res is None:
                    res = True
                else:
                    res = False
                elapsed = round(time() - start, 4)
                print("  del: %s - server: %s [%s]" % (res, server.sentinel_discover(), elapsed))
            except Exception as ex:
                self.app.error("  get: %s" % ex)

            start = time()
            try:
                res = server.get(key)
                if res is None:
                    res = True
                else:
                    res = False
                elapsed = round(time() - start, 4)
                print("  get: %s - server: %s [%s]" % (res, server.sentinel_discover(), elapsed))
            except Exception as ex:
                self.app.error("  get: %s" % ex)

        def func(server):
            for i in range(100):
                print("test case - %s" % i)
                test_case(server)
                sleep(2)

        self.run_cmd(func, print_res=False)

    @ex(
        help="info from redis instances",
        description="info from redis instances",
        arguments=REDIS_ARGS([(["-port"], {"help": "redis port", "action": "store", "default": 443})]),
    )
    def info(self):
        def func(server):
            return server.info()

        self.run_cmd(func)

    @ex(
        help="config of redis instances",
        description="config of redis instances",
        arguments=REDIS_ARGS([(["-port"], {"help": "redis port", "action": "store", "default": 443})]),
    )
    def confs(self):
        def func(server):
            return server.config()

        res = self.run_cmd(func, print_res=False)[0]["response"]
        self.app.render(res, details=True)

    @ex(
        help="summary of redis instances",
        description="summary of redis instances",
        arguments=REDIS_ARGS([(["-port"], {"help": "redis port", "action": "store", "default": 443})]),
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
        help="size of redis instances",
        description="size of redis instances",
        arguments=REDIS_ARGS([(["-port"], {"help": "redis port", "action": "store", "default": 443})]),
    )
    def size(self):
        def func(server):
            return server.size()

        self.run_cmd(func, dbs=range(0, 8))

    @ex(
        help="client list  of redis instances",
        description="client list  of redis instances",
        arguments=REDIS_ARGS([(["-port"], {"help": "redis port", "action": "store", "default": 443})]),
    )
    def client_list(self):
        def func(server):
            return server.server.client_list()

        self.run_cmd(func)

    @ex(
        help="flush redis instances",
        description="flush redis instances",
        arguments=REDIS_ARGS([(["-port"], {"help": "redis port", "action": "store", "default": 443})]),
    )
    def flush(self):
        def func(server):
            return server.server.flushall()

        self.run_cmd(func)

    @ex(
        help="inspect redis instances",
        description="inspect redis instances",
        arguments=REDIS_ARGS(
            [
                (["-port"], {"help": "redis port", "action": "store", "default": 443}),
                (
                    ["-pattern"],
                    {
                        "help": "keys search pattern [default=*]",
                        "action": "store",
                        "default": 443,
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
        help="scan redis instances",
        description="scan redis instances",
        arguments=REDIS_ARGS(
            [
                (["-port"], {"help": "redis port", "action": "store", "default": 443}),
                (
                    ["-db"],
                    {"help": "redis db [default=0]", "action": "store", "default": 0},
                ),
                (
                    ["-pattern"],
                    {
                        "help": "keys search pattern [default=*]",
                        "action": "store",
                        "default": "*",
                    },
                ),
                (
                    ["-cursor"],
                    {"help": "cursor [default=0]", "action": "store", "default": 0},
                ),
                (
                    ["-count"],
                    {"help": "cursor [default=10]", "action": "store", "default": 1000},
                ),
            ]
        ),
    )
    def scan(self):
        pattern = self.app.pargs.pattern
        cursor = self.app.pargs.cursor
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
            print("host: %s" % resp.get("host"))
            print("db: %s" % resp.get("db"))

            for item in resp.get("response"):
                print("--------------------------------------------")
                print("key:   %s" % self.app.colored_text.blue(item.get("key").decode("utf-8")))
                print("value: %s" % self.app.colored_text.blue(item.get("val").decode("utf-8")))

    @ex(
        help="get redis records by pattern",
        description="get redis records by pattern",
        arguments=REDIS_ARGS(
            [
                (["-port"], {"help": "redis port", "action": "store", "default": 443}),
                (
                    ["-pattern"],
                    {
                        "help": "keys search pattern [default=*]",
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

            # res = server.query(keys, ttl=False)
            # resp = []
            #
            # for k, v in res.items():
            #     try:
            #         v = v.decode('utf-8')
            #     except:
            #         pass
            #     resp.append('%s: %s' % (self.color_string(k.decode('utf-8'), 'BLUE'), v))
            return resp

        self.run_cmd(func, dbs=range(0, 8), print_res=False, format_res=False)

    @ex(
        help="set redis record",
        description="set redis record",
        arguments=REDIS_ARGS(
            [
                (["-port"], {"help": "redis port", "action": "store", "default": 443}),
                (["key"], {"help": "record key", "action": "store"}),
                (["value"], {"help": "record value", "action": "store"}),
            ]
        ),
    )
    def set(self):
        key = self.app.pargs.key
        value = self.app.pargs.value

        def func(server):
            resp = server.set(key=key, value=value)
            return resp

        self.run_cmd(func, dbs=range(0, 8))

    @ex(
        help="delete redis records",
        description="delete redis records",
        arguments=REDIS_ARGS(
            [
                (["-port"], {"help": "redis port", "action": "store", "default": 443}),
                (
                    ["-pattern"],
                    {
                        "help": "keys search pattern [default=*]",
                        "action": "store",
                        "default": 443,
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
        help="delete redis keys older than a value in seconds",
        description="delete redis keys older than a value in seconds",
        arguments=REDIS_ARGS(
            [
                (
                    ["seconds"],
                    {
                        "help": "min ttl accepted",
                        "action": "store",
                        "default": 443,
                        "type": int,
                    },
                ),
                (["-port"], {"help": "redis port", "action": "store", "default": 443}),
                (
                    ["-db"],
                    {"help": "redis db [default=0]", "action": "store", "default": 0},
                ),
                (
                    ["-pattern"],
                    {
                        "help": "keys search pattern [default=*]",
                        "action": "store",
                        "default": "*",
                    },
                ),
                (
                    ["-cursor"],
                    {"help": "cursor [default=0]", "action": "store", "default": 0},
                ),
                (
                    ["-count"],
                    {"help": "cursor [default=10]", "action": "store", "default": 50},
                ),
            ]
        ),
    )
    def deletes(self):
        seconds = self.app.pargs.seconds
        pattern = self.app.pargs.pattern
        cursor = self.app.pargs.cursor
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
                print("cursor: %s" % data.get("cursor"))
                data = get_data(data.get("cursor"))
            return data

        resp = self.run_cmd(func, dbs=[db], print_res=False, format_res=False)
        if len(resp) > 0:
            resp = resp[0]
            print("host: %s" % resp.get("host"))
            print("db: %s" % resp.get("db"))
            # print('cursor: %s' % resp.get('response').get('cursor'))
            # for item in resp.get('response').get('data'):
            #     check = False
            #     if item.get('ttl') < seconds:
            #         check = True
            #     print(item, check)
            #
            #     if check:
            #         def func(server):
            #             return server.delete_key(item.get('key'))
            #
            #         self.run_cmd(func, dbs=[db], print_res=False, format_res=False)

    @ex(
        help="get cache",
        description="get cache",
        arguments=REDIS_ARGS(
            [
                (["-port"], {"help": "redis port", "action": "store", "default": 443}),
                (
                    ["-db"],
                    {"help": "redis db [default=0]", "action": "store", "default": 0},
                ),
                (
                    ["-pattern"],
                    {
                        "help": "keys search pattern [default=*]",
                        "action": "store",
                        "default": "*",
                    },
                ),
                (
                    ["-cursor"],
                    {"help": "cursor [default=0]", "action": "store", "default": 0},
                ),
                (
                    ["-count"],
                    {"help": "count [default=10]", "action": "store", "default": 1000},
                ),
                (
                    ["-value"],
                    {
                        "help": "if True show cache value",
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
        cursor = self.app.pargs.cursor
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
            print("host: %s" % resp.get("host"))
            print("db: %s" % resp.get("db"))

            for item in resp.get("response"):
                print("key:   %s" % self.app.colored_text.blue(item.get("key").decode("utf-8")))
                if value is True:
                    print("value: %s" % self.app.colored_text.blue(item.get("val").decode("utf-8")))
                    print("--------------------------------------------")

    @ex(
        help="delete cache item",
        description="delete cache item",
        arguments=REDIS_ARGS(
            [
                (["-port"], {"help": "redis port", "action": "store", "default": 443}),
                (
                    ["-pattern"],
                    {
                        "help": "keys search pattern [default=*]",
                        "action": "store",
                        "default": 443,
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
