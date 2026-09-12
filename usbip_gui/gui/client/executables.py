"""Client-side executable detection helpers."""

import os
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path


def resolve_usbip_client_executable() -> str:
    """Resolve the usbip client executable, with Windows install fallbacks."""
    if sys.platform != "win32":
        return "usbip"

    which_match = shutil.which("usbip.exe") or shutil.which("usbip")
    if which_match:
        return which_match

    candidate_paths: list[Path] = []
    for env_var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        base = os.environ.get(env_var)
        if base:
            candidate_paths.append(Path(base) / "USBip" / "usbip.exe")

    candidate_paths.extend(
        [
            Path("C:/Program Files/USBip/usbip.exe"),
            Path("C:/Program Files (x86)/USBip/usbip.exe"),
        ]
    )

    checked_paths: list[str] = []
    seen: set[str] = set()
    for candidate in candidate_paths:
        normalized = str(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        checked_paths.append(normalized)
        if candidate.exists():
            return normalized

    checked = "\n - ".join(checked_paths)
    raise FileNotFoundError(
        "usbip.exe was not found in PATH and was not found at:\n"
        f" - {checked}"
    )


_resolve_usbip_client_executable = resolve_usbip_client_executable


@lru_cache(maxsize=None)
def detect_windows_attach_bus_option(exe: str) -> str:
    """Detect whether this Windows usbip build expects --bus-id or --busid."""
    try:
        probe = subprocess.run(
            [exe, "attach", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        help_text = f"{probe.stdout}\n{probe.stderr}".lower()
    except OSError:
        help_text = ""

    if "--bus-id" in help_text:
        return "--bus-id"
    if "--busid" in help_text:
        return "--busid"
    return "--busid"


_detect_windows_attach_bus_option = detect_windows_attach_bus_option
