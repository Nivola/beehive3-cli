# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from sys import stdout
from re import match
from time import sleep
from beecell.remote import NotFoundException
from beehive3_cli.core.controller import CliController, BaseController
from beehive3_cli.core.util import CmpUtils, rotating_bar, stoprotation
from beehive3_cli.translate import _


class BusinessController(CliController):
    class Meta:
        label = "bu"
        stacked_on = "base"
        stacked_type = "nested"
        description = _("business service and authority management")
        help = _("business service and authority management")

    def _default(self):
        self._parser.print_help()


class BusinessControllerChild(BaseController):
    class Meta:
        stacked_on = "bu"
        stacked_type = "nested"

        cmp = {"baseuri": "/v1.0/nws", "subsystem": "service"}

    def pre_command_run(self):
        super().pre_command_run()
        self.configure_cmp_api_client()

    def is_name(self, oid):
        """Check if id is uuid, id or literal name.

        :param oid:
        :return: True if it is a literal name
        """
        # get obj by uuid
        if self.is_uuid(oid):
            self.app.log.debug("Param %s is an uuid", oid)
            return False
        # get obj by id
        if match("^\\d+$", str(oid)):
            self.app.log.debug("Param %s is an id", oid)
            return False
        # get obj by name
        if match("[\\-\\w\\d]+", oid):
            self.app.log.debug("Param %s is a name", oid)
            return True
        return False

    def is_uuid(self, oid):
        """Check if id is uuid

        :param oid:
        :return: True if it is a uuid
        """
        return match("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", str(oid)) is not None

    def get_account(self, account_id, expired=False):
        """Get account by id

        :param account_id: account id
        :return: account object
        """
        data_base = ""
        # print("get_account - active: %s" % active)
        if expired:
            # data_base = "filter_expired=True&active=False&"
            data_base = "filter_expired=True&"
            # print("get_account - data: %s" % data)

        check = self.is_name(account_id)
        uri = "/v1.0/nws/accounts"
        if check:
            oid = account_id.split(".")
            if len(oid) == 1:
                data = data_base + f"name={oid[0]}"
                res = self.cmp_get(uri, data=data)
            elif len(oid) == 2:
                data = data_base + f"name={oid[1]}&division_id={oid[0]}"
                res = self.cmp_get(uri, data=data)
            elif len(oid) == 3:
                # get division
                data = data_base + f"name={oid[1]}&organization_id={oid[0]}"
                uri2 = "/v1.0/nws/divisions"
                divs = self.cmp_get(uri2, data=data)
                # get account
                if divs.get("count") > 0:
                    name = oid[2]
                    division_uuid = divs["divisions"][0]["uuid"]
                    data = data_base + f"name={name}&division_id={division_uuid}"
                    res = self.cmp_get(uri, data=data)
                else:
                    raise Exception("Account is wrong")
            else:
                raise Exception("Account is wrong")

            count = res.get("count")
            if count > 1:
                raise Exception(f"There are some account with name {account_id}. Select one using uuid")
            if count == 0:
                raise Exception(f"The account {account_id} does not exist")

            account = res.get("accounts")[0]
            self.app.log.info("get account by name: %s", account)
            return account

        data = data_base
        uri += "/" + account_id
        account = self.cmp_get(uri, data).get("account")
        self.app.log.info(f"get account by id: {account}")
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
                data = data_base + f"name={oid[0]}"
                res = self.cmp_get(uri, data=data)
            elif len(oid) == 2:
                # get division
                data = data_base + f"name={oid[1]}&organization_id={oid[0]}"
                uri2 = "/v1.0/nws/divisions"
                res = self.cmp_get(uri2, data=data)
            else:
                raise Exception("Division is wrong")

            count = res.get("count")
            if count > 1:
                raise Exception(f"There are some divisions with name {division_id}. Select one using uuid")
            if count == 0:
                raise Exception(f"The account {division_id} does not exist")

            division = res.get("divisions")[0]
            self.app.log.info(f"get divisions by name: {division}")
            return division

        data = data_base
        uri += "/" + division_id
        division = self.cmp_get(uri, data).get("division")
        self.app.log.info(f"get account by id: {division}")
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
        self.app.log.info(f"get organization by id: {organization}")
        return organization

    def get_service_state(self, uuid, retry_times=10):
        try:
            res = self.cmp_get(f"/v2.0/nws/serviceinsts/{uuid}")
            state = res.get("serviceinst").get("status")
            self.app.log.debug("Get service %s status: %s", uuid, state)
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
            return "UNKNOWN"

    def get_service_instance_error(self, uuid):
        try:
            res = self.cmp_get(f"/v2.0/nws/serviceinsts/{uuid}")
            last_error = res.get("serviceinst").get("last_error")
            self.app.log.debug(f"Get service {uuid} last_error: {last_error}")
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
        self.app.log.info("wait for: %s", uuid)
        state = self.get_service_state(uuid)
        elapsed = 0
        rot_bar = rotating_bar()
        while state not in ["ACTIVE", "ERROR", "DELETED", "TIMEOUT"]:
            # stdout.write(".")
            stdout.write(next(rot_bar))
            stdout.flush()
            self.app.log.info(f"wait for: {uuid}")
            sleep(delta)
            state = self.get_service_state(uuid)
            elapsed += delta
            if elapsed > maxtime and state != accepted_state:
                state = "TIMEOUT"

        stoprotation()
        # set exit code
        if state in ('ACTIVE', 'DELETED'):
            self.app.exit_code = 0
        elif state == "TIMEOUT":
            self.app.exit_code = 253
        else:
            self.app.exit_code = 254

        if state == "ERROR":
            error = self.get_service_instance_error(uuid)
            # raise Exception('Service %s error' % uuid)
            raise Exception(f"Service {uuid} error: {error}")
        return state

    def wait_for_service_v2(self, uuid, delta=3, accepted_state="ACTIVE", maxtime=3600):
        """Wait for service instance

        :param maxtime: timeout threshold
        :param delta:
        :param uuid:
        :param accepted_state: can be ACTIVE, ERROR or DELETED
        """

        def map_state_to_exit_code(state):
            if state in ('ACTIVE', 'DELETED'):
                self.app.exit_code = 0
            elif state == "TIMEOUT":
                self.app.exit_code = 253
            else:
                self.app.exit_code = 254

        self.app.log.info(f"wait for: {uuid}")
        state, __ = CmpUtils.wait_instance(uuid, self.get_service_state, True, delta, maxtime)

        map_state_to_exit_code(state)

        if state == "ERROR":
            error = self.get_service_instance_error(uuid)
            raise Exception(f"Service {uuid} error: {error}")
        if state != accepted_state:
            raise Exception(f"Service {uuid} unexpected status: {state} instead of {accepted_state}")

    def get_service_definition(self, oid):
        """Get service definition

        :param oid:
        :return:
        """
        check = self.is_name(oid)
        if check is True:
            uri = "/v1.0/nws/servicedefs"
            res = self.cmp_get(uri, data=f"name={oid}")
            count = res.get("count")
            if count > 1:
                raise Exception(f"There are some template with name {oid}. Select one using uuid")
            if count == 0:
                raise Exception(f"{oid} does not exist or you are not authorized to see it")

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
            data = f"name={oid}"
            if account_id is not None:
                data += f"&account_id={account_id}"
            res = self.cmp_get(uri, data=data)
            count = res.get("count")
            if count > 1:
                raise Exception(f"There is more than one service with name {oid}. Select one using uuid")
            if count == 0:
                raise Exception(f"{oid} does not exist or you are not authorized to see it")
            return res.get("serviceinsts")[0]
        uri = f"/v2.0/nws/serviceinsts/{oid}"
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
            data = f"name={oid}"
            if account_id is not None:
                data += f"&account_id={account_id}"
            res = self.cmp_get(uri, data=data)
            count = res.get("count")
            if count > 1:
                raise Exception(f"There is more than one service with name {oid}. Select one using uuid")
            if count == 0:
                raise Exception(f"{oid} does not exist or you are not authorized to see it")

            return res.get("serviceinsts")[0]["uuid"]
        return oid

    def get_service_definitions(self, plugintype, prefix=None):
        account = self.get_account(self.app.pargs.account).get("uuid")
        template = self.app.pargs.id
        if template is None:
            data = {"plugintype": plugintype, "size": -1}
            if isinstance(prefix, str):
                data["name"] = prefix
            uri = f"/v2.0/nws/accounts/{account}/definitions"
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
            uri = f"{self.baseuri}/servicedefs/{template}"
            res = self.cmp_get(uri).get("servicedef")
            res.pop("__meta__")
            res.pop("service_type_id")
            res.pop("id")
            res["id"] = res.pop("uuid")
            self.app.render(res, details=True)

            # get service definition configs
            uri = f"{self.baseuri}/servicecfgs"
            res = self.cmp_get(uri, data=f"service_definition_id={template}").get("servicecfgs", [{}])[0]
            params = res.pop("params", {})
            self.c("\nparams", "underline")
            self.app.render(params, details=True)

    def generic_service_delete(self, uuid: str, name: str, plugin: str, force: bool = False):
        """delete a service

        Args:
            uuid (str): _description_
            name (str): _description_
            plugin (str): _description_
        """
        # delete service using specific method if exists
        if plugin == "ComputeInstance":
            data = {"InstanceId.N": [uuid]}
            uri = "/v2.0/nws/computeservices/instance/terminateinstances"
        elif plugin == "DatabaseInstance":
            uri = "/v2.0/nws/databaseservices/instance/deletedbinstance"
            data = {"DBInstanceIdentifier": uuid}
        elif plugin == "StorageEFS":
            uri = f"/v1.0/nws/storageservices/efs/file-systems/{uuid}"
            data = {}
        elif plugin == "LoggingInstance":
            uri = "/v1.0/nws/loggingservices/instance/deleteteinstance"
            data = {"InstanceId": uuid}
        elif plugin == "LoggingSpace":
            uri = "/v1.0/nws/loggingservices/spaces/deletespace"
            data = {"SpaceId": uuid}
        elif plugin == "MonitoringFolder":
            uri = "/v1.0/nws/monitoringservices/folders/deletefolder"
            data = {"FolderId": uuid}
        elif plugin == "MonitoringAlert":
            uri = "/v1.0/nws/monitoringservices/alerts/deletealert"
            data = {"AlertId": uuid}
        elif plugin == "MonitoringInstance":
            uri = "/v1.0/nws/monitoringservices/instance/deleteteinstance"
            data = {"InstanceId": uuid}
        elif plugin == "ComputeKeyPairs":
            data = {"KeyName": uuid}
            uri = "/v1.0/nws/computeservices/keypair/deletekeypair"
        elif plugin == "ComputeSecurityGroup":
            data = {"security_group": {"GroupName": uuid}}
            uri = "/v1.0/nws/computeservices/securitygroup/deletesecuritygroup"
        else:
            ## use service instance api
            uri = f"/v2.0/nws/serviceinsts/{uuid}"
            data = {"force": force, "propagate": True}
        entity = f" {plugin} name: {name} uuid: {uuid}"
        print("Now deleting ", entity, " ...")
        self.cmp_delete(uri, data=data, timeout=1000, entity=entity, output=False)
        state = self.wait_for_service(uuid, delta=2)
        if state == "DELETED":
            print(f" {entity} [{plugin}] deleted")
