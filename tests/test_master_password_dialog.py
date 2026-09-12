"""Unit tests for master password dialogs."""

from unittest.mock import patch
from PyQt6.QtWidgets import QDialog, QMessageBox
from usbip_gui.gui.dialogs.master_password import (
    ChangeMasterPasswordDialog,
    MasterPasswordManagementDialog,
    SetMasterPasswordDialog,
    UnlockMasterPasswordDialog,
    ensure_unlocked,
)


def test_unlock_dialog_empty_password():
    """Test unlock dialog with empty password shows error."""
    dlg = UnlockMasterPasswordDialog()

    dlg.password_input.setText("")
    dlg.on_unlock()

    assert not dlg.error_label.isHidden()
    assert "Please enter" in dlg.error_label.text()


def test_unlock_dialog_wrong_password():
    """Test unlock dialog with incorrect password."""
    dlg = UnlockMasterPasswordDialog()

    with patch(
        "usbip_gui.gui.dialogs.master_password.unlock_master_password",
        return_value=False,
    ):
        dlg.password_input.setText("wrongpwd")
        dlg.on_unlock()

        assert not dlg.error_label.isHidden()
        assert "Incorrect" in dlg.error_label.text()
        assert dlg.password_input.text() == ""


def test_unlock_dialog_success():
    """Test unlock dialog accepts on valid password."""
    dlg = UnlockMasterPasswordDialog()

    with patch(
        "usbip_gui.gui.dialogs.master_password.unlock_master_password",
        return_value=True,
    ):
        with patch.object(dlg, "accept") as mock_accept:
            dlg.password_input.setText("correctpwd")
            dlg.on_unlock()
            mock_accept.assert_called_once()


def test_unlock_dialog_reset_cancel_and_confirm():
    """Test forgot/reset button in unlock dialog."""
    dlg = UnlockMasterPasswordDialog()

    # Cancel confirmation
    with patch(
        "usbip_gui.gui.dialogs.master_password.QMessageBox.warning",
        return_value=QMessageBox.StandardButton.No,
    ):
        with patch(
            "usbip_gui.gui.dialogs.master_password.reset_storage"
        ) as mock_reset:
            dlg.on_reset()
            mock_reset.assert_not_called()

    # Confirm reset
    with patch(
        "usbip_gui.gui.dialogs.master_password.QMessageBox.warning",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        with patch(
            "usbip_gui.gui.dialogs.master_password.reset_storage"
        ) as mock_reset:
            with patch(
                "usbip_gui.gui.dialogs.master_password.QMessageBox.information"
            ):
                with patch.object(dlg, "accept") as mock_accept:
                    dlg.on_reset()
                    mock_reset.assert_called_once()
                    mock_accept.assert_called_once()


def test_set_master_password_dialog():
    """Test SetMasterPasswordDialog validations and submit."""
    dlg = SetMasterPasswordDialog()

    # 1. Empty password
    dlg.new_pwd_input.setText("")
    dlg.confirm_pwd_input.setText("")
    dlg.on_save()
    assert not dlg.error_label.isHidden()
    assert "cannot be empty" in dlg.error_label.text()

    # 2. Mismatched passwords
    dlg.new_pwd_input.setText("password123")
    dlg.confirm_pwd_input.setText("mismatch")
    dlg.on_save()
    assert not dlg.error_label.isHidden()
    assert "do not match" in dlg.error_label.text()

    # 3. Successful set
    dlg.new_pwd_input.setText("password123")
    dlg.confirm_pwd_input.setText("password123")
    with patch(
        "usbip_gui.gui.dialogs.master_password.set_master_password"
    ) as mock_set:
        with patch(
            "usbip_gui.gui.dialogs.master_password.QMessageBox.information"
        ):
            with patch.object(dlg, "accept") as mock_accept:
                dlg.on_save()
                mock_set.assert_called_once_with("password123")
                mock_accept.assert_called_once()


def test_change_master_password_dialog():
    """Test ChangeMasterPasswordDialog validations and submit."""
    dlg = ChangeMasterPasswordDialog()

    # Empty current
    dlg.curr_pwd_input.setText("")
    dlg.on_change()
    assert not dlg.error_label.isHidden()

    # Empty new
    dlg.curr_pwd_input.setText("curr")
    dlg.new_pwd_input.setText("")
    dlg.on_change()
    assert not dlg.error_label.isHidden()

    # Mismatched new
    dlg.new_pwd_input.setText("new1")
    dlg.confirm_pwd_input.setText("new2")
    dlg.on_change()
    assert not dlg.error_label.isHidden()

    # Failed change (wrong current)
    dlg.confirm_pwd_input.setText("new1")
    with patch(
        "usbip_gui.gui.dialogs.master_password.change_master_password",
        return_value=False,
    ):
        dlg.on_change()
        assert not dlg.error_label.isHidden()
        assert "incorrect" in dlg.error_label.text()

    # Successful change
    with patch(
        "usbip_gui.gui.dialogs.master_password.change_master_password",
        return_value=True,
    ):
        with patch(
            "usbip_gui.gui.dialogs.master_password.QMessageBox.information"
        ):
            with patch.object(dlg, "accept") as mock_accept:
                dlg.on_change()
                mock_accept.assert_called_once()


def test_master_password_management_dialog():
    """Test MasterPasswordManagementDialog tabs."""
    dlg = MasterPasswordManagementDialog()

    # Change password tab validations
    dlg.chg_curr_pwd.setText("")
    dlg.on_change_password()
    assert not dlg.chg_error_label.isHidden()

    dlg.chg_curr_pwd.setText("cur")
    dlg.chg_new_pwd.setText("")
    dlg.on_change_password()
    assert not dlg.chg_error_label.isHidden()

    dlg.chg_new_pwd.setText("new1")
    dlg.chg_conf_pwd.setText("new2")
    dlg.on_change_password()
    assert not dlg.chg_error_label.isHidden()

    # Change failed
    dlg.chg_conf_pwd.setText("new1")
    with patch(
        "usbip_gui.gui.dialogs.master_password.change_master_password",
        return_value=False,
    ):
        dlg.on_change_password()
        assert not dlg.chg_error_label.isHidden()

    # Change success
    with patch(
        "usbip_gui.gui.dialogs.master_password.change_master_password",
        return_value=True,
    ):
        with patch(
            "usbip_gui.gui.dialogs.master_password.QMessageBox.information"
        ):
            with patch.object(dlg, "accept") as mock_accept:
                dlg.on_change_password()
                mock_accept.assert_called_once()

    # Remove password tab validations
    dlg.rem_curr_pwd.setText("")
    dlg.on_remove_password()
    assert not dlg.rem_error_label.isHidden()

    dlg.rem_curr_pwd.setText("cur")
    # Cancel removal confirmation
    with patch(
        "usbip_gui.gui.dialogs.master_password.QMessageBox.warning",
        return_value=QMessageBox.StandardButton.No,
    ):
        with patch(
            "usbip_gui.gui.dialogs.master_password.remove_master_password"
        ) as mock_rem:
            dlg.on_remove_password()
            mock_rem.assert_not_called()

    # Confirm removal - failed
    with patch(
        "usbip_gui.gui.dialogs.master_password.QMessageBox.warning",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        with patch(
            "usbip_gui.gui.dialogs.master_password.remove_master_password",
            return_value=False,
        ):
            dlg.on_remove_password()
            assert not dlg.rem_error_label.isHidden()

    # Confirm removal - success
    with patch(
        "usbip_gui.gui.dialogs.master_password.QMessageBox.warning",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        with patch(
            "usbip_gui.gui.dialogs.master_password.remove_master_password",
            return_value=True,
        ):
            with patch(
                "usbip_gui.gui.dialogs.master_password.QMessageBox.information"
            ):
                with patch.object(dlg, "accept") as mock_accept:
                    dlg.on_remove_password()
                    mock_accept.assert_called_once()


def test_ensure_unlocked():
    """Test ensure_unlocked helper function."""
    # 1. Not configured -> returns True
    with patch(
        "usbip_gui.gui.dialogs.master_password.is_master_password_configured",
        return_value=False,
    ):
        assert ensure_unlocked() is True

    # 2. Configured and already unlocked -> returns True (unless force=True)
    mp_mod = "usbip_gui.gui.dialogs.master_password"
    with patch(f"{mp_mod}.is_master_password_configured", return_value=True):
        with patch(f"{mp_mod}.is_master_password_unlocked", return_value=True):
            assert ensure_unlocked() is True
            # With force=True, prompts dialog even if unlocked
            with patch.object(
                UnlockMasterPasswordDialog,
                "exec",
                return_value=QDialog.DialogCode.Accepted,
            ):
                assert ensure_unlocked(force=True) is True

    # 3. Configured and locked -> prompts dialog
    with patch(f"{mp_mod}.is_master_password_configured", return_value=True):
        with patch(
            f"{mp_mod}.is_master_password_unlocked", return_value=False
        ):
            with patch.object(
                UnlockMasterPasswordDialog,
                "exec",
                return_value=QDialog.DialogCode.Accepted,
            ):
                assert ensure_unlocked() is True

            with patch.object(
                UnlockMasterPasswordDialog,
                "exec",
                return_value=QDialog.DialogCode.Rejected,
            ):
                assert ensure_unlocked() is False
