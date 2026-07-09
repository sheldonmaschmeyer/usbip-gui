"""Main application menu bar implementation."""

from tkinter import Menu
from typing import TYPE_CHECKING
from ..common import get_translator
from .about import show_about_dialog
from .language_switcher import toggle_language

t = get_translator("menu")

if TYPE_CHECKING:
    from usbip_gui.gui.gui import UsbIpGui


def create_main_menu(app: "UsbIpGui"):
    """Create main menu."""
    root = app.root
    bg = "#1e1e2e"
    menu_bg = "#313244"
    fg = "#cdd6f4"
    abg = "#45475a"
    afg = "#cdd6f4"
    bw = 0

    menubar = Menu(
        root,
        bg=bg,
        fg=fg,
        activebackground=abg,
        activeforeground=afg,
        borderwidth=bw,
    )

    filemenu = Menu(
        menubar,
        tearoff=0,
        bg=menu_bg,
        fg=fg,
        activebackground=abg,
        activeforeground=afg,
        borderwidth=1,
        relief="solid",
    )
    filemenu.add_command(
        label=t("About"), command=lambda: show_about_dialog(root)
    )
    filemenu.add_separator()
    filemenu.add_command(label=t("Close"), command=root.quit)

    menubar.add_cascade(label=t("File"), menu=filemenu)

    viewmenu = Menu(
        menubar,
        tearoff=0,
        bg=menu_bg,
        fg=fg,
        activebackground=abg,
        activeforeground=afg,
        borderwidth=1,
        relief="solid",
    )

    tabsmenu = Menu(
        viewmenu,
        tearoff=0,
        bg=menu_bg,
        fg=fg,
        activebackground=abg,
        activeforeground=afg,
        borderwidth=1,
        relief="solid",
    )
    tabsmenu.add_checkbutton(
        label=t("Server"),
        variable=app.show_server_var,
        command=app.update_tabs,
    )
    tabsmenu.add_checkbutton(
        label=t("Client"),
        variable=app.show_client_var,
        command=app.update_tabs,
    )

    defaulttabmenu = Menu(
        viewmenu,
        tearoff=0,
        bg=menu_bg,
        fg=fg,
        activebackground=abg,
        activeforeground=afg,
        borderwidth=1,
        relief="solid",
    )
    defaulttabmenu.add_radiobutton(
        label=t("Server"),
        variable=app.default_tab_var,
        value="server",
        command=app.save_settings,
    )
    defaulttabmenu.add_radiobutton(
        label=t("Client"),
        variable=app.default_tab_var,
        value="client",
        command=app.save_settings,
    )

    viewmenu.add_cascade(label=t("Visible Tabs"), menu=tabsmenu)
    viewmenu.add_cascade(label=t("Default Tab"), menu=defaulttabmenu)

    menubar.add_cascade(label=t("View"), menu=viewmenu)

    # Add Language toggle directly to the menu bar
    menubar.add_command(label="EN / FR", command=toggle_language)

    root.config(menu=menubar)
