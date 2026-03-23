#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


from threading import Thread
from textual.screen import  Screen
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Button, DataTable, LoadingIndicator
from textual import containers, lazy

from beehive3_cli.plugins.vsphere.controllers.manage_datasource.header import Header


class PodScreen(Screen):
    DEFAULT_CSS = """
    DataTable {        
        height: 16 !important;            
        &.-maximized {
            height: auto !important;
        }
    }
    
    """

    def compose(self) -> ComposeResult:
        with lazy.Reveal(containers.VerticalScroll(can_focus=True)):
            yield Header(id_selected="button_header_pod")
            yield Static("Select pod")

            pods = [
                { "name": "podto1", "id": "Podto1Vsphere" },
                { "name": "podto2", "id": "Podto2Vsphere" },
                { "name": "podvc", "id": "Podvc1Vsphere" },
                { "name": "podto5", "id": "Podto5Vsphere" },
                { "name": "podge6", "id": "Podge6Vsphere" },
            ]

            # with Vertical() as container:
            with Horizontal():
                for pod in pods:
                    if self.app.container_oid == pod.get("id"):
                        yield Button(pod.get("name"), id=pod.get("id"), variant="success")
                    else:
                        yield Button(pod.get("name"), id=pod.get("id"), variant="primary")

            yield Static("Datastore to synchronize")
            yield DataTable()
            yield Button.warning("Synchronize datastore", id="synchronize")

    def on_mount(self) -> None:
        loading = self.query_one("#header_loading", LoadingIndicator)
        loading.display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = str(event.button.id)
        self.app.base.app.log.info(f"button_id: {button_id}")

        if button_id == "synchronize":
            if self.app.container_oid is None:
                self.notify("ERROR: Select pod", severity="error")
            else:
                self.thread_progress = Thread(target = self.exec_sync)
                self.thread_progress.start()
                self.notify(f"Synchronize datastore on {self.app.container_oid} ...", severity="warning")

        elif button_id.startswith("Pod"):
            self.app.container_oid = str(event.button.id)
            self.app.base.app.log.info("exec_discover")

            for button in self.query("Button"):
                if button.id.startswith("Pod"):
                    button.variant = "primary"

            button_pressed = self.query_one(f"#{button_id}", Button)
            button_pressed.variant = "success"

            # reset volume type selected when change pod
            self.app.volume_type_oid = None
            self.app.volume_type_name = None

            self.thread_progress = Thread(target = self.exec_discover)
            self.thread_progress.start()
            self.notify(f"Discover datastore on {self.app.container_oid} ...", severity="warning")

    def exec_discover(self):
        self.app.base.app.log.info("exec_discover...")

        try:
            loading = self.query_one("#header_loading", LoadingIndicator)
            loading.display = True

            table = self.query_one(DataTable)
            table.cursor_type = "row"
            # table.zebra_stripes = True
            table.clear()

            resclass = "Vsphere.DataCenter.Datastore"
            uri = f"/v1.0/nrs/containers/{self.app.container_oid}/discover"
            res = self.app.base.cmp_get(uri, data={"type": resclass})
            self.app.base.app.log.info(f"exec_discover - res: {res}")
            discover_resources = res.get("discover_resources")
            new = discover_resources.get("new")
            died = discover_resources.get("died")
            changed = discover_resources.get("changed")
            # self.app.base.app.log.info("exec_discover - new: %s" % new)

            rows = []
            for item in new:
                rows.append(("new", item.get("id"), item.get("name")))
            for item in died:
                rows.append(("died", item.get("id"), item.get("name")))
            for item in changed:
                rows.append(("changed", item.get("id"), item.get("name")))

            if table.columns == {}:
                columns = [
                    ("type", "id", "name"),
                ]
                table.add_columns(*columns[0])
            table.add_rows(rows)

            self.notify("Discover datastore finished")
            loading.display = False

        except Exception as exc:
            self.app.base.app.log.error(f"exec_discover - ex: {exc}", exc_info=True)
            self.notify(f"Error {exc}", severity="error")

    def exec_sync(self):
        try:
            loading = self.query_one("#header_loading", LoadingIndicator)
            loading.display = True

            oid = self.app.container_oid
            new = True
            died = True
            changed = False

            resclass = "Vsphere.DataCenter.Datastore"
            data = {"types": resclass, "new": new, "died": died, "changed": changed}
            uri = f"/v1.0/nrs/containers/{oid}/discover"
            res = self.app.base.cmp_put(uri, data={"synchronize": data}, output=False)
            self.app.base.app.log.info(f"exec_sync - res: {res}")

            table = self.query_one(DataTable)
            table.clear()

            self.notify("Synchronize datastore finished")

            loading.display = False

        except Exception as exc:
            self.app.base.app.log.error(f"exec_discover - ex: {exc}", exc_info=True)
            self.notify(f"Error {exc}", severity="error")
