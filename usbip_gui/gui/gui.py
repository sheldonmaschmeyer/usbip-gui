"""Main graphical user interface implementation and window management."""

import os
import subprocess
import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt6.QtGui import QAction

from .common import DEFAULT_GEOMETRY, get_translator, load_config, save_config
from .server import ServerTab
from .client import ClientTab
from .menu import create_main_menu

t = get_translator("gui")


class UsbIpGui:
    """
    Main application class for the USB/IP GUI manager.
    """

    server_visible_action: QAction | None
    client_visible_action: QAction | None
    server_default_action: QAction | None
    client_default_action: QAction | None
    show_server_var: bool
    show_client_var: bool
    default_tab_var: str

    def __init__(self, root: QMainWindow):
        """Initialize the class instance."""
        self.root = root
        self.root.setWindowTitle(t("USB/IP Manager"))

        self.server_visible_action = None
        self.client_visible_action = None
        self.server_default_action = None
        self.client_default_action = None

        geom = DEFAULT_GEOMETRY.split("x")
        if len(geom) == 2:
            self.root.resize(int(geom[0]), int(geom[1]))

        self.notebook = QTabWidget(self.root)
        self.root.setCentralWidget(self.notebook)

        self.server_tab = ServerTab()
        self.client_tab = ClientTab()

        config = load_config()
        self.show_server_var = bool(config.get("show_server", True))
        self.show_client_var = bool(config.get("show_client", True))
        self.default_tab_var = str(config.get("default_tab", "server"))

        create_main_menu(self)

        self.update_tabs()
        self.apply_default_tab()

    def update_tabs(self) -> None:
        """Update visible tabs based on settings."""
        # Get actions from self if they exist
        if self.server_visible_action:
            self.show_server_var = self.server_visible_action.isChecked()
        if self.client_visible_action:
            self.show_client_var = self.client_visible_action.isChecked()

        current_idx = self.notebook.currentIndex()
        current_widget = (
            self.notebook.widget(current_idx) if current_idx >= 0 else None
        )

        self.notebook.clear()

        if self.show_server_var:
            self.notebook.addTab(
                self.server_tab, t("Server (Local USB Devices)")
            )
        if self.show_client_var:
            self.notebook.addTab(
                self.client_tab, t("Client (Remote USB Devices)")
            )

        if current_widget:
            idx = self.notebook.indexOf(current_widget)
            if idx >= 0:
                self.notebook.setCurrentIndex(idx)

        self.save_settings()

    def apply_default_tab(self) -> None:
        """Select default tab."""
        if self.default_tab_var == "server" and self.show_server_var:
            idx = self.notebook.indexOf(self.server_tab)
            if idx >= 0:
                self.notebook.setCurrentIndex(idx)
        elif self.default_tab_var == "client" and self.show_client_var:
            idx = self.notebook.indexOf(self.client_tab)
            if idx >= 0:
                self.notebook.setCurrentIndex(idx)

    def save_settings(self) -> None:
        """Save settings to config file."""
        if (
            self.server_default_action
            and self.server_default_action.isChecked()
        ):
            self.default_tab_var = "server"
        elif (
            self.client_default_action
            and self.client_default_action.isChecked()
        ):
            self.default_tab_var = "client"

        config = load_config()
        config["show_server"] = self.show_server_var
        config["show_client"] = self.show_client_var
        config["default_tab"] = self.default_tab_var
        save_config(config)


def start_app():
    """Start app."""
    app = QApplication(sys.argv)

    script_path = os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ),
        "setup_usbip.sh",
    )
    if os.path.exists(script_path):
        modules = ["usbip_core", "usbip_host", "vhci_hcd"]
        if not all(os.path.exists(f"/sys/module/{mod}") for mod in modules):
            subprocess.run(["bash", script_path], check=False)

    root = QMainWindow()

    style_path = os.path.join(os.path.dirname(__file__), "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    UsbIpGui(root)
    root.show()
    sys.exit(app.exec())
