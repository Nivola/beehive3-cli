# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement.ext.ext_argparse import ex
from beehive3_cli.core.controller import BaseController, ARGS, PARGS
from beehive3_cli.translate import _


class CatalogController(BaseController):
    class Meta:
        label = "catalogs"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("api catalog management")
        help = _("api catalog management")

        cmp = {"baseuri": "/v1.0/ncs", "subsystem": "auth"}

        catalog_headers = ["uuid", "name", "zone", "active", "creation", "modified"]
        catalog_fields = [
            "uuid",
            "name",
            "zone",
            "active",
            "date.creation",
            "date.modified",
        ]
        endpoint_headers = [
            "uuid",
            "name",
            "catalog.name",
            "service",
            "endpoint",
            "active",
            "creation",
            "modified",
        ]
        endpoint_fields = [
            "uuid",
            "name",
            "catalog.name",
            "service",
            "endpoint",
            "active",
            "date.creation",
            "date.modified",
        ]

    def _default(self):
        self._parser.print_help()

    def pre_command_run(self):
        super().pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help=_("get catalogs"),
        description=_("get catalogs"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("catalog uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/catalogs/{oid}"
            res = self.cmp_get(uri)

            if self.is_output_text():
                # # get roles
                # data = urlencode({'catalog': oid, 'size': -1})
                # uri = '%s/endpoints' % self.baseuri
                # roles = self.cmp_get(uri, data).get('roles')

                services = res.get("catalog").pop("services")

                self.app.render(res, key="catalog", details=True)
                self.c("\nendpoints", "underline")
                self.app.render(services, headers=["service", "endpoints"], maxsize=200)
            else:
                self.app.render(res, key="catalog", details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/catalogs"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="catalogs",
                headers=self._meta.catalog_headers,
                fields=self._meta.catalog_fields,
            )

    @ex(
        help=_("add catalog"),
        description=_("add catalog"),
        arguments=ARGS(
            [
                (["name"], {"help": _("catalog name"), "action": "store", "type": str}),
                (["zone"], {"help": _("catalog zone"), "action": "store", "type": str}),
            ]
        ),
    )
    def add(self):
        name = self.app.pargs.name
        zone = self.app.pargs.zone
        res = self.api.client.catalog.create_catalog(name, zone)
        self.app.render({"msg": f"add catalog {res['uuid']}"})

    @ex(
        help=_("delete catalog"),
        description=_("delete catalog"),
        arguments=ARGS(
            [
                (["id"], {"help": _("catalog uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/catalogs/{oid}"
        self.cmp_delete(uri, entity=f"catalog {oid}")

    @ex(
        help=_("get catalog endpoints"),
        description=_("get catalog endpoints"),
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("catalog endpoint uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get_endpoints(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/endpoints/{oid}"
            res = self.cmp_get(uri)
            self.app.render(res, key="endpoint", details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/endpoints"
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="endpoints",
                headers=self._meta.endpoint_headers,
                fields=self._meta.endpoint_fields,
            )

    @ex(
        help=_("add catalog endpoint"),
        description=_("add catalog endpoint"),
        arguments=ARGS(
            [
                (
                    ["name"],
                    {"help": _("catalog endpoint name"), "action": "store", "type": str},
                ),
                (["catalog"], {"help": _("catalog uuid"), "action": "store", "type": str}),
                (
                    ["service"],
                    {
                        "help": _("service name like auth or resource"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (["uri"], {"help": _("service uri"), "action": "store", "type": str}),
            ]
        ),
    )
    def add_endpoint(self):
        name = self.app.pargs.name
        catalog = self.app.pargs.catalog
        service = self.app.pargs.service
        uri = self.app.pargs.uri

        # if endpoint exist update it else create new one
        try:
            res = self.api.client.catalog.get_endpoint(name)
            res = self.api.client.catalog.update_endpoint(name, catalog_id=catalog, name=name, service=service, uri=uri)
        except Exception:
            res = self.api.client.catalog.create_endpoint(catalog, name, service, uri)
        self.app.render({"msg": f"add catalog endpoint {res['uuid']}"})

    @ex(
        help=_("delete catalog endpoint"),
        description=_("delete catalog endpoint"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("catalog endpoint uuid"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def delete_endpoint(self):
        oid = self.app.pargs.id
        self.api.client.catalog.delete_endpoint(oid)

    @ex(
        help=_("ping catalog endpoint"),
        description=_("ping catalog endpoint"),
        arguments=ARGS(
            [
                (
                    ["id"],
                    {"help": _("catalog endpoint uuid"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def ping_endpoint(self):
        oid = self.app.pargs.id
        endpoint = self.api.client.catalog.get_endpoint(oid).get("endpoint").get("endpoint")
        res = self.api.client.ping(endpoint=endpoint)
        self.app.render({"endpoint": endpoint, "ping": res}, headers=["endpoint", "ping"])

    @ex(
        help=_("ping catalog endpoints"),
        description=_("ping catalog endpoints"),
        arguments=ARGS(
            [
                (["id"], {"help": _("catalog uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def ping_endpoints(self):
        oid = self.app.pargs.id
        services = []
        catalog = self.api.client.catalog.get_catalog(oid)
        for v in catalog.get("services", {}):
            for v1 in v.get("endpoints", []):
                res = self.api.client.ping(endpoint=v1)
                services.append({"service": v["service"], "endpoint": v1, "ping": res})
        self.app.render(services, headers=["service", "endpoint", "ping"])
