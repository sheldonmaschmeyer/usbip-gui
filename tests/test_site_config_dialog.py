"""Unit tests for the site configuration GUI dialog and widget."""

# pylint: disable=protected-access

from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QDialog, QMessageBox
from usbip_gui.gui.menu.site_config import (
    SiteTypeWidget,
    SiteConfigDialog,
    show_site_config_dialog,
    create_status_icon,
    get_saved_icon,
    get_unsaved_icon,
    normalize_site,
)


def test_site_type_widget_empty_init():
    """Test SiteTypeWidget initializes cleanly with no saved sites."""
    with patch("usbip_gui.gui.menu.site_config.load_sites", return_value=[]):
        widget = SiteTypeWidget("client")
        assert widget.site_list.count() == 0
        assert widget.current_index == -1
        assert not widget.form_widget.isEnabled()
        assert widget.form_widget.isHidden()
        assert not widget.empty_widget.isHidden()
        assert not widget.del_btn.isEnabled()
        assert "No sites configured" in widget.empty_label.text()


def test_site_type_widget_client_direct_and_cf():
    """Test SiteTypeWidget with populated client sites (direct and CF)."""
    mock_sites = [
        {
            "name": "Direct Client",
            "connection_type": "direct",
            "host": "192.168.1.100",
            "port": 3240,
            "secure": False,
            "password": "pass",
            "cloudflared_path": "",
        },
        {
            "name": "CF Client",
            "connection_type": "cloudflared",
            "cloudflared_hostname": "usbip.maschmeyer.ca",
            "cloudflared_token_id": "tok_id_123",
            "cloudflared_token_secret": "tok_sec_456",
            "port": 3240,
            "secure": True,
            "password": "pass",
            "cloudflared_path": "/usr/bin/cloudflared",
        },
    ]
    with patch(
        "usbip_gui.gui.menu.site_config.load_sites", return_value=mock_sites
    ):
        widget = SiteTypeWidget("client")
        assert widget.site_list.count() == 2
        assert widget.current_index == 0
        assert not widget.form_widget.isHidden()
        assert widget.empty_widget.isHidden()
        assert widget.del_btn.isEnabled()
        assert widget.name_input.text() == "Direct Client"
        assert not widget.host_input.isHidden()
        assert widget.cf_input.isHidden()
        assert widget.cf_tokens_widget.isHidden()
        assert widget.host_label.wordWrap()
        assert widget.cf_label.wordWrap()
        assert widget.cf_path_label.wordWrap()

        # Switch to CF Client
        widget.on_site_selected(1)
        assert widget.current_index == 1
        assert widget.name_input.text() == "CF Client"
        assert widget.host_input.isHidden()
        assert not widget.cf_input.isHidden()
        assert widget.cf_input.text() == "usbip.maschmeyer.ca"
        assert not widget.cf_tokens_widget.isHidden()
        assert widget.cf_token_id_input.text() == "tok_id_123"
        assert widget.cf_token_secret_input.text() == "tok_sec_456"

        # Out-of-bounds selection
        widget.on_site_selected(-1)
        assert widget.current_index == -1
        assert not widget.form_widget.isEnabled()
        assert widget.form_widget.isHidden()
        assert not widget.empty_widget.isHidden()
        assert "No site selected" in widget.empty_label.text()


def test_site_type_widget_server_sites():
    """Test SiteTypeWidget with server sites."""
    mock_sites = [
        {
            "name": "Direct Server",
            "connection_type": "direct",
            "bind_ip": "0.0.0.0",
            "port": 3240,
            "secure": True,
            "password": "secret",
            "cloudflared_path": "",
        },
        {
            "name": "CF Server",
            "connection_type": "cloudflared",
            "bind_ip": "127.0.0.1",
            "port": 3240,
            "cloudflared_token": "token123",
            "cloudflared_path": "/opt/cf",
            "secure": True,
            "password": "pass",
        },
    ]
    with patch(
        "usbip_gui.gui.menu.site_config.load_sites", return_value=mock_sites
    ):
        widget = SiteTypeWidget("server")
        assert widget.site_list.count() == 2
        assert widget.host_input.text() == "0.0.0.0"
        assert widget.cf_input.isHidden()

        # Switch to CF Server
        widget.on_site_selected(1)
        assert widget.host_input.text() == "127.0.0.1"
        assert not widget.cf_input.isHidden()
        assert widget.cf_input.text() == "token123"


def test_site_type_widget_field_changes():
    """Test editing fields in the form updates the in-memory site data."""
    mock_sites = [
        {
            "name": "Site 1",
            "connection_type": "direct",
            "host": "127.0.0.1",
            "port": 3240,
            "secure": True,
            "password": "",
            "cloudflared_path": "",
        }
    ]
    with patch(
        "usbip_gui.gui.menu.site_config.load_sites", return_value=mock_sites
    ):
        widget = SiteTypeWidget("client")

        # Change name and port
        widget.name_input.setText("Renamed Site")
        assert widget.sites[0]["name"] == "Renamed Site"
        item = widget.site_list.item(0)
        assert item is not None
        assert item.text() == "Renamed Site"

        # Invalid port text falls back gracefully
        widget.port_input.setText("invalid_port")
        assert widget.sites[0]["port"] == 3240

        widget.port_input.setText("5000")
        assert widget.sites[0]["port"] == 5000

        # Type combo change
        widget.type_combo.setCurrentIndex(1)  # cloudflared
        assert widget.sites[0]["connection_type"] == "cloudflared"
        assert not widget.cf_input.isHidden()

        widget.cf_input.setText("usbip.maschmeyer.ca")
        assert widget.sites[0]["cloudflared_hostname"] == "usbip.maschmeyer.ca"

        widget.cf_token_id_input.setText("my_tok_id")
        widget.cf_token_secret_input.setText("my_tok_sec")
        assert widget.sites[0]["cloudflared_token_id"] == "my_tok_id"
        assert widget.sites[0]["cloudflared_token_secret"] == "my_tok_sec"

        # Change field when current_index is invalid
        widget.current_index = -1
        widget.on_field_changed()


def test_site_type_widget_server_field_changes():
    """Test editing fields on a server site widget."""
    mock_sites = [
        {
            "name": "Server 1",
            "connection_type": "cloudflared",
            "bind_ip": "0.0.0.0",
            "cloudflared_token": "token",
            "port": 3240,
            "secure": True,
            "password": "",
            "cloudflared_path": "",
        }
    ]
    with patch(
        "usbip_gui.gui.menu.site_config.load_sites", return_value=mock_sites
    ):
        widget = SiteTypeWidget("server")
        widget.host_input.setText("192.168.1.1")
        widget.cf_input.setText("new_token")
        assert widget.sites[0]["bind_ip"] == "192.168.1.1"
        assert widget.sites[0]["cloudflared_token"] == "new_token"


def test_site_type_widget_new_site():
    """Test creating new sites and resolving naming collisions."""
    mock_sites = [
        {"name": "New Site", "connection_type": "direct"},
        {"name": "New Site 2", "connection_type": "direct"},
    ]
    with patch(
        "usbip_gui.gui.menu.site_config.load_sites", return_value=mock_sites
    ):
        widget = SiteTypeWidget("client")
        widget.on_new_site()
        assert widget.site_list.count() == 3
        item = widget.site_list.item(2)
        assert item is not None
        assert item.text() == "New Site 3"
        assert widget.sites[2]["name"] == "New Site 3"
        assert widget.sites[2]["host"] == "127.0.0.1"

    # Test server new site defaults
    with patch("usbip_gui.gui.menu.site_config.load_sites", return_value=[]):
        widget_server = SiteTypeWidget("server")
        widget_server.on_new_site()
        assert widget_server.sites[0]["bind_ip"] == "0.0.0.0"
        assert widget_server.sites[0]["cloudflared_token"] == ""


def test_site_type_widget_delete_site():
    """Test deleting sites with confirmation."""
    mock_sites = [
        {"name": "Site A", "connection_type": "direct"},
        {"name": "Site B", "connection_type": "direct"},
    ]
    with patch(
        "usbip_gui.gui.menu.site_config.load_sites", return_value=mock_sites
    ):
        widget = SiteTypeWidget("client")

        # Invalid index deletion does nothing
        widget.current_index = -1
        widget.on_delete_site()
        assert len(widget.sites) == 2

        # User clicks "No"
        widget.current_index = 0
        with patch(
            "usbip_gui.gui.menu.site_config.QMessageBox.question",
            return_value=QMessageBox.StandardButton.No,
        ):
            widget.on_delete_site()
            assert len(widget.sites) == 2

        # User clicks "Yes"
        with patch(
            "usbip_gui.gui.menu.site_config.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            widget.on_delete_site()
            assert len(widget.sites) == 1
            assert widget.sites[0]["name"] == "Site B"

            # Delete the remaining site -> transitions to empty state
            widget.current_index = 0
            widget.on_delete_site()
            assert len(widget.sites) == 0
            assert widget.form_widget.isHidden()
            assert not widget.empty_widget.isHidden()
            assert not widget.del_btn.isEnabled()
            assert "No sites configured" in widget.empty_label.text()


def test_site_type_widget_browse_cloudflared():
    """Test browsing for cloudflared executable."""
    mock_sites = [{"name": "Site A", "connection_type": "cloudflared"}]
    with patch(
        "usbip_gui.gui.menu.site_config.load_sites", return_value=mock_sites
    ):
        widget = SiteTypeWidget("client")

        # Cancel dialog (empty path)
        with patch(
            "usbip_gui.gui.menu.site_config.QFileDialog.getOpenFileName",
            return_value=("", ""),
        ):
            widget.on_browse_cloudflared()
            assert widget.cf_path_input.text() == ""

        # Select valid executable
        with patch(
            "usbip_gui.gui.menu.site_config.QFileDialog.getOpenFileName",
            return_value=("/custom/cloudflared", ""),
        ):
            widget.on_browse_cloudflared()
            assert widget.cf_path_input.text() == "/custom/cloudflared"
            assert widget.sites[0]["cloudflared_path"] == "/custom/cloudflared"


def test_site_config_dialog_validation_and_save():
    """Test validation errors and successful save in SiteConfigDialog."""
    with patch("usbip_gui.gui.menu.site_config.load_sites", return_value=[]):
        dialog = SiteConfigDialog(None)

    # Empty site name
    dialog.client_widget.sites = [{"name": "   ", "port": 3240}]
    with patch(
        "usbip_gui.gui.menu.site_config.QMessageBox.warning"
    ) as mock_warn:
        assert dialog.validate_sites(dialog.client_widget) is False
        mock_warn.assert_called_once()

    # Duplicate site name
    dialog.client_widget.sites = [
        {"name": "Site 1", "port": 3240},
        {"name": "Site 1", "port": 3241},
    ]
    with patch(
        "usbip_gui.gui.menu.site_config.QMessageBox.warning"
    ) as mock_warn:
        assert dialog.validate_sites(dialog.client_widget) is False
        mock_warn.assert_called_once()

    # Invalid port (out of range or non-numeric)
    dialog.client_widget.sites = [{"name": "Site 1", "port": 70000}]
    with patch(
        "usbip_gui.gui.menu.site_config.QMessageBox.warning"
    ) as mock_warn:
        assert dialog.validate_sites(dialog.client_widget) is False
        mock_warn.assert_called_once()

    dialog.client_widget.sites = [{"name": "Site 1", "port": "abc"}]
    with patch(
        "usbip_gui.gui.menu.site_config.QMessageBox.warning"
    ) as mock_warn:
        assert dialog.validate_sites(dialog.client_widget) is False
        mock_warn.assert_called_once()

    # Valid sites
    dialog.client_widget.sites = [{"name": "Client Site", "port": 3240}]
    dialog.server_widget.sites = [{"name": "Server Site", "port": 3240}]
    assert dialog.validate_sites(dialog.client_widget) is True
    assert dialog.validate_sites(dialog.server_widget) is True

    # Test on_save failure on client tab
    dialog.client_widget.sites = [{"name": "", "port": 3240}]
    with patch("usbip_gui.gui.menu.site_config.QMessageBox.warning"):
        dialog.on_save()
        assert dialog.tabs.currentWidget() == dialog.client_widget

    # Test on_save failure on server tab
    dialog.client_widget.sites = [{"name": "Client Site", "port": 3240}]
    dialog.server_widget.sites = [{"name": "", "port": 3240}]
    with patch("usbip_gui.gui.menu.site_config.QMessageBox.warning"):
        dialog.on_save()
        assert dialog.tabs.currentWidget() == dialog.server_widget

    # Test on_save success (saves sites without closing dialog)
    dialog.server_widget.sites = [{"name": "Server Site", "port": 3240}]
    with patch("usbip_gui.gui.menu.site_config.save_all_sites") as mock_save:
        with patch.object(dialog, "accept") as mock_accept:
            dialog.on_save()
            assert mock_save.call_count == 2
            mock_accept.assert_not_called()
            assert not dialog.save_status_label.isHidden()
            assert dialog.save_status_label.text() == "✓ Saved"
            dialog.hide_save_status()
            assert dialog.save_status_label.isHidden()

    # Test Save Sites and Close buttons and reject
    assert dialog.save_btn.text() == "Save Sites"
    assert dialog.close_btn.text() == "Close"
    dialog.show_save_status()
    with patch.object(dialog, "accept") as mock_accept:
        dialog.close_btn.click()
        mock_accept.assert_called_once()
    assert dialog.save_status_timer is not None
    dialog.reject()
    assert dialog.save_status_timer.isActive() is False


@patch("usbip_gui.gui.menu.site_config.SiteConfigDialog")
def test_show_site_config_dialog(mock_dialog_cls: MagicMock):
    """Test show_site_config_dialog instantiates and executes dialog."""
    parent = MagicMock()
    with patch(
        "usbip_gui.gui.menu.site_config.is_master_password_configured",
        return_value=False,
    ):
        show_site_config_dialog(parent)
        mock_dialog_cls.assert_called_once_with(parent)
        mock_dialog_cls.return_value.exec.assert_called_once()


def test_show_site_config_dialog_when_locked():
    """Test show_site_config_dialog prompts unlock when locked."""
    with patch(
        "usbip_gui.gui.menu.site_config.is_master_password_configured",
        return_value=True,
    ):
        with patch(
            "usbip_gui.gui.menu.site_config.is_master_password_unlocked",
            return_value=False,
        ):
            # When ensure_unlocked returns False, dialog is not shown
            with patch(
                "usbip_gui.gui.menu.site_config.ensure_unlocked",
                return_value=False,
            ):
                with patch(
                    "usbip_gui.gui.menu.site_config.SiteConfigDialog"
                ) as mock_dlg:
                    show_site_config_dialog(None)
                    mock_dlg.assert_not_called()

            # When ensure_unlocked returns True, dialog is shown
            with patch(
                "usbip_gui.gui.menu.site_config.ensure_unlocked",
                return_value=True,
            ):
                with patch(
                    "usbip_gui.gui.menu.site_config.SiteConfigDialog"
                ) as mock_dlg:
                    show_site_config_dialog(None)
                    mock_dlg.assert_called_once()


def test_site_config_dialog_security_button():
    """Test security button opens appropriate master password dialog."""
    dialog = SiteConfigDialog()

    # When not configured: opens SetMasterPasswordDialog
    with patch(
        "usbip_gui.gui.menu.site_config.is_master_password_configured",
        return_value=False,
    ):
        with patch(
            "usbip_gui.gui.menu.site_config.SetMasterPasswordDialog"
        ) as mock_set:
            dialog.security_btn.click()
            mock_set.assert_called_once_with(dialog)

    # When configured: opens MasterPasswordManagementDialog
    with patch(
        "usbip_gui.gui.menu.site_config.is_master_password_configured",
        return_value=True,
    ):
        with patch(
            "usbip_gui.gui.menu.site_config.MasterPasswordManagementDialog"
        ) as mock_mgmt:
            dialog.security_btn.click()
            mock_mgmt.assert_called_once_with(dialog)


def test_site_type_widget_reload_sites():
    """Test reload_sites updates sites list and form."""
    widget = SiteTypeWidget("client")
    with patch(
        "usbip_gui.gui.menu.site_config.load_sites",
        return_value=[{"name": "ReloadedSite", "port": 3240}],
    ):
        widget.reload_sites()
        assert widget.site_list.count() == 1
        assert widget.name_input.text() == "ReloadedSite"


def test_site_config_dialog_exec_guard():
    """Test SiteConfigDialog.exec guards against locked master password."""
    with patch("usbip_gui.gui.menu.site_config.load_sites", return_value=[]):
        dialog = SiteConfigDialog(None)

    # 1. Master password configured and ensure_unlocked returns False
    with patch(
        "usbip_gui.gui.menu.site_config.is_master_password_configured",
        return_value=True,
    ):
        with patch(
            "usbip_gui.gui.menu.site_config.is_master_password_unlocked",
            return_value=False,
        ):
            with patch(
                "usbip_gui.gui.menu.site_config.ensure_unlocked",
                return_value=False,
            ):
                with patch(
                    "usbip_gui.gui.menu.site_config.lock_master_password"
                ) as mock_lock:
                    res = dialog.exec()
                    assert res == int(QDialog.DialogCode.Rejected)
                    mock_lock.assert_not_called()

    # 2. Master password configured and ensure_unlocked returns True
    with patch(
        "usbip_gui.gui.menu.site_config.is_master_password_configured",
        return_value=True,
    ):
        with patch(
            "usbip_gui.gui.menu.site_config.is_master_password_unlocked",
            return_value=False,
        ):
            with patch(
                "usbip_gui.gui.menu.site_config.ensure_unlocked",
                return_value=True,
            ):
                with patch.object(
                    QDialog,
                    "exec",
                    return_value=int(QDialog.DialogCode.Accepted),
                ):
                    with patch.object(
                        dialog.client_widget, "reload_sites"
                    ) as mock_reload_c:
                        with patch.object(
                            dialog.server_widget, "reload_sites"
                        ) as mock_reload_s:
                            with patch(
                                "usbip_gui.gui.menu.site_config"
                                ".lock_master_password"
                            ) as mock_lock:
                                res = dialog.exec()
                                assert res == int(QDialog.DialogCode.Accepted)
                                mock_reload_c.assert_called_once()
                                mock_reload_s.assert_called_once()
                                mock_lock.assert_called_once()


def test_site_type_widget_status_icons_and_modification() -> None:
    """Test site list status icons for saved vs modified vs new sites."""
    initial_site = {
        "name": "Initial Site",
        "connection_type": "direct",
        "port": 3240,
        "secure": True,
        "password": "secret",
        "cloudflared_path": "",
        "host": "192.168.1.10",
        "cloudflared_hostname": "",
        "cloudflared_token_id": "",
        "cloudflared_token_secret": "",
    }
    with patch(
        "usbip_gui.gui.menu.site_config.load_sites",
        return_value=[initial_site],
    ):
        widget = SiteTypeWidget("client", None)

    # Clean site initially has saved icon and tooltip
    assert widget.site_list.count() == 1
    item = widget.site_list.item(0)
    assert item is not None
    assert item.toolTip() == "Saved"
    assert widget.is_site_modified(widget.sites[0]) is False

    # Modifying field updates status to unsaved
    widget.name_input.setText("Modified Name")
    assert widget.is_site_modified(widget.sites[0]) is True
    assert item.toolTip() == "Unsaved changes"

    # Restoring name restores saved status
    widget.name_input.setText("Initial Site")
    assert widget.is_site_modified(widget.sites[0]) is False
    assert item.toolTip() == "Saved"

    # Adding a new site gives it unsaved icon
    widget.on_new_site()
    assert widget.site_list.count() == 2
    new_item = widget.site_list.item(1)
    assert new_item is not None
    assert new_item.toolTip() == "Unsaved changes"
    assert widget.is_site_modified(widget.sites[1]) is True

    # Calling mark_saved updates all items to saved status
    widget.mark_saved()
    assert item.toolTip() == "Saved"
    assert new_item.toolTip() == "Saved"
    assert widget.is_site_modified(widget.sites[0]) is False
    assert widget.is_site_modified(widget.sites[1]) is False


def test_site_normalization_and_icons() -> None:
    """Test normalize_site and icon generators."""
    # Test icon generators
    saved_icon = get_saved_icon()
    unsaved_icon = get_unsaved_icon()
    assert not saved_icon.isNull()
    assert not unsaved_icon.isNull()
    assert not create_status_icon(True).isNull()
    assert not create_status_icon(False).isNull()

    # Test normalize_site client with string/invalid port
    norm_client = normalize_site(
        {"name": "Client", "port": "invalid_port"},
        "client",
    )
    assert norm_client["port"] == "invalid_port"
    assert "host" in norm_client

    # Test normalize_site server
    norm_server = normalize_site(
        {"name": "Server", "port": 3240},
        "server",
    )
    assert norm_server["port"] == 3240
    assert "bind_ip" in norm_server
