# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from sys import stdout
from os import path, mkdir
from time import sleep
from beedrones.cmp.client import CmpApiManager, CmpApiClientError
from cement.utils import fs
from beecell.simple import truncate, dict_get
from beehive3_cli.core.util import load_environment_config, CmpUtils, rotating_bar


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

    def _task_trace(self, subsystem, task_id, task_status, msg=None):
        bar = rotating_bar()
        if task_status in ["SUCCESS", "FAILURE", "TIMEOUT"]:
            stdout.write("%s task %s %s\n" % (subsystem, task_id, task_status))
            stdout.flush()
        else:
            stdout.write(next(bar))
            stdout.flush()

    def _setup(self):
        self.app.log.info("Setup CMP - START")

        self._create_token_dir()

        config = self.config["cmp"]

        auth_endpoint = config.get("endpoint", None)
        endpoints = dict_get(config, "endpoints")
        authtype = config["authtype"]
        prefixuri = config.get("prefix_path", None)

        if endpoints is None:
            if auth_endpoint is None:
                raise Exception("at least endpoints or auth endpoint must be specified")
            else:
                # set prefixuri
                if prefixuri is not None and prefixuri != "":
                    auth_endpoint[0] = "%s%s" % (auth_endpoint[0], prefixuri)
                endpoints = {"auth": auth_endpoint[0]}
        else:
            # set prefixuri
            if prefixuri is not None and prefixuri != "":
                for k, v in endpoints.items():
                    endpoints[k] = "%s%s" % (v, prefixuri)

        user = config.get("user", None)
        if user is None:
            raise Exception("CMP User must be specified")

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

        # get optional proxy
        proxy = config.get("http_proxy", None)

        # configure beehive client
        client_config = None
        if authtype == "oauth2":
            if self.app.oauth2_client is None:  # client.json file does not exist
                oauth2_client_id = config.get("oauth2_client", None)
                if oauth2_client_id is None:
                    raise Exception("no oauth2 client is configured")
                client_config = {"uuid": oauth2_client_id, "grant_type": "user"}
            elif isinstance(
                self.app.oauth2_client, str
            ):  # client.json file exists but oauth2_client specified as string in the environment file
                client_config = {"uuid": oauth2_client_id, "grant_type": "user"}
            else:
                client_config = self.app.oauth2_client.get(
                    self.app.env, None
                )  # read config from client.json based on environment name
                if client_config is None:
                    raise Exception("no oauth2 client config available for env %s" % self.app.env)
            authparams["client_config"] = client_config

        # set user agent cli
        from beehive3_cli.core.version import get_version

        user_agent_cli = "Beehive3 Console %s" % get_version()

        self.client = CmpApiManager(
            endpoints, authparams, key=self.key, proxy=proxy, catalog=config["catalog"], user_agent=user_agent_cli
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
                    self.client.uid, self.client.seckey = "", ""
                    self.app.log.warning("Authorization token can not be created")
                if ex.code == 503:
                    self.client.uid, self.client.seckey = "", ""
                    self.app.log.warning(ex.value)
                else:
                    raise

            # set token
            token_data = self.client.get_token()
            self.save_token(token_data.get("token"), token_data.get("seckey"))
        else:
            self.client.set_token(token, seckey=seckey)

        self.app.log.info("Setup CMP - STOP")

    def _get_token_file_full_path(self):
        return fs.abspath("%s/%s.token" % (self.app.config.get("beehive", "token_file_path"), self.app.env))

    def _get_seckey_file_full_path(self):
        return fs.abspath("%s/%s.seckey" % (self.app.config.get("beehive", "token_file_path"), self.app.env))

    def _create_token_dir(self):
        token_path = fs.abspath(self.app.config.get("beehive", "token_file_path"))
        if path.exists(token_path) is False:
            mkdir(token_path)

    def get_token(self):
        """Get token and secret key from file.

        :return: token
        """
        token = None
        if path.isfile(self._get_token_file_full_path()) is True:
            # get token
            f = open(self._get_token_file_full_path(), "r")
            token = f.read()
            f.close()

        seckey = None
        if path.isfile(self._get_seckey_file_full_path()) is True:
            # get secret key
            f = open(self._get_seckey_file_full_path(), "r")
            seckey = f.read()
            f.close()

        self.app.log.debug("get environment %s token %s" % (self.app.env, token))
        self.app.log.debug("get environment %s secret key %s" % (self.app.env, truncate(seckey)))
        return token, seckey

    def save_token(self, token, seckey):
        """Save token and secret key on a file.

        :param token: token to save
        :param seckey: secret key to save
        """
        # save token
        if token is None:
            raise Exception("token None. Check connection")

        f = open(self._get_token_file_full_path(), "w")
        f.write(token)
        f.close()
        # save secret key
        if seckey is not None:
            f = open(self._get_seckey_file_full_path(), "w")
            f.write(seckey)
            f.close()
        self.app.log.debug("save environment %s token %s" % (self.app.env, token))

    def call(self, uri, method, data="", headers=None, timeout=60, silent=True):
        try:
            # if headers is None:
            #     headers = {}

            # from beehive3_cli.core.version import get_version
            # headers.update({"User-Agent": "Beehive3 Console %s" % get_version()})

            self.client.set_print_curl(self.app.curl)
            self.client.set_timeout(timeout)
            self.client.set_debug(silent)
            resp = self.client.api_request(self.subsystem, uri, method, data=data, headers=headers)
            if self.app.curl is True:
                print(self.app.colored_text.blue(self.client.get_curl_request()))
        except CmpApiClientError as ex:
            if self.app.curl is True and self.app.curl_error is True:
                print(self.app.colored_text.yellow(self.client.get_curl_request() or ""))

            if ex.code == 404:
                from beecell.remote import NotFoundException

                raise NotFoundException(ex.value)
            else:
                raise Exception(ex.value)
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
                "/v2.0/%s/worker/tasks/%s/status" % (module_uri, taskid),
                "GET",
                silent=True,
            )
            status = res.get("task_instance").get("status")
            self.app.log.debug("Get task %s status: %s" % (taskid, status))
            # print("+++++ get_task_status - status: %s" % status)
            return status
        except Exception:
            # print("+++++ get_task_status - FAILURE: %s" % status)
            return "FAILURE"

    def get_task_trace(self, taskid):
        try:
            module_uri = self.baseuri.split("/")[2]
            res = self.call(
                "/v2.0/%s/worker/tasks/%s/trace" % (module_uri, taskid),
                "GET",
                silent=True,
            )
            trace = res.get("task_trace")[-1]["message"]
            self.app.log.debug("Get task %s trace: %s" % (taskid, trace))
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
        self.app.log.debug("wait for task: %s" % taskid)
        status = self.get_task_status(taskid)
        if output is True:
            stdout.write("task:%s" % taskid)
            stdout.flush()
        elapsed = 0
        bar = rotating_bar()
        while status not in ["SUCCESS", "FAILURE", "TIMEOUT"]:
            if output is True:
                # stdout.write(".")
                stdout.write(next(bar))
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
                stdout.write(data)
                stdout.flush()
            return False
        elif status == "FAILURE":
            trace = self.get_task_trace(taskid)
            raise Exception(trace)
        else:
            if output is True:
                # print(":end")
                # cover rotating_bar
                stdout.write(":end               \n\r")
                stdout.flush()

    def wait_task_v2(self, taskid, delta=2, maxtime=600, output=True):
        """Wait task
        :param taskid: task id
        :param delta: poolling interval [default=2]
        :param maxtime: max task time [default=600]
        ;param output: if True print output [default=True]
        :return:
        """
        self.app.log.debug("wait for task: %s" % taskid)
        if output is True:
            stdout.write("task:%s" % taskid)
            stdout.flush()
        status, elapsed = CmpUtils.wait_task(
            task_id=taskid, get_task_status_function=self.get_task_status, delta=delta, max_time=maxtime, output=output
        )
        elapsed_str = f"Elapsed: {elapsed.ljust(7)}"
        if status == "TIMEOUT":
            data = self.app.colored_text.error(":timeout (%s)\n" % elapsed_str)
            if output is True:
                stdout.write(data)
                stdout.flush()
            return False
        elif status == "FAILURE":
            trace = self.get_task_trace(taskid)
            raise Exception(trace)
        else:
            if output is True:
                # cover rotating_bar
                stdout.write(":end (%s)               \n\r" % elapsed_str)
                stdout.flush()
