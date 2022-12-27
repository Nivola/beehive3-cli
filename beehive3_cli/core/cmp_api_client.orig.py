# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import os
import sys
from time import sleep
from cement.utils import fs

from beecell.simple import truncate, dict_get
from beehive.common.apiclient import BeehiveApiClient, BeehiveApiClientError
from beehive3_cli.core.util import load_environment_config


class CmpApiClient(object):
    def __init__(self, app, subsystem, baseuri, key):
        self.app = app
        self.config = load_environment_config(app)
        self.subsystem = subsystem
        self.prefixuri = None
        self.baseuri = baseuri
        self.key = key

        self.client = None

        self._setup()

    # def split_arg(self, key, default=None, keyvalue=True, required=False, splitWith=','):
    #     splitList = []
    #
    #     values = self.get_arg(name=key, default=default, keyvalue=keyvalue, required=required)
    #     if values is not None:
    #         for value in values.split(splitWith):
    #             splitList.append(value)
    #     return splitList

    def _setup(self):
        self.app.log.info('Setup CMP - START')

        self._create_token_dir()

        config = self.config['cmp']

        auth_endpoint = config.get('endpoint', None)
        endpoints = None

        # get auth endpoint
        if auth_endpoint is None:
            auth_endpoint = [dict_get(config, 'endpoints.auth')]
            endpoints = dict_get(config, 'endpoints')
        if auth_endpoint is None:
            raise Exception('Cmp endpoints are not configured')
       
        authtype = config['authtype']       

        user = config.get('user', None)
        pwd = None
        secret = None
        if user is None:
            raise Exception('CMP User must be specified')

        if authtype == 'keyauth':
            pwd = config.get('pwd', None)
            if pwd is None:
                raise Exception('CMP User password must be specified')
        elif authtype == 'oauth2':
            secret = config.get('secret', None)
            if secret is None:
                raise Exception('CMP User secret must be specified')

        # get optional proxy
        proxy = config.get('http_proxy', None)

        # configure beehive client 
        client_config = None
        if authtype == 'oauth2':
            client_config = self.app.oauth2_client.get(self.app.env, None)
            if client_config is None:
                raise Exception('no oauth2 client config available for env %s' % self.app.env)
        prefixuri = config.get('prefix_path', '')
        self.client = BeehiveApiClient(auth_endpoint, authtype, user, pwd, secret, config['catalog'],
                                       client_config=client_config, key=self.key, proxy=proxy, prefixuri=prefixuri)
        # set endpoints manually from config
        if endpoints is not None:
            self.client.set_endpoints(endpoints)

        # get token
        self.client.uid, self.client.seckey = self.get_token()

        if self.client.uid is None:
            # create token
            try:
                self.client.create_token()
            except BeehiveApiClientError as ex:
                if ex.code == 400:
                    self.client.uid, self.client.seckey = '', ''
                    self.app.log.warning('Authorization token can not be created')
                if ex.code == 503:
                    self.client.uid, self.client.seckey = '', ''
                    self.app.log.warning(ex.value)
                else:
                    raise

            # set token
            self.save_token(self.client.uid, self.client.seckey)

        self.app.log.info('Setup CMP - STOP')

    def _get_token_file_full_path(self):
        return fs.abspath('%s/%s.token' % (self.app.config.get('beehive', 'token_file_path'), self.app.env))

    def _get_seckey_file_full_path(self):
        return fs.abspath('%s/%s.seckey' % (self.app.config.get('beehive', 'token_file_path'), self.app.env))

    def _create_token_dir(self):
        path = fs.abspath(self.app.config.get('beehive', 'token_file_path'))
        if os.path.exists(path) is False:
            os.mkdir(path)

    def get_token(self):
        """Get token and secret key from file.

        :return: token
        """
        token = None
        if os.path.isfile(self._get_token_file_full_path()) is True:
            # get token
            f = open(self._get_token_file_full_path(), 'r')
            token = f.read()
            f.close()

        seckey = None
        if os.path.isfile(self._get_seckey_file_full_path()) is True:
            # get secret key
            f = open(self._get_seckey_file_full_path(), 'r')
            seckey = f.read()
            f.close()

        self.app.log.debug('get environment %s token %s' % (self.app.env, token))
        self.app.log.debug('get environment %s secret key %s' % (self.app.env, truncate(seckey)))
        return token, seckey

    def save_token(self, token, seckey):
        """Save token and secret key on a file.

        :param token: token to save
        :param seckey: secret key to save
        """
        # save token
        f = open(self._get_token_file_full_path(), 'w')
        f.write(token)
        f.close()
        # save secret key
        if seckey is not None:
            f = open(self._get_seckey_file_full_path(), 'w')
            f.write(seckey)
            f.close()
        self.app.log.debug('save environment %s token %s' % (self.app.env, token))

    def call(self, uri, method, data='', headers=None, timeout=60, silent=True):
        try:
            # make request
            resp = self.client.invoke(self.subsystem, uri, method, data=data, other_headers=headers, parse=False,
                                      timeout=timeout, silent=silent, print_curl=self.app.curl)
        except BeehiveApiClientError as ex:
            raise Exception(ex.value)
        finally:
            # set token3
            if self.client.uid is not None:
                self.save_token(self.client.uid, self.client.seckey)

        return resp

    # #
    # # job
    # #
    # def get_job_state(self, jobid):
    #     try:
    #         module_uri = self.baseuri.split('/')[2]
    #         res = self.call('/v1.0/%s/worker/tasks/%s' % (module_uri, jobid), 'GET', data='chain=false', silent=True)
    #         # res = self.call('%s/worker/tasks/%s' % (self.baseuri, jobid), 'GET', data='chain=false', silent=True)
    #         state = res.get('task_instance').get('status')
    #         self.app.log.debug('Get job %s state: %s' % (jobid, state))
    #         if state == 'FAILURE':
    #             data = self.app.colored_text.error('%s ..' % res['task_instance']['traceback'][-1])
    #             sys.stdout.write(data)
    #             sys.stdout.flush()
    #         return state
    #     except Exception:
    #         return 'EXPUNGED'
    #
    # def async_result(self, res, msg):
    #     if res is None:
    #         return None
    #     if 'jobid' in res:
    #         self.wait_job(res['jobid'])
    #     self.result({'msg': msg}, headers=['msg'], maxsize=200)
    #
    # def wait_job(self, jobid, delta=2, maxtime=600):
    #     """Wait job
    #
    #     :param jobid:
    #     :param delta:
    #     :param maxtime:
    #     :return:
    #     """
    #     self.app.log.debug('wait for job: %s' % jobid)
    #     state = self.get_job_state(jobid)
    #     sys.stdout.write('JOB:%s' % jobid)
    #     sys.stdout.flush()
    #     elapsed = 0
    #     while state not in ['SUCCESS', 'FAILURE', 'TIMEOUT']:
    #         sys.stdout.write('.')
    #         sys.stdout.flush()
    #         sleep(delta)
    #         state = self.get_job_state(jobid)
    #         elapsed += delta
    #         if elapsed > maxtime:
    #             state = 'TIMEOUT'
    #
    #     if state == 'TIMEOUT':
    #         data = self.app.colored_text.error('..TIMEOUT..')
    #         sys.stdout.write(data)
    #         sys.stdout.flush()
    #     elif state == 'FAILURE':
    #         data = self.app.colored_text.error('- ERROR -')
    #         sys.stdout.write(data)
    #         sys.stdout.flush()
    #
    #     print('END')

    #
    # task
    #
    def get_task_status(self, taskid):
        try:
            module_uri = self.baseuri.split('/')[2]
            res = self.call('/v2.0/%s/worker/tasks/%s/status' % (module_uri, taskid), 'GET', silent=True)
            status = res.get('task_instance').get('status')
            self.app.log.debug('Get task %s status: %s' % (taskid, status))
            return status
        except Exception:
            return 'FAILURE'

    def get_task_trace(self, taskid):
        try:
            module_uri = self.baseuri.split('/')[2]
            res = self.call('/v2.0/%s/worker/tasks/%s/trace' % (module_uri, taskid), 'GET', silent=True)
            trace = res.get('task_trace')[-1]['message']
            self.app.log.debug('Get task %s trace: %s' % (taskid, trace))
            return trace
        except Exception:
            return None

    def wait_task(self, taskid, delta=2, maxtime=600, output=True):
        """Wait task

        :param taskid: task id
        :param delta: poolling interval [default=2]
        :param maxtime: max task time [default=600]
        ;param output: if True print output [default=True]
        :return:
        """
        self.app.log.debug('wait for task: %s' % taskid)
        status = self.get_task_status(taskid)
        if output is True:
            sys.stdout.write('task:%s' % taskid)
            sys.stdout.flush()
        elapsed = 0
        while status not in ['SUCCESS', 'FAILURE', 'TIMEOUT']:
            if output is True:
                sys.stdout.write('.')
                sys.stdout.flush()
            sleep(delta)
            status = self.get_task_status(taskid)
            elapsed += delta
            if elapsed > maxtime:
                status = 'TIMEOUT'

        if status == 'TIMEOUT':
            data = self.app.colored_text.error(':timeout\n')
            if output is True:
                sys.stdout.write(data)
                sys.stdout.flush()
            return False
        elif status == 'FAILURE':
            # data = self.app.colored_text.error(':error\n')
            # if output is True:
            #     sys.stdout.write(data)
            #     sys.stdout.flush()
            # else:
            #     print(self.app.colored_text.error('error'))
            trace = self.get_task_trace(taskid)
            raise Exception(trace)
        else:
            if output is True:
                print(':end')
