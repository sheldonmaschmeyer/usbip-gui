"""Main graphical user interface implementation and window management."""

from tkinter import Tk, BooleanVar, StringVar, TclError
from tkinter.ttk import Notebook, Label, Style
import tkinter.font as tkfont
import os
import subprocess
import sys
from typing import Protocol, Literal

from .common import DEFAULT_GEOMETRY, get_translator, load_config, save_config
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

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.notebook = Notebook(self.root)
        self.notebook.grid(column=0, row=0, sticky="nsew", padx=10, pady=10)

        self.server_tab = ServerTab(self.notebook)
        self.client_tab = ClientTab(self.notebook)

        config = load_config()
        self.show_server_var = BooleanVar(
            value=bool(config.get("show_server", True))
        )
        self.show_client_var = BooleanVar(
            value=bool(config.get("show_client", True))
        )
        self.default_tab_var = StringVar(
            value=str(config.get("default_tab", "server"))
        )

        self.update_tabs()
        self.apply_default_tab()

        create_main_menu(self)
        
        from . import common
        self.base_scale = common.APP_SCALE
        self.zoom_level = 1.0
        
        self.root.bind("<Control-plus>", self.zoom_in)
        self.root.bind("<Control-equal>", self.zoom_in)
        self.root.bind("<Control-KP_Add>", self.zoom_in)
        self.root.bind("<Control-minus>", self.zoom_out)
        self.root.bind("<Control-KP_Subtract>", self.zoom_out)
        self.root.bind("<Control-0>", self.zoom_reset)
        
        Style(self.root).configure("TScrollbar", width=int(15 * self.base_scale), arrowsize=int(15 * self.base_scale))

    def apply_zoom(self, zoom: float):
        self.zoom_level = zoom
        total_scale = self.base_scale * self.zoom_level
        
        from . import common
        common.APP_SCALE = total_scale
        
        base_width, base_height = map(int, common.DEFAULT_GEOMETRY.split('x'))
        scaled_w = int(base_width * total_scale)
        scaled_h = int(base_height * total_scale)
        self.root.geometry(f"{scaled_w}x{scaled_h}")

        style = Style(self.root)
        style.configure("Treeview", rowheight=int(28 * total_scale))
        style.configure("TButton", padding=int(5 * total_scale))
        style.configure("TCheckbutton", indicatorsize=int(16 * total_scale), indicatormargin=int(4 * total_scale))
        style.configure("TEntry", padding=int(4 * total_scale))
        style.configure("TNotebook.Tab", padding=[int(10 * total_scale), int(5 * total_scale)])
        style.configure("TScrollbar", width=int(15 * total_scale), arrowsize=int(15 * total_scale))

        tkfont.nametofont("TkDefaultFont").configure(size=int(-15 * total_scale))
        tkfont.nametofont("TkHeadingFont").configure(size=int(-16 * total_scale))
        tkfont.nametofont("TkTextFont").configure(size=int(-15 * total_scale))
        style.configure("Treeview", font=("sans-serif", int(-15 * total_scale), "bold"))
        style.configure("Treeview.Heading", font=("sans-serif", int(-16 * total_scale), "bold"))
        
        self.root.option_add("*Menu.font", f"sans-serif {int(-15 * total_scale)} bold")
        from .menu import create_main_menu
        create_main_menu(self)

    def zoom_in(self, event=None):
        self.apply_zoom(self.zoom_level + 0.25)
        
    def zoom_out(self, event=None):
        self.apply_zoom(max(0.5, self.zoom_level - 0.25))
        
    def zoom_reset(self, event=None):
        self.apply_zoom(1.0)

    def update_tabs(self) -> None:
        """Update visible tabs based on settings."""
        current_tab = None
        try:
            current_tab = self.notebook.select()  # type: ignore
        except TclError:
            pass

        # Hide both to ensure correct order when re-adding
        try:
            self.notebook.forget(self.server_tab.frame)  # type: ignore
        except TclError:
            pass
        try:
            self.notebook.forget(self.client_tab.frame)  # type: ignore
        except TclError:
            pass

        if self.show_server_var.get():
            self.notebook.add(
                self.server_tab.frame, text=t("Server (Local USB Devices)")
            )
        if self.show_client_var.get():
            self.notebook.add(
                self.client_tab.frame, text=t("Client (Remote USB Devices)")
            )

        try:
            if current_tab in self.notebook.tabs():  # type: ignore
                self.notebook.select(current_tab)  # type: ignore
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        self.save_settings()

    def apply_default_tab(self) -> None:
        """Select default tab."""
        if (
            self.default_tab_var.get() == "server"
            and self.show_server_var.get()
        ):
            self.notebook.select(self.server_tab.frame)  # type: ignore
        elif (
            self.default_tab_var.get() == "client"
            and self.show_client_var.get()
        ):
            self.notebook.select(self.client_tab.frame)  # type: ignore

    def save_settings(self) -> None:
        """Save settings to config file."""
        config = load_config()
        config["show_server"] = self.show_server_var.get()
        config["show_client"] = self.show_client_var.get()
        config["default_tab"] = self.default_tab_var.get()
        save_config(config)


def enable_4k_scaling():
    """Enable 4K scaling."""
    # 1. Tell Windows/macOS to use native monitor resolution (DPI Aware)
    if sys.platform.startswith("win"):
        import ctypes
        try:
            # For Windows 8.1 and Windows 10/11
            ctypes.windll.shcore.SetProcessDpiAwareness(2) # 2 = Process_Per_Monitor_DPI_Aware
        except Exception:
            # Fallback for Windows 7/8
            ctypes.windll.user32.SetProcessDPIAware()

    # 2. Initialize a temporary root to read system metrics
    root = Tk()
    
    # Calculate the system scaling factor relative to baseline (72 DPI)
    # A standard 4K screen with 150% Windows scaling will report roughly 1.5 - 2.0
    scaling_factor = root.winfo_fpixels('1i') / 72
    
    # Apply scaling factor to Tkinter's font and widget engine
    root.tk.call('tk', 'scaling', scaling_factor)
    
    return root, scaling_factor


def start_app():
    """Start app."""
    root, app_scale = enable_4k_scaling()
    from . import common
    common.APP_SCALE = app_scale
    root.wm_title(t("USB/IP Manager"))
    
    base_width, base_height = map(int, DEFAULT_GEOMETRY.split('x'))
    scaled_w = int(base_width * app_scale)
    scaled_h = int(base_height * app_scale)
    root.geometry(f"{scaled_w}x{scaled_h}")

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
        adder.option_add("*Menu.font", f"sans-serif {int(-15 * app_scale)} bold")

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
        "TScrollbar",
        background=button_bg,
        troughcolor=bg_color,
        bordercolor=bg_color,
        arrowcolor=fg_color,
    )
    style.map(
        "TScrollbar",
        background=[("active", button_active_bg), ("pressed", select_bg)],
    )

    style.configure(
        "Treeview",
        background=input_bg,
        fieldbackground=input_bg,
        foreground=fg_color,
        borderwidth=0,
        rowheight=int(28 * app_scale),
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
        padding=int(5 * app_scale),
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
        indicatorsize=int(16 * app_scale),
        indicatormargin=int(4 * app_scale),
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
        padding=int(4 * app_scale),
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
        padding=[int(10 * app_scale), int(5 * app_scale)],
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", bg_color)],
        foreground=[("selected", select_bg)],
    )

    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(family="sans-serif", size=int(-15 * app_scale), weight="bold")

    heading_font = tkfont.nametofont("TkHeadingFont")
    heading_font.configure(family="sans-serif", size=int(-16 * app_scale), weight="bold")

    text_font = tkfont.nametofont("TkTextFont")
    text_font.configure(family="sans-serif", size=int(-15 * app_scale), weight="bold")

    style.configure(".", font="TkDefaultFont")
    style.configure("Treeview", font=("sans-serif", int(-15 * app_scale), "bold"))
    style.configure("Treeview.Heading", font=("sans-serif", int(-16 * app_scale), "bold"))

    loading_label = Label(
        root,
        text="Loading...\n--------------\nChargement...",
        font=("sans-serif", int(-32 * app_scale)),
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
