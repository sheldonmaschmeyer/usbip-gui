"""Product detection module."""

import json
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Tuple

from PyQt6.QtCore import QObject, pyqtSignal

from usbip_gui.common import SortableTreeWidgetItem, run_elevated
from .heuristics import is_generic_manufacturer
from .usb_ids import get_device_description


def is_unknown_product(description: str) -> bool:
    """Return True when usbip only exposed an unknown product label."""
    normalized = description.strip().lower()
    return normalized == "unknown product" or normalized.startswith(
        "unknown product ("
    )


def extract_unknown_product_suffix(description: str) -> str:
    """Return the VID/PID suffix from an unknown-product label."""
    match = re.search(r"\(([^)]+)\)\s*$", description.strip())
    if match:
        return f" ({match.group(1)})"
    return ""


def usb_details_script_path() -> str:
    """Return the absolute path to the usb_details.py probe script."""
    return str(Path(__file__).parent / "usb_details.py")


def read_local_usb_descriptor_details(bus_id: str) -> Tuple[str, str]:
    """Read iManufacturer and iProduct for a local USB device."""
    cmd = [sys.executable, usb_details_script_path(), bus_id]
    if sys.platform == "win32":
        # ShellExecuteExW (used by run_elevated) cannot capture stdout,
        # and reading USB descriptors via pyusb does not require elevation
        # on Windows.
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        )
    else:
        result = run_elevated(cmd)
    if result.returncode != 0:
        details = str(result.stderr).strip() or str(result.stdout).strip()
        raise OSError(details or "Failed to read USB descriptor details.")

    payload_text = str(result.stdout).strip()
    if not payload_text:
        raise OSError("USB descriptor probe did not return any data.")

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise OSError("USB descriptor probe returned invalid data.") from exc

    error = str(payload.get("error", "")).strip()
    if error:
        raise OSError(error)

    manufacturer = str(payload.get("manufacturer", "")).strip()
    product = str(payload.get("product", "")).strip()
    return manufacturer, product


def read_windows_registry_usb_descriptor_details(
    vid_pid: str,
) -> Tuple[str, str]:
    """Read iManufacturer and iProduct from the Windows Registry."""
    if sys.platform != "win32" or not vid_pid or ":" not in vid_pid:
        return "", ""

    cmd = [sys.executable, usb_details_script_path(), "--vid-pid", vid_pid]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        return "", ""

    payload_text = str(result.stdout).strip()
    if not payload_text:
        return "", ""

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return "", ""

    error = str(payload.get("error", "")).strip()
    if error:
        return "", ""

    manufacturer = str(payload.get("manufacturer", "")).strip()
    product = str(payload.get("product", "")).strip()
    return manufacturer, product


class ItemUpdater(QObject):
    """Thread-safe bridge for updating QTreeWidgetItem text from a worker
    thread.

    Emitting ``update`` from a non-GUI thread causes Qt to automatically
    deliver the signal via a QueuedConnection to the GUI thread, so
    ``apply_text`` is always called safely on the main thread.
    """

    update: pyqtSignal = pyqtSignal(object, int, str)

    def apply_text(self, item: object, col: int, text: str) -> None:
        """Set item column text; always invoked in the GUI thread."""
        if isinstance(item, SortableTreeWidgetItem):
            item.setText(col, text)


# pylint: disable=too-many-arguments,too-many-positional-arguments
def enrich_device_item(
    item_updater: ItemUpdater,
    item: SortableTreeWidgetItem,
    bus_id: str,
    on_windows: bool,
    vid_pid: str = "",
    original_description: str = "",
    manufacturer_col: int = 2,
    description_col: int = 3,
) -> None:
    """Look up USB descriptor strings for *item* in a background thread."""

    def _do_lookup() -> None:
        try:
            manufacturer, product = read_local_usb_descriptor_details(bus_id)
        except OSError:
            manufacturer, product = "", ""

        if on_windows:
            db_mfg, db_prod = get_device_description(vid_pid)
            if db_prod:
                product = db_prod
            if db_mfg:
                manufacturer = db_mfg

            if is_generic_manufacturer(manufacturer):
                first_word = original_description.split(" ")[0]
                if first_word.lower() not in (
                    "usb",
                    "generic",
                    "unknown",
                    "",
                ):
                    manufacturer = first_word

            if (
                original_description
                and manufacturer
                and original_description.startswith(manufacturer)
            ):
                product = original_description.split(",")[0].strip()
            elif not product:
                product = original_description

        else:
            # Linux: concat manufacturer and product
            product = " ".join(
                part for part in (manufacturer, product) if part
            ).strip()

        try:
            if manufacturer:
                item_updater.update.emit(item, manufacturer_col, manufacturer)
            if product:
                item_updater.update.emit(item, description_col, product)
        except RuntimeError:  # pragma: no cover
            pass

    threading.Thread(target=_do_lookup, daemon=True).start()


# pylint: disable=too-many-arguments,too-many-positional-arguments
def enrich_remote_device_item(
    item_updater: ItemUpdater,
    item: SortableTreeWidgetItem,
    vid_pid: str,
    original_manufacturer: str,
    manufacturer_col: int = 4,
    description_col: int = 5,
) -> None:
    """Look up USB descriptor strings for a remote device via registry."""
    if sys.platform != "win32" or not vid_pid:
        return

    def _do_lookup() -> None:
        reg_manufacturer, reg_product = (
            read_windows_registry_usb_descriptor_details(vid_pid)
        )

        db_mfg, db_prod = get_device_description(vid_pid)
        if db_prod:
            reg_product = db_prod
        if db_mfg:
            reg_manufacturer = db_mfg

        if not reg_manufacturer and not reg_product:
            return

        if is_generic_manufacturer(reg_manufacturer):
            # If the registry manufacturer is generic, use the
            # manufacturer from usbip
            reg_manufacturer = original_manufacturer.split(" ")[0]

        if (
            reg_product
            and reg_manufacturer
            and reg_product.startswith(reg_manufacturer)
        ):
            reg_product = reg_product.split(",", maxsplit=1)[0].strip()

        try:
            if reg_manufacturer:
                item_updater.update.emit(
                    item, manufacturer_col, reg_manufacturer.strip(",")
                )
            if reg_product:
                item_updater.update.emit(item, description_col, reg_product)
        except RuntimeError:  # pragma: no cover
            pass

    threading.Thread(target=_do_lookup, daemon=True).start()
