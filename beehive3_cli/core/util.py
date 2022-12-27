# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte
from functools import wraps
from time import time

from beecell.simple import read_file
from beehive3_cli.core.exc import CliManagerError
from cement.utils import fs
from pathlib import Path
from pygments.style import Style
from pygments.token import Token

class TreeStyle(Style):
    default_style = ''
    styles = {
        Token.Text.Whitespace: '#fff',
        Token.Name: 'bold #ffcc66',
        Token.Literal.String: '#fff',
        Token.Literal.Number: '#0099ff',
        Token.Operator: '#ff3300'
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
            print('%s.%s duration: %s' % (fn.__module__, fn.__name__, elapsed))
            return ret
        return decorated
    return wrapper


def load_config(file_name):
    data = read_file(file_name)
    return data


def load_environment_config(app, env=None):
    if env is None:
        env = app.env
    file = fs.join_exists(app.environment_config_path, '%s.yml' % env)

    if file[1] is True:
        env_configs = load_config(file[0])
    else:
        raise CliManagerError('No configuration file found for the environment specified')
    if env_configs is None or env_configs.get('cmp', None) is None:
        raise CliManagerError('No configuration file found for the environment specified')

    return env_configs


def list_environments(app):
    envs = []
    p = Path(app.environment_config_path)
    for file in sorted(Path(p.expanduser()).glob('*.yml')):
        envs.append((file.name[:-4]))
    return envs


class ColoredText:
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
    UNDERLINE = 4
    UNDERLINE2 = 21
    CROSSED = 9
    ITALIC = 3
    BLINK = 5
    RESET = 0

    def escape(self, style):
        return '\33[%sm' % style

    def output(self, data, color):
        return self.escape(getattr(self, color)) + data + self.escape(self.RESET)

    def error(self, data):
        return self.format('ERROR : ' + str(data), self.LRED)

    def format(self, data, style):
        return self.escape(style) + data + self.escape(self.RESET)

    def blue(self, data):
        return self.format(data, self.LBLUE)

    def red(self, data):
        return self.format(data, self.LRED)

    def bold(self, data):
        return self.format(data, self.BOLD)

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
