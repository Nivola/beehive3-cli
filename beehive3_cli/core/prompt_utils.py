#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


import os
import fnmatch
import re
import ipaddress
from threading import Thread
from time import time, sleep
from typing import Generator, Tuple, Optional, List, Dict, TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter, Completion, Completer
from prompt_toolkit.validation import Validator, ValidationError, _ValidatorFromCallable
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.key_binding.bindings.completion import generate_completions

from beecell.types.type_dict import dict_get
from beehive3_cli.plugins.business.controllers.business import BusinessControllerChild
from beehive3_cli.translate import _
if TYPE_CHECKING:
    from beehive3_cli.main import CliManager

FQDN_REGEX = re.compile(
    r"^(?=.{1,255}$)"  # lunghezza totale
    r"([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"  # label intermedie
    r"[A-Za-z](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$"  # TLD non numerico
)

LABEL_REGEX = re.compile("^(?![0-9]+$)(?!-)[a-zA-Z0-9-]{,63}(?<!-)$")


class IPv4Validator(Validator):
    def validate(self, document):
        text = document.text.strip()

        try:
            ipaddress.IPv4Address(text)
        except ValueError as exc:
            raise ValidationError(
                message="Please use a valid IPv4 address (e.g.: 192.168.1.1)",
                cursor_position=len(text),
            ) from exc


class IPv4ListValidator(Validator):
    def validate(self, document):
        text = document.text.strip()

        if not text:
            return
        #     raise ValidationError(
        #         message="Inserisci almeno un IP o CIDR",
        #         cursor_position=0
        #     )

        # separa per virgola
        parts = [p.strip() for p in text.split(",")]

        for part in parts:
            try:
                # prova come IP singolo
                ipaddress.IPv4Address(part)
                continue
            except ValueError:
                pass

            try:
                # prova come CIDR
                ipaddress.IPv4Network(part, strict=False)
                continue
            except ValueError:
                pass

            # Se non è né IP né CIDR → errore
            raise ValidationError(message=f"{_('not a valid IPv4 or CIDR ')} '{part}' ", cursor_position=len(text))


class AlNumValidator(Validator):
    """Alfa num validator

    Args:
        Validator (_type_): _description_
    """

    def __init__(self, maxlength: int, not_in: List[str] = None, app=None):
        super().__init__()
        self.app = app
        self.length = maxlength
        if not_in is not None:
            self.not_in = not_in
        else:
            self.not_in = []

    def validate(self, document):
        text = document.text.strip()
        if self.app:
            self.app.log.info(f"text: {text}")
        if not text.isalnum():
            raise ValidationError(message=_("Not a valid alfa num text "), cursor_position=len(text))
        if len(text) > self.length:
            raise ValidationError(message=_("Too long"), cursor_position=len(text))
        if text in self.not_in:
            raise ValidationError(message=_("Not  unique"), cursor_position=len(text))


class FQDNValidator(Validator):
    def validate(self, document):
        text = document.text.strip()
        if not FQDN_REGEX.match(text):
            raise ValidationError(
                message=_("Not a valid fqdn (example: myserver.example.com)"), cursor_position=len(text)
            )


class LabelValidator(Validator):
    def validate(self, document):
        text = document.text.strip()
        if not LABEL_REGEX.match(text):
            raise ValidationError(message=_("Not a valid name (Dns Label)"), cursor_position=len(text))


class NumberValidator(Validator):
    app: 'CliManager'
    length: int

    def __init__(self, app, length):
        super().__init__()
        self.app = app
        self.length = length

    def validate(self, document):
        text = document.text
        self.app.log.info(f"text: {text}")
        if len(text) != self.length:
            raise ValidationError(message=f"Insert {self.length} digits")
        if not text.isnumeric():
            raise ValidationError(message="Insert only digits")


class MandatoryValidator(Validator):
    app: 'CliManager'
    length: int

    def __init__(self, app: 'CliManager', length=-1):
        super().__init__()
        self.app = app
        self.length = length

    def validate(self, document):
        text = document.text
        self.app.log.info(f"text: {text}")
        if not text:
            raise ValidationError(message="Insert value")
        if self.length > 0 and len(text) > self.length:
            raise ValidationError(message=f"Max length {self.length}")


class CmpValidator(Validator):
    app: 'CliManager'
    values: List = []
    required = False

    def __init__(self, app, values, required: bool = True):
        super().__init__()
        self.app = app
        self.values = values
        self.required = required

    def validate(self, document):
        text = document.text
        self.app.log.info(f"text: {text}")
        if self.required:
            if not text or text not in self.values:
                raise ValidationError(message="Select item")
        else:
            if text and text not in self.values:
                raise ValidationError(message="Select valid item or none")


class PromptUtil:
    kb = KeyBindings()
    handle = kb.add

    def __init__(self):
        pass

    # @handle("tab", filter=readline_complete_style & default_focused)
    @handle("space")
    @handle("down")
    def _complete_like_readline(event) -> None:
        "Display completions (like Readline)."
        # display_completions_like_readline(event)
        generate_completions(event)

    @staticmethod
    def start_completer(prompt_session: PromptSession):
        # open completer after prompt is running
        def open_completer(prompt_session: PromptSession):
            sleep_millis = 0.01
            while sleep_millis < 3:
                try:
                    sleep(sleep_millis)
                    prompt_session.app.current_buffer.start_completion(insert_common_part=True)
                    return
                except Exception:
                    # in case prompt doesn't already running ...RuntimeError: no running event loop
                    sleep_millis += 0.1

        thread_complete = Thread(target=open_completer, args=[prompt_session])
        thread_complete.start()


class ControlThread:
    stop_threads = None

    def __init__(self):
        self.stop_threads = False

    def stop(self):
        self.stop_threads = True


def loading(what, start_time=None) -> Generator[str, None, None]:
    """
    loading
    """
    prefix = f"...loading {what}  "
    if start_time:
        st_time = start_time
    else:
        st_time = time()
    rotobar = ("-", "\\", "|", "/")
    len_rotobar = len(rotobar)
    len_message = len(prefix) + 7 + 1  # two spaces + ljust 7 + rotobar item
    i = 0
    while True:
        pre = f"{(time()-st_time):.2f}"
        pre = prefix + pre.ljust(7, " ")
        yield pre + rotobar[i] + f"\33[{len_message}D"
        i += 1
        i %= len_rotobar


def progress(what, control_thread: ControlThread):
    # out = args[0]
    control_thread.stop_threads = False
    # bar = rotating_bar()
    load_bar = loading(what)
    while True:
        from sys import stdout

        stdout.write(next(load_bar))
        stdout.flush()
        sleep(0.09)

        if control_thread.stop_threads:
            # self.stream.write("aaa stop")
            break


def start_progress(what: str):
    control_thread = ControlThread()
    thread_progress = Thread(target=progress, args=[what, control_thread])
    thread_progress.start()
    return control_thread


class PromptAccount:
    def get_account(controller: BusinessControllerChild, prompt_prefix: str) -> Tuple[str, str]:
        # organization
        control_thread = start_progress("organizations")

        uri = "/v1.0/nws/organizations"
        data = {
            "page": 0,
            "size": -1,
            "field": "name",
            "order": "ASC",
        }
        res = controller.cmp_get(uri, data=data)
        control_thread.stop()
        organizations: List[Dict] = dict_get(res, "organizations") # type: ignore
        org_names: List[str] = [organization.get("name") for organization in organizations] # type: ignore
        org_completer = WordCompleter(org_names, ignore_case=True, match_middle=True)
        org_session = PromptSession(completer=org_completer)  # , placeholder="<tab> for selecting")
        PromptUtil.start_completer(org_session)
        vm_org = org_session.prompt(
            f"{prompt_prefix} organization > ",
            search_ignore_case=True,
            key_bindings=PromptUtil.kb,
            validator=CmpValidator(controller.app, org_names, required=False),
        )

        # division
        control_thread = start_progress("divisions")

        uri = "/v1.0/nws/divisions"
        data = {
            "page": 0,
            "size": -1,
            "field": "name",
            "order": "ASC",
        }
        if vm_org:
            for organization in organizations:
                if organization.get("name") == vm_org:
                    org_id = organization.get("id")
                    data.update({"organization_id": org_id})

        res = controller.cmp_get(uri, data=data)
        control_thread.stop()
        divisions: List[Dict] = dict_get(res, "divisions") # type: ignore
        division_names: List[str] = [division.get("name") for division in divisions] # type: ignore
        division_completer = WordCompleter(division_names, ignore_case=True, match_middle=True)
        division_session = PromptSession(completer=division_completer)
        PromptUtil.start_completer(division_session)
        vm_division = division_session.prompt(
            f"{prompt_prefix} division > ",
            search_ignore_case=True,
            key_bindings=PromptUtil.kb,
            validator=CmpValidator(controller.app, division_names, required=False),
        )

        # account
        control_thread = start_progress("accounts")

        uri = f"{controller.baseuri}/accounts"
        data = {
            "page": 0,
            "size": -1,
            "field": "name",
            "order": "ASC",
        }

        if vm_division:
            for division in divisions:
                if division.get("name") == vm_division:
                    division_id = division.get("id")
                    data.update({"division_id": division_id})

        res = controller.cmp_get(uri, data=data)
        control_thread.stop()
        accounts = res.get("accounts")
        account_names = [account.get("name") for account in accounts]

        account_completer = WordCompleter(account_names, ignore_case=True, match_middle=True)
        account_session = PromptSession(
            completer=account_completer, search_ignore_case=True, complete_while_typing=True
        )
        vm_account = None
        vm_account_uuid = None
        while vm_account_uuid is None:
            PromptUtil.start_completer(account_session)
            vm_account = account_session.prompt(
                f"{prompt_prefix} account > ",
                search_ignore_case=True,
                key_bindings=PromptUtil.kb,
                validator=CmpValidator(controller.app, account_names),
            )

            for account in accounts:
                if account.get("name") == vm_account:
                    vm_account_uuid = account.get("uuid")

        return vm_account, vm_account_uuid


class RecursiveFilePatternCompleter(Completer):
    def __init__(self, patterns, base_path="."):
        """
        patterns: lista di pattern (es: ["*.yml", "*.json"])
        base_path: directory radice da cui partire
        """
        self.patterns = patterns
        self.base_path = base_path

    def iter_matches(self, dirname):
        """Restituisce file (filtrati) + directory, da mostrare come completamenti."""
        try:
            entries = os.listdir(dirname)
        except FileNotFoundError:
            return [], []

        files = []
        dirs = []

        for entry in entries:
            full = os.path.join(dirname, entry)
            if os.path.isdir(full):
                dirs.append(entry + "/")
            else:
                # file match sui pattern
                for pattern in self.patterns:
                    if fnmatch.fnmatch(entry, pattern):
                        files.append(entry)
                        break

        return files, dirs

    def get_completions(self, document, complete_event):
        text = document.text.strip()

        # Caso base: niente digitato → mostra contenuto della root
        if not text:
            dirname = self.base_path
            prefix = ""
        else:
            # Identifica dirname e prefix relativi al testo digitato
            if text.endswith("/"):
                # utente ha completato una directory → entra in essa
                dirname = os.path.join(self.base_path, text)
                prefix = ""
            else:
                dirname = os.path.join(self.base_path, os.path.dirname(text))
                prefix = os.path.basename(text)

        files, dirs = self.iter_matches(dirname)

        # Directory sempre mostrate e filtrate per prefix
        for d in dirs:
            if d.startswith(prefix):
                yield Completion(d, start_position=-len(prefix), display=os.path.join(dirname, d))

        # File filtrati per prefix
        for f in files:
            if f.startswith(prefix):
                yield Completion(f, start_position=-len(prefix), display=os.path.join(dirname, f))


class PromptTool:
    def __init__(
        self,
        controller: BusinessControllerChild = None,
        account_uuid: Optional[str] = None,
        account: Optional[str] = None,
    ) -> None:
        self._account: Optional[str] = account
        self._account_uuid: Optional[str] = account_uuid
        self._controller: BusinessControllerChild = controller
        self._session: Optional[PromptSession] = None
        self._filevalidator: Optional[Validator] = None
        self._ipv4listvalidator: Optional[Validator] = None
        self._digitvalidator: Optional[Validator] = None
        self._fqdnvalidator: Optional[Validator] = None
        self._labelvalidator: Optional[Validator] = None

    @property
    def labelvalidator(self) -> Validator:
        if self._labelvalidator is not None:
            return self._labelvalidator
        self._labelvalidator = LabelValidator()
        return self._labelvalidator

    @property
    def fqdnvalidator(self) -> Validator:
        if self._fqdnvalidator is not None:
            return self._fqdnvalidator
        self._fqdnvalidator = FQDNValidator()
        return self._fqdnvalidator

    @property
    def digitvalidator(self) -> Validator:
        if self._digitvalidator is not None:
            return self._digitvalidator
        self._digitvalidator = _ValidatorFromCallable(
            lambda x: x.isnumeric(), _("Not a digit"), move_cursor_to_end=False
        )
        return self._digitvalidator

    @property
    def ipv4listvalidator(self) -> Validator:
        if self._ipv4listvalidator is not None:
            return self._ipv4listvalidator
        self._ipv4listvalidator = IPv4ListValidator()
        return self._ipv4listvalidator

    @property
    def file_validator(self) -> Validator:
        if self._filevalidator is not None:
            return self._filevalidator
        self._filevalidator = _ValidatorFromCallable(os.path.exists, _("File not found"), move_cursor_to_end=False)
        return self._filevalidator

    @property
    def session(self) -> PromptSession:
        if self._session is not None:
            return self._session
        self._session = PromptSession(key_bindings=PromptUtil.kb)
        return self._session

    def _check(self) -> None:
        """check  accounti have yet been set, if not prompt for account"""
        if self._account_uuid is None:
            self._account, self._account_uuid = self.get_account()

    def get_account(self, prompt_prefix: str = "") -> Tuple[str, str]:
        """prompt for anm account by choosing organization, divisionamd account

        Args:
            prompt_prefix (str, optional): _description_. Defaults to "".

        Returns:
            Tuple[str, str]: _description_
        """
        if self._account is not None:
            return self._account, self._account_uuid
        # organization
        control_thread = start_progress("organizations")

        uri = "/v1.0/nws/organizations"
        data = {
            "page": 0,
            "size": -1,
            "field": "name",
            "order": "ASC",
        }
        res = self._controller.cmp_get(uri, data=data)
        control_thread.stop()
        organizations = dict_get(res, "organizations")
        org_names = [organization.get("name") for organization in organizations]
        org_names.sort()
        vm_org = self.get_word(opts=org_names, prompt_prefix=f"{prompt_prefix} organization > ")

        # division
        control_thread = start_progress("divisions")

        uri = "/v1.0/nws/divisions"
        data = {
            "page": 0,
            "size": -1,
            "field": "name",
            "order": "ASC",
        }
        if vm_org:
            for organization in organizations:
                if organization.get("name") == vm_org:
                    org_id = organization.get("id")
                    data.update({"organization_id": org_id})

        res = self._controller.cmp_get(uri, data=data)
        control_thread.stop()
        divisions = dict_get(res, "divisions")
        division_names = [division.get("name") for division in divisions]
        division_names.sort()
        vm_division = self.get_word(opts=division_names, prompt_prefix=f"{prompt_prefix} division > ")

        # account
        control_thread = start_progress("accounts")

        uri = "/v2.0/nws/accounts"
        data = {
            "page": 0,
            "size": -1,
            "field": "name",
            "order": "ASC",
        }

        if vm_division:
            for division in divisions:
                if division.get("name") == vm_division:
                    division_id = division.get("id")
                    data.update({"division_id": division_id})

        res = self._controller.cmp_get(uri, data=data)
        control_thread.stop()
        accounts = res.get("accounts")
        account_names = [account.get("name") for account in accounts]
        account_names.sort()

        account_completer = WordCompleter(account_names, ignore_case=True, match_middle=True)
        account_session = PromptSession(
            completer=account_completer, search_ignore_case=True, complete_while_typing=True
        )
        vm_account = None
        vm_account_uuid = None
        while vm_account_uuid is None:
            PromptUtil.start_completer(account_session)
            vm_account = self.get_word(opts=account_names, prompt_prefix=f"{prompt_prefix} account > ")

            for account in accounts:
                if account.get("name") == vm_account:
                    vm_account_uuid = account.get("uuid")
        self._account = vm_account
        self._account_uuid = vm_account_uuid
        return vm_account, vm_account_uuid

    def get_lbaas_flavours(self, prompt_prefix: str = "", default: str = "") -> str:
        self._check()
        uri = f"/v1.0/nws/account/{self._account_uuid}/network/lbaas_flavours"
        res: dict = self._controller.cmp_get(uri)
        lb: dict = res.get("flavours")
        names = [instance.get("name") for instance in lb]
        names.sort()
        return self.get_word(names, prompt_prefix=prompt_prefix, default=default)

    def get_lbaas_templates(self, prompt_prefix: str = "", default: str = "") -> str:
        """Prompt for a lbaas template in  the account

        Args:
            prompt_prefix (str, optional): _description_. Defaults to "".
            default (str, optional): _description_. Defaults to "".

        Returns:
            str: _description_
        """
        self._check()

        uri = f"/v1.0/nws/account/{self._account_uuid}/network/lbaas_templates"
        res: dict = self._controller.cmp_get(uri)
        lb: dict = res.get("templates")

        names = [instance.get("name") for instance in lb]
        names.sort()
        return self.get_word(names, prompt_prefix=prompt_prefix, default=default)

    def get_subnet(self, prompt_prefix: str = "") -> str:
        """prompt for a subnete in the account

        Args:
            prompt_prefix (str, optional): _description_. Defaults to "".

        Returns:
            str: _description_
        """
        self._check()

        control_thread = start_progress("subnets")

        uri = "/v1.0/nws/computeservices/subnet/describesubnets"
        data = {
            "owner-id.N": self._account_uuid,
            "Nvl-NextToken": 0,
            "Nvl-MaxResults": -1,
        }
        res = self._controller.cmp_get(uri, data=data)
        control_thread.stop()
        res = dict_get(res, "DescribeSubnetsResponse")
        instances: List[Dict] = res.get("subnetSet") # type: ignore
        subnet_names: List[str] = [instance.get("nvl-name") for instance in instances] # type: ignore
        subnet_names.sort()

        subnet = self.get_word(prompt_prefix=prompt_prefix, opts=subnet_names)
        return subnet

    def get_security_group(self, prompt_prefix: str = "") -> str:
        """prompt for a security group in the account

        Args:
            prompt_prefix (str, optional): _description_. Defaults to "".

        Returns:
            str: _description_
        """
        self._check()
        control_thread = start_progress("security groups")

        uri = "/v1.0/nws/computeservices/securitygroup/describesecuritygroups"
        data = {
            "owner-id.N": self._account_uuid,
            "NextToken": 0,
            "MaxResults": -1,
        }
        res = self._controller.cmp_get(uri, data=data)
        control_thread.stop()
        res = dict_get(res, "DescribeSecurityGroupsResponse")
        security_group_info: List[Dict] = res.get("securityGroupInfo") # type: ignore
        securitygroup_names: List[str] = [instance.get("groupName") for instance in security_group_info] # type: ignore
        securitygroup_names.sort()

        vm_securitygroup = self.get_word(opts=securitygroup_names, prompt_prefix=prompt_prefix)
        return vm_securitygroup

    def get_lbaas(self, prompt_prefix: str = "") -> Tuple[str, str]:
        """prompt for a  lbaas service in the account

        Args:
            prompt_prefix (str, optional): _description_. Defaults to "".

        Returns:
            Tuple[str, str]: service name and uuid
        """
        self._check()

        control_thread = start_progress("Lbaas")

        uri = "/v1.0/nws/networkservices/lbaas"
        data = {
            "owner-id.N": self._account_uuid,
            "MaxResults": -1,
        }
        res = self._controller.cmp_get(uri, data=data)
        control_thread.stop()
        res = dict_get(res, "Lbaas")
        lbaass_names = [instance.get("name") for instance in res]
        lbaass_names.sort()
        vm_lbaas_name = self.get_word(lbaass_names, prompt_prefix=prompt_prefix)
        vm_lbaas_uuid = None
        for lbaas in res:
            if lbaas["name"] == vm_lbaas_name:
                vm_lbaas_uuid = lbaas["loadBalancerId"]
                break
        return vm_lbaas_name, vm_lbaas_uuid

    def get_word(
        self,
        opts: List[str],
        prompt_prefix: str = "",
        default: str = "",
    ) -> str:
        """Prompt for a word beetwin options with autocomplitee nd choices

        Args:
            opts (List[str]): list of word to  choose
            prompt_prefix (str): message prompt
            default (str, optional): optional default value

        Returns:
            str: _description_
        """
        completer = WordCompleter(opts, ignore_case=True, match_middle=True)
        validator = CmpValidator(self._controller.app, opts)
        self.session.completer = completer
        PromptUtil.start_completer(self.session)
        word = self.session.prompt(
            f"{prompt_prefix} > ",
            search_ignore_case=True,
            key_bindings=PromptUtil.kb,
            completer=completer,
            validator=validator,
            default=default,
        )
        return word

    def get_filename(self, prompt_prefix: str = "", default: str = "", patterns: Optional[List[str]] = None) -> str:
        """Prompt for an aexisating file name helped by completer

        Args:
            prompt_prefix (str, optional): string tom prompt . Defaults to "".
            default (str, optional): default value. Defaults to "".
            patterns (Optional[List[str]], optional): estension to look for eg ["*.yamlk"] . Defaults to None.

        Returns:
            str: the file name
        """
        if patterns is None:
            patterns = ["*.*"]
        self.session.completer = RecursiveFilePatternCompleter(patterns=patterns)
        PromptUtil.start_completer(self.session)
        return self.session.prompt(f"{prompt_prefix} > ", validator=self.file_validator, default=default)

    def get_ipv4(self, prompt_prefix: str = "", default: str = "") -> str:
        """prompt for an IPV$ string

        Args:
            prompt_prefix (str, optional): _description_. Defaults to "".
            default (str, optional): _description_. Defaults to "".

        Returns:
            str: the validated IP
        """
        self.session.completer = None
        self.session.validator = None
        return self.session.prompt(f"{prompt_prefix} ip > ", validator=IPv4Validator(), default=default)

    def get_alfanum(
        self, prompt_prefix: str = "", default: str = "", not_in: Optional[List[str]] = None, maxlen: int = 50
    ) -> str:
        """prompt for a alfanumeric word

        Args:
            prompt_prefix (str, optional): _description_. Defaults to "".
            default (str, optional): _description_. Defaults to "".
            not_in (Optional[List[str]], optional): _description_. Defaults to None.
            maxlen (int, optional): _description_. Defaults to 50.

        Returns:
            str: the validated string
        """
        self.session.completer = None
        self.session.validator = None
        return self.session.prompt(f"{prompt_prefix}  > ", validator=AlNumValidator(maxlen, not_in), default=default)

    def get_name(
        self, prompt_prefix: str = "", default: str = "", not_in: Optional[List[str]] = None, maxlen: int = 50
    ) -> str:
        """Prompt for a valide name that may be used as a DNS label

        Args:
            prompt_prefix (str, optional): _description_. Defaults to "".
            default (str, optional): _description_. Defaults to "".
            not_in (Optional[List[str]], optional): _description_. Defaults to None.
            maxlen (int, optional): _description_. Defaults to 50.

        Returns:
            str: the validated name
        """
        self.session.completer = None
        self.session.validator = None
        return self.session.prompt(f"{prompt_prefix}  > ", validator=self.labelvalidator, default=default)

    def get_number(self, prompt_prefix: str = "", default: str = "") -> str:
        """prompt for a numeric string

        Args:
            prompt_prefix (str, optional): _description_. Defaults to "".
            default (str, optional): _description_. Defaults to "".

        Returns:
            str: _description_
        """
        self.session.completer = None
        self.session.validator = None
        return self.session.prompt(f"{prompt_prefix}  > ", validator=self.digitvalidator, default=default)

    def get_ipv4_cidr_list(self, prompt_prefix: str = "", default: str = ""):
        """prompt for a list of IPV4 or CIDR delimnited by comma

        Args:
            prompt_prefix (str, optional): _description_. Defaults to "".
            default (str, optional): _description_. Defaults to "".

        Returns:
            _type_: _description_
        """
        self.session.completer = None
        self.session.validator = None
        return self.session.prompt(
            f"{prompt_prefix} {_('(comma separated IPV4 or CIDR)')} > ",
            validator=self.ipv4listvalidator,
            default=default,
        )

    def get_fqdn(self, prompt_prefix: str = "", default: str = ""):
        """prompt for a valid fqdn

        Args:
            prompt_prefix (str, optional): _description_. Defaults to "".
            default (str, optional): _description_. Defaults to "".

        Returns:
            _type_: _description_
        """
        self.session.completer = None
        self.session.validator = None
        return self.session.prompt(f"{prompt_prefix} fqdn > ", validator=self.fqdnvalidator, default=default)

    def get_vm(self, prompt_prefix) -> Tuple[str, str, dict]:
        """prompt for an existing vm in the account

        Args:
            prompt_prefix (_type_): _description_

        Returns:
            Tuple[str, str, dict]: service name, uuid, and descriptio dict
        """
        if self._account_uuid is None:
            self._account, self._account_uuid = self.get_account(prompt_prefix=prompt_prefix)

        control_thread = start_progress("vms")

        uri = "/v2.0/nws/computeservices/instance/describeinstances"
        data = {
            "owner-id.N": self._account_uuid,
            "MaxResults": -1,
        }
        res = self._controller.cmp_get(uri, data=data)
        control_thread.stop()
        # import pprint
        # pprint.pprint(res)
        instances = dict_get(res, "DescribeInstancesResponse.reservationSet.0.instancesSet", default=[])
        names = [instance.get("nvl-name") for instance in instances]
        names.sort()

        completer = WordCompleter(names, ignore_case=True, match_middle=True)
        self.session.completer = completer
        PromptUtil.start_completer(self.session)
        curname = self.session.prompt(
            f"{prompt_prefix} vm > ",
            search_ignore_case=True,
            key_bindings=PromptUtil.kb,
            validator=CmpValidator(self._controller.app, names),
        )
        curdict = None
        curuuid = None
        for i in range(len(instances)):
            if instances[i]["nvl-name"] == curname:
                curdict = instances[i]
                curuuid = curdict["instanceId"]
        return curname, curuuid, curdict


class PromptNetaas:
    def get_subnet(controller: BusinessControllerChild, vm_account_uuid, prompt_prefix) -> str:
        p = PromptTool(controller=controller, account="", account_uuid=vm_account_uuid)
        return p.get_subnet()

        # control_thread = start_progress("subnets")
        # uri = "/v1.0/nws/computeservices/subnet/describesubnets"
        # data = {
        #     "owner-id.N": vm_account_uuid,
        #     "Nvl-NextToken": 0,
        #     "Nvl-MaxResults": -1,
        # }
        # res = controller.cmp_get(uri, data=data)
        # control_thread.stop()
        # res = dict_get(res, "DescribeSubnetsResponse")
        # instances = res.get("subnetSet")
        # subnet_names = [instance.get("nvl-name") for instance in instances]
        # subnet_names.sort()
        # subnet_completer = WordCompleter(subnet_names, ignore_case=True, match_middle=True)
        # subnet_session = PromptSession(completer=subnet_completer)
        # PromptUtil.start_completer(subnet_session)
        # vm_subnet = subnet_session.prompt(
        #     "%s subnet > " % prompt_prefix,
        #     search_ignore_case=True,
        #     key_bindings=PromptUtil.kb,
        #     validator=CmpValidator(controller.app, subnet_names),
        # )
        # return vm_subnet

    def get_security_group(controller: BusinessControllerChild, vm_account_uuid, prompt_prefix) -> str:
        p = PromptTool(controller=controller, account="", account_uuid=vm_account_uuid)
        return p.get_security_group()
        # control_thread = start_progress("security groups")
        # uri = "/v1.0/nws/computeservices/securitygroup/describesecuritygroups"
        # data = {
        #     "owner-id.N": vm_account_uuid,
        #     "NextToken": 0,
        #     "MaxResults": -1,
        # }
        # res = controller.cmp_get(uri, data=data)
        # control_thread.stop()
        # res = dict_get(res, "DescribeSecurityGroupsResponse")
        # securityGroupInfo = res.get("securityGroupInfo")
        # securitygroup_names = [instance.get("groupName") for instance in securityGroupInfo]
        # securitygroup_names.sort()
        # securitygroup_completer = WordCompleter(securitygroup_names, ignore_case=True, match_middle=True)
        # securitygroup_session = PromptSession(completer=securitygroup_completer)
        # PromptUtil.start_completer(securitygroup_session)
        # vm_securitygroup = securitygroup_session.prompt(
        #     "%s securitygroup > " % prompt_prefix,
        #     search_ignore_case=True,
        #     key_bindings=PromptUtil.kb,
        #     validator=CmpValidator(controller.app, securitygroup_names),
        # )
        # return vm_securitygroup
