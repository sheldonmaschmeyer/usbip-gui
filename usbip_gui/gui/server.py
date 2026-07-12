"""Server tab implementation for exposing local USB devices."""

import subprocess
import os
import sys
import time
import threading
from typing import List, Tuple

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

from usbip_gui.typings import connect_signal, set_header_labels
from .. import ssl_tunnel
from .common import (
    get_translator,
    USBIPD_PORT,
    tunnel_state,
    SortableTreeWidgetItem,
)

t = get_translator("server")

LOCAL_DEVICE_COLUMNS = [
    t("Bus ID"),
    t("State"),
    t("Manufacturer"),
    t("Description"),
]


def init_usbip_server(
    port: int = 3240,
    secure: bool = False,
    password: str = "",
    bind_host: str = "0.0.0.0",
):
    """Init usbip server."""
    subprocess.run(["sudo", "pkill", "usbipd"], check=False)
    subprocess.run(["pkill", "-f", "ssl_tunnel.py server"], check=False)
    if tunnel_state.server_process:
        try:
            tunnel_state.server_process.terminate()
            tunnel_state.server_process.wait()
        except OSError:
            pass
        tunnel_state.server_process = None

    if secure:
        target_port = port + 10000
        subprocess.run(
            ["sudo", "usbipd", "-D", "--tcp-port", str(target_port)],
            check=False,
        )

        def run_tunnel():
            with subprocess.Popen(
                [
                    sys.executable,
                    os.path.join(
                        os.path.dirname(os.path.dirname(__file__)),
                        "ssl_tunnel.py",
                    ),
                    "server",
                    "--listen-port",
                    str(port),
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
        subprocess.run(
            ["sudo", "usbipd", "-D", "--tcp-port", str(port)], check=False
        )


def parse_local_list(text: str) -> List[Tuple[str, str, str, str]]:
    """Parse local list."""
    if not text or not text.strip():
        return []

    rows: List[Tuple[str, str, str, str]] = []
    devices = text.strip().split("\n\n")
    for device in devices:
        lines = device.strip().split("\n")
        if len(lines) < 2:
            continue
        bus_info = lines[0].split(" ")
        man_info = lines[1].split(":")

        bus_id = bus_info[2] if len(bus_info) > 2 else ""
        manufacturer = man_info[0] if len(man_info) > 0 else ""
        description = ":".join(man_info[1:]) if len(man_info) > 1 else ""

        state = t("Unbound")
        if bus_id:
            driver_path = f"/sys/bus/usb/devices/{bus_id}/driver"
            if os.path.exists(driver_path) and os.path.islink(driver_path):
                driver = os.path.basename(os.readlink(driver_path))
                if driver == "usbip-host":
                    state = t("Bound")

        rows.append((bus_id, state, manufacturer, description))
    return rows


def list_local_usb() -> List[Tuple[str, str, str, str]]:
    """List local usb."""
    result = subprocess.run(
        ["sudo", "usbip", "list", "--local"],
        capture_output=True,
        text=True,
        check=False,
    )
    return parse_local_list(result.stdout)


def bind_local_usb(bus_id: str):
    """Bind local usb."""
    result = subprocess.run(
        ["sudo", "usbip", "bind", "--busid=" + bus_id],
        capture_output=True,
        text=True,
        check=False,
    )
    print(result.stdout)
    print(result.stderr)
    return result


def unbind_local_usb(bus_id: str):
    """Unbind local usb."""
    result = subprocess.run(
        ["sudo", "usbip", "unbind", "--busid=" + bus_id],
        capture_output=True,
        text=True,
        check=False,
    )
    print(result.stdout)
    print(result.stderr)
    return result


class ServerTab(QWidget):
    """Servertab."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the class instance."""
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # Control Frame 1 (top row)
        self.local_control_layout1 = QHBoxLayout()
        self.local_list_label = QLabel(t("Local USB Devices"))
        self.local_port_label = QLabel(t("Port "))
        self.local_port_input = QLineEdit()
        self.local_port_input.setText(str(USBIPD_PORT))
        self.local_port_input.setFixedWidth(60)

        self.local_bind_ip_label = QLabel(t("Bind IP"))
        self.local_bind_ip_input = QLineEdit()
        self.local_bind_ip_input.setText("0.0.0.0")
        self.local_bind_ip_input.setFixedWidth(120)

        self.local_secure_checkbox = QCheckBox(t("Secure"))
        self.local_secure_checkbox.setChecked(True)
        connect_signal(
            self.local_secure_checkbox.stateChanged, self.check_secure_warning
        )

        self.local_password_input = QLineEdit()
        self.local_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.local_password_input.setFixedWidth(150)

        self.local_server_restart_button = QPushButton(
            t("Apply Port & Restart")
        )
        self.local_server_restart_button.setToolTip(t("local_restart_tooltip"))
        connect_signal(
            self.local_server_restart_button.clicked, self.restart_server
        )
        connect_signal(
            self.local_port_input.returnPressed, self.restart_server
        )

        self.local_show_fingerprint_button = QPushButton(t("Show Fingerprint"))
        connect_signal(
            self.local_show_fingerprint_button.clicked, self.show_fingerprint
        )

        self.local_regen_cert_button = QPushButton(t("Regen Cert"))
        connect_signal(
            self.local_regen_cert_button.clicked, self.regenerate_cert
        )

        self.local_control_layout1.addWidget(self.local_list_label)
        self.local_control_layout1.addWidget(self.local_port_label)
        self.local_control_layout1.addWidget(self.local_port_input)
        self.local_control_layout1.addWidget(self.local_bind_ip_label)
        self.local_control_layout1.addWidget(self.local_bind_ip_input)
        self.local_control_layout1.addWidget(self.local_secure_checkbox)
        self.local_control_layout1.addWidget(self.local_password_input)
        self.local_control_layout1.addWidget(self.local_server_restart_button)
        self.local_control_layout1.addWidget(
            self.local_show_fingerprint_button
        )
        self.local_control_layout1.addWidget(self.local_regen_cert_button)
        self.local_control_layout1.addStretch()

        # Control Frame 2 (actions)
        self.local_actions_layout = QHBoxLayout()
        self.local_list_refresh_button = QPushButton(t("Refresh"))
        self.local_list_refresh_button.setToolTip(t("local_refresh_tooltip"))
        connect_signal(
            self.local_list_refresh_button.clicked, self.refresh_local
        )

        self.local_list_bind_button = QPushButton(t("Bind Device"))
        self.local_list_bind_button.setToolTip(t("local_bind_tooltip"))
        connect_signal(self.local_list_bind_button.clicked, self.bind_local)

        self.local_list_unbind_button = QPushButton(t("Unbind Device"))
        self.local_list_unbind_button.setToolTip(t("local_unbind_tooltip"))
        connect_signal(
            self.local_list_unbind_button.clicked, self.unbind_local
        )

        self.local_actions_layout.addWidget(self.local_list_refresh_button)
        self.local_actions_layout.addWidget(self.local_list_bind_button)
        self.local_actions_layout.addWidget(self.local_list_unbind_button)
        self.local_actions_layout.addStretch()

        # List
        self.local_listbox = QTreeWidget()
        set_header_labels(self.local_listbox, LOCAL_DEVICE_COLUMNS)
        self.local_listbox.setSortingEnabled(True)
        connect_signal(
            self.local_listbox.itemDoubleClicked, self.on_double_click
        )
        self.local_listbox.setRootIsDecorated(False)
        self.local_listbox.setSelectionBehavior(
            QTreeWidget.SelectionBehavior.SelectRows
        )

        layout.addLayout(self.local_control_layout1)
        layout.addLayout(self.local_actions_layout)
        layout.addWidget(self.local_listbox)

        self.refresh_local()

    def check_secure_warning(self, state: int):
        """Check secure warning."""
        if state == 0:
            QMessageBox.warning(self, t("Warning"), t("insecure_warning_msg"))

    def show_fingerprint(self):
        """Show fingerprint."""
        try:
            cert_path, _key_path = ssl_tunnel.get_cert_paths()
            fp = ssl_tunnel.get_cert_fingerprint(cert_path)
            QMessageBox.information(self, t("Certificate Fingerprint"), fp)
        except OSError as e:
            QMessageBox.critical(self, t("Error"), str(e))

    def regenerate_cert(self):
        """Regenerate cert."""
        try:
            cert_path, key_path = ssl_tunnel.get_cert_paths()
            if os.path.exists(cert_path):
                os.remove(cert_path)
            if os.path.exists(key_path):
                os.remove(key_path)
            ssl_tunnel.generate_self_signed_cert(cert_path, key_path)
            QMessageBox.information(self, t("Success"), t("cert_regen"))
        except OSError as e:
            QMessageBox.critical(self, t("Error"), str(e))

    def refresh_local(self):
        """Refresh local."""
        local_devices = list_local_usb()
        self.local_listbox.clear()
        for device in local_devices:
            item = SortableTreeWidgetItem(
                self.local_listbox, [str(d) for d in device]
            )
            self.local_listbox.addTopLevelItem(item)

        for i in range(len(LOCAL_DEVICE_COLUMNS)):
            self.local_listbox.resizeColumnToContents(i)

    def restart_server(self):
        """Restart server."""
        try:
            port = int(self.local_port_input.text())
        except ValueError:
            QMessageBox.critical(self, t("Error"), t("Invalid port number"))
            return
        secure = self.local_secure_checkbox.isChecked()
        password = self.local_password_input.text()
        if secure and not password:
            QMessageBox.critical(
                self, t("Error"), t("Password required for secure connection")
            )
            return
        bind_host = self.local_bind_ip_input.text().strip() or "0.0.0.0"
        init_usbip_server(port, secure, password, bind_host)

    def bind_local(self):
        """Bind local."""
        selection = self.local_listbox.selectedItems()
        if not selection:
            QMessageBox.critical(self, t("Error"), t("no selection to bind"))
            return
        bus_id = selection[0].text(0)
        bind_local_usb(bus_id)
        time.sleep(0.5)
        self.refresh_local()

    def unbind_local(self):
        """Unbind local."""
        selection = self.local_listbox.selectedItems()
        if not selection:
            QMessageBox.critical(self, t("Error"), t("no selection to unbind"))
            return
        bus_id = selection[0].text(0)
        unbind_local_usb(bus_id)
        time.sleep(0.5)
        self.refresh_local()

    def on_double_click(
        self, _item: SortableTreeWidgetItem, _column: int
    ) -> None:
        """Handle double clicks on the device list."""
        if not _item:
            return
        state = _item.text(1)
        if state == t("Bound"):
            self.unbind_local()
        else:
            self.bind_local()
