# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


import os
import sys
from pathlib import Path
import gettext


def setup_translation(lang: str):
    """
    Set up gettext translation for language.

    Args:
        lang (str): language to setup. It can be 'it' or 'en'.
    """
    if lang == "en":
        return gettext
    localepath = Path(__file__).resolve().parents[0].joinpath("locale")
    if localepath.exists() and localepath.joinpath(lang).exists():
        localedir = str(localepath)
        combined = None
        for domain in ['beehive', 'argparse']:
            trans = gettext.translation(domain, localedir=localedir, languages=[lang])
            if combined is None:
                combined = trans
            else:
                combined.add_fallback(trans)
        # Set _ as global
        combined.install()
        return combined
    return gettext


def initialize_translations():
    """
    It performs all the operations needed to have a correct translation.
    """
    language = os.environ.get("NIVOLA_CLI_LANG", "it")
    __translation: gettext.GNUTranslations = setup_translation(language)

    # Monkey patch gettext with our implementation
    gettext.gettext =  __translation.gettext

    # Monkey patch argparse in order to do missing translations
    monkey_patch_argparse()


def _(msg: str) -> str:
    return gettext.gettext(msg)


def monkey_patch_argparse():
    """
    Need to fix argparse.py bugs. Some crucial points has not the gettext '_'.
    """
    # IMPORTANT: Do not move this import to the top of the file.
    # It must be placed here to ensure gettext translations are properly initialized before use.
    from argparse import ArgumentParser, ArgumentError # pylint: disable=import-outside-toplevel

    def translated_error(self, message):
        self.print_usage(sys.stderr)
        translated_prefix = _('error')
        full_message = f'{self.prog}: {translated_prefix}: {message}\n'
        self.exit(2, full_message)

    def translated_format(self):
        if self.argument_name is None:
            _format = '%(message)s'
        else:
            _format = _('argument %(argument_name)s: %(message)s')
        return _format % {"message": self.message, "argument_name": self.argument_name}

    ArgumentParser.error = translated_error
    ArgumentError.__str__ = translated_format
