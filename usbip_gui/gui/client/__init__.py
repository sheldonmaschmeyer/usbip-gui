"""Client tab package exports."""

import hashlib
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import threading
import time

from PyQt6.QtWidgets import QMessageBox

from usbip_gui.common import run_elevated, tunnel_state

from .executables import (
    detect_windows_attach_bus_option,
    resolve_usbip_client_executable,
)
from .operations import (
    attach_remote_usb,
    detach_remote_usb,
    list_attached_usb,
    list_remote_usb,
)
from .parsing import device_columns, parse_attached_list, parse_remote_list
from .tab import ClientTab
from .tunnels import (
    get_or_create_client_tunnel,
    get_or_create_cloudflared_client_tunnel,
    reset_client_tunnels_for_host,
    secure_port_candidates,
)


_resolve_usbip_client_executable = resolve_usbip_client_executable
_reset_client_tunnels_for_host = reset_client_tunnels_for_host
_detect_windows_attach_bus_option = detect_windows_attach_bus_option
_secure_port_candidates = secure_port_candidates


__patch_compat_exports__ = (
    hashlib,
    os,
    Path,
    shutil,
    socket,
    ssl,
    subprocess,
    sys,
    threading,
    time,
    QMessageBox,
    run_elevated,
    tunnel_state,
)

__all__ = [
    "ClientTab",
    "device_columns",
    "parse_remote_list",
    "parse_attached_list",
    "resolve_usbip_client_executable",
    "detect_windows_attach_bus_option",
    "get_or_create_client_tunnel",
    "get_or_create_cloudflared_client_tunnel",
    "reset_client_tunnels_for_host",
    "secure_port_candidates",
    "list_remote_usb",
    "list_attached_usb",
    "attach_remote_usb",
    "detach_remote_usb",
    "_resolve_usbip_client_executable",
    "_secure_port_candidates",
    "_reset_client_tunnels_for_host",
    "_detect_windows_attach_bus_option",
]
