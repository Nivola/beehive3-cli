# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from cement.core.output import OutputHandler
from beehive3_cli.core.util import ColoredText


class DynamicOutputHandler(OutputHandler):
    c = ColoredText()

    class Meta:
        label = "dynamic_output_handler"

        default_template = "{:10} {:10}"

    # def __set_template(self, template):
    #     """set line template
    #
    #     :param template: line template. Ex. '{:10} {:50} {:6} {:35} {:8} {:>11}'
    #     """
    #     # self.line_tmpl = '%-10s %-50s %6s %-35s %-8s %8s'
    #     self.line_template = '{:10} {:50} {:6} {:35} {:8} {:>11}'
    #     # self.separator = self.line_tmpl % (get_line(10), get_line(50), get_line(6), get_line(35), get_line(8),
    #     #                                    get_line(8))

    def __create_separator(self):
        pass

    def __print_headers(self, headers):
        """print header

        :param header: tupla like ('engine', 'host', 'port', 'action', 'status', 'elapsed')
        :return:
        """
        raw = self.template.format(*headers)
        print(raw)
        self.__create_separator()

    def __print_raw(self, data):
        # if data[4] is True:
        #     data[4] = self.app.colored_text.output(bool2str(data[4]), 'GREEN')
        # else:
        #     data[4] = self.app.colored_text.output(bool2str(data[4]), 'RED')
        raw = self.template.format(*data)
        print(raw)

    def render(self, data, *args, **kwargs):
        """Render the ``data`` dict into output in some fashion.  This function
        must accept both ``*args`` and ``**kwargs`` to allow an application to
        mix output handlers that support different features.

        :param data: data to print
        :param template: line template to use during rendering
        :param headers: list of headers to print with tabular format [optional]
        :param data: single raw data to print
        """
        self.template = kwargs.get("template", self._meta.default_template)
        headers = kwargs.get("headers", None)
        format = kwargs.get("format", lambda x: x)

        if headers is not None:
            self.__print_headers(headers)

        if data is not None:
            data = format(data)
            self.__print_raw(data)
