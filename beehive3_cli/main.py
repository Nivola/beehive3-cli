#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

try:
    import os
    from traceback import print_exc, format_exc
    from logging import captureWarnings
    from cement import App, init_defaults
    from cement.core.exc import CaughtSignal
    from beecell.file import read_file
    from beehive3_cli.core.argument import CliArgumentHandler
    from beehive3_cli.core.exc import CliManagerError
    from beehive3_cli.controllers.base import Base
    from beehive3_cli.core.json_output import JsonOutputHandler
    from beehive3_cli.core.log import CliLogHandler
    from beehive3_cli.core.tabular_output import TabularOutputHandler
    from beehive3_cli.core.tabular_color_output import TabularColorOutputHandler
    from beehive3_cli.core.dynamic_output import DynamicOutputHandler
    from beehive3_cli.core.yaml_output import YamlOutputHandler
    from beehive3_cli.core.util import ColoredText

    from beehive3_cli.core.mixed_output import MixedOutputHandler

    captureWarnings(True)

    CONFIG = init_defaults("beehive", "log.clilog")
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

    def setup_logging(app):
        """Setup loggers

        :param app: cement app
        """
        # app.log.info('ciao')

        # get a list of sections
        s = app.config.get("beehive", "debug")

    def load_configs(app):
        app.env = app.config.get("beehive", "default_env")
        app.format = app.config.get("beehive", "default_format")
        app.key = app.config.get("beehive", "encryption_key")
        app.curl = app.config.get("beehive", "print_curl_request")
        app.curl_error = app.config.get("beehive", "print_curl_request_error")

        app.environment_config_path = app.config.get("beehive", "environment_config_path")

        oauth2_client_path = app.config.get("beehive", "oauth2_client_path")
        if oauth2_client_path is not None:
            try:
                app.oauth2_client = read_file(oauth2_client_path)
            except Exception as ex:
                if app.config.get("log.clilog", "verbose_log"):
                    app.warning(ex)
                app.oauth2_client = None

    class CliManager(App):
        colored_text = ColoredText()

        class Meta:
            label = "beehive3"

            # configuration defaults
            config_defaults = CONFIG

            # call sys.exit() on close
            exit_on_close = True

            # load additional framework extensions
            extensions = [
                "json",
                "yaml",
                "colorlog",
                "jinja2",
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
                MixedOutputHandler,
            ]

            # register hooks
            hooks = [
                ("post_setup", setup_logging),
                ("post_setup", load_configs),
            ]

            plugin_dirs = [os.path.join(os.path.dirname(__file__), "plugins")]

            template_dirs = [os.path.join(os.path.dirname(__file__), "templates")]

        def output(self, msg, color="GREEN"):
            if self.config.get("beehive", "colored") is True:
                msg = self.colored_text.output(msg, color)
            print(msg)

        def print(self, msg, color="GREEN"):
            if self.config.get("beehive", "colored") is True:
                msg = self.colored_text.output(msg, color)
            print(msg)

        def warning(self, msg):
            if self.config.get("beehive", "colored") is True:
                msg = self.colored_text.warning(msg)
            print(msg)

        def error(self, msg):
            if self.config.get("beehive", "colored") is True:
                msg = self.colored_text.error(msg)
            print(msg)

        def color_error(self, val):
            if isinstance(val, str):
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
                res = super(CliManager, self).run()
                return res
            except Exception as ex:
                self.exit_code = 255
                self.log.error(format_exc())
                self.error(ex)

    def main():
        with CliManager() as app:
            try:
                app.run()
            except KeyboardInterrupt:
                pass

            except AssertionError as e:
                print("AssertionError > %s" % e.args[0])
                app.exit_code = 1

                if app.debug is True:
                    print_exc()

            except CliManagerError as e:
                print("CliManagerError > %s" % e.args[0])
                app.exit_code = 1

                if app.debug is True:
                    print_exc()

            except CaughtSignal as e:
                # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
                print("\n%s" % e)
                app.exit_code = 0

    if __name__ == "__main__":
        main()

except KeyboardInterrupt as ex:
    pass
