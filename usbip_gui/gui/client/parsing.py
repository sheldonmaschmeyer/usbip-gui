"""Client-side parsing helpers for remote and attached USB lists."""

import re
import sys
from typing import List, Tuple
from urllib.parse import urlparse

from usbip_gui.common import USBIPD_PORT, get_translator
from usbip_gui.product_detection import is_unknown_product

t = get_translator("client")


def device_columns() -> List[str]:
    """Column headers for the remote device tree, for the active language."""
    # pylint: disable=duplicate-code
    cols = [
        t("Host"),
        t("Port"),
        t("Bus ID"),
        t("State"),
        t("Manufacturer"),
        t("Description"),
        t("VID : PID"),
    ]
    if sys.platform == "win32":
        cols.insert(6, t("Windows Driver"))
    return cols


def parse_remote_list(text: str) -> List[Tuple[str, str, str, str]]:
    """Parse remote list."""
    if "no exportable devices found on" in text:
        return []

    rows: List[Tuple[str, str, str, str]] = []
    busid_regex = re.compile("^\\d+-\\d+$|^\\d+-\\d+\\.\\d+$")
    lines = text.strip().split("\n")
    for line in lines:
        vals = line.strip().split(":")
        if len(vals) < 4:
            continue
        match = busid_regex.match(vals[0].strip())
        if not match:
            continue

        bus_id = vals[0].strip()
        manufacturer = vals[1].strip()
        description = vals[2].strip() + ":" + vals[3].strip()

        vid_pid = ""
        vid_match = re.search(r"\(([^)]+)\)", description)
        if vid_match:
            vid_pid = vid_match.group(1)
            description = description[: -len(vid_match.group(0))].strip()

        if sys.platform == "win32" and is_unknown_product(description):
            original_desc = manufacturer
            first_word = original_desc.split(" ")[0]
            if first_word.lower() not in ("usb", "generic", "unknown", ""):
                manufacturer = first_word
            else:
                manufacturer = ""
            description = original_desc.split(",")[0].strip()

        rows.append((bus_id, vid_pid, manufacturer, description))
    return rows


def parse_attached_list(
    text: str,
) -> List[Tuple[str, int, str, str, str, str]]:
    """Parse attached list."""
    rows: List[Tuple[str, int, str, str, str, str]] = []
    lines = text.strip().split("\n")
    for i, line in enumerate(lines):
        if "Port " not in line:
            continue

        port = int(line.strip().split(":")[0].replace("Port ", ""))
        info_line = lines[i + 1]
        busid_line = lines[i + 2]

        info = info_line.strip().split(":")
        manufacturer = info[0].strip()
        description = info[1].strip() + ":" + info[2].strip()

        vid_pid = ""
        vid_match = re.search(r"\(([^)]+)\)", description)
        if vid_match:
            vid_pid = vid_match.group(1)
            description = description[: -len(vid_match.group(0))].strip()

        if sys.platform == "win32" and is_unknown_product(description):
            original_desc = manufacturer
            first_word = original_desc.split(" ")[0]
            if first_word.lower() not in ("usb", "generic", "unknown", ""):
                manufacturer = first_word
            else:
                manufacturer = ""
            description = original_desc.split(",")[0].strip()

        businfo = busid_line.strip().split("->")
        bus_id = businfo[0].strip()
        host = urlparse(businfo[1].strip())[1]
        rows.append((host, port, bus_id, vid_pid, manufacturer, description))
    return rows


__all__ = [
    "device_columns",
    "parse_remote_list",
    "parse_attached_list",
    "USBIPD_PORT",
]
