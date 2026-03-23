# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from requests import get
from cement import ex

from beehive3_cli.core.util import load_environment_config
from beehive3_cli.plugins.platforms.controllers import (
    ChildPlatformController,
    PLATFORM_ARGS,
)
from beehive3_cli.translate import _


class NginxController(ChildPlatformController):
    class Meta:
        label = "nginx"
        description = _("Nginx management")
        help = _("Nginx management")

        default_group = "nginx"

    def pre_command_run(self):
        super().pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("nginx", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No nginx default platform is available for this environment. Select another environment"
                )

        if label not in orchestrators:
            raise Exception(f"Valid label are: {', '.join(orchestrators.keys())}")
        conf = orchestrators.get(label)

        self.hosts = conf.get("hosts")
        self.port = conf.get("port")

    def run_cmd(self, func, render=True):
        """Run command on nginx instances"""
        hosts = self.hosts

        resp = []
        for host in hosts:
            res = func(str(host))
            resp.append({"host": host, "response": res})
            self.app.log.info(f"Exec {func.__name__} on ngninx server {host!s} : {resp}")
        if render is True:
            self.app.render(resp, headers=["host", "response"], maxsize=200)
        return resp

    @ex(
        help=_("ping nginx instances"),
        description=_("ping nginx instances"),
        arguments=PLATFORM_ARGS([]),
    )
    def ping(self):
        def func(server):
            try:
                proxies = {
                    "http": None,
                    "https": None,
                }
                res = get(f"https://{server}:{self.port}", proxies=proxies, verify=False, timeout=120)
                self.app.log.debug(f"uri: https://{server}:{self.port}")
                res = res.status_code == 200
            except:
                self.app.log.warning("", exc_info=True)
                res = False

            return res

        self.run_cmd(func)

    @ex(
        description=_("get nginx instances status"),
        help=_("get nginx instances status"),
        arguments=PLATFORM_ARGS([]),
    )
    def status(self):
        def func(server):
            try:
                proxies = {
                    "http": None,
                    "https": None,
                }
                res = get(
                    f"https://{server}:{self.port}/nginx_status",
                    proxies=proxies,
                    verify=False,
                    timeout=120
                )
                self.app.log.debug(f"uri: https://{server}:{self.port}")
                if res.status_code == 200:
                    self.app.log.debug(res.text)
                    data = res.text.split("\n")
                    for item in data:
                        data[item] = data[item].split(" ")
                    res = {
                        "conns": {
                            "active": int(data[0][2]),
                            "accepts": int(data[2][1]),
                            "handled": int(data[2][2]),
                            "requests": int(data[2][3]),
                            "reading": int(data[3][1]),
                            "writing": int(data[3][3]),
                            "waiting": int(data[3][5]),
                        }
                    }
                else:
                    # print(res)
                    self.app.render(res)
            except:
                self.app.log.warning("", exc_info=1)
                res = False

            return res

        resp = self.run_cmd(func, render=False)
        headers = [
            "host",
            "active",
            "accepts",
            "handled",
            "requests",
            "reading",
            "writing",
            "waiting",
        ]
        fields = [
            "host",
            "response.conns.active",
            "response.conns.accepts",
            "response.conns.handled",
            "response.conns.requests",
            "response.conns.reading",
            "response.conns.writing",
            "response.conns.waiting",
        ]
        self.app.render(resp, headers=headers, fields=fields, maxsize=200)
