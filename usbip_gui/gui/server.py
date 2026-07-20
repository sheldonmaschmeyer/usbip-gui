"""Server tab implementation for exposing local USB devices."""

import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import List, Tuple

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

from usbip_gui.typings import connect_signal, set_header_labels
from usbip_gui.common import (
    get_translator,
    USBIPD_PORT,
    tunnel_state,
    SortableTreeWidgetItem,
    set_min_column_widths,
    elevate_command,
    run_elevated,
)
from usbip_gui.common.common import configure_tree_widget_interaction
from .. import ssl_tunnel

t = get_translator("server")


def local_device_columns() -> List[str]:
    """Column headers for the local device tree, for the active language."""
    return [
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
                        os.path.dirname(os.path.dirname(__file__)),
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


def _is_unknown_product(description: str) -> bool:
    """Return True when usbip only exposed an unknown product label."""
    normalized = description.strip().lower()
    return normalized == "unknown product" or normalized.startswith(
        "unknown product ("
    )


def _extract_unknown_product_suffix(description: str) -> str:
    """Return the VID/PID suffix from an unknown-product label."""
    match = re.search(r"\(([^)]+)\)\s*$", description.strip())
    if match:
        return f" ({match.group(1)})"
    return ""


def _usb_details_script_path() -> str:
    """Return the absolute path to the usb_details.py probe script."""
    return str(Path(__file__).parent / "usb_details.py")


def _read_local_usb_descriptor_details(bus_id: str) -> Tuple[str, str]:
    """Read iManufacturer and iProduct for a local USB device."""
    cmd = [sys.executable, _usb_details_script_path(), bus_id]
    if sys.platform == "win32":
        # ShellExecuteExW (used by run_elevated) cannot capture stdout,
        # and reading USB descriptors via pyusb does not require elevation
        # on Windows.
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        )
    else:
        result = run_elevated(cmd)
    if result.returncode != 0:
        details = str(result.stderr).strip() or str(result.stdout).strip()
        raise OSError(details or "Failed to read USB descriptor details.")

    payload_text = str(result.stdout).strip()
    if not payload_text:
        raise OSError("USB descriptor probe did not return any data.")

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise OSError("USB descriptor probe returned invalid data.") from exc

    error = str(payload.get("error", "")).strip()
    if error:
        raise OSError(error)

    manufacturer = str(payload.get("manufacturer", "")).strip()
    product = str(payload.get("product", "")).strip()
    return manufacturer, product


def parse_windows_local_list(text: str) -> List[Tuple[str, str, str, str]]:
    """Parse windows local list."""
    if not text or not text.strip():
        return []

    rows: List[Tuple[str, str, str, str]] = []
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
            rows.append((bus_id, gui_state, device, vid_pid))
    return rows


def list_local_usb() -> List[Tuple[str, str, str, str]]:
    """List local usb."""
    if sys.platform == "win32":
        result = subprocess.run(
            ["usbipd", "list"], capture_output=True, text=True, check=False
        )
        return parse_windows_local_list(result.stdout)

    result = run_elevated(["usbip", "list", "--local"])
    return parse_local_list(result.stdout)


def bind_local_usb(bus_id: str):
    """Bind local usb."""
    if sys.platform == "win32":
        cmd = ["usbipd", "bind", "--busid", bus_id]
    else:
        cmd = ["usbip", "bind", "--busid=" + bus_id]

    result = run_elevated(cmd)
    print(result.stdout)
    print(result.stderr)
    return result


def unbind_local_usb(bus_id: str):
    """Unbind local usb."""
    if sys.platform == "win32":
        cmd = ["usbipd", "unbind", "--busid", bus_id]
    else:
        cmd = ["usbip", "unbind", "--busid=" + bus_id]

    result = run_elevated(cmd)
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

        self.local_server_restart_button = QPushButton(t("apply_port_restart"))
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
        set_header_labels(self.local_listbox, local_device_columns())
        self.local_listbox.setSortingEnabled(True)
        configure_tree_widget_interaction(self.local_listbox)
        connect_signal(
            self.local_listbox.itemDoubleClicked, self.on_double_click
        )
        self.local_listbox.setRootIsDecorated(False)
        self.local_listbox.setSelectionBehavior(
            QTreeWidget.SelectionBehavior.SelectRows
        )
        set_min_column_widths(self.local_listbox, [110, 100, 160, 200])

        layout.addLayout(self.local_control_layout1)
        layout.addLayout(self.local_actions_layout)
        layout.addWidget(self.local_listbox)
        self._last_local_devices: List[Tuple[str, str, str, str]] = []

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
        try:
            local_devices = list_local_usb()
        except OSError as e:
            QMessageBox.critical(
                self, t("Error"), t("usbip_client_missing_msg").format(e)
            )
            return
        self.local_listbox.clear()
        for device in local_devices:
            item = SortableTreeWidgetItem(
                self.local_listbox, [str(d) for d in device]
            )
            self.local_listbox.addTopLevelItem(item)

            description = device[3]
            on_windows = sys.platform == "win32"
            if _is_unknown_product(description) or on_windows:
                suffix = (
                    f" ({description})"
                    if on_windows
                    else _extract_unknown_product_suffix(description)
                )
                details_widget = QWidget(self.local_listbox)
                row_font = self.local_listbox.font()
                details_widget.setFont(row_font)
                details_layout = QHBoxLayout(details_widget)
                details_layout.setContentsMargins(0, 0, 0, 0)
                details_layout.setSpacing(8)

                show_details_button = QPushButton(t("Show Details"))
                show_details_button.setFont(row_font)
                suffix_label = QLabel(suffix)
                suffix_label.setFont(row_font)
                details_layout.addWidget(show_details_button)
                if suffix:
                    details_layout.addWidget(suffix_label)
                details_layout.addStretch()

                def show_details(
                    _checked: bool = False,
                    current_item: SortableTreeWidgetItem = item,
                ) -> None:
                    self.show_local_device_details(current_item)

                connect_signal(
                    show_details_button.clicked,
                    show_details,
                )
                self.local_listbox.setItemWidget(item, 3, details_widget)
            else:
                self.local_listbox.setItemWidget(item, 3, None)

        for i in range(len(local_device_columns())):
            self.local_listbox.resizeColumnToContents(i)

    def show_local_device_details(
        self, item: SortableTreeWidgetItem
    ) -> None:
        """Reveal descriptor strings for a local USB device."""
        bus_id = item.text(0)
        current_description = item.text(3)
        suffix = (
            f" ({current_description})"
            if sys.platform == "win32"
            else _extract_unknown_product_suffix(current_description)
        )
        try:
            manufacturer, product = _read_local_usb_descriptor_details(bus_id)
        except OSError as e:
            QMessageBox.critical(self, t("Error"), str(e))
            return

        details = " ".join(
            part for part in (manufacturer, product) if part.strip()
        ).strip()
        if not details:
            QMessageBox.information(
                self,
                t("Info"),
                t("No USB descriptor details were available."),
            )
            return

        details_label = QLabel(f"{details}{suffix}")
        details_label.setFont(self.local_listbox.font())
        details_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        details_label.setToolTip(details)
        self.local_listbox.setItemWidget(item, 3, details_label)

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
