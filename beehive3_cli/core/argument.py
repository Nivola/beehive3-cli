# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from argparse import RawDescriptionHelpFormatter, _ArgumentGroup, _SubParsersAction, Action
from cement.ext.ext_argparse import ArgparseArgumentHandler


class CliHelpFormatter(RawDescriptionHelpFormatter):
    def _metavar_formatter(self, action, default_metavar):
        if action.metavar is not None:
            result = action.metavar
        # elif action.choices is not None:
        #     choice_strs = [str(choice) for choice in action.choices]
        #     print(choice_strs)
        #     result = '{%s}' % ','.join(choice_strs)
        else:
            result = default_metavar

        def format(tuple_size):
            if isinstance(result, tuple):
                return result
            else:
                return (result, ) * tuple_size
        return format


class _CliSubParsersAction(_SubParsersAction):
    class _ChoicesPseudoAction(Action):
        def __init__(self, name, aliases, help):
            metavar = dest = name
            if aliases:
                metavar = aliases[0]
                # metavar += ' (%s)' % ', '.join(aliases)
            sup = super(_CliSubParsersAction._ChoicesPseudoAction, self)
            sup.__init__(option_strings=[], dest=dest, help=help,
                         metavar=metavar)


class ArgumentGroup(_ArgumentGroup):
    def __init__(self, container, title=None, description=None, **kwargs):
        super(ArgumentGroup, self).__init__(container, title=None, description=None, **kwargs)
        self.register('action', 'parsers', _CliSubParsersAction)


class CliArgumentHandler(ArgparseArgumentHandler):
    class Meta:
        label = 'cli_argument_handler'

    def add_argument_group(self, *args, **kwargs):
        group = ArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group

    # def parse_known_args(self, args=None, namespace=None):
    #     if args is None:
    #         # args default to the system args
    #         args = _sys.argv[1:]
    #     else:
    #         # make sure that args are mutable
    #         args = list(args)
    #
    #     # default Namespace built from parser defaults
    #     if namespace is None:
    #         namespace = Namespace()
    #
    #     # add any action defaults that aren't present
    #     for action in self._actions:
    #         if action.dest is not SUPPRESS:
    #             if not hasattr(namespace, action.dest):
    #                 if action.default is not SUPPRESS:
    #                     setattr(namespace, action.dest, action.default)
    #
    #     # add any parser defaults that aren't present
    #     for dest in self._defaults:
    #         if not hasattr(namespace, dest):
    #             setattr(namespace, dest, self._defaults[dest])
    #
    #     # parse the arguments and exit if there are any errors
    #     try:
    #         namespace, args = self._parse_known_args(args, namespace)
    #         if hasattr(namespace, _UNRECOGNIZED_ARGS_ATTR):
    #             args.extend(getattr(namespace, _UNRECOGNIZED_ARGS_ATTR))
    #             delattr(namespace, _UNRECOGNIZED_ARGS_ATTR)
    #         return namespace, args
    #     except ArgumentError:
    #         err = _sys.exc_info()[1]
    #         self.error(str(err))