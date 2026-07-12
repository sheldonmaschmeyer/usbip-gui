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
import random
import time
from typing import List, Tuple
from urllib.parse import urlparse

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
)

from .common import (
    get_translator,
    USBIPD_PORT,
    tunnel_state,
    get_config_dir,
)

t = get_translator("client")

DEVICE_COLUMNS = [t("Bus ID"), t("Manufacturer"), t("Description")]
ATTACHED_COLUMNS = [
    t("Host"),
    t("Port"),
    t("Bus ID"),
    t("Manufacturer"),
    t("Description"),
]


def parse_remote_list(text: str) -> List[Tuple[str, str, str]]:
    """Parse remote list."""
    if "no exportable devices found on" in text:
        return []

    rows: List[Tuple[str, str, str]] = []
    busid_regex = re.compile("^\\d+-\\d+$|^\\d+-\\d+\\.\\d+$")
    lines = text.strip().split("\n")
    for line in lines:
        vals = line.strip().split(":")
        if len(vals) < 4:
            continue
        m = busid_regex.match(vals[0].strip())
        if m:
            rows.append(
                (
                    vals[0].strip(),
                    vals[1].strip(),
                    vals[2].strip() + ":" + vals[3].strip(),
                )
            )
    return rows


def parse_attached_list(text: str) -> List[Tuple[str, int, str, str, str]]:
    """Parse attached list."""
    rows: List[Tuple[str, int, str, str, str]] = []
    lines = text.strip().split("\n")
    for i, line in enumerate(lines):
        if "Port " in line:
            port = int(line.strip().split(":")[0].replace("Port ", ""))
            info_line = lines[i + 1]
            busid_line = lines[i + 2]

            info = info_line.strip().split(":")
            manufacturer = info[0].strip()
            description = info[1].strip() + ":" + info[2].strip()

            businfo = busid_line.strip().split("->")
            bus_id = businfo[0].strip()
            host = urlparse(businfo[1].strip())[1]  # netloc

            rows.append((host, port, bus_id, manufacturer, description))
    return rows


def get_or_create_client_tunnel(
    host: str, port: int, secure: bool, password: str
) -> Tuple[str, int]:
    """Get or create client tunnel."""
    if not secure:
        return host, port

    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        with socket.create_connection((host, port)) as sock:
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

        host_key = f"{host}:{port}"
        if host_key not in known_hosts or known_hosts[host_key] != fingerprint:
            msg = t("cert_fingerprint_msg").format(fingerprint)
            reply = QMessageBox.question(
                None,
                t("Certificate Check"),
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
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
                None, t("Error"), t("Password required for secure connection")
            )
            return "", 0

        with socket.create_connection((host, port)) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                test_cert_der = ssock.getpeercert(binary_form=True)
                if test_cert_der:
                    test_fp = hashlib.sha256(test_cert_der).hexdigest().upper()
                    it = iter(test_fp)
                    test_fp = ":".join(a + b for a, b in zip(it, it))
                    if test_fp != fingerprint:
                        raise ValueError(
                            "Fingerprint mismatch during auth check"
                        )

                pwd_bytes = password.encode("utf-8")
                pwd_len = len(pwd_bytes)
                ssock.sendall(pwd_len.to_bytes(4, byteorder="big") + pwd_bytes)

                response = ssock.recv(1)
                if response != b"\x01":
                    QMessageBox.critical(
                        None, t("Error"), t("auth_failed_msg")
                    )
                    return "", 0

    except (OSError, ValueError) as e:
        QMessageBox.critical(
            None, t("Error"), t(f"Failed to check certificate: {e}")
        )
        return "", 0

    key = (host, port)
    if key in tunnel_state.client_processes:
        local_port, proc, cached_password = tunnel_state.client_processes[key]
        if proc.poll() is None:
            if cached_password == password:
                return "127.0.0.1", local_port
            tunnel_state.client_processes.pop(key)
            proc.kill()

    local_port = random.randint(40000, 50000)

    def run_tunnel():
        with subprocess.Popen(
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
                str(port),
                "--password",
                password,
                "--fingerprint",
                fingerprint,
            ]
        ) as proc:
            tunnel_state.client_processes[key] = (local_port, proc, password)
            proc.wait()

    threading.Thread(target=run_tunnel, daemon=True).start()

    time.sleep(1)
    return "127.0.0.1", local_port


def list_remote_usb(
    server_ip: str, port: int = 3240, secure: bool = False, password: str = ""
) -> List[Tuple[str, str, str]]:
    """List remote usb."""
    target_ip, target_port = get_or_create_client_tunnel(
        server_ip, port, secure, password
    )
    if not target_ip:
        return []
    result = subprocess.run(
        [
            "sudo",
            "usbip",
            "--tcp-port",
            str(target_port),
            "list",
            "--remote=" + target_ip,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return parse_remote_list(result.stdout)


def list_attached_usb() -> List[Tuple[str, int, str, str, str]]:
    """List attached usb."""
    result = subprocess.run(
        ["sudo", "usbip", "port"], capture_output=True, text=True, check=False
    )
    return parse_attached_list(result.stdout)


def attach_remote_usb(
    server_ip: str,
    bus_id: str,
    port: int = 3240,
    secure: bool = False,
    password: str = "",
):
    """Attach remote usb."""
    target_ip, target_port = get_or_create_client_tunnel(
        server_ip, port, secure, password
    )
    if not target_ip:
        return subprocess.CompletedProcess(
            args=[], returncode=-1, stdout="", stderr=""
        )
    result = subprocess.run(
        [
            "sudo",
            "usbip",
            "--tcp-port",
            str(target_port),
            "attach",
            "--remote=" + target_ip,
            "--busid=" + bus_id,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result


def detach_remote_usb(port: int):
    """Detach remote usb."""
    subprocess.run(
        ["sudo", "usbip", "detach", "--port=" + str(port)],
        capture_output=True,
        text=True,
        check=False,
    )


class ClientTab(QWidget):
    """Clienttab."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the class instance."""
        super().__init__(parent)

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
        self.remote_secure_checkbox.stateChanged.connect(
            self.check_secure_warning
        )

        self.remote_password_input = QLineEdit()
        self.remote_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.remote_password_input.setFixedWidth(100)

        self.remote_list_refresh_button = QPushButton(t("Refresh"))
        self.remote_list_refresh_button.setToolTip(t("remote_refresh_tooltip"))
        self.remote_list_refresh_button.clicked.connect(self.refresh_remote)

        self.remote_list_attach_button = QPushButton(t("Attach Device"))
        self.remote_list_attach_button.setToolTip(t("remote_attach_tooltip"))
        self.remote_list_attach_button.clicked.connect(self.attach_remote)

        self.remote_control_layout.addWidget(self.remote_list_label)
        self.remote_control_layout.addWidget(self.remote_ip_input)
        self.remote_control_layout.addWidget(self.remote_port_input)
        self.remote_control_layout.addWidget(self.remote_secure_checkbox)
        self.remote_control_layout.addWidget(self.remote_password_input)
        self.remote_control_layout.addWidget(self.remote_list_refresh_button)
        self.remote_control_layout.addWidget(self.remote_list_attach_button)
        self.remote_control_layout.addStretch()

        # Remote List
        self.remote_listbox = QTreeWidget()
        self.remote_listbox.setHeaderLabels(DEVICE_COLUMNS)
        self.remote_listbox.itemDoubleClicked.connect(
            self.on_double_click_remote
        )
        self.remote_listbox.setRootIsDecorated(False)
        self.remote_listbox.setSelectionBehavior(
            QTreeWidget.SelectionBehavior.SelectRows
        )

        # Attached Control Frame
        self.attached_control_layout = QHBoxLayout()
        self.attached_list_label = QLabel(t("Attached Devices"))

        self.attached_list_refresh_button = QPushButton(t("Refresh"))
        self.attached_list_refresh_button.setToolTip(
            t("attached_refresh_tooltip")
        )
        self.attached_list_refresh_button.clicked.connect(
            self.refresh_attached
        )

        self.detach_button = QPushButton(t("Detach Device"))
        self.detach_button.setToolTip(t("attached_detach_tooltip"))
        self.detach_button.clicked.connect(self.detach_remote)

        self.attached_control_layout.addWidget(self.attached_list_label)
        self.attached_control_layout.addWidget(
            self.attached_list_refresh_button
        )
        self.attached_control_layout.addWidget(self.detach_button)
        self.attached_control_layout.addStretch()

        # Attached List
        self.attached_listbox = QTreeWidget()
        self.attached_listbox.setHeaderLabels(ATTACHED_COLUMNS)
        self.attached_listbox.itemDoubleClicked.connect(
            self.on_double_click_attached
        )
        self.attached_listbox.setRootIsDecorated(False)
        self.attached_listbox.setSelectionBehavior(
            QTreeWidget.SelectionBehavior.SelectRows
        )

        layout.addLayout(self.remote_control_layout)
        layout.addWidget(self.remote_listbox)
        layout.addLayout(self.attached_control_layout)
        layout.addWidget(self.attached_listbox)

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

        remote_devices = list_remote_usb(server_ip, port, secure, password)
        self.remote_listbox.clear()
        for device in remote_devices:
            item = QTreeWidgetItem(
                self.remote_listbox, [str(d) for d in device]
            )
            self.remote_listbox.addTopLevelItem(item)

        for i in range(len(DEVICE_COLUMNS)):
            self.remote_listbox.resizeColumnToContents(i)

    def refresh_attached(self):
        """Refresh attached."""
        attached_devices = list_attached_usb()
        self.attached_listbox.clear()
        for attached_device in attached_devices:
            item = QTreeWidgetItem(
                self.attached_listbox, [str(d) for d in attached_device]
            )
            self.attached_listbox.addTopLevelItem(item)

        for i in range(len(ATTACHED_COLUMNS)):
            self.attached_listbox.resizeColumnToContents(i)

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

        secure = self.remote_secure_checkbox.isChecked()
        password = self.remote_password_input.text()
        bus_id = selection[0].text(0)

        attach_remote_usb(server_ip, bus_id, port, secure, password)
        time.sleep(0.5)
        self.refresh_remote()
        self.refresh_attached()

    def detach_remote(self):
        """Detach remote."""
        selection = self.attached_listbox.selectedItems()
        if not selection:
            QMessageBox.critical(self, t("Error"), t("no selection to detach"))
            return

        port = int(selection[0].text(1))
        detach_remote_usb(port)
        time.sleep(0.5)
        self.refresh_remote()
        self.refresh_attached()

    def on_double_click_remote(
        self, _item: QTreeWidgetItem, _column: int
    ) -> None:
        """Attach remote usb on double click."""
        if _item:
            self.attach_remote()

    def on_double_click_attached(
        self, _item: QTreeWidgetItem, _column: int
    ) -> None:
        """Detach remote usb on double click."""
        if _item:
            self.detach_remote()
