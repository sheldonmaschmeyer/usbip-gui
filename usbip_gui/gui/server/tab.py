"""Server tab UI and interactions."""

import os
import sys
import time
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
    QComboBox,
)

from usbip_gui.typings import connect_signal, set_header_labels
from usbip_gui.common import (
    get_translator,
    USBIPD_PORT,
    SortableTreeWidgetItem,
    set_min_column_widths,
    load_sites,
    get_site,
    get_selected_site_name,
    set_selected_site_name,
    site_requires_unlock,
    sites_updated,
)
from usbip_gui.common.common import configure_tree_widget_interaction
from usbip_gui.gui.dialogs import ensure_unlocked
from usbip_gui.product_detection import (
    ItemUpdater,
    enrich_device_item,
    is_unknown_product,
)
from ... import ssl_tunnel
from .parsing import (
    bind_local_usb,
    list_local_usb,
    local_device_columns,
    unbind_local_usb,
)
from .runtime import init_usbip_server

t = get_translator("server")


class ServerTab(QWidget):
    """Server tab implementation for exposing local USB devices."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the class instance."""
        # pylint: disable=duplicate-code,too-many-statements
        super().__init__(parent)

        self._item_updater = ItemUpdater(self)
        connect_signal(
            self._item_updater.update, self._item_updater.apply_text
        )

        layout = QVBoxLayout(self)

        # Control Frame 1 (top row)
        self.local_control_layout1 = QHBoxLayout()
        self.local_site_label = QLabel(t("Site:"))
        self.local_site_combo = QComboBox()
        self.local_site_combo.setMinimumWidth(110)
        connect_signal(
            self.local_site_combo.currentIndexChanged, self.on_site_selected
        )
        connect_signal(sites_updated.changed, self.on_sites_updated)

        self.local_connect_button = QPushButton(t("Connect"))
        connect_signal(self.local_connect_button.clicked, self.restart_server)

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
        self.local_password_input.setFixedWidth(180)

        self.local_show_password_checkbox = QCheckBox(t("Show"))
        self.local_show_password_checkbox.setToolTip(
            t("show_password_tooltip")
        )
        connect_signal(
            self.local_show_password_checkbox.stateChanged,
            self.toggle_show_password,
        )

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

        self.local_control_layout1.addWidget(self.local_site_label)
        self.local_control_layout1.addWidget(self.local_site_combo)
        self.local_control_layout1.addWidget(self.local_connect_button)
        self.local_control_layout1.addWidget(self.local_list_label)
        self.local_control_layout1.addWidget(self.local_port_label)
        self.local_control_layout1.addWidget(self.local_port_input)
        self.local_control_layout1.addWidget(self.local_bind_ip_label)
        self.local_control_layout1.addWidget(self.local_bind_ip_input)
        self.local_control_layout1.addWidget(self.local_secure_checkbox)
        self.local_control_layout1.addWidget(self.local_password_input)
        self.local_control_layout1.addWidget(self.local_show_password_checkbox)
        self.local_control_layout1.addStretch()

        self.populate_site_combo()

        # Control Frame 2 (actions)
        self.local_actions_layout = QHBoxLayout()
        self.local_actions_layout.addWidget(self.local_server_restart_button)
        self.local_actions_layout.addWidget(self.local_show_fingerprint_button)
        self.local_actions_layout.addWidget(self.local_regen_cert_button)

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

    def toggle_show_password(self, _state: int = 0) -> None:
        """Toggle local password visibility between masked and plain text."""
        if self.local_show_password_checkbox.isChecked():
            self.local_password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.local_password_input.setEchoMode(QLineEdit.EchoMode.Password)

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
        on_windows = sys.platform == "win32"
        for device in local_devices:
            item_data = [str(d) for d in device]
            if on_windows:
                item_data.insert(4, item_data[3])
                item_data[3] = ""

            item = SortableTreeWidgetItem(self.local_listbox, item_data)
            self.local_listbox.addTopLevelItem(item)

            bus_id = device[0]
            description = device[3]
            vid_pid = device[4]

            if on_windows or is_unknown_product(description):
                enrich_device_item(
                    self._item_updater,
                    item,
                    bus_id,
                    on_windows,
                    vid_pid,
                    description,
                )

        for i in range(len(local_device_columns())):
            self.local_listbox.resizeColumnToContents(i)

    def populate_site_combo(self) -> None:
        """Populate the site dropdown with saved server sites."""
        saved_sites = load_sites("server")
        saved_names = {str(site.get("name", "")) for site in saved_sites}
        current_data = self.local_site_combo.currentData()
        if current_data and str(current_data) in saved_names:
            selected_name = str(current_data)
        else:
            selected_name = get_selected_site_name("server")
        self.local_site_combo.blockSignals(True)
        self.local_site_combo.clear()
        self.local_site_combo.addItem(t("Manual / Default"), "")
        selected_idx = 0
        for idx, site in enumerate(saved_sites, start=1):
            name = str(site.get("name", ""))
            self.local_site_combo.addItem(name, name)
            if name == selected_name:
                selected_idx = idx
        self.local_site_combo.setCurrentIndex(selected_idx)
        self.local_site_combo.blockSignals(False)

    def on_sites_updated(self, site_type: str) -> None:
        """Handle site configuration updates."""
        if site_type == "server":
            self.populate_site_combo()

    def on_site_selected(self, _index: int) -> None:
        """Handle selection change in site dropdown."""
        site_name = str(self.local_site_combo.currentData() or "")
        set_selected_site_name("server", site_name)
        if not site_name:
            return
        site = get_site("server", site_name)
        if not site:
            return
        self.local_port_input.setText(str(site.get("port", USBIPD_PORT)))
        self.local_bind_ip_input.setText(str(site.get("bind_ip", "0.0.0.0")))
        self.local_secure_checkbox.blockSignals(True)
        self.local_secure_checkbox.setChecked(bool(site.get("secure", True)))
        self.local_secure_checkbox.blockSignals(False)
        pwd_val = site.get("password", "")
        self.local_password_input.setText(
            str(pwd_val) if isinstance(pwd_val, str) else ""
        )

    def get_active_cf_settings(self) -> Tuple[bool, str, str]:
        """Return (use_cf, cf_token, cf_path) based on active site."""
        site_name = str(self.local_site_combo.currentData() or "")
        if site_name:
            site = get_site("server", site_name)
            if site and site.get("connection_type") == "cloudflared":
                token_val = site.get("cloudflared_token")
                token = (
                    str(token_val).strip()
                    if isinstance(token_val, str)
                    else ""
                )
                cf_path = str(site.get("cloudflared_path") or "").strip()
                return True, token, cf_path
        return False, "", ""

    def restart_server(self):
        """Restart server."""
        site_name = str(self.local_site_combo.currentData() or "")
        if site_name:
            site = get_site("server", site_name)
            if site_requires_unlock(site):
                if not ensure_unlocked(self):
                    return
                self.on_site_selected(self.local_site_combo.currentIndex())

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

        try:
            use_cf, cf_token, cf_path = self.get_active_cf_settings()
        except (ValueError, TypeError):
            use_cf, cf_token, cf_path = False, "", ""
        if use_cf and not cf_token:
            QMessageBox.critical(
                self,
                t("Error"),
                t("Tunnel token required for Cloudflare Tunnel server."),
            )
            return

        if use_cf:
            init_usbip_server(
                port,
                secure,
                password,
                bind_host,
                use_cloudflared=True,
                cloudflared_token=cf_token,
                cloudflared_path=cf_path,
            )
        else:
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
