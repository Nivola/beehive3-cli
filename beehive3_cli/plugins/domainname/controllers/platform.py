# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement import ex
from beecell.simple import merge_list
from beedrones.dns.client import DnsManager

from beehive3_cli.core.controller import BaseController, BASE_ARGS
from beehive3_cli.core.util import load_environment_config
from beehive3_cli.translate import _


def dns_args(*list_args):
    orchestrator_args = [
        (
            ["-O", "--orchestrator"],
            {
                "action": "store",
                "dest": "orchestrator",
                "help": _("dns platform reference label"),
            },
        ),
        (
            ["-P", "--project"],
            {"action": "store", "dest": "project", "help": _("dns current project name")},
        ),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class DnsPlatformController(BaseController):
    class Meta:
        label = "dns"
        stacked_on = "platform"
        stacked_type = "nested"
        description = _("dns platform")
        help = _("dns platform")

    def pre_command_run(self):
        super().pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("dns", {})
        label = getattr(self.app.pargs, "orchestrator", None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception(
                    "No dns default platform is available for this environment. Select another environment"
                )

        if label not in orchestrators:
            raise Exception(f"Valid label are: {', '.join(orchestrators.keys())}")
        conf = orchestrators.get(label)

        self.client = DnsManager(
            conf.get("serverdns"),
            zones=conf.get("zones"),
            dnskey=conf.get("key"),
            key=self.key,
        )

    @ex(help=_("ping dns"), description=_("ping dns"), arguments=dns_args())
    def ping(self):
        res = self.client.ping()
        self.app.render({"ping": res}, headers=["ping"])

    @ex(help=_("get dns version"), description=_("get dns version"), arguments=dns_args())
    def version(self):
        res = self.client.version()
        self.app.render({"version": res}, headers=["version"])

    @ex(
        help=_("get all the configured orchestrators"),
        description=_("get all the configured orchestrators"),
        arguments=dns_args(),
    )
    def zone_orchestrator_get(self):
        orchestrators = self.config.get("orchestrators", {}).get("dns", {})

        # orchestrators = self.configs['environments'][self.env]['orchestrators'].get('dns')
        resp = []
        for k, v in orchestrators.items():
            update = True
            if v.get("key", {}) == {}:
                update = False
            item = {
                "name": k,
                "nameservers": v.get("serverdns", {}).get("resolver", []),
                "zones": v.get("zones", []),
                "support_update": update,
            }
            resp.append(item)
        self.app.render(
            resp,
            headers=["name", "nameservers", "zones", "support_update"],
            maxsize=200,
        )

    @ex(
        help=_("get all the managed zones"),
        description=_("get all the managed zones"),
        arguments=dns_args(),
    )
    def zone_get(self):
        zones = self.client.get_managed_zones()
        resp = [{"label": k, "zone": v} for k, v in zones.items()]
        self.app.render(resp, headers=["label", "zone"])

    @ex(
        help=_("get all the nameservers that resolve the zone"),
        description=_("get all the nameservers that resolve the zone"),
        arguments=dns_args(
            [
                (
                    ["id"],
                    {"help": _("zone"), "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def zone_nameserver_get(self):
        zone = self.app.pargs.id
        res = self.client.query_nameservers(zone, timeout=1.0)
        resp = []
        for k, vs in res.items():
            if vs is not None:
                for v in vs:
                    resp.append({"start-nameserver": k, "ip_addr": v[0], "fqdn": v[1]})
        self.app.render(resp, headers=["start-nameserver", "ip_addr", "fqdn"])

    @ex(
        help=_("the SOA (Start of Authority) used to manage the zone"),
        description=_("the SOA (Start of Authority) used to manage the zone"),
        arguments=dns_args(
            [
                (
                    ["id"],
                    {"help": _("zone"), "action": "store", "type": str, "default": None},
                ),
            ]
        ),
    )
    def zone_authority_get(self):
        """
        - start-nameserver: dns queried
        - mname: The <domain-name> of the name server that was the original or primary source of data for this zone.
        - rname: A <domain-name> which specifies the mailbox of the person responsible for this zone.
        - serial: The unsigned 32 bit version number of the original copy of the zone. Zone transfers preserve this
            value. This value wraps and should be compared using sequence space arithmetic.
        - refresh: A 32 bit time interval before the zone should be refreshed.
        - retry: A 32 bit time interval that should elapse before a failed refresh should be retried.
        - expire: A 32 bit time value that specifies the upper limit on the time interval that can elapse before the
            zone is no longer authoritative.
        - minimum: The unsigned 32 bit minimum TTL field that should be exported with any RR from this zone.
        All times are in units of seconds.
        """
        zone = self.app.pargs.id
        res = self.client.query_authority(zone)
        resp = []
        for k, v in res.items():
            v["start-nameserver"] = k
            resp.append(v)
        self.app.render(
            resp,
            headers=[
                "start-nameserver",
                "rname",
                "mname",
                "retry",
                "minimum",
                "refresh",
                "expire",
                "serial",
            ],
        )

    @ex(
        help=_("get ip address form fqdn"),
        description=_("get ip address form fqdn"),
        arguments=dns_args(
            [
                (
                    ["fqdn"],
                    {"help": _("fqdn"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-group"],
                    {
                        "help": _("dns group. Can be resolver or update [default=resolver]"),
                        "action": "store",
                        "type": str,
                        "default": "resolver",
                    },
                ),
            ]
        ),
    )
    def zone_fqdn_query(self):
        host = self.app.pargs.fqdn
        group = self.app.pargs.group
        res = self.client.query_record_A(host, timeout=1.0, group=group, return_error=True)
        resp = []
        for k, v in res.items():
            resp.append({"start-nameserver": k, "ip-address": v})
        self.app.render(resp, headers=["start-nameserver", "ip-address"])

    @ex(
        help=_("get fqdn address form alias"),
        description=_("get fqdn address form alias"),
        arguments=dns_args(
            [
                (
                    ["alias"],
                    {"help": _("alias"), "action": "store", "type": str, "default": None},
                ),
                (
                    ["-group"],
                    {
                        "help": _("dns group. Can be resolver or update [default=resolver]"),
                        "action": "store",
                        "type": str,
                        "default": "resolver",
                    },
                ),
            ]
        ),
    )
    def zone_alias_query(self):
        alias = self.app.pargs.alias
        group = self.app.pargs.group
        res = self.client.query_record_CNAME(alias, timeout=1.0, group=group, return_error=True)
        resp = []
        for k, v in res.items():
            resp.append({"start-nameserver": k, "base-fqdn": v})
        self.app.render(resp, headers=["start-nameserver", "base-fqdn"])
