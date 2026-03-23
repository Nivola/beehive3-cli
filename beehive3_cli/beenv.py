#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte
# a small module to implement behavior like .env using .beenv in home directory


"""Small module to implement .env-like behavior using ~/.beenv."""


import os


_beenv_singleton: dict[str, str] = {}


def init_beenv():
    """initialize  environment.
    It looks for an environment file in ~/.beenv
    if found parse in format
    <KEY>=<VAL>
    then set environem variable <KEY> to value <VAL>
    """
    
    envfile = os.path.join(os.environ.get("HOME", "~"), ".beenv")
    if os.path.isfile(envfile):
        with open(envfile, 'r',  encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line.startswith("#"):
                    kv = line.split("=")
                    if len(kv)==2:
                        key=kv[0].strip()
                        val=kv[1].strip()
                        if len(key)>0 and len(val)>0:
                            _beenv_singleton[key]=val

        for key, val in _beenv_singleton.items():
            os.environ[key]=val


def print_env():
    """print env
    """
    for key, val in _beenv_singleton.items():
        print(f"{key}={val}\n")


def reset_env():
    """truncate environment file
    """
    envfile = os.path.join(os.environ.get("HOME", "~"), ".beenv")
    with open(envfile, 'w', encoding='utf-8'):
        pass


def _update_env():
    """update environment file
    """
    envfile = os.path.join(os.environ.get("HOME", "~"), ".beenv")
    with open(envfile, 'w', encoding='utf-8') as file:
        for key, val in _beenv_singleton.items():
            file.write(f"{key}={val}\n")


def clear_env():
    """remove environment file
    """
    envfile = os.path.join(os.environ.get("HOME", "~"), ".beenv")
    if os.path.isfile(envfile):
        os.remove(envfile)


def unset_beenv(key:str)->None:
    """remove a <KEY>=<VAL> in the application environment
    to be loaded at next execution.

    Args:
        key (str): the variable name
        value (str): the value
    """
    if str(key).strip() in _beenv_singleton:
        _beenv_singleton.pop(str(key).strip())
    _update_env()


def set_beenv(key:str, value:str)->None:
    """add a <KEY>=<VAL> in the application environment
    to be loaded at next execution.

    Args:
        key (str): the variable name
        value (str): the value
    """
    _beenv_singleton[str(key).strip()]=str(value).strip()
    _update_env()
