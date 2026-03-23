# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from argparse import (
    RawDescriptionHelpFormatter,
    _ArgumentGroup,
    _SubParsersAction,
    Action,
)
from cement.ext.ext_argparse import ArgparseArgumentHandler
from beehive3_cli.translate import _


class CliHelpFormatter(RawDescriptionHelpFormatter):
    """
    Custom help formatter that fix missing translations.
    """

    def _metavar_formatter(self, action, default_metavar):
        """
        Return a function that generates the metavar tuple used in help output.

        :param action: The argparse action object.
        :param default_metavar: The default metavar string to use if none is set.
        :return
        """
        def cli_format(tuple_size):
            result = action.metavar if action.metavar is not None else default_metavar
            if isinstance(result, tuple):
                return result
            return (result,) * tuple_size

        return cli_format


class _CliSubParsersAction(_SubParsersAction):
    class _ChoicesPseudoAction(Action):
        def __init__(self, name, aliases, help_c):
            metavar = aliases[0] if aliases else name
            super().__init__(option_strings=[], dest=name, help=help_c, metavar=metavar)


class _CliArgumentGroup(_ArgumentGroup):
    def __init__(self, container, title=None, description=None, **kwargs):
        super().__init__(container, title=None, description=None, **kwargs)
        self.register("action", "parsers", _CliSubParsersAction)


class CliArgumentHandler(ArgparseArgumentHandler):
    """
    Custom Cement argument handler that adds gettext translation support
    for argument strings such as help messages, usage, and subparser titles.

    This handler extends Cement's ArgparseArgumentHandler to automatically
    translate CLI text using gettext, allowing localized command-line interfaces.

    REGARDS: _CliArgumentGroup and action are custom.
    """

    class Meta: # type: ignore
        label = "cli_argument_handler"
        formatter_class = CliHelpFormatter

    def add_argument_group(self, *args, **kwargs):
        """
        Add custom argument group.

        :param args: Positional arguments passed to ArgumentGroup.
        :param kwargs: Keyword arguments passed to ArgumentGroup.
        :return: An instance of the localized ArgumentGroup.
        """
        group = _CliArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group

    def add_subparsers(self, **kwargs):
        """
        Adds subparsers to the argument parser with gettext translation support.

        This method wraps the original `add_subparsers()` method to automatically
        translate all string keyword arguments using gettext, enabling
        internationalization support for Cement CLI applications.

        :param kwargs: Keyword arguments passed to `add_subparsers()`.
                       All string values are passed through `_()` for translation.
        :return: The object returned by the base class's `add_subparsers()`.
        """
        translated_kwargs = {
            k: _(v) if v is not None and isinstance(v, str) else v
            for k, v in kwargs.items()
        }
        return super().add_subparsers(**translated_kwargs) # type: ignore

    def error(self, message):
        translated_prefix = _('error')
        app = self.app
        # Start from root parser, use this if something goes wrong
        parser = self
        if app is not None:
            args = self.app.argv

            try:
                # Traverse into subparsers to find the deepest valid parser
                while True:
                    subparser_action = next(
                        (action for action in parser._actions if isinstance(action, _SubParsersAction)),
                        None
                    )
                    if not subparser_action:
                        break

                    for i, arg in enumerate(args):
                        if arg in subparser_action.choices:
                            parser = subparser_action.choices[arg]
                            args = args[i + 1:]  # Continue with remaining args
                            break
                    else:
                        break
            except Exception:
                parser = self  # Fallback

        # Show error message with correct parser name
        full_message = f'{parser.prog}: {translated_prefix}: {message}\n'
        parser._print_message(full_message + '\n')

        # Show help for the most relevant parser
        parser.print_help()
        self.exit(2, "\n")
