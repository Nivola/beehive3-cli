# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from sys import stdout
from typing import TYPE_CHECKING, Dict, Any, Optional, List, Union
from os import path, mkdir
from time import sleep
from urllib.parse import urlencode

# from beedrones.cmp.client import CmpApiManager, CmpApiClientError
from bee_client.client import CmpApiManager, CmpApiClientError
from cement.utils import fs
from beecell.simple import truncate, dict_get
from beehive3_cli.core.util import load_environment_config, CmpUtils, rotating_bar, stoprotation

if TYPE_CHECKING:
    from beehive3_cli.main import CliManager

class CmpApiClient:
    app: "CliManager"
    client: "CmpApiManager"

    def __init__(self, app: "CliManager", subsystem, baseuri, key):
        self.app = app
        self.config = load_environment_config(app)
        self.subsystem = subsystem
        self.prefixuri = None
        self.baseuri = baseuri
        self.key = key

        self.client = None
        self._setup()

    @property
    def cmpkey(self) -> str:
        res = self.config.get("cmp", {}).get("cmpkey")
        return res

    def _task_trace(self, subsystem, task_id, task_status, msg=None):
        progress_bar = rotating_bar()
        if task_status in ["SUCCESS", "FAILURE", "TIMEOUT"]:
            stdout.write(f"{subsystem} task {task_id} {task_status}\n")
            stdout.flush()
        else:
            stdout.write(next(progress_bar))
            stdout.flush()

    def _setup_resolve_endpoints(self, config: Dict[str, Any]) -> Dict[str, str]:
        auth_endpoint: Optional[List[str]] = config.get("endpoint", None) # type: ignore
        endpoints: Optional[Dict[str, str]] = dict_get(config, "endpoints") # type: ignore
        prefixuri: Optional[str] = config.get("prefix_path", None) # type: ignore

        if endpoints is None:
            if auth_endpoint is None:
                raise Exception("at least endpoints or auth endpoint must be specified")

            # set prefixuri
            if prefixuri is not None and prefixuri != "":
                auth_endpoint[0] = f"{auth_endpoint[0]}{prefixuri}"
            endpoints = {"auth": auth_endpoint[0]}
        else:
            # set prefixuri
            if prefixuri is not None and prefixuri != "":
                for k, v in endpoints.items():
                    endpoints[k] = f"{v}{prefixuri}"

        return endpoints

    def _setup_resolve_user_authparams(self, config: Dict[str, Any], user: str) -> Dict[str, str]:
        authtype = config["authtype"]
        authparams = {"type": authtype, "user": user}

        if authtype == "keyauth":
            pwd = config.get("pwd", None)
            if pwd is None:
                raise Exception("CMP User password must be specified")
            authparams["pwd"] = pwd
        elif authtype == "oauth2":
            secret = config.get("secret", None)
            if secret is None:
                raise Exception("CMP User secret must be specified")
            authparams["secret"] = secret

        # configure beehive client
        client_config = None
        if authtype == "oauth2":
            client = self.app.oauth2_client
            if client and isinstance(client, dict) and (self.app.env in client.keys()):
                # client.json file exists and was parsed
                client_config = client.get(self.app.env, None)
            if not client_config:
                # read from environment configuration
                oauth2_client_id = config.get("oauth2_client", None)
                if oauth2_client_id is None:
                    raise Exception(f"no oauth2 client config available for env {self.app.env}")
                client_config = {"uuid": oauth2_client_id, "grant_type": "user"}
            authparams["client_config"] = client_config
        return authparams

    def _setup(self):
        self.app.log.info("Setup CMP - START")

        self._create_token_dir()
        config: Dict[str, Any] = self.config["cmp"]

        prefixuri: Optional[str] = config.get("prefix_path", None) # type: ignore
        endpoints = self._setup_resolve_endpoints(config)

        user = config.get("user", None)
        if user is None:
            raise Exception("CMP User must be specified")

        authparams = self._setup_resolve_user_authparams(config, user)

        # set user agent cli
        from beehive3_cli.core.version import get_version

        user_agent_cli = f"Beehive3 Console {get_version()}"

        # get optional proxy
        proxy = config.get("http_proxy", None)
        self.client = CmpApiManager(
            endpoints, authparams, key=self.key, proxy=proxy,
            catalog=config["catalog"], user_agent=user_agent_cli
        )
        if prefixuri is not None and prefixuri != "":
            self.client.set_prefixuri(prefixuri)
        self.client.set_task_trace(self._task_trace)
        self.client.set_debug(True)

        # get token
        token, seckey = self.get_token()

        if token is None:
            # create token
            try:
                # headers = {}
                # from beehive3_cli.core.version import get_version
                # headers.update({"User-Agent": "Beehive3 Console %s" % get_version()})
                # self.client.create_token(headers=headers)
                self.client.create_token()
            except CmpApiClientError as ex:
                if ex.code == 400:
                    # TODO check: assignments to be removed.
                    # not used anymore. Was used by BeehiveApiClient
                    self.client.uid, self.client.seckey = "", ""
                    self.app.log.warning("Authorization token can not be created")
                    raise Exception(ex.value)
                if ex.code == 503:
                    # TODO check: assignments to be removed.
                    # not used anymore. Was used by BeehiveApiClient
                    self.client.uid, self.client.seckey = "", ""
                    self.app.log.warning(ex.value)
                    raise Exception(ex.value)
                else:
                    raise

            # set token
            token_data = self.client.get_token()
            self.save_token(token_data.get("token"), token_data.get("seckey"))
        else:
            self.client.set_token(token, seckey=seckey)

        self.app.log.info("Setup CMP - STOP")

    def _get_token_file_full_path(self):
        token_path = self.app.config.get("beehive", "token_file_path")
        return fs.abspath(f"{token_path}/{self.app.env}.token")

    def _get_seckey_file_full_path(self):
        token_path = self.app.config.get("beehive", "token_file_path")
        return fs.abspath(f"{token_path}/{self.app.env}.seckey")

    def _create_token_dir(self):
        token_path = fs.abspath(self.app.config.get("beehive", "token_file_path"))
        if not path.exists(token_path):
            mkdir(token_path)

    def get_token(self):
        """Get token and secret key from file.

        :return: token
        """
        token = None
        token_path = self._get_token_file_full_path()
        
        if path.isfile(token_path):
            # get token
            with open(token_path, "r", encoding="utf-8") as f:
                token = f.read()

        seckey = None
        seckey_path = self._get_seckey_file_full_path()
        
        if path.isfile(seckey_path):
            # get secret key
            with open(seckey_path, "r", encoding="utf-8") as f:
                seckey = f.read()

        self.app.log.debug(f"get environment {self.app.env} token {token}")
        self.app.log.debug(f"get environment {self.app.env} secret key {truncate(str(seckey))}")
        return token, seckey

    def save_token(self, token, seckey):
        """Save token and secret key on a file.

        :param token: token to save
        :param seckey: secret key to save
        """
        # save token
        if token is None:
            raise Exception("token None. Check connection")

        with open(self._get_token_file_full_path(), "w", encoding="utf-8") as f:
            f.write(token)

        # save secret key
        if seckey is not None:
            with open(self._get_seckey_file_full_path(), "w", encoding="utf-8") as f:
                f.write(seckey)
        self.app.log.debug(f"save environment {self.app.env} token {token}")

    def call(
        self, uri: str, method: str, data: Union[Dict, List, str]="",
        headers: Optional[Dict] = None, timeout=60, silent=True
    ) -> Dict[str, Any]:
        try:
            dryrun = getattr(self.app.pargs, "dryrun", False)
            self.client.set_print_curl(self.app.curl)
            self.client.set_timeout(timeout)
            self.client.set_debug(silent)

            raw_response = getattr(self.app.pargs, "raw_response", False)
            self.client.set_print_raw_response(raw_response)

            fake_response = getattr(self.app.pargs, "fake_response", False)
            if fake_response:
                if headers is None:
                    headers = {}
                headers.update({
                    "X-Fake-response": True
                })

            resp = self.client.api_request(
                self.subsystem, uri, method, data=data,
                headers=headers, dryrun=dryrun
            )
            if self.app.curl is True:
                print(self.app.colored_text.blue(self.client.get_curl_request()))
            if raw_response is True:
                print(self.app.colored_text.green(self.client.get_raw_response()))

        except CmpApiClientError as ex:
            self.app.log.debug(ex)
            if self.app.curl is True:   # and self.app.curl_error is True:
                print(self.app.colored_text.yellow(self.client.get_curl_request() or ""))
            if raw_response is True:
                print(self.app.colored_text.red(self.client.get_raw_response()))

            if ex.code == 404:
                from beecell.remote import NotFoundException
                raise NotFoundException(ex.value) from ex

            raise Exception(ex.value) from ex
        finally:
            # set token
            token_data = self.client.get_token()
            if token_data.get("token", None) is not None:
                self.save_token(token_data.get("token", None), token_data.get("seckey", None))

        return resp

    #
    # api service
    #
    @property
    def auth(self):
        return self.client.auth

    @property
    def event(self):
        return self.client.event

    @property
    def catalog(self):
        return self.client.catalog

    @property
    def business(self):
        return self.client.business

    @property
    def resource(self):
        return self.client.resource

    @property
    def ssh(self):
        return self.client.ssh

    #
    # task
    #
    def get_task_status(self, taskid):
        try:
            module_uri = self.baseuri.split("/")[2]
            res = self.call(
                f"/v2.0/{module_uri}/worker/tasks/{taskid}/status",
                "GET",
                silent=True,
            )
            status = res.get("task_instance").get("status")
            self.app.log.debug(f"Get task {taskid} status: {status}")
            # print("+++++ get_task_status - status: %s" % status)
            return status
        except Exception:
            # print("+++++ get_task_status - FAILURE: %s" % status)
            return "FAILURE"

    def get_task_trace(self, taskid):
        try:
            module_uri = self.baseuri.split("/")[2]
            res = self.call(
                f"/v2.0/{module_uri}/worker/tasks/{taskid}/trace",
                "GET",
                silent=True,
            )
            trace = res.get("task_trace")[-1]["message"]
            self.app.log.debug(f"Get task {taskid} trace: {trace}")
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
        self.app.log.debug(f"wait for task: {taskid}")
        status = self.get_task_status(taskid)
        if output is True:
            stdout.write(f"task:{taskid}")
            stdout.flush()
        elapsed = 0
        rot_bar = rotating_bar()
        while status not in ["SUCCESS", "FAILURE", "TIMEOUT"]:
            if output is True:
                # stdout.write(".")
                stdout.write(next(rot_bar))
                stdout.flush()
            sleep(delta)
            status = self.get_task_status(taskid)
            elapsed += delta
            if elapsed > maxtime:
                status = "TIMEOUT"

        # print("+++++ wait_task - status: %s" % status)
        if status == "TIMEOUT":
            data = self.app.colored_text.error(":timeout\n")
            if output is True:
                stoprotation()
                stdout.write(data)
                stdout.flush()
            return
        if status == "FAILURE":
            trace = self.get_task_trace(taskid)
            raise Exception(trace)
        if output is True:
            # print(":end")
            # cover rotating_bar
            stoprotation()
            stdout.write(":end               \n\r")
            stdout.flush()

    def wait_task_v2(self, taskid: str, delta=2, maxtime=600, output=True):
        """Wait task
        :param taskid: task id
        :param delta: poolling interval [default=2]
        :param maxtime: max task time [default=600]
        ;param output: if True print output [default=True]
        :return:
        """
        self.app.log.debug(f"wait for task: {taskid}")
        if output is True:
            stdout.write(f"task:{taskid}")
            stdout.flush()
        status, elapsed = CmpUtils.wait_task(
            task_id=taskid, get_task_status_function=self.get_task_status,
            delta=delta, max_time=maxtime, output=output
        )
        elapsed_str = f"Elapsed: {elapsed.ljust(7)}"
        if status == "TIMEOUT":
            data = self.app.colored_text.error(f":timeout ({elapsed_str})\n")
            if output is True:
                stoprotation()
                stdout.write(data)
                stdout.flush()
        elif status == "FAILURE":
            trace = self.get_task_trace(taskid)
            raise Exception(trace)
        else:
            if output is True:
                # cover rotating_bar
                stoprotation()
                stdout.write(f":end ({elapsed_str})               \n\r")
                stdout.flush()

    def error_if_resource_exists(
        self, restype: Optional[str] = None, name: Optional[str]=None,
        exact_name_match=False, ext_id: Optional[str]=None
    ):
        """
        if the resource specified by name or ext_id exists raise exception
        """
        if name is None and ext_id is None:
            raise Exception("Provide at least name or ext_id")
        if name is not None and ext_id is not None:
            raise Exception("Search either by name or by ext_id, but not both")

        tmp_data_dict: Dict[str, Union[str, int]] = {
            "size": 1,
        }

        if name is not None:
            tmp_name = name if exact_name_match else "%" + name + "%"
            tmp_data_dict["name"] = tmp_name

        if ext_id is not None:
            tmp_data_dict["ext_id"] = ext_id

        if restype is not None:
            tmp_data_dict["type"] = restype

        tmp_data: str = urlencode(tmp_data_dict)
        tmp = self.call("/v1.0/nrs/entities", "GET", data=tmp_data, timeout=240).get("total")
        if tmp != 0:
            if name:
                msg = f"name {tmp_name}" # type: ignore
            if ext_id:
                msg = f"ext_id {ext_id}"
            raise Exception(f"A resource with {msg} already exists ({tmp} found)") # type: ignore

    def error_if_service_exists(
        self, servtype: Optional[str] = None, name: Optional[str] = None,
        exact_name_match=False, flag_container=False
    ):
        """
        if the srvice specified by name exists raise exception
        """
        if name is None:
            raise Exception("name parameter missing")

        tmp_data_dict = {
            "size": 1,
            "flag_container": flag_container,
        }

        if name is not None:
            tmp_name = name if exact_name_match else "%" + name + "%"
            tmp_data_dict["name"] = tmp_name

        if servtype is not None:
            tmp_data_dict["plugintype"] = servtype

        tmp_data = urlencode(tmp_data_dict)
        tmp = self.call("/v2.0/nws/serviceinsts", "GET", data=tmp_data, timeout=240).get("total")
        if tmp != 0:
            msg = f"A service with name {tmp_name}"
            if servtype is not None:
                msg += f"and type {servtype}"
            raise Exception(f"{msg} already exists ({tmp} found)")
