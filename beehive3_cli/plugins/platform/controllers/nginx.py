# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from requests import get
from beehive3_cli.core.util import load_environment_config
from beehive3_cli.plugins.platform.controllers import (
    ChildPlatformController,
    PLATFORM_ARGS,
)
from cement import ex


class NginxController(ChildPlatformController):
    class Meta:
        label = "nginx"
        description = "Nginx management"
        help = "Nginx management"

        default_group = "nginx"

    def pre_command_run(self):
        super(NginxController, self).pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("nginx", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No nginx default platform is available for this environment. Select " "another environment"
                )

        if label not in orchestrators:
            raise Exception("Valid label are: %s" % ", ".join(orchestrators.keys()))
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
            self.app.log.info("Exec %s on ngninx server %s : %s" % (func.__name__, str(host), resp))
        if render is True:
            self.app.render(resp, headers=["host", "response"], maxsize=200)
        return resp

    @ex(
        help="ping nginx instances",
        description="ping nginx instances",
        arguments=PLATFORM_ARGS([]),
    )
    def ping(self):
        def func(server):
            try:
                proxies = {
                    "http": None,
                    "https": None,
                }
                res = get("https://%s:%s" % (server, self.port), proxies=proxies, verify=False)
                self.app.log.debug("uri: https://%s:%s" % (server, self.port))
                if res.status_code == 200:
                    res = True
                else:
                    res = False
            except:
                self.app.log.warning("", exc_info=True)
                res = False

            return res

        self.run_cmd(func)

    @ex(
        description="get nginx instances status",
        help="get nginx instances status",
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
                    "https://%s:%s/nginx_status" % (server, self.port),
                    proxies=proxies,
                    verify=False,
                )
                self.app.log.debug("uri: https://%s:%s" % (server, self.port))
                if res.status_code == 200:
                    self.app.log.debug(res.text)
                    data = res.text.split("\n")
                    for item in range(0, len(data)):
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

    #
    # @ex(
    #     description='get nginx instances engine status',
    #     help='get nginx instances engine status',
    #     arguments=PLATFORM_ARGS()
    # )
    # def engine_status(self):
    #     self.ansible_task('nginx', 'systemctl status nginx')
    #
    # @ex(
    #     description='start nginx instances',
    #     help='start nginx instances',
    #     arguments=PLATFORM_ARGS()
    # )
    # def engine_start(self):
    #     self.ansible_task('nginx', 'systemctl start nginx')
    #
    # @ex(
    #     description='stop nginx instances',
    #     help='stop nginx instances',
    #     arguments=PLATFORM_ARGS()
    # )
    # def engine_stop(self):
    #     self.ansible_task('nginx', 'systemctl stop nginx')
    #
    # @ex(
    #     description='update nginx configuration',
    #     help='update nginx configuration',
    #     arguments=PLATFORM_ARGS()
    # )
    # def config(self):
    #     run_data = {
    #         'tags': ['config']
    #     }
    #     self.ansible_playbook('nginx', run_data, playbook=self.nginx_playbook)
    #
    # @ex(
    #     description='deploy ssl certificate to nginx instances',
    #     help='deploy ssl certificate to nginx instances',
    #     arguments=PLATFORM_ARGS([
    #         (['cert-file'], {'help': 'file certificate', 'action': 'store', 'default': None}),
    #         (['cert-file-key'], {'help': 'file certificate key', 'action': 'store', 'default': None}),
    #     ])
    # )
    # def deploy_cert(self):
    #     """Deploy nginx ssl certificate
    #     """
    #     cert_file = self.app.pargs.cert_file
    #     cert_file_key = self.app.pargs.cert_file_key
    #     run_data = {
    #         'tags': ['deploy-cert'],
    #         'cert_file': cert_file,
    #         'cert_file_key': cert_file_key
    #     }
    #     self.ansible_playbook('nginx', run_data, playbook=self.nginx_playbook)
