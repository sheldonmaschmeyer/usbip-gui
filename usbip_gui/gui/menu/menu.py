"""Main application menu bar implementation."""

from typing import TYPE_CHECKING

from PyQt6.QtGui import QAction, QActionGroup

from usbip_gui.typings import connect_signal, add_action
from usbip_gui.common import get_translator
from .about import show_about_dialog
from .language_switcher import toggle_language
from .debug import show_debug_window

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
    connect_signal(about_action.triggered, lambda: show_about_dialog(app.root))
    add_action(file_menu, about_action)

    file_menu.addSeparator()

    close_action = QAction(t("Close"), app.root)
    connect_signal(close_action.triggered, app.root.close)
    add_action(file_menu, close_action)

    # View Menu
    view_menu = menubar.addMenu(t("View"))
    assert view_menu is not None

    debug_action = QAction(t("Debug Window"), app.root)
    connect_signal(debug_action.triggered, lambda: show_debug_window(app.root))
    add_action(view_menu, debug_action)

    view_menu.addSeparator()

    # Visible Tabs Submenu
    tabs_menu = view_menu.addMenu(t("Visible Tabs"))
    assert tabs_menu is not None

    server_visible_action = QAction(t("Server"), app.root)
    server_visible_action.setCheckable(True)
    server_visible_action.setChecked(app.show_server_var)
    connect_signal(server_visible_action.triggered, app.update_tabs)
    add_action(tabs_menu, server_visible_action)
    app.server_visible_action = server_visible_action

    client_visible_action = QAction(t("Client"), app.root)
    client_visible_action.setCheckable(True)
    client_visible_action.setChecked(app.show_client_var)
    connect_signal(client_visible_action.triggered, app.update_tabs)
    add_action(tabs_menu, client_visible_action)
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
    connect_signal(server_default_action.triggered, app.save_settings)
    add_action(default_tab_group, server_default_action)
    add_action(default_tab_menu, server_default_action)
    app.server_default_action = server_default_action

    client_default_action = QAction(t("Client"), app.root)
    client_default_action.setCheckable(True)
    client_default_action.setData("client")
    if app.default_tab_var == "client":
        client_default_action.setChecked(True)
    connect_signal(client_default_action.triggered, app.save_settings)
    add_action(default_tab_group, client_default_action)
    add_action(default_tab_menu, client_default_action)
    app.client_default_action = client_default_action

    # Language Switcher
    lang_action = QAction("EN / FR", app.root)
    connect_signal(lang_action.triggered, toggle_language)
    add_action(menubar, lang_action)
