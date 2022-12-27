# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from cement.ext.ext_json import JsonOutputHandler as OriginalJsonOutputHandler
from cement.utils.misc import minimal_logger
import json

LOG = minimal_logger(__name__)


class JsonOutputHandler(OriginalJsonOutputHandler):
    class Meta:
        label = 'json_output_handler'

    def render(self, data, *args, **kwargs):
        """
        Take a data dictionary and render it as Json output.  Note that the
        template option is received here per the interface, however this
        handler just ignores it.  Additional keyword arguments passed to
        ``jsonDumps()``.

        Args:
            data_dict (dict): The data dictionary to render.

        Keyword Args:
            template: This option is completely ignored.

        Returns:
            str: A JSON encoded string.

        """
        LOG.debug("rendering output as Json via %s" % self.__module__)
        return json.dumps(data, indent=2) + '\n'
