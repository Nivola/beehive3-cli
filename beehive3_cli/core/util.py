# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from sys import stdout
from typing import Generator, List, Callable, Tuple, Optional, AbstractSet, TYPE_CHECKING, Set
from uuid import UUID
from re import match
from functools import wraps
from time import time, sleep
from pathlib import Path
from pygments.style import Style
from pygments.token import Token
from cement.utils import fs
from beecell.simple import read_file
from beehive3_cli.translate import _
from beehive3_cli.core.exc import CliManagerError
if TYPE_CHECKING:
    from beehive3_cli.main import CliManager

class TreeStyle(Style):
    """
    TreeStyle
    """

    default_style = ""
    styles = {
        # Token.Text.Whitespace: "#fff",    # bianco
        # Token.Name: "bold #ffcc66",       # giallo
        # Token.Literal.String: "#fff",     # bianco
        # Token.Literal.Number: "#0099ff",  # blu
        # Token.Operator: "#ff3300",        # rosso
        Token.Text.Whitespace: "#fff",
        Token.Name: "bold #ffcc66",
        Token.Literal.String: "#33aa00",
        Token.Literal.Number: "#0099ff",
        Token.Operator: "#ff3300",
    }


def duration(precision=3):
    """Use this decorator to get method duration

    :param precision: result precision
    Example::

        @duration()
        def fn(*args, **kwargs):
            ....
    """

    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            # get start time
            start = time()
            ret = fn(*args, **kwargs)
            elapsed = round(time() - start, precision)
            print(f"{fn.__module__}.{fn.__name__} duration: {elapsed}")
            return ret

        return decorated

    return wrapper


def load_config(file_name, secret: Optional[str]=None):
    """load config from file"""
    data = read_file(file_name, secret=secret)
    return data


def load_environment_config(app: 'CliManager', env=None):
    """load environment config"""
    if env is None:
        env = app.env
    file = fs.join_exists(app.environment_config_path, f"{env}.yml")

    if file[1] is True:
        env_configs = load_config(file[0], secret=app.key)
    else:
        raise CliManagerError(_("No configuration file found for the environment specified"))

    if env_configs is None or env_configs.get("cmp", None) is None:
        raise CliManagerError(_("No configuration file found for the environment specified"))

    return env_configs


def list_environments(app: 'CliManager'):
    """list environments"""
    envs = []
    # print("environment_config_path: %s" % app.environment_config_path)
    p = Path(app.environment_config_path)
    for file in sorted(Path(p.expanduser()).glob("*.yml")):
        # print(file.name)
        envs.append((file.name[:-4]))
    return envs


def get_orchestrator_config(app: 'CliManager', orch: str, label: str) -> dict:
    """
    return orchestrator configuration
    - orch: orchestrator type e.g. ontap, zabbix, vsphere
    - label: orchestrator label e.g. podto1
    """
    config = load_environment_config(app)
    orchestrators = config.get("orchestrators", {}).get(orch, {})
    if label not in orchestrators:
        msg = _("Valid labels are: ") + ', '.join(orchestrators.keys())
        raise CliManagerError(msg)
    return orchestrators.get(label)


class ColoredText:
    """
    utility functions operating mainly on text
    """

    GRAY = 2
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    PURPLE = 35
    CYAN = 36
    WHITE = 37

    LBLACK = 90
    LRED = 91
    LGREEN = 92
    LYELLOW = 93
    LBLUE = 94
    LPURPLE = 95
    LCYAN = 96
    LWHITE = 97

    FAIL = 91

    BOLD = 7
    BOLD_2 = 1
    UNDERLINE = 4
    UNDERLINE2 = 21
    CROSSED = 9
    ITALIC = 3
    BLINK = 5
    RESET = 0

    styles = (
        2,
        3,
        4,
        5,
        7,
        9,
        21,
        30,
        31,
        32,
        33,
        34,
        35,
        36,
        37,
        90,
        91,
        91,
        92,
        93,
        94,
        95,
        96,
        97,
    )

    def escape(self, style):
        return f"\33[{style}m"

    def output(self, data, color):
        return self.escape(getattr(self, color)) + data + self.escape(self.RESET)

    def warning(self, data):
        return self.format(_("WARNING: ") + str(data), self.YELLOW)

    def error(self, data):
        return self.format(_("ERROR: ") + str(data), self.RED)

    def format(self, data, style):
        return self.escape(style) + data + self.escape(self.RESET)

    def blue(self, data):
        return self.format(data, self.LBLUE)

    def red(self, data):
        return self.format(data, self.LRED)

    def bold(self, data):
        return self.format(data, self.BOLD)

    def bold_2(self, data):
        return self.format(data, self.BOLD_2)

    def gray(self, data):
        return self.format(data, self.GRAY)

    def green(self, data):
        return self.format(data, self.GREEN)

    def white(self, data):
        return self.format(data, self.WHITE)

    def yellow(self, data):
        return self.format(data, self.YELLOW)

    def underline(self, data):
        return self.format(data, self.UNDERLINE)

    @staticmethod
    def cur_up(n: int) -> str:
        """move cursor up n line"""
        return f"\33[{n}A"

    @staticmethod
    def cur_down(n: int) -> str:
        """move cursor down n line"""
        return f"\33[{n}B"

    @staticmethod
    def cur_right(n: int) -> str:
        """move cursor right n cols"""
        return f"\33[{n}C"

    @staticmethod
    def cur_left(n: int) -> str:
        """move cursor left n cols"""
        return f"\33[{n}D"

    @staticmethod
    def cur_at_coll(n: int) -> str:
        """move cursor n collumn"""
        return f"\33[{n}G"

    @staticmethod
    def clear_line() -> str:
        """erase line and move at 0 col"""
        return "\33[2K\33[0G"

    @staticmethod
    def clear_to_end() -> str:
        """erase to end line do not move cursor"""
        return "\33[0K"

    @staticmethod
    def clear_from_start() -> str:
        """erase from start tu cursor and move at 0 col"""
        return "\33[1K\33[0G"

    def prompt(
        self, question: str, style: Optional[int] = None,
        scroll: bool = False, case_sensitive = False
    ) -> str:
        """
        Display prompt.
        """
        ret = ""
        if style in self.styles:
            ret = input(self.clear_line() + self.format(question, style))
        else:
            ret = input(self.clear_line() + question)
        if not scroll:
            stdout.write(self.cur_up(1))
        if not case_sensitive:
            ret = ret.lower()
        return ret

    def prompt_choice(
        self,
        prompt_msg=_("Are you sure?"),
        options: Optional[List[str]]=None,
        scroll: bool = True,
        loop_until_valid = True,
        except_on_invalid = False,
        case_sensitive = False,
    ) -> Optional[str]:
        """
        Ask user to choose among a list of options.

        :param prompt_msg: the prompt message
        :param options: the options to choose among. defaults to ["y", "n"]
        :param loop_until_valid: continue until a valid option is chosen. (default=True)
        :param except_on_invalid: raise exception if invalid value is received (default=False)
        :param case_sensitive: whether option matching should be case sensitive (default=False)
        :return: valid chosen option or None or CliManagerError
        """
        if options is None:
            options = ["y", "n"]

        while True:
            msg = prompt_msg + " [" + str("/".join(options)) + "] "
            choice = self.prompt(question=msg, style=self.YELLOW, scroll=scroll,case_sensitive=case_sensitive)
            if choice in options:
                return choice
            if loop_until_valid:
                continue
            if except_on_invalid:
                msg = _("Invalid choice: ") + f"{choice}" + "."
                raise CliManagerError(msg)
            return None


class CmpUtils:
    """
    collection of utility functions for tasks and other cmp objects
    """

    DEFAULT_API_REQUEST_TIMEOUT = 120
    DEFAULT_CHECK_DELTA = 2

    DEFAULT_TASK_TIMEOUT = 600
    DEFAULT_TASK_EXIT_STATUSES: Set[str] = {"SUCCESS", "FAILURE", "TIMEOUT"}
    DEFAULT_TASK_KEYS: Set[str] = {"jobid", "taskid", "nvl_TaskId"}

    DEFAULT_INSTANCE_TIMEOUT = 600
    DEFAULT_INSTANCE_EXIT_STATUSES: Set[str] = {"ACTIVE", "ERROR", "DELETED"}

    @staticmethod
    def get_task_id_from(from_var, key_path: Optional[List[str]] = None, keys: Optional[AbstractSet[str]] = None):
        """
        get task id from api response, if present. None if a string can't be found.
        key_path = list of keys following hierarchy inside dict
        """
        task_id = from_var

        if key_path:
            for key in key_path:
                if isinstance(task_id, dict):
                    task_id = task_id.get(key, None)
                else:
                    return None

        if keys:
            if isinstance(task_id, dict):
                for key in keys:
                    if key in task_id:
                        task_id = task_id.get(key)
                        break

        if isinstance(task_id, dict):
            task_id = task_id.get("nvl-activeTask", None)

        if task_id is not None and CmpUtils.is_valid_uuid(task_id):
            return task_id

        return None

    @staticmethod
    def _wait_item(
        item_id: str,
        get_item_status_function: Callable[[str], str],
        output,
        exit_statuses: AbstractSet[str],
        delta: int,
        max_time: int,
    ) -> Tuple[str, str]:
        """Wait task
        :param item_id: item id
        :param get_item_status_function: function to fetch status
        :param output: whether to print animation
        :param exit_statuses: set of any statuses for which to stop checking
        :param delta: polling interval [default=2]
        :param max_time: max check time [default=600]
        :return: final status and elapsed time
        """
        elapsed = 0
        status = None
        start_time = time()
        animation = rotating_bar(start_time)
        while True:
            status = get_item_status_function(item_id)
            if status in exit_statuses:
                break

            if elapsed > max_time:
                status = "TIMEOUT"
                break

            if output:
                stdout.write(next(animation))
                stdout.flush()

            sleep(delta)
            elapsed += delta
        if output:
            stoprotation()
        elapsed_real = f"{(time()-start_time):.2f}"
        return (status, elapsed_real)

    @staticmethod
    def wait_instance(
        instance_id: str,
        get_status_function: Callable[[str], str],
        output=True,
        delta: int = DEFAULT_CHECK_DELTA,
        max_time: int = DEFAULT_INSTANCE_TIMEOUT,
    ):
        """Wait instance
        :param instance_id: instance id
        :param get_status_function: function to fetch status
        :param output: whether to print animation
        :param delta: polling interval [default=2]
        :param max_time: max task time [default=600]
        :return: final status and elapsed time
        """
        return CmpUtils._wait_item(
            instance_id, get_status_function, output, CmpUtils.DEFAULT_INSTANCE_EXIT_STATUSES, delta, max_time
        )

    @staticmethod
    def wait_task(
        task_id: str,
        get_task_status_function: Callable[[str], str],
        output=True,
        delta: int = DEFAULT_CHECK_DELTA,
        max_time: int = DEFAULT_TASK_TIMEOUT,
        exit_statuses: Optional[AbstractSet[str]] = None,
    ) -> Tuple[str, str]:
        """Wait task
        :param task_id: task id
        :param get_item_status_function: function to fetch status
        :param output: whether to print animation
        :param delta: polling interval [default=2]
        :param max_time: max task time [default=600]
        :param exit_statuses: set of any statuses for which to stop checking
                            [default= {"SUCCESS","FAILURE","TIMEOUT"}]
        :return: final status and elapsed time
        """
        if exit_statuses is None:
            exit_statuses = CmpUtils.DEFAULT_TASK_EXIT_STATUSES

        status, elapsed_real = CmpUtils._wait_item(
            task_id, get_task_status_function, output, exit_statuses, delta, max_time
        )
        return (status, elapsed_real)

    @staticmethod
    def is_valid_uuid(val):
        """
        check if val is valid uuid
        """
        try:
            UUID(str(val))
            return True
        except ValueError:
            return False

    @staticmethod
    def is_valid_id(val):
        """
        check if val is valid db id
        """
        if match(r"^[1-9]\d*$", str(val)):
            return True
        return False


def stoprotation():
    """ """
    stdout.write(ColoredText.cur_right(10) + "\n\n")
    stdout.flush()



def rotating_bar(start_time=None) -> Generator[str, None, None]:
    """
    rotating_bar
    """
    if start_time:
        st_time = start_time
    else:
        st_time = time()
    rotobar = ("-", "\\", "|", "/")
    len_rotobar = len(rotobar)
    len_message = 14  # two spaces + ljust 7 + unita misura + rotobar item
    i = 0
    while True:
        sec = time() - st_time
        if sec < 60:
            pre = f"{sec:.2f} sec"
        else:
            sec = int(sec)
            minutes = int(sec / 60)
            sec = sec % 60
            pre = f"{minutes}:{sec:02} min"
        pre = "  " + pre.ljust(11, " ")
        yield pre + rotobar[i] + f"\33[{len_message}D"
        i += 1
        i %= len_rotobar
