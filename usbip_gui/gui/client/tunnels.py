"""Client-side secure tunnel and Cloudflare tunnel management."""

import hashlib
import json
import os
import random
import socket
import ssl
import subprocess
import sys
import threading
import time
from typing import Tuple

from PyQt6.QtWidgets import QMessageBox

from usbip_gui.common import (
    USBIPD_PORT,
    get_config_dir,
    get_translator,
    resolve_cloudflared_executable,
    tunnel_state,
)

t = get_translator("client")


def secure_port_candidates(port: int) -> list[int]:
    """Return secure-port candidates, including Windows default fallback."""
    if sys.platform == "win32" and port == USBIPD_PORT:
        return [port, port + 1]
    return [port]


_secure_port_candidates = secure_port_candidates


def reset_client_tunnels_for_host(host: str) -> None:
    """Terminate cached client tunnel processes for a given host."""
    keys_to_reset = [
        key for key in tunnel_state.client_processes if key[0] == host
    ]
    for key in keys_to_reset:
        _local_port, proc, _password = tunnel_state.client_processes.pop(key)
        if proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass


_reset_client_tunnels_for_host = reset_client_tunnels_for_host


def _format_fingerprint(cert_der: bytes) -> str:
    fingerprint = hashlib.sha256(cert_der).hexdigest().upper()
    fingerprint_iter = iter(fingerprint)
    return ":".join(a + b for a, b in zip(fingerprint_iter, fingerprint_iter))


def get_or_create_client_tunnel(
    host: str, port: int, secure: bool, password: str
) -> Tuple[str, int]:
    # pylint: disable=too-many-statements
    """Get or create client tunnel."""
    if not secure:
        return host, port

    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    fingerprint = ""
    selected_secure_port: int | None = None
    last_error: OSError | ValueError | None = None

    for candidate_port in secure_port_candidates(port):
        try:
            with socket.create_connection((host, candidate_port)) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)

            if not cert_der:
                raise ValueError("No certificate provided by server")

            fingerprint = _format_fingerprint(cert_der)
            known_hosts_path = get_config_dir() / "known_hosts.json"
            known_hosts = {}
            if os.path.exists(known_hosts_path):
                with open(known_hosts_path, "r", encoding="utf-8") as file_obj:
                    known_hosts = json.load(file_obj)

            host_key = f"{host}:{candidate_port}"
            if (
                host_key not in known_hosts
                or known_hosts[host_key] != fingerprint
            ):
                msg = t("cert_fingerprint_msg").format(fingerprint)
                reply = QMessageBox.question(
                    None,
                    t("Certificate Check"),
                    msg,
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    known_hosts[host_key] = fingerprint
                    os.makedirs(known_hosts_path.parent, exist_ok=True)
                    with open(
                        known_hosts_path, "w", encoding="utf-8"
                    ) as file_obj:
                        json.dump(known_hosts, file_obj)
                else:
                    return "", 0

            if not password:
                QMessageBox.critical(
                    None,
                    t("Error"),
                    t("Password required for secure connection"),
                )
                return "", 0

            with socket.create_connection((host, candidate_port)) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    test_cert_der = ssock.getpeercert(binary_form=True)
                    if test_cert_der:
                        test_fp = _format_fingerprint(test_cert_der)
                        if test_fp != fingerprint:
                            raise ValueError(
                                "Fingerprint mismatch during auth check"
                            )

                    pwd_bytes = password.encode("utf-8")
                    pwd_len = len(pwd_bytes)
                    ssock.sendall(
                        pwd_len.to_bytes(4, byteorder="big") + pwd_bytes
                    )

                    response = ssock.recv(1)
                    if response != b"\x01":
                        QMessageBox.critical(
                            None, t("Error"), t("auth_failed_msg")
                        )
                        return "", 0

            selected_secure_port = candidate_port
            break

        except (OSError, ValueError) as error:
            last_error = error
            continue

    if selected_secure_port is None:
        details = f"Failed to check certificate: {last_error}"
        if secure and getattr(last_error, "winerror", None) == 10054:
            details += (
                "\n\nThe remote host closed the connection during TLS setup. "
                "Verify that the server is running in secure mode on this "
                "port and that client/server passwords match."
            )
            if sys.platform == "win32" and port == USBIPD_PORT:
                details += (
                    "\n\nTip: Windows secure mode may listen on port 3241 "
                    "while usbipd stays on 3240."
                )
        QMessageBox.critical(None, t("Error"), t(details))
        return "", 0

    key = (host, selected_secure_port)
    if key in tunnel_state.client_processes:
        local_port, proc, cached_password = tunnel_state.client_processes[key]
        if proc.poll() is None:
            if cached_password == password:
                return "127.0.0.1", local_port
            tunnel_state.client_processes.pop(key)
            proc.kill()

    local_port = random.randint(40000, 50000)
    # Long-lived child process is intentionally kept for active tunnel reuse.
    # pylint: disable=consider-using-with
    proc = subprocess.Popen(
        [
            sys.executable,
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "ssl_tunnel.py",
            ),
            "client",
            "--listen-port",
            str(local_port),
            "--remote-host",
            host,
            "--remote-port",
            str(selected_secure_port),
            "--password",
            password,
            "--fingerprint",
            fingerprint,
        ]
    )
    tunnel_state.client_processes[key] = (local_port, proc, password)

    def watch_tunnel() -> None:
        proc.wait()
        current = tunnel_state.client_processes.get(key)
        if current and current[1] is proc:
            tunnel_state.client_processes.pop(key, None)

    threading.Thread(target=watch_tunnel, daemon=True).start()

    time.sleep(1)
    return "127.0.0.1", local_port


def get_or_create_cloudflared_client_tunnel(
    hostname: str,
    custom_path: str = "",
    service_token_id: str = "",
    service_token_secret: str = "",
) -> Tuple[str, int]:
    """Get or create cloudflared access tcp tunnel on the client."""
    cache_key = (
        f"{hostname}:{service_token_id}" if service_token_id else hostname
    )
    if cache_key in tunnel_state.cloudflared_client_processes:
        local_port, proc = tunnel_state.cloudflared_client_processes[cache_key]
        if proc.poll() is None:
            return "127.0.0.1", local_port
        tunnel_state.cloudflared_client_processes.pop(cache_key, None)

    cloudflared_exe = resolve_cloudflared_executable(custom_path)
    local_port = random.randint(40000, 50000)

    cmd = [
        cloudflared_exe,
        "access",
        "tcp",
        "--hostname",
        hostname,
        "--url",
        f"127.0.0.1:{local_port}",
    ]
    if service_token_id and service_token_secret:
        cmd.extend(
            [
                "--service-token-id",
                service_token_id,
                "--service-token-secret",
                service_token_secret,
            ]
        )

    # Long-lived child process is intentionally kept for active tunnel reuse.
    # pylint: disable=consider-using-with
    proc = subprocess.Popen(cmd)
    tunnel_state.cloudflared_client_processes[cache_key] = (local_port, proc)

    def watch_cf_tunnel() -> None:
        proc.wait()
        current = tunnel_state.cloudflared_client_processes.get(cache_key)
        if current and current[1] is proc:
            tunnel_state.cloudflared_client_processes.pop(cache_key, None)

    threading.Thread(target=watch_cf_tunnel, daemon=True).start()

    time.sleep(1)
    return "127.0.0.1", local_port
