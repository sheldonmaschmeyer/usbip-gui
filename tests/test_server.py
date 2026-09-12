"""Tests for the server tab."""

import sys
from typing import Callable
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QLineEdit

from usbip_gui.common import tunnel_state
from usbip_gui.gui.server import (
    ServerTab,
    parse_local_list,
    init_usbip_server,
    list_local_usb,
    bind_local_usb,
    unbind_local_usb,
    parse_windows_local_list,
)


@patch("usbip_gui.gui.server.tab.list_local_usb", return_value=[])
def test_server_tab_init(_mock_local: MagicMock):
    """Test ServerTab initialization."""
    tab = ServerTab(None)
    assert tab.local_listbox is not None


def test_server_tab_toggle_show_password():
    """Test toggle_show_password toggles EchoMode."""
    with patch("usbip_gui.gui.server.tab.list_local_usb", return_value=[]):
        tab = ServerTab(None)
    assert tab.local_password_input.echoMode() == QLineEdit.EchoMode.Password

    tab.local_show_password_checkbox.setChecked(True)
    assert tab.local_password_input.echoMode() == QLineEdit.EchoMode.Normal

    tab.local_show_password_checkbox.setChecked(False)
    assert tab.local_password_input.echoMode() == QLineEdit.EchoMode.Password


def test_parse_local_list():
    """Test parsing of local USB devices."""
    text = "- busid 1-1 (046d:c52b)\nManufacturer:Desc"
    with patch("os.path.exists", return_value=False):
        rows = parse_local_list(text)
        assert len(rows) == 1
        assert rows[0][0] == "1-1"
        assert rows[0][1] == "Unbound"
        assert rows[0][2] == "Manufacturer"
        assert rows[0][3] == "Desc"
        assert rows[0][4] == "046d:c52b"

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.islink", return_value=True),
        patch("os.readlink", return_value="/drivers/usbip-host"),
    ):
        rows_bound = parse_local_list(text)
        assert rows_bound[0][1] == "Bound"

    # Test unknown product stripping
    unknown_text = (
        " - busid 1-2 (8765:4321)\n"
        "   Unknown : unknown product (8765:4321)\n"
    )
    rows2 = parse_local_list(unknown_text)
    assert len(rows2) == 1
    assert rows2[0][3] == "unknown product"


@patch("usbip_gui.gui.server.runtime.subprocess.run")
@patch("usbip_gui.gui.server.runtime.tunnel_state")
@patch("usbip_gui.gui.server.runtime.sys")
def test_init_usbip_server(
    mock_sys: MagicMock,
    mock_tunnel_state: MagicMock,
    mock_run: MagicMock,
):
    """Test init_usbip_server function."""
    mock_sys.platform = "linux"
    mock_tunnel_state.server_process = MagicMock()
    init_usbip_server(port=3240, secure=False)
    assert mock_run.call_count == 3
    mock_run.assert_any_call(["pkexec", "pkill", "usbipd"], check=False)
    mock_run.assert_called_with(
        ["pkexec", "usbipd", "-D", "--tcp-port", "3240"], check=False
    )


@patch("usbip_gui.gui.server.runtime.subprocess.run")
@patch("usbip_gui.gui.server.runtime.threading.Thread")
@patch("usbip_gui.gui.server.runtime.tunnel_state")
@patch("usbip_gui.gui.server.runtime.sys")
def test_init_usbip_server_secure(
    mock_sys: MagicMock,
    mock_tunnel_state: MagicMock,
    mock_thread: MagicMock,
    mock_run: MagicMock,
):
    """Test init_usbip_server secure function."""
    mock_sys.platform = "linux"
    mock_tunnel_state.server_process = None
    init_usbip_server(port=3240, secure=True, password="test")
    assert mock_run.call_count == 3
    mock_thread.assert_called_once()
    mock_thread.return_value.start.assert_called_once()


@patch("usbip_gui.gui.server.parsing.run_elevated")
@patch("usbip_gui.gui.server.parsing.sys")
def test_list_local_usb(mock_sys: MagicMock, mock_run_elevated: MagicMock):
    """Test listing local usb."""
    mock_sys.platform = "linux"
    mock_run_elevated.return_value.stdout = (
        "- busid 1-1 (0000:0000)\nMan:Desc\n\n"
    )
    res = list_local_usb()
    assert len(res) == 1
    mock_run_elevated.assert_called_once_with(["usbip", "list", "--local"])


@patch("usbip_gui.gui.server.parsing.run_elevated")
@patch("usbip_gui.gui.server.parsing.sys")
def test_bind_unbind_local_usb(
    mock_sys: MagicMock, mock_run_elevated: MagicMock
):
    """Test binding and unbinding."""
    mock_sys.platform = "linux"
    bind_local_usb("1-1")
    mock_run_elevated.assert_called_with(["usbip", "bind", "--busid=1-1"])
    unbind_local_usb("1-1")
    mock_run_elevated.assert_called_with(["usbip", "unbind", "--busid=1-1"])


@patch("usbip_gui.gui.server.tab.QMessageBox.warning")
def test_check_secure_warning(mock_warning: MagicMock):
    """Test secure warning popup."""
    tab = MagicMock()
    ServerTab.check_secure_warning(tab, 0)
    mock_warning.assert_called_once()


@patch("usbip_gui.gui.server.tab.QMessageBox.information")
@patch("usbip_gui.gui.server.tab.ssl_tunnel.get_cert_fingerprint")
@patch("usbip_gui.gui.server.tab.ssl_tunnel.get_cert_paths")
def test_show_fingerprint(
    mock_paths: MagicMock, mock_fp: MagicMock, mock_info: MagicMock
):
    """Test show fingerprint."""
    mock_paths.return_value = ("cert", "key")
    mock_fp.return_value = "ABC"
    tab = MagicMock()
    ServerTab.show_fingerprint(tab)
    mock_info.assert_called_once()


@patch("usbip_gui.gui.server.tab.init_usbip_server")
def test_restart_server(mock_init: MagicMock):
    """Test restart server."""
    tab = MagicMock()
    tab.local_port_input.text.return_value = "3240"
    tab.local_secure_checkbox.isChecked.return_value = True
    tab.local_password_input.text.return_value = "pass"
    tab.local_bind_ip_input.text.return_value = "1.2.3.4"
    ServerTab.restart_server(tab)
    mock_init.assert_called_once_with(3240, True, "pass", "1.2.3.4")


@patch("usbip_gui.gui.server.tab.QMessageBox.information")
@patch("usbip_gui.gui.server.tab.ssl_tunnel.generate_self_signed_cert")
@patch("usbip_gui.gui.server.tab.os.remove")
@patch("usbip_gui.gui.server.tab.os.path.exists", return_value=True)
@patch("usbip_gui.gui.server.tab.ssl_tunnel.get_cert_paths")
def test_regenerate_cert(
    mock_paths: MagicMock,
    _mock_exists: MagicMock,
    mock_remove: MagicMock,
    mock_gen: MagicMock,
    mock_info: MagicMock,
):
    """Test regenerating certificate from UI."""
    mock_paths.return_value = ("cert", "key")
    tab = MagicMock()
    ServerTab.regenerate_cert(tab)
    mock_remove.assert_any_call("cert")
    mock_remove.assert_any_call("key")
    mock_gen.assert_called_once_with("cert", "key")
    mock_info.assert_called_once()


@patch("usbip_gui.gui.server.tab.SortableTreeWidgetItem")
@patch("usbip_gui.gui.server.tab.list_local_usb")
def test_refresh_local(mock_list: MagicMock, mock_item: MagicMock):
    """Test refresh local devices list."""
    mock_list.return_value = [("1-1", "Bound", "Man", "Desc", "1234:5678")]
    tab = MagicMock()
    ServerTab.refresh_local(tab)
    tab.local_listbox.clear.assert_called_once()
    expected = ["1-1", "Bound", "Man"]
    if sys.platform == "win32":
        expected.append("")
    expected.extend(["Desc", "1234:5678"])
    mock_item.assert_called_once_with(tab.local_listbox, expected)
    assert tab.local_listbox.addTopLevelItem.called

    with patch("usbip_gui.gui.server.tab.sys.platform", "win32"):
        with patch(
            "usbip_gui.gui.server.tab.enrich_device_item"
        ) as mock_enrich:
            ServerTab.refresh_local(tab)
            mock_enrich.assert_called_once()


@patch("usbip_gui.gui.server.tab.QMessageBox.critical")
@patch("usbip_gui.gui.server.tab.list_local_usb")
def test_refresh_local_usbip_not_found(
    mock_list: MagicMock, mock_critical: MagicMock
):
    """Test refresh local shows a clear error if usbipd isn't installed."""
    mock_list.side_effect = FileNotFoundError(
        "[WinError 2] The system cannot find the file specified"
    )
    tab = MagicMock()
    ServerTab.refresh_local(tab)
    mock_critical.assert_called_once()
    tab.local_listbox.clear.assert_not_called()


@patch("usbip_gui.gui.server.tab.time.sleep")
@patch("usbip_gui.gui.server.tab.bind_local_usb")
def test_bind_local_ui(mock_bind: MagicMock, _mock_sleep: MagicMock):
    """Test bind button handler."""
    tab = MagicMock()
    item = MagicMock()
    item.text.return_value = "1-1"
    tab.local_listbox.selectedItems.return_value = [item]
    ServerTab.bind_local(tab)
    mock_bind.assert_called_once_with("1-1")
    tab.refresh_local.assert_called_once()


@patch("usbip_gui.gui.server.tab.time.sleep")
@patch("usbip_gui.gui.server.tab.unbind_local_usb")
def test_unbind_local_ui(mock_unbind: MagicMock, _mock_sleep: MagicMock):
    """Test unbind button handler."""
    tab = MagicMock()
    item = MagicMock()
    item.text.return_value = "1-1"
    tab.local_listbox.selectedItems.return_value = [item]
    ServerTab.unbind_local(tab)
    mock_unbind.assert_called_once_with("1-1")
    tab.refresh_local.assert_called_once()


def test_on_double_click():
    """Test double click toggle on treeview."""
    server_tab = MagicMock()
    item = MagicMock()
    item.text.return_value = "Bound"
    server_tab.local_listbox.selectedItems.return_value = [item]
    ServerTab.on_double_click(server_tab, item, 0)
    server_tab.unbind_local.assert_called_once()

    # Test unbound -> bind
    server_tab.unbind_local.reset_mock()
    item = MagicMock()
    item.text.return_value = "Unbound"
    server_tab.local_listbox.selectedItems.return_value = [item]
    ServerTab.on_double_click(server_tab, item, 0)
    server_tab.bind_local.assert_called_once()


@patch("usbip_gui.gui.server.runtime.subprocess.run")
@patch("usbip_gui.gui.server.runtime.tunnel_state")
def test_init_usbip_server_terminate_oserror(
    mock_state: MagicMock, _mock_run: MagicMock
):
    """Test init server handles oserror on terminate."""

    mock_proc = MagicMock()
    mock_proc.terminate.side_effect = OSError()
    mock_state.server_process = mock_proc
    init_usbip_server()


@patch("usbip_gui.gui.server.runtime.subprocess.run")
@patch("usbip_gui.gui.server.runtime.subprocess.Popen")
@patch("usbip_gui.gui.server.runtime.threading.Thread")
def test_init_usbip_server_run_tunnel(
    mock_thread: MagicMock, mock_popen: MagicMock, _mock_run: MagicMock
):
    """Test init server runs secure tunnel."""

    init_usbip_server(secure=True)
    target = mock_thread.call_args[1]["target"]
    target()
    mock_popen.assert_called_once()


def test_parse_local_list_empty():
    """Test parse local list handles empty input."""
    assert not parse_local_list("")
    assert not parse_local_list(" \n ")
    assert not parse_local_list("1-1\n")


@patch("usbip_gui.gui.server.parsing.os.path.exists", return_value=True)
@patch("usbip_gui.gui.server.parsing.os.path.islink", return_value=True)
@patch("usbip_gui.gui.server.parsing.os.readlink", return_value="usbip-host")
def test_parse_local_list_bound(
    _mock_readlink: MagicMock,
    _mock_islink: MagicMock,
    _mock_exists: MagicMock,
):
    """Test parse local list correctly parses bound state."""

    res = parse_local_list("  busid 1-1 (046d:c52b)\nman:desc")
    assert len(res) == 1
    assert res[0][1] == "Bound"


@patch("usbip_gui.gui.server.tab.list_local_usb")
def test_server_ui_errors(mock_local: MagicMock):
    """Test server ui errors."""

    mock_local.return_value = [("a", "b", "c", "d", "e")]
    server_tab = ServerTab(None)

    with patch.object(
        server_tab.local_listbox, "selectedItems", return_value=()
    ):
        with (
            patch("usbip_gui.gui.server.tab.QMessageBox.critical") as mock_err,
            patch.object(
                server_tab.local_port_input, "text", return_value="abc"
            ),
        ):
            server_tab.restart_server()
            mock_err.assert_called_once()

        with (
            patch("usbip_gui.gui.server.tab.QMessageBox.critical") as mock_err,
            patch.object(
                server_tab.local_port_input, "text", return_value="1234"
            ),
            patch.object(
                server_tab.local_secure_checkbox,
                "isChecked",
                return_value=True,
            ),
            patch.object(
                server_tab.local_password_input, "text", return_value=""
            ),
        ):
            server_tab.restart_server()
            mock_err.assert_called_once()

        with patch(
            "usbip_gui.gui.server.tab.QMessageBox.critical"
        ) as mock_err:
            server_tab.bind_local()
            mock_err.assert_called_once()

        with patch(
            "usbip_gui.gui.server.tab.QMessageBox.critical"
        ) as mock_err:
            server_tab.unbind_local()
            mock_err.assert_called_once()

        with patch(
            "usbip_gui.gui.server.tab.QMessageBox.critical"
        ) as mock_err:
            server_tab.on_double_click(None, 0)  # type: ignore
            mock_err.assert_not_called()


@patch("usbip_gui.gui.server.tab.list_local_usb", return_value=[])
@patch(
    "usbip_gui.gui.server.tab.ssl_tunnel.get_cert_paths", side_effect=OSError
)
def test_show_fingerprint_oserror(
    _mock_get: MagicMock, _mock_local: MagicMock
):
    """Test show fingerprint handles oserror."""

    server_tab = ServerTab(None)
    with patch("usbip_gui.gui.server.tab.QMessageBox.critical") as mock_err:
        server_tab.show_fingerprint()
        mock_err.assert_called_once()


@patch("usbip_gui.gui.server.tab.list_local_usb", return_value=[])
@patch(
    "usbip_gui.gui.server.tab.ssl_tunnel.get_cert_paths", side_effect=OSError
)
def test_regenerate_cert_oserror(_mock_get: MagicMock, _mock_local: MagicMock):
    """Test regenerate cert handles oserror."""

    server_tab = ServerTab(None)
    with patch("usbip_gui.gui.server.tab.QMessageBox.critical") as mock_err:
        server_tab.regenerate_cert()
        mock_err.assert_called_once()


def test_parse_windows_local_list():
    """Test parse windows local list."""
    assert not parse_windows_local_list("")
    assert not parse_windows_local_list(" \n ")

    text = (
        "1-1      046d:c52b  Manufacturer Desc  Not shared\n"
        "1-2      1234:5678  Another Device     Shared\n"
        "1-3      8765:4321  Attached Device    Attached to something"
    )

    rows = parse_windows_local_list(text)
    assert len(rows) == 3
    assert rows[0][0] == "1-1"
    assert rows[0][1] == "Unbound"
    assert rows[0][2] == ""
    assert rows[0][3] == "Manufacturer Desc"
    assert rows[0][4] == "046d:c52b"
    assert rows[1][1] == "Bound"
    assert rows[2][1] == "Bound"


@patch("usbip_gui.gui.server.runtime.sys")
@patch("usbip_gui.gui.server.runtime.subprocess.run")
@patch("usbip_gui.gui.server.runtime.tunnel_state")
def test_init_usbip_server_win32(
    mock_tunnel: MagicMock, mock_run: MagicMock, mock_sys: MagicMock
):
    """Test init_usbip_server on win32."""
    mock_sys.platform = "win32"
    mock_sys.executable = "python.exe"
    mock_tunnel.server_process = None

    # Insecure
    init_usbip_server(port=3240, secure=False)
    # Shouldn't call run because win32 insecure doesn't start usbipd -D
    mock_run.assert_not_called()

    # Secure
    with patch("usbip_gui.gui.server.runtime.threading.Thread") as mock_thread:
        init_usbip_server(port=3240, secure=True)
        mock_thread.assert_called_once()
        target = mock_thread.call_args[1]["target"]
        with patch(
            "usbip_gui.gui.server.runtime.subprocess.Popen"
        ) as mock_popen:
            target()
            mock_popen.assert_called_once()


@patch("usbip_gui.gui.server.parsing.sys")
@patch("usbip_gui.gui.server.parsing.subprocess.run")
def test_list_local_usb_win32(mock_run: MagicMock, mock_sys: MagicMock):
    """Test list_local_usb on win32."""
    mock_sys.platform = "win32"
    mock_run.return_value.stdout = "1-1      0000:0000  dev      Not shared"
    res = list_local_usb()
    mock_run.assert_called_once_with(
        ["usbipd", "list"], capture_output=True, text=True, check=False
    )
    assert len(res) == 1


@patch("usbip_gui.gui.server.parsing.sys")
@patch("usbip_gui.gui.server.parsing.run_elevated")
def test_bind_unbind_local_usb_win32(
    mock_run_elevated: MagicMock, mock_sys: MagicMock
):
    """Test bind/unbind local usb on win32 triggers UAC via run_elevated."""
    mock_sys.platform = "win32"

    bind_local_usb("1-1")
    mock_run_elevated.assert_called_with(["usbipd", "bind", "--busid", "1-1"])

    unbind_local_usb("1-1")
    mock_run_elevated.assert_called_with(
        ["usbipd", "unbind", "--busid", "1-1"]
    )


@patch("usbip_gui.gui.server.runtime.resolve_cloudflared_executable")
@patch("usbip_gui.gui.server.runtime.subprocess.Popen")
@patch("usbip_gui.gui.server.runtime.threading.Thread")
@patch("usbip_gui.gui.server.runtime.subprocess.run")
def test_init_usbip_server_cloudflared(
    _mock_run: MagicMock,
    mock_thread: MagicMock,
    mock_popen: MagicMock,
    mock_resolve: MagicMock,
):
    """Test init_usbip_server with cloudflared enabled."""
    # Test terminating existing cloudflared process and handling OSError
    old_proc = MagicMock()
    old_proc.terminate.side_effect = OSError("failed")
    tunnel_state.cloudflared_server_process = old_proc

    mock_resolve.return_value = "/usr/bin/cloudflared"

    def execute_thread_target(
        target: Callable[[], object] | None = None,
        **_kwargs: object,
    ) -> MagicMock:
        thread_mock = MagicMock()
        if target:
            target()
        return thread_mock

    mock_thread.side_effect = execute_thread_target
    mock_proc_instance = MagicMock()
    mock_proc_instance.__enter__.return_value = mock_proc_instance
    mock_popen.return_value = mock_proc_instance

    init_usbip_server(
        port=3240,
        secure=False,
        use_cloudflared=True,
        cloudflared_token="token123",
        cloudflared_path="/usr/bin/cloudflared",
    )
    mock_resolve.assert_called_with("/usr/bin/cloudflared")
    mock_popen.assert_called_with(
        [
            "/usr/bin/cloudflared",
            "tunnel",
            "run",
            "--token",
            "token123",
        ]
    )
    assert tunnel_state.cloudflared_server_process is None


@patch("usbip_gui.gui.server.tab.set_selected_site_name")
def test_server_tab_site_selection(mock_set: MagicMock):
    """Test ServerTab site combo population, updates, and selection."""
    with patch("usbip_gui.gui.server.tab.list_local_usb", return_value=[]):
        tab = ServerTab(None)

    # Test populate_site_combo with saved sites
    mock_sites = [
        {
            "name": "Local Server",
            "connection_type": "direct",
            "port": 3240,
            "bind_ip": "127.0.0.1",
            "secure": False,
            "password": "",
        },
        {
            "name": "Cloudflare Server",
            "connection_type": "cloudflared",
            "port": 3240,
            "bind_ip": "0.0.0.0",
            "secure": True,
            "password": "secret",
            "cloudflared_token": "token-abc",
            "cloudflared_path": "/opt/cf",
        },
    ]

    with (
        patch("usbip_gui.gui.server.tab.load_sites", return_value=mock_sites),
        patch(
            "usbip_gui.gui.server.tab.get_selected_site_name",
            return_value="Cloudflare Server",
        ),
    ):
        tab.populate_site_combo()
        assert tab.local_site_combo.count() == 3
        assert tab.local_site_combo.currentText() == "Cloudflare Server"

        tab.populate_site_combo()
        assert tab.local_site_combo.currentText() == "Cloudflare Server"

    # Test on_sites_updated
    with patch.object(tab, "populate_site_combo") as mock_pop:
        tab.on_sites_updated("client")
        mock_pop.assert_not_called()
        tab.on_sites_updated("server")
        mock_pop.assert_called_once()

    # Test on_site_selected with empty site
    tab.local_site_combo.setCurrentIndex(0)
    tab.on_site_selected(0)
    mock_set.assert_called_with("server", "")

    # Test on_site_selected with non-existent site
    tab.local_site_combo.setCurrentIndex(1)
    with patch("usbip_gui.gui.server.tab.get_site", return_value=None):
        tab.on_site_selected(1)

    # Test on_site_selected with valid cloudflared site
    cf_site = mock_sites[1]
    with patch("usbip_gui.gui.server.tab.get_site", return_value=cf_site):
        tab.local_site_combo.setCurrentIndex(2)
        tab.on_site_selected(2)
        assert tab.local_port_input.text() == "3240"
        assert tab.local_bind_ip_input.text() == "0.0.0.0"
        assert tab.local_secure_checkbox.isChecked() is True
        assert tab.local_password_input.text() == "secret"

    # Test get_active_cf_settings (cloudflared site)
    with patch("usbip_gui.gui.server.tab.get_site", return_value=cf_site):
        use_cf, token, path = tab.get_active_cf_settings()
        assert use_cf is True
        assert token == "token-abc"
        assert path == "/opt/cf"

    # Test get_active_cf_settings (direct site)
    direct_site = mock_sites[0]
    with patch("usbip_gui.gui.server.tab.get_site", return_value=direct_site):
        use_cf, token, path = tab.get_active_cf_settings()
        assert use_cf is False
        assert token == ""
        assert path == ""

    # Test encrypted password sets empty string in on_site_selected
    enc_site = {
        "name": "Encrypted Server",
        "connection_type": "cloudflared",
        "cloudflared_token": {"enc": "v1"},
        "port": 3240,
        "password": {"enc": "v1"},
    }
    with patch("usbip_gui.gui.server.tab.get_site", return_value=enc_site):
        tab.on_site_selected(2)
        assert tab.local_password_input.text() == ""
        use_cf, token, path = tab.get_active_cf_settings()
        assert use_cf is True
        assert token == ""

    # Test restart_server aborts if unlock cancelled
    with patch.object(
        tab.local_site_combo, "currentData", return_value="Encrypted Server"
    ):
        with patch("usbip_gui.gui.server.tab.get_site", return_value=enc_site):
            with patch(
                "usbip_gui.gui.server.tab.site_requires_unlock",
                return_value=True,
            ):
                with patch(
                    "usbip_gui.gui.server.tab.ensure_unlocked",
                    return_value=False,
                ):
                    with patch(
                        "usbip_gui.gui.server.tab.init_usbip_server"
                    ) as mock_srv:
                        tab.restart_server()
                        mock_srv.assert_not_called()

                # Test restart_server succeeds if unlocked
                with patch(
                    "usbip_gui.gui.server.tab.ensure_unlocked",
                    return_value=True,
                ):
                    with patch.object(tab, "on_site_selected") as mock_sel:
                        with patch(
                            "usbip_gui.gui.server.tab.init_usbip_server"
                        ) as mock_srv:
                            tab.local_port_input.setText("3240")
                            tab.local_password_input.setText("testpass")
                            tab.local_bind_ip_input.setText("0.0.0.0")
                            with patch.object(
                                tab,
                                "get_active_cf_settings",
                                return_value=(False, "", ""),
                            ):
                                tab.restart_server()
                            mock_sel.assert_called_once()
                            mock_srv.assert_called_once()


@patch("usbip_gui.gui.server.tab.init_usbip_server")
@patch("usbip_gui.gui.server.tab.QMessageBox.critical")
def test_restart_server_cloudflared_validation_and_success(
    mock_critical: MagicMock, mock_init: MagicMock
):
    """Test restart_server validation and invocation with cloudflared."""
    tab = MagicMock()
    tab.local_port_input.text.return_value = "3240"
    tab.local_secure_checkbox.isChecked.return_value = False
    tab.local_password_input.text.return_value = ""
    tab.local_bind_ip_input.text.return_value = "0.0.0.0"

    # Case 1: use_cf=True but missing token
    tab.get_active_cf_settings.return_value = (True, "", "")
    ServerTab.restart_server(tab)
    mock_critical.assert_called_once()
    mock_init.assert_not_called()

    # Case 2: use_cf=True with valid token
    mock_critical.reset_mock()
    tab.get_active_cf_settings.return_value = (
        True,
        "valid-token",
        "/opt/cloudflared",
    )
    ServerTab.restart_server(tab)
    mock_critical.assert_not_called()
    mock_init.assert_called_once_with(
        3240,
        False,
        "",
        "0.0.0.0",
        use_cloudflared=True,
        cloudflared_token="valid-token",
        cloudflared_path="/opt/cloudflared",
    )
