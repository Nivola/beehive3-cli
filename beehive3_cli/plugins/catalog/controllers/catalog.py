# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from cement.ext.ext_argparse import ex
from beehive3_cli.core.controller import CliController, BaseController, ARGS, PARGS


class CatalogController(BaseController):
    class Meta:
        label = 'catalogs'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'api catalog management'
        help = 'api catalog management'

        cmp = {'baseuri': '/v1.0/ncs', 'subsystem': 'auth'}

        catalog_headers = ['uuid', 'name', 'zone', 'active', 'creation', 'modified']
        catalog_fields = ['uuid', 'name', 'zone', 'active', 'date.creation', 'date.modified']
        endpoint_headers = ['uuid', 'name', 'catalog.name', 'service', 'endpoint', 'active', 'creation', 'modified']
        endpoint_fields = ['uuid', 'name', 'catalog.name', 'service', 'endpoint', 'active', 'date.creation',
                           'date.modified']

    def _default(self):
        self._parser.print_help()

    def pre_command_run(self):
        super(CatalogController, self).pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help='get catalogs',
        description='get catalogs',
        arguments=PARGS([
            (['-id'], {'help': 'catalog uuid', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def get(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/catalogs/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)

            if self.is_output_text():
                # # get roles
                # data = urlencode({'catalog': oid, 'size': -1})
                # uri = '%s/endpoints' % self.baseuri
                # roles = self.cmp_get(uri, data).get('roles')

                services = res.get('catalog').pop('services')

                self.app.render(res, key='catalog', details=True)
                self.c('\nendpoints', 'underline')
                self.app.render(services, headers=['service', 'endpoints'], maxsize=200)
            else:
                self.app.render(res, key='catalog', details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/catalogs' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='catalogs', headers=self._meta.catalog_headers, fields=self._meta.catalog_fields)

    @ex(
        help='add catalog',
        description='add catalog',
        arguments=ARGS([
            (['name'], {'help': 'catalog name', 'action': 'store', 'type': str}),
            (['zone'], {'help': 'catalog zone', 'action': 'store', 'type': str}),
        ])
    )
    def add(self):
        name = self.app.pargs.name
        zone = self.app.pargs.zone
        res = self.api.client.catalog.create_catalog(name, zone)
        self.app.render({'msg': 'add catalog %s' % res['uuid']})

    @ex(
        help='delete catalog',
        description='delete catalog',
        arguments=ARGS([
            (['id'], {'help': 'catalog uuid', 'action': 'store', 'type': str}),
        ])
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = '%s/catalogs/%s' % (self.baseuri, oid)
        self.cmp_delete(uri, entity='catalog %s' % oid)

    @ex(
        help='get catalog endpoints',
        description='get catalog endpoints',
        arguments=PARGS([
            (['-id'], {'help': 'catalog endpoint uuid', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def get_endpoints(self):
        oid = getattr(self.app.pargs, 'id', None)
        if oid is not None:
            uri = '%s/endpoints/%s' % (self.baseuri, oid)
            res = self.cmp_get(uri)
            self.app.render(res, key='endpoint', details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = '%s/endpoints' % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key='endpoints', headers=self._meta.endpoint_headers, 
                            fields=self._meta.endpoint_fields)

    @ex(
        help='add catalog endpoint',
        description='add catalog endpoint',
        arguments=ARGS([
            (['name'], {'help': 'catalog endpoint name', 'action': 'store', 'type': str}),
            (['catalog'], {'help': 'catalog uuid', 'action': 'store', 'type': str}),
            (['service'], {'help': 'service name like auth or resource', 'action': 'store', 'type': str}),
            (['uri'], {'help': 'service uri', 'action': 'store', 'type': str}),
        ])
    )
    def add_endpoint(self):
        name = self.app.pargs.name
        catalog = self.app.pargs.catalog
        service = self.app.pargs.service
        uri = self.app.pargs.uri
        
        # if endpoint exist update it else create new one
        try:
            res = self.api.client.catalog.get_endpoint(name)
            res = self.api.client.catalog.update_endpoint(name, catalog_id=catalog, name=name, service=service,
                                                          uri=uri)
        except Exception as ex:
            res = self.api.client.catalog.create_endpoint(catalog, name, service, uri)
        self.app.render({'msg': 'add catalog endpoint %s' % res['uuid']})

    @ex(
        help='delete catalog endpoint',
        description='delete catalog endpoint',
        arguments=ARGS([
            (['id'], {'help': 'catalog endpoint uuid', 'action': 'store', 'type': str}),
        ])
    )
    def delete_endpoint(self):
        oid = self.app.pargs.id
        self.api.client.catalog.delete_endpoint(oid)

    @ex(
        help='ping catalog endpoint',
        description='ping catalog endpoint',
        arguments=ARGS([
            (['id'], {'help': 'catalog endpoint uuid', 'action': 'store', 'type': str}),
        ])
    )
    def ping_endpoint(self):
        oid = self.app.pargs.id
        endpoint = self.api.client.catalog.get_endpoint(oid).get('endpoint').get('endpoint')
        # todo: ping
        res = self.api.client.ping(endpoint=endpoint)
        self.app.render({'endpoint': endpoint, 'ping': res}, headers=['endpoint', 'ping'])

    @ex(
        help='ping catalog endpoints',
        description='ping catalog endpoints',
        arguments=ARGS([
            (['id'], {'help': 'catalog uuid', 'action': 'store', 'type': str}),
        ])
    )
    def ping_endpoints(self):
        oid = self.app.pargs.id
        services = []
        catalog = self.api.client.catalog.get_catalog(oid)
        for v in catalog.get('services', {}):
            for v1 in v.get('endpoints', []):
                # todo: ping
                res = self.api.client.ping(endpoint=v1)
                services.append({'service': v['service'], 'endpoint': v1, 'ping': res})
        self.app.render(services, headers=['service', 'endpoint', 'ping'])         
