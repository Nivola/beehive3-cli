#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from textual.scroll_view import ScrollView
from textual.app import ComposeResult
from textual.widgets import Button, LoadingIndicator
from textual.containers import Horizontal


class Header(ScrollView, can_focus=False):

    def __init__(
            self,
            *children,
            id_selected=None,
            name=None,
            id=None,
            classes=None,
            disabled=False,
            can_focus=None,
            can_focus_children=None,
            can_maximize=None
    ):
        super().__init__(
            *children,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            can_focus=can_focus,
            can_focus_children=can_focus_children,
            can_maximize=can_maximize
        )
        self.id_selected = id_selected

    def compose(self) -> ComposeResult:
        tabs = [
            {
                "name": "-> Pod", 
                "id":"button_header_pod"
            }, {
                "name": "-> Volume type", 
                "id":"button_header_volumetype"
            }, {
                "name": "-> Manage", 
                "id":"button_header_manage"
            },
        ]

        with Horizontal():
            for tab in tabs:
                if tab.get("id") == self.id_selected:
                    yield Button.success(tab.get("name"), id=tab.get("id"))
                else:
                    yield Button(tab.get("name"), id=tab.get("id"), variant="primary")

            yield Button.error("-> Exit", id="button_header_exit")

            yield LoadingIndicator(id="header_loading", )
