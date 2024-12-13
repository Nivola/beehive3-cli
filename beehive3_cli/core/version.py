# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte


def get_version():
    from pathlib import Path

    path = Path(__file__)
    path_version = "%s/%s" % (path.parent.parent.absolute(), "VERSION")
    # print("path_version %s" % path_version)
    with open(path_version) as f:
        version = f.read()
    return version


def get_changelog(all=False):
    from pathlib import Path

    path = Path(__file__)
    path_changelog = "%s/%s" % (path.parent.parent.parent.absolute(), "CHANGELOG.md")
    # print("path_version %s" % path_version)

    str_out: str = ""
    line_version = False
    with open(path_changelog) as f:
        Lines = f.readlines()
        count = 0
        # Strips the newline character
        for line in Lines:
            count += 1
            # print("Line{}: {}".format(count, line.strip()))
            if line.strip().startswith("## "):
                if not line_version:
                    line_version = True
                elif not all:
                    return str_out

            str_out += line

    return str_out
