#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict

# This must be done before import cement
from beehive3_cli.beenv import init_beenv
init_beenv()

from beehive3_cli.translate import initialize_translations
initialize_translations()

try:
    import os
    import sys
    from traceback import print_exc, format_exc
    from logging import captureWarnings
    from cement import App, init_defaults
    from cement.core.exc import CaughtSignal
    from beecell.file import read_file
    from beehive3_cli.core.argument import CliArgumentHandler
    from beehive3_cli.core.dynamic_output import DynamicOutputHandler
    from beehive3_cli.core.exc import CliManagerError
    from beehive3_cli.core.json_output import JsonOutputHandler
    from beehive3_cli.core.log import CliLogHandler
    from beehive3_cli.core.tabular_output import TabularOutputHandler
    from beehive3_cli.core.tabular_color_output import TabularColorOutputHandler
    from beehive3_cli.core.yaml_output import YamlOutputHandler
    from beehive3_cli.core.util import ColoredText
    from beehive3_cli.controllers.base import Base
    if TYPE_CHECKING:
        from cement.core.output import OutputHandler
        from cement.ext.ext_configparser import ConfigParserConfigHandler
        from beehive3_cli.core.argument import CliArgumentHandler

    captureWarnings(True)

    CONFIG = init_defaults("beehive", "log.clilog")
    CONFIG["beehive"]["language"] = "it"
    CONFIG["beehive"]["debug"] = False
    CONFIG["beehive"]["default_env"] = "local"
    CONFIG["beehive"]["default_format"] = "text"
    CONFIG["beehive"]["encryption_key"] = ""
    CONFIG["beehive"]["print_curl_request"] = False
    CONFIG["beehive"]["print_curl_request_error"] = False
    CONFIG["beehive"]["environment_config_path"] = ""
    CONFIG["beehive"]["cmp_post_install_path"] = "~"
    CONFIG["beehive"]["cmp_config_path"] = "~"
    CONFIG["beehive"]["colored"] = True
    CONFIG["beehive"]["oauth2_client_path"] = None
    CONFIG["log.clilog"]["additional_loggers"] = []
    CONFIG["log.clilog"]["file"] = "~/beehive3.log"
    CONFIG["log.clilog"]["to_console"] = False
    CONFIG["log.clilog"]["verbose_log"] = False

    def load_configs(app: 'CliManager'):
        app.env = app.config.get("beehive", "default_env")
        app.env = os.environ.get("NIVOLA_CLI_ENV", app.env)
        app.format = app.config.get("beehive", "default_format")
        app.key = app.config.get("beehive", "encryption_key")
        app.curl = bool(app.config.get("beehive", "print_curl_request"))
        app.curl_error = bool(app.config.get("beehive", "print_curl_request_error"))

        app.environment_config_path = app.config.get("beehive", "environment_config_path")

        oauth2_client_path = app.config.get("beehive", "oauth2_client_path")
        if oauth2_client_path is not None:
            try:
                app.oauth2_client = read_file(oauth2_client_path)
            except Exception as exc:
                if app.config.get("log.clilog", "verbose_log"):
                    app.warning(exc)
                app.oauth2_client = None


    class CliManager(App):
        """
        Command line interface manager
        """
        colored_text = ColoredText()
        log: 'CliLogHandler'
        output: 'OutputHandler'
        config: 'ConfigParserConfigHandler'
        env: str
        format: str
        key: str
        curl: bool
        curl_error: bool
        environment_config_path: str
        oauth2_client: Optional[Dict]
        args: 'CliArgumentHandler'

        class Meta: # type: ignore
            label = "beehive3"

            # configuration defaults
            config_defaults = CONFIG

            # call sys.exit() on close
            exit_on_close = True

            # load additional framework extensions
            extensions = [
                "json",
                "yaml",
                "jinja2",
                "beehive3_cli.ext.ext_nivola_simple",
                # "beehive3_cli.ext.ext_nivola",
            ]

            # configuration handler
            config_handler = "yaml"

            # configuration file suffix
            config_file_suffix = ".yml"

            # configuration files
            home = os.environ.get("HOME", "~")
            default_cfg = os.environ.get("BEEHIVE_CFG", f"{home}/.beehive3/config/beehive.yml")

            config_files = [default_cfg]

            core_handler_override_options = {}

            # set the log handler
            log_handler = "clilog"

            # set the output handler
            # output_handler = "tabular_output_handler"
            output_handler = "tabular_color_output_handler"
            format = "colortext"

            argument_handler = "cli_argument_handler"

            template_handler = "jinja2"

            # register handlers
            handlers = [
                Base,
                TabularOutputHandler,
                DynamicOutputHandler,
                JsonOutputHandler,
                YamlOutputHandler,
                CliArgumentHandler,
                CliLogHandler,
                TabularColorOutputHandler,
            ]

            # register hooks
            hooks = [
                ("post_setup", load_configs),
            ]

            # plugin_handler = 'nivola'
            plugin_handler = "nivolasimple"
            plugin_dirs = [os.path.join(os.path.dirname(__file__), "plugins")]

            template_dirs = [os.path.join(os.path.dirname(__file__), "templates")]
            debug_argument_options = None
            quiet_argument_options = None

        def print(self, msg, color="GREEN"):
            if self.config.get("beehive", "colored"):
                msg = self.colored_text.output(msg, color)
            print(msg)

        def warning(self, msg):
            if self.config.get("beehive", "colored"):
                msg = self.colored_text.warning(msg)
            else:
                msg = f"WARNING : {msg}"
            print(msg)

        def error(self, msg):
            if self.config.get("beehive", "colored"):
                msg = self.colored_text.error(msg)
            else:
                msg = f"ERROR : {msg}"
            print(msg)

        def color_error(self, val):
            if self.config.get("beehive", "colored") is True and isinstance(val, str):
                exp = val.lower()
                if exp in ["error", "failure", "ko"]:
                    val = self.colored_text.output(val, "RED")
                elif exp in ["active", "success", "running", "available", "ok"]:
                    val = self.colored_text.output(val, "GREEN")
                elif exp in ["stopped"]:
                    val = self.colored_text.output(val, "GRAY")
                elif exp in ["building"]:
                    val = self.colored_text.output(val, "CYAN")
                elif exp in ["pending"]:
                    val = self.colored_text.output(val, "BLUE")
                elif exp in ["closed"]:
                    val = self.colored_text.output(val, "LYELLOW")
                elif exp in ["deleted"]:
                    val = self.colored_text.output(val, "GRAY")
            return val

        def render(self, data, template=None, out=sys.stdout, handler=None, **kwargs):
            suppress_formatting = False
            if not os.isatty(1):
                # output is piped: no color, no formatting, no truncate
                suppress_formatting = True # for output handler
                self.config["beehive"]["colored"] = "false" # for generic transforms. NB: must be string
                self.pargs.notruncate = True # do not truncate anything
            super().render(data, template, out, handler, suppress_formatting=suppress_formatting, **kwargs)

        def run(self):
            """
            This function wraps everything together (after ``self._setup()`` is
            called) to run the application.

            Returns:
                unknown: The result of the executed controller function if
                a base controller is set and a controller function is called,
                otherwise ``None`` if no controller dispatched or no controller
                function was called.

            """
            try:
                res = super().run()
                return res
            except Exception as exc:
                self.exit_code = 255
                self.log.error(format_exc())
                self.error(exc)
            return None

    def main():
        """
        Command line main
        """
        try:
            with CliManager() as app:
                try:
                    app.run()
                except KeyboardInterrupt:
                    pass

                except AssertionError as e:
                    print(f"AssertionError > {e.args[0]}")
                    app.exit_code = 1

                    if app.debug is True:
                        print_exc()

                except CliManagerError as e:
                    print(f"CliManagerError > {e.args[0]}")
                    app.exit_code = 1

                    if app.debug is True:
                        print_exc()
                except CaughtSignal as e:
                    # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
                    print(f"\n{e}")
                    app.exit_code = 0

        except CaughtSignal as e:
            # Interrupt during plugin setup or earlier
            # avoids printing useless stack trace
            print(f"\n{e}")
            # app is yet defined if here. can't set exit code with app. ...
            # alternatively set it with sys.exit(...)

    if __name__ == "__main__":
        main()

except KeyboardInterrupt as ex:
    pass
