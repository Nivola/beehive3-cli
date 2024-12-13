# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from cement.core.output import OutputHandler
from tabulate import tabulate
from beecell.simple import truncate
from beehive3_cli.core.util import ColoredText

from typing import Callable, Dict, List, Optional, Union, Tuple

# data Dict in input
# in output tuple with updated data Dict, and list of sections
ManageDataFunction = Callable[[Dict], Tuple[Dict, List[Dict]]]

# example section:
# {
#     "title": "example title"
#     "headers": ["header1","header2",...]
#     "fields": ["field1", "field2",...]
#     "value": [...]
# }


class MixedOutputHandler(OutputHandler):
    c = ColoredText()

    def handles_text(self) -> bool:
        """
        True if handler should be able to handle data of format -f "text"
        """
        return True

    DO_NOT_TRUNCATE = ["id", "uuid", "parent", "ip_address", "hostname"]

    class Meta:
        label = "mixed_output_handler"
        overridable = True

    def _check_render_msg(self, data, transforms: Dict) -> bool:
        """
        if data is a dict, and has "msg" key,
        apply optional transform and print msg
        return True if handled (i.e. something printed)
        otherwise False (try using next handlers)
        """
        if isinstance(data, dict):
            msg = data.get("msg")
            transform_fun = transforms.get("msg")
            if msg is not None:
                if transform_fun is not None:
                    try:
                        msg = transform_fun(msg)
                    except ValueError:
                        self.app.warning("transform value error")
                        pass
                print(msg)
                return True
        return False

    @staticmethod
    def _multi_get(data, key, separator="."):
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
        if res is None or res == {}:
            res = "-"

        return res

    @staticmethod
    def _format_details_data(key, values: Union[List, str]) -> List[Dict]:
        res = []
        if isinstance(values, list):
            i = 0
            for value in values:
                res.extend(MixedOutputHandler._format_details_data("%s.%s" % (key, i), value))
                i += 1
        elif isinstance(values, dict):
            for v_key, v_values in values.items():
                res.extend(MixedOutputHandler._format_details_data("%s.%s" % (key, v_key), v_values))
        else:
            res.append({"attrib": key, "value": values})
        return res

    def _get_details_table_data(
        self, data: Dict, transforms: Dict, manage_data: Optional[ManageDataFunction] = None
    ) -> Dict:
        table_data = []
        sections = []
        tmp_data = data

        # optionally apply manage_data
        if manage_data is not None:
            tmp_data, sections = manage_data(tmp_data)

        if tmp_data is not None:
            for k, v in data.items():
                table_data.extend(MixedOutputHandler._format_details_data(k, v))
        else:
            self.app.error("data is None!")

        return table_data, sections

    def _render_pagination(self, data: Dict):
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

    def _check_resolve_alternative_headers_and_fields(self, headers, fields) -> Tuple[List, List]:
        """
        add additional headers to headers list if any
        add additional fields to fields list if any
        resolve headers and fields
        """
        new_fields = []
        if getattr(self.app.pargs, "afields", None) is not None:
            new_fields = self.app.pargs.afields.split(",")
            headers.extend(new_fields)
        elif getattr(self.app.pargs, "fields", None) is not None:
            alt_fields = self.app.pargs.fields.split(",")
            headers = alt_fields
            fields = alt_fields

        if fields is None:
            fields = headers
        else:
            fields.extend(new_fields)
        return headers, fields

    def _render_table(self, data, headers=[], fields=None, transforms=None, options={}) -> bool:
        """
        print table
        """
        # import pdb
        # pdb.set_trace()
        if data is None:
            data = "-"

        if not isinstance(data, list):
            values = [data]
        else:
            values = data

        headers, fields = self._check_resolve_alternative_headers_and_fields(headers, fields)
        if not (options.get("print_header", True)):
            headers = []
        headers_len = len(headers)
        fields_len = len(fields)
        opt_maxcolumn = options.get("max_column", 15)
        opt_notruncate = options.get("notruncate", False)

        table = []
        even_line = True
        for item in values:
            raw = []  # line before formatting
            # get line value
            if isinstance(item, dict):
                for key in fields:
                    val = MixedOutputHandler._multi_get(item, key, separator=options.get("separator", "."))
                    raw.append(str(val))  # str() is needed in some cases
            else:
                raw.append(str(item))  # str() is needed in some cases

            # apply formatting to line
            for col_idx, col_val in enumerate(raw):
                field_name = fields[col_idx] if col_idx < fields_len else None
                header_name = headers[col_idx] if col_idx < headers_len else None
                # check if truncate set and truncate if permitted and necessary
                if not (opt_notruncate) and header_name not in self.DO_NOT_TRUNCATE and len(col_val) > opt_maxcolumn:
                    col_val = truncate(col_val, opt_maxcolumn, replace_new_line=False)
                # check if specific transform for field, otherwise color even/odd (line based)
                if field_name in transforms.keys():
                    raw[col_idx] = transforms[field_name](col_val)
                elif even_line:
                    raw[col_idx] = self.c.yellow(col_val)
                else:
                    raw[col_idx] = col_val

            # add formatted line to table
            table.append(raw)
            even_line = not (even_line)

        headers = [self.c.blue(h) for h in headers]
        print(
            tabulate(
                table,
                headers=headers,
                tablefmt=options.get("table_style", "plain"),
                showindex=options.get("showindex", "never"),
            )
        )

    def _render_inner(
        self,
        data: Union[Dict, str],
        # handle details data
        key: Optional[str] = None,
        details: bool = False,
        transforms: Optional[Dict] = None,
        manage_data: Optional[ManageDataFunction] = None,
        # handle table data
        headers: List = [],
        fields: Optional[List] = None,
        # options
        options: Dict = {},
    ):
        if data is None:
            self.app.error("data is undefined")
            return

        DEFAULT_TRANSFORMS = {
            "base_state": self.app.color_error,
            "state": self.app.color_error,
            "status": self.app.color_error,
        }
        if transforms is not None:
            DEFAULT_TRANSFORMS.update(transforms)
        transforms = DEFAULT_TRANSFORMS

        orig_data = data
        if key is not None:
            data = data[key]

        # if present, render message and exit
        if self._check_render_msg(data, transforms):
            return

        # if details, get data in expected table format
        if details:
            table_data, sections = self._get_details_table_data(data, transforms, manage_data)
            headers = ["attrib", "value"]
            options["print_header"] = False
            options["table_style"] = "plain"
            options["notruncate"] = True
        else:
            sections = []
            table_data = data

        # print data in "table" format
        if isinstance(data, dict) or isinstance(data, list):
            # print pagination header if pagination data present
            self._render_pagination(orig_data)

            # print table
            self._render_table(
                table_data,
                headers=headers,
                fields=fields,
                transforms=transforms,
                options=options,
            )

            for section in sections:
                print("\n" + self.c.underline(section.get("title")))
                self._render_table(
                    section.get("value"),
                    headers=section.get("headers"),
                    fields=section.get("fields"),
                    transforms=transforms,
                    options=options,
                )

    def render(self, data, *args, **kwargs):
        key = kwargs.get("key")
        transforms = kwargs.get("transform")
        details = kwargs.get("details", False)
        manage_data = kwargs.get("manage_data", lambda identity: (identity, []))

        headers = kwargs.get("headers", [])
        other_headers = kwargs.get("other_headers", [])
        headers.extend(other_headers)
        fields = kwargs.get("fields", None)

        options = {k: v for k, v in kwargs.items() if k in ("separator", "table_style", "print_header", "show_index")}
        options["notruncate"] = self.app.pargs.notruncate

        self._render_inner(data, key, details, transforms, manage_data, headers, fields, options)
