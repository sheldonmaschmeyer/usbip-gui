"""Common utilities, state management, and shared components for the GUI."""

import subprocess
import atexit
import json
import os
import sys
import re
from pathlib import Path
from typing import Optional, Dict, Tuple, Callable, Union, List

from babel.core import Locale
from PyQt6.QtWidgets import QTreeWidgetItem, QTreeWidget

from usbip_gui.typings import connect_signal

VERSION = "1.3.0"

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
    """Get translator loading from JSON files to avoid compiling .mo files."""
    locales_dir = Path(__file__).parent.parent / "locales"

    # Determine current language using Babel
    lang = "en"
    loc = Locale.default()
    if loc and loc.language:
        lang = loc.language
        if loc.territory:
            lang = f"{loc.language}_{loc.territory}"

    def load_json(name: str, language_code: str) -> Dict[str, str]:
        base_lang = language_code.split("_")[0]

        path = locales_dir / base_lang / f"{name}.json"
        if not path.exists():
            path = locales_dir / "en" / f"{name}.json"

        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
        return {}

    common_translations = load_json("common", lang)
    domain_translations = load_json(domain, lang) if domain != "common" else {}

    def translate(message: str) -> str:
        if message in domain_translations and domain_translations[message]:
            return domain_translations[message]
        if message in common_translations and common_translations[message]:
            return common_translations[message]
        return message

    return translate


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
