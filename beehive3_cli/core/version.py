# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte


from cement.utils.version import get_version as cement_get_version

# 1.15.0
VERSION = (1, 15, 0, "final", 0)


def get_version(version=VERSION):
    return cement_get_version(version)
