"""Main application menu bar implementation."""

from typing import TYPE_CHECKING

from PyQt6.QtGui import QAction, QActionGroup

from ..common import get_translator
from .about import show_about_dialog
from .language_switcher import toggle_language

t = get_translator("menu")

if TYPE_CHECKING:
    from usbip_gui.gui.gui import UsbIpGui


def create_main_menu(app: "UsbIpGui"):
    """Create main menu."""
    menubar = app.root.menuBar()
    assert menubar is not None

    # File Menu
    file_menu = menubar.addMenu(t("File"))
    assert file_menu is not None

    about_action = QAction(t("About"), app.root)
    about_action.triggered.connect(lambda: show_about_dialog(app.root))
    file_menu.addAction(about_action)

    file_menu.addSeparator()

    close_action = QAction(t("Close"), app.root)
    close_action.triggered.connect(app.root.close)
    file_menu.addAction(close_action)

    # View Menu
    view_menu = menubar.addMenu(t("View"))
    assert view_menu is not None

    # Visible Tabs Submenu
    tabs_menu = view_menu.addMenu(t("Visible Tabs"))
    assert tabs_menu is not None

    server_visible_action = QAction(t("Server"), app.root)
    server_visible_action.setCheckable(True)
    server_visible_action.setChecked(app.show_server_var)
    server_visible_action.triggered.connect(app.update_tabs)
    tabs_menu.addAction(server_visible_action)
    app.server_visible_action = server_visible_action

    client_visible_action = QAction(t("Client"), app.root)
    client_visible_action.setCheckable(True)
    client_visible_action.setChecked(app.show_client_var)
    client_visible_action.triggered.connect(app.update_tabs)
    tabs_menu.addAction(client_visible_action)
    app.client_visible_action = client_visible_action

    # Default Tab Submenu
    default_tab_menu = view_menu.addMenu(t("Default Tab"))
    assert default_tab_menu is not None

    default_tab_group = QActionGroup(app.root)

    server_default_action = QAction(t("Server"), app.root)
    server_default_action.setCheckable(True)
    server_default_action.setData("server")
    if app.default_tab_var == "server":
        server_default_action.setChecked(True)
    server_default_action.triggered.connect(app.save_settings)
    default_tab_group.addAction(server_default_action)
    default_tab_menu.addAction(server_default_action)
    app.server_default_action = server_default_action

    client_default_action = QAction(t("Client"), app.root)
    client_default_action.setCheckable(True)
    client_default_action.setData("client")
    if app.default_tab_var == "client":
        client_default_action.setChecked(True)
    client_default_action.triggered.connect(app.save_settings)
    default_tab_group.addAction(client_default_action)
    default_tab_menu.addAction(client_default_action)
    app.client_default_action = client_default_action

    # Language Switcher
    lang_action = QAction("EN / FR", app.root)
    lang_action.triggered.connect(toggle_language)
    menubar.addAction(lang_action)
