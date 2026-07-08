"""Common utilities, state management, and shared components for the GUI."""

import subprocess
import atexit
import tkinter as tk
from typing import Optional, Dict, Tuple
import gettext
from pathlib import Path

VERSION = "1.1.0"

USBIPD_PORT = 3240
DEFAULT_GEOMETRY = "1400x842"


def get_translator(domain: str):
    """Get translator."""
    _local_localedir = Path(__file__).parent.parent.parent / "share" / "locale"
    localedir = (
        str(_local_localedir)
        if _local_localedir.exists()
        else "/usr/local/share/locale/"
    )

    common_t = gettext.translation(
        "usbip-gui-common", localedir=localedir, fallback=True
    )

    if domain == "common":
        return common_t.gettext

    t = gettext.translation(
        f"usbip-gui-{domain}", localedir=localedir, fallback=True
    )
    t.add_fallback(common_t)
    return t.gettext


_ = get_translator("common")


class TunnelState:
    """Tunnelstate."""

    def __init__(self):
        """Initialize the class instance."""
        self.server_process: Optional[subprocess.Popen[bytes]] = None
        self.client_processes: Dict[
            Tuple[str, int], Tuple[int, subprocess.Popen[bytes], str]
        ] = {}


tunnel_state = TunnelState()


def cleanup_tunnels():
    """Cleanup tunnels."""
    if tunnel_state.server_process:
        try:
            tunnel_state.server_process.terminate()
        except OSError:
            pass
    for _port, proc, _pwd in tunnel_state.client_processes.values():
        try:
            proc.terminate()
        except OSError:
            pass


atexit.register(cleanup_tunnels)


class ToolTip:
    """Tooltip."""

    def __init__(self, widget: tk.Widget, text: str):
        """Initialize the class instance."""
        self.widget = widget
        self.text = text
        self.tooltip_window: Optional[tk.Toplevel] = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, _event: Optional[tk.Event] = None):
        """Show tooltip."""
        if self.tooltip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 20
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#313244",
            foreground="#cdd6f4",
            relief="solid",
            borderwidth=1,
            font=("Ubuntu", 10),
        )
        label.pack(ipadx=5, ipady=3)

    def hide_tooltip(self, _event: Optional[tk.Event] = None):
        """Hide tooltip."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
