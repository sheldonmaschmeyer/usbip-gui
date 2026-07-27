"""Client tab implementation for managing remote USB device connections."""

import json
import socket
import ssl
import hashlib
import subprocess
import threading
import os
import sys
import re
import shutil
import random
import time
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QTreeWidget,
    QMessageBox,
)
from usbip_gui.common import SortableTreeWidgetItem, set_min_column_widths

from usbip_gui.typings import connect_signal, set_header_labels
from usbip_gui.common import (
    get_translator,
    USBIPD_PORT,
    tunnel_state,
    get_config_dir,
    elevate_command,
    run_elevated,
)
from usbip_gui.common.common import configure_tree_widget_interaction
from usbip_gui.product_detection import (
    ItemUpdater,
    enrich_remote_device_item,
    is_unknown_product,
)

t = get_translator("client")


def _resolve_usbip_client_executable() -> str:
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

    # Common defaults if environment variables are missing/unusual.
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


def _secure_port_candidates(port: int) -> List[int]:
    """Return secure-port candidates, including Windows default fallback."""
    if sys.platform == "win32" and port == USBIPD_PORT:
        # Windows server mode may expose TLS on 3241 when usbipd uses 3240.
        return [port, port + 1]
    return [port]


def _reset_client_tunnels_for_host(host: str) -> None:
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


@lru_cache(maxsize=None)
def _detect_windows_attach_bus_option(exe: str) -> str:
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
        m = busid_regex.match(vals[0].strip())
        if m:
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
        if "Port " in line:
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
            host = urlparse(businfo[1].strip())[1]  # netloc

            rows.append(
                (host, port, bus_id, vid_pid, manufacturer, description)
            )
    return rows


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

    for candidate_port in _secure_port_candidates(port):
        try:
            with socket.create_connection((host, candidate_port)) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)

            if not cert_der:
                raise ValueError("No certificate provided by server")

            fingerprint = hashlib.sha256(cert_der).hexdigest().upper()
            it = iter(fingerprint)
            fingerprint = ":".join(a + b for a, b in zip(it, it))

            known_hosts_path = get_config_dir() / "known_hosts.json"
            known_hosts = {}
            if os.path.exists(known_hosts_path):
                with open(known_hosts_path, "r", encoding="utf-8") as f:
                    known_hosts = json.load(f)

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
                    with open(known_hosts_path, "w", encoding="utf-8") as f:
                        json.dump(known_hosts, f)
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
                        test_fp = (
                            hashlib.sha256(test_cert_der).hexdigest().upper()
                        )
                        it = iter(test_fp)
                        test_fp = ":".join(a + b for a, b in zip(it, it))
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

        except (OSError, ValueError) as e:
            last_error = e
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
                os.path.dirname(os.path.dirname(__file__)), "ssl_tunnel.py"
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


def list_remote_usb(
    server_ip: str, port: int = 3240, secure: bool = False, password: str = ""
) -> List[Tuple[str, str, str, str]]:
    """List remote usb."""
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


def attach_remote_usb(
    server_ip: str,
    bus_id: str,
    port: int = 3240,
    secure: bool = False,
    password: str = "",
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

    target_ip, target_port = get_or_create_client_tunnel(
        server_ip, port, secure, password
    )
    if not target_ip:
        return subprocess.CompletedProcess(
            args=[], returncode=-1, stdout="", stderr=""
        )

    result = _run_attach(target_ip, target_port)
    if secure and result.returncode != 0:
        # The secure tunnel can transiently fail on Windows after being idle.
        _reset_client_tunnels_for_host(server_ip)
        target_ip, target_port = get_or_create_client_tunnel(
            server_ip, port, secure, password
        )
        if not target_ip:
            return result
        result = _run_attach(target_ip, target_port)

    if sys.platform == "win32" and result.returncode != 0:
        # UAC-elevated runs don't expose stdout/stderr. Run once without UAC
        # to capture actionable diagnostics for the UI.
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


class ClientTab(QWidget):
    """Clienttab."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the class instance."""
        # pylint: disable=duplicate-code
        super().__init__(parent)

        self._item_updater = ItemUpdater(self)
        connect_signal(
            self._item_updater.update, self._item_updater.apply_text
        )

        layout = QVBoxLayout(self)

        # Remote Control Frame
        self.remote_control_layout = QHBoxLayout()
        self.remote_list_label = QLabel(t("Remote USB Devices for "))
        self.remote_ip_input = QLineEdit()
        self.remote_ip_input.setText("127.0.0.1")
        self.remote_ip_input.setFixedWidth(100)

        self.remote_port_input = QLineEdit()
        self.remote_port_input.setText(str(USBIPD_PORT))
        self.remote_port_input.setFixedWidth(60)

        self.remote_secure_checkbox = QCheckBox(t("Secure"))
        self.remote_secure_checkbox.setChecked(True)
        connect_signal(
            self.remote_secure_checkbox.stateChanged, self.check_secure_warning
        )

        self.remote_password_input = QLineEdit()
        self.remote_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.remote_password_input.setFixedWidth(100)

        self.remote_list_refresh_button = QPushButton(t("Refresh"))
        self.remote_list_refresh_button.setToolTip(t("remote_refresh_tooltip"))
        connect_signal(
            self.remote_list_refresh_button.clicked, self.refresh_remote
        )

        self.remote_list_attach_button = QPushButton(t("Attach Device"))
        self.remote_list_attach_button.setToolTip(t("remote_attach_tooltip"))
        connect_signal(
            self.remote_list_attach_button.clicked, self.attach_remote
        )

        self.detach_button = QPushButton(t("Detach Device"))
        self.detach_button.setToolTip(t("attached_detach_tooltip"))
        connect_signal(self.detach_button.clicked, self.detach_remote)

        self.remote_control_layout.addWidget(self.remote_list_label)
        self.remote_control_layout.addWidget(self.remote_ip_input)
        self.remote_control_layout.addWidget(self.remote_port_input)
        self.remote_control_layout.addWidget(self.remote_secure_checkbox)
        self.remote_control_layout.addWidget(self.remote_password_input)
        self.remote_control_layout.addWidget(self.remote_list_refresh_button)
        self.remote_control_layout.addWidget(self.remote_list_attach_button)
        self.remote_control_layout.addWidget(self.detach_button)
        self.remote_control_layout.addStretch()

        # Remote List
        self.remote_listbox = QTreeWidget()
        set_header_labels(self.remote_listbox, device_columns())
        self.remote_listbox.setSortingEnabled(True)
        configure_tree_widget_interaction(self.remote_listbox)
        connect_signal(
            self.remote_listbox.itemDoubleClicked, self.on_double_click_remote
        )
        self.remote_listbox.setRootIsDecorated(False)
        self.remote_listbox.setSelectionBehavior(
            QTreeWidget.SelectionBehavior.SelectRows
        )
        set_min_column_widths(
            self.remote_listbox, [100, 60, 100, 120, 160, 200]
        )

        layout.addLayout(self.remote_control_layout)
        layout.addWidget(self.remote_listbox)

    def check_secure_warning(self, state: int):
        """Check secure warning."""
        if state == 0:
            QMessageBox.warning(self, t("Warning"), t("insecure_warning_msg"))

    def refresh_remote(self):
        """Refresh remote."""
        server_ip = self.remote_ip_input.text()
        try:
            port = int(self.remote_port_input.text())
        except ValueError:
            QMessageBox.critical(self, t("Error"), t("Invalid port number"))
            return
        secure = self.remote_secure_checkbox.isChecked()
        password = self.remote_password_input.text()

        try:
            remote_devices = list_remote_usb(server_ip, port, secure, password)
            attached_devices = list_attached_usb()
        except OSError as e:
            QMessageBox.critical(
                self, t("Error"), t("usbip_client_missing_msg").format(e)
            )
            return
        self.remote_listbox.clear()

        attached_by_busid = {d[2]: d for d in attached_devices}

        for r_bus_id, vid_pid, manufacturer, description in remote_devices:
            status = t("Detached")
            local_port = -1
            if r_bus_id in attached_by_busid:
                status = t("Attached")
                att = attached_by_busid.pop(r_bus_id)
                local_port = att[1]

            item_data = [
                server_ip,
                str(port),
                r_bus_id,
                status,
                manufacturer,
                description,
                vid_pid,
            ]
            if sys.platform == "win32":
                item_data.insert(6, description)
                item_data[5] = ""

            item = SortableTreeWidgetItem(self.remote_listbox, item_data)
            item.setData(0, Qt.ItemDataRole.UserRole, local_port)
            self.remote_listbox.addTopLevelItem(item)

            if sys.platform == "win32":
                enrich_remote_device_item(
                    self._item_updater,
                    item,
                    vid_pid,
                    manufacturer,
                    manufacturer_col=4,
                    description_col=5,
                )

        for (
            host,
            att_port,
            a_bus_id,
            vid_pid,
            manufacturer,
            description,
        ) in attached_by_busid.values():
            status = t("Attached")
            display_host = host
            display_port = ""
            if ":" in host:
                display_host, display_port = host.split(":", 1)

            item_data = [
                display_host,
                display_port,
                a_bus_id,
                status,
                manufacturer,
                description,
                vid_pid,
            ]
            if sys.platform == "win32":
                item_data.insert(6, description)
                item_data[5] = ""

            item = SortableTreeWidgetItem(self.remote_listbox, item_data)
            item.setData(0, Qt.ItemDataRole.UserRole, att_port)
            self.remote_listbox.addTopLevelItem(item)

            if sys.platform == "win32":
                enrich_remote_device_item(
                    self._item_updater,
                    item,
                    vid_pid,
                    manufacturer,
                    manufacturer_col=4,
                    description_col=5,
                )

        for i in range(len(device_columns())):
            self.remote_listbox.resizeColumnToContents(i)

    def attach_remote(self):
        """Attach remote."""
        server_ip = self.remote_ip_input.text()
        try:
            port = int(self.remote_port_input.text())
        except ValueError:
            QMessageBox.critical(self, t("Error"), t("Invalid port number"))
            return

        selection = self.remote_listbox.selectedItems()
        if not selection:
            QMessageBox.critical(self, t("Error"), t("no selection to attach"))
            return

        status = selection[0].text(3)
        if status == t("Attached"):
            QMessageBox.information(
                self, t("Info"), t("Device is already attached.")
            )
            return

        secure = self.remote_secure_checkbox.isChecked()
        password = self.remote_password_input.text()
        bus_id = selection[0].text(2)

        result = attach_remote_usb(server_ip, bus_id, port, secure, password)
        return_code = getattr(result, "returncode", 0)
        if isinstance(return_code, int) and return_code != 0:
            stderr = getattr(result, "stderr", "")
            stdout = getattr(result, "stdout", "")
            details = str(stderr).strip() or str(stdout).strip()
            if not details:
                details = f"Exit code: {return_code}"
            if return_code == 106:
                details += (
                    "\n\nHint: The device may not be shared on the server "
                    "yet, may already be attached elsewhere, or the local "
                    "USB/IP driver/service is not ready."
                )
            QMessageBox.critical(
                self,
                t("Error"),
                f"Failed to attach device {bus_id}:\n{details}",
            )
            return
        time.sleep(0.5)
        self.refresh_remote()

    def detach_remote(self):
        """Detach remote."""
        selection = self.remote_listbox.selectedItems()
        if not selection:
            QMessageBox.critical(self, t("Error"), t("no selection to detach"))
            return

        status = selection[0].text(3)
        if status != t("Attached"):
            QMessageBox.information(
                self, t("Info"), t("Device is not attached.")
            )
            return

        local_port = selection[0].data(0, Qt.ItemDataRole.UserRole)
        if local_port is None or local_port == -1:
            QMessageBox.critical(
                self,
                t("Error"),
                t("Could not find local port for detachment."),
            )
            return

        detach_remote_usb(local_port)
        time.sleep(0.5)
        self.refresh_remote()

    def on_double_click_remote(
        self, _item: SortableTreeWidgetItem, _column: int
    ) -> None:
        """Attach or detach remote usb on double click."""
        if _item:
            status = _item.text(3)
            if status == t("Attached"):
                self.detach_remote()
            else:
                self.attach_remote()
