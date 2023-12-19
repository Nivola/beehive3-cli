# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

import os
import logging
import logging.handlers
from sys import stdout
from socket import gethostname

from cement import Handler
from cement.ext.ext_colorlog import ColorLogHandler
from cement.ext.ext_logging import NullHandler
from cement.utils import fs
from cement.utils.misc import is_true, minimal_logger
from colorlog import ColoredFormatter
from beecell.logger import LoggerHelper


LOG = minimal_logger(__name__)


class CliLogHandler(ColorLogHandler):
    class Meta:
        label = "clilog"

        #: The logging format for the file logger.
        file_format = "%(asctime)s - %(levelname)s - %(name)s.%(funcName)s:%(lineno)d - %(message)s"

        #: The logging format for the consoler logger.
        console_format = "%(levelname)s: %(message)s"

        #: The logging format for both file and console if ``debug==True``.
        debug_format = "%(asctime)s - %(levelname)s - %(name)s.%(funcName)s:%(lineno)d - %(message)s"

        #: Color mapping for each log level
        colors = {
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        }

        #: Default configuration settings.  Will be overridden by the same
        #: settings in any application configuration file under a
        #: ``[log.colorlog]`` block.
        config_defaults = dict(
            file=None,
            level="INFO",
            to_console=True,
            rotate=False,
            max_bytes=512000,
            max_files=4,
            colorize_file_log=True,
            colorize_console_log=False,
        )

        #: Formatter class to use for non-colorized logging (non-tty, file,
        #: etc)
        formatter_class_without_color = logging.Formatter

        #: Formatter class to use for colorized logging
        formatter_class = ColoredFormatter

    def _setup(self, app_obj):
        Handler._setup(self, app_obj)

        if self._meta.namespace is None:
            self._meta.namespace = "%s" % self.app._meta.label

        self.backend = logging.getLogger("cement:app:%s" % self._meta.namespace)

        # setup other loggers
        self.other_backends = []
        loggers = self.app.config.get(self._meta.config_section, "additional_loggers")
        for logger in loggers:
            self.other_backends.append(logging.getLogger(logger))
        self.other_backends.append(logging.getLogger("beecell.paramiko_shell.shell"))

        # hack for application debugging
        if is_true(self.app._meta.debug):
            self.app.config.set(self._meta.config_section, "level", "DEBUG")

        level = self.app.config.get(self._meta.config_section, "level")
        self.set_level(level)

        LOG.debug("logging initialized for '%s' using %s" % (self._meta.namespace, self.__class__.__name__))

    def set_level(self, level):
        """
        Set the log level.  Must be one of the log levels configured in
        self.levels which are
        ``['INFO', 'WARNING', 'ERROR', 'DEBUG', 'FATAL']``.

        :param level: The log level to set.

        """
        self.clear_loggers(self._meta.namespace)
        for namespace in self._meta.clear_loggers:
            self.clear_loggers(namespace)

        level = level.upper()
        if level not in self.levels:
            level = "INFO"
        level = getattr(logging, level.upper())

        self.backend.setLevel(level)

        for logger in self.other_backends:
            logger.setLevel(level)

        # console
        self._setup_console_log()

        # file
        self._setup_file_log()

        # syslog
        self._setup_syslog()

    def _get_console_format(self):
        format = super(ColorLogHandler, self)._get_console_format()
        colorize = self.app.config.get(self._meta.config_section, "colorize_console_log")
        if stdout.isatty() or "CEMENT_TEST" in os.environ:
            if is_true(colorize):
                format = "%(log_color)s" + format
        return format

    def _get_file_format(self):
        format = super(ColorLogHandler, self)._get_file_format()
        colorize = self.app.config.get(self._meta.config_section, "colorize_file_log")
        if is_true(colorize):
            format = "%(log_color)s" + format
        return format

    def _get_console_formatter(self, format):
        colorize = self.app.config.get(self._meta.config_section, "colorize_console_log")
        if stdout.isatty() or "CEMENT_TEST" in os.environ:
            if is_true(colorize):
                formatter = self._meta.formatter_class(format, log_colors=self._meta.colors)
            else:
                formatter = self._meta.formatter_class_without_color(format)
        else:
            klass = self._meta.formatter_class_without_color  # pragma: nocover
            formatter = klass(format)  # pragma: nocover

        return formatter

    def _get_file_formatter(self, format):
        colorize = self.app.config.get(self._meta.config_section, "colorize_file_log")
        if is_true(colorize):
            formatter = self._meta.formatter_class(format, log_colors=self._meta.colors)
        else:
            formatter = self._meta.formatter_class_without_color(format)

        return formatter

    def _setup_file_log(self):
        """Add a file log handler."""

        namespace = self._meta.namespace
        file_path = self.app.config.get(self._meta.config_section, "file")
        rotate = self.app.config.get(self._meta.config_section, "rotate")
        max_bytes = self.app.config.get(self._meta.config_section, "max_bytes")
        max_files = self.app.config.get(self._meta.config_section, "max_files")
        if file_path:
            file_path = fs.abspath(file_path)
            log_dir = os.path.dirname(file_path)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            if rotate:
                from logging.handlers import RotatingFileHandler

                file_handler = RotatingFileHandler(
                    file_path,
                    maxBytes=int(max_bytes),
                    backupCount=int(max_files),
                )
            else:
                from logging import FileHandler

                file_handler = FileHandler(file_path)

            format = self._get_file_format()
            formatter = self._get_file_formatter(format)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(getattr(logging, self.get_level()))
        else:
            file_handler = NullHandler()

        # FIXME: self._clear_loggers() should be preventing this but its not!
        for i in logging.getLogger("cement:app:%s" % namespace).handlers:
            if isinstance(i, file_handler.__class__):  # pragma: nocover
                self.backend.removeHandler(i)  # pragma: nocover

        self.backend.addHandler(file_handler)

        # setup other loggers
        for logger in self.other_backends:
            logger.addHandler(file_handler)

    @staticmethod
    def _setup_syslog():
        """Add syslog handler."""
        logger = logging.getLogger("beecell.paramiko_shell.shell")
        loggers = [logger]
        logging_level = logging.INFO
        syslog_server = gethostname()
        syslog_server = syslog_server.split(".")[0]
        facility = logging.handlers.SysLogHandler.LOG_LOCAL7

        LoggerHelper.syslog_handler(
            loggers,
            logging_level,
            syslog_server,
            facility,
            frmt=None,
            propagate=False,
            syslog_port=514,
        )


def load(app):
    app.handler.register(CliLogHandler)
