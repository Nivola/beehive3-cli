#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from typing import TYPE_CHECKING
from argparse import Namespace
from threading import Thread
from textual.screen import  Screen, ModalScreen
from textual.app import ComposeResult
from textual.containers import Horizontal, Grid, VerticalScroll
from textual.widgets import Static, Button, DataTable, Label, Input, LoadingIndicator


if TYPE_CHECKING:
    from beehive3_cli.plugins.vsphere.controllers.manage_datasource.app import ManageDatasourceApp

from beehive3_cli.plugins.vsphere.controllers.manage_datasource.header import Header


class RemoveDatastoreScreen(ModalScreen[bool]):
    """Screen with a dialog."""
    datastore_uuid = None
    datastore_name = None

    def __init__(self, datastore_uuid=None, datastore_name=None, name = None, screen_id = None, classes = None):
        self.datastore_uuid = datastore_uuid
        self.datastore_name = datastore_name
        super().__init__(name=name, id=screen_id, classes=classes)

    def compose(self) -> ComposeResult:
        self.app.base.app.log.info("compose RemoveDatastoreScreen")
        yield Grid(
            Label(f"Are you sure you want to remove datastore {self.datastore_name} ?", id="question"),
            Button("OK", variant="error", id="button_ok"),
            Button("Cancel", variant="primary", id="button_cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        try:
            self.app.base.app.log.info(f"on_button_pressed - event.button.id: {event.button.id}")
            if event.button.id == "button_ok":
                data_entities = {
                    "datastore": {
                        "uuid": self.datastore_uuid,
                    }
                }
                self.app.base.app.log.info(f"on_button_pressed - data_entities: {data_entities}")
                uri = f"/v1.0/nrs/vsphere/volumetypes/{self.app.volume_type_oid}/datastores"
                self.app.base.app.log.info(f"on_button_pressed - uri: {uri}")

                app: ManageDatasourceApp = self.app
                # avoid confirm on delete
                namespace: Namespace = app.base.app.pargs
                self.app.base.app.log.info(f"on_button_pressed - namespace: {namespace}")
                namespace.__dict__.update({"assumeyes": True})

                # remove datastore from volumetype
                self.app.base.app.log.info(f"on_button_pressed - app.base.app.pargs: {app.base.app.pargs}")
                res = app.base.cmp_delete(uri, data=data_entities, entity=f"datastore {self.datastore_uuid}")
                self.app.base.app.log.info(f"remove datastore {self.datastore_uuid} - res: {res}")
                self.notify(f"Removed datastore {self.datastore_name}", severity="warning")
                self.dismiss(True)
            else:
                self.dismiss(False)
        except Exception as ex:
            self.app.base.app.log.error(f"on_button_pressed - ex: {ex}", exc_info=True)

class ManageScreen(Screen):
    all_datastores_pod = []
    datastores_pod = []

    composed = False
    DEFAULT_CSS = """
    DataTable {        
        height: 10 !important;            
        &.-maximized {
            height: auto !important;
        }
    }
    
    """

    def compose(self) -> ComposeResult:
        self.app.base.app.log.info("compose ManageScreen")
        with VerticalScroll() as container:
            yield Header(id_selected="button_header_manage")
            yield Static("Manage datastore in volume type")

            yield Static("---")
            yield Static(f"Pod {self.app.container_oid} datastores", id="static_pod_datastore")

            with Horizontal():
                yield Input(placeholder="filter name", id="input_name")
                yield Button.warning("Filter", id="filter_name")

            yield DataTable(id="datatable_not_linked")
            yield Button.warning("Add datastore to volume type", id="add_datastore")

            yield Static("---")
            yield Static(
                f"Volume type {self.app.volume_type_name} linked datastores",
                id="static_volumetype_datastore"
            )
            yield DataTable(id="datatable_linked")
            yield Button.warning("Remove datastore from volume type", id="del_datastore")

    def _on_screen_resume(self):
        self.app.base.app.log.info(f"_on_screen_resume - self.composed: {self.composed}")

        static_pod_datastore = self.query_one("#static_pod_datastore", Static)
        static_pod_datastore.update(f"Pod {self.app.container_oid} datastores")

        static_volumetype_datastore = self.query_one("#static_volumetype_datastore", Static)
        static_volumetype_datastore.update(f"Volume type {self.app.volume_type_name} linked datastores")

        if not self.composed:
            self.composed = True

            app: ManageDatasourceApp = self.app
            if app.container_oid is None:
                self.notify("ERROR: Select pod", severity="error")
            elif app.volume_type_oid is None:
                self.notify("ERROR: Select volume type", severity="error")
            else:
                self.thread_progress = Thread(target = self.exec_get_volumetype_datastore, args=(True,))
                self.thread_progress.start()
                self.notify(f"Get volumetype datastore on {app.volume_type_name}", severity="warning")

        return super()._on_screen_resume()

    def _on_screen_suspend(self):
        self.composed = False
        return super()._on_screen_suspend()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = str(event.button.id)
        self.app.base.app.log.info(f"button_id: {button_id}")

        if button_id == "add_datastore":
            datatable_not_linked = self.query_one("#datatable_not_linked", DataTable)
            cursor_row = datatable_not_linked.cursor_row
            if 0 <= cursor_row < len(datatable_not_linked.rows):
                row = datatable_not_linked.get_row_at(cursor_row)
                datastore_uuid = row[0]
                datastore_name = row[1]

                data_entities = {
                    "datastore": {
                        "uuid": datastore_uuid,
                        "tag": "default",
                    }
                }
                uri = f"/v1.0/nrs/vsphere/volumetypes/{self.app.volume_type_oid}/datastores"
                res = self.app.base.cmp_post(uri, data=data_entities)
                self.app.base.app.log.info(f"add datastore {datastore_uuid} - res: {res}")
                self.notify(f"Added datastore {datastore_name}", severity="warning")

                self.thread_progress = Thread(target = self.exec_get_volumetype_datastore,  args=(False,))
                self.thread_progress.start()
                self.notify(f"Get volumetype datastore on {self.app.volume_type_name}", severity="warning")

        elif button_id == "del_datastore":
            datatable_linked = self.query_one("#datatable_linked", DataTable)
            cursor_row = datatable_linked.cursor_row
            if 0 <= cursor_row < len(datatable_linked.rows):
                row = datatable_linked.get_row_at(cursor_row)
                datastore_uuid = row[0]
                datastore_name = row[1]

                def check_quit(reload: bool):
                    """Called when QuitScreen is dismissed."""
                    self.app.base.app.log.info(f"check_quit - reload: {reload}")
                    if reload:
                        self.composed = False
                    else:
                        self.composed = True

                self.app.push_screen(
                    RemoveDatastoreScreen(datastore_uuid=datastore_uuid, datastore_name=datastore_name),
                    check_quit
                )

        elif button_id == "filter_name":
            input_name = self.query_one("#input_name", Input)
            l_filter: str = input_name.value

            rows_pod = []
            for datastore_pod in self.datastores_pod:
                ds_uuid_pod = datastore_pod.get("uuid")
                ds_name_pod: str = datastore_pod.get("name")
                if l_filter is None or ds_name_pod.upper().find(l_filter.upper()) >= 0:
                    rows_pod.append((ds_uuid_pod, ds_name_pod))

            def my_func_sort_name(e):
                return e[1]

            rows_pod.sort(key=my_func_sort_name)

            # not linked
            datatable_not_linked = self.query_one("#datatable_not_linked", DataTable)
            datatable_not_linked.clear()
            if datatable_not_linked.columns == {}:
                columns = [
                    ("uuid", "name"),
                ]
                datatable_not_linked.add_columns(*columns[0])
            datatable_not_linked.add_rows(rows_pod)

    def exec_get_volumetype_datastore(self, reload_datastore_pod):
        try:
            loading = self.query_one("#header_loading", LoadingIndicator)
            loading.display = True

            self.app.base.app.log.info(f"exec_get_volumetype_datastore - reload_datastore_pod: {reload_datastore_pod}")
            datatable_not_linked = self.query_one("#datatable_not_linked", DataTable)
            datatable_not_linked.clear()

            datatable_linked = self.query_one("#datatable_linked", DataTable)
            datatable_linked.clear()

            input_name = self.query_one("#input_name", Input)
            l_filter: str = input_name.value

            # get datastore of selected pod
            if reload_datastore_pod:
                data_pod = {
                    "container": self.app.container_oid,
                    "page": 0,
                    "size": -1,
                    "field": "name",
                    "order": "ASC",
                }
                uri = "/v1.0/nrs/vsphere/datastores"
                res_pod = self.app.base.cmp_get(uri, data=data_pod)
                self.app.base.app.log.info(f"exec_get_volumetype_datastore - res_pod: {res_pod}")
                self.all_datastores_pod: list = res_pod.get("datastores")

            # get datastore linked to volumetype
            data_volumetype = {
                "page": 0,
                "size": 100,
                "field": "name",
                "order": "ASC",
            }
            uri = f"/v1.0/nrs/vsphere/volumetypes/{self.app.volume_type_oid}/datastores"
            res_volumetype = self.app.base.cmp_get(uri, data=data_volumetype)
            self.app.base.app.log.info(f"exec_get_volumetype_datastore - res_volumetype: {res_volumetype}")
            datastores_volumetype: list = res_volumetype.get("datastores")

            rows_volumetype = []
            rows_pod = []
            self.datastores_pod = self.all_datastores_pod.copy()

            for datastore_volumetype in datastores_volumetype:
                ds_uuid_volumetype = datastore_volumetype.get("uuid")
                ds_name_volumetype = datastore_volumetype.get("name")
                rows_volumetype.append((ds_uuid_volumetype, ds_name_volumetype))

                # check datastore already linked
                for datastore_pod in self.all_datastores_pod:
                    ds_uuid_pod = datastore_pod.get("uuid")
                    if ds_uuid_pod == ds_uuid_volumetype:
                        self.datastores_pod.remove(datastore_pod)

            for datastore_pod in self.datastores_pod:
                ds_uuid_pod = datastore_pod.get("uuid")
                ds_name_pod = datastore_pod.get("name")
                if l_filter is None or ds_name_pod.upper().find(l_filter.upper()) >= 0:
                    rows_pod.append((ds_uuid_pod, ds_name_pod))

            def my_func_sort_name(e):
                return e[1]

            rows_volumetype.sort(key=my_func_sort_name)
            rows_pod.sort(key=my_func_sort_name)

            # not linked
            if datatable_not_linked.columns == {}:
                columns = [
                    ("uuid", "name"),
                ]
                datatable_not_linked.add_columns(*columns[0])
            datatable_not_linked.add_rows(rows_pod)

            # linked
            if datatable_linked.columns == {}:
                columns = [
                    ("uuid", "name"),
                ]
                datatable_linked.add_columns(*columns[0])
            datatable_linked.add_rows(rows_volumetype)

            self.notify("Get volumetype datastore finished")
            loading.display = False

        except Exception as exc:
            self.app.base.app.log.error("exec_get_volumetype_datastore", exc, exc_info=True)
            self.notify(f"Error {exc}", severity="error")
