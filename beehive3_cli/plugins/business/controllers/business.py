# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from sys import stdout
from re import match
from time import sleep
from beecell.remote import NotFoundException
from beehive3_cli.core.controller import CliController, BaseController


class BusinessController(CliController):
    class Meta:
        label = 'bu'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'business service and authority management'
        help = 'business service and authority management'

    def _default(self):
        self._parser.print_help()


class BusinessControllerChild(BaseController):
    class Meta:
        stacked_on = 'bu'
        stacked_type = 'nested'        

        cmp = {'baseuri': '/v1.0/nws', 'subsystem': 'service'}

    def pre_command_run(self):
        super(BusinessControllerChild, self).pre_command_run()
        self.configure_cmp_api_client()

    def is_name(self, oid):
        """Check if id is uuid, id or literal name.

        :param oid:
        :return: True if it is a literal name
        """
        # get obj by uuid
        if match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
            self.app.log.debug('Param %s is an uuid' % oid)
            return False
        # get obj by id
        elif match('^\d+$', str(oid)):
            self.app.log.debug('Param %s is an id' % oid)
            return False
        # get obj by name
        elif match('[\-\w\d]+', oid):
            self.app.log.debug('Param %s is a name' % oid)
            return True

    def is_uuid(self, oid):
        """Check if id is uuid

        :param oid:
        :return: True if it is a uuid
        """
        if match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)) is not None:
            return True
        return False

    def get_account(self, account_id):
        """Get account by id

        :param account_id: account id
        :return: account object
        """
        check = self.is_name(account_id)
        uri = '/v1.0/nws/accounts'
        if check is True:
            oid = account_id.split('.')
            if len(oid) == 1:
                data = 'name=%s' % oid[0]
                res = self.cmp_get(uri, data=data)
            elif len(oid) == 2:
                data = 'name=%s&division_id=%s' % (oid[1], oid[0])
                res = self.cmp_get(uri, data=data)
            elif len(oid) == 3:
                # get division
                data = 'name=%s&organization_id=%s' % (oid[1], oid[0])
                uri2 = '/v1.0/nws/divisions'
                divs = self.cmp_get(uri2, data=data)
                # get account
                if divs.get('count') > 0:
                    data = 'name=%s&division_id=%s' % (oid[2], divs['divisions'][0]['uuid'])
                    res = self.cmp_get(uri, data=data)
                else:
                    raise Exception('Account is wrong')
            else:
                raise Exception('Account is wrong')

            count = res.get('count')
            if count > 1:
                raise Exception('There are some account with name %s. Select one using uuid' % account_id)
            if count == 0:
                raise Exception('The account %s does not exist' % account_id)

            account = res.get('accounts')[0]
            self.app.log.info('get account by name: %s' % account)
            return account

        uri += '/' + account_id
        account = self.cmp_get(uri).get('account')
        self.app.log.info('get account by id: %s' % account)
        return account

    def get_account_ids(self, account_ids):
        """Get account id list from string of comma separated id

        :param account_ids: comma separated account id
        :return: list of account object
        """
        res = []
        for account_id in account_ids.split(','):
            res.append(self.get_account(account_id).get('uuid'))

        return res

    def get_service_state(self, uuid):
        try:
            res = self.cmp_get('/v2.0/nws/serviceinsts/%s' % uuid)
            state = res.get('serviceinst').get('status')
            self.app.log.debug('Get service %s status: %s' % (uuid, state))
            return state
        except (NotFoundException, Exception):
            return 'DELETED'

    def get_service_instance_error(self, uuid):
        try:
            res = self.cmp_get('/v2.0/nws/serviceinsts/%s' % uuid)
            last_error = res.get('serviceinst').get('last_error')
            self.app.log.debug('Get service %s last_error: %s' % (uuid, last_error))
            return last_error
        except (NotFoundException, Exception):
            return ''

    def wait_for_service(self, uuid, delta=1, accepted_state='ACTIVE', maxtime=3600):
        """Wait for service instance

        :param maxtime: timeout threshold
        :param delta:
        :param uuid:
        :param accepted_state: can be ACTIVE, ERROR or DELETED
        """
        self.app.log.info('wait for: %s' % uuid)
        state = self.get_service_state(uuid)
        elapsed = 0
        while state not in ['ACTIVE', 'ERROR', 'DELETED', 'TIMEOUT']:
            stdout.write('.')
            stdout.flush()
            self.app.log.info('wait for: %s' % uuid)
            sleep(delta)
            state = self.get_service_state(uuid)
            elapsed += delta
            if elapsed > maxtime and state != accepted_state:
                state = 'TIMEOUT'
        if state == 'ERROR':
            error = self.get_service_instance_error(uuid)
            # raise Exception('Service %s error' % uuid)
            raise Exception('Service %s error: %s' % (uuid, error))

    def get_service_definition(self, oid):
        """Get service definition

        :param oid:
        :return:
        """
        check = self.is_name(oid)
        if check is True:
            uri = '/v1.0/nws/servicedefs'
            res = self.cmp_get(uri, data='name=%s' % oid)
            count = res.get('count')
            if count > 1:
                raise Exception('There are some template with name %s. Select one using uuid' % oid)
            if count == 0:
                raise Exception('%s does not exist or you are not authorized to see it' % oid)

            return res.get('servicedefs')[0]['uuid']
        return oid

    def get_service_instance(self, oid, account_id=None):
        """Get service instance

        :param oid:
        :param account_id:
        :return:
        """
        check = self.is_name(oid)
        if check is True:
            uri = '/v2.0/nws/serviceinsts'
            data = 'name=%s' % oid
            if account_id is not None:
                data += '&account_id=%s' % account_id
            res = self.cmp_get(uri, data=data)
            count = res.get('count')
            if count > 1:
                raise Exception('There are some service with name %s. Select one using uuid' % oid)
            if count == 0:
                raise Exception('%s does not exist or you are not authorized to see it' % oid)

            return res.get('serviceinsts')[0]['uuid']
        return oid

    def get_service_definitions(self, plugintype):
        account = self.get_account(self.app.pargs.account).get('uuid')
        template = self.app.pargs.id
        if template is None:
            data = {'plugintype': plugintype, 'size': -1}
            uri = '%s/accounts/%s/definitions' % ('/v2.0/nws', account)
            res = self.cmp_get(uri, data=data)
            headers = ['id', 'image_type', 'desc', 'status', 'active', 'creation', 'is_default']
            fields = ['uuid', 'name', 'desc', 'status', 'active', 'date.creation', 'is_default']
            self.app.render(res, key='definitions', headers=headers, fields=fields)
        else:
            uri = '%s/servicedefs/%s' % (self.baseuri, template)
            res = self.cmp_get(uri).get('servicedef')
            res.pop('__meta__')
            res.pop('service_type_id')
            res.pop('id')
            res['id'] = res.pop('uuid')
            self.app.render(res, details=True)

            # get rules
            uri = '%s/servicecfgs' % self.baseuri
            res = self.cmp_get(uri, data='service_definition_id=%s' % template).get('servicecfgs', [{}])[0]
            params = res.pop('params', {})
            self.c('\nparams', 'underline')
            self.app.render(params, details=True)

    @staticmethod
    def __join(items):
        return ', '.join(item for item in items)
