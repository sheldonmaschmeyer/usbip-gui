"""Client tab UI implementation."""

import sys
import time
from typing import Tuple

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
    QComboBox,
)

from usbip_gui.common import (
    SortableTreeWidgetItem,
    USBIPD_PORT,
    get_site,
    get_selected_site_name,
    get_translator,
    load_sites,
    set_min_column_widths,
    set_selected_site_name,
    site_requires_unlock,
    sites_updated,
)
from usbip_gui.common.common import configure_tree_widget_interaction
from usbip_gui.gui.dialogs import ensure_unlocked
from usbip_gui.product_detection import ItemUpdater, enrich_remote_device_item
from usbip_gui.typings import connect_signal, set_header_labels

from .operations import (
    attach_remote_usb,
    detach_remote_usb,
    list_attached_usb,
    list_remote_usb,
)
from .parsing import device_columns

t = get_translator("client")


class ClientTab(QWidget):
    """Client tab implementation for managing remote USB devices."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the class instance."""
        # pylint: disable=duplicate-code
        super().__init__(parent)

        self._item_updater = ItemUpdater(self)
        connect_signal(
            self._item_updater.update, self._item_updater.apply_text
        )

        layout = QVBoxLayout(self)

        self.remote_control_layout = QHBoxLayout()
        self.remote_site_label = QLabel(t("Site:"))
        self.remote_site_combo = QComboBox()
        self.remote_site_combo.setMinimumWidth(110)
        connect_signal(
            self.remote_site_combo.currentIndexChanged, self.on_site_selected
        )
        connect_signal(sites_updated.changed, self.on_sites_updated)

        self.remote_connect_button = QPushButton(t("Connect"))
        connect_signal(self.remote_connect_button.clicked, self.connect_site)

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

        self.remote_control_layout.addWidget(self.remote_site_label)
        self.remote_control_layout.addWidget(self.remote_site_combo)
        self.remote_control_layout.addWidget(self.remote_connect_button)
        self.remote_control_layout.addWidget(self.remote_list_label)
        self.remote_control_layout.addWidget(self.remote_ip_input)
        self.remote_control_layout.addWidget(self.remote_port_input)
        self.remote_control_layout.addWidget(self.remote_secure_checkbox)
        self.remote_control_layout.addWidget(self.remote_password_input)
        self.remote_control_layout.addWidget(self.remote_list_refresh_button)
        self.remote_control_layout.addWidget(self.remote_list_attach_button)
        self.remote_control_layout.addWidget(self.detach_button)
        self.remote_control_layout.addStretch()

        self.populate_site_combo()

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

    def populate_site_combo(self) -> None:
        """Populate the site dropdown with saved client sites."""
        current_data = self.remote_site_combo.currentData()
        selected_name = (
            str(current_data)
            if current_data
            else get_selected_site_name("client")
        )
        self.remote_site_combo.blockSignals(True)
        self.remote_site_combo.clear()
        self.remote_site_combo.addItem(t("Manual / Direct"), "")
        saved_sites = load_sites("client")
        selected_idx = 0
        for idx, site in enumerate(saved_sites, start=1):
            name = str(site.get("name", ""))
            self.remote_site_combo.addItem(name, name)
            if name == selected_name:
                selected_idx = idx
        self.remote_site_combo.setCurrentIndex(selected_idx)
        self.remote_site_combo.blockSignals(False)

    def _populate_site_combo(self) -> None:
        """Backwards-compatible alias for populate_site_combo."""
        self.populate_site_combo()

    def on_sites_updated(self, site_type: str) -> None:
        """Handle site configuration updates."""
        if site_type == "client":
            self.populate_site_combo()

    def _on_sites_updated(self, site_type: str) -> None:
        """Backwards-compatible alias for on_sites_updated."""
        self.on_sites_updated(site_type)

    def on_site_selected(self, _index: int) -> None:
        """Handle selection change in site dropdown."""
        site_name = str(self.remote_site_combo.currentData() or "")
        set_selected_site_name("client", site_name)
        if not site_name:
            return
        site = get_site("client", site_name)
        if not site:
            return
        conn_type = str(site.get("connection_type", "direct"))
        if conn_type == "cloudflared":
            self.remote_ip_input.setText(
                str(site.get("cloudflared_hostname", ""))
            )
        else:
            self.remote_ip_input.setText(str(site.get("host", "127.0.0.1")))
        self.remote_port_input.setText(str(site.get("port", USBIPD_PORT)))
        self.remote_secure_checkbox.blockSignals(True)
        self.remote_secure_checkbox.setChecked(bool(site.get("secure", True)))
        self.remote_secure_checkbox.blockSignals(False)
        pwd_val = site.get("password", "")
        self.remote_password_input.setText(
            str(pwd_val) if isinstance(pwd_val, str) else ""
        )

    def _on_site_selected(self, index: int) -> None:
        """Backwards-compatible alias for on_site_selected."""
        self.on_site_selected(index)

    def get_active_cf_settings(
        self,
    ) -> Tuple[bool, str, str, str, str]:
        """Return (use_cf, hostname, path, token_id, token_secret)."""
        site_name = str(self.remote_site_combo.currentData() or "")
        if site_name:
            site = get_site("client", site_name)
            if site and site.get("connection_type") == "cloudflared":
                cf_host = str(
                    site.get("cloudflared_hostname")
                    or self.remote_ip_input.text()
                ).strip()
                cf_path = str(site.get("cloudflared_path") or "").strip()
                token_id_val = site.get("cloudflared_token_id")
                cf_token_id = (
                    str(token_id_val).strip()
                    if isinstance(token_id_val, str)
                    else ""
                )
                secret_val = site.get("cloudflared_token_secret")
                cf_token_secret = (
                    str(secret_val).strip()
                    if isinstance(secret_val, str)
                    else ""
                )
                return (
                    True,
                    cf_host,
                    cf_path,
                    cf_token_id,
                    cf_token_secret,
                )
        return False, "", "", "", ""

    def _get_active_cf_settings(
        self,
    ) -> Tuple[bool, str, str, str, str]:
        """Backwards-compatible alias for get_active_cf_settings."""
        return self.get_active_cf_settings()

    def connect_site(self) -> None:
        """Connect to the selected site and populate remote devices."""
        self.refresh_remote()

    def check_secure_warning(self, state: int):
        """Check secure warning."""
        if state == 0:
            QMessageBox.warning(self, t("Warning"), t("insecure_warning_msg"))

    def refresh_remote(self):
        """Refresh remote."""
        site_name = str(self.remote_site_combo.currentData() or "")
        if site_name:
            site = get_site("client", site_name)
            if site_requires_unlock(site):
                if not ensure_unlocked(self):
                    return
                self.on_site_selected(self.remote_site_combo.currentIndex())

        server_ip = self.remote_ip_input.text()
        try:
            port = int(self.remote_port_input.text())
        except ValueError:
            QMessageBox.critical(self, t("Error"), t("Invalid port number"))
            return
        secure = self.remote_secure_checkbox.isChecked()
        password = self.remote_password_input.text()

        try:
            (
                use_cf,
                cf_hostname,
                cf_path,
                cf_token_id,
                cf_token_secret,
            ) = self.get_active_cf_settings()
        except (ValueError, TypeError):
            use_cf, cf_hostname, cf_path = False, "", ""
            cf_token_id, cf_token_secret = "", ""
        if use_cf and not cf_hostname:
            QMessageBox.critical(
                self,
                t("Error"),
                t(
                    "Cloudflare hostname required for Cloudflare "
                    "Tunnel connection."
                ),
            )
            return

        try:
            remote_devices = list_remote_usb(
                server_ip,
                port,
                secure,
                password,
                use_cloudflared=use_cf,
                cloudflared_hostname=cf_hostname,
                cloudflared_path=cf_path,
                service_token_id=cf_token_id,
                service_token_secret=cf_token_secret,
            )
            attached_devices = list_attached_usb()
        except OSError as error:
            QMessageBox.critical(
                self, t("Error"), t("usbip_client_missing_msg").format(error)
            )
            return
        self.remote_listbox.clear()

        attached_by_busid = {device[2]: device for device in attached_devices}

        for r_bus_id, vid_pid, manufacturer, description in remote_devices:
            status = t("Detached")
            local_port = -1
            if r_bus_id in attached_by_busid:
                status = t("Attached")
                attached = attached_by_busid.pop(r_bus_id)
                local_port = attached[1]

            display_ip = cf_hostname if use_cf and cf_hostname else server_ip
            item_data = [
                display_ip,
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

        try:
            (
                use_cf,
                cf_hostname,
                cf_path,
                cf_token_id,
                cf_token_secret,
            ) = self.get_active_cf_settings()
        except (ValueError, TypeError):
            use_cf, cf_hostname, cf_path = False, "", ""
            cf_token_id, cf_token_secret = "", ""
        if use_cf and not cf_hostname:
            QMessageBox.critical(
                self,
                t("Error"),
                t(
                    "Cloudflare hostname required for Cloudflare "
                    "Tunnel connection."
                ),
            )
            return

        result = attach_remote_usb(
            server_ip,
            bus_id,
            port,
            secure,
            password,
            use_cloudflared=use_cf,
            cloudflared_hostname=cf_hostname,
            cloudflared_path=cf_path,
            service_token_id=cf_token_id,
            service_token_secret=cf_token_secret,
        )
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
