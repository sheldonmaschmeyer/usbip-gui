"""Tests for the server tab."""

from unittest.mock import patch, MagicMock
from usbip_gui.gui.server import (
    ServerTab,
    parse_local_list,
    init_usbip_server,
    list_local_usb,
    bind_local_usb,
    unbind_local_usb,
)


@patch("usbip_gui.gui.server.BooleanVar")
@patch("usbip_gui.gui.server.Frame")
@patch("usbip_gui.gui.server.Treeview")
@patch("usbip_gui.gui.server.Button")
@patch("usbip_gui.gui.server.list_local_usb", return_value=[])
# pylint: disable=too-many-arguments,too-many-positional-arguments
def test_server_tab_init(
    _mock_local: MagicMock,
    _mock_button: MagicMock,
    _mock_tree: MagicMock,
    mock_frame: MagicMock,
    _mock_bool: MagicMock,
):
    """Test ServerTab initialization."""
    mock_parent = MagicMock()
    tab = ServerTab(mock_parent)

    mock_frame.assert_called()
    assert tab.frame is not None
    assert tab.local_listbox is not None


def test_parse_local_list():
    """Test parsing of local USB devices."""
    text = "- busid 1-1 (046d:c52b)\nManufacturer:Desc"
    rows = parse_local_list(text)
    assert len(rows) == 1
    assert rows[0][0] == "1-1"
    assert rows[0][2] == "Manufacturer"
    assert rows[0][3] == "Desc"


@patch("usbip_gui.gui.server.subprocess.run")
@patch("usbip_gui.gui.server.tunnel_state")
def test_init_usbip_server(mock_tunnel_state: MagicMock, mock_run: MagicMock):
    """Test init_usbip_server function."""
    mock_tunnel_state.server_process = MagicMock()
    init_usbip_server(port=3240, secure=False)
    assert mock_run.call_count == 2
    mock_run.assert_any_call(["sudo", "pkill", "usbipd"], check=False)
    mock_run.assert_called_with(
        ["sudo", "usbipd", "-D", "--tcp-port", "3240"], check=False
    )


@patch("usbip_gui.gui.server.subprocess.run")
@patch("usbip_gui.gui.server.threading.Thread")
@patch("usbip_gui.gui.server.tunnel_state")
def test_init_usbip_server_secure(
    mock_tunnel_state: MagicMock, mock_thread: MagicMock, mock_run: MagicMock
):
    """Test init_usbip_server secure function."""
    mock_tunnel_state.server_process = None
    init_usbip_server(port=3240, secure=True, password="test")
    assert mock_run.call_count == 2
    mock_thread.assert_called_once()
    mock_thread.return_value.start.assert_called_once()


@patch("usbip_gui.gui.server.subprocess.run")
def test_list_local_usb(mock_run: MagicMock):
    """Test listing local usb."""
    mock_run.return_value.stdout = "- busid 1-1 (0000:0000)\nMan:Desc\n\n"
    res = list_local_usb()
    assert len(res) == 1
    mock_run.assert_called_once()


@patch("usbip_gui.gui.server.subprocess.run")
def test_bind_unbind_local_usb(mock_run: MagicMock):
    """Test binding and unbinding."""
    bind_local_usb("1-1")
    mock_run.assert_called_with(
        ["sudo", "usbip", "bind", "--busid=1-1"],
        capture_output=True,
        text=True,
        check=False,
    )
    unbind_local_usb("1-1")
    mock_run.assert_called_with(
        ["sudo", "usbip", "unbind", "--busid=1-1"],
        capture_output=True,
        text=True,
        check=False,
    )


@patch("usbip_gui.gui.server.messagebox.showwarning")
def test_check_secure_warning(mock_warning: MagicMock):
    """Test secure warning popup."""
    var = MagicMock()
    var.get.return_value = False
    tab = MagicMock()
    ServerTab.check_secure_warning(tab, var)
    mock_warning.assert_called_once()


@patch("usbip_gui.gui.server.messagebox.showinfo")
@patch("usbip_gui.gui.server.ssl_tunnel.get_cert_fingerprint")
@patch("usbip_gui.gui.server.ssl_tunnel.get_cert_paths")
def test_show_fingerprint(
    mock_paths: MagicMock, mock_fp: MagicMock, mock_info: MagicMock
):
    """Test show fingerprint."""
    mock_paths.return_value = ("cert", "key")
    mock_fp.return_value = "ABC"
    tab = MagicMock()
    ServerTab.show_fingerprint(tab)
    mock_info.assert_called_once()


@patch("usbip_gui.gui.server.init_usbip_server")
def test_restart_server(mock_init: MagicMock):
    """Test restart server."""
    tab = MagicMock()
    tab.local_port_input.get.return_value = "3240"
    tab.local_secure_var.get.return_value = True
    tab.local_password_input.get.return_value = "pass"
    tab.local_bind_ip_input.get.return_value = "1.2.3.4"
    ServerTab.restart_server(tab)
    mock_init.assert_called_once_with(3240, True, "pass", "1.2.3.4")


@patch("usbip_gui.gui.server.messagebox.showinfo")
@patch("usbip_gui.gui.server.ssl_tunnel.generate_self_signed_cert")
@patch("usbip_gui.gui.server.os.remove")
@patch("usbip_gui.gui.server.os.path.exists", return_value=True)
@patch("usbip_gui.gui.server.ssl_tunnel.get_cert_paths")
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


@patch("usbip_gui.gui.server.list_local_usb")
def test_refresh_local(mock_list: MagicMock):
    """Test refresh local devices list."""
    mock_list.return_value = [("1-1", "Bound", "Man", "Desc")]
    tab = MagicMock()
    ServerTab.refresh_local(tab)
    tab.local_listbox.delete.assert_called_once()
    tab.local_listbox.insert.assert_called_once()


@patch("usbip_gui.gui.server.time.sleep")
@patch("usbip_gui.gui.server.bind_local_usb")
def test_bind_local_ui(mock_bind: MagicMock, _mock_sleep: MagicMock):
    """Test bind button handler."""
    tab = MagicMock()
    tab.local_listbox.selection.return_value = ["item1"]
    tab.local_listbox.item.return_value = {"values": ["1-1"]}
    ServerTab.bind_local(tab)
    mock_bind.assert_called_once_with("1-1")
    tab.refresh_local.assert_called_once()


@patch("usbip_gui.gui.server.time.sleep")
@patch("usbip_gui.gui.server.unbind_local_usb")
def test_unbind_local_ui(mock_unbind: MagicMock, _mock_sleep: MagicMock):
    """Test unbind button handler."""
    tab = MagicMock()
    tab.local_listbox.selection.return_value = ["item1"]
    tab.local_listbox.item.return_value = {"values": ["1-1"]}
    ServerTab.unbind_local(tab)
    mock_unbind.assert_called_once_with("1-1")
    tab.refresh_local.assert_called_once()


def test_on_double_click():
    """Test double click toggle on treeview."""
    server_tab = MagicMock()
    server_tab.local_listbox.selection.return_value = ["item1"]
    # Test bound -> unbind
    server_tab.local_listbox.item.return_value = {"values": ["1-1", "Bound"]}
    ServerTab.on_double_click(server_tab, MagicMock())
    server_tab.unbind_local.assert_called_once()

    # Test unbound -> bind
    server_tab.unbind_local.reset_mock()
    server_tab.local_listbox.item.return_value = {"values": ["1-1", "Unbound"]}
    ServerTab.on_double_click(server_tab, MagicMock())
    server_tab.bind_local.assert_called_once()


@patch("usbip_gui.gui.server.subprocess.run")
@patch("usbip_gui.gui.server.tunnel_state")
def test_init_usbip_server_terminate_oserror(
    mock_state: MagicMock, _mock_run: MagicMock
):
    """Test init server handles oserror on terminate."""

    mock_proc = MagicMock()
    mock_proc.terminate.side_effect = OSError()
    mock_state.server_process = mock_proc
    init_usbip_server()


@patch("usbip_gui.gui.server.subprocess.run")
@patch("usbip_gui.gui.server.subprocess.Popen")
@patch("usbip_gui.gui.server.threading.Thread")
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


@patch("usbip_gui.gui.server.os.path.exists", return_value=True)
@patch("usbip_gui.gui.server.os.path.islink", return_value=True)
@patch("usbip_gui.gui.server.os.readlink", return_value="usbip-host")
def test_parse_local_list_bound(
    _mock_readlink: MagicMock,
    _mock_islink: MagicMock,
    _mock_exists: MagicMock,
):
    """Test parse local list correctly parses bound state."""

    res = parse_local_list("  busid 1-1 (046d:c52b)\nman:desc")
    assert len(res) == 1
    assert res[0][1] == "Bound"


@patch("usbip_gui.gui.server.BooleanVar")
@patch("usbip_gui.gui.server.list_local_usb")
def test_server_ui_errors(mock_local: MagicMock, _mock_bool: MagicMock):
    """Test server ui errors."""

    mock_local.return_value = [("a", "b", "c", "d")]
    parent = MagicMock()
    server_tab = ServerTab(parent)

    with patch.object(server_tab.local_listbox, "selection", return_value=()):
        with (
            patch("usbip_gui.gui.server.messagebox.showerror") as mock_err,
            patch.object(
                server_tab.local_port_input, "get", return_value="abc"
            ),
        ):
            server_tab.restart_server()
            mock_err.assert_called_once()

        with (
            patch("usbip_gui.gui.server.messagebox.showerror") as mock_err,
            patch.object(
                server_tab.local_port_input, "get", return_value="1234"
            ),
            patch.object(
                server_tab.local_secure_var, "get", return_value=True
            ),
            patch.object(
                server_tab.local_password_input, "get", return_value=""
            ),
        ):
            server_tab.restart_server()
            mock_err.assert_called_once()

        with patch("usbip_gui.gui.server.messagebox.showerror") as mock_err:
            server_tab.bind_local()
            mock_err.assert_called_once()

        with patch("usbip_gui.gui.server.messagebox.showerror") as mock_err:
            server_tab.unbind_local()
            mock_err.assert_called_once()

        with patch("usbip_gui.gui.server.messagebox.showerror") as mock_err:
            server_tab.on_double_click(MagicMock())
            mock_err.assert_not_called()


@patch("usbip_gui.gui.server.BooleanVar")
@patch("usbip_gui.gui.server.ssl_tunnel.get_cert_paths", side_effect=OSError)
def test_show_fingerprint_oserror(_mock_get: MagicMock, _mock_bool: MagicMock):
    """Test show fingerprint handles oserror."""

    parent = MagicMock()
    server_tab = ServerTab(parent)
    with patch("usbip_gui.gui.server.messagebox.showerror") as mock_err:
        server_tab.show_fingerprint()
        mock_err.assert_called_once()


@patch("usbip_gui.gui.server.BooleanVar")
@patch("usbip_gui.gui.server.ssl_tunnel.get_cert_paths", side_effect=OSError)
def test_regenerate_cert_oserror(_mock_get: MagicMock, _mock_bool: MagicMock):
    """Test regenerate cert handles oserror."""

    parent = MagicMock()
    server_tab = ServerTab(parent)
    with patch("usbip_gui.gui.server.messagebox.showerror") as mock_err:
        server_tab.regenerate_cert()
        mock_err.assert_called_once()
