"""Common utilities, state management, and shared components for the GUI."""

import subprocess
import atexit
from typing import Optional, Dict, Tuple, Callable, Union, List
import gettext
from pathlib import Path
import json
import os
import sys
import re
from PyQt6.QtWidgets import QTreeWidgetItem, QTreeWidget
from usbip_gui.typings import connect_signal

VERSION = "1.2.0"

USBIPD_PORT = 3240
DEFAULT_GEOMETRY = "900x842"

JsonValue = Union[
    str, int, float, bool, None, Dict[str, "JsonValue"], List["JsonValue"]
]
JsonDict = Dict[str, JsonValue]


def set_min_column_widths(tree: QTreeWidget, min_widths: List[int]) -> None:
    """Enforce a minimum pixel width per column."""
    header = tree.header()
    if not header:
        return

    def enforce_min(index: int, _old: int, new: int) -> None:
        if index < len(min_widths) and new < min_widths[index]:
            if header := tree.header():
                header.resizeSection(index, min_widths[index])

    connect_signal(header.sectionResized, enforce_min)

    # Apply immediately
    for i, w in enumerate(min_widths):
        if tree.columnWidth(i) < w:
            tree.setColumnWidth(i, w)


def get_config_dir() -> Path:
    """Get the configuration directory."""
    if sys.platform == "win32":
        base_dir = os.environ.get("APPDATA") or (
            Path.home() / "AppData" / "Roaming"
        )
    else:
        base_dir = os.environ.get("XDG_CONFIG_HOME") or (
            Path.home() / ".config"
        )

    config_dir = Path(base_dir) / "usbip-gui"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "settings.json"


def load_config() -> JsonDict:
    """Load configuration from file."""
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # pylint: disable=broad-exception-caught
            pass
    return {}


def save_config(config: JsonDict) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception:  # pylint: disable=broad-exception-caught
        pass


def get_translator(domain: str) -> Callable[[str], str]:
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

    translator = gettext.translation(
        f"usbip-gui-{domain}", localedir=localedir, fallback=True
    )
    translator.add_fallback(common_t)
    return translator.gettext


t = get_translator("common")


class TunnelState:
    """Tunnelstate."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        self.server_process: Optional[subprocess.Popen[bytes]] = None
        self.client_processes: Dict[
            Tuple[str, int], Tuple[int, subprocess.Popen[bytes], str]
        ] = {}


tunnel_state = TunnelState()


def cleanup_tunnels() -> None:
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


class SortableTreeWidgetItem(QTreeWidgetItem):
    """Tree widget item that supports natural sorting."""

    def __lt__(self, other: "QTreeWidgetItem") -> bool:
        tree = self.treeWidget()
        if not tree:
            return super().__lt__(other)

        column = tree.sortColumn()
        text1 = self.text(column)
        text2 = other.text(column)

        def natural_sort_key(s: str) -> List[Union[int, str]]:
            return [
                int(text) if text.isdigit() else text.lower()
                for text in re.split(r"(\d+)", s)
            ]

        try:
            return natural_sort_key(text1) < natural_sort_key(text2)
        except TypeError:
            return super().__lt__(other)
