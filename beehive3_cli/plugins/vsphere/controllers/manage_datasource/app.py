# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


from textual.app import App
from textual.widgets import Button

from beehive3_cli.core.controller import BaseController
from beehive3_cli.plugins.vsphere.controllers.manage_datasource.manage_screen import ManageScreen
from beehive3_cli.plugins.vsphere.controllers.manage_datasource.pod_screen import PodScreen
from beehive3_cli.plugins.vsphere.controllers.manage_datasource.volumetype_screeen import VolumeTypeScreen

class ManageDatasourceApp(App):
    base: BaseController = None
    container_oid = None
    volume_type_oid = None
    volume_type_name = None

    b_pressed = False

    MODES = {
        "pod": PodScreen,
        "volumetype": VolumeTypeScreen,
        "manage": ManageScreen,
    }
    DEFAULT_MODE = "pod"

    CSS_PATH = "modal01.tcss"

    def set_parent(self, base):
        self.base = base
        self.base.app.log.info("starting...")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.b_pressed:
            return
        self.b_pressed = True

        # self.exit(str(event.button))
        button_id = str(event.button.id)
        self.base.app.log.info(f"button_id: {button_id}")

        # for button in self.query("Button"):
        #     if button.id.startswith("button_header_"):
        #         button.variant = "primary"

        if button_id.startswith("button_header_"):
            # button_pressed = self.query_one("#%s" % button_id, Button)
            # button_pressed.variant = "success"

            if button_id == "button_header_pod":
                self.switch_mode("pod")

            elif button_id == "button_header_volumetype":
                if self.container_oid is None:
                    self.notify("ERROR: Select pod", severity="error")
                else:
                    if self.get_screen(ManageScreen) is not None:
                        self.base.app.log.info("uninstall_screen ManageScreen")
                        self.uninstall_screen(ManageScreen)
                    self.switch_mode("volumetype")

            elif button_id == "button_header_manage":
                if self.volume_type_oid is None:
                    self.notify("ERROR: Select volume type", severity="error")
                else:
                    self.switch_mode("manage")

            elif button_id == "button_header_exit":
                self.exit()

        self.b_pressed = False
