# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

"""
PyTest Fixtures.
"""

import pytest
from cement import fs


@pytest.fixture(scope="function")
def tmp(request):
    """
    Create a `tmp` object that geneates a unique temporary directory, and file
    for each test function that requires it.
    """
    t = fs.Tmp()
    yield t
    t.remove()
