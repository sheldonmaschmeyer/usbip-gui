"""Site configuration management dialog."""

from typing import Dict, List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QDialogButtonBox,
)
from usbip_gui.common import (
    get_translator,
    load_sites,
    save_all_sites,
    USBIPD_PORT,
)
from usbip_gui.common.common import JsonValue
from usbip_gui.typings import connect_signal

t = get_translator("site_config")

SiteData = Dict[str, JsonValue]

LABEL_WIDTH: int = 170


def _create_form_label(text: str) -> QLabel:
    """Create a standardized form label with fixed width and word wrap."""
    label = QLabel(text)
    label.setFixedWidth(LABEL_WIDTH)
    label.setWordWrap(True)
    return label


# pylint: disable=too-many-instance-attributes
class SiteTypeWidget(QWidget):
    """Editor widget for a specific category of sites (client or server)."""

    def __init__(
        self, site_type: str, parent: Optional[QWidget] = None
    ) -> None:
        """Initialize the site editor widget."""
        # pylint: disable=too-many-statements
        super().__init__(parent)
        self.site_type = site_type
        self.sites: List[SiteData] = load_sites(site_type)
        self.current_index: int = -1
        self._loading: bool = False

        main_layout = QHBoxLayout(self)

        # Left pane: site list and add/remove buttons
        left_layout = QVBoxLayout()
        self.site_list = QListWidget()
        connect_signal(
            self.site_list.currentRowChanged, self._on_site_selected
        )
        left_layout.addWidget(self.site_list)

        btn_row = QHBoxLayout()
        self.new_btn = QPushButton(t("New Site"))
        connect_signal(self.new_btn.clicked, self._on_new_site)
        self.del_btn = QPushButton(t("Delete Site"))
        connect_signal(self.del_btn.clicked, self._on_delete_site)
        btn_row.addWidget(self.new_btn)
        btn_row.addWidget(self.del_btn)
        left_layout.addLayout(btn_row)

        main_layout.addLayout(left_layout, stretch=1)

        # Right pane: stacked widget for placeholder or form editor
        self.right_stack = QStackedWidget()

        # Empty state placeholder
        self.empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_widget)
        self.empty_label = QLabel()
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        empty_layout.addStretch()
        empty_layout.addWidget(self.empty_label)
        empty_layout.addStretch()
        self.right_stack.addWidget(self.empty_widget)

        # Form editor
        self.form_widget = QWidget()
        form_layout = QVBoxLayout(self.form_widget)

        # Site Name
        name_row = QHBoxLayout()
        name_label = _create_form_label(t("Site Name:"))
        self.name_input = QLineEdit()
        connect_signal(self.name_input.textChanged, self._on_field_changed)
        name_row.addWidget(name_label)
        name_row.addWidget(self.name_input)
        form_layout.addLayout(name_row)

        # Connection Type
        type_row = QHBoxLayout()
        type_label = _create_form_label(t("Connection Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem(t("Direct (IP / Port)"), "direct")
        self.type_combo.addItem(t("Cloudflare Tunnel"), "cloudflared")
        connect_signal(
            self.type_combo.currentIndexChanged, self._on_type_changed
        )
        type_row.addWidget(type_label)
        type_row.addWidget(self.type_combo)
        form_layout.addLayout(type_row)

        # Host / IP (client direct) or Bind IP (server)
        host_row = QHBoxLayout()
        self.host_label = _create_form_label(
            t("Remote Host / IP:")
            if self.site_type == "client"
            else t("Bind IP:")
        )
        self.host_input = QLineEdit()
        connect_signal(self.host_input.textChanged, self._on_field_changed)
        host_row.addWidget(self.host_label)
        host_row.addWidget(self.host_input)
        form_layout.addLayout(host_row)

        # Port
        port_row = QHBoxLayout()
        port_label = _create_form_label(t("Port:"))
        self.port_input = QLineEdit()
        connect_signal(self.port_input.textChanged, self._on_field_changed)
        port_row.addWidget(port_label)
        port_row.addWidget(self.port_input)
        form_layout.addLayout(port_row)

        # Cloudflare Hostname (client) or Tunnel Token (server)
        cf_row = QHBoxLayout()
        self.cf_label = _create_form_label(
            t("Cloudflare Hostname:")
            if self.site_type == "client"
            else t("Cloudflare Tunnel Token:")
        )
        self.cf_input = QLineEdit()
        if self.site_type == "client":
            self.cf_input.setPlaceholderText("usbip.maschmeyer.ca")
        else:
            self.cf_input.setEchoMode(QLineEdit.EchoMode.Password)
        connect_signal(self.cf_input.textChanged, self._on_field_changed)
        cf_row.addWidget(self.cf_label)
        cf_row.addWidget(self.cf_input)
        form_layout.addLayout(cf_row)

        # Cloudflare Access Service Token (Client ID & Secret)
        self.cf_tokens_widget = QWidget()
        cf_tokens_layout = QVBoxLayout(self.cf_tokens_widget)
        cf_tokens_layout.setContentsMargins(0, 0, 0, 0)

        token_id_row = QHBoxLayout()
        token_id_label = _create_form_label(
            t("Service Token ID (Optional):")
        )
        self.cf_token_id_input = QLineEdit()
        connect_signal(
            self.cf_token_id_input.textChanged, self._on_field_changed
        )
        token_id_row.addWidget(token_id_label)
        token_id_row.addWidget(self.cf_token_id_input)
        cf_tokens_layout.addLayout(token_id_row)

        token_secret_row = QHBoxLayout()
        token_secret_label = _create_form_label(
            t("Service Token Secret (Optional):")
        )
        self.cf_token_secret_input = QLineEdit()
        self.cf_token_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        connect_signal(
            self.cf_token_secret_input.textChanged, self._on_field_changed
        )
        token_secret_row.addWidget(token_secret_label)
        token_secret_row.addWidget(self.cf_token_secret_input)
        cf_tokens_layout.addLayout(token_secret_row)

        form_layout.addWidget(self.cf_tokens_widget)

        # Security & Password
        sec_row = QHBoxLayout()
        self.secure_check = QCheckBox(t("Secure (SSL/TLS)"))
        connect_signal(self.secure_check.stateChanged, self._on_field_changed)
        sec_row.addWidget(self.secure_check)
        form_layout.addLayout(sec_row)

        pwd_row = QHBoxLayout()
        pwd_label = _create_form_label(t("Password:"))
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        connect_signal(self.pwd_input.textChanged, self._on_field_changed)
        pwd_row.addWidget(pwd_label)
        pwd_row.addWidget(self.pwd_input)
        form_layout.addLayout(pwd_row)

        # Custom cloudflared path
        cf_path_row = QHBoxLayout()
        self.cf_path_label = _create_form_label(
            t("Custom cloudflared Path (Optional):")
        )
        self.cf_path_input = QLineEdit()
        connect_signal(self.cf_path_input.textChanged, self._on_field_changed)
        self.browse_btn = QPushButton(t("Browse..."))
        connect_signal(self.browse_btn.clicked, self._on_browse_cloudflared)
        cf_path_row.addWidget(self.cf_path_label)
        cf_path_row.addWidget(self.cf_path_input)
        cf_path_row.addWidget(self.browse_btn)
        form_layout.addLayout(cf_path_row)

        form_layout.addStretch()
        self.right_stack.addWidget(self.form_widget)
        main_layout.addWidget(self.right_stack, stretch=2)

        self._populate_list()

    def _populate_list(self) -> None:
        """Populate the QListWidget with current sites."""
        self.site_list.clear()
        for s in self.sites:
            name = str(s.get("name", ""))
            self.site_list.addItem(QListWidgetItem(name))
        if self.sites:
            self.site_list.setCurrentRow(0)
        else:
            self._clear_form()
            self.form_widget.setEnabled(False)
            self.del_btn.setEnabled(False)
            self.empty_label.setText(
                t("No sites configured. Click 'New Site' to add one.")
            )
            self.right_stack.setCurrentWidget(self.empty_widget)

    def _on_site_selected(self, row: int) -> None:
        """Handle selection change in site list."""
        if row < 0 or row >= len(self.sites):
            self.current_index = -1
            self.form_widget.setEnabled(False)
            self.del_btn.setEnabled(False)
            self.empty_label.setText(
                t("No sites configured. Click 'New Site' to add one.")
                if not self.sites
                else t("No site selected.")
            )
            self.right_stack.setCurrentWidget(self.empty_widget)
            return

        self.current_index = row
        self.form_widget.setEnabled(True)
        self.del_btn.setEnabled(True)
        self.right_stack.setCurrentWidget(self.form_widget)
        site = self.sites[row]

        self._loading = True
        try:
            self.name_input.setText(str(site.get("name", "")))
            conn_type = str(site.get("connection_type", "direct"))
            idx = 1 if conn_type == "cloudflared" else 0
            self.type_combo.setCurrentIndex(idx)

            if self.site_type == "client":
                self.host_input.setText(str(site.get("host", "127.0.0.1")))
                self.cf_input.setText(
                    str(site.get("cloudflared_hostname", ""))
                )
                self.cf_token_id_input.setText(
                    str(site.get("cloudflared_token_id", ""))
                )
                self.cf_token_secret_input.setText(
                    str(site.get("cloudflared_token_secret", ""))
                )
            else:
                self.host_input.setText(str(site.get("bind_ip", "0.0.0.0")))
                self.cf_input.setText(str(site.get("cloudflared_token", "")))

            self.port_input.setText(str(site.get("port", USBIPD_PORT)))
            self.secure_check.setChecked(bool(site.get("secure", True)))
            self.pwd_input.setText(str(site.get("password", "")))
            self.cf_path_input.setText(str(site.get("cloudflared_path", "")))

            self._update_visibility(conn_type)
        finally:
            self._loading = False

    def _update_visibility(self, conn_type: str) -> None:
        """Show or hide fields according to connection type."""
        is_cf = conn_type == "cloudflared"
        if self.site_type == "client":
            self.host_label.setVisible(not is_cf)
            self.host_input.setVisible(not is_cf)
            self.cf_label.setVisible(is_cf)
            self.cf_input.setVisible(is_cf)
            self.cf_tokens_widget.setVisible(is_cf)
        else:
            # Server shows host/bind_ip in both, but cf_row only in cloudflared
            self.cf_label.setVisible(is_cf)
            self.cf_input.setVisible(is_cf)
            self.cf_tokens_widget.setVisible(False)
        self.cf_path_label.setEnabled(is_cf)
        self.cf_path_input.setEnabled(is_cf)
        self.browse_btn.setEnabled(is_cf)

    def _on_type_changed(self, index: int) -> None:
        """Handle connection type dropdown switch."""
        conn_type = "cloudflared" if index == 1 else "direct"
        self._update_visibility(conn_type)
        self._on_field_changed()

    def _on_field_changed(self, *_args: object) -> None:
        """Save form modifications back into in-memory site data."""
        if self._loading:
            return
        if self.current_index < 0 or self.current_index >= len(self.sites):
            return

        name = self.name_input.text().strip()
        conn_type = (
            "cloudflared" if self.type_combo.currentIndex() == 1 else "direct"
        )
        port_val: JsonValue = USBIPD_PORT
        try:
            port_val = int(self.port_input.text().strip())
        except ValueError:
            pass

        site = self.sites[self.current_index]
        site["name"] = name
        site["connection_type"] = conn_type
        site["port"] = port_val
        site["secure"] = self.secure_check.isChecked()
        site["password"] = self.pwd_input.text()
        site["cloudflared_path"] = self.cf_path_input.text().strip()

        if self.site_type == "client":
            site["host"] = self.host_input.text().strip()
            site["cloudflared_hostname"] = self.cf_input.text().strip()
            site["cloudflared_token_id"] = (
                self.cf_token_id_input.text().strip()
            )
            site["cloudflared_token_secret"] = (
                self.cf_token_secret_input.text().strip()
            )
        else:
            site["bind_ip"] = self.host_input.text().strip()
            site["cloudflared_token"] = self.cf_input.text().strip()

        # Update item label in list
        item = self.site_list.item(self.current_index)
        if item and item.text() != name:
            item.setText(name)

    def _on_new_site(self) -> None:
        """Create a new site profile."""
        base_name = "New Site"
        count = 1
        existing_names = {str(s.get("name", "")) for s in self.sites}
        new_name = base_name
        while new_name in existing_names:
            count += 1
            new_name = f"{base_name} {count}"

        new_site: SiteData = {
            "name": new_name,
            "connection_type": "direct",
            "port": USBIPD_PORT,
            "secure": True,
            "password": "",
            "cloudflared_path": "",
        }
        if self.site_type == "client":
            new_site["host"] = "127.0.0.1"
            new_site["cloudflared_hostname"] = ""
            new_site["cloudflared_token_id"] = ""
            new_site["cloudflared_token_secret"] = ""
        else:
            new_site["bind_ip"] = "0.0.0.0"
            new_site["cloudflared_token"] = ""

        self.sites.append(new_site)
        item = QListWidgetItem(new_name)
        self.site_list.addItem(item)
        self.site_list.setCurrentItem(item)

    def _on_delete_site(self) -> None:
        """Remove the selected site profile."""
        if self.current_index < 0 or self.current_index >= len(self.sites):
            return
        name = str(self.sites[self.current_index].get("name", ""))
        reply = QMessageBox.question(
            self,
            t("Delete Confirmation"),
            t("Are you sure you want to delete site '{}'?").format(name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.sites.pop(self.current_index)
            self._populate_list()

    def _on_browse_cloudflared(self) -> None:
        """Open file dialog to browse for cloudflared executable."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("Custom cloudflared Path (Optional):"),
            "",
            "Executable Files (*.exe *);;All Files (*)",
        )
        if path:
            self.cf_path_input.setText(path)

    def _clear_form(self) -> None:
        """Reset all form fields."""
        self.name_input.clear()
        self.host_input.clear()
        self.port_input.clear()
        self.cf_input.clear()
        self.cf_token_id_input.clear()
        self.cf_token_secret_input.clear()
        self.pwd_input.clear()
        self.cf_path_input.clear()


class SiteConfigDialog(QDialog):
    """Main modal dialog for managing Site Configurations."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the site configuration dialog."""
        super().__init__(parent)
        self.setWindowTitle(t("Site Configuration"))
        self.resize(740, 500)

        dialog_layout = QVBoxLayout(self)

        self.tabs = QTabWidget(self)
        self.client_widget = SiteTypeWidget("client", self)
        self.server_widget = SiteTypeWidget("server", self)
        self.tabs.addTab(self.client_widget, t("Client Sites"))
        self.tabs.addTab(self.server_widget, t("Server Sites"))
        dialog_layout.addWidget(self.tabs)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        connect_signal(self.button_box.accepted, self._on_save)
        connect_signal(self.button_box.rejected, self.reject)
        dialog_layout.addWidget(self.button_box)

    def _validate_sites(self, widget: SiteTypeWidget) -> bool:
        """Validate site entries before saving."""
        seen_names: set[str] = set()
        for s in widget.sites:
            name = str(s.get("name", "")).strip()
            if not name:
                QMessageBox.warning(
                    self,
                    t("Validation Error"),
                    t("Site name cannot be empty."),
                )
                return False
            if name in seen_names:
                QMessageBox.warning(
                    self,
                    t("Validation Error"),
                    t("A site with this name already exists."),
                )
                return False
            seen_names.add(name)

            try:
                port = int(str(s.get("port", USBIPD_PORT)))
                if port < 1 or port > 65535:
                    raise ValueError
            except ValueError:
                QMessageBox.warning(
                    self,
                    t("Validation Error"),
                    t("Please specify a valid port number."),
                )
                return False
        return True

    def _on_save(self) -> None:
        """Save sites to settings file and accept dialog."""
        if not self._validate_sites(self.client_widget):
            self.tabs.setCurrentWidget(self.client_widget)
            return
        if not self._validate_sites(self.server_widget):
            self.tabs.setCurrentWidget(self.server_widget)
            return

        save_all_sites("client", self.client_widget.sites)
        save_all_sites("server", self.server_widget.sites)
        self.accept()


def show_site_config_dialog(parent: Optional[QWidget] = None) -> None:
    """Show the Site Configuration dialog."""
    dialog = SiteConfigDialog(parent)
    dialog.exec()
