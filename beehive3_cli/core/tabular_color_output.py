# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from cement.core.output import OutputHandler
from tabulate import tabulate
from beecell.simple import truncate
from beehive3_cli.core.util import ColoredText


class TabularColorOutputHandler(OutputHandler):
    c = ColoredText()

    class Meta:
        label = "tabular_color_output_handler"

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
        # else:
        #     print("data: %s" % data)

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

            # base_transform = {
            #     "base_state": self.app.color_error,
            #     "state": self.app.color_error,
            #     "status": self.app.color_error,
            # }
            # if transform is None:
            #     transform = base_transform
            # else:
            #     base_transform.update(transform)
            #     transform = base_transform

            # apply transform
            # print("transform: %s" % transform)
            for k, func in transform.items():
                try:
                    raw_item = fields.index(k)
                    # print("raw_item: %s" % raw_item)
                    # print("raw: %s" % raw)

                    raw[raw_item] = func(raw[raw_item])
                except ValueError:
                    pass

            # if getattr(self.app.pargs, "notruncate", False) is False:
            #     raw = map(lambda x: truncate(x, maxsize, replace_new_line=False), raw)

            table.append(raw)

        if print_header is True:
            if table_style == "plain":
                headers = [self.c.gray(h) for h in headers]
            print(tabulate(table, headers=headers, tablefmt=table_style, showindex=showindex))
        else:
            print(tabulate(table, tablefmt=table_style, showindex=showindex))

    def color_even(self, transform, item, maxsize, parent_item_key: str = ""):
        func = lambda a: self.c.yellow(a)
        self.color_item(transform, item, maxsize, func, parent_item_key)

    def color_odd(self, transform, item, maxsize, parent_item_key: str = ""):
        # func = lambda a: self.c.white(a)
        func = lambda a: a
        self.color_item(transform, item, maxsize, func, parent_item_key)

    def color_item(self, transform, item, maxsize, func, parent_item_key: str = ""):
        # print("+++++ AAA render - data: %s" % data)
        # print("+++++ %s" % self.c.white("prova colorata"))
        # print("+++++ %s" % self.c.bgred("prova colorata"))
        # print("+++++ transform %s" % transform)

        # item[item_key] = self.c.yellow(value)
        # Back_gray = '\x1b[48;5;59m'
        # Back_gray = '\x1b[48;5;188m'
        # Style_reset = '\x1b[0m'
        # item[item_key] = f'{Back_gray}{value}{Style_reset}'

        for item_key in item:
            colortext = transform.get(parent_item_key + item_key + ".colortext")
            # print("transform key: %s - value: %s" % (parent_item_key + item_key, transform.get(parent_item_key + item_key + ".colortext")))
            if (
                type(item_key) is str
                and (transform.get(parent_item_key + item_key) is None or colortext is True)
                and (colortext is None or colortext is True)
            ):
                # print("parent_item_key - item_key: %s - %s  - %s" % (parent_item_key, item_key, type(item_key)))

                from beecell.simple import dict_get, dict_set

                # value = item[item_key]
                value = dict_get(item, item_key)

                if type(value) == str:
                    if getattr(self.app.pargs, "notruncate", False) is False:
                        value = truncate(value, size=(maxsize), replace_new_line=False)
                    dict_set(item, item_key, func(value))

                elif type(value) == bool:
                    from beecell.types.type_string import bool2str

                    item[item_key] = func(bool2str(value))

                elif type(value) == int:
                    item[item_key] = func(str(value))

                elif type(value) == float:
                    item[item_key] = func(str(value))

                elif type(value) == dict:
                    self.color_item(transform, value, maxsize, func, parent_item_key=parent_item_key + item_key + ".")

                elif type(value) == list:
                    for subitem in value:
                        if type(subitem) == dict:
                            self.color_item(transform, subitem, maxsize, func)
                        # TODO: not dict (list IP)

            # else:
            #     print("+++++ parent_item_key + item_key %s %s" % (parent_item_key, item_key))

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

        from copy import deepcopy

        color_data = deepcopy(data)

        # print("+++++ key: %s" % key)
        # print("+++++ data: %s" % data)
        if color_data is not None and key is not None:
            color_data = color_data[key]
        elif isinstance(color_data, dict) and color_data.get("msg", None) is not None:
            msg = color_data.get("msg")
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
                color_data, sections = manage_data(color_data)

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

            if color_data is not None:
                for k, v in color_data.items():
                    __format_table_data(k, v)
            else:
                self.app.error("data is None!")

            color_data = resp
            headers = ["attrib", "value"]
            print_header = False
            table_style = "plain"

        # transform
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

        def __color_rows(data):
            i: int = 0
            new_data = []
            for item in data:
                i += 1
                if i % 2 == 0:
                    self.color_even(transform, item, maxsize)
                else:
                    self.color_odd(transform, item, maxsize)
                new_data.append(item)
            return new_data

        if isinstance(data, dict) or isinstance(data, list):
            if data is not None and "page" in data:
                print("Page: %s" % data["page"])
                print("Count: %s" % data["count"])
                print("Total: %s" % data["total"])
                print(
                    "Order: %s %s"
                    % (
                        data.get("sort").get("field"),
                        data.get("sort").get("order"),
                    )
                )
                print("")

            # color odd rows
            if isinstance(color_data, list):
                color_data = __color_rows(color_data)

            self._tabularprint(
                color_data,
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
                color_data = section.get("value")
                if isinstance(color_data, list):
                    color_data = __color_rows(color_data)
                self._tabularprint(
                    color_data,
                    table_style,
                    headers=section.get("headers"),
                    fields=section.get("fields"),
                    maxsize=maxsize,
                    transform=transform,
                )
