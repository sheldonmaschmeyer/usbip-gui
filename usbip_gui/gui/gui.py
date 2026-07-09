"""Main graphical user interface implementation and window management."""

from tkinter import Tk
from tkinter.ttk import Notebook, Label, Style
import tkinter.font as tkfont
import os
import subprocess
from typing import Protocol, Literal

from .common import DEFAULT_GEOMETRY, get_translator
from .server import ServerTab
from .client import ClientTab
from .menu import create_main_menu

t = get_translator("gui")


class UsbIpGui:
    """
    Main application class for the USB/IP GUI manager.

    This class encapsulates the main Tkinter window (root), style
    configurations, and notebook tabs (Server and Client). It replaces the
    previous architecture that relied on global variables, providing a clean,
    object-oriented state management system for the UI components.
    """

    def __init__(self, root: Tk):
        """Initialize the class instance."""
        self.root = root
        self.root.wm_title(t("USB/IP Manager"))
        self.root.geometry(DEFAULT_GEOMETRY)

        create_main_menu(self.root)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.notebook = Notebook(self.root)
        self.notebook.grid(column=0, row=0, sticky="nsew", padx=10, pady=10)

        self.server_tab = ServerTab(self.notebook)
        self.client_tab = ClientTab(self.notebook)

        self.notebook.add(
            self.server_tab.frame, text=t("Server (Local USB Devices)")
        )
        self.notebook.add(
            self.client_tab.frame, text=t("Client (Remote USB Devices)")
        )


def start_app():
    """Start app."""
    root = Tk()
    root.wm_title(t("USB/IP Manager"))
    root.geometry(DEFAULT_GEOMETRY)

    style = Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    bg_color = "#1e1e2e"
    fg_color = "#cdd6f4"
    input_bg = "#181825"
    button_bg = "#313244"
    button_active_bg = "#45475a"
    select_bg = "#89b4fa"
    select_fg = "#1e1e2e"
    border_color = "#313244"

    root.configure(bg=bg_color)

    class OptionAdder(Protocol):
        """Protocol for widgets that support adding options."""

        def option_add(
            self,
            pattern: str,
            value: str | int,
            priority: (
                int
                | Literal[
                    "widgetDefault",
                    "startupFile",
                    "userDefault",
                    "interactive",
                ]
                | None
            ) = ...,
        ) -> None:
            """Add an option to the Tkinter option database."""

    def configure_menu_options(adder: OptionAdder) -> None:
        adder.option_add("*Menu.background", bg_color)
        adder.option_add("*Menu.foreground", fg_color)
        adder.option_add("*Menu.activeBackground", button_active_bg)
        adder.option_add("*Menu.activeForeground", fg_color)
        adder.option_add("*Menu.activeBorderWidth", 0)
        adder.option_add("*Menu.borderWidth", 0)

    configure_menu_options(root)

    style.configure(
        ".",
        background=bg_color,
        foreground=fg_color,
        troughcolor=bg_color,
        selectbackground=select_bg,
        selectforeground=select_fg,
        fieldbackground=input_bg,
        borderwidth=1,
        bordercolor=border_color,
    )

    style.configure(
        "Treeview",
        background=input_bg,
        fieldbackground=input_bg,
        foreground=fg_color,
        borderwidth=0,
        rowheight=28,
    )
    style.map(
        "Treeview",
        background=[("selected", select_bg)],
        foreground=[("selected", select_fg)],
    )

    style.configure(
        "Treeview.Heading",
        background=button_bg,
        foreground=fg_color,
        borderwidth=1,
        bordercolor=border_color,
        relief="flat",
    )
    style.map("Treeview.Heading", background=[("active", button_active_bg)])

    style.configure(
        "TButton",
        background=button_bg,
        foreground=fg_color,
        borderwidth=0,
        focuscolor=bg_color,
        relief="flat",
        padding=5,
    )
    style.map(
        "TButton",
        background=[("active", button_active_bg), ("pressed", select_bg)],
        foreground=[("pressed", select_fg)],
    )

    style.configure(
        "TCheckbutton",
        background=bg_color,
        foreground=fg_color,
        focuscolor=bg_color,
    )
    style.map(
        "TCheckbutton",
        background=[("active", bg_color), ("pressed", bg_color)],
        foreground=[("active", fg_color)],
        indicatorcolor=[("selected", select_bg), ("pressed", select_bg)],
    )

    style.configure(
        "TEntry",
        fieldbackground=input_bg,
        foreground=fg_color,
        bordercolor=border_color,
        lightcolor=bg_color,
        darkcolor=bg_color,
        padding=4,
        insertcolor=fg_color,
    )

    style.configure(
        "TNotebook",
        background=bg_color,
        borderwidth=0,
    )
    style.configure(
        "TNotebook.Tab",
        background=button_bg,
        foreground=fg_color,
        padding=[10, 5],
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", bg_color)],
        foreground=[("selected", select_bg)],
    )

    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(family="Ubuntu", size=11, weight="bold")

    heading_font = tkfont.nametofont("TkHeadingFont")
    heading_font.configure(family="Ubuntu", size=12, weight="bold")

    text_font = tkfont.nametofont("TkTextFont")
    text_font.configure(family="Ubuntu", size=11, weight="bold")

    style.configure(".", font="TkDefaultFont")
    style.configure("Treeview", font=("Ubuntu", 11, "bold"))
    style.configure("Treeview.Heading", font=("Ubuntu", 12, "bold"))

    loading_label = Label(
        root,
        text="Loading...\n--------------\nChargement...",
        font=("Sans Serif", 24),
    )
    loading_label.pack(expand=True)
    root.update()

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

    loading_label.destroy()
    UsbIpGui(root)
    root.mainloop()
