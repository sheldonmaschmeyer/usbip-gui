"""Tests for the client tab."""

# pylint: disable=duplicate-code

from unittest.mock import MagicMock, mock_open, patch
from PyQt6.QtWidgets import QMessageBox

from usbip_gui.gui.client import (
    ClientTab,
    parse_remote_list,
    parse_attached_list,
    get_or_create_client_tunnel,
    list_remote_usb,
    list_attached_usb,
    attach_remote_usb,
    detach_remote_usb,
)


@patch("usbip_gui.gui.client.list_remote_usb", return_value=[])
@patch("usbip_gui.gui.client.list_attached_usb", return_value=[])
def test_client_tab_init(
    _mock_attached: MagicMock,
    _mock_remote: MagicMock,
):
    """Test ClientTab initialization."""
    tab = ClientTab(None)

    assert tab.remote_listbox is not None


def test_parse_remote_list():
    """Test parsing of remote USB devices list."""
    text = (
        "1-1: Apple, Inc. : iPhone (05ac:12a8)\n"
        "2-2.1: Mouse : Generic (0000:0000)"
    )
    rows = parse_remote_list(text)
    assert len(rows) == 2
    assert rows[0] == ("1-1", "Apple, Inc.", "iPhone (05ac:12a8)")

    # Test no exportable
    empty = parse_remote_list("no exportable devices found on host")
    assert not empty


def test_parse_attached_list():
    """Test parsing of already attached USB devices."""
    text = "Port 1:\nManufacturer: Desc : Extra\n1-1 -> usb://192.168.1.100\n"
    rows = parse_attached_list(text)
    assert len(rows) == 1
    assert rows[0] == ("192.168.1.100", 1, "1-1", "Manufacturer", "Desc:Extra")


def test_get_or_create_client_tunnel_insecure():
    """Test get tunnel when secure is False."""
    h, p = get_or_create_client_tunnel("host", 1234, False, "")
    assert h == "host"
    assert p == 1234


@patch("usbip_gui.gui.client.socket.create_connection")
@patch("usbip_gui.gui.client.ssl.create_default_context")
@patch("usbip_gui.gui.client.subprocess.Popen")
@patch("usbip_gui.gui.client.tunnel_state")
@patch("usbip_gui.gui.client.os.path.exists", return_value=False)
@patch(
    "usbip_gui.gui.client.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("usbip_gui.gui.client.os.makedirs")
@patch("builtins.open", new_callable=mock_open, read_data="{}")
def test_get_or_create_client_tunnel_secure_cached(
    _mock_open: MagicMock,
    _mock_makedirs: MagicMock,
    _mock_ask: MagicMock,
    _mock_exists: MagicMock,
    mock_tunnel: MagicMock,
    _mock_popen: MagicMock,
    _mock_ctx: MagicMock,
    _mock_sock: MagicMock,
):
    """Test get tunnel when tunnel is already running."""
    proc = MagicMock()
    proc.poll.return_value = None
    mock_tunnel.client_processes = {("host", 1234): (50000, proc, "pass")}

    mock_ssock = (
        _mock_ctx.return_value.wrap_socket.return_value.__enter__.return_value
    )
    mock_ssock.getpeercert.return_value = b"mock_cert_der"
    mock_ssock.recv.return_value = b"\x01"

    h, p = get_or_create_client_tunnel("host", 1234, True, "pass")
    assert h == "127.0.0.1"
    assert p == 50000


@patch("usbip_gui.gui.client.socket.create_connection")
@patch("usbip_gui.gui.client.ssl.create_default_context")
@patch("usbip_gui.gui.client.subprocess.Popen")
@patch("usbip_gui.gui.client.tunnel_state")
@patch(
    "usbip_gui.gui.client.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("usbip_gui.gui.client.os.path.exists", return_value=False)
@patch("usbip_gui.gui.client.os.makedirs")
@patch("builtins.open", new_callable=mock_open, read_data="{}")
def test_get_or_create_client_tunnel_secure_new(
    _mock_open: MagicMock,
    _mock_makedirs: MagicMock,
    _mock_exists: MagicMock,
    mock_ask: MagicMock,
    mock_tunnel: MagicMock,
    mock_popen: MagicMock,
    mock_ctx: MagicMock,
    _mock_sock: MagicMock,
):
    """Test get tunnel with new process creation and user accepting cert."""
    mock_tunnel.client_processes = {}

    # Mock SSL cert response
    mock_ssock = (
        mock_ctx.return_value.wrap_socket.return_value.__enter__.return_value
    )
    mock_ssock.getpeercert.return_value = b"mock_cert_der"
    mock_ssock.recv.return_value = b"\x01"

    h, p = get_or_create_client_tunnel("host", 1234, True, "pass")
    assert h == "127.0.0.1"
    assert p > 0
    mock_popen.assert_called_once()
    mock_ask.assert_called_once()


@patch("usbip_gui.gui.client.socket.create_connection")
@patch("usbip_gui.gui.client.ssl.create_default_context")
@patch(
    "usbip_gui.gui.client.QMessageBox.question",
    return_value=QMessageBox.StandardButton.No,
)
@patch("usbip_gui.gui.client.os.path.exists", return_value=False)
def test_get_or_create_client_tunnel_reject_cert(
    _mock_exists: MagicMock,
    mock_ask: MagicMock,
    mock_ctx: MagicMock,
    _mock_sock: MagicMock,
):
    """Test get tunnel when user rejects the new cert."""
    mock_ssock = (
        mock_ctx.return_value.wrap_socket.return_value.__enter__.return_value
    )
    mock_ssock.getpeercert.return_value = b"mock_cert_der"

    h, p = get_or_create_client_tunnel("host", 1234, True, "pass")
    assert h == ""
    assert p == 0
    mock_ask.assert_called_once()


@patch("usbip_gui.gui.client.socket.create_connection")
@patch("usbip_gui.gui.client.ssl.create_default_context")
@patch(
    "usbip_gui.gui.client.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("usbip_gui.gui.client.QMessageBox.critical")
@patch("usbip_gui.gui.client.os.path.exists", return_value=False)
@patch("usbip_gui.gui.client.os.makedirs")
@patch("builtins.open", new_callable=mock_open, read_data="{}")
def test_get_or_create_client_tunnel_auth_fail(
    _mock_open: MagicMock,
    _mock_makedirs: MagicMock,
    _mock_exists: MagicMock,
    mock_error: MagicMock,
    _mock_ask: MagicMock,
    mock_ctx: MagicMock,
    _mock_sock: MagicMock,
):
    """Test get tunnel when authentication fails."""
    mock_ssock = (
        mock_ctx.return_value.wrap_socket.return_value.__enter__.return_value
    )
    mock_ssock.getpeercert.return_value = b"mock_cert_der"
    mock_ssock.recv.return_value = b"\x00"

    h, p = get_or_create_client_tunnel("host", 1234, True, "badpass")
    assert h == ""
    assert p == 0
    mock_error.assert_called_once()


@patch("usbip_gui.gui.client.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client.subprocess.run")
def test_list_remote_usb(mock_run: MagicMock, mock_tunnel: MagicMock):
    """Test list remote usb."""
    mock_tunnel.return_value = ("127.0.0.1", 1234)
    mock_run.return_value.stdout = "1-1: Man : Desc (00:00)"
    res = list_remote_usb("host", 1234)
    assert len(res) == 1
    mock_run.assert_called_once()

    mock_tunnel.return_value = ("", 0)
    res = list_remote_usb("host", 1234)
    assert len(res) == 0


@patch("usbip_gui.gui.client.subprocess.run")
def test_list_attached_usb(mock_run: MagicMock):
    """Test list attached usb."""
    mock_run.return_value.stdout = ""
    list_attached_usb()
    mock_run.assert_called_with(
        ["sudo", "usbip", "port"], capture_output=True, text=True, check=False
    )


@patch("usbip_gui.gui.client.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client.subprocess.run")
def test_attach_remote_usb(mock_run: MagicMock, mock_tunnel: MagicMock):
    """Test attach remote usb."""
    mock_tunnel.return_value = ("127.0.0.1", 1234)
    attach_remote_usb("host", "1-1")
    mock_run.assert_called_once()

    mock_run.reset_mock()
    mock_tunnel.return_value = ("", 0)
    attach_remote_usb("host", "1-1")
    mock_run.assert_not_called()


@patch("usbip_gui.gui.client.subprocess.run")
def test_detach_remote_usb(mock_run: MagicMock):
    """Test detach remote usb."""
    detach_remote_usb(1)
    mock_run.assert_called_with(
        ["sudo", "usbip", "detach", "--port=1"],
        capture_output=True,
        text=True,
        check=False,
    )


@patch("usbip_gui.gui.client.QMessageBox.warning")
def test_check_secure_warning(mock_warning: MagicMock):
    """Test check secure warning."""
    ClientTab.check_secure_warning(MagicMock(), 0)
    mock_warning.assert_called_once()


@patch("usbip_gui.gui.client.QTreeWidgetItem")
@patch("usbip_gui.gui.client.list_remote_usb")
def test_refresh_remote(mock_list: MagicMock, mock_item: MagicMock):
    """Test refresh remote."""
    mock_list.return_value = [("1-1", "Man", "Desc")]
    tab = MagicMock()
    tab.remote_port_input.text.return_value = "1234"
    ClientTab.refresh_remote(tab)
    tab.remote_listbox.clear.assert_called_once()
    mock_item.assert_called_once_with(
        tab.remote_listbox, ["1-1", "Man", "Desc"]
    )


@patch("usbip_gui.gui.client.QTreeWidgetItem")
@patch("usbip_gui.gui.client.list_attached_usb")
def test_refresh_attached(mock_list: MagicMock, mock_item: MagicMock):
    """Test refresh attached."""
    mock_list.return_value = [("127.0.0.1", 1, "1-1", "Man", "Desc")]
    tab = MagicMock()
    ClientTab.refresh_attached(tab)
    tab.attached_listbox.clear.assert_called_once()
    mock_item.assert_called_once_with(
        tab.attached_listbox, ["127.0.0.1", "1", "1-1", "Man", "Desc"]
    )


@patch("usbip_gui.gui.client.time.sleep")
@patch("usbip_gui.gui.client.attach_remote_usb")
def test_attach_remote_ui(mock_attach: MagicMock, _mock_sleep: MagicMock):
    """Test attach remote from UI."""
    tab = MagicMock()
    tab.remote_port_input.get.return_value = "1234"
    tab.remote_listbox.selection.return_value = ["item1"]
    tab.remote_listbox.item.return_value = {"values": ["1-1"]}
    ClientTab.attach_remote(tab)
    mock_attach.assert_called_once()
    tab.refresh_remote.assert_called_once()
    tab.refresh_attached.assert_called_once()


@patch("usbip_gui.gui.client.time.sleep")
@patch("usbip_gui.gui.client.detach_remote_usb")
def test_detach_remote_ui(mock_detach: MagicMock, _mock_sleep: MagicMock):
    """Test detach remote from UI."""
    tab = MagicMock()
    tab.attached_listbox.selection.return_value = ["item1"]
    tab.attached_listbox.item.return_value = {"values": ["host", "1"]}
    ClientTab.detach_remote(tab)
    mock_detach.assert_called_once_with(1)
    tab.refresh_remote.assert_called_once()
    tab.refresh_attached.assert_called_once()


def test_on_double_click_remote():
    """Test remote double click."""
    tab = MagicMock()
    tab.remote_listbox.selection.return_value = ["item"]
    ClientTab.on_double_click_remote(tab, MagicMock(), 0)
    tab.attach_remote.assert_called_once()


def test_on_double_click_attached():
    """Test attached double click."""
    tab = MagicMock()
    tab.attached_listbox.selection.return_value = ["item"]
    ClientTab.on_double_click_attached(tab, MagicMock(), 0)
    tab.detach_remote.assert_called_once()


def test_parse_remote_list_short():
    """Test parse short remote list."""
    res = parse_remote_list("1-1: a: b")  # length 3
    assert not res


@patch("usbip_gui.gui.client.socket.create_connection")
@patch("usbip_gui.gui.client.ssl.create_default_context")
@patch("usbip_gui.gui.client.QMessageBox.critical")
def test_get_or_create_client_tunnel_no_cert(
    _mock_error: MagicMock, mock_ctx: MagicMock, _mock_conn: MagicMock
):
    """Test get or create client tunnel no cert."""

    mock_ssock = (
        mock_ctx.return_value.wrap_socket.return_value.__enter__.return_value
    )
    mock_ssock.getpeercert.return_value = None
    target, _port = get_or_create_client_tunnel(
        "localhost", 1234, True, "pass"
    )
    assert target == ""


@patch(
    "usbip_gui.gui.client.os.path.exists",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='{"localhost:1234": "FP"}',
)
@patch("usbip_gui.gui.client.socket.create_connection")
@patch("usbip_gui.gui.client.ssl.create_default_context")
def test_get_or_create_client_tunnel_known_hosts(
    mock_ctx: MagicMock,
    _mock_conn: MagicMock,
    _mock_open_f: MagicMock,
    _mock_exists: MagicMock,
):
    """Test get or create tunnel with known hosts."""

    mock_ssock = (
        mock_ctx.return_value.wrap_socket.return_value.__enter__.return_value
    )
    mock_ssock.getpeercert.return_value = b"der"
    mock_ssock.recv.return_value = b"\x01"
    with patch("usbip_gui.gui.client.hashlib.sha256") as mock_sha:
        mock_sha.return_value.hexdigest.return_value = "fp"
        get_or_create_client_tunnel("localhost", 1234, True, "pass")


@patch("usbip_gui.gui.client.socket.create_connection")
@patch("usbip_gui.gui.client.ssl.create_default_context")
@patch(
    "usbip_gui.gui.client.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("builtins.open", new_callable=mock_open, read_data="{}")
def test_get_or_create_client_tunnel_no_password(
    _mock_open: MagicMock,
    _mock_ask: MagicMock,
    mock_ctx: MagicMock,
    _mock_conn: MagicMock,
):
    """Test get or create tunnel no password."""

    mock_ssock = (
        mock_ctx.return_value.wrap_socket.return_value.__enter__.return_value
    )
    mock_ssock.getpeercert.return_value = b"der"
    with patch("usbip_gui.gui.client.QMessageBox.critical") as mock_err:
        target, _port = get_or_create_client_tunnel(
            "localhost", 1234, True, ""
        )
        mock_err.assert_called_once()
        assert target == ""


@patch("usbip_gui.gui.client.socket.create_connection")
@patch("usbip_gui.gui.client.ssl.create_default_context")
@patch(
    "usbip_gui.gui.client.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("builtins.open", new_callable=mock_open)
def test_get_or_create_client_tunnel_mismatch(
    _mock_open_f: MagicMock,
    _mock_ask: MagicMock,
    mock_ctx: MagicMock,
    _mock_conn: MagicMock,
):
    """Test get or create tunnel with mismatch."""

    mock_ssock = (
        mock_ctx.return_value.wrap_socket.return_value.__enter__.return_value
    )
    mock_ssock.getpeercert.side_effect = [b"der", b"der2"]
    with patch("usbip_gui.gui.client.QMessageBox.critical") as mock_err:
        target, _port = get_or_create_client_tunnel(
            "localhost", 1234, True, "pass"
        )
        mock_err.assert_called_once()
        assert target == ""


@patch("usbip_gui.gui.client.tunnel_state")
@patch(
    "usbip_gui.gui.client.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("builtins.open", new_callable=mock_open)
def test_get_or_create_client_tunnel_kill(
    _mock_open: MagicMock, _mock_ask: MagicMock, mock_state: MagicMock
):
    """Test get or create client tunnel kills old process."""

    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_state.client_processes = {
        ("localhost", 1234): (1111, mock_proc, "old_pass")
    }
    with (
        patch("usbip_gui.gui.client.subprocess.Popen"),
        patch("usbip_gui.gui.client.threading.Thread"),
        patch("usbip_gui.gui.client.time.sleep"),
        patch("usbip_gui.gui.client.socket.create_connection"),
        patch("usbip_gui.gui.client.ssl.create_default_context") as mock_ctx,
    ):
        mock_wrap = mock_ctx.return_value.wrap_socket.return_value
        mock_ssock = mock_wrap.__enter__.return_value
        mock_ssock.getpeercert.return_value = b"cert"
        mock_ssock.recv.return_value = b"\x01"
        get_or_create_client_tunnel("localhost", 1234, True, "new_pass")
        mock_proc.kill.assert_called_once()


@patch("usbip_gui.gui.client.list_remote_usb")
@patch("usbip_gui.gui.client.list_attached_usb")
def test_client_ui_errors(mock_attached: MagicMock, mock_remote: MagicMock):
    """Test client ui errors."""

    mock_remote.return_value = [("a", "b", "c")]
    mock_attached.return_value = [("a", 1, "b", "c", "d")]
    parent = None
    client_tab = ClientTab(parent)

    with (
        patch.object(
            client_tab.remote_listbox, "selectedItems", return_value=()
        ),
        patch.object(
            client_tab.attached_listbox, "selectedItems", return_value=()
        ),
    ):
        with (
            patch("usbip_gui.gui.client.QMessageBox.critical") as mock_err,
            patch.object(
                client_tab.remote_ip_input, "text", return_value="localhost"
            ),
            patch.object(
                client_tab.remote_port_input, "text", return_value="abc"
            ),
        ):
            client_tab.refresh_remote()
            mock_err.assert_called_once()

        with (
            patch("usbip_gui.gui.client.QMessageBox.critical") as mock_err,
            patch.object(
                client_tab.remote_ip_input, "text", return_value="localhost"
            ),
            patch.object(
                client_tab.remote_port_input, "text", return_value="abc"
            ),
        ):
            client_tab.attach_remote()
            mock_err.assert_called_once()

        with (
            patch("usbip_gui.gui.client.QMessageBox.critical") as mock_err,
            patch.object(
                client_tab.remote_ip_input, "text", return_value="localhost"
            ),
            patch.object(
                client_tab.remote_port_input, "text", return_value="1234"
            ),
        ):
            client_tab.attach_remote()
            mock_err.assert_called_once()

        with patch("usbip_gui.gui.client.QMessageBox.critical") as mock_err:
            client_tab.detach_remote()
            mock_err.assert_called_once()
