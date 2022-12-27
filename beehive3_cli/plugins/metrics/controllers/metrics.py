# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import logging

from datetime import datetime, timedelta
from cement.ext.ext_argparse import ex
from beehive3_cli.core.controller import CliController, BaseController, ARGS, PARGS
from urllib.parse import urlencode
from beehive3_cli.core.util import list_environments, load_environment_config
from beedrones.openstack.client import OpenstackManager
from beedrones.trilio.client import TrilioManager
from beecell.simple import str2bool, random_password, format_date, dict_get
from beedrones.zabbix.client import ZabbixManager
from beecell.db import MysqlManager
from beecell.simple import jsonDumps

from pprint import pprint
import requests
from six import string_types

logger = logging.getLogger(__name__)

class MetricsBaseController(BaseController):
    class Meta:

        # cmp = {'baseuri': '/v1.0/nrs/provider', 'subsystem': 'resource'}
        cmp_resource = {'baseuri': '/v1.0/nrs', 'subsystem': 'resource'}
        cmp_service= {'baseuri': '/v1.0/nws', 'subsystem': 'service'}


    @property
    def cmpService(self):
        return self._meta.cmp_service

    @property
    def cmpResource(self):
        return self._meta.cmp_resource

    def configure_cmp_resource(self):
        self._meta.cmp = self._meta.cmp_resource
        # print('######################### CONFIGURED CMP  ###################### {}' .format(pprint(self._meta.cmp)))
        self.configure_cmp_api_client()
  
    def configure_cmp_service(self):
        self._meta.cmp = self._meta.cmp_service 
        # print('######################### CONFIGURED CMP  ###################### {}' .format(pprint(self._meta.cmp)))
        self.configure_cmp_api_client()

    def pre_command_run(self):
        super(MetricsBaseController, self).pre_command_run()
        self.config = load_environment_config(self.app)

class MetricsController(MetricsBaseController):
    class Meta:
        label = 'metrics'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'api metrics management'
        help = 'api metrics management'

        compute_zones_headers = ['uuid','id', 'name','desc', 'parent','state','active','runstate','creation','modified']
        compute_zones_fields  = ['uuid','id', 'name','desc', 'parent','state','active','runstate','date.creation','date.modified']

        backup_headers = ['id', 'uuid', 'name', 'compute_service_uuid', 'compute_service_name',
                   'trilio_used_capacity [GB]', 'veeam_used_capacity [GB]']
        backup_headers_fields = ['id', 'uuid', 'name', 'compute_service.uuid', 'compute_service.name',
                  'compute_service.trilio_used_capacity.tot', 'compute_service.veeam_used_capacity.tot']

        monit_headers = ['id', 'uuid', 'name', 'compute_service_uuid', 'match',
                   'Monit Hosts Number']
        monit_headers_fields = ['account_id', 'account_uuid', 'name', 'compute_service_uuid', 'match_found',
                  'monit_hosts']          
    # def _default(self):
    #     self._parser.print_help()

    def pre_command_run(self):
        super(MetricsController, self).pre_command_run()

    @ex(
        help='backup',
        description='get bck',
        arguments=PARGS([
            (['-id'], {'help': 'account id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def get_bck(self):
        oid = getattr(self.app.pargs, 'id', None)
        account = {}
        accounts = self.get_accounts(oid)
        compute_zones = self.get_compute_zones()

        compute_zones_uuids = {str(r['uuid']): r for r in compute_zones}
        compute_services = self.get_compute_services()
        veeam_usage = self.get_veeam_usage()
        trilio_usage = self.get_trilio_usage()

        for cs in compute_services:
            cz = compute_zones_uuids[cs['resource_uuid']]
            cz_id = cz['name'][15:len(cz['name'])]
            used_capacity = trilio_usage.get(cz['name'], {})
            if accounts.get(cs['account_id']) is not None:
                accounts[cs['account_id']][u'compute_service'] = {
                    u'uuid': cs['uuid'],
                    u'name': cz['name'],
                    u'trilio_used_capacity': used_capacity,
                    u'veeam_used_capacity': veeam_usage.get(cz_id, {})
                }
        res = [value for value in accounts.values()]  
        self.app.render(res, headers=self._meta.backup_headers, fields=self._meta.backup_headers_fields)


    @ex(
        help='backup',
        description='add bck metrics',
        arguments=PARGS([
            (['-id'], {'help': 'account id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def add_bck_metrics(self):
        oid = getattr(self.app.pargs, 'id', None)

        czs = self.get_compute_zones()
        czs = {str(r['uuid']): r for r in czs}
        css = self.get_compute_services()

        accounts = self.get_accounts(oid)
        trilio_usage = self.get_trilio_usage()
        veeam_usage = self.get_veeam_usage()

        # imposto cmp service per tutti i methodi sottostanti
        self.configure_cmp_service() 
        self.metrictypes = self.get_metrictypes()

        for cs in css:
            cz = czs[cs['resource_uuid']]
            cz_id = cz['name'][15:len(cz['name'])]
            used_capacity = trilio_usage.get(cz['name'], {})
            if accounts.get(cs['account_id']) is not None:
                accounts[cs['account_id']][u'compute_service'] = {
                    u'uuid': cs['uuid'],
                    u'id': cs['id'],
                    u'name': cz['name'],
                    u'trilio_used_capacity': used_capacity,
                    u'veeam_used_capacity': veeam_usage.get(cz_id, {})
                }

        accounts = accounts.values()
        for a in accounts:
            try:
                print('add or replace metrics for account %s %s' % (a.get('uuid'), a.get('name')))
                service_id = a.get('compute_service', {}).get('id', None)
                trilio_used_capacity = dict_get(a, 'compute_service.trilio_used_capacity.tot')
                veeam_used_capacity = dict_get(a, 'compute_service.veeam_used_capacity.tot')

                # now = datetime.today().date()
                # date = '%sT00:00:00Z' % str(now)
                date = datetime.today().strftime("%Y-%m-%dT%H:%M:%SZ")
                print ("===========================%s" % date)

                os_metrictype = 'vm_backup_os1'
                if trilio_used_capacity is not None and trilio_used_capacity > 500:
                    os_metrictype = 'vm_backup_os2'
                if service_id is not None and trilio_used_capacity is not None:
                    self.add_or_replace_metric(service_id, trilio_used_capacity, os_metrictype, date)
                if service_id is not None and veeam_used_capacity is not None:
                    self.add_or_replace_metric(service_id, veeam_used_capacity, 'vm_backup_com', date)
            except Exception as ex:
                logger.warning(ex, exc_info=True)
                print("==============ERR") 
                print(ex) 
    
    @ex(
        help='monitoring metrics',
        description='Create monitoring metrics',
        arguments=PARGS([ ])
    )
    def add_monit_metrics(self):
        """
            Create monitoring metric.

        Fields:
        account    account uuid or composed name (org.div.account)
        """
        self.configure_cmp_service()
        self.metrictypes = self.get_metrictypes()
        metricsdate = datetime.today().strftime("%Y-%m-%dT%H:%M:%SZ")
        print ("===========================%s" % metricsdate)
        usage_list = self.get_monit_list()

        for item in usage_list:
            self.add_or_replace_metric(item['compute_service_id'], item['monit_hosts'], 'vm_monit', metricsdate)
            pass

    
    @ex(
        help='get monitoring metrics',
        description='Get monitoring metrics',
        arguments=PARGS([ ])
    )
    def get_monit_metrics(self):
        """
            get monitoring metric.

        Fields:
        account    account uuid or composed name (org.div.account)
        """
        self.configure_cmp_service()
        self.metrictypes = self.get_metrictypes()
        metricsdate = datetime.today().strftime("%Y-%m-%dT%H:%M:%SZ")
        print ("===========================%s" % metricsdate)
        usage_list = self.get_monit_list()
        self.app.render(usage_list, headers=self._meta.monit_headers, fields=self._meta.monit_headers_fields)

    @ex(
        help='update-volumes',
        description='update-volumes',
        arguments=PARGS([ ])
    )
    def add_volumes_info(self):
        """ estrai dati circa i volumi e li carica nelle strutture temporanee di gestione dei volumi.
        N.B. idempotente
        """
        vols = self.get_volumes()
        server = self.get_db_connection()
        print ("=========================== creating connection to db" )

        server.create_simple_engine()

        try:
            connection = server.engine.connect()
            for item in vols:
                self.add_or_update_volume_item(connection, item)
        except Exception as ex:
            logger.warning(ex, exc_info=True)
            print(ex)
        finally:
            if connection is not None:
                self.finalize_volumes_update(connection)
                connection.close()

    @ex(
        help='update-oracle',
        description='update-oracle',
        arguments=PARGS([ ])
    )
    def add_oracle_info(self):
        """ estrai dati circa i database oracle e li carica nelle strutture temporanee di gestione dei db.
        N.B. idempotente
        """

        dbs = self.get_oracle_dbs()
        server = self.get_db_connection()
        server.create_simple_engine()

        try:
            connection = server.engine.connect()
            for item in dbs:
                self.add_or_update_ora_dbitem(connection, item)
        except Exception as ex:
            logger.warning(ex, exc_info=True)
            print(ex)
        finally:
            if connection is not None:
                finalize = '''UPDATE service.tmp_databases_ td
                set uuid = (SELECT  si.uuid  from service.service_instance si where si.resource_uuid = td.resource_uuid ),
                    fk_service_instance_id = (SELECT  si.id  from service.service_instance si where si.resource_uuid  = td.resource_uuid )
                where  uuid  is NULL '''
                connection.execute(finalize)
                connection.close()


    def get_compute_zones(self, index='uuid'):
        self.configure_cmp_resource() 
        data = urlencode({ 'size': -1})
        uri = '%s/provider/compute_zones' % self.baseuri
        res = self.cmp_get(uri, data=data)
        print('Total compute zone instances: %s' % len(res))
        # print('######################### get_compute_service ###################### {}' .format(pprint(res.get('compute_zones'))))

        return res.get('compute_zones',[])


    def get_compute_services(self):
        self.configure_cmp_service() 
        data = urlencode({ 'plugintype':'ComputeService','size': -1})
        uri = '%s/serviceinsts' % self.baseuri
        res = self.cmp_get(uri, data=data)
        print('Total compute services instances:: %s' % len(res))

        # print('######################### get_compute_service ###################### {}' .format(pprint(res)))

        return res.get('serviceinsts',[])

    def get_accounts(self,oid=None):
        self.configure_cmp_service() 
        data = urlencode({'size': -1})
        uri = u'%s/accounts' % self.baseuri
        accounts = []
        if oid is not None:
            uri = u'%s/accounts/%s' % (self.baseuri, oid)
            account = self.cmp_get(uri, data=data).get(u'account', [])
            accounts = [account]
        else:
            accounts = self.cmp_get(uri, data=data).get(u'accounts', [])
        print('Total accounts: %s' % len(accounts))
        return {str(a['id']): a for a in accounts}

    def get_veeam_usage(self):
        tenants_usage = {}
        uri = self.config[u'orchestrators'][u'veeam'].get(u'usage_uri', None)

        if uri is not None:
            res = requests.get(uri)
            data = res.json()
            jobs = {}
        
            for item in data:     
                job_names = item['Job']

                if isinstance(job_names, string_types) :
                    job_names = [job_names]

                for job_name in job_names:
                    if job_name.find('BCK') == 0:
                        cz_id = job_name.split('-')[1]
                        if job_name[4:-1] in jobs:
                            jobs.pop(job_name[4:-1])
                    elif job_name.find('avz') > 0:
                        cz_id = job_name.split('-')[0]
                    else:
                        cz_id = job_name.split('_')[0]

                    if job_name.lower().find(self.env) == 0:
                        continue

                    used_capacity = item.get('jobBackupSize', 0) / 1073741824
                            
                    if cz_id in tenants_usage:
                        tenants_usage[cz_id][self.env] = used_capacity
                        tenants_usage[cz_id]['tot'] += used_capacity
                        tenants_usage[cz_id]['name'] = job_name
                    else:
                        tenants_usage[cz_id] = { self.env: used_capacity, 'tot': used_capacity, 'name': job_name}
            # print('######################### tenants_veeam_usage ###################### {}' .format(pprint(tenants_usage)))

        return tenants_usage


    def get_trilio_usage(self):
        tenants_usage = {}
        # get OpenStack configuration settings for given environment
        uri, region, user, password, project, domain = self.get_openstack_config_settings()
         # create instance of OpenStack manager
        if uri and user and password is not None:
            openstack_manager = OpenstackManager(uri=uri, default_region=region)
            openstack_manager.authorize(user, password, project=project, domain=domain, key=self.key)
        else:
            raise Exception(u'OpenstackError: missing config settings.')
            # create instance of Trilio client
        trilio_client = TrilioManager(openstack_manager)
            # get storage usage by tenant
        res = trilio_client.job_scheduler.get_tenant_usage()
        for item in res[u'tenants_usage'].items():
            if item[1].__contains__('tenant_name'):
                name = item[1]['tenant_name'][0:23]
                # keep only tenants with non-null backup
                if item[1].get(u'used_capacity') > 0:
                    used_capacity = item[1].get('used_capacity', 0)
                    used_capacity = used_capacity / 1073741824
                    if name in tenants_usage:
                        tenants_usage[name][self.env] = used_capacity
                        tenants_usage[name]['tot'] += used_capacity
                    else:
                        tenants_usage[name] = {self.env: used_capacity, 'tot': used_capacity}
        print('get trilio usage pod %s' % self.env)
        # print('######################### tenants_trilio_usage ###################### {}' .format(pprint(tenants_usage)))

        return tenants_usage

    def get_zabbix_config_settings(self):
        uri = None
        user = None
        password = None

        uri = self.config[u'orchestrators'][u'zabbix'].get(u'uri', None)
        user = self.config[u'orchestrators'][u'zabbix'].get(u'user', None)
        password = self.config[u'orchestrators'][u'zabbix'].get(u'pwd', None)

        # for debug purposes
        # print(u'uri      : ' + uri)
        # print(u'user     : ' + user)
        # print(u'password : ' + password)

        return uri, user, password

    def get_openstack_config_settings(self):
        uri = None
        region = None
        user = None
        password = None
        project = None
        domain = None

        uri = self.config[u'orchestrators'][u'openstack'].get(u'uri', None)
        region = self.config[u'orchestrators'][u'openstack'].get(u'region', None)
        user = self.config[u'orchestrators'][u'openstack'].get(u'user', None)
        password = self.config[u'orchestrators'][u'openstack'].get(u'pwd', None)
        project = self.config[u'orchestrators'][u'openstack'].get(u'project', None)
        domain = self.config[u'orchestrators'][u'openstack'].get(u'domain', None)

        # for debug purposes
        # print(u'uri      : ' + uri)
        # print(u'region   : ' + region)
        # print(u'user     : ' + user)
        # print(u'password : ' + password)
        # print(u'project  : ' + project)
        # print(u'domain   : ' + domain)
        # print(u'-')

        return uri, region, user, password, project, domain    

    def get_metrictypes(self):
        data = urlencode({'size': -1})
        uri = '%s/services/metricstypes' % self.baseuri
        res = self.cmp_get(uri, data=data)
        return {r['name']: r for r in res['metric_types']}

    def get_metric(self, service_instance_id, metric_type, creation_date):
        uri = u'%s/services/metrics' % self.baseuri
        data = {
            'service_instance_id': service_instance_id,
            'metric_type': metric_type
        }
        if creation_date is not None:
            data['creation_date'] = creation_date
        data = urlencode(data)   
        res = self.cmp_get(uri, data=data).get('metrics', [])
        if len(res) > 0:
            return res[0]
        else:
            return None

    def add_or_replace_metric(self, service_id, value, metrictype, date):

        print ("==== ADDING %s to service %s value %s " % (metrictype,service_id, value))
        metrictype_id = self.metrictypes.get(metrictype).get('id')
        metric = self.get_metric(service_id, metrictype, date)
        print('get metric: %s %s %s' % (service_id, metrictype, date))
        if metric is not None:
            try:
                print('==============need delete metric %s' % metric)
                oid = metric.get(u'id', None)
                if oid is not None:
                    self.del_metric(service_id, oid)
                    print('del metric:%s %s %s' % (service_id, metrictype, date))
            except Exception as ex:
                print('ERROR deleting metric:  %s' % (ex))
        res = self.add_metric(metrictype_id, value, service_id, date)
        print('add metric: %s %s %s %s' % (service_id, value, metrictype, date))   

    def del_metric(self, service_uuid, metricid):
        try:
            uri = u'%s/services/metrics' % self.baseuri
            data = {'metric': {'metric_oid': str(metricid), 'service_instance_oid': str(service_uuid)}}
            res = self.cmp_delete(uri,  data=data)
        except Exception as ex:
            print(ex)

    def add_metric(self, metrictype_id, value, service_uuid, date):
        uri = u'%s/services/metrics' % self.baseuri
        data = {
            u'metric': {
                u'value': value,
                u'metric_type_id': u'%s' % metrictype_id,
                u'metric_num': u'0',
                u'service_instance_oid': u'%s' % service_uuid,
                u'job_id': u'1',
                u'creation_date': date
            }
        }
        res = self.cmp_post(uri, data=data)
        return res



    def get_monit_list(self, *args):
        # inner support class
        def cross_data_cz_cs(resources, services):
            res = []
            for r in resources:
                for s in services:
                    if r[u'uuid'] == s[u'resource_uuid']:
                        # ds = DataSupport(
                        #     r[u'desc'],
                        #     s[u'uuid']
                        # )
                        ds = {
                            'name' : r.get(u'desc', None),
                            'account_uuid': s.get(u'account',{}).get(u'uuid',None),
                            'account_id': s.get(u'account_id', None),
                            'compute_service_id' : s.get(u'id',None),
                            'compute_service_uuid' : s.get(u'uuid', None),
                            'match_found' : False,
                            'monit_hosts' : 0,
                        }
                        res.append(ds)
                        services.remove(s)
            return res

        def cross_data_czcs_groups(accounts, zabbix_groups):
            res = []
            # check for matches
            for account_item in accounts:
                for group_item in zabbix_groups:
                    full_name_hyperv = account_item['name']
                    if full_name_hyperv == group_item[u'name']:
                        account_item['match_found'] = True
                        account_item['monit_hosts'] += int(group_item[u'hosts'])
                    if not account_item['match_found']:
                        for hypervisor in [u'vmware', u'openstack']:
                            full_name_hyperv = u'%s-%s' % (account_item['name'], hypervisor)
                            if full_name_hyperv == group_item[u'name']:
                                account_item['match_found'] = True
                                account_item['monit_hosts'] += int(group_item[u'hosts'])
            # take only matched items
            for account_item in accounts:
                if account_item['match_found']:
                    res.append(account_item)
            return res

        ### entry point ###
        resource_ids = self.get_compute_zones()
        compute_service_ids = self.get_compute_services()

        # comment
        accounts = cross_data_cz_cs(resource_ids, compute_service_ids)

        hostgroups = self.get_zabbix_usage()

        # find accounts which have host(s) monitored by Zabbix
        monit_accounts = cross_data_czcs_groups(accounts, hostgroups)
        return monit_accounts

    
    def get_zabbix_usage(self):
        hostgroups = []
        # get Zabbix configuration settings for given environment
        uri, user, password  = self.get_zabbix_config_settings()
        # create instance of Zabbix manager
        if uri and user and password is not None:
            zabbix_client = ZabbixManager(uri=uri)
            zabbix_client.authorize(user, password, key=self.key )
        else:
            raise Exception(u'ZabbixError: missing configuration settings.')
        print(u'Getting hosts monitored by account in \'%s\' environment ...' % self.env)  # for debug purposes
        # get list of Zabbix hostgroups
        res = zabbix_client.group.list( selecthosts='hostids')
        # print(jsonDumps(res, ensure_ascii=False, indent=2 ))
        for item in res:
            host_lst = item.get(u'hosts', {})
            if len(host_lst) > 0:
                item[u'hosts'] = u'%s' % str(len(host_lst))
                hostgroups.append(item)
        print('got zabbix usage pod %s' % self.env)
        return hostgroups
    

    # VOLUMES METHODS
    def get_volumes(self):
        self.configure_cmp_resource()
        data = {'size': -1}
        data = urlencode(data)
        uri = u'%s/provider/volumes' % self.baseuri
        res = self.cmp_get(uri, data=data, timeout=120)
        return res.get(u'volumes', None)

    def get_db_connection(self):
        conf = self.config[u'db'].get(u'service', None)
        host = conf.get('host')
        port = conf.get('port')
        db = conf.get('db')
        pwd = conf.get('pwd')
        db_uri = u'mysql+pymysql://%s:%s@%s:%s/%s' % ('service', pwd, host, port, db)
        server = MysqlManager(1, db_uri)
        return server

    def add_or_update_volume_item(self, dbconn, voldesc):
        selectsqlstmnt = '''SELECT
            id,
            date_format(creation_date,'%%Y-%%m-%%dT%%TZ' ) creation_date ,
            date_format(modification_date,'%%Y-%%m-%%dT%%TZ') modification_date
            from service.tmp_volumes_
            where resource_uuid  = '{resource_uuid}' '''
        updatesqlstmnt = '''UPDATE  service.tmp_volumes_  set
            modification_date = str_to_date('{modified_date}','%%Y-%%m-%%dT%%TZ'),
            `desc` = '{desc}',
            name = '{name}',
            params = '{params}',
            instance_resource_uuid = '{instance_resource_uuid}',
            instance_uuid = null,
            status = '{state}',
            size = '{size}',
            container = '{container_name}'
           where id = {id}'''
        insertsqlstmnt = '''INSERT INTO service.tmp_volumes_ (
            creation_date, modification_date, uuid, objid,
            `desc`, name, fk_service_definition_id, params,
            resource_uuid, instance_resource_uuid, instance_uuid,
            status, size, container ) VALUES (
            str_to_date('{creation_date}','%%Y-%%m-%%dT%%TZ'),
            str_to_date('{modified_date}','%%Y-%%m-%%dT%%TZ'),
            uuid(), '', '{desc}', '{name}',  72,
            '{params}', '{resource_uuid}', '{instance_resource_uuid}', null,
            '{state}', '{size}', '{container_name}')'''

        resource_uuid = voldesc.get(u'uuid', None)
        modified_date = voldesc.get(u'date', {}).get(u'modified', None)

        if resource_uuid is not None:
            res = None
            try:
                sqlstmnt = selectsqlstmnt.format(resource_uuid=resource_uuid)
                # print(sqlstmnt)
                res = dbconn.execute(sqlstmnt)
                row = res.fetchone()
                if row is None:
                    creation_date = voldesc.get(u'date', {}).get(u'creation', None)
                    instance_resource_uuid=voldesc.get(u'instance', {}).get(u'uuid', None)
                    name = voldesc.get(u'name', None)
                    desc = voldesc.get(u'desc', None)
                    state = voldesc.get(u'state', None)
                    size = voldesc.get(u'size', None)
                    container_name = voldesc.get(u'container', {}).get(u'name', None)
                    params = sqlquote(jsonDumps(voldesc, ensure_ascii=False))

                    sqlstmnt = insertsqlstmnt.format(
                            resource_uuid=resource_uuid,
                            creation_date=creation_date,
                            modified_date=modified_date,
                            instance_resource_uuid=instance_resource_uuid,
                            name=name, desc=desc, size=size, state=state,
                            container_name=container_name,
                            params=params)
                    print('inserting volume resource_uuid: {resource_uuid}'.format(resource_uuid=resource_uuid))
                    # print(sqlstmnt)
                    dbconn.execute( sqlstmnt)
                elif row['modification_date'] != modified_date:
                    instance_resource_uuid=voldesc.get(u'instance', {}).get(u'uuid', None)
                    name = voldesc.get(u'name', None)
                    desc = voldesc.get(u'desc', None)
                    state = voldesc.get(u'state', None)
                    size = voldesc.get(u'size', None)
                    container_name = voldesc.get(u'container', {}).get(u'name', None)
                    params = sqlquote(jsonDumps(voldesc, ensure_ascii=False))

                    sqlstmnt = updatesqlstmnt.format(
                            id=row['id'],
                            resource_uuid=resource_uuid,
                            modified_date=modified_date,
                            instance_resource_uuid=instance_resource_uuid,
                            name=name, desc=desc, size=size, state=state,
                            container_name=container_name,
                            params=params
                            )
                    print('updating volume resource_uuid: {resource_uuid}'.format(resource_uuid=resource_uuid))
                    # print(sqlstmnt)
                    dbconn.execute(sqlstmnt)
                else:
                    print('Volume resource_uuid: {resource_uuid} already up to date'.format(resource_uuid=resource_uuid))

                res.close()
            except Exception as ex:
                logger.warning(ex, exc_info=True)
                print(ex)
                if res:
                    res.close()
            finally:
                pass

    def finalize_volumes_update(self, dbconn):
        """ esegue le elaborazioni sicessive al caricamento delle info sui volumi
        """
        sqlstmnts =[
            # cerco la servicnce isnstance che rappresenta la macchina che monta il volume
            '''
            UPDATE tmp_volumes_  tv set instance_uuid = (SELECT  si.uuid from service_instance si
                    WHERE si.id = (select max(ss.id) from service_instance ss WHERE ss.resource_uuid = tv.instance_resource_uuid))
            WHERE tv.instance_uuid is NULL and tv.instance_resource_uuid != '' ''',
            # determino l'account dalla serviceinstance che monta il volume
            '''
            UPDATE tmp_volumes_ tv set fk_account_id = (SELECT  si.fk_account_id from service_instance si WHERE si.uuid = tv.instance_uuid )
            WHERE tv.fk_account_id is NULL and tv.instance_uuid is not NULL''',
            # cambio service definition per volumi di tio db usndo le regole di nomenclatura
            '''
            UPDATE tmp_volumes_  tv set objid   = (SELECT  si.objid from service_instance si where si.uuid = tv.instance_uuid )
            WHERE tv.objid ='' and tv.instance_uuid is not NULL''',
            # assegno al volume lo stesso objectid della itanza che lo monta eredita gli stessi permessi
            ''' UPDATE tmp_volumes_ tv set fk_service_definition_id  = 73
            WHERE tv.name like 'dbs-%%'  and fk_service_instance_id is NULL ''',
             # creo il volume come servizio  service_instance
            '''
            INSERT INTO service.service_instance (creation_date, modification_date, expiry_date, uuid,
                objid, `desc`, active, name, version, fk_account_id, fk_service_definition_id, params,
                bpmn_process_id, resource_uuid, status, last_error)
            SELECT
                creation_date, modification_date, NULL expiry_date, uuid, objid,
                `desc`, 1 active, name, '1.0' version, fk_account_id, fk_service_definition_id,
                NULL params, NULL bpmn_process_id, resource_uuid, status, NULL last_error
            FROM
                service.tmp_volumes_
            WHERE fk_account_id is not NULL and fk_service_instance_id is NULL ''',
            # creo il volume come servizio  service_instance_config
            '''
            INSERT INTO service.service_instance_config (creation_date, modification_date, expiry_date,
                uuid, objid, `desc`, active, name, json_cfg, fk_service_instance_id)
            SELECT
	            si.creation_date, si.modification_date, NULL expiry_date, uuid() uuid, si.objid,
                CONCAT('cfg ',si.name) `desc`, 1 active, CONCAT('cfg ' ,si.name) name,
                tv.params json_cfg, si.id fk_service_instance_id
            FROM
                service.tmp_volumes_ tv
                INNER JOIN service_instance si on si.uuid = tv.uuid
            WHERE tv.fk_service_instance_id is NULL ''',
            # aggiorno i dati del volume  e prendo nota del fatto che e' stato creato il servizio per quel volume
            '''
            UPDATE service.tmp_volumes_ tv set
                fk_service_instance_id = (SELECT si.id from service.service_instance si WHERE si.resource_uuid = tv.resource_uuid)
            WHERE fk_service_instance_id  is NULL ''',
            # agiungo i volumi alle risorse di database nel caso in cui siano volumi di database
            '''
            INSERT INTO tmp_databases_
                (creation_date , modification_date ,uuid, dbtype ,resource_uuid,params , fk_service_instance_id )
            SELECT
                tv.creation_date , tv.modification_date , tv.uuid , td.dbtype, tv.resource_uuid , tv.params , tv.fk_service_instance_id
	        FROM
                tmp_databases_ td
                INNER JOIN tmp_volumes_ tv on tv.instance_uuid = td.uuid
                LEFT OUTER JOIN tmp_databases_ tdd 	on tv.uuid = tdd.uuid
            WHERE  tdd.id is NULL ''',
            # creo service_link inst uguali a quello della service instance che rappresenta la macchina che monta il volume -- questionabile 
            '''
            INSERT INTO service_link_inst(creation_date, modification_date, expiry_date, uuid, objid, `desc`, active, name, version, start_service_id, end_service_id, `attributes`, priority) 
            SELECT tv.creation_date creation_date, tv.modification_date modification_date, sli.expiry_date, UUID() uuid, sli.objid, concat( 'vol_', sli.`desc`), sli.active, CONCAT('lnk_', sli.start_service_id , '_', tv.fk_service_instance_id )  name, 
                sli.version, sli.start_service_id, tv.fk_service_instance_id  end_service_id, sli.`attributes`, sli.priority 
            FROM 
                tmp_volumes_ tv
                INNER JOIN service_instance si on si.uuid = tv.instance_uuid
                INNER JOIN service_link_inst sli on sli.end_service_id = si.id
                LEFT JOIN  service_link_inst sli2 on sli2.end_service_id = tv.fk_service_instance_id  and sli2.start_service_id = sli.start_service_id 
            WHERE sli2.id IS NULL ''',
        ]
        for statement in sqlstmnts:
            # print(statement)
            dbconn.execute(statement)
        pass


    #ORACLE
    def get_oracle_dbs(self):
        dbaas = []
        self.configure_cmp_resource()

        data = {'size': -1}
        data = urlencode(data)
        uri = u'%s/provider/instances' % self.baseuri
        res = self.cmp_get(uri, data=data, timeout=120)

        self.configure_cmp_service()
        for item in res[u'instances']:
            if item['image']['os'] == 'OracleLinux':
                dbaas.append(item)
        return dbaas

    def get_compute_instance(self):
        self.configure_cmp_service()
        data = {'plugintype': u'ComputeInstance', 'size': -1}
        data = urlencode(data)
        uri = u'%s/serviceinsts' % self.baseuri
        res = self.cmp_get(uri, data=data)
        res = res[u'serviceinsts']
        print('get service instances: %s' % len(res))
        return res
    
    def add_or_update_ora_dbitem(self, dbconn, dbdesc):
        getsqlstmnt = '''SELECT
            id,
            date_format(creation_date,'%%Y-%%m-%%dT%%TZ' ) creation_date ,
            date_format(modification_date,'%%Y-%%m-%%dT%%TZ') modification_date
            from service.tmp_databases_
            where resource_uuid  = '{resource_uuid}' '''
        updatesqlstmnt = '''UPDATE  service.tmp_databases_  set
            params ='{jsondescription}' ,
            modification_date = str_to_date('{date_modified}','%%Y-%%m-%%dT%%TZ')
            where id = {id}'''
        insertsqlstmnt = '''INSERT INTO service.tmp_databases_
            (creation_date, modification_date, uuid, resource_uuid, dbtype, params)
            VALUES(
                str_to_date('{date_created}','%%Y-%%m-%%dT%%TZ'),
                str_to_date('{date_modified}','%%Y-%%m-%%dT%%TZ'),
                NULL,
                '{resource_uuid}',
                'ORACLE', '{jsondescription}') '''

        uuid = dbdesc.get(u'uuid', None)
        creation_date = dbdesc.get(u'date', {}).get(u'creation', None)
        modified_date = dbdesc.get(u'date', {}).get(u'modified', None)
        if uuid is not None:
            # trans = None
            res = None
            try:
                # trans = dbconn.begin()
                sqlstmnt = getsqlstmnt.format(resource_uuid=uuid)
                # print(sqlstmnt)
                res = dbconn.execute(sqlstmnt)
                row = res.fetchone()
                if row is None:
                    sqlstmnt = insertsqlstmnt.format(
                            resource_uuid=uuid,
                            date_created=creation_date,
                            date_modified=modified_date,
                            jsondescription=sqlquote(jsonDumps(dbdesc, ensure_ascii=False)))
                    print('inserting db ORACLE resource_uuid: {resource_uuid}'.format(resource_uuid=uuid))
                    # print(sqlstmnt)
                    dbconn.execute( sqlstmnt)
                elif row['modification_date'] != modified_date:
                    sqlstmnt = updatesqlstmnt.format(
                            id=row['id'],
                            date_modified=modified_date,
                            jsondescription=sqlquote(jsonDumps(dbdesc, ensure_ascii=False)))
                    print('updating db ORACLE resource_uuid: {resource_uuid}'.format(resource_uuid=uuid))
                    # print(sqlstmnt)
                    dbconn.execute(sqlstmnt)
                else:
                    print('db ORACLE resource_uuid: {resource_uuid} already up to date'.format(resource_uuid=uuid))

                res.close()
            except Exception as ex:
                logger.warning(ex, exc_info=True)
                print(ex)
                if res:
                    res.close()
            finally:
                pass
                # if trans:
                #     trans.commit()

    def get_oracle_usage(self):
        dbs = {d['uuid']: d for d in self.get_oracle_dbs()}
        sii = self.get_compute_instance()

        res = []
        for si in sii:
            db = dbs.get(si['resource_uuid'], None)
            if db is not None:
                db['disk_tot'] = sum([i['volume_size'] for i in db.get('block_device_mapping')])
                si['resource'] = db
                res.append(si)

        resp = []
        for r in res:
            item = {
                'service_id': r['id'],
                # 'db_ora_vcpu': dict_get(r, 'resource.flavor.vcpus'),
                # 'db_ora_gbram': dict_get(r, 'resource.flavor.memory'),
                # 'db_ora_gbdisk_hi': 0,
                'db_ora_gbdisk_low': dict_get(r, 'resource.disk_tot')
            }
            resp.append(item)
        return resp


def sqlquote(statement):
    return statement.replace("'", "''").replace('%', '%%')                