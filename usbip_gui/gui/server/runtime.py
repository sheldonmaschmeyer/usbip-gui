"""Server process lifecycle management for USB/IP and cloudflared."""

import os
import subprocess
import sys
import threading

from usbip_gui.common import (
    elevate_command,
    resolve_cloudflared_executable,
    tunnel_state,
)


# pylint: disable=too-many-arguments,too-many-positional-arguments
def init_usbip_server(
    port: int = 3240,
    secure: bool = False,
    password: str = "",
    bind_host: str = "0.0.0.0",
    use_cloudflared: bool = False,
    cloudflared_token: str = "",
    cloudflared_path: str = "",
):
    """Initialize or restart local USB/IP and optional cloudflared tunnel."""
    if sys.platform != "win32":
        subprocess.run(elevate_command(["pkill", "usbipd"]), check=False)
        subprocess.run(["pkill", "-f", "ssl_tunnel.py server"], check=False)

    if tunnel_state.server_process:
        try:
            tunnel_state.server_process.terminate()
            tunnel_state.server_process.wait()
        except OSError:
            pass
        tunnel_state.server_process = None

    if tunnel_state.cloudflared_server_process:
        try:
            tunnel_state.cloudflared_server_process.terminate()
            tunnel_state.cloudflared_server_process.wait()
        except OSError:
            pass
        tunnel_state.cloudflared_server_process = None

    if use_cloudflared and cloudflared_token:
        cloudflared_exe = resolve_cloudflared_executable(cloudflared_path)

        def run_cf_server():
            with subprocess.Popen(
                [
                    cloudflared_exe,
                    "tunnel",
                    "run",
                    "--token",
                    cloudflared_token,
                ]
            ) as process:
                tunnel_state.cloudflared_server_process = process
                process.wait()
                if tunnel_state.cloudflared_server_process is process:
                    tunnel_state.cloudflared_server_process = None

        threading.Thread(target=run_cf_server, daemon=True).start()

    if secure:
        if sys.platform != "win32":
            target_port = port + 10000
            listen_port = port
            subprocess.run(
                elevate_command(
                    ["usbipd", "-D", "--tcp-port", str(target_port)]
                ),
                check=False,
            )
        else:
            target_port = 3240
            listen_port = 3241 if port == 3240 else port

        def run_tunnel():
            with subprocess.Popen(
                [
                    sys.executable,
                    os.path.join(
                        os.path.dirname(
                            os.path.dirname(os.path.dirname(__file__))
                        ),
                        "ssl_tunnel.py",
                    ),
                    "server",
                    "--listen-port",
                    str(listen_port),
                    "--target-port",
                    str(target_port),
                    "--bind-host",
                    bind_host,
                    "--password",
                    password,
                ]
            ) as process:
                tunnel_state.server_process = process
                process.wait()

        threading.Thread(target=run_tunnel, daemon=True).start()
    else:
        if sys.platform != "win32":
            subprocess.run(
                elevate_command(["usbipd", "-D", "--tcp-port", str(port)]),
                check=False,
            )
