"""Client-side USB/IP command execution."""

import subprocess
import sys
from typing import List, Tuple

from usbip_gui.common import elevate_command, run_elevated

from .executables import (
    detect_windows_attach_bus_option,
    resolve_usbip_client_executable,
)
from .parsing import parse_attached_list, parse_remote_list
from .tunnels import (
    get_or_create_client_tunnel,
    get_or_create_cloudflared_client_tunnel,
    reset_client_tunnels_for_host,
)

_resolve_usbip_client_executable = resolve_usbip_client_executable
_detect_windows_attach_bus_option = detect_windows_attach_bus_option
_reset_client_tunnels_for_host = reset_client_tunnels_for_host


# pylint: disable=too-many-arguments,too-many-positional-arguments
def list_remote_usb(
    server_ip: str,
    port: int = 3240,
    secure: bool = False,
    password: str = "",
    use_cloudflared: bool = False,
    cloudflared_hostname: str = "",
    cloudflared_path: str = "",
    service_token_id: str = "",
    service_token_secret: str = "",
) -> List[Tuple[str, str, str, str]]:
    """List remote usb."""
    if use_cloudflared:
        cf_host = cloudflared_hostname or server_ip
        cf_ip, cf_port = get_or_create_cloudflared_client_tunnel(
            cf_host,
            cloudflared_path,
            service_token_id=service_token_id,
            service_token_secret=service_token_secret,
        )
        if not cf_ip:
            return []
        server_ip, port = cf_ip, cf_port

    target_ip, target_port = get_or_create_client_tunnel(
        server_ip, port, secure, password
    )
    if not target_ip:
        return []

    cmd = [
        _resolve_usbip_client_executable(),
        "--tcp-port",
        str(target_port),
        "list",
        "--remote=" + target_ip,
    ]
    if sys.platform != "win32":
        cmd = elevate_command(cmd)

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return parse_remote_list(result.stdout)


def list_attached_usb() -> List[Tuple[str, int, str, str, str, str]]:
    """List attached usb."""
    cmd = [_resolve_usbip_client_executable(), "port"]
    if sys.platform != "win32":
        cmd = elevate_command(cmd)

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return parse_attached_list(result.stdout)


# pylint: disable=too-many-arguments,too-many-positional-arguments
def attach_remote_usb(
    server_ip: str,
    bus_id: str,
    port: int = 3240,
    secure: bool = False,
    password: str = "",
    use_cloudflared: bool = False,
    cloudflared_hostname: str = "",
    cloudflared_path: str = "",
    service_token_id: str = "",
    service_token_secret: str = "",
):
    """Attach remote usb."""

    def _run_attach(
        target_ip: str, target_port: int
    ) -> subprocess.CompletedProcess[str]:
        exe = _resolve_usbip_client_executable()
        cmd = [
            exe,
            "--tcp-port",
            str(target_port),
            "attach",
            "--remote=" + target_ip,
        ]
        if sys.platform == "win32":
            bus_opt = _detect_windows_attach_bus_option(exe)
            cmd.append(f"{bus_opt}={bus_id}")
        else:
            cmd.append("--busid=" + bus_id)

        return run_elevated(cmd)

    if use_cloudflared:
        cf_host = cloudflared_hostname or server_ip
        cf_ip, cf_port = get_or_create_cloudflared_client_tunnel(
            cf_host,
            cloudflared_path,
            service_token_id=service_token_id,
            service_token_secret=service_token_secret,
        )
        if not cf_ip:
            return subprocess.CompletedProcess(
                args=[], returncode=-1, stdout="", stderr=""
            )
        server_ip, port = cf_ip, cf_port

    target_ip, target_port = get_or_create_client_tunnel(
        server_ip, port, secure, password
    )
    if not target_ip:
        return subprocess.CompletedProcess(
            args=[], returncode=-1, stdout="", stderr=""
        )

    result = _run_attach(target_ip, target_port)
    if secure and result.returncode != 0:
        _reset_client_tunnels_for_host(server_ip)
        target_ip, target_port = get_or_create_client_tunnel(
            server_ip, port, secure, password
        )
        if not target_ip:
            return result
        result = _run_attach(target_ip, target_port)

    if sys.platform == "win32" and result.returncode != 0:
        diag_cmd = [
            _resolve_usbip_client_executable(),
            "--tcp-port",
            str(target_port),
            "attach",
            "--remote=" + target_ip,
            "--busid=" + bus_id,
        ]
        diag = subprocess.run(
            diag_cmd, capture_output=True, text=True, check=False
        )
        if (diag.stderr and diag.stderr.strip()) or (
            diag.stdout and diag.stdout.strip()
        ):
            return subprocess.CompletedProcess(
                args=result.args,
                returncode=result.returncode,
                stdout=diag.stdout,
                stderr=diag.stderr or diag.stdout,
            )

    return result


def detach_remote_usb(port: int):
    """Detach remote usb."""
    cmd = [
        _resolve_usbip_client_executable(),
        "detach",
        "--port=" + str(port),
    ]
    run_elevated(cmd)
