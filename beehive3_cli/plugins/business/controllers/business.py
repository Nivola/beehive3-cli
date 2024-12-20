# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from sys import stdout
from re import match
from time import sleep
from beecell.remote import NotFoundException
from beehive3_cli.core.controller import CliController, BaseController
from beehive3_cli.core.util import CmpUtils, rotating_bar


class BusinessController(CliController):
    class Meta:
        label = "bu"
        stacked_on = "base"
        stacked_type = "nested"
        description = "business service and authority management"
        help = "business service and authority management"

    def _default(self):
        self._parser.print_help()


class BusinessControllerChild(BaseController):
    class Meta:
        stacked_on = "bu"
        stacked_type = "nested"

        cmp = {"baseuri": "/v1.0/nws", "subsystem": "service"}

    def pre_command_run(self):
        super(BusinessControllerChild, self).pre_command_run()
        self.configure_cmp_api_client()

    def is_name(self, oid):
        """Check if id is uuid, id or literal name.

        :param oid:
        :return: True if it is a literal name
        """
        # get obj by uuid
        if self.is_uuid(oid):
            self.app.log.debug("Param %s is an uuid" % oid)
            return False
        # get obj by id
        if match("^\\d+$", str(oid)):
            self.app.log.debug("Param %s is an id" % oid)
            return False
        # get obj by name
        if match("[\\-\\w\\d]+", oid):
            self.app.log.debug("Param %s is a name" % oid)
            return True
        return False

    def is_uuid(self, oid):
        """Check if id is uuid

        :param oid:
        :return: True if it is a uuid
        """
        return match("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", str(oid)) is not None

    def get_account(self, account_id, active=True):
        """Get account by id

        :param account_id: account id
        :return: account object
        """
        data_base = ""
        # print("get_account - active: %s" % active)
        if active == False:
            data_base = "filter_expired=True&active=False&"
            # print("get_account - data: %s" % data)

        check = self.is_name(account_id)
        uri = "/v1.0/nws/accounts"
        if check is True:
            oid = account_id.split(".")
            if len(oid) == 1:
                data = data_base + "name=%s" % oid[0]
                res = self.cmp_get(uri, data=data)
            elif len(oid) == 2:
                data = data_base + "name=%s&division_id=%s" % (oid[1], oid[0])
                res = self.cmp_get(uri, data=data)
            elif len(oid) == 3:
                # get division
                data = data_base + "name=%s&organization_id=%s" % (oid[1], oid[0])
                uri2 = "/v1.0/nws/divisions"
                divs = self.cmp_get(uri2, data=data)
                # get account
                if divs.get("count") > 0:
                    data = data_base + "name=%s&division_id=%s" % (
                        oid[2],
                        divs["divisions"][0]["uuid"],
                    )
                    res = self.cmp_get(uri, data=data)
                else:
                    raise Exception("Account is wrong")
            else:
                raise Exception("Account is wrong")

            count = res.get("count")
            if count > 1:
                raise Exception("There are some account with name %s. Select one using uuid" % account_id)
            if count == 0:
                raise Exception("The account %s does not exist" % account_id)

            account = res.get("accounts")[0]
            self.app.log.info("get account by name: %s" % account)
            return account
        else:
            data = data_base

        uri += "/" + account_id
        account = self.cmp_get(uri, data).get("account")
        self.app.log.info("get account by id: %s" % account)
        return account

    def get_account_ids(self, account_ids):
        """Get account id list from string of comma separated id

        :param account_ids: comma separated account id
        :return: list of account object
        """
        res = []
        for account_id in account_ids.split(","):
            res.append(self.get_account(account_id).get("uuid"))

        return res

    def get_division(self, division_id):
        """Get division by id

        :param division_id: division id
        :return: division object
        """
        data_base = ""

        check = self.is_name(division_id)
        uri = "/v1.0/nws/divisions"
        if check is True:
            oid = division_id.split(".")
            if len(oid) == 1:
                data = data_base + "name=%s" % oid[0]
                res = self.cmp_get(uri, data=data)
            elif len(oid) == 2:
                # get division
                data = data_base + "name=%s&organization_id=%s" % (oid[1], oid[0])
                uri2 = "/v1.0/nws/divisions"
                res = self.cmp_get(uri2, data=data)
            else:
                raise Exception("Division is wrong")

            count = res.get("count")
            if count > 1:
                raise Exception("There are some divisions with name %s. Select one using uuid" % division_id)
            if count == 0:
                raise Exception("The account %s does not exist" % division_id)

            division = res.get("divisions")[0]
            self.app.log.info("get divisions by name: %s" % division)
            return division
        else:
            data = data_base

        uri += "/" + division_id
        division = self.cmp_get(uri, data).get("division")
        self.app.log.info("get account by id: %s" % division)
        return division

    def get_organization(self, org_id):
        """Get organization by id

        :param get_organization: organization id
        :return: organization object
        """
        uri = "/v1.0/nws/organizations"
        uri += "/" + org_id
        data = ""
        organization = self.cmp_get(uri, data).get("organization")
        self.app.log.info("get organization by id: %s" % organization)
        return organization

    def get_service_state(self, uuid, retry_times=10):
        try:
            res = self.cmp_get("/v2.0/nws/serviceinsts/%s" % uuid)
            state = res.get("serviceinst").get("status")
            self.app.log.debug("Get service %s status: %s" % (uuid, state))
            return state

        except NotFoundException:
            # print("+++++ get_service_state - NotFoundException")
            return "DELETED"

        except Exception:
            print("connection error")
            retry_times = retry_times - 1
            if retry_times > 0:
                sleep(3)
                return self.get_service_state(uuid, retry_times)
            else:
                return "UNKNOWN"

    def get_service_instance_error(self, uuid):
        try:
            res = self.cmp_get("/v2.0/nws/serviceinsts/%s" % uuid)
            last_error = res.get("serviceinst").get("last_error")
            self.app.log.debug("Get service %s last_error: %s" % (uuid, last_error))
            return last_error
        except (NotFoundException, Exception):
            return ""

    def wait_for_service(self, uuid, delta=1, accepted_state="ACTIVE", maxtime=3600):
        """Wait for service instance

        :param maxtime: timeout threshold
        :param delta:
        :param uuid:
        :param accepted_state: can be ACTIVE, ERROR or DELETED
        """
        self.app.log.info("wait for: %s" % uuid)
        state = self.get_service_state(uuid)
        elapsed = 0
        bar = rotating_bar()
        while state not in ["ACTIVE", "ERROR", "DELETED", "TIMEOUT"]:
            # stdout.write(".")
            stdout.write(next(bar))
            stdout.flush()
            self.app.log.info("wait for: %s" % uuid)
            sleep(delta)
            state = self.get_service_state(uuid)
            elapsed += delta
            if elapsed > maxtime and state != accepted_state:
                state = "TIMEOUT"

        # set exit code
        if state == "ACTIVE" or state == "DELETED":
            self.app.exit_code = 0
        elif state == "TIMEOUT":
            self.app.exit_code = 253
        else:
            self.app.exit_code = 254

        if state == "ERROR":
            error = self.get_service_instance_error(uuid)
            # raise Exception('Service %s error' % uuid)
            raise Exception("Service %s error: %s" % (uuid, error))

        return state

    def wait_for_service_v2(self, uuid, delta=2, accepted_state="ACTIVE", maxtime=3600):
        """Wait for service instance

        :param maxtime: timeout threshold
        :param delta:
        :param uuid:
        :param accepted_state: can be ACTIVE, ERROR or DELETED
        """
        self.app.log.info("wait for: %s" % uuid)
        state, elapsed = CmpUtils.wait_instance(uuid, self.get_service_state, True, delta, maxtime)

        if state == "ERROR":
            error = self.get_service_instance_error(uuid)
            raise Exception("Service %s error: %s" % (uuid, error))
        if state != accepted_state:
            raise Exception("Service %s unexpected status: %s instead of %s" % (uuid, state, accepted_state))

    def get_service_definition(self, oid):
        """Get service definition

        :param oid:
        :return:
        """
        check = self.is_name(oid)
        if check is True:
            uri = "/v1.0/nws/servicedefs"
            res = self.cmp_get(uri, data="name=%s" % oid)
            count = res.get("count")
            if count > 1:
                raise Exception("There are some template with name %s. Select one using uuid" % oid)
            if count == 0:
                raise Exception("%s does not exist or you are not authorized to see it" % oid)

            return res.get("servicedefs")[0]["uuid"]
        return oid

    def get_service_instance_full(self, oid, account_id=None):
        """Get service instance full

        :param oid:
        :param account_id:
        :return: dict
        """
        if self.is_name(oid):
            uri = "/v2.0/nws/serviceinsts"
            data = "name=%s" % oid
            if account_id is not None:
                data += "&account_id=%s" % account_id
            res = self.cmp_get(uri, data=data)
            count = res.get("count")
            if count > 1:
                raise Exception("There is more than one service with name %s. Select one using uuid" % oid)
            if count == 0:
                raise Exception("%s does not exist or you are not authorized to see it" % oid)
            return res.get("serviceinsts")[0]
        else:
            uri = "/v2.0/nws/serviceinsts/%s" % oid
            return self.cmp_get(uri).get("serviceinst", None)

    def get_service_instance(self, oid, account_id=None):
        """Get service instance

        :param oid:
        :param account_id:
        :return: uuid or oid
        """
        check = self.is_name(oid)
        if check is True:
            uri = "/v2.0/nws/serviceinsts"
            data = "name=%s" % oid
            if account_id is not None:
                data += "&account_id=%s" % account_id
            res = self.cmp_get(uri, data=data)
            count = res.get("count")
            if count > 1:
                raise Exception("There is more than one service with name %s. Select one using uuid" % oid)
            if count == 0:
                raise Exception("%s does not exist or you are not authorized to see it" % oid)

            return res.get("serviceinsts")[0]["uuid"]
        return oid

    def get_service_definitions(self, plugintype):
        account = self.get_account(self.app.pargs.account).get("uuid")
        template = self.app.pargs.id
        if template is None:
            data = {"plugintype": plugintype, "size": -1}
            uri = "%s/accounts/%s/definitions" % ("/v2.0/nws", account)
            res = self.cmp_get(uri, data=data)
            headers = [
                "id",
                "name",
                "desc",
                "status",
                "active",
                "creation",
                "is_default",
            ]
            fields = [
                "uuid",
                "name",
                "desc",
                "status",
                "active",
                "date.creation",
                "is_default",
            ]
            self.app.render(res, key="definitions", headers=headers, fields=fields)
        else:
            uri = "%s/servicedefs/%s" % (self.baseuri, template)
            res = self.cmp_get(uri).get("servicedef")
            res.pop("__meta__")
            res.pop("service_type_id")
            res.pop("id")
            res["id"] = res.pop("uuid")
            self.app.render(res, details=True)

            # get service definition configs
            uri = "%s/servicecfgs" % self.baseuri
            res = self.cmp_get(uri, data="service_definition_id=%s" % template).get("servicecfgs", [{}])[0]
            params = res.pop("params", {})
            self.c("\nparams", "underline")
            self.app.render(params, details=True)
