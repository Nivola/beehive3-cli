# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beedrones.datadomain.client import DataDomainManager
from beehive3_cli.core.controller import ARGS, PARGS
from beehive3_cli.core.util import load_environment_config
from cement import ex
from beehive3_cli.plugins.platform.controllers.k8s import BaseK8sController


class DataDomainController(BaseK8sController):
    class Meta:
        label = 'datadomain'
        description = "datadomain management"
        help = "datadomain management"

        default_group = 'datadomain'

    def pre_command_run(self):
        super(DataDomainController, self).pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get('orchestrators', {}).get('datadomain', {})
        label = getattr(self.app.pargs, 'cluster', None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception('No datadomain default platform is available for this environment. Select '
                                'another environment')

        if label not in orchestrators:
            raise Exception('Valid label are: %s' % ', '.join(orchestrators.keys()))
        conf = orchestrators.get(label)

        uri = '%s://%s:%s%s' % (conf.get('proto'), conf.get('hosts')[0], conf.get('port'), conf.get('path'))
        self.client = DataDomainManager(uri)
        self.client.authorize(conf.get('user'), conf.get('pwd'), key=self.key)

    def print_pagination(self, data):
        paging_info = data.get('paging_info')
        print('current_page: %s' % paging_info.get('current_page'))
        print('page_entries: %s' % paging_info.get('page_entries'))
        print('total_entries: %s' % paging_info.get('total_entries'))
        print('page_size: %s' % paging_info.get('page_size'))

    @ex(
        help='ping datadomain instances',
        description='ping datadomain instances',
        arguments=ARGS([
            (['-port'], {'help': 'datadomain port', 'action': 'store', 'default': 443})
        ])
    )
    def ping(self):
        def func(server):
            return server.ping()

        self.run_cmd(func)

    @ex(
        help='info from datadomain',
        description='info from datadomain',
        arguments=ARGS([])
    )
    def info(self):
        res = self.client.system.get()
        self.app.render(res, details=True)

    @ex(
        help='get datadomain settings',
        description='get datadomain settings',
        arguments=ARGS([
            (['id'], {'help': 'data domain system id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def setting_get(self):
        oid = self.app.pargs.id
        res = self.client.system.get_settings(oid)
        self.app.render(res, details=True)

    @ex(
        help='get datadomain services',
        description='get datadomain services',
        arguments=ARGS([
            (['id'], {'help': 'data domain system id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def services_get(self):
        oid = self.app.pargs.id
        res = self.client.system.get_services(oid)
        self.app.render(res.get('services'), headers=['name', 'status'])

    @ex(
        help='get datadomain users',
        description='get datadomain users',
        arguments=PARGS([
            (['id'], {'help': 'data domain system id', 'action': 'store', 'type': str, 'default': None}),
            (['-user_id'], {'help': 'data domain user id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def user_get(self):
        oid = self.app.pargs.id
        user_id = self.app.pargs.user_id
        if user_id is not None:
            res = self.client.user.get(oid, user_id)
            self.app.render(res, details=True)
        else:
            size = self.app.pargs.size
            page = self.app.pargs.page
            res = self.client.user.list(oid, size=size, page=page)
            if self.is_output_text():
                self.print_pagination(res)
            self.app.render(res.get('user'), headers=['uid', 'id', 'name', 'role', 'status'])

    @ex(
        help='get datadomain trust',
        description='get datadomain trust',
        arguments=PARGS([
            (['id'], {'help': 'data domain system id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def trust_get(self):
        oid = self.app.pargs.id
        res = self.client.trust.get(oid)
        self.app.render(res, details=True)

    @ex(
        help='get datadomain tenants',
        description='get datadomain tenants',
        arguments=PARGS([
            (['id'], {'help': 'data domain system id', 'action': 'store', 'type': str, 'default': None}),
            (['-tenant_id'], {'help': 'data domain tenant id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def tenant_get(self):
        oid = self.app.pargs.id
        tenant_id = self.app.pargs.tenant_id
        if tenant_id is not None:
            res = self.client.tenant.get(oid, tenant_id)
            self.app.render(res, details=True)
        else:
            size = self.app.pargs.size
            page = self.app.pargs.page
            res = self.client.tenant.list(oid, size=size, page=page)
            if self.is_output_text():
                self.print_pagination(res)
            self.app.render(res.get('tenant'), headers=['id', 'name'])

    @ex(
        help='get datadomain networks',
        description='get datadomain networks',
        arguments=PARGS([
            (['id'], {'help': 'data domain system id', 'action': 'store', 'type': str, 'default': None}),
            (['-network_id'], {'help': 'data domain network id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def network_get(self):
        oid = self.app.pargs.id
        network_id = self.app.pargs.network_id
        if network_id is not None:
            res = self.client.network.get(oid, network_id)
            self.app.render(res, details=True)
        else:
            size = self.app.pargs.size
            page = self.app.pargs.page
            res = self.client.network.list(oid, size=size, page=page)
            if self.is_output_text():
                self.print_pagination(res)
            self.app.render(res.get('network'), headers=['id', 'name'])

    @ex(
        help='get datadomain mtrees',
        description='get datadomain mtrees',
        arguments=PARGS([
            (['id'], {'help': 'data domain system id', 'action': 'store', 'type': str, 'default': None}),
            (['-mtree_id'], {'help': 'data domain mtree id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def mtree_get(self):
        oid = self.app.pargs.id
        mtree_id = self.app.pargs.mtree_id
        if mtree_id is not None:
            res = self.client.mtree.get(oid, mtree_id)
            self.app.render(res, details=True)
        else:
            size = self.app.pargs.size
            page = self.app.pargs.page
            res = self.client.mtree.list(oid, size=size, page=page)
            if self.is_output_text():
                self.print_pagination(res)
            self.app.render(res.get('mtree'), headers=['id', 'name'])

    @ex(
        help='get datadomain nfs exports',
        description='get datadomain nfs exports',
        arguments=PARGS([
            (['id'], {'help': 'data domain system id', 'action': 'store', 'type': str, 'default': None}),
            (['-nfs_id'], {'help': 'data domain nfs exports id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def protocol_nfs_get(self):
        oid = self.app.pargs.id
        nfs_id = self.app.pargs.nfs_id
        if nfs_id is not None:
            res = self.client.protocol.nfs.get(oid, nfs_id)
            self.app.render(res, details=True)
        else:
            size = self.app.pargs.size
            page = self.app.pargs.page
            res = self.client.protocol.nfs.list(oid, size=size, page=page)
            if self.is_output_text():
                self.print_pagination(res)
            self.app.render(res.get('exports'), headers=['id', 'path', 'path_status'], maxsize=200)

    @ex(
        help='add datadomain nfs exports',
        description='add datadomain nfs exports',
        arguments=PARGS([
            (['id'], {'help': 'data domain system id', 'action': 'store', 'type': str, 'default': None}),
            (['mtree'], {'help': 'mtree name', 'action': 'store', 'type': str, 'default': None}),
            (['path'], {'help': 'data domain nfs export path', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def protocol_nfs_add(self):
        oid = self.app.pargs.id
        mtree = self.app.pargs.mtree
        path = self.app.pargs.path
        res = self.client.protocol.nfs.add(oid, mtree, path)
        self.app.render({'msg': 'add mtree %s nfs export %s' % (mtree, path)})

    @ex(
        help='add datadomain nfs export client',
        description='add datadomain nfs export client',
        arguments=PARGS([
            (['id'], {'help': 'data domain system id', 'action': 'store', 'type': str, 'default': None}),
            (['nfs_id'], {'help': 'data domain nfs exports id', 'action': 'store', 'type': str, 'default': None}),
            (['client'], {'help': 'client fqdn', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def protocol_nfs_client_add(self):
        oid = self.app.pargs.id
        nfs_id = self.app.pargs.nfs_id
        client = self.app.pargs.client
        self.client.protocol.nfs.add_client(oid, nfs_id, client)
        self.app.render({'msg': 'add nfs %s export client %s' % (nfs_id, client)})

    @ex(
        help='delete datadomain nfs export client',
        description='delete datadomain nfs export client',
        arguments=PARGS([
            (['id'], {'help': 'data domain system id', 'action': 'store', 'type': str, 'default': None}),
            (['nfs_id'], {'help': 'data domain nfs exports id', 'action': 'store', 'type': str, 'default': None}),
            (['client'], {'help': 'client fqdn', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def protocol_nfs_client_del(self):
        oid = self.app.pargs.id
        nfs_id = self.app.pargs.nfs_id
        client = self.app.pargs.client
        self.client.protocol.nfs.del_client(oid, nfs_id, client)
        self.app.render({'msg': 'delete nfs %s export client %s' % (nfs_id, client)})
