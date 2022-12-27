# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from sys import stdout
from datetime import datetime
from time import sleep
from beecell.types.type_string import str2bool
from beecell.types.type_dict import dict_get
from beecell.types.type_list import merge_list
from beedrones.openstack.client import OpenstackManager
from beedrones.trilio.client import TrilioManager
from beehive3_cli.core.controller import BaseController, BASE_ARGS
from cement import ex
from beehive3_cli.core.util import load_environment_config, load_config


def OPENSTACK_ARGS(*list_args):
    orchestrator_args = [
        (['-O', '--orchestrator'], {'action': 'store', 'dest': 'orchestrator',
                                    'help': 'openstack platform reference label'}),
        (['-P', '--project'], {'action': 'store', 'dest': 'project', 'help': 'openstack current project name'}),
    ]
    res = merge_list(BASE_ARGS, orchestrator_args, *list_args)
    return res


class TrilioPlatformController(BaseController):
    class Meta:
        label = 'trilio'
        stacked_on = 'platform'
        stacked_type = 'nested'
        description = "Trilio Platform management\n" \
                      "Below are some of the important terms in OpenStack and TrilioVault.\n" \
                      "- Instances: Instances are the running virtual machines within an OpenStack cloud. In the\n" \
                      "  context of TrilioVault, instances are members of workloads (backup-jobs). TrilioVault\n" \
                      "  takes the backup of those OpenStack Instances which are members of the workloads.\n" \
                      "- Workload: A workload is defined as a collection of instances, the interconnectivity\n" \
                      "  between them, the virtual disks mapped to those machines and any metadata associated with\n" \
                      "  each of these resources. The tenant can add or remove instances to/from a workload. An\n" \
                      "  instance can only be a member of a single workload at any given time. If a tenant wants to\n" \
                      "  move an instance from one workload to another, the instance first need to be removed from\n" \
                      "  old workload and then add to the new workload.\n" \
                      "- Workload Policy: Workload policy defines various aspects of the backup process including\n" \
                      "  number of backups to retain, frequency at which backups are taken and full backups between\n" \
                      "  incrementals.\n" \
                      "- Snapshot: A snapshot is the actual copy of the data backup stored in some storage\n" \
                      "  designated as backup store or respository. A snapshot can also be defined as a state of a\n" \
                      "  system at a particular point-in-time. TrilioVault provides its users with the ability to\n" \
                      "  take full and incremental snapshots. A Full type snapshot takes a complete backup of all\n" \
                      "  instances included in the workload independent of previous snapshots. In an Incremental\n" \
                      "  type snapshot, TrilioVault takes backups of only data modfied since the last snapshot.\n" \
                      "- Backup target: Backup target is the storage repository where TrilioVault keeps its backup\n" \
                      "  data. TrilioVault supports both NFS and Swift as a backup target.\n" \
                      "- Restore: Restore operation recreates a selected snapshot. TrilioVault supports multiple\n" \
                      "  restore options for user to choose from.\n" \
                      "- One-click restore: One-click restore restores the selected snapshot to the exact location\n" \
                      "  including the same network/subnet, volume types, security groups, IP addresses and so on.\n" \
                      "  One-click Restore only works when original instances are deleted.\n" \
                      "- Selective Restore: The selective restore method provides a significant amount of\n" \
                      "  flexibility to recover instances. With the selective restore, user can choose different\n" \
                      "  target networks, target volume types, include/exclude specific instances to restore, and\n" \
                      "  target flavor for each instance, etc.\n" \
                      "- In-place restore: One click and selective restores creates brand new resources when\n" \
                      "  restoring virtual resources from the backup media. In some cases it is not desirable to\n" \
                      "  construct new resources. Instead user may want to restore an existing volume to a\n" \
                      "  particular point in time. In-place restore functionality will overwrite existing volume\n" \
                      "  with the data from the backup media."
        help = "trilio platform"

    def pre_command_run(self):
        super(TrilioPlatformController, self).pre_command_run()

        self.config = load_environment_config(self.app)

        orchestrators = self.config.get('orchestrators', {}).get('openstack', {})
        label = getattr(self.app.pargs, 'orchestrator', None)

        if label is None:
            keys = list(orchestrators.keys())
            if len(keys) > 0:
                label = keys[0]
            else:
                raise Exception('No openstack default platform is available for this environment. Select '
                                'another environment')

        if label not in orchestrators:
            raise Exception('Valid label are: %s' % ', '.join(orchestrators.keys()))
        conf = orchestrators.get(label)

        project = getattr(self.app.pargs, 'project', None)
        self.all_project = False
        if project is None:
            project = conf.get('project')
            self.all_project = True
        uri = '%s://%s:%s%s' % (conf.get('proto'), conf.get('vhost'), conf.get('port'), conf.get('path'))
        self.oclient = OpenstackManager(uri, default_region=conf.get('region'))
        self.oclient.authorize(conf.get('user'), conf.get('pwd'), project=project, domain=conf.get('domain'),
                               key=self.key)
        self.client = TrilioManager(self.oclient)

    @ex(
        help='Return the status ( true or false ) of the Cloud Wide TrilioVault Job Scheduler',
        description='Return the status ( true or false ) of the Cloud Wide TrilioVault Job Scheduler',
        arguments=OPENSTACK_ARGS()
    )
    def status(self):
        res = self.client.job_scheduler.get_global_job_scheduler()
        resp = {'status': res}
        if res is True:
            resp['global_job_scheduler'] = 'Enabled'
        else:
            resp['global_job_scheduler'] = 'Disabled'
        self.app.render(resp, headers=['status', 'global_job_scheduler'], fields=['status', 'global_job_scheduler'])

    @ex(
        help='Gives storage used and vms protected by tenants',
        description='Gives storage used and vms protected by tenants',
        arguments=OPENSTACK_ARGS()
    )
    def tenant_usage(self):
        res = self.client.job_scheduler.get_tenant_usage()
        tenants_usage = [{
            'id': k,
            'name': v.get('tenant_name', None),
            'vms_protected': v.get('vms_protected', None),
            'total_vms': v.get('total_vms', None),
            'passively_protected': v.get('passively_protected', None),
            'used_capacity': v.get('used_capacity', None)} for k, v in res.get('tenants_usage').items()]
        headers = ['total_vms', 'total_usage', 'vms_protected', 'total_capacity']
        fields = ['total_vms', 'total_usage', 'vms_protected', 'total_capacity']
        self.app.render(res.get('global_usage'), headers=headers, fields=fields)
        headers = ['id', 'name', 'vms_protected', 'total_vms', 'passively_protected', 'used_capacity']
        fields = ['id', 'name', 'vms_protected', 'total_vms', 'passively_protected', 'used_capacity']
        self.app.render(tenants_usage, headers=headers, fields=fields)

    @ex(
        help='get workload storage usage',
        description='get workload storage usage',
        arguments=OPENSTACK_ARGS()
    )
    def storage_usage(self):
        res = self.client.job_scheduler.get_storage_usage()
        self.app.render(res['count_dict'], details=True)
        for item in res['storage_usage']:
            self.app.render(item, details=True)

    @ex(
        help='get auditlog of workload manager',
        description='get auditlog of workload manager',
        arguments=OPENSTACK_ARGS([
            (['-time_in_minutes'], {'help': 'time in minutes(default is 24 hrs.)', 'action': 'store', 'type': int,
                                    'default': 720}),
            (['-time_from'], {'help': 'From date time in format MM-DD-YYYY', 'action': 'store', 'type': str,
                              'default': None}),
            (['-time_to'], {'help': 'To date time in format MM-DD-YYYY (default is current day)', 'action': 'store',
                            'type': str, 'default': None}),
        ])
    )
    def auditlog(self):
        time_in_minutes = self.app.pargs.time_in_minutes
        time_from = self.app.pargs.time_from
        time_to = self.app.pargs.time_to
        res = self.client.workload.auditlog(time_in_minutes=time_in_minutes, time_from=time_from, time_to=time_to)
        headers = ['workload', 'project', 'tiemstamp', 'details']
        fields = ['ObjectId', 'ProjectName', 'Timestamp', 'Details']
        res.reverse()
        self.app.render(res, headers=headers, fields=fields, maxsize=200)

    @ex(
        help='get protected vm',
        description='get protected vm',
        arguments=OPENSTACK_ARGS()
    )
    def protected_vm_get(self):
        res = self.client.job_scheduler.get_protected_vms()
        self.app.render(res, headers=['id'])

    @ex(
        help='list license',
        description='list license',
        arguments=OPENSTACK_ARGS()
    )
    def license_get(self):
        res = self.client.license.list()
        self.app.render(res, details=True)

    @ex(
        help='check license',
        description='check license',
        arguments=OPENSTACK_ARGS()
    )
    def license_check(self):
        res = self.client.license.check()
        self.app.render({'msg': res}, maxsize=200)

    @ex(
        help='add license',
        description='add license',
        arguments=OPENSTACK_ARGS([
            (['license_file'], {'help': 'license file name', 'action': 'store', 'type': str})
        ])
    )
    def license_add(self):
        license_file = self.app.pargs.license_file
        license = load_config(license_file)
        resp = self.client.license.add(license)
        self.app.render(resp, details=True, maxsize=200)

    @ex(
        help='display workload types',
        description='display workload types',
        arguments=OPENSTACK_ARGS()
    )
    def workload_types(self):
        res = self.client.workload.types()
        headers = ['id', 'name', 'description', 'project', 'status', 'created_at']
        fields = ['id', 'name', 'description', 'project_id', 'status', 'created_at']
        self.app.render(res, headers=headers, fields=fields)

    @ex(
        help='display workloads status with the last snapshot',
        description='display workloads status with the last snapshot',
        arguments=OPENSTACK_ARGS()
    )
    def workload_status(self):
        works = self.client.workload.list(all=True)
        snaps = self.client.snapshot.list(all=True)
        projects = self.oclient.project.list()

        works_idx = {w['id']: w for w in works}
        projects_idx = {w['id']: w for w in projects}

        for snap in snaps:
            workload_id = snap['workload_id']
            try:
                works_idx[workload_id]['snaps'].append(snap)
            except:
                works_idx[workload_id]['snaps'] = [snap]
        for work in works:
            work['snap_status'] = dict_get(work, 'snaps.-1.status')
            work['snap_date'] = dict_get(work, 'snaps.-1.created_at')
            work['snap_type'] = dict_get(work, 'snaps.-1.snapshot_type')
            work['project_name'] = projects_idx[work['project_id']]['name']

        headers = ['id', 'name', 'desc', 'project_id', 'project_name', 'status', 'created_at', 'Last snapshot status',
                   'Last snapshot date', 'Snapshot type']
        fields = ['id', 'name', 'description', 'project_id', 'project_name', 'status', 'created_at', 'snap_status',
                  'snap_date', 'snap_type']
        self.app.render(works, headers=headers, fields=fields)

    @ex(
        help='get workload',
        description='get workload',
        arguments=OPENSTACK_ARGS([
            (['-id'], {'help': 'workload id', 'action': 'store', 'type': str, 'default': None}),
            (['-verbose'], {'help': 'workload verbose info', 'action': 'store', 'type': str, 'default': 'false'}),
        ])
    )
    def workload_get(self):
        workload_id = self.app.pargs.id
        if workload_id is not None:
            resp = self.client.workload.get(workload_id)
            if self.format == 'text':
                instances = resp.pop('instances')
                jobschedule = resp.pop('jobschedule')
                storage_usage = resp.pop('storage_usage')
                self.app.render(resp, details=True)
                self.c('\ninstances', 'underline')
                headers = ['id', 'name', 'metadata.key_data', 'metadata.workload_id', 'metadata.workload_name',
                           'metadata.config_drive']
                self.app.render(instances, headers=headers)
                self.c('\njobschedule', 'underline')
                headers = ['fullbackup_interval', 'retention_policy_type', 'start_time', 'start_date', 'interval',
                           'enabled', 'retention_policy_value', 'global_jobscheduler']
                self.app.render(jobschedule, headers=headers)
                self.c('\nstorage_usage', 'underline')
                headers = ['usage', 'full.usage', 'full.snap_count', 'incremental.usage', 'incremental.snap_count']
                self.app.render(storage_usage, headers=headers)
            else:
                self.app.render(resp, details=True)
        else:
            headers = ['id', 'name', 'description', 'project', 'status', 'created_at']
            fields = ['id', 'name', 'description', 'project_id', 'status', 'created_at']
            workloads = self.client.workload.list(all=self.all_project)
            if str2bool(self.app.pargs.verbose) is True:
                res = [self.client.workload.get(w['id']) for w in workloads]
                fields.extend(['jobschedule.enabled', 'jobschedule.start_time'])
                headers.extend(['job_enabled', 'job_start'])
            else:
                res = workloads
            self.app.render(res, headers=headers, fields=fields, maxsize=40)

    @ex(
        help='add a workload. Project with -P must be specified',
        description='add a workload. Project with -P must be specified',
        arguments=OPENSTACK_ARGS([
            (['name'], {'help': 'workload name', 'action': 'store', 'type': str}),
            (['type_id'], {'help': 'workload type id', 'action': 'store', 'type': str}),
            (['instances'], {'help': 'comme separated list of instances', 'action': 'store', 'type': str}),
            (['-metadata'], {'help': 'metadata', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'workload description', 'action': 'store', 'type': str, 'default': None}),
            (['-fullbackup_interval'], {'help': 'fullbackup interval [default=2]', 'action': 'store', 'type': int,
                                        'default': 2}),
            (['-start_date'], {'help': 'start date. Ex. \'06/05/2014\'', 'action': 'store', 'type': str,
                               'default': None}),
            (['-end_date'], {'help': 'end date. Ex. \'07/15/2014\'', 'action': 'store', 'type': str, 'default': None}),
            (['-start_time'], {'help': 'start time. Ex. \'2:30 PM\' [default=\'4:00 AM\']', 'action': 'store',
                               'type': str, 'default': '4:00 AM'}),
            (['-interval'], {'help': 'interval. [default=24hrs]', 'action': 'store', 'type': str, 'default': '24hrs'}),
            (['-snapshots_to_retain'], {'help': 'snapshots to retain [default=4]', 'action': 'store', 'type': int,
                                        'default': 4}),
            (['-timezone'], {'help': 'timezone [default=Europe/Rome]', 'action': 'store', 'type': str,
                             'default': 'Europe/Rome'}),
        ])
    )
    def workload_add(self):
        name = self.app.pargs.name
        workload_type_id = self.app.pargs.type_id
        instances = self.app.pargs.instances.split(',')
        desc = self.app.pargs.desc
        fullbackup_interval = self.app.pargs.fullbackup_interval
        start_date = self.app.pargs.start_date
        end_date = self.app.pargs.end_date
        start_time = self.app.pargs.start_time
        interval = self.app.pargs.interval
        snapshots_to_retain = self.app.pargs.snapshots_to_retain
        timezone = self.app.pargs.timezone
        metadata = self.app.pargs.metadata
        if desc is None:
            desc = name
        if start_date is None:
            now = datetime.today()
            start_date = '%s/%s/%s' % (now.day, now.month, now.year)
        if metadata is None:
            metadata = {}

        res = self.client.workload.add(name, workload_type_id, instances, metadata=metadata, desc=desc,
                                       fullbackup_interval=fullbackup_interval, start_date=start_date,
                                       end_date=end_date, start_time=start_time, interval=interval,
                                       snapshots_to_retain=snapshots_to_retain, timezone=timezone)
        workload = res['id']
        status = res['status']
        while status not in ['available', 'error']:
            res = self.client.workload.get(workload)
            status = res['status']
            stdout.write('.')
            stdout.flush()
            sleep(2)
        self.app.render({'msg': 'Workload %s created' % workload}, headers=['msg'], maxsize=200)

    @ex(
        help='update the workload. Project with -P must be specified',
        description='update the workload. Project with -P must be specified',
        arguments=OPENSTACK_ARGS([
            (['workload'], {'help': 'workload id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'workload name', 'action': 'store', 'type': str, 'default': None}),
            (['-instances'], {'help': 'comme separated list of instances', 'action': 'store', 'type': str,
                              'default': None}),
            (['-metadata'], {'help': 'metadata', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'workload description', 'action': 'store', 'type': str, 'default': None}),
            (['-fullbackup_interval'], {'help': 'fullbackup interval', 'action': 'store', 'type': int,
                                        'default': None}),
            (['-start_date'], {'help': 'start date. Ex. \'06/05/2014\'', 'action': 'store', 'type': str,
                               'default': None}),
            (['-end_date'], {'help': 'end date. Ex. \'07/15/2014\'', 'action': 'store', 'type': str, 'default': None}),
            (['-start_time'], {'help': 'start time. Ex. \'2:30 PM\'', 'action': 'store',
                               'type': str, 'default': None}),
            (['-interval'], {'help': 'interval', 'action': 'store', 'type': str, 'default': None}),
            (['-snapshots_to_retain'], {'help': 'snapshots to retain', 'action': 'store', 'type': int,
                                        'default': None}),
            (['-timezone'], {'help': 'timezone', 'action': 'store', 'type': str, 'default': None}),
            (['-enabled'], {'help': 'enable workloa', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def workload_update(self):
        workload_id = self.app.pargs.workload
        name = self.app.pargs.name
        instances = self.app.pargs.instances
        desc = self.app.pargs.desc
        fullbackup_interval = self.app.pargs.fullbackup_interval
        start_date = self.app.pargs.start_date
        end_date = self.app.pargs.end_date
        start_time = self.app.pargs.start_time
        interval = self.app.pargs.interval
        snapshots_to_retain = self.app.pargs.snapshots_to_retain
        timezone = self.app.pargs.timezone
        metadata = self.app.pargs.metadata
        enabled = self.app.pargs.enabled
        if instances is not None:
            instances = instances.split(',')
        if enabled is not None:
            enabled = str2bool(enabled)
        self.client.workload.update(workload_id, name=name, instances=instances, metadata=metadata, desc=desc,
                                    fullbackup_interval=fullbackup_interval, start_date=start_date,
                                    end_date=end_date, start_time=start_time, interval=interval,
                                    snapshots_to_retain=snapshots_to_retain, timezone=timezone, enabled=enabled)
        status = None
        while status not in ['available', 'error']:
            res = self.client.workload.get(workload_id)
            status = res['status']
            stdout.write('.')
            stdout.flush()
            sleep(2)
        self.app.render({'msg': 'Workload %s updated' % workload_id}, headers=['msg'], maxsize=200)

    @ex(
        help='delete the workload. Project with -P must be specified',
        description='delete the workload. Project with -P must be specified',
        arguments=OPENSTACK_ARGS([
            (['workload'], {'help': 'workload id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def workload_del(self):
        workload_id = self.app.pargs.workload
        self.client.workload.delete(workload_id)
        while True:
            try:
                self.client.workload.get(workload_id)
                stdout.write('.')
                stdout.flush()
                sleep(2)
            except:
                break
        self.app.render({'msg': 'Workload %s deleted' % workload_id}, maxsize=200)

    @ex(
        help='unlock the workload',
        description='unlock the workload',
        arguments=OPENSTACK_ARGS([
            (['workload'], {'help': 'workload id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def workload_unlock(self):
        workload_id = self.app.pargs.workload
        resp = self.client.workload.unlock(workload_id)
        self.app.render({'msg': 'Workload %s unlocked' % workload_id}, maxsize=200)

    @ex(
        help='Reset the workload. TrilioVault uses storage based snapshots for calculating backup images of application'
             ' resources. For cinder volumes, it uses cinder snapshots and for ceph based nova backends, it uses ceph '
             'snapshots for calculating the backup images. Depending the state of the workload backup operation, each '
             'of these resources may have one or more snapshots outstanding. Workload-reset deletes all outstanding '
             'snapshots on all resources of the application. Workload-reset is useful if you want to decommission the '
             'application, but you still want to keep all the backups of the application. NOTE: It is highly '
             'recommended to perform workload-reset before deleting any application resources from OpenStack.',
        description='Reset the workload. TrilioVault uses storage based snapshots for calculating backup images of '
                    'application resources. For cinder volumes, it uses cinder snapshots and for ceph based nova '
                    'backends, it uses ceph snapshots for calculating the backup images. Depending the state of the '
                    'workload backup operation, each of these resources may have one or more snapshots outstanding. '
                    'Workload-reset deletes all outstanding snapshots on all resources of the application. '
                    'Workload-reset is useful if you want to decommission the application, but you still want to keep '
                    'all the backups of the application. NOTE: It is highly recommended to perform workload-reset '
                    'before deleting any application resources from OpenStack.',
        arguments=OPENSTACK_ARGS([
            (['workload'], {'help': 'workload id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def workload_reset(self):
        workload_id = self.app.pargs.workload
        self.client.workload.reset(workload_id)
        self.app.render({'msg': 'Workload %s resetted' % workload_id}, maxsize=200)

    @ex(
        help='display the snapshots of the specified workload',
        description='display the snapshots of the specified workload',
        arguments=OPENSTACK_ARGS([
            (['-workload'], {'help': 'workload id', 'action': 'store', 'type': str, 'default': None}),
            (['-id'], {'help': 'snapshot id', 'action': 'store', 'type': str, 'default': None}),
            # (['-all'], {'help': 'snapshot name', 'action': 'store', 'type': str, 'default': 'true'}),
            (['-date_from'], {'help': 'From date in format \'YYYY-MM-DDTHH:MM:SS\' eg 2016-10-10T00:00:00, If don\'t '
                                      'specify time then it takes 00:00 by default [default=3 day ago]',
                              'action': 'store', 'type': str, 'default': None}),
            (['-date_to'], {'help': 'To date in format \'YYYY-MM-DDTHH:MM:SS\', Specify HH:MM:SS to get snapshots '
                                    'within same day inclusive/exclusive results for date_from and date_to '
                                    '[default=today]', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def snapshot_get(self):
        snapshot_id = self.app.pargs.id
        if snapshot_id is not None:
            resp = self.client.snapshot.get(snapshot_id)
            if self.format == 'text':
                instances = resp.pop('instances')
                metadata = resp.pop('metadata')
                self.app.render(resp, details=True)
                self.c('\ninstances', 'underline')
                self.app.render(instances, headers=['id', 'name', 'status'])
                self.c('\nmetadata', 'underline')
                self.app.render(metadata, headers=['id', 'key', 'value', 'version', 'created_at', 'deleted'])
            else:
                self.app.render(resp, details=True)
        else:
            # all = str2bool(self.app.pargs.all)
            all = True
            workload_id = self.app.pargs.workload
            # if workload_id is not None:
            #     all = False

            date_from = self.app.pargs.date_from
            date_to = self.app.pargs.date_to

            if date_from is None and date_to is None:
                now = datetime.today()
                date_from = '%s-%s-%sT' % (now.year, now.month, now.day - 1)
                date_to = '%s-%s-%sT' % (now.year, now.month, now.day + 1)

            res = self.client.snapshot.list(all=all, workload_id=workload_id, date_from=date_from, date_to=date_to)
            headers = ['id', 'name', 'status', 'snapshot type', 'workload', 'created_at']
            fields = ['id', 'name', 'status', 'snapshot_type', 'workload_id', 'created_at']
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help='add a snapshot. Project with -P must be specified',
        description='add a snapshot. Project with -P must be specified',
        arguments=OPENSTACK_ARGS([
            (['workload'], {'help': 'workload id', 'action': 'store', 'type': str, 'default': None}),
            (['-name'], {'help': 'snapshot name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'snapshot description', 'action': 'store', 'type': str, 'default': None}),
            (['-full'], {'help': 'snapshot full flag.If True make a full snapshot', 'action': 'store', 'type': str,
                         'default': 'false'}),
        ])
    )
    def snapshot_add(self):
        workload_id = self.app.pargs.workload
        name = self.app.pargs.name
        desc = self.app.pargs.desc
        full = str2bool(self.app.pargs.full)
        resp = self.client.snapshot.add(workload_id, name=name, desc=desc, full=full)
        self.app.render(resp, details=True)

    @ex(
        help='delete a snapshot',
        description='delete a snapshot',
        arguments=OPENSTACK_ARGS([
            (['snapshot'], {'help': 'snapshot id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def snapshot_del(self):
        snapshot_id = self.app.pargs.snapshot
        self.client.snapshot.delete(snapshot_id)
        self.app.render({'msg': 'Delete snapshot %s' % snapshot_id}, maxsize=200)

    @ex(
        help='cancel a snapshot that is running. If the snapshot operation is in the middle of the data transfer of a '
             'resource, it waits for the data transfer operation is complete before terminating the snapshot operation.',
        description='cancel a snapshot that is running. If the snapshot operation is in the middle of the data transfer'
                    ' of aresource, it waits for the data transfer operation is complete before terminating the '
                    'snapshot operation.',
        arguments=OPENSTACK_ARGS([
            (['snapshot'], {'help': 'snapshot id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def snapshot_cancel(self):
        snapshot_id = self.app.pargs.snapshot
        self.client.snapshot.cancel(snapshot_id)
        self.app.render({'msg': 'Cancel snapshot %s' % snapshot_id}, maxsize=200)

    @ex(
        help='list of all mounted snapshots',
        description='list of all mounted snapshots',
        arguments=OPENSTACK_ARGS()
    )
    def snapshot_mounted(self):
        res = self.client.snapshot.mounted()
        headers = ['status', 'mounturl', 'snapshot_name', 'workload_id', 'snapshot_id']
        fields = ['status', 'mounturl', 'snapshot_name', 'workload_id', 'snapshot_id']
        self.app.render(res, headers=headers, fields=fields)

    @ex(
        help='mount a snapshot to an instance',
        description='mount a snapshot to an instance',
        arguments=OPENSTACK_ARGS([
            (['snapshot'], {'help': 'snapshot id', 'action': 'store', 'type': str, 'default': None}),
            (['instance'], {'help': 'instance id where mount snapshot', 'action': 'store', 'type': str})
        ])
    )
    def snapshot_mount(self):
        snapshot_id = self.app.pargs.snapshot
        instance_id = self.app.pargs.instance
        res = self.client.snapshot.mount(snapshot_id, instance_id)

    @ex(
        help='umount a snapshot from an instance',
        description='umount a snapshot from an instance',
        arguments=OPENSTACK_ARGS([
            (['snapshot'], {'help': 'snapshot id', 'action': 'store', 'type': str, 'default': None})
        ])
    )
    def snapshot_umount(self):
        snapshot_id = self.app.pargs.snapshot
        self.client.snapshot.dismount(snapshot_id)

    @ex(
        help='display the snapshot restore',
        description='display the snapshot restore',
        arguments=OPENSTACK_ARGS([
            (['-snapshot'], {'help': 'snapshot id', 'action': 'store', 'type': str, 'default': None}),
            (['-id'], {'help': 'snapshot restore id', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def restore_get(self):
        restore_id = self.app.pargs.id
        if restore_id is not None:
            resp = self.client.restore.get(restore_id)
            if self.format == 'text':
                metadata = resp.pop('metadata', [])
                instances = resp.pop('instances', [])
                restore_options = resp.pop('restore_options', {})
                snapshot_details = resp.pop('snapshot_details', {})
                snapshot_details_metadata = snapshot_details.pop('metadata', [])
                self.app.render(resp, details=True)
                self.c('\nrestore_options', 'underline')
                self.app.render(restore_options, details=True)
                self.c('\nmetadata', 'underline')
                self.app.render(metadata, headers=['id', 'key', 'value', 'version'])
                self.c('\ninstances', 'underline')
                self.app.render(instances, headers=['id', 'name', 'status', 'metadata'])
                self.c('\nsnapshot details', 'underline')
                self.app.render(snapshot_details, details=True)
                self.c('\nsnapshot details metadata', 'underline')
                self.app.render(snapshot_details_metadata, headers=['id', 'key', 'value', 'version'])
            else:
                self.app.render(resp, details=True)
        else:
            snapshot_id = self.app.pargs.snapshot
            res = self.client.restore.list(snapshot_id=snapshot_id)
            headers = ['id', 'name', 'status', 'snapshot', 'size', 'uploaded_size', 'progress_percent', 'created_at']
            fields = ['id', 'name', 'status', 'snapshot_id', 'size', 'uploaded_size', 'progress_percent', 'created_at']
            self.app.render(res, headers=headers, fields=fields)

    @ex(
        help='follow the execution of a shapshot restore',
        description='follow the execution of a shapshot restore',
        arguments=OPENSTACK_ARGS([
            (['restore'], {'help': 'unique identifier of trilio workload snapshot restore', 'action': 'store',
                           'type': str}),
        ])
    )
    def restore_follow(self):
        restore_id = self.app.pargs.restore
        resp = self.client.restore.get(restore_id)
        while resp['status'] not in ['available', 'error']:
            stdout.write('.')
            stdout.flush()
            sleep(2)
            resp = self.client.restore.get(restore_id)
        headers = ['id', 'name', 'status', 'snapshot', 'size', 'uploaded_size', 'progress_percent', 'created_at']
        fields = ['id', 'name', 'status', 'snapshot_id', 'size', 'uploaded_size', 'progress_percent', 'created_at']
        self.app.render(resp, headers=headers, fields=fields)
        if resp['status'] == 'error':
            raise Exception(resp.get('error_msg', ''))

    @ex(
        help='delete the shapshot restore',
        description='delete the shapshot restore',
        arguments=OPENSTACK_ARGS([
            (['restore'], {'help': 'unique identifier of trilio workload snapshot restore', 'action': 'store',
                           'type': str}),
        ])
    )
    def restore_delete(self):
        restore_ids = self.app.pargs.restore.split(',')
        for restore_id in restore_ids:
            self.client.restore.delete(restore_id)
            self.app.render({'msg': 'delete restore %s' % restore_id})

    @ex(
        help='cancel the shapshot restore',
        description='cancel the shapshot restore',
        arguments=OPENSTACK_ARGS([
            (['restore'], {'help': 'unique identifier of trilio workload snapshot restore', 'action': 'store', 
                           'type': str}),
        ])
    )
    def restore_cancel(self):
        restore_id = self.app.pargs.restore
        self.client.restore.cancel(restore_id)

    # @ex(
    #     help='selective restore of a snapshot',
    #     description='selective restore of a snapshot',
    #     arguments=OPENSTACK_ARGS([
    #         (['snapshot'], {'help': 'unique identifier of trilio workload snapshot', 'action': 'store', 'type': str}),
    #         (['config_file'], {'help': 'restore config file', 'action': 'store', 'type': str})
    #     ])
    # )
    # def restore_selective(self):
    #     snapshot_id = self.app.pargs.snapshot
    #     config_file = self.app.pargs.config_file
    #     config = load_config(config_file)
    #     res = self.client.restore.selective(snapshot_id, config)
    #     self.app.render(res, details=True)
    #
    # @ex(
    #     help='inplace restore of a snapshot',
    #     description='inplace restore of a snapshot',
    #     arguments=OPENSTACK_ARGS([
    #         (['snapshot'], {'help': 'unique identifier of trilio workload snapshot', 'action': 'store', 'type': str}),
    #         (['config_file'], {'help': 'restore config file', 'action': 'store', 'type': str})
    #     ])
    # )
    # def restore_inplace(self):
    #     snapshot_id = self.app.pargs.snapshot
    #     config_file = self.app.pargs.config_file
    #     config = load_config(config_file)
    #     res = self.client.restore.inplace(snapshot_id, config)
    #     self.app.render(res, details=True)

    @ex(
        help='restore a server from a snapshot. Project with -P must be specified',
        description='restore a server from a snapshot. Project with -P must be specified',
        arguments=OPENSTACK_ARGS([
            (['snapshot'], {'help': 'unique identifier of trilio workload snapshot', 'action': 'store', 'type': str}),
            (['server'], {'help': 'server id', 'action': 'store', 'type': str}),
            (['-server_name'], {'help': 'server name [default=<orig name>-restore-<..>]', 'action': 'store', 
                                'type': str, 'default': None}),
            (['-overwrite'], {'help': 'if True overwrite server', 'action': 'store', 'type': str, 'default': 'false'}),
            (['-name'], {'help': 'restore name', 'action': 'store', 'type': str, 'default': None}),
            (['-desc'], {'help': 'restore description', 'action': 'store', 'type': str, 'default': None}),
            (['-network'], {'help': 'target <network id>:<subnet id>', 'action': 'store', 'type': str,
                            'default': None}),
            (['-keep_ip'], {'help': 'keep original ip', 'action': 'store', 'type': str, 'default': 'false'}),
        ])
    )
    def restore_server(self):
        snapshot_id = self.app.pargs.snapshot
        server_id = self.app.pargs.server
        server_name = self.app.pargs.server_name
        overwrite = str2bool(self.app.pargs.overwrite)
        network = self.app.pargs.network
        keep_ip = str2bool(self.app.pargs.keep_ip)
        if network is None:
            network_id, subnet_id = None, None
        else:
            try:
                network_id, subnet_id = network.split(':')
            except:
                raise Exception('network syntax is <network id>:<subnet id>')
        res = self.client.restore.server(snapshot_id, server_id, server_name=server_name, overwrite=overwrite,
                                         target_network=network_id, target_subnet=subnet_id, keep_original_ip=keep_ip)
        self.app.render(res, details=True)

    @ex(
        help='restore a volume from a snapshot',
        description='restore a volume from a snapshot',
        arguments=OPENSTACK_ARGS([
            (['snapshot'], {'help': 'unique identifier of trilio workload snapshot', 'action': 'store', 'type': str}),
            (['volume'], {'help': 'volume id', 'action': 'store', 'type': str}),
            (['-restore_name'], {'help': 'restore name', 'action': 'store', 'type': str, 'default': None}),
            (['-restore_desc'], {'help': 'restore description', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def restore_volume(self):
        snapshot_id = self.app.pargs.snapshot
        volume_id = self.app.pargs.volume
        overwrite = self.app.pargs.overwrite
        name = self.app.pargs.restore_name
        desc = self.app.pargs.restore_desc
        res = self.client.restore.volume(snapshot_id, volume_id, overwrite=overwrite, name=name, desc=desc)
        self.app.render(res, details=True)
