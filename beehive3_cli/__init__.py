# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from pathlib import Path

__version__ = (Path(__file__).parent / "VERSION").read_text().strip()
