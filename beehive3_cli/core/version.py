# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


def get_version():
    from pathlib import Path

    path = Path(__file__)
    path_version = f"{path.parent.parent.absolute()}/VERSION"
    # print("path_version %s" % path_version)
    with open(path_version, encoding="utf-8") as f:
        version = f.read()
    return version.strip()


def get_changelog(all_items=False):
    from pathlib import Path

    path = Path(__file__)
    path_changelog = f"{path.parent.parent.parent.absolute()}/CHANGELOG.md"
    # print("path_version %s" % path_version)

    str_out: str = ""
    line_version = False
    with open(path_changelog, encoding="utf-8") as f:
        lines = f.readlines()
        count = 0
        # Strips the newline character
        for line in lines:
            count += 1
            # print("Line{}: {}".format(count, line.strip()))
            if line.strip().startswith("## "):
                if not line_version:
                    line_version = True
                elif not all_items:
                    return str_out

            str_out += line

    return str_out
