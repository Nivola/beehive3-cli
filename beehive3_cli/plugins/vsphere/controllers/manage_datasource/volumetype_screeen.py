#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


from threading import Thread
from textual.screen import  Screen
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static, Button, DataTable, LoadingIndicator

from beehive3_cli.plugins.vsphere.controllers.manage_datasource.header import Header

class VolumeTypeScreen(Screen):
    composed = False
    DEFAULT_CSS = """
    DataTable {
        height: 16 !important;
        &.-maximized {
            height: auto !important;
        }
    }
    
    """

    def compose(self) -> ComposeResult:
        self.app.base.app.log.info("compose VolumeTypeScreen")
        with VerticalScroll() as container:
            yield Header(id_selected="button_header_volumetype")
            yield Static(f"Select volume type of pod {self.app.container_oid}", id="static_volumetype")
            yield DataTable()
            yield Button.warning("Select volume type", id="select_volume_type")

    def _on_screen_resume(self):
        self.app.base.app.log.info(f"_on_screen_resume - self.composed: {self.composed}")

        static_volumetype = self.query_one("#static_volumetype", Static)
        static_volumetype.update(f"Select volume type of pod {self.app.container_oid}")

        if not self.composed:
            self.composed = True

            if self.app.container_oid is None:
                self.notify("ERROR: Select pod", severity="error")
            else:
                self.thread_progress = Thread(target = self.exec_get_volumetype)
                self.thread_progress.start()
                self.notify(f"Get volumetype on {self.app.container_oid}", severity="warning")

        return super()._on_screen_resume()

    def _on_screen_suspend(self):
        self.composed = False
        return super()._on_screen_suspend()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = str(event.button.id)
        self.app.base.app.log.info(f"button_id: {button_id}")

        if button_id == "select_volume_type":
            table = self.query_one(DataTable)
            row = table.get_row_at(table.cursor_row)
            self.app.volume_type_oid = row[0]
            self.app.volume_type_name = row[1]
            self.notify(f"Selected volume type {self.app.volume_type_name}", severity="warning")
            self.app.switch_mode("manage")

    def exec_get_volumetype(self):
        try:
            loading = self.query_one("#header_loading", LoadingIndicator)
            loading.display = True

            table = self.query_one(DataTable)
            table.cursor_type = "row"
            # table.zebra_stripes = True
            table.clear()

            data_entities = {
                "container": self.app.container_oid,
                "type": "Vsphere.DataCenter.VolumeType",
                "page": 0,
                "size": 50,
                "field": "name",
                "order": "ASC",
            }

            uri = "/v1.0/nrs/entities"
            res = self.app.base.cmp_get(uri, data=data_entities)
            self.app.base.app.log.info(f"exec_get_volumetype - res: {res}")
            resources = res.get("resources")

            rows = []
            for item in resources:
                rows.append((item.get("id"), item.get("name")))

            if table.columns == {}:
                columns = [
                    ("id", "name"),
                ]
                table.add_columns(*columns[0])
            table.add_rows(rows)
            self.notify("Get volumetype finished")

            loading.display = False

        except Exception as exc:
            self.app.base.app.log.error(f"exec_get_volumetype - ex: {exc}", exc_info=True)
            self.notify(f"Error {exc}", severity="error")
