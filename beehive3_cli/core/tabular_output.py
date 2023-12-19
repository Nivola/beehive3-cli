# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from cement.core.output import OutputHandler
from tabulate import tabulate
from beecell.simple import truncate
from beehive3_cli.core.util import ColoredText


class TabularOutputHandler(OutputHandler):
    c = ColoredText()

    class Meta:
        label = "tabular_output_handler"

    def _multi_get(self, data, key, separator="."):
        keys = key.split(separator)
        res = data
        for k in keys:
            if isinstance(res, list):
                try:
                    res = res[int(k)]
                except:
                    res = {}
            else:
                if res is not None:
                    res = res.get(k, {})
        # if isinstance(res, list):
        #     res = res
        if res is None or res == {}:
            res = "-"

        return res

    def _tabularprint(
        self,
        data,
        table_style,
        headers=None,
        other_headers=None,
        fields=None,
        maxsize=20,
        separator=".",
        transform=None,
        print_header=True,
        showindex="never",
    ):
        if data is None:
            data = "-"
        if not isinstance(data, list):
            values = [data]
        else:
            values = data

        # get additional fields from external parameters
        new_fields = []
        if getattr(self.app.pargs, "afields", None) is not None:
            new_fields = self.app.pargs.afields.split(",")

        # get alternative fields from external parameters
        elif getattr(self.app.pargs, "fields", None) is not None:
            alt_fields = self.app.pargs.fields.split(",")
            headers = alt_fields
            fields = alt_fields

        if headers is not None:
            headers.extend(new_fields)

            if other_headers is not None:
                headers.extend(other_headers)

        table = []
        if fields is None:
            fields = headers
        else:
            fields.extend(new_fields)

        for item in values:
            raw = []
            if isinstance(item, dict):
                for key in fields:
                    val = self._multi_get(item, key, separator=separator)
                    raw.append(val)
            else:
                raw.append(item)

            base_transform = {
                "base_state": self.app.color_error,
                "state": self.app.color_error,
                "status": self.app.color_error,
            }
            if transform is None:
                transform = base_transform
            else:
                base_transform.update(transform)
                transform = base_transform

            # apply transform
            for k, func in transform.items():
                try:
                    raw_item = fields.index(k)
                    raw[raw_item] = func(raw[raw_item])
                except ValueError:
                    pass

            if getattr(self.app.pargs, "notruncate", False) is False:
                raw = map(lambda x: truncate(x, maxsize, replace_new_line=False), raw)

            table.append(raw)

        if print_header is True:
            if table_style == "plain":
                headers = [self.c.gray(h) for h in headers]
            print(tabulate(table, headers=headers, tablefmt=table_style, showindex=showindex))
        else:
            print(tabulate(table, tablefmt=table_style, showindex=showindex))

    def render(self, data, *args, **kwargs):
        """Render the ``data`` dict into output in some fashion.  This function
        must accept both ``*args`` and ``**kwargs`` to allow an application to
        mix output handlers that support different features.

        :param data: data to print
        :param other_headers:
        :param headers: list of headers to print with tabular format
        :param key: if set use data from data.get(key)
        :param fields: list of fields key used to print data with tabular format
        :param details: if True and format tabular print a vertical table where first column is the key and second
            column is the value
        :param maxsize: max field value length [default=50, 200 with details=True]
        :param separator: key separator used when parsing key [default=.]
        :param format: format used when print [default=text]
        :param table_style: table style used when format is tabular [defualt=simple]
        :param transform: dict with function to apply to columns set in headers [default={}]
        :param print_header: if True print table header [default=True]
        :param manage_data: custom function used to manage data and extract sections [optional]
        :param showindex: use never [default] to suppress row index. Use always to show row index
        :return: None

        **manage_data**::

            def manage_data(data):
                sections = [
                    {
                        'title': 'monitor',
                        'headers': ['id', 'name', 'interval', 'timeout', 'maxRetries', 'type'],
                        'fields': ['monitorId', 'name', 'interval', 'timeout', 'maxRetries', 'type']
                    },
                ]

                return data, sections
        """
        other_headers = kwargs.get("other_headers", [])
        headers = kwargs.get("headers", None)
        key = kwargs.get("key", None)
        fields = kwargs.get("fields", None)
        details = kwargs.get("details", False)
        maxsize = kwargs.get("maxsize", 50)
        key_separator = kwargs.get("separator", ".")
        table_style = kwargs.get("table_style", "plain")
        transform = kwargs.get("transform", {})
        print_header = kwargs.get("print_header", True)
        manage_data = kwargs.get("manage_data", None)
        showindex = kwargs.get("showindex", "never")

        if data is None:
            self.app.error("data is undefined")

        orig_data = data

        if data is not None and key is not None:
            data = data[key]
        elif isinstance(data, dict) and data.get("msg", None) is not None:
            msg = data.get("msg")
            if transform.get("msg", None) is not None:
                try:
                    msg = transform.get("msg")(msg)
                except ValueError:
                    pass
            print(msg)
            return

        sections = []

        # # check if get by id
        # if getattr(self.app.pargs, 'id', None) is not None:
        #     details = True
        #     if isinstance(data, list):
        #         data = data[0]

        # convert input data for query with one raw
        if details is True:
            resp = []

            # manage data
            if manage_data is not None:
                data, sections = manage_data(data)

            maxsize = 500

            def __format_table_data(k, v):
                if isinstance(v, list):
                    i = 0
                    for n in v:
                        __format_table_data("%s.%s" % (k, i), n)
                        i += 1
                elif isinstance(v, dict):
                    for k1, v1 in v.items():
                        __format_table_data("%s.%s" % (k, k1), v1)
                else:
                    # if isinstance(v, str):
                    #     v = v

                    value = truncate(v, size=maxsize, replace_new_line=False)
                    key = k
                    resp.append({"attrib": self.c.gray(key), "value": value})

            if data is not None:
                for k, v in data.items():
                    __format_table_data(k, v)
            else:
                self.app.error("data is None!")

            data = resp
            headers = ["attrib", "value"]
            print_header = False
            table_style = "plain"

        if isinstance(data, dict) or isinstance(data, list):
            if orig_data is not None and "page" in orig_data:
                print("Page: %s" % orig_data["page"])
                print("Count: %s" % orig_data["count"])
                print("Total: %s" % orig_data["total"])
                print(
                    "Order: %s %s"
                    % (
                        orig_data.get("sort").get("field"),
                        orig_data.get("sort").get("order"),
                    )
                )
                print("")
            self._tabularprint(
                data,
                table_style,
                other_headers=other_headers,
                headers=headers,
                fields=fields,
                maxsize=maxsize,
                separator=key_separator,
                transform=transform,
                print_header=print_header,
                showindex=showindex,
            )

            fn = getattr(ColoredText(), "underline")
            for section in sections:
                print("\n" + fn(section.get("title")))
                self._tabularprint(
                    section.get("value"),
                    table_style,
                    headers=section.get("headers"),
                    fields=section.get("fields"),
                    maxsize=maxsize,
                )
