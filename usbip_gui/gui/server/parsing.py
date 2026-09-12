"""USB listing and bind/unbind helpers for the server tab."""

import os
import re
import subprocess
import sys
from typing import List, Tuple

from usbip_gui.common import get_translator, run_elevated
from usbip_gui.product_detection import extract_unknown_product_suffix

t = get_translator("server")


def local_device_columns() -> List[str]:
    """Column headers for the local device tree, for the active language."""
    cols = [
        t("Bus ID"),
        t("State"),
        t("Manufacturer"),
        t("Description"),
        t("VID : PID"),
    ]
    if sys.platform == "win32":
        cols.insert(4, t("Windows Driver"))
    return cols


def parse_local_list(text: str) -> List[Tuple[str, str, str, str, str]]:
    """Parse `usbip list --local` output on Linux."""
    if not text or not text.strip():
        return []

    rows: List[Tuple[str, str, str, str, str]] = []
    devices = text.strip().split("\n\n")
    for device in devices:
        lines = device.strip().split("\n")
        if len(lines) < 2:
            continue
        bus_info = lines[0].split(" ")
        man_info = lines[1].split(":")

        bus_id = bus_info[2] if len(bus_info) > 2 else ""
        vid_pid = ""
        vid_match = re.search(r"\(([^)]+)\)", lines[0])
        if vid_match:
            vid_pid = vid_match.group(1)

        manufacturer = man_info[0].strip() if len(man_info) > 0 else ""
        description = (
            ":".join(man_info[1:]).strip() if len(man_info) > 1 else ""
        )

        # Strip the redundant suffix if it's in the description.
        suffix_match = extract_unknown_product_suffix(description)
        if suffix_match:
            description = description[: -len(suffix_match)].strip()

        state = t("Unbound")
        if bus_id:
            driver_path = f"/sys/bus/usb/devices/{bus_id}/driver"
            if os.path.exists(driver_path) and os.path.islink(driver_path):
                driver = os.path.basename(os.readlink(driver_path))
                if driver == "usbip-host":
                    state = t("Bound")

        rows.append((bus_id, state, manufacturer, description, vid_pid))
    return rows


def parse_windows_local_list(
    text: str,
) -> List[Tuple[str, str, str, str, str]]:
    """Parse `usbipd list` output on Windows."""
    if not text or not text.strip():
        return []

    rows: List[Tuple[str, str, str, str, str]] = []
    for line in text.strip().split("\n"):
        match = re.match(
            r"^(\d+-\d+(?:\.\d+)*)\s+"
            r"([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\s+"
            r"(.+?)\s{2,}(Not shared|Shared|Attached.*)$",
            line.strip(),
        )
        if match:
            bus_id, vid_pid, device, state = match.groups()
            gui_state = (
                t("Bound")
                if "Shared" in state or "Attached" in state
                else t("Unbound")
            )
            rows.append((bus_id, gui_state, "", device, vid_pid))
    return rows


def list_local_usb() -> List[Tuple[str, str, str, str, str]]:
    """List local USB devices with state and descriptor metadata."""
    if sys.platform == "win32":
        result = subprocess.run(
            ["usbipd", "list"], capture_output=True, text=True, check=False
        )
        return parse_windows_local_list(result.stdout)

    result = run_elevated(["usbip", "list", "--local"])
    return parse_local_list(result.stdout)


def bind_local_usb(bus_id: str):
    """Bind a local USB device for remote export."""
    if sys.platform == "win32":
        cmd = ["usbipd", "bind", "--busid", bus_id]
    else:
        cmd = ["usbip", "bind", "--busid=" + bus_id]

    print(f"DEBUG: Executing elevated command: {' '.join(cmd)}", flush=True)
    result = run_elevated(cmd)
    if result.stdout:
        print(f"stdout: {result.stdout}", flush=True)
    if result.stderr:
        print(f"stderr: {result.stderr}", flush=True)
    print(
        f"DEBUG: Command finished with exit code {result.returncode}",
        flush=True,
    )
    return result


def unbind_local_usb(bus_id: str):
    """Unbind a local USB device from remote export."""
    if sys.platform == "win32":
        cmd = ["usbipd", "unbind", "--busid", bus_id]
    else:
        cmd = ["usbip", "unbind", "--busid=" + bus_id]

    print(f"DEBUG: Executing elevated command: {' '.join(cmd)}", flush=True)
    result = run_elevated(cmd)
    if result.stdout:
        print(f"stdout: {result.stdout}", flush=True)
    if result.stderr:
        print(f"stderr: {result.stderr}", flush=True)
    print(
        f"DEBUG: Command finished with exit code {result.returncode}",
        flush=True,
    )
    return result
