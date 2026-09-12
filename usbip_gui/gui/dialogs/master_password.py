"""Master password dialogs for setting, unlocking, and managing credentials."""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QMessageBox,
    QDialogButtonBox,
)

from usbip_gui.common import (
    change_master_password,
    get_translator,
    is_master_password_configured,
    is_master_password_unlocked,
    remove_master_password,
    reset_storage,
    set_master_password,
    unlock_master_password,
)
from usbip_gui.typings import connect_signal

t = get_translator("master_password")


class UnlockMasterPasswordDialog(QDialog):
    """Dialog prompting the user to unlock encrypted credentials."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the unlock dialog."""
        super().__init__(parent)
        self.setWindowTitle(t("Enter Master Password"))
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        desc_label = QLabel(
            t("Enter your Master Password to unlock stored credentials:")
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(t("Master Password"))
        connect_signal(self.password_input.returnPressed, self._on_unlock)
        layout.addWidget(self.password_input)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #d20f39;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton(t("Reset Storage..."))
        connect_signal(self.reset_btn.clicked, self._on_reset)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()

        self.unlock_btn = QPushButton(t("Unlock"))
        self.unlock_btn.setDefault(True)
        connect_signal(self.unlock_btn.clicked, self._on_unlock)
        btn_layout.addWidget(self.unlock_btn)

        self.cancel_btn = QPushButton(t("Cancel"))
        connect_signal(self.cancel_btn.clicked, self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def _on_unlock(self) -> None:
        """Verify the password and accept if valid."""
        pwd = self.password_input.text()
        if not pwd:
            self.error_label.setText(t("Please enter your Master Password."))
            self.error_label.show()
            return

        if unlock_master_password(pwd):
            self.accept()
        else:
            self.error_label.setText(
                t("Incorrect Master Password. Please try again.")
            )
            self.error_label.show()
            self.password_input.clear()
            self.password_input.setFocus()

    def on_unlock(self) -> None:
        """Public wrapper for unlock submission."""
        self._on_unlock()

    def _on_reset(self) -> None:
        """Prompt confirmation to reset storage and master password."""
        confirm = QMessageBox.warning(
            self,
            t("Reset Storage"),
            t(
                "Resetting storage will permanently erase all saved site "
                "configurations and remove Master Password protection.\n\n"
                "Are you sure you want to proceed?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            reset_storage()
            QMessageBox.information(
                self,
                t("Storage Reset"),
                t(
                    "All site configurations and Master Password have been "
                    "reset."
                ),
            )
            self.accept()

    def on_reset(self) -> None:
        """Public wrapper for storage reset."""
        self._on_reset()


class SetMasterPasswordDialog(QDialog):
    """Dialog for configuring a new master password."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the set master password dialog."""
        super().__init__(parent)
        self.setWindowTitle(t("Set Master Password"))
        self.setMinimumWidth(480)
        self.setMinimumHeight(200)

        layout = QVBoxLayout(self)

        notice = QLabel(
            t(
                "Protect sensitive site credentials (passwords, Cloudflare "
                "tokens and secrets) with AES-256 encryption.\n\n"
                "Important: There is no password recovery. If forgotten, "
                "stored secrets must be reset and re-entered."
            )
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)

        new_row = QHBoxLayout()
        new_label = QLabel(t("Master Password:"))
        new_label.setFixedWidth(140)
        self.new_pwd_input = QLineEdit()
        self.new_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        new_row.addWidget(new_label)
        new_row.addWidget(self.new_pwd_input)
        layout.addLayout(new_row)

        confirm_row = QHBoxLayout()
        confirm_label = QLabel(t("Confirm Password:"))
        confirm_label.setFixedWidth(140)
        self.confirm_pwd_input = QLineEdit()
        self.confirm_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_row.addWidget(confirm_label)
        confirm_row.addWidget(self.confirm_pwd_input)
        layout.addLayout(confirm_row)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #d20f39;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        connect_signal(btn_box.accepted, self._on_save)
        connect_signal(btn_box.rejected, self.reject)
        layout.addWidget(btn_box)

    def _on_save(self) -> None:
        """Validate passwords and set new master password."""
        pwd = self.new_pwd_input.text()
        confirm = self.confirm_pwd_input.text()

        if not pwd:
            self.error_label.setText(t("Password cannot be empty."))
            self.error_label.show()
            return
        if pwd != confirm:
            self.error_label.setText(t("Passwords do not match."))
            self.error_label.show()
            return

        set_master_password(pwd)
        QMessageBox.information(
            self,
            t("Master Password Enabled"),
            t("Master Password has been set and site credentials encrypted."),
        )
        self.accept()

    def on_save(self) -> None:
        """Public wrapper for setting a master password."""
        self._on_save()


class ChangeMasterPasswordDialog(QDialog):
    """Dialog for changing the current master password."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the change master password dialog."""
        super().__init__(parent)
        self.setWindowTitle(t("Change Master Password"))
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        curr_row = QHBoxLayout()
        curr_label = QLabel(t("Current Password:"))
        curr_label.setFixedWidth(140)
        self.curr_pwd_input = QLineEdit()
        self.curr_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        curr_row.addWidget(curr_label)
        curr_row.addWidget(self.curr_pwd_input)
        layout.addLayout(curr_row)

        new_row = QHBoxLayout()
        new_label = QLabel(t("New Password:"))
        new_label.setFixedWidth(140)
        self.new_pwd_input = QLineEdit()
        self.new_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        new_row.addWidget(new_label)
        new_row.addWidget(self.new_pwd_input)
        layout.addLayout(new_row)

        confirm_row = QHBoxLayout()
        confirm_label = QLabel(t("Confirm Password:"))
        confirm_label.setFixedWidth(140)
        self.confirm_pwd_input = QLineEdit()
        self.confirm_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_row.addWidget(confirm_label)
        confirm_row.addWidget(self.confirm_pwd_input)
        layout.addLayout(confirm_row)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #d20f39;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        connect_signal(btn_box.accepted, self._on_change)
        connect_signal(btn_box.rejected, self.reject)
        layout.addWidget(btn_box)

    def _on_change(self) -> None:
        """Validate input and update the master password."""
        curr_pwd = self.curr_pwd_input.text()
        new_pwd = self.new_pwd_input.text()
        confirm_pwd = self.confirm_pwd_input.text()

        if not curr_pwd:
            self.error_label.setText(t("Current password cannot be empty."))
            self.error_label.show()
            return
        if not new_pwd:
            self.error_label.setText(t("New password cannot be empty."))
            self.error_label.show()
            return
        if new_pwd != confirm_pwd:
            self.error_label.setText(t("New passwords do not match."))
            self.error_label.show()
            return

        if change_master_password(curr_pwd, new_pwd):
            QMessageBox.information(
                self,
                t("Success"),
                t("Master Password has been changed successfully."),
            )
            self.accept()
        else:
            self.error_label.setText(t("Current password is incorrect."))
            self.error_label.show()

    def on_change(self) -> None:
        """Public wrapper for changing a master password."""
        self._on_change()


class MasterPasswordManagementDialog(QDialog):
    """Dialog for managing (changing or removing) the master password."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the master password management dialog."""
        super().__init__(parent)
        self.setWindowTitle(t("Master Password Settings"))
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_change_tab(), t("Change Password"))
        self.tabs.addTab(self._create_remove_tab(), t("Remove Password"))
        layout.addWidget(self.tabs)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        connect_signal(close_box.rejected, self.accept)
        layout.addWidget(close_box)

    def _create_change_tab(self) -> QWidget:
        """Create and return the change password tab widget."""
        change_widget = QWidget()
        change_layout = QVBoxLayout(change_widget)

        curr_row = QHBoxLayout()
        curr_label = QLabel(t("Current Password:"))
        curr_label.setFixedWidth(140)
        self.chg_curr_pwd = QLineEdit()
        self.chg_curr_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        curr_row.addWidget(curr_label)
        curr_row.addWidget(self.chg_curr_pwd)
        change_layout.addLayout(curr_row)

        new_row = QHBoxLayout()
        new_label = QLabel(t("New Password:"))
        new_label.setFixedWidth(140)
        self.chg_new_pwd = QLineEdit()
        self.chg_new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        new_row.addWidget(new_label)
        new_row.addWidget(self.chg_new_pwd)
        change_layout.addLayout(new_row)

        conf_row = QHBoxLayout()
        conf_label = QLabel(t("Confirm Password:"))
        conf_label.setFixedWidth(140)
        self.chg_conf_pwd = QLineEdit()
        self.chg_conf_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        conf_row.addWidget(conf_label)
        conf_row.addWidget(self.chg_conf_pwd)
        change_layout.addLayout(conf_row)

        self.chg_error_label = QLabel()
        self.chg_error_label.setStyleSheet("color: #d20f39;")
        self.chg_error_label.setWordWrap(True)
        self.chg_error_label.hide()
        change_layout.addWidget(self.chg_error_label)

        chg_btn_row = QHBoxLayout()
        chg_btn_row.addStretch()
        self.chg_submit_btn = QPushButton(t("Change Password"))
        connect_signal(self.chg_submit_btn.clicked, self._on_change_password)
        chg_btn_row.addWidget(self.chg_submit_btn)
        change_layout.addLayout(chg_btn_row)
        change_layout.addStretch()

        return change_widget

    def _create_remove_tab(self) -> QWidget:
        """Create and return the remove password tab widget."""
        remove_widget = QWidget()
        remove_layout = QVBoxLayout(remove_widget)

        rem_desc = QLabel(
            t(
                "Removing the Master Password will decrypt all site "
                "credentials. Credentials will be stored in plain text with "
                "restricted user permissions (0600).\n"
            )
        )
        rem_desc.setWordWrap(True)
        remove_layout.addWidget(rem_desc)

        rem_row = QHBoxLayout()
        rem_label = QLabel(t("Current Password:"))
        rem_label.setFixedWidth(140)
        self.rem_curr_pwd = QLineEdit()
        self.rem_curr_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        rem_row.addWidget(rem_label)
        rem_row.addWidget(self.rem_curr_pwd)
        remove_layout.addLayout(rem_row)

        self.rem_error_label = QLabel()
        self.rem_error_label.setStyleSheet("color: #d20f39;")
        self.rem_error_label.setWordWrap(True)
        self.rem_error_label.hide()
        remove_layout.addWidget(self.rem_error_label)

        rem_btn_row = QHBoxLayout()
        rem_btn_row.addStretch()
        self.rem_submit_btn = QPushButton(t("Remove Master Password"))
        connect_signal(self.rem_submit_btn.clicked, self._on_remove_password)
        rem_btn_row.addWidget(self.rem_submit_btn)
        remove_layout.addLayout(rem_btn_row)
        remove_layout.addStretch()

        return remove_widget

    def _on_change_password(self) -> None:
        """Handle change password button click."""
        curr_pwd = self.chg_curr_pwd.text()
        new_pwd = self.chg_new_pwd.text()
        conf_pwd = self.chg_conf_pwd.text()

        if not curr_pwd:
            self.chg_error_label.setText(
                t("Current password cannot be empty.")
            )
            self.chg_error_label.show()
            return
        if not new_pwd:
            self.chg_error_label.setText(t("New password cannot be empty."))
            self.chg_error_label.show()
            return
        if new_pwd != conf_pwd:
            self.chg_error_label.setText(t("New passwords do not match."))
            self.chg_error_label.show()
            return

        if change_master_password(curr_pwd, new_pwd):
            QMessageBox.information(
                self,
                t("Success"),
                t("Master Password has been changed successfully."),
            )
            self.accept()
        else:
            self.chg_error_label.setText(t("Current password is incorrect."))
            self.chg_error_label.show()

    def on_change_password(self) -> None:
        """Public wrapper for the change-password tab action."""
        self._on_change_password()

    def _on_remove_password(self) -> None:
        """Handle remove password button click."""
        curr_pwd = self.rem_curr_pwd.text()
        if not curr_pwd:
            self.rem_error_label.setText(
                t("Current password cannot be empty.")
            )
            self.rem_error_label.show()
            return

        confirm = QMessageBox.warning(
            self,
            t("Remove Master Password"),
            t(
                "Are you sure you want to remove Master Password protection?\n"
                "Credentials will be stored in plain text."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        if remove_master_password(curr_pwd):
            QMessageBox.information(
                self,
                t("Master Password Removed"),
                t(
                    "Master Password removed. "
                    "Credentials stored in plain text."
                ),
            )
            self.accept()
        else:
            self.rem_error_label.setText(t("Current password is incorrect."))
            self.rem_error_label.show()

    def on_remove_password(self) -> None:
        """Public wrapper for the remove-password tab action."""
        self._on_remove_password()


def ensure_unlocked(
    parent: Optional[QWidget] = None, force: bool = False
) -> bool:
    """
    Ensure the session master key is unlocked.

    If locked (or forced), prompts the user with UnlockMasterPasswordDialog.

    Args:
        parent: Optional parent QWidget.
        force: If True, prompt even if already unlocked in memory.

    Returns:
        bool: True if unlocked or no master password, False if cancelled.
    """
    if not is_master_password_configured():
        return True
    if is_master_password_unlocked() and not force:
        return True
    dlg = UnlockMasterPasswordDialog(parent)
    return dlg.exec() == int(QDialog.DialogCode.Accepted)
